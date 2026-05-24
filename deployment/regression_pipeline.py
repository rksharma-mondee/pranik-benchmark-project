# pranik/deployment/regression_pipeline.py
# Status: draft
# Clinical Reviewer Required: no
# TODO: add email/Slack alert on critical regression in Phase 4.
"""End-to-end monthly regression pipeline for PRANIK."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
import time
from typing import Any, Optional

import jsonlines
from pydantic import BaseModel
import structlog

from deployment.pipeline_config import PipelineConfig
from evaluation.analysis.clinician_export import export_for_clinician_review
from evaluation.analysis.failure_analyzer import analyze_failures
from evaluation.comparison.comparison_report import (
    ComparisonReport,
    build_comparison_report,
    save_comparison_report,
)
from evaluation.comparison.model_registry import ComparisonModel
from evaluation.configs.eval_config import EvalConfig
from evaluation.pipelines.local_eval import run_evaluation
from evaluation.scoring.score_predictions import score_predictions
from evaluation.scoring.types import ScoreReport
from preprocessing.configs.preprocessing_config import PreprocessingConfig
from preprocessing.pipeline import preprocess_dataset
from schemas.gold_label.gold_schema_v1 import BenchmarkCase


# TODO(schedule): add Windows Task Scheduler / cron trigger in Phase 4
# TODO(notify): add Slack webhook on critical regression alert
# TODO(dvc): commit new dataset version after successful pipeline run
# TODO(labelstudio): push fatal_miss cases to Label Studio review queue
# FUTURE: replace manual trigger with GitHub Actions monthly schedule


logger = structlog.get_logger(__name__)


class StageResult(BaseModel):
    """Status and output metadata for one pipeline stage."""

    stage: str
    status: str
    duration_seconds: float
    output_path: Optional[Path] = None
    error_message: Optional[str] = None


class RegressionAlert(BaseModel):
    """Metric regression alert between current and previous comparisons."""

    metric: str
    model_id: str
    previous_value: float
    current_value: float
    drop_pct: float
    severity: str


class PipelineResult(BaseModel):
    """Full regression pipeline result."""

    run_id: str
    started_at: datetime
    completed_at: Optional[datetime]
    status: str
    stages: list[StageResult]
    regression_alerts: list[RegressionAlert] = []
    fatal_miss_count: int = 0
    production_blocked_models: list[str] = []
    report_path: Optional[Path] = None


@dataclass
class _PipelineState:
    gold_cases_path: Path | None = None
    eval_result_paths: dict[str, Path] | None = None
    score_reports: dict[str, ScoreReport] | None = None
    comparison_report: ComparisonReport | None = None
    comparison_report_path: Path | None = None


def _safe_name(value: str) -> str:
    return "".join(
        character if character.isalnum() or character in {"-", "_", "."} else "_"
        for character in value
    ).strip("_")


def _normalize_model_id(model_id: str) -> str:
    lowered = model_id.lower()
    if lowered.startswith(("groq:", "mock", "gemini")):
        return model_id
    return f"groq:{model_id}"


def _display_name(model_id: str) -> str:
    native = model_id.removeprefix("groq:")
    if "llama-3.3-70b" in native:
        return "llama-3.3-70b"
    if "llama-3.1-8b" in native:
        return "llama-3.1-8b"
    return native


def _output_task_name(tasks: list[str]) -> str:
    return tasks[0] if len(tasks) == 1 else "mixed"


def _jsonl_paths(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.exists():
        return []
    return sorted(item for item in path.glob("*.jsonl") if item.is_file())


def _normalize_language_code(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    language_map = {
        "bn": "bn",
        "bengali": "bn",
        "en": "en-IN",
        "en-in": "en-IN",
        "english": "en-IN",
        "hi": "hi",
        "hindi": "hi",
        "kn": "kn",
        "kannada": "kn",
        "mix": "mix",
        "mixed": "mix",
        "te": "te",
        "telugu": "te",
    }
    return language_map.get(value.strip().lower(), value)


def _sanitize_gold_payload(payload: dict[str, Any]) -> dict[str, Any]:
    cleaned = {
        key: value
        for key, value in payload.items()
        if key in BenchmarkCase.model_fields
    }

    cleaned["language"] = _normalize_language_code(cleaned.get("language"))

    code_mix = cleaned.get("code_mix")
    if isinstance(code_mix, dict):
        code_mix = dict(code_mix)
        code_mix["primary_language"] = _normalize_language_code(
            code_mix.get("primary_language")
        )
        secondary_languages = code_mix.get("secondary_languages", [])
        if isinstance(secondary_languages, list):
            code_mix["secondary_languages"] = [
                _normalize_language_code(language)
                for language in secondary_languages
            ]
        cleaned["code_mix"] = code_mix

    annotation = cleaned.get("annotation")
    if isinstance(annotation, dict):
        annotation = dict(annotation)
        annotator_tier = annotation.get("annotator_tier")
        if not isinstance(annotator_tier, int) or annotator_tier < 1:
            annotation["annotator_tier"] = 1
        cleaned["annotation"] = annotation

    return cleaned


def _merge_gold_cases(paths: list[Path], output_path: Path, tasks: list[str]) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    written = 0
    with jsonlines.open(output_path, mode="w") as writer:
        for path in paths:
            with jsonlines.open(path, mode="r") as reader:
                for payload in reader:
                    if payload.get("task") not in tasks:
                        continue
                    case_id = payload.get("case_id")
                    if isinstance(case_id, str) and case_id in seen:
                        continue
                    try:
                        case = BenchmarkCase.model_validate(
                            _sanitize_gold_payload(payload)
                        )
                    except Exception as exc:
                        logger.warning(
                            "regression_gold_case_skipped",
                            case_id=case_id,
                            task=payload.get("task"),
                            source_path=str(path),
                            error=str(exc),
                        )
                        continue
                    seen.add(case.case_id)
                    writer.write(case.model_dump(mode="json"))
                    written += 1

    if written == 0:
        raise RuntimeError(
            f"No schema-valid gold cases found for tasks {tasks} in {paths}"
        )
    return output_path


def _prepare_gold_cases(config: PipelineConfig, run_id: str) -> Path:
    paths = _jsonl_paths(config.gold_cases_dir)
    if not paths:
        raise FileNotFoundError(f"No JSONL gold cases found in {config.gold_cases_dir}")
    return _merge_gold_cases(
        paths,
        config.reports_dir / f"pipeline_gold_cases_{run_id}.jsonl",
        config.tasks,
    )


def _latest_eval_result_path(model_id: str, tasks: list[str], results_dir: Path) -> Path:
    safe_model = _safe_name(model_id)
    task_name = _output_task_name(tasks)
    matches = sorted(
        results_dir.glob(f"{safe_model}_{task_name}_*.jsonl"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not matches:
        raise FileNotFoundError(f"No evaluation result found for {model_id} on {task_name}")
    return matches[0]


def _comparison_paths(reports_dir: Path) -> list[Path]:
    if not reports_dir.exists():
        return []
    paths = list(reports_dir.glob("comparison_*.json"))
    paths.extend(reports_dir.glob("*_comparison_*.json"))
    return sorted(set(paths), key=lambda path: path.stat().st_mtime, reverse=True)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _comparison_model_lookup(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for model in report.get("models", []):
        if isinstance(model, dict) and model.get("model_id"):
            lookup[str(model["model_id"])] = model
    return lookup


def _metric_drop(previous: float, current: float) -> float:
    if previous == 0:
        return 0.0 if current >= previous else 1.0
    return (previous - current) / abs(previous)


def _run_stage(stage: str, action: Callable[[], Path | None]) -> StageResult:
    started = time.perf_counter()
    try:
        output_path = action()
    except Exception as exc:
        logger.exception("regression_stage_failed", stage=stage, error=str(exc))
        return StageResult(
            stage=stage,
            status="failed",
            duration_seconds=time.perf_counter() - started,
            error_message=str(exc),
        )
    return StageResult(
        stage=stage,
        status="success",
        duration_seconds=time.perf_counter() - started,
        output_path=output_path,
    )


def _skipped(stage: str) -> StageResult:
    return StageResult(stage=stage, status="skipped", duration_seconds=0.0)


def _preprocessing_input_dir(config: PipelineConfig) -> Path:
    if config.gold_cases_dir.name == "processed":
        return Path("datasets/synthetic")
    return config.gold_cases_dir


def _stage_preprocessing(config: PipelineConfig) -> Path:
    input_dir = _preprocessing_input_dir(config)
    preprocessing_config = PreprocessingConfig(
        input_dir=input_dir,
        output_dir=config.gold_cases_dir,
        rejected_dir=Path("datasets/rejected"),
        audit_log_path=Path("datasets/audit/pii_audit_log.jsonl"),
    )
    preprocess_dataset(input_dir=input_dir, config=preprocessing_config)
    return config.gold_cases_dir


def _stage_evaluation(config: PipelineConfig, state: _PipelineState, run_id: str) -> Path:
    gold_cases_path = _prepare_gold_cases(config, run_id)
    state.gold_cases_path = gold_cases_path
    state.eval_result_paths = {}
    normalized_models = [_normalize_model_id(model_id) for model_id in config.model_ids]

    for model_id in normalized_models:
        eval_config = EvalConfig(
            model_id=model_id,
            tasks=config.tasks,
            input_paths=[gold_cases_path],
            output_dir=config.results_dir,
        )
        try:
            run_evaluation(eval_config)
            state.eval_result_paths[model_id] = _latest_eval_result_path(
                model_id,
                config.tasks,
                config.results_dir,
            )
        except Exception as exc:
            logger.error(
                "regression_model_evaluation_skipped",
                model_id=model_id,
                error=str(exc),
            )

    if not state.eval_result_paths:
        raise RuntimeError("All model evaluations failed or were skipped")
    return config.results_dir


def _stage_scoring(config: PipelineConfig, state: _PipelineState) -> Path:
    if not state.gold_cases_path:
        state.gold_cases_path = _prepare_gold_cases(config, "latest")
    if not state.eval_result_paths:
        raise RuntimeError("No evaluation results available for scoring")

    config.reports_dir.mkdir(parents=True, exist_ok=True)
    state.score_reports = {}
    for model_id, eval_path in state.eval_result_paths.items():
        report_path = config.reports_dir / f"{_safe_name(model_id)}_{_output_task_name(config.tasks)}_scores.json"
        score_report = score_predictions(
            eval_results_path=eval_path,
            gold_cases_path=state.gold_cases_path,
            output_report_path=report_path,
        )
        state.score_reports[model_id] = score_report

    return config.reports_dir


def _stage_failure_analysis(config: PipelineConfig, state: _PipelineState) -> Path:
    if not state.score_reports or not state.eval_result_paths or not state.gold_cases_path:
        raise RuntimeError("Scoring outputs are required for failure analysis")

    for model_id, score_report in state.score_reports.items():
        eval_path = state.eval_result_paths[model_id]
        failure_report = analyze_failures(
            score_report=score_report,
            eval_results_path=eval_path,
            gold_cases_path=state.gold_cases_path,
        )
        csv_path = config.reports_dir / f"clinician_review_{_safe_name(model_id)}_{score_report.task}.csv"
        export_for_clinician_review(failure_report, csv_path)
    return config.reports_dir


def _stage_comparison(config: PipelineConfig, state: _PipelineState) -> Path:
    if not state.score_reports or not state.gold_cases_path:
        raise RuntimeError("Score reports are required for comparison")

    scored_reports = [
        (_display_name(model_id), report)
        for model_id, report in state.score_reports.items()
    ]
    task_name = _output_task_name(config.tasks)
    state.comparison_report = build_comparison_report(
        task=task_name,
        benchmark_path=state.gold_cases_path,
        scored_reports=scored_reports,
    )
    state.comparison_report_path = save_comparison_report(
        state.comparison_report,
        config.reports_dir,
    )
    return state.comparison_report_path


def _stage_regression_check(
    config: PipelineConfig,
    state: _PipelineState,
    result: PipelineResult,
) -> Path | None:
    current_path = state.comparison_report_path
    if current_path is None:
        paths = _comparison_paths(config.reports_dir)
        current_path = paths[0] if paths else None
    if current_path is None:
        return None

    paths = [path for path in _comparison_paths(config.reports_dir) if path != current_path]
    if not paths:
        return current_path

    current = _load_json(current_path)
    previous = _load_json(paths[0])
    previous_models = _comparison_model_lookup(previous)
    current_models = _comparison_model_lookup(current)

    for model_id, current_model in current_models.items():
        previous_model = previous_models.get(model_id)
        if not previous_model:
            continue
        for metric in ("emergency_recall", "severity_accuracy"):
            previous_value = float(previous_model.get(metric) or 0.0)
            current_value = float(current_model.get(metric) or 0.0)
            drop_pct = _metric_drop(previous_value, current_value)
            if drop_pct > config.regression_alert_threshold:
                result.regression_alerts.append(
                    RegressionAlert(
                        metric=metric,
                        model_id=model_id,
                        previous_value=previous_value,
                        current_value=current_value,
                        drop_pct=drop_pct,
                        severity="critical" if metric == "emergency_recall" else "warning",
                    )
                )

        previous_fatal = float(previous_model.get("fatal_failure_count") or 0.0)
        current_fatal = float(current_model.get("fatal_failure_count") or 0.0)
        if current_fatal > previous_fatal:
            increase = current_fatal - previous_fatal
            result.regression_alerts.append(
                RegressionAlert(
                    metric="fatal_failure_count",
                    model_id=model_id,
                    previous_value=previous_fatal,
                    current_value=current_fatal,
                    drop_pct=increase,
                    severity="critical",
                )
            )

    return current_path


def _stage_safety_gate(config: PipelineConfig, state: _PipelineState, result: PipelineResult) -> None:
    score_reports = state.score_reports or {}
    fatal_miss_count = sum(report.fatal_failure_count for report in score_reports.values())
    result.fatal_miss_count = fatal_miss_count
    blocked = [
        model_id
        for model_id, report in score_reports.items()
        if report.fatal_failure_count > config.fatal_miss_threshold
    ]
    result.production_blocked_models = blocked
    if config.block_on_fatal_miss and fatal_miss_count > config.fatal_miss_threshold:
        logger.critical(
            "regression_pipeline_safety_gate_blocked",
            fatal_miss_count=fatal_miss_count,
            blocked_models=blocked,
        )
        result.status = "blocked"


def _write_pipeline_result(result: PipelineResult, config: PipelineConfig) -> Path:
    config.reports_dir.mkdir(parents=True, exist_ok=True)
    path = config.reports_dir / f"pipeline_run_{result.run_id}.json"
    result.report_path = path
    path.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def _stage_icon(status: str) -> str:
    return {"success": "✅", "failed": "❌", "skipped": "⏭"}.get(status, "•")


def _print_summary(result: PipelineResult) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print("════════════════════════════════════════════════════")
    print("PRANIK Regression Pipeline")
    print(f"Run ID  : {result.run_id}")
    print(f"Started : {result.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print("════════════════════════════════════════════════════")
    print("STAGES")
    for stage in result.stages:
        suffix = f"  ({stage.error_message})" if stage.error_message else ""
        print(f"{_stage_icon(stage.status)} {stage.stage:<18} {stage.duration_seconds:.1f}s{suffix}")
    print("────────────────────────────────────────────────────")
    print("REGRESSION ALERTS")
    if result.regression_alerts:
        for alert in result.regression_alerts:
            print(
                f"⚠ {alert.model_id} {alert.metric}: "
                f"{alert.previous_value:.3f} → {alert.current_value:.3f} "
                f"(-{alert.drop_pct:.1%})"
            )
    else:
        print("none")
    print("────────────────────────────────────────────────────")
    print("SAFETY GATE")
    blocked = ", ".join(result.production_blocked_models) if result.production_blocked_models else "none"
    print(f"fatal_misses: {result.fatal_miss_count}")
    print(f"production_blocked: {blocked}")
    print("────────────────────────────────────────────────────")
    if result.status == "success":
        status = "✅ PIPELINE COMPLETE"
    elif result.status == "blocked":
        status = "⛔ PIPELINE BLOCKED"
    else:
        status = "❌ PIPELINE FAILED"
    print(f"STATUS: {status}")
    print(f"Report: {result.report_path}")
    print("════════════════════════════════════════════════════")


def run_regression_pipeline(config: PipelineConfig) -> PipelineResult:
    """Run the full PRANIK benchmark regression pipeline."""

    run_id = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    result = PipelineResult(
        run_id=run_id,
        started_at=datetime.now(UTC),
        completed_at=None,
        status="success",
        stages=[],
    )
    state = _PipelineState()

    stages: list[tuple[str, bool, Callable[[], Path | None]]] = [
        ("preprocessing", config.run_preprocessing, lambda: _stage_preprocessing(config)),
        ("evaluation", config.run_evaluation, lambda: _stage_evaluation(config, state, run_id)),
        ("scoring", config.run_scoring, lambda: _stage_scoring(config, state)),
        ("failure_analysis", config.run_failure_analysis, lambda: _stage_failure_analysis(config, state)),
        ("comparison", config.run_comparison, lambda: _stage_comparison(config, state)),
        (
            "regression_check",
            config.compare_against_previous,
            lambda: _stage_regression_check(config, state, result),
        ),
    ]

    for stage_name, enabled, action in stages:
        if not enabled:
            result.stages.append(_skipped(stage_name))
            continue
        stage_result = _run_stage(stage_name, action)
        result.stages.append(stage_result)
        if stage_result.status == "failed":
            result.status = "failed"
            break

    if result.status != "failed":
        _stage_safety_gate(config, state, result)

    result.completed_at = datetime.now(UTC)
    _write_pipeline_result(result, config)
    _print_summary(result)
    return result
