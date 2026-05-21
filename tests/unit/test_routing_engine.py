from evaluation.routing.routing_engine import route_case


def test_route_case_flags_review_terms() -> None:
    decision = route_case("Patient has chest pain")
    assert decision.requires_human_review is True
    assert "chest pain" in decision.reasons

