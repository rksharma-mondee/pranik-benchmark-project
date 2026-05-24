# pranik/preprocessing/pii_scrubber.py
# Status: draft
# Clinical Reviewer Required: no
# DPDP 2025: this file is part of the compliance pipeline - do not skip
# TODO: Validate Aadhaar regex against edge cases with legal team.
"""PII detection and redaction for Indian clinical benchmark cases."""

from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import re
from typing import Any

import structlog

from preprocessing.configs.preprocessing_config import PreprocessingConfig


# TODO(dedup): add MinHash LSH deduplication via Setu in Phase 3
# TODO(indic): replace langdetect with IndicLID for better Indic accuracy
# TODO(consent): add consent_verified field check before processing real data
# TODO(erasure): implement case deletion by case_id for DPDP erasure rights
# FUTURE: integrate Presidio with custom MedNER for clinical entity types


logger = structlog.get_logger(__name__)

STANDARD_ENTITIES = ["PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "LOCATION", "DATE_TIME"]
CUSTOM_PATTERNS: tuple[tuple[str, str, float], ...] = (
    ("AADHAAR_NUMBER", r"\b\d{4}\s?\d{4}\s?\d{4}\b", 0.90),
    ("AYUSHMAN_ID", r"(?i)\b[A-Z]{2}-\d{2}-\d{4}-\d{7}\b", 0.90),
    ("INDIAN_PHONE", r"\b(\+91[\s-]?)?\d{10}\b", 0.88),
    ("PAN_NUMBER", r"(?i)\b[A-Z]{5}\d{4}[A-Z]\b", 0.90),
    ("VOTER_ID", r"(?i)\b[A-Z]{3}\d{7}\b", 0.85),
)
FALLBACK_PATTERNS: tuple[tuple[str, re.Pattern[str], float], ...] = (
    *(
        (entity_type, re.compile(pattern), score)
        for entity_type, pattern, score in CUSTOM_PATTERNS
    ),
    (
        "EMAIL_ADDRESS",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        0.85,
    ),
    ("PHONE_NUMBER", re.compile(r"\b(\+91[\s-]?)?\d{10}\b"), 0.75),
)


def _placeholder(entity_type: str) -> str:
    return f"<{entity_type}_REDACTED>"


def _make_finding(entity_type: str, start: int, end: int, score: float) -> Any:
    from preprocessing.pipeline import PIIFinding

    return PIIFinding(
        entity_type=entity_type,
        start=start,
        end=end,
        score=score,
        scrubbed_value=_placeholder(entity_type),
    )


@lru_cache(maxsize=1)
def _build_analyzer() -> Any:
    from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer

    analyzer = AnalyzerEngine()
    for entity_type, regex, score in CUSTOM_PATTERNS:
        recognizer = PatternRecognizer(
            supported_entity=entity_type,
            patterns=[Pattern(name=entity_type.lower(), regex=regex, score=score)],
        )
        analyzer.registry.add_recognizer(recognizer)
    return analyzer


def _presidio_findings(text: str, threshold: float) -> list[Any]:
    analyzer = _build_analyzer()
    results = analyzer.analyze(
        text=text,
        language="en",
        entities=[*STANDARD_ENTITIES, *(pattern[0] for pattern in CUSTOM_PATTERNS)],
        score_threshold=threshold,
    )
    return [
        _make_finding(result.entity_type, result.start, result.end, float(result.score))
        for result in results
    ]


def _fallback_findings(text: str, threshold: float) -> list[Any]:
    findings: list[Any] = []
    for entity_type, pattern, score in FALLBACK_PATTERNS:
        if score < threshold:
            continue
        for match in pattern.finditer(text):
            findings.append(_make_finding(entity_type, match.start(), match.end(), score))
    return findings


def _dedupe_overlapping_findings(findings: list[Any]) -> list[Any]:
    ordered = sorted(
        findings,
        key=lambda finding: (
            finding.start,
            -(finding.end - finding.start),
            -finding.score,
            finding.entity_type,
        ),
    )
    selected: list[Any] = []
    occupied: list[range] = []
    for finding in ordered:
        current_span = range(finding.start, finding.end)
        if any(
            max(current_span.start, existing.start) < min(current_span.stop, existing.stop)
            for existing in occupied
        ):
            continue
        selected.append(finding)
        occupied.append(current_span)
    return sorted(selected, key=lambda finding: finding.start)


def _replace_findings(text: str, findings: list[Any]) -> str:
    scrubbed = text
    for finding in sorted(findings, key=lambda item: item.start, reverse=True):
        scrubbed = scrubbed[: finding.start] + finding.scrubbed_value + scrubbed[finding.end :]
    return scrubbed


def scrub_text(text: str, config: PreprocessingConfig) -> tuple[str, list[Any]]:
    """Scrub PII from a string, returning the redacted text and findings."""

    if not config.pii_enabled or not text:
        return text, []

    try:
        findings = _presidio_findings(text, config.pii_score_threshold)
    except Exception as exc:
        logger.warning("presidio_unavailable_using_regex_fallback", error_type=type(exc).__name__)
        findings = _fallback_findings(text, config.pii_score_threshold)

    findings = _dedupe_overlapping_findings(findings)
    return _replace_findings(text, findings), findings


def _scrub_nested_string(
    case: dict[str, Any],
    path: tuple[str, ...],
    config: PreprocessingConfig,
    case_id: str,
) -> list[Any]:
    current: Any = case
    for key in path[:-1]:
        if not isinstance(current, dict):
            return []
        current = current.get(key)
    if not isinstance(current, dict):
        return []

    final_key = path[-1]
    value = current.get(final_key)
    if not isinstance(value, str):
        return []

    scrubbed_text, findings = scrub_text(value, config)
    current[final_key] = scrubbed_text
    for finding in findings:
        logger.info(
            "pii_scrubbed",
            case_id=case_id,
            entity_type=finding.entity_type,
            start=finding.start,
            end=finding.end,
            score=finding.score,
        )
    return findings


def scrub_case(case: dict[str, Any], config: PreprocessingConfig) -> tuple[dict[str, Any], list[Any]]:
    """Scrub approved text fields from a benchmark case without mutating input."""

    scrubbed = deepcopy(case)
    case_id = str(scrubbed.get("case_id", "unknown"))
    findings: list[Any] = []

    for path in (
        ("input", "patient_query"),
        ("gold_label", "reasoning"),
        ("gold_label", "action"),
        ("unsafe_answer",),
    ):
        findings.extend(_scrub_nested_string(scrubbed, path, config, case_id))

    return scrubbed, findings
