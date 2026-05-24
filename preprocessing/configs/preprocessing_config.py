# pranik/preprocessing/preprocessing_config.py
# Status: draft
# Clinical Reviewer Required: no
# DPDP 2025: this file is part of the compliance pipeline - do not skip
# TODO: Confirm production thresholds with legal and clinical governance.
"""Configuration for PRANIK benchmark preprocessing."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


# TODO(dedup): add MinHash LSH deduplication via Setu in Phase 3
# TODO(indic): replace langdetect with IndicLID for better Indic accuracy
# TODO(consent): add consent_verified field check before processing real data
# TODO(erasure): implement case deletion by case_id for DPDP erasure rights
# FUTURE: integrate Presidio with custom MedNER for clinical entity types


@dataclass
class PreprocessingConfig:
    """Runtime switches and paths for the preprocessing gate."""

    # PII settings
    pii_enabled: bool = True
    pii_score_threshold: float = 0.6
    fail_on_pii_detection: bool = False

    # Language validation
    language_validation_enabled: bool = True
    allowed_languages: list[str] = field(
        default_factory=lambda: ["hi", "te", "kn", "bn", "en", "en-IN", "mix"]
    )

    # Normalization
    strip_markdown: bool = True
    normalize_whitespace: bool = True
    normalize_unicode: bool = True

    # Output
    input_dir: Path = Path("datasets/synthetic")
    output_dir: Path = Path("datasets/processed")
    rejected_dir: Path = Path("datasets/rejected")

    # Audit
    save_audit_log: bool = True
    audit_log_path: Path = Path("datasets/audit/pii_audit_log.jsonl")
