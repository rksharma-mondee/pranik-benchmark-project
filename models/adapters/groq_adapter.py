# pranik/models/adapters/groq_adapter.py
# Status: draft
# Clinical Reviewer Required: no
# TODO: Validate selected Groq model IDs and JSON reliability before production eval runs.
"""Groq adapter for PRANIK local evaluation."""

from __future__ import annotations

import os

import structlog
from dotenv import load_dotenv
from groq import APIConnectionError, InternalServerError, RateLimitError
from groq import Groq
from tenacity import RetryCallState
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from models.adapters.base import AdapterConfig, ModelAdapter


logger = structlog.get_logger(__name__)


def _log_attempt(retry_state: RetryCallState) -> None:
    """Log each Groq generation attempt.

    Args:
        retry_state: Tenacity retry state for the current call.
    """
    adapter = retry_state.args[0]
    logger.info(
        "groq_generate_attempt",
        model_id=adapter.model_id,
        attempt_number=retry_state.attempt_number,
    )


class GroqAdapter(ModelAdapter):
    """Model adapter backed by the official Groq Python SDK."""

    def __init__(self, config: AdapterConfig) -> None:
        """Initialize Groq client from environment configuration.

        Args:
            config: Adapter runtime configuration.

        Raises:
            RuntimeError: If GROQ_API_KEY is not configured.
        """
        super().__init__(config)
        load_dotenv()
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is required for GroqAdapter")

        self.model_id = self._normalize_model_id(config.model_id)
        self._client = Groq(api_key=api_key, timeout=config.timeout_seconds)

    @staticmethod
    def _normalize_model_id(model_id: str) -> str:
        """Strip PRANIK provider prefix from Groq model IDs.

        Args:
            model_id: Raw configured model identifier.

        Returns:
            Provider-native Groq model ID.
        """
        return model_id.removeprefix("groq:")

    @retry(
        retry=retry_if_exception_type((APIConnectionError, InternalServerError, RateLimitError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        before=_log_attempt,
        reraise=True,
    )
    def generate(self, prompt: str) -> str:
        """Send prompt to Groq and return raw response text.

        Args:
            prompt: Final prompt string to send to Groq.

        Returns:
            Raw model response text.
        """
        completion = self._client.chat.completions.create(
            model=self.model_id,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            response_format={"type": "json_object"},
        )
        content = completion.choices[0].message.content
        return content or ""

    def health_check(self) -> bool:
        """Verify Groq is reachable before running evaluation.

        Returns:
            True when a minimal Groq request succeeds, otherwise False.
        """
        try:
            response = self.generate(
                'Return only valid JSON for this health check: {"ok": true}'
            )
            return bool(response)
        except Exception as exc:
            logger.error(
                "groq_health_check_failed",
                model_id=self.model_id,
                error=str(exc),
            )
            return False


# TODO(batch): replace single-case loop with batch inference in Phase 3
# TODO(safety): pipe EvaluationResult through safety/pipeline.py after scoring
# TODO(metrics): add task-specific scorer after raw outputs are stable
# FUTURE: replace file-based output with DVC-tracked dataset in Phase 4
