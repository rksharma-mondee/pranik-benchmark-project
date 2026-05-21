"""Qwen model adapter scaffold."""

from __future__ import annotations


class QwenAdapter:
    def generate(self, prompt: str) -> str:
        raise NotImplementedError("Connect Qwen inference before production use.")

