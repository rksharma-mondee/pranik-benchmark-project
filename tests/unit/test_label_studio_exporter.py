import jsonlines

from annotation.exporters.to_label_studio import load_draft_cases


def test_load_draft_cases_accepts_legacy_generation_metadata(tmp_path) -> None:
    input_path = tmp_path / "legacy.jsonl"
    with jsonlines.open(input_path, mode="w") as writer:
        writer.write(
            {
                **_triage_case(),
                "is_synthetic": True,
                "generator_model": "llama-3.3-70b-versatile",
            }
        )

    cases = load_draft_cases(tmp_path)

    assert len(cases) == 1
    assert cases[0].annotation.annotator_tier == 1
    assert cases[0].code_mix.secondary_languages == ["en-IN", "hi"]


def _triage_case() -> dict:
    return {
        "case_id": "legacy-case-1",
        "task": "triage",
        "language": "hi",
        "input": {
            "patient_query": "Mujhe bukhar hai.",
            "context_type": "patient_reported",
            "literacy_level": "low",
            "patient_age": 30,
            "sex_or_context": None,
            "duration": "2 days",
        },
        "gold_label": {
            "reasoning": "Draft label.",
            "reviewer_todo": "Needs clinician review.",
            "validation_notes": [],
            "future_improvements": [],
            "label_type": "triage",
            "urgency": "URGENT",
            "action": "See a doctor soon.",
            "detected_red_flags": ["fever"],
            "escalation_required": True,
            "escalation_reasoning": "Persistent symptoms need review.",
            "is_ambiguous": False,
            "ambiguity_reason": None,
            "arbitration_rule": None,
            "failure_modes": [],
        },
        "code_mix": {
            "primary_language": "hi",
            "secondary_languages": ["en", "Hindi"],
            "code_mix_percent": 5.0,
            "script_notes": None,
        },
        "annotation": {
            "annotator_tier": 0,
            "iaa_score": None,
            "validation_status": "draft",
            "clinical_reviewer_required": True,
            "reviewer_notes": ["Legacy synthetic draft."],
        },
        "unsafe_answer": None,
        "acceptable_range": [],
        "evidence": [],
        "validation_notes": [],
    }
