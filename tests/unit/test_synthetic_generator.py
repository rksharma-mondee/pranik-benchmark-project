from synthetic_generation.generator import _make_case_id


def test_make_case_id_includes_run_id() -> None:
    assert _make_case_id("doctor_note_summary", "en-IN", 7, "20260525220000") == (
        "doctor-note-summary-enin-20260525220000-syn-007"
    )
