# pranik/evaluation/scoring/score_predictions.py
# Status: draft
# Clinical Reviewer Required: yes — penalty matrix must be validated by MD
# TODO: Export fatal_miss cases to annotation review queue in Phase 3.
"""Score PRANIK model predictions against gold benchmark labels."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jsonlines
import structlog

from evaluation.pipelines.local_eval import EvaluationResult
from evaluation.scoring.metrics import (
    compute_emergency_recall,
    compute_escalation_accuracy,
    compute_per_language_accuracy,
    compute_severity_accuracy,
    compute_weighted_f1,
    detect_unsafe_reassurance,
)
from evaluation.scoring.types import CaseScore, ScoreReport, SeverityPenalty, get_penalty
from schemas.gold_label.gold_schema_v1 import BenchmarkCase, TriageGoldLabel


logger = structlog.get_logger(__name__)


def _load_evaluation_results(eval_results_path: Path) -> list[EvaluationResult]:
    """Load local evaluation result records from JSONL.

    Args:
        eval_results_path: Path to an EvaluationResult JSONL file.

    Returns:
        Validated evaluation results.
    """
    with jsonlines.open(eval_results_path, mode="r") as reader:
        return [EvaluationResult.model_validate(payload) for payload in reader]


def _load_gold_cases(gold_cases_path: Path) -> dict[str, BenchmarkCase]:
    """Load gold benchmark cases keyed by case_id.

    Args:
        gold_cases_path: Path to BenchmarkCase JSONL file.

    Returns:
        Mapping from case_id to BenchmarkCase.
    """
    with jsonlines.open(gold_cases_path, mode="r") as reader:
        cases = [BenchmarkCase.model_validate(payload) for payload in reader]
    return {case.case_id: case for case in cases}


def _extract_predicted_urgency(parsed_output: dict[str, Any] | None) -> str | None:
    """Extract normalized predicted urgency from parsed output.

    Args:
        parsed_output: Parsed model output.

    Returns:
        Uppercase urgency value, or None when missing.
    """
    if parsed_output is None:
        return None
    urgency = parsed_output.get("urgency")
    return str(urgency).upper() if urgency is not None else None


def _extract_predicted_escalation(parsed_output: dict[str, Any] | None) -> bool | None:
    """Extract predicted escalation flag from parsed output.

    Args:
        parsed_output: Parsed model output.

    Returns:
        Escalation boolean, or None when missing or not boolean-like.
    """
    if parsed_output is None or "escalation_required" not in parsed_output:
        return None

    value = parsed_output["escalation_required"]
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
    return None


def _build_case_score(result: EvaluationResult, gold_case: BenchmarkCase) -> CaseScore | None:
    """Build a per-case score from one result and one gold case.

    Args:
        result: Model evaluation output.
        gold_case: Gold benchmark case.

    Returns:
        CaseScore for supported triage labels, or None for unsupported labels.
    """
    if not isinstance(gold_case.gold_label, TriageGoldLabel):
        logger.warning(
            "unsupported_gold_label_for_scoring",
            case_id=result.case_id,
            task=result.task,
            label_type=gold_case.gold_label.label_type,
        )
        return None
    if gold_case.gold_label.urgency is None:
        logger.warning(
            "ambiguous_gold_label_skipped",
            case_id=result.case_id,
            task=result.task,
        )
        return None

    gold_urgency = gold_case.gold_label.urgency.value
    predicted_urgency = _extract_predicted_urgency(result.parsed_output)
    predicted_escalation = _extract_predicted_escalation(result.parsed_output)
    penalty = get_penalty(predicted_urgency, gold_urgency)
    is_unsafe_reassurance = detect_unsafe_reassurance(
        predicted_urgency=predicted_urgency,
        gold_urgency=gold_urgency,
        raw_response=result.raw_response,
    )

    return CaseScore(
        case_id=result.case_id,
        task=result.task,
        model=result.model,
        gold_urgency=gold_urgency,
        predicted_urgency=predicted_urgency,
        urgency_correct=predicted_urgency == gold_urgency,
        severity_penalty=float(penalty.value),
        is_fatal_miss=penalty == SeverityPenalty.FATAL_MISS,
        gold_escalation=gold_case.gold_label.escalation_required,
        predicted_escalation=predicted_escalation,
        escalation_correct=predicted_escalation == gold_case.gold_label.escalation_required,
        is_unsafe_reassurance=is_unsafe_reassurance,
        parse_success=result.parse_success,
        raw_response_preview=result.raw_response[:150],
        language=gold_case.language.value,
    )


def _default_report_path(report: ScoreReport) -> Path:
    """Build default score report path.

    Args:
        report: Score report requiring persistence.

    Returns:
        Timestamped JSON report path.
    """
    timestamp = report.generated_at.strftime("%Y%m%d_%H%M%S")
    safe_model = "".join(
        character if character.isalnum() or character in {"-", "_", "."} else "_"
        for character in report.model_id
    ).strip("_")
    file_name = "{}_{}_{}_scores.json".format(safe_model, report.task, timestamp)
    return Path("evaluation/reports") / file_name


def _save_report(report: ScoreReport, output_report_path: Path) -> None:
    """Persist a score report as JSON.

    Args:
        report: Score report to write.
        output_report_path: Destination JSON file.
    """
    output_report_path.parent.mkdir(parents=True, exist_ok=True)
    output_report_path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def score_predictions(
    eval_results_path: Path,
    gold_cases_path: Path,
    output_report_path: Path | None = None,
) -> ScoreReport:
    """Score model predictions against gold benchmark cases.

    Args:
        eval_results_path: EvaluationResult JSONL file from local_eval.
        gold_cases_path: BenchmarkCase JSONL file containing gold labels.
        output_report_path: Optional destination for ScoreReport JSON.

    Returns:
        Aggregate ScoreReport.
    """
    results = _load_evaluation_results(eval_results_path)
    gold_lookup = _load_gold_cases(gold_cases_path)
    case_scores: list[CaseScore] = []

    for result in results:
        gold_case = gold_lookup.get(result.case_id)
        if gold_case is None:
            logger.warning("gold_case_not_found", case_id=result.case_id)
            continue

        case_score = _build_case_score(result, gold_case)
        if case_score is not None:
            case_scores.append(case_score)

    total_cases = len(case_scores)
    parse_success_rate = (
        sum(1 for score in case_scores if score.parse_success) / total_cases
        if total_cases
        else 0.0
    )
    mean_severity_penalty = (
        sum(score.severity_penalty for score in case_scores) / total_cases
        if total_cases
        else 0.0
    )

    report = ScoreReport(
        model_id=results[0].model if results else "unknown",
        task=results[0].task if results else "unknown",
        total_cases=total_cases,
        parse_success_rate=parse_success_rate,
        severity_accuracy=compute_severity_accuracy(case_scores),
        weighted_f1=compute_weighted_f1(case_scores),
        emergency_recall=compute_emergency_recall(case_scores),
        escalation_accuracy=compute_escalation_accuracy(case_scores),
        mean_severity_penalty=mean_severity_penalty,
        fatal_failure_count=sum(1 for score in case_scores if score.is_fatal_miss),
        unsafe_reassurance_count=sum(
            1 for score in case_scores if score.is_unsafe_reassurance
        ),
        per_language_accuracy=compute_per_language_accuracy(case_scores),
        case_scores=case_scores,
        generated_at=datetime.now(UTC),
    )

    logger.info(
        "score_report_summary",
        model_id=report.model_id,
        task=report.task,
        total_cases=report.total_cases,
        severity_accuracy=report.severity_accuracy,
        emergency_recall=report.emergency_recall,
        fatal_failure_count=report.fatal_failure_count,
        unsafe_reassurance_count=report.unsafe_reassurance_count,
    )

    report_path = output_report_path or _default_report_path(report)
    _save_report(report, report_path)
    logger.info("score_report_written", output_report_path=str(report_path))
    return report


def _latest_eval_results_path() -> Path:
    """Find latest local evaluation JSONL result file.

    Returns:
        Path to latest JSONL result.

    Raises:
        FileNotFoundError: If no evaluation result JSONL exists.
    """
    result_paths = sorted(
        Path("evaluation/results").glob("*.jsonl"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not result_paths:
        raise FileNotFoundError("No evaluation result JSONL files found.")
    return result_paths[0]


def _print_report_table(report: ScoreReport) -> None:
    """Print a concise score report to stdout.

    Args:
        report: Score report to print.
    """
    rows = [
        ("model_id", report.model_id),
        ("task", report.task),
        ("total_cases", report.total_cases),
        ("parse_success_rate", "{:.3f}".format(report.parse_success_rate)),
        ("severity_accuracy", "{:.3f}".format(report.severity_accuracy)),
        ("weighted_f1", "{:.3f}".format(report.weighted_f1)),
        ("emergency_recall", "{:.3f}".format(report.emergency_recall)),
        ("escalation_accuracy", "{:.3f}".format(report.escalation_accuracy)),
        ("mean_severity_penalty", "{:.3f}".format(report.mean_severity_penalty)),
        ("fatal_failure_count", report.fatal_failure_count),
        ("unsafe_reassurance_count", report.unsafe_reassurance_count),
        ("per_language_accuracy", report.per_language_accuracy),
    ]
    width = max(len(name) for name, _ in rows)
    for name, value in rows:
        print("{:<{width}}  {}".format(name, value, width=width))


# TODO(confusion): add confusion matrix export in Phase 3
# TODO(clinician): export fatal_miss cases to Label Studio review queue
# TODO(language): add per-language F1 using sklearn per-class metrics
# TODO(hallucination): pipe case_scores into safety/hallucination_detector.py
# FUTURE: stream ScoreReport to W&B as evaluation artifact in Phase 4

if __name__ == "__main__":
    latest_path = _latest_eval_results_path()
    score_report = score_predictions(
        eval_results_path=latest_path,
        gold_cases_path=Path("examples/triage_cases.jsonl"),
    )
    _print_report_table(score_report)
