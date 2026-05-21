"""MedGemma model adapter scaffold."""

from __future__ import annotations


class MedGemmaAdapter:
    def generate(self, prompt: str) -> str:
        raise NotImplementedError("Connect MedGemma inference before production use.")

