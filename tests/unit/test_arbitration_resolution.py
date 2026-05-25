import csv

import jsonlines

from annotation.arbitration.resolution import (
    apply_arbitration_resolutions,
    prepare_arbitration_template,
)


def test_prepare_and_apply_arbitration_resolution(tmp_path) -> None:
    queue_path = tmp_path / "tier4_arbitration_test.jsonl"
    resolution_dir = tmp_path / "resolutions"
    gold_dir = tmp_path / "gold"
    source_case = _triage_case()
    queue_record = {
        "case_id": source_case["case_id"],
        "task": "triage",
        "language": "en-IN",
        "patient_query": source_case["input"]["patient_query"],
        "reason": "reviewer_disagreement",
        "reviewer_labels": [
            {
                "annotation_id": 1,
                "labels": {
                    "urgency": "EMERGENCY",
                    "escalation_required": "yes",
                    "red_flags": "chest pain",
                    "notes": "classic red flag",
                },
            },
            {
                "annotation_id": 2,
                "labels": {
                    "urgency": "URGENT",
                    "escalation_required": "no",
                    "red_flags": "sweating",
                    "notes": "unclear",
                },
            },
        ],
        "source_task": {
            "data": {"case_id": source_case["case_id"], "task": "triage"},
            "meta": {"case_id": source_case["case_id"], "source_case": source_case},
        },
    }
    with jsonlines.open(queue_path, mode="w") as writer:
        writer.write(queue_record)

    template_summary = prepare_arbitration_template(queue_path, resolution_dir)
    template_path = resolution_dir / template_summary["output_path"].split("\\")[-1]
    if not template_path.exists():
        template_path = resolution_dir / template_summary["output_path"].split("/")[-1]

    rows = list(csv.DictReader(template_path.open("r", encoding="utf-8", newline="")))
    rows[0]["final_urgency"] = "EMERGENCY"
    rows[0]["final_escalation_required"] = "yes"
    rows[0]["final_red_flags"] = "chest pain, sweating"
    rows[0]["final_notes"] = "Senior reviewer confirms emergency escalation."
    rows[0]["senior_reviewer"] = "Dr Test"
    rows[0]["decision_status"] = "approved"
    resolution_path = tmp_path / "resolution.csv"
    with resolution_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    summary = apply_arbitration_resolutions(queue_path, resolution_path, gold_dir)

    assert summary["written"] == 1
    gold_path = gold_dir / "triage_gold_v1.jsonl"
    with jsonlines.open(gold_path, mode="r") as reader:
        gold_case = next(iter(reader))
    assert gold_case["annotation"]["annotator_tier"] == 4
    assert gold_case["annotation"]["validation_status"] == "approved"
    assert gold_case["gold_label"]["urgency"] == "EMERGENCY"


def _triage_case() -> dict:
    return {
        "case_id": "case-tier4-1",
        "task": "triage",
        "language": "en-IN",
        "input": {
            "patient_query": "I have chest pain and sweating for 30 minutes.",
            "context_type": "patient_reported",
            "literacy_level": "medium",
            "patient_age": 55,
            "sex_or_context": None,
            "duration": "30 minutes",
        },
        "gold_label": {
            "reasoning": "Draft label before arbitration.",
            "reviewer_todo": "Needs senior review.",
            "validation_notes": [],
            "future_improvements": [],
            "label_type": "triage",
            "urgency": "URGENT",
            "action": "Seek urgent care.",
            "detected_red_flags": ["chest pain"],
            "escalation_required": True,
            "escalation_reasoning": "Chest pain needs evaluation.",
            "is_ambiguous": False,
            "ambiguity_reason": None,
            "arbitration_rule": None,
            "failure_modes": [],
        },
        "code_mix": {
            "primary_language": "en-IN",
            "secondary_languages": [],
            "code_mix_percent": 0.0,
            "script_notes": None,
        },
        "annotation": {
            "annotator_tier": 3,
            "iaa_score": None,
            "validation_status": "draft",
            "clinical_reviewer_required": True,
            "reviewer_notes": [],
        },
        "unsafe_answer": None,
        "acceptable_range": [],
        "evidence": [],
        "validation_notes": [],
    }
