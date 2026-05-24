# pranik/evaluation/analysis/failure_types.py
# Status: draft
# Clinical Reviewer Required: yes - failure taxonomy must be validated by MD
# TODO(validation): validate failure severity map with clinical safety board
"""Failure taxonomy and report models for PRANIK evaluation analysis."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class FailureType(str, Enum):
    """Actionable failure types detected from score reports."""

    FATAL_UNDER_TRIAGE = "fatal_under_triage"
    DANGEROUS_UNDER_TRIAGE = "dangerous_under_triage"
    OVER_TRIAGE = "over_triage"
    MISSED_ESCALATION = "missed_escalation"
    FALSE_ESCALATION = "false_escalation"
    UNSAFE_REASSURANCE = "unsafe_reassurance"
    PARSE_FAILURE = "parse_failure"
    WRONG_FORMAT = "wrong_format"
    WRONG_LANGUAGE = "wrong_language"
    CODE_MIX_FAILURE = "code_mix_failure"


class FailureSeverity(str, Enum):
    """Reviewer-facing severity labels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


FAILURE_SEVERITY_MAP: dict[FailureType, FailureSeverity] = {
    FailureType.FATAL_UNDER_TRIAGE: FailureSeverity.CRITICAL,
    FailureType.UNSAFE_REASSURANCE: FailureSeverity.CRITICAL,
    FailureType.DANGEROUS_UNDER_TRIAGE: FailureSeverity.HIGH,
    FailureType.MISSED_ESCALATION: FailureSeverity.HIGH,
    FailureType.PARSE_FAILURE: FailureSeverity.HIGH,
    FailureType.CODE_MIX_FAILURE: FailureSeverity.HIGH,
    FailureType.OVER_TRIAGE: FailureSeverity.MEDIUM,
    FailureType.FALSE_ESCALATION: FailureSeverity.MEDIUM,
    FailureType.WRONG_FORMAT: FailureSeverity.MEDIUM,
    FailureType.WRONG_LANGUAGE: FailureSeverity.MEDIUM,
}


class FailureRecord(BaseModel):
    """One failed benchmark case requiring analysis or review."""

    case_id: str
    task: str
    language: str
    model: str
    failure_types: list[FailureType]
    primary_failure: FailureType
    failure_severity: FailureSeverity
    gold_urgency: Optional[str]
    predicted_urgency: Optional[str]
    gold_escalation: Optional[bool]
    predicted_escalation: Optional[bool]
    severity_penalty: float
    patient_query_preview: str
    raw_response_preview: str
    recommended_action: str
    is_synthetic: bool = True
    clinician_review_required: bool


class FailureAnalysisReport(BaseModel):
    """Aggregate failure analysis for a score report."""

    model: str
    task: str
    total_cases_analyzed: int
    total_failures: int
    failure_rate: float
    critical_failure_count: int
    failure_distribution: dict[str, int]
    failure_by_language: dict[str, int]
    failure_by_task: dict[str, int]
    most_common_failure: str
    critical_failures: list[FailureRecord]
    all_failures: list[FailureRecord]
    recommendations: list[str]
    generated_at: datetime
