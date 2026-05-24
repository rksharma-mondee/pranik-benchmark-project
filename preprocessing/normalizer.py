# pranik/preprocessing/normalizer.py
# Status: draft
# Clinical Reviewer Required: no
# DPDP 2025: this file is part of the compliance pipeline - do not skip
# TODO: Add fixture-based tests for markdown, whitespace, Unicode, and romanized mix cases.
"""Case normalization for benchmark inputs."""

from __future__ import annotations

from copy import deepcopy
import re
import unicodedata
from typing import Any

from preprocessing.configs.preprocessing_config import PreprocessingConfig


# TODO(dedup): add MinHash LSH deduplication via Setu in Phase 3
# TODO(indic): replace langdetect with IndicLID for better Indic accuracy
# TODO(consent): add consent_verified field check before processing real data
# TODO(erasure): implement case deletion by case_id for DPDP erasure rights
# FUTURE: integrate Presidio with custom MedNER for clinical entity types


MARKDOWN_FENCE_RE = re.compile(r"```[\w]*\n?")
WHITESPACE_RE = re.compile(r"\s+")
INDIC_SCRIPT_RE = re.compile(r"[\u0900-\u0D7F]")
LATIN_RE = re.compile(r"[A-Za-z]")


def strip_markdown_fences(text: str) -> str:
    """Remove Markdown code fences from a model-generated text field."""

    return MARKDOWN_FENCE_RE.sub("", text).strip()


def normalize_whitespace_text(text: str) -> str:
    """Collapse repeated whitespace and trim a text field."""

    return WHITESPACE_RE.sub(" ", text).strip()


def normalize_unicode_text(text: str) -> str:
    """Apply NFC Unicode normalization."""

    return unicodedata.normalize("NFC", text)


def _is_code_mixed_case(case: dict[str, Any]) -> bool:
    code_mix = case.get("code_mix")
    primary = code_mix.get("primary_language") if isinstance(code_mix, dict) else None
    return case.get("language") == "mix" or primary == "mix"


def _should_lowercase_romanized(text: str, is_code_mixed_case: bool) -> bool:
    if not is_code_mixed_case:
        return False
    return bool(LATIN_RE.search(text)) and not bool(INDIC_SCRIPT_RE.search(text))


def _normalize_text(text: str, config: PreprocessingConfig, is_code_mixed_case: bool) -> str:
    normalized = text
    if config.strip_markdown:
        normalized = strip_markdown_fences(normalized)
    if config.normalize_whitespace:
        normalized = normalize_whitespace_text(normalized)
    if config.normalize_unicode:
        normalized = normalize_unicode_text(normalized)
    if _should_lowercase_romanized(normalized, is_code_mixed_case):
        normalized = normalized.lower()
    return normalized


def _normalize_nested_string(
    case: dict[str, Any],
    path: tuple[str, ...],
    config: PreprocessingConfig,
    is_code_mixed_case: bool,
) -> None:
    current: Any = case
    for key in path[:-1]:
        if not isinstance(current, dict):
            return
        current = current.get(key)
    if not isinstance(current, dict):
        return

    final_key = path[-1]
    value = current.get(final_key)
    if isinstance(value, str):
        current[final_key] = _normalize_text(value, config, is_code_mixed_case)


def normalize_case(case: dict[str, Any], config: PreprocessingConfig) -> dict[str, Any]:
    """Normalize selected benchmark fields without mutating the input case."""

    normalized = deepcopy(case)
    is_code_mixed_case = _is_code_mixed_case(normalized)

    for path in (
        ("input", "patient_query"),
        ("gold_label", "action"),
        ("gold_label", "reasoning"),
        ("unsafe_answer",),
    ):
        _normalize_nested_string(normalized, path, config, is_code_mixed_case)

    acceptable_range = normalized.get("acceptable_range")
    if isinstance(acceptable_range, list):
        normalized["acceptable_range"] = [
            _normalize_text(item, config, is_code_mixed_case) if isinstance(item, str) else item
            for item in acceptable_range
        ]

    return normalized
