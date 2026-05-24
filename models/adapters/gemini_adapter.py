# pranik/models/adapters/gemini_adapter.py
# Status: draft
# Clinical Reviewer Required: no
# TODO: Validate Gemini request settings and quota behavior in the target production account.
"""Gemini adapter for PRANIK local evaluation."""

from __future__ import annotations

import os

import google.generativeai as genai
import structlog
from dotenv import load_dotenv
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from tenacity import RetryCallState

from models.adapters.base import AdapterConfig, ModelAdapter


logger = structlog.get_logger(__name__)


def _log_attempt(retry_state: RetryCallState) -> None:
    """Log each Gemini generation attempt.

    Args:
        retry_state: Tenacity retry state for the current call.
    """
    adapter = retry_state.args[0]
    logger.info(
        "gemini_generate_attempt",
        model_id=adapter.config.model_id,
        attempt_number=retry_state.attempt_number,
    )


class GeminiAdapter(ModelAdapter):
    """Model adapter backed by the google-generativeai SDK."""

    def __init__(self, config: AdapterConfig) -> None:
        """Initialize Gemini client from environment configuration.

        Args:
            config: Adapter runtime configuration.

        Raises:
            RuntimeError: If GOOGLE_API_KEY is not configured.
        """
        super().__init__(config)
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY is required for GeminiAdapter")

        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(
            model_name=config.model_id,
            generation_config={
                "temperature": config.temperature,
                "max_output_tokens": config.max_tokens,
            },
        )

    @retry(
        retry=retry_if_exception_type((ServiceUnavailable, ResourceExhausted)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        before=_log_attempt,
        reraise=True,
    )
    def generate(self, prompt: str) -> str:
        """Send prompt to Gemini and return raw response text.

        Args:
            prompt: Final prompt string to send to Gemini.

        Returns:
            Raw model response text.
        """
        response = self._model.generate_content(prompt)
        return response.text

    def health_check(self) -> bool:
        """Verify Gemini is reachable before running evaluation.

        Returns:
            True when a minimal Gemini request succeeds, otherwise False.
        """
        try:
            response = self.generate('{"health_check": true}')
            return bool(response)
        except Exception as exc:
            logger.error(
                "gemini_health_check_failed",
                model_id=self.config.model_id,
                error=str(exc),
            )
            return False


# TODO(batch): replace single-case loop with batch inference in Phase 3
# TODO(safety): pipe EvaluationResult through safety/pipeline.py after scoring
# TODO(metrics): add task-specific scorer after raw outputs are stable
# FUTURE: replace file-based output with DVC-tracked dataset in Phase 4
