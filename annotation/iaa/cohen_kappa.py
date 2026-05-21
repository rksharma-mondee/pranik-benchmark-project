"""Inter-annotator agreement helpers."""

from __future__ import annotations

from collections.abc import Sequence


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


if __name__ == "__main__":
    print(cohen_kappa(["urgent", "routine"], ["urgent", "routine"]))

