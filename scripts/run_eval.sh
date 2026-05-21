#!/usr/bin/env bash
set -euo pipefail

python evaluation/pipelines/batch_eval.py --config "${1:-configs/app/dev.yaml}"

