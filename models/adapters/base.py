# pranik/models/adapters/base.py
# Status: draft
# Clinical Reviewer Required: no
# TODO: Register concrete adapters in models/adapters/__init__.py once model selection is finalized.
"""Base interfaces for PRANIK model adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AdapterConfig:
    """Configuration shared by all model adapters.

    Attributes:
        model_id: Provider-specific model identifier.
        temperature: Sampling temperature; defaults to deterministic output.
        max_tokens: Maximum output tokens requested from the model.
        timeout_seconds: Request timeout in seconds.
    """

    model_id: str
    temperature: float = 0.0
    max_tokens: int = 1024
    timeout_seconds: int = 30


class ModelAdapter(ABC):
    """Base class for all model adapters.

    To add a new model: subclass this, implement generate().
    Register in models/adapters/__init__.py adapter registry.
    """

    def __init__(self, config: AdapterConfig) -> None:
        """Initialize the adapter with provider configuration.

        Args:
            config: Shared adapter configuration.
        """
        self.config = config

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Send prompt and return raw string response.

        Args:
            prompt: Final prompt string to send to the model.

        Returns:
            Raw model response text.

        Raises:
            Exception: Provider-specific exception on generation failure.
        """
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Verify model is reachable before evaluation run starts.

        Returns:
            True when the adapter is ready for generation.
        """
        ...


# TODO(batch): replace single-case loop with batch inference in Phase 3
# TODO(safety): pipe EvaluationResult through safety/pipeline.py after scoring
# TODO(metrics): add task-specific scorer after raw outputs are stable
# FUTURE: replace file-based output with DVC-tracked dataset in Phase 4
