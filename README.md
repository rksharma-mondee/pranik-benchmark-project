# Pranik Benchmark

Production-grade benchmark scaffold for multilingual medical AI evaluation, safety checks, routing, and scorecard generation.

## Goals

- Maintain versioned gold datasets with clear provenance.
- Evaluate model behavior across triage, escalation, extraction, counseling, and safety tasks.
- Keep safety, privacy, and clinical escalation policies explicit and testable.
- Support reproducible local, staging, and production evaluation runs.

## Repository Layout

- `configs/` - environment, model, evaluation, and safety configuration.
- `datasets/` - raw, processed, gold, holdout, and metadata artifacts.
- `tasks/` - task definitions, schemas, metrics, guidelines, and examples.
- `schemas/` - shared annotation, gold label, and model output schemas.
- `annotation/` - reviewer policies, arbitration, inter-annotator agreement tooling.
- `evaluation/` - batch evaluation, regression evaluation, drift detection, routing.
- `safety/` - PII, refusal, escalation, hallucination, and audit checks.
- `models/` - model adapters, inference helpers, and routing integrations.
- `deployment/` - container, Kubernetes, Terraform, and release scripts.
- `docs/` - architecture, API, benchmark design, compliance, and decisions.
- `tests/` - unit, integration, evaluation, and safety tests.

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Run validation and tests:

```powershell
python -m pytest
python evaluation/pipelines/batch_eval.py --config configs/app/dev.yaml
```

## Production Notes

- Never commit patient data, secrets, raw clinical notes, or generated PII.
- Keep dataset releases under `datasets/gold/v*` immutable after publication.
- Add every benchmark change to `docs/decisions/` when it affects scoring, safety, or release criteria.
- Treat `datasets/holdout/` as restricted access. Do not use it for prompt tuning.

