# pranik/deployment/run_regression.py
# Status: draft
# Clinical Reviewer Required: no
# TODO: expose config overrides via CLI flags before CI/CD use.
"""Manual entrypoint for the PRANIK regression pipeline."""

from __future__ import annotations

import sys

from deployment.pipeline_config import PipelineConfig
from deployment.regression_pipeline import run_regression_pipeline

# TODO(schedule): add Windows Task Scheduler / cron trigger in Phase 4
# TODO(notify): add Slack webhook on critical regression alert
# TODO(dvc): commit new dataset version after successful pipeline run
# TODO(labelstudio): push fatal_miss cases to Label Studio review queue
# FUTURE: replace manual trigger with GitHub Actions monthly schedule


if __name__ == "__main__":
    config = PipelineConfig(
        model_ids=[
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "gemma2-9b-it",
            "mixtral-8x7b-32768",
        ],
        tasks=["triage", "escalation"],
        run_preprocessing=False,
        block_on_fatal_miss=True,
    )
    result = run_regression_pipeline(config)

    if result.status == "failed":
        sys.exit(1)
