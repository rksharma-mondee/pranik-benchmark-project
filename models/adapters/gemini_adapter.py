"""Gemini model adapter scaffold."""

from __future__ import annotations


class GeminiAdapter:
    def generate(self, prompt: str) -> str:
        raise NotImplementedError("Connect Gemini client before production use.")

