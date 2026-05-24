from annotation.iaa.cohen_kappa import cohen_kappa, compute_iaa


def test_cohen_kappa_perfect_agreement() -> None:
    assert cohen_kappa(["a", "b", "a"], ["a", "b", "a"]) == 1.0


def test_compute_iaa_accepts_two_label_studio_annotations() -> None:
    export = [
        {
            "data": {"case_id": "case-1", "task": "triage"},
            "annotations": [
                {
                    "id": 1,
                    "result": [
                        {"from_name": "urgency", "value": {"choices": ["EMERGENCY"]}},
                        {"from_name": "escalation_required", "value": {"choices": ["yes"]}},
                    ],
                },
                {
                    "id": 2,
                    "result": [
                        {"from_name": "urgency", "value": {"choices": ["EMERGENCY"]}},
                        {"from_name": "escalation_required", "value": {"choices": ["yes"]}},
                    ],
                },
            ],
        }
    ]

    report = compute_iaa(export, task="triage")

    assert report["meets_gate"] is True
    assert report["overall_kappa"] == 1.0
    assert report["paired_case_count"] == 1
