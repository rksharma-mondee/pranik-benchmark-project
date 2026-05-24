# pranik/evaluation/pipelines/local_eval.py
# Status: draft
# Clinical Reviewer Required: no
# TODO: Add task-specific scorer integration after raw model-output stability is measured.
"""Local evaluation runner for PRANIK benchmark cases."""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

import jsonlines
import structlog
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from evaluation.configs.eval_config import EvalConfig
from evaluation.prompts.prompt_builder import build_prompt
from models.adapters.base import AdapterConfig, ModelAdapter
from schemas.gold_label.gold_schema_v1 import BenchmarkCase


logger = structlog.get_logger(__name__)


class EvaluationResult(BaseModel):
    """Single model-output record from a local evaluation run."""

    case_id: str
    task: str
    model: str
    prompt: str
    raw_response: str
    parsed_output: Optional[dict[str, Any]] = None
    parse_success: bool
    error_message: Optional[str] = None
    latency_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    eval_config_hash: str


def _json_default(value: Any) -> str:
    """Serialize non-JSON-native config values.

    Args:
        value: Arbitrary value from configuration.

    Returns:
        JSON-serializable string representation.
    """
    if isinstance(value, Path):
        return value.as_posix()
    return str(value)


def compute_eval_config_hash(config: EvalConfig) -> str:
    """Compute reproducibility hash for an evaluation config.

    Args:
        config: Evaluation configuration.

    Returns:
        SHA256 hash of JSON-serialized config.
    """
    config_json = json.dumps(asdict(config), default=_json_default, sort_keys=True)
    return hashlib.sha256(config_json.encode("utf-8")).hexdigest()


def _safe_model_name(model_id: str) -> str:
    """Create filesystem-safe model name for output files.

    Args:
        model_id: Raw model identifier.

    Returns:
        Sanitized model identifier.
    """
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", model_id).strip("_")


def _output_task_name(config: EvalConfig) -> str:
    """Create task segment for the output filename.

    Args:
        config: Evaluation configuration.

    Returns:
        Single task name or mixed task marker.
    """
    return config.tasks[0] if len(config.tasks) == 1 else "mixed"


def _build_adapter(config: EvalConfig) -> ModelAdapter:
    """Instantiate the configured model adapter.

    Args:
        config: Evaluation configuration.

    Returns:
        Model adapter instance.
    """
    adapter_config = AdapterConfig(
        model_id=config.model_id,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )
    if config.model_id.lower().startswith("mock"):
        from models.adapters.mock_adapter import MockAdapter

        return MockAdapter(adapter_config)
    if config.model_id.lower().startswith("groq:"):
        from models.adapters.groq_adapter import GroqAdapter

        return GroqAdapter(adapter_config)

    from models.adapters.gemini_adapter import GeminiAdapter

    return GeminiAdapter(adapter_config)


def load_cases(config: EvalConfig) -> list[BenchmarkCase]:
    """Load and validate JSONL benchmark cases.

    Args:
        config: Evaluation configuration.

    Returns:
        Validated benchmark cases, filtered by configured tasks and max_cases.
    """
    cases: list[BenchmarkCase] = []
    for input_path in config.input_paths:
        with jsonlines.open(input_path, mode="r") as reader:
            for payload in reader:
                case = BenchmarkCase.model_validate(payload)
                if case.task not in config.tasks:
                    continue
                cases.append(case)
                if config.max_cases is not None and len(cases) >= config.max_cases:
                    return cases
    return cases


def parse_model_output(raw_response: str, case_id: str | None = None) -> dict[str, Any] | None:
    """Parse a raw model response into a JSON dictionary.

    Args:
        raw_response: Unmodified model output.
        case_id: Optional case identifier for structured parse-failure logs.

    Returns:
        Parsed JSON object, or None when parsing fails.
    """
    stripped = raw_response.strip()
    try:
        parsed = json.loads(stripped)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass

    logger.warning(
        "model_output_parse_failed",
        case_id=case_id,
        raw_response_preview=raw_response[:200],
    )
    return None


def _write_result(writer: jsonlines.Writer, result: EvaluationResult) -> None:
    """Write one evaluation result to JSONL immediately.

    Args:
        writer: Open jsonlines writer.
        result: Evaluation result to persist.
    """
    writer.write(result.model_dump(mode="json"))


def run_evaluation(config: EvalConfig) -> list[EvaluationResult]:
    """Run local evaluation and persist JSONL results incrementally.

    Args:
        config: Evaluation configuration.

    Returns:
        Evaluation results in execution order.

    Raises:
        RuntimeError: If adapter health check fails.
    """
    load_dotenv()
    config.output_dir.mkdir(parents=True, exist_ok=True)
    eval_config_hash = compute_eval_config_hash(config)
    adapter = _build_adapter(config)

    if not adapter.health_check():
        raise RuntimeError(f"Model adapter health check failed for {config.model_id}")

    cases = load_cases(config)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    output_file = (
        config.output_dir
        / f"{_safe_model_name(config.model_id)}_{_output_task_name(config)}_{timestamp}.jsonl"
    )

    results: list[EvaluationResult] = []
    model_errors = 0
    parse_failures = 0

    with jsonlines.open(output_file, mode="w") as writer:
        for case in cases:
            prompt = build_prompt(case)
            started = time.perf_counter()
            raw_response = ""
            error_message: str | None = None

            try:
                raw_response = adapter.generate(prompt)
            except Exception as exc:
                model_errors += 1
                error_message = str(exc)
                logger.error(
                    "model_generation_failed",
                    case_id=case.case_id,
                    task=case.task,
                    model_id=config.model_id,
                    error=error_message,
                )

            latency_ms = (time.perf_counter() - started) * 1000
            parsed_output = parse_model_output(raw_response, case_id=case.case_id)
            parse_success = parsed_output is not None
            if not parse_success:
                parse_failures += 1

            result = EvaluationResult(
                case_id=case.case_id,
                task=case.task,
                model=config.model_id,
                prompt=prompt,
                raw_response=raw_response,
                parsed_output=parsed_output,
                parse_success=parse_success,
                error_message=error_message,
                latency_ms=latency_ms,
                eval_config_hash=eval_config_hash,
            )
            results.append(result)

            if error_message is None or config.save_failed_cases:
                _write_result(writer, result)

    logger.info(
        "local_eval_summary",
        total_cases=len(cases),
        success=sum(result.error_message is None for result in results),
        parse_failures=parse_failures,
        model_errors=model_errors,
        output_file=str(output_file),
    )
    return results


# TODO(batch): replace single-case loop with batch inference in Phase 3
# TODO(safety): pipe EvaluationResult through safety/pipeline.py after scoring
# TODO(metrics): add task-specific scorer after raw outputs are stable
# FUTURE: replace file-based output with DVC-tracked dataset in Phase 4

if __name__ == "__main__":
    config = EvalConfig(model_id="mock-triage", max_cases=5)
    results = run_evaluation(config)
