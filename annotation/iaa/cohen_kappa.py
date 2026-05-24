# pranik/annotation/iaa/cohen_kappa.py
# Status: draft
# Clinical Reviewer Required: yes - this is the clinical review system
# TODO: Calibrate agreement gates with the first clinician-reviewed batch.
"""Inter-annotator agreement helpers for Label Studio exports."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from sklearn.metrics import cohen_kappa_score

# TODO(tier4): add arbitration workflow for kappa < 0.60 cases
# TODO(audit): export full annotation audit trail for ICMR compliance
# TODO(credits): integrate NMC CME credit tracking for annotators
# FUTURE: replace manual Label Studio with automated annotation API


def cohen_kappa(labels_a: Sequence[str], labels_b: Sequence[str]) -> float:
    """Compute Cohen's kappa for two equal-length label sequences."""
    if len(labels_a) != len(labels_b):
        raise ValueError("label sequences must have the same length")
    if not labels_a:
        raise ValueError("label sequences must not be empty")

    total = len(labels_a)
    observed = sum(a == b for a, b in zip(labels_a, labels_b, strict=True)) / total
    label_set = set(labels_a) | set(labels_b)
    expected = sum(
        (labels_a.count(label) / total) * (labels_b.count(label) / total) for label in label_set
    )
    if expected == 1.0:
        return 1.0
    return (observed - expected) / (1 - expected)


def compute_iaa(annotations: list[dict[str, Any]], task: str) -> dict[str, Any]:
    """Compute Cohen's kappa for completed Label Studio task exports.

    Label Studio project exports are expected: each item is a task containing
    ``data.case_id`` and an ``annotations`` list with reviewer results.
    """

    grouped = _group_completed_tasks_by_case(annotations)
    label_pairs: dict[str, tuple[list[str], list[str]]] = {
        "urgency": ([], []),
        "escalation": ([], []),
        "clinical_correctness": ([], []),
        "safety_risk": ([], []),
    }
    tier4_case_ids: list[str] = []
    review_case_ids: list[str] = []
    paired_case_ids: list[str] = []

    for case_id, tasks in grouped.items():
        task_annotations = _task_annotations(tasks)
        if len(task_annotations) < 2:
            continue

        first, second = task_annotations[0], task_annotations[1]
        case_metrics: list[float] = []
        for metric_name, from_name in _metric_fields(task):
            first_label = extract_label_value(first, from_name)
            second_label = extract_label_value(second, from_name)
            if first_label is None or second_label is None:
                continue
            label_pairs[metric_name][0].append(str(first_label))
            label_pairs[metric_name][1].append(str(second_label))
            case_metrics.append(1.0 if first_label == second_label else 0.0)

        if case_metrics:
            paired_case_ids.append(case_id)
            case_agreement = sum(case_metrics) / len(case_metrics)
            if case_agreement < 0.60:
                tier4_case_ids.append(case_id)
            elif case_agreement < 0.70:
                review_case_ids.append(case_id)

    kappas: dict[str, float] = {}
    for metric_name, (labels_a, labels_b) in label_pairs.items():
        if labels_a and labels_b:
            kappas[f"{metric_name}_kappa"] = _safe_cohen_kappa(labels_a, labels_b)

    overall_values = list(kappas.values())
    overall_kappa = sum(overall_values) / len(overall_values) if overall_values else 0.0
    meets_gate = bool(overall_values) and all(value > 0.70 for value in overall_values)
    requires_tier4 = any(value < 0.60 for value in overall_values) or bool(tier4_case_ids)

    return {
        **kappas,
        "overall_kappa": overall_kappa,
        "meets_gate": meets_gate,
        "requires_tier4": requires_tier4,
        "paired_case_count": len(set(paired_case_ids)),
        "tier4_case_ids": sorted(set(tier4_case_ids)),
        "review_case_ids": sorted(set(review_case_ids)),
    }


def extract_case_id(task: dict[str, Any]) -> str | None:
    """Extract a case id from a Label Studio task/export object."""

    data = task.get("data")
    if isinstance(data, dict) and isinstance(data.get("case_id"), str):
        return data["case_id"]

    meta = task.get("meta")
    if isinstance(meta, dict) and isinstance(meta.get("case_id"), str):
        return meta["case_id"]

    case_id = task.get("case_id")
    return case_id if isinstance(case_id, str) else None


def extract_label_value(annotation: dict[str, Any], from_name: str) -> str | None:
    """Extract a scalar reviewer value from one Label Studio annotation."""

    results = annotation.get("result")
    if not isinstance(results, list):
        return None

    for result in results:
        if not isinstance(result, dict) or result.get("from_name") != from_name:
            continue
        value = result.get("value")
        if not isinstance(value, dict):
            continue
        choices = value.get("choices")
        if isinstance(choices, list) and choices:
            return str(choices[0])
        text = value.get("text")
        if isinstance(text, list) and text:
            return str(text[0])
        if isinstance(text, str):
            return text
    return None


def _group_completed_tasks_by_case(
    exported_tasks: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for exported_task in exported_tasks:
        case_id = extract_case_id(exported_task)
        if case_id is not None:
            grouped[case_id].append(exported_task)
    return grouped


def _task_annotations(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    task_annotations: list[dict[str, Any]] = []
    for task in tasks:
        annotations = task.get("annotations")
        if isinstance(annotations, list):
            task_annotations.extend(
                annotation for annotation in annotations if isinstance(annotation, dict)
            )
    return sorted(
        task_annotations,
        key=lambda item: str(item.get("id") or item.get("created_at") or ""),
    )


def _metric_fields(task: str) -> list[tuple[str, str]]:
    if task == "triage":
        return [("urgency", "urgency"), ("escalation", "escalation_required")]
    if task == "escalation":
        return [("escalation", "escalation_required"), ("urgency", "escalation_level")]
    return [
        ("clinical_correctness", "clinical_correctness"),
        ("safety_risk", "safety_risk"),
    ]


def _safe_cohen_kappa(labels_a: Sequence[str], labels_b: Sequence[str]) -> float:
    """Compute Cohen's kappa while treating identical single-class batches as perfect."""

    if len(set(labels_a) | set(labels_b)) == 1:
        return 1.0 if list(labels_a) == list(labels_b) else 0.0
    return float(cohen_kappa_score(labels_a, labels_b))


if __name__ == "__main__":
    print(cohen_kappa(["urgent", "routine"], ["urgent", "routine"]))
