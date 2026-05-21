"""Llama model adapter scaffold."""

from __future__ import annotations


class LlamaAdapter:
    def generate(self, prompt: str) -> str:
        raise NotImplementedError("Connect Llama inference before production use.")

