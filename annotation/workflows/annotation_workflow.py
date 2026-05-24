# pranik/annotation/workflows/annotation_workflow.py
# Status: draft
# Clinical Reviewer Required: yes - this is the clinical review system
# TODO: Add resume/idempotency checks before running large annotation batches.
"""Orchestrate PRANIK Label Studio upload, export, IAA, and gold writing."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import structlog
from dotenv import load_dotenv

from annotation.configs.label_studio_config import get_label_config
from annotation.exporters.to_label_studio import benchmark_case_to_ls_task, load_draft_cases
from annotation.iaa.cohen_kappa import compute_iaa
from annotation.importers.from_label_studio import write_gold_cases

# TODO(tier4): add arbitration workflow for kappa < 0.60 cases
# TODO(audit): export full annotation audit trail for ICMR compliance
# TODO(credits): integrate NMC CME credit tracking for annotators
# FUTURE: replace manual Label Studio with automated annotation API


logger = structlog.get_logger(__name__)


def run_annotation_cycle(
    input_dir: Path,
    ls_url: str,
    ls_api_key: str,
    project_id: int,
    task_filter: str | None = None,
) -> dict[str, Any]:
    """Upload draft BenchmarkCase records into an existing Label Studio project."""

    cases = load_draft_cases(input_dir)
    if task_filter:
        cases = [case for case in cases if case.task == task_filter]
    tasks = [benchmark_case_to_ls_task(case) for case in cases]
    if tasks:
        _ls_import_tasks(ls_url=ls_url, ls_api_key=ls_api_key, project_id=project_id, tasks=tasks)

    logger.info(
        "label_studio_tasks_uploaded",
        uploaded=len(tasks),
        project_id=project_id,
        input_dir=str(input_dir),
        task_filter=task_filter,
    )
    return {"uploaded": len(tasks), "project_id": project_id, "task_filter": task_filter}


def import_completed_annotations(
    ls_url: str,
    ls_api_key: str,
    project_id: int,
    output_dir: Path,
) -> dict[str, Any]:
    """Export completed annotations, apply the IAA gate, and write approved gold cases."""

    exported_tasks = _ls_export_tasks(
        ls_url=ls_url,
        ls_api_key=ls_api_key,
        project_id=project_id,
    )
    completed = [
        task
        for task in exported_tasks
        if isinstance(task.get("annotations"), list) and len(task["annotations"]) >= 2
    ]
    pending = len(exported_tasks) - len(completed)

    approved_tasks: list[dict[str, Any]] = []
    flagged_tasks: list[dict[str, Any]] = []
    iaa_by_task: dict[str, dict[str, Any]] = {}
    for task_name in sorted({_task_name(task) for task in completed if _task_name(task)}):
        task_batch = [task for task in completed if _task_name(task) == task_name]
        iaa_report = compute_iaa(task_batch, task_name)
        iaa_by_task[task_name] = iaa_report
        tier4_ids = set(iaa_report["tier4_case_ids"])
        for task in task_batch:
            case_id = _case_id(task)
            if case_id in tier4_ids or iaa_report["requires_tier4"]:
                flagged_tasks.append(task)
            elif iaa_report["meets_gate"]:
                approved_tasks.append(task)

    write_counts = {}
    if approved_tasks:
        overall = _mean(
            report["overall_kappa"]
            for report in iaa_by_task.values()
            if report.get("meets_gate")
        )
        write_counts = write_gold_cases(approved_tasks, output_dir, iaa_score=overall)

    summary = {
        "project_id": project_id,
        "exported": len(exported_tasks),
        "completed": len(completed),
        "approved": len(approved_tasks),
        "flagged_for_tier4": len(flagged_tasks),
        "pending": pending,
        "gold_write_counts": write_counts,
        "iaa": iaa_by_task,
    }
    logger.info("label_studio_annotation_import_complete", **summary)
    return summary


def verify_label_studio_connection(
    ls_url: str,
    ls_api_key: str,
    project_id: int | None = None,
) -> dict[str, Any]:
    """Verify Label Studio credentials and optionally fetch a project."""

    try:
        client = _v2_client(ls_url, ls_api_key)
        user = client.users.whoami()
        project = client.projects.get(id=project_id) if project_id is not None else None
        return {
            "status": "ok",
            "sdk": "v2",
            "username": getattr(user, "username", None),
            "email": getattr(user, "email", None),
            "project_id": getattr(project, "id", project_id),
            "project_title": getattr(project, "title", None),
        }
    except Exception:
        try:
            client = _legacy_client(ls_url, ls_api_key)
            project = client.get_project(project_id) if project_id is not None else None
            return {
                "status": "ok",
                "sdk": "legacy",
                "project_id": getattr(project, "id", project_id),
                "project_title": getattr(project, "title", None),
            }
        except Exception as legacy_exc:
            raise RuntimeError(
                "Unable to connect to Label Studio with SDK v2 or legacy client"
            ) from legacy_exc


def create_label_studio_project(
    ls_url: str,
    ls_api_key: str,
    *,
    title: str,
    task: str,
    env_path: Path = Path(".env"),
) -> dict[str, Any]:
    """Create a Label Studio project and persist its ID into the local env file."""

    client = _v2_client(ls_url, ls_api_key)
    project = client.projects.create(
        title=title,
        description=(
            "PRANIK clinician review project. Requires 2+ reviewer annotations "
            "for Cohen's kappa IAA before gold dataset approval."
        ),
        label_config=get_label_config(task),
        show_instruction=True,
        expert_instruction=(
            "Review the patient query and AI pre-label. Use clinical judgment, "
            "prioritize patient safety, and document reasoning in reviewer notes."
        ),
    )
    project_id = int(project.id)
    _upsert_env_value(env_path, "LABEL_STUDIO_PROJECT_ID", str(project_id))
    logger.info(
        "label_studio_project_created",
        project_id=project_id,
        title=title,
        task=task,
        env_path=str(env_path),
    )
    return {
        "created": True,
        "project_id": project_id,
        "project_title": getattr(project, "title", title),
        "task": task,
        "env_path": str(env_path),
    }


def _ls_import_tasks(
    *,
    ls_url: str,
    ls_api_key: str,
    project_id: int,
    tasks: list[dict[str, Any]],
) -> None:
    try:
        client = _v2_client(ls_url, ls_api_key)
        client.projects.import_tasks(
            id=project_id,
            request=tasks,
            return_task_ids=True,
        )
    except (ImportError, AttributeError):
        client = _legacy_client(ls_url, ls_api_key)
        project = client.get_project(project_id)
        project.import_tasks(tasks)


def _ls_export_tasks(*, ls_url: str, ls_api_key: str, project_id: int) -> list[dict[str, Any]]:
    try:
        client = _v2_client(ls_url, ls_api_key)
        exported = client.projects.exports.as_json(project_id=project_id)
        return exported if isinstance(exported, list) else list(exported)
    except (ImportError, AttributeError):
        try:
            return _http_export_tasks(ls_url=ls_url, ls_api_key=ls_api_key, project_id=project_id)
        except RuntimeError:
            pass

        client = _legacy_client(ls_url, ls_api_key)
        project = client.get_project(project_id)
        exported = project.export_tasks()
        return exported if isinstance(exported, list) else list(exported)


def _v2_client(ls_url: str, ls_api_key: str) -> Any:
    try:
        from label_studio_sdk import LabelStudio
    except ImportError as exc:
        raise ImportError("label-studio-sdk>=2 is required for the v2 client") from exc

    client = LabelStudio(base_url=_normalize_url(ls_url), api_key=ls_api_key, timeout=20)
    client.users.whoami()
    return client


def _http_export_tasks(*, ls_url: str, ls_api_key: str, project_id: int) -> list[dict[str, Any]]:
    query = urlencode({"exportType": "JSON", "download_all_tasks": "true"})
    url = f"{_normalize_url(ls_url)}/api/projects/{project_id}/export?{query}"
    last_error: Exception | None = None
    for scheme in ("Bearer", "Token"):
        request = Request(
            url,
            headers={
                "Authorization": f"{scheme} {ls_api_key}",
                "Content-Type": "application/json",
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
                if not isinstance(payload, list):
                    raise RuntimeError("Label Studio export did not return a JSON task list")
                return payload
        except HTTPError as exc:
            last_error = exc
            if exc.code not in {401, 403}:
                break
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            break
    raise RuntimeError(f"Label Studio export failed: {last_error}") from last_error


def _legacy_client(ls_url: str, ls_api_key: str) -> Any:
    try:
        from label_studio_sdk import Client
    except ImportError as exc:
        raise RuntimeError(
            "label-studio-sdk is required. Install with: pip install label-studio-sdk"
        ) from exc

    client = Client(url=_normalize_url(ls_url), api_key=ls_api_key)
    client.check_connection()
    return client


def _normalize_url(ls_url: str) -> str:
    normalized = ls_url.rstrip("/")
    if not normalized.startswith(("http://", "https://")):
        raise ValueError("LABEL_STUDIO_URL must start with http:// or https://")
    return normalized


def _upsert_env_value(env_path: Path, key: str, value: str) -> None:
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    prefix = f"{key}="
    updated = False
    next_lines: list[str] = []
    for line in lines:
        if line.startswith(prefix):
            next_lines.append(f"{key}={value}")
            updated = True
        else:
            next_lines.append(line)
    if not updated:
        next_lines.append(f"{key}={value}")
    env_path.write_text("\n".join(next_lines) + "\n", encoding="utf-8")


def _task_name(task: dict[str, Any]) -> str:
    data = task.get("data")
    if isinstance(data, dict) and isinstance(data.get("task"), str):
        return data["task"]
    return ""


def _case_id(task: dict[str, Any]) -> str:
    data = task.get("data")
    if isinstance(data, dict) and isinstance(data.get("case_id"), str):
        return data["case_id"]
    meta = task.get("meta")
    if isinstance(meta, dict) and isinstance(meta.get("case_id"), str):
        return meta["case_id"]
    return ""


def _mean(values: Any) -> float:
    numeric = [float(value) for value in values]
    return sum(numeric) / len(numeric) if numeric else 0.0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run PRANIK Label Studio annotation workflow.")
    parser.add_argument("command", choices=["upload", "import", "verify", "create-project"])
    parser.add_argument("--input-dir", type=Path, default=Path("datasets/processed"))
    parser.add_argument("--output-dir", type=Path, default=Path("datasets/gold"))
    parser.add_argument("--ls-url", default=None)
    parser.add_argument("--ls-api-key", default=None)
    parser.add_argument("--project-id", type=int, default=None)
    parser.add_argument("--title", default="PRANIK Triage Review")
    parser.add_argument("--task", default="triage")
    parser.add_argument("--env-path", type=Path, default=Path(".env"))
    return parser.parse_args()


def _env_or_arg(value: str | None, env_name: str) -> str:
    resolved = value or os.getenv(env_name)
    if not resolved:
        raise RuntimeError(f"Missing {env_name}")
    return resolved


def _project_id(value: int | None) -> int:
    if value is not None:
        return value
    raw = os.getenv("LABEL_STUDIO_PROJECT_ID")
    if not raw:
        raise RuntimeError("Missing LABEL_STUDIO_PROJECT_ID")
    return int(raw)


def _optional_project_id(value: int | None) -> int | None:
    if value is not None:
        return value
    raw = os.getenv("LABEL_STUDIO_PROJECT_ID")
    return int(raw) if raw else None


if __name__ == "__main__":
    load_dotenv()
    args = _parse_args()
    url = _env_or_arg(args.ls_url, "LABEL_STUDIO_URL")
    api_key = _env_or_arg(args.ls_api_key, "LABEL_STUDIO_API_KEY")
    if args.command == "upload":
        project = _project_id(args.project_id)
        task_filter = None if args.task == "all" else args.task
        print(run_annotation_cycle(args.input_dir, url, api_key, project, task_filter))
    elif args.command == "import":
        project = _project_id(args.project_id)
        print(import_completed_annotations(url, api_key, project, args.output_dir))
    elif args.command == "create-project":
        print(
            create_label_studio_project(
                url,
                api_key,
                title=args.title,
                task=args.task,
                env_path=args.env_path,
            )
        )
    else:
        print(verify_label_studio_connection(url, api_key, _optional_project_id(args.project_id)))
