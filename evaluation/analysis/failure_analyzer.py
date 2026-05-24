# pranik/evaluation/analysis/failure_analyzer.py
# Status: draft
# Clinical Reviewer Required: yes - failure taxonomy must be validated by MD
# TODO: add hallucination detection as separate failure type in Phase 3
"""Failure analysis for PRANIK score reports."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jsonlines
import structlog

from evaluation.analysis.failure_types import (
    FAILURE_SEVERITY_MAP,
    FailureAnalysisReport,
    FailureRecord,
    FailureSeverity,
    FailureType,
)
from evaluation.pipelines.local_eval import EvaluationResult
from evaluation.scoring.types import CaseScore, ScoreReport
from schemas.gold_label.gold_schema_v1 import BenchmarkCase


logger = structlog.get_logger(__name__)

SEVERITY_RANK = {
    FailureSeverity.CRITICAL: 4,
    FailureSeverity.HIGH: 3,
    FailureSeverity.MEDIUM: 2,
    FailureSeverity.LOW: 1,
}

TRIAGE_REQUIRED_KEYS = {
    "label_type",
    "urgency",
    "action",
    "detected_red_flags",
    "reasoning",
    "escalation_required",
    "is_ambiguous",
}


def _load_evaluation_results(eval_results_path: Path) -> dict[str, EvaluationResult]:
    """Load evaluation results keyed by case ID."""
    with jsonlines.open(eval_results_path, mode="r") as reader:
        results = [EvaluationResult.model_validate(payload) for payload in reader]
    return {result.case_id: result for result in results}


def _load_gold_payloads(gold_cases_path: Path) -> dict[str, dict[str, Any]]:
    """Load gold case payloads while tolerating draft/synthetic schema drift."""
    payloads: dict[str, dict[str, Any]] = {}
    with jsonlines.open(gold_cases_path, mode="r") as reader:
        for payload in reader:
            case_id = payload.get("case_id")
            if isinstance(case_id, str):
                payloads[case_id] = payload
                try:
                    BenchmarkCase.model_validate(payload)
                except Exception as exc:
                    logger.warning(
                        "gold_case_schema_validation_skipped",
                        case_id=case_id,
                        error=str(exc),
                    )
    return payloads


def _patient_query_preview(gold_payload: dict[str, Any] | None) -> str:
    """Extract patient query preview from a gold payload."""
    if not gold_payload:
        return ""
    input_payload = gold_payload.get("input", {})
    if not isinstance(input_payload, dict):
        return ""
    return str(input_payload.get("patient_query", ""))[:120]


def _is_synthetic(gold_payload: dict[str, Any] | None) -> bool:
    """Infer whether the source case is synthetic."""
    if not gold_payload:
        return True
    value = gold_payload.get("is_synthetic")
    return bool(value) if value is not None else True


def _has_wrong_format(score: CaseScore, result: EvaluationResult | None) -> bool:
    """Detect parseable but malformed model output for supported task types."""
    if result is None or result.parsed_output is None or not score.parse_success:
        return False
    if score.task == "triage":
        missing = TRIAGE_REQUIRED_KEYS - set(result.parsed_output.keys())
        if missing:
            return True
        label_type = result.parsed_output.get("label_type")
        return label_type not in {None, "triage"}
    return False


def _detect_wrong_language(score: CaseScore, result: EvaluationResult | None) -> bool:
    """Best-effort language failure detection without external language ID packages."""
    if result is None or not result.raw_response:
        return False
    if score.language in {"en-IN", "mix"}:
        return False
    response = result.raw_response
    non_ascii = sum(1 for character in response if ord(character) > 127)
    return len(response) > 40 and non_ascii == 0


def _identify_failure_types(score: CaseScore, result: EvaluationResult | None) -> list[FailureType]:
    """Identify all applicable failures for one scored case."""
    failures: list[FailureType] = []
    if score.is_fatal_miss:
        failures.append(FailureType.FATAL_UNDER_TRIAGE)
    if score.gold_urgency == "URGENT" and score.predicted_urgency == "SELF_CARE":
        failures.append(FailureType.DANGEROUS_UNDER_TRIAGE)
    if score.gold_urgency == "ROUTINE" and score.predicted_urgency == "EMERGENCY":
        failures.append(FailureType.OVER_TRIAGE)
    if score.gold_escalation is True and score.predicted_escalation is False:
        failures.append(FailureType.MISSED_ESCALATION)
    if score.gold_escalation is False and score.predicted_escalation is True:
        failures.append(FailureType.FALSE_ESCALATION)
    if score.is_unsafe_reassurance:
        failures.append(FailureType.UNSAFE_REASSURANCE)
    if not score.parse_success:
        failures.append(FailureType.PARSE_FAILURE)
    if _has_wrong_format(score, result):
        failures.append(FailureType.WRONG_FORMAT)
    if _detect_wrong_language(score, result):
        failures.append(FailureType.WRONG_LANGUAGE)
    if score.language == "mix" and not score.urgency_correct:
        failures.append(FailureType.CODE_MIX_FAILURE)
    return failures


def _primary_failure(failures: list[FailureType]) -> FailureType:
    """Choose the most severe failure type."""
    return max(
        failures,
        key=lambda failure: SEVERITY_RANK[FAILURE_SEVERITY_MAP[failure]],
    )


def _recommended_action(primary_failure: FailureType) -> str:
    """Map failure type to reviewer action."""
    actions = {
        FailureType.FATAL_UNDER_TRIAGE: (
            "Immediate MD review required. Add to EMERGENCY training set."
        ),
        FailureType.UNSAFE_REASSURANCE: (
            "Flag for safety audit. Review prompt constraints."
        ),
        FailureType.PARSE_FAILURE: (
            "Review prompt template. Check JSON output instruction."
        ),
        FailureType.CODE_MIX_FAILURE: (
            "Add to code-mix training examples. Check tokenizer."
        ),
        FailureType.MISSED_ESCALATION: (
            "Review escalation policy and add similar cases to safety set."
        ),
        FailureType.DANGEROUS_UNDER_TRIAGE: (
            "Review urgent-care boundary and add hard negative examples."
        ),
        FailureType.OVER_TRIAGE: (
            "Review over-triage pattern to reduce unnecessary emergency routing."
        ),
        FailureType.FALSE_ESCALATION: (
            "Review escalation precision and benign-case examples."
        ),
        FailureType.WRONG_FORMAT: (
            "Validate model output schema and tighten structured output prompt."
        ),
        FailureType.WRONG_LANGUAGE: (
            "Review language instruction and add language-specific examples."
        ),
    }
    return actions[primary_failure]


def _build_failure_record(
    score: CaseScore,
    failures: list[FailureType],
    result: EvaluationResult | None,
    gold_payload: dict[str, Any] | None,
) -> FailureRecord:
    """Build one failure record."""
    primary = _primary_failure(failures)
    severity = FAILURE_SEVERITY_MAP[primary]
    return FailureRecord(
        case_id=score.case_id,
        task=score.task,
        language=score.language,
        model=score.model,
        failure_types=failures,
        primary_failure=primary,
        failure_severity=severity,
        gold_urgency=score.gold_urgency,
        predicted_urgency=score.predicted_urgency,
        gold_escalation=score.gold_escalation,
        predicted_escalation=score.predicted_escalation,
        severity_penalty=score.severity_penalty,
        patient_query_preview=_patient_query_preview(gold_payload),
        raw_response_preview=(result.raw_response[:120] if result else score.raw_response_preview[:120]),
        recommended_action=_recommended_action(primary),
        is_synthetic=_is_synthetic(gold_payload),
        clinician_review_required=severity in {FailureSeverity.CRITICAL, FailureSeverity.HIGH},
    )


def _generate_recommendations(
    score_report: ScoreReport,
    failures: list[FailureRecord],
    failure_counter: Counter[str],
    language_counter: Counter[str],
) -> list[str]:
    """Generate top actionable recommendations."""
    recommendations: list[str] = []
    total = max(score_report.total_cases, 1)
    if failure_counter.get(FailureType.PARSE_FAILURE.value, 0) / total > 0.20:
        recommendations.append("Fix prompt template JSON instructions.")
    if failure_counter.get(FailureType.CODE_MIX_FAILURE.value, 0) / total > 0.30:
        recommendations.append("Prioritize code-mix dataset expansion.")
    if any(record.failure_severity == FailureSeverity.CRITICAL for record in failures):
        recommendations.append("Block model from production deployment until critical failures are reviewed.")

    total_by_language: dict[str, int] = defaultdict(int)
    for score in score_report.case_scores:
        total_by_language[score.language] += 1
    for language, failure_count in language_counter.items():
        language_total = total_by_language.get(language, 0)
        if language_total and failure_count / language_total > 0.50:
            recommendations.append(f"Expand {language} training and review data.")

    if not recommendations and failures:
        recommendations.append("Review recurring failure clusters before adding cases to scorecards.")
    if not recommendations:
        recommendations.append("No major failure cluster detected in this run.")
    return recommendations[:3]


def analyze_failures(
    score_report: ScoreReport,
    eval_results_path: Path,
    gold_cases_path: Path,
) -> FailureAnalysisReport:
    """Analyze failed cases from a score report."""
    eval_lookup = _load_evaluation_results(eval_results_path)
    gold_lookup = _load_gold_payloads(gold_cases_path)
    failure_records: list[FailureRecord] = []

    for case_score in score_report.case_scores:
        result = eval_lookup.get(case_score.case_id)
        gold_payload = gold_lookup.get(case_score.case_id)
        failures = _identify_failure_types(case_score, result)
        if not failures:
            continue
        failure_records.append(
            _build_failure_record(case_score, failures, result, gold_payload)
        )

    failure_distribution: Counter[str] = Counter()
    failure_by_language: Counter[str] = Counter()
    failure_by_task: Counter[str] = Counter()
    for record in failure_records:
        for failure_type in record.failure_types:
            failure_distribution[failure_type.value] += 1
        failure_by_language[record.language] += 1
        failure_by_task[record.task] += 1

    critical_failures = [
        record
        for record in failure_records
        if record.failure_severity == FailureSeverity.CRITICAL
    ]
    most_common_failure = (
        failure_distribution.most_common(1)[0][0] if failure_distribution else "none"
    )

    report = FailureAnalysisReport(
        model=score_report.model_id,
        task=score_report.task,
        total_cases_analyzed=score_report.total_cases,
        total_failures=len(failure_records),
        failure_rate=(
            len(failure_records) / score_report.total_cases
            if score_report.total_cases
            else 0.0
        ),
        critical_failure_count=len(critical_failures),
        failure_distribution=dict(failure_distribution),
        failure_by_language=dict(failure_by_language),
        failure_by_task=dict(failure_by_task),
        most_common_failure=most_common_failure,
        critical_failures=critical_failures,
        all_failures=failure_records,
        recommendations=_generate_recommendations(
            score_report,
            failure_records,
            failure_distribution,
            failure_by_language,
        ),
        generated_at=datetime.now(UTC),
    )
    logger.info(
        "failure_analysis_summary",
        model=report.model,
        task=report.task,
        total_failures=report.total_failures,
        critical_failure_count=report.critical_failure_count,
        most_common_failure=report.most_common_failure,
    )
    return report
