import jsonlines

from annotation.workflows import annotation_workflow


def test_finalize_gold_batch_writes_only_consensus_cases(tmp_path, monkeypatch) -> None:
    gold_dir = tmp_path / "gold"
    agreed = _ls_task(_triage_case("case-agreed"), "EMERGENCY", "yes", "EMERGENCY", "yes")
    disputed = _ls_task(_triage_case("case-disputed"), "URGENT", "yes", "EMERGENCY", "yes")
    existing = _ls_task(_triage_case("case-existing"), "ROUTINE", "no", "ROUTINE", "no")

    gold_dir.mkdir()
    with jsonlines.open(gold_dir / "triage_gold_v1.jsonl", mode="w") as writer:
        writer.write(existing["meta"]["source_case"])

    monkeypatch.setattr(
        annotation_workflow,
        "_ls_export_tasks",
        lambda **_kwargs: [agreed, disputed, existing],
    )

    summary = annotation_workflow.finalize_gold_batch(
        "http://localhost:8080",
        "test-key",
        2,
        gold_dir,
    )
    rerun_summary = annotation_workflow.finalize_gold_batch(
        "http://localhost:8080",
        "test-key",
        2,
        gold_dir,
    )

    assert summary["finalized"] == 1
    assert summary["skipped_existing_gold"] == 1
    assert summary["skipped_disagreement"] == 1
    assert rerun_summary["finalized"] == 0

    with jsonlines.open(gold_dir / "triage_gold_v1.jsonl", mode="r") as reader:
        cases = list(reader)
    assert {case["case_id"] for case in cases} == {"case-agreed", "case-existing"}
    assert cases[-1]["annotation"]["validation_status"] == "approved"
    assert cases[-1]["annotation"]["iaa_score"] == 1.0


def test_import_completed_annotations_skips_existing_gold(tmp_path, monkeypatch) -> None:
    gold_dir = tmp_path / "gold"
    gold_dir.mkdir()
    existing_case = _triage_case("case-existing")
    with jsonlines.open(gold_dir / "triage_gold_v1.jsonl", mode="w") as writer:
        writer.write(existing_case)

    existing_disputed = _ls_task(existing_case, "URGENT", "yes", "EMERGENCY", "yes")
    new_disputed = _ls_task(_triage_case("case-new"), "URGENT", "yes", "EMERGENCY", "yes")
    exported_queues = []

    monkeypatch.setattr(
        annotation_workflow,
        "_ls_export_tasks",
        lambda **_kwargs: [existing_disputed, new_disputed],
    )

    def _capture_queue(tasks, output_dir, *, reason):
        exported_queues.append((tasks, output_dir, reason))
        return {"written": len(tasks), "output_path": "queue.jsonl"}

    monkeypatch.setattr(annotation_workflow, "export_tier4_arbitration_queue", _capture_queue)

    summary = annotation_workflow.import_completed_annotations(
        "http://localhost:8080",
        "test-key",
        2,
        gold_dir,
    )

    assert summary["skipped_existing_gold"] == 1
    assert summary["flagged_for_tier4"] == 1
    assert [annotation_workflow._case_id(task) for task in exported_queues[0][0]] == ["case-new"]


def _ls_task(
    source_case: dict,
    reviewer1_urgency: str,
    reviewer1_escalation: str,
    reviewer2_urgency: str,
    reviewer2_escalation: str,
) -> dict:
    return {
        "data": {
            "case_id": source_case["case_id"],
            "task": "triage",
            "language": "en-IN",
            "patient_query": source_case["input"]["patient_query"],
        },
        "meta": {
            "case_id": source_case["case_id"],
            "tier_required": 3,
            "source_case": source_case,
        },
        "annotations": [
            _annotation(1, reviewer1_urgency, reviewer1_escalation),
            _annotation(2, reviewer2_urgency, reviewer2_escalation),
        ],
    }


def _annotation(annotation_id: int, urgency: str, escalation_required: str) -> dict:
    return {
        "id": annotation_id,
        "result": [
            {
                "from_name": "urgency",
                "value": {"choices": [urgency]},
            },
            {
                "from_name": "escalation_required",
                "value": {"choices": [escalation_required]},
            },
            {
                "from_name": "notes",
                "value": {"text": ["Reviewer consensus note."]},
            },
        ],
    }


def _triage_case(case_id: str) -> dict:
    return {
        "case_id": case_id,
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
            "reasoning": "Draft label before clinician review.",
            "reviewer_todo": "Needs clinical review.",
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
