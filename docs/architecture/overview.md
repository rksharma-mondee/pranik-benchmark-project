# Architecture Overview

Pranik Benchmark separates datasets, task definitions, schemas, model adapters, safety checks, and evaluation pipelines so each part can evolve independently.

## Core Flow

1. Ingest raw data into `datasets/raw/`.
2. Normalize and validate into `datasets/processed/`.
3. Review and adjudicate gold labels under `datasets/gold/`.
4. Run model adapters through evaluation pipelines.
5. Apply safety checks and thresholds.
6. Publish scorecards and release reports.

