# Dataset Card

## Intended Use

This benchmark is intended to evaluate medical AI behavior across multilingual Indian healthcare scenarios, including safety, escalation, refusal, extraction, and simplification tasks.

## Data Sources

- Native examples
- Synthetic examples
- Translated examples
- ASR-derived examples

Do not include patient-identifiable data without documented consent, de-identification, and approval.

## Splits

- `raw/` - source data before cleaning
- `interim/` - temporary transformation outputs
- `processed/` - normalized evaluation-ready data
- `gold/` - versioned adjudicated benchmark sets
- `holdout/` - restricted final evaluation data

## Governance

Every gold release must document source mix, annotation protocol, reviewer roles, IAA, known limitations, and release approver.

