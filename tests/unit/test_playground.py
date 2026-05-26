from api.routes.playground import PlaygroundRequest, _build_playground_case, assess_safety


def test_assess_safety_marks_emergency_escalation_safe() -> None:
    report = assess_safety(
        {"urgency": "EMERGENCY", "escalation_required": True},
        "triage",
    )

    assert report["status"] == "CORRECT_ESCALATION"


def test_build_playground_case_supports_medication_task() -> None:
    case = _build_playground_case(
        PlaygroundRequest(
            patient_query="BP medicine kab leni hai?",
            task="medication_explanation",
            language="mix",
        )
    )

    assert case.task == "medication_explanation"
    assert case.gold_label.label_type == "medication_explanation"
