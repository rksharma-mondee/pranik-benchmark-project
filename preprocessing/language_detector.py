# pranik/preprocessing/language_detector.py
# Status: draft
# Clinical Reviewer Required: no
# DPDP 2025: this file is part of the compliance pipeline - do not skip
# TODO: Calibrate confidence behavior on clinician-reviewed Indic samples.
"""Language detection and validation for PRANIK benchmark cases."""

from __future__ import annotations

import re
from typing import Optional


# TODO(dedup): add MinHash LSH deduplication via Setu in Phase 3
# TODO(indic): replace langdetect with IndicLID for better Indic accuracy
# TODO(consent): add consent_verified field check before processing real data
# TODO(erasure): implement case deletion by case_id for DPDP erasure rights
# FUTURE: integrate Presidio with custom MedNER for clinical entity types


LANGDETECT_MAP = {
    "hi": "hi",
    "te": "te",
    "kn": "kn",
    "bn": "bn",
    "en": "en-IN",
}

DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
LATIN_RE = re.compile(r"[a-zA-Z]")


def _is_devanagari_latin_code_mix(text: str) -> bool:
    if not DEVANAGARI_RE.search(text) or not LATIN_RE.search(text):
        return False

    non_space_chars = [char for char in text if not char.isspace()]
    if not non_space_chars:
        return False

    latin_count = sum(1 for char in non_space_chars if LATIN_RE.fullmatch(char))
    return latin_count / len(non_space_chars) > 0.10


def detect_language(text: str, declared: Optional[str] = None) -> tuple[Optional[str], float]:
    """Detect a PRANIK language code from text.

    Very short strings cannot be reliably classified, so callers may pass the
    declared benchmark label as a safe fallback.
    """

    cleaned = (text or "").strip()
    if _is_devanagari_latin_code_mix(cleaned):
        return "mix", 1.0
    if len(cleaned) < 20:
        return declared, 0.0

    try:
        from langdetect import DetectorFactory, detect_langs
    except ImportError:
        return None, 0.0

    DetectorFactory.seed = 0
    try:
        detected_candidates = detect_langs(cleaned)
    except Exception:
        return None, 0.0

    if not detected_candidates:
        return None, 0.0

    best = detected_candidates[0]
    return LANGDETECT_MAP.get(best.lang, best.lang), float(best.prob)


def validate_language(
    detected: Optional[str],
    declared: Optional[str],
    confidence: float,
) -> tuple[bool, list[str]]:
    """Compare detected and declared labels.

    A mismatch is intentionally a warning, not a rejection. Language labels can
    be fixed during review without discarding the clinical case.
    """

    warnings: list[str] = []
    if detected is None:
        warnings.append("Language detection failed; manual language review required.")
        return False, warnings

    normalized_declared = "en-IN" if declared == "en" else declared
    normalized_detected = "en-IN" if detected == "en" else detected

    if normalized_detected == "mix":
        matches = normalized_declared == "mix"
    else:
        matches = normalized_detected == normalized_declared

    if not matches:
        warnings.append(
            "Language mismatch: "
            f"declared={normalized_declared}, detected={normalized_detected}, "
            f"confidence={confidence:.3f}."
        )
    return matches, warnings
