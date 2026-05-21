from annotation.iaa.cohen_kappa import cohen_kappa


def test_cohen_kappa_perfect_agreement() -> None:
    assert cohen_kappa(["a", "b", "a"], ["a", "b", "a"]) == 1.0

