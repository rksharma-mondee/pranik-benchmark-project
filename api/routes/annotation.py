# api/routes/annotation.py
# Status: draft
# Clinical Reviewer Required: no
# TODO: replace local Label Studio token lookup with dashboard service credentials
"""Annotation workflow status endpoint for the dashboard."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import APIRouter

from annotation.workflows.annotation_workflow import get_annotation_status

router = APIRouter()


@router.get("/status")
def get_dashboard_annotation_status() -> dict[str, Any]:
    """Return Label Studio annotation status when local credentials are configured."""

    load_dotenv()
    url = os.getenv("LABEL_STUDIO_URL")
    api_key = os.getenv("LABEL_STUDIO_API_KEY")
    project_id = os.getenv("LABEL_STUDIO_PROJECT_ID")
    if not url or not api_key or not project_id:
        return {
            "available": False,
            "error": "Label Studio environment variables are not configured.",
            "gold_cases_total": _gold_case_count(),
        }
    try:
        status = get_annotation_status(url, api_key, int(project_id), Path("datasets/gold"))
    except Exception as exc:
        return {
            "available": False,
            "error": str(exc),
            "gold_cases_total": _gold_case_count(),
        }
    return {"available": True, **status}


def _gold_case_count() -> int:
    total = 0
    gold_dir = Path("datasets/gold")
    if not gold_dir.exists():
        return total
    for path in gold_dir.glob("*_gold_v1.jsonl"):
        with path.open("r", encoding="utf-8") as file:
            total += sum(1 for line in file if line.strip())
    return total

