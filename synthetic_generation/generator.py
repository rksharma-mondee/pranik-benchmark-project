# pranik/synthetic_generation/generator.py
# Status: draft
# Clinical Reviewer Required: yes - ALL synthetic cases need MD review before gold
# TODO(validation): add Giskard safety pre-scan before writing to output
# TODO(diversity): audit symptom distribution across cases quarterly
# TODO(clinician): route all synthetic cases to Label Studio review queue
# TODO(dedup): add MinHash deduplication before adding to benchmark pool
# FUTURE: replace Groq generator with MedGemma 4B self-hosted for clinical domain quality
"""Synthetic draft-case generator for PRANIK benchmark expansion."""

from __future__ import annotations

import argparse
import json
import random
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jsonlines
import structlog
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from models.adapters.base import AdapterConfig
from models.adapters.groq_adapter import GroqAdapter
from synthetic_generation.configs.generation_config import GenerationConfig
from synthetic_generation.templates.task_prompts import PATIENT_PROFILES, get_generation_prompt

logger = structlog.get_logger(__name__)


class GeneratedCase(BaseModel):
    """Raw output from generator before schema validation."""

    case_id: str
    task: str
    language: str
    raw_llm_output: str
    parsed_case: dict[str, Any] | None = None
    generation_success: bool
    validation_status: str = "draft"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    generator_model: str
    generation_prompt: str


def _parse_json_object(raw_response: str) -> dict[str, Any] | None:
    """Parse a raw LLM response into a JSON object."""
    stripped = raw_response.strip()
    try:
        parsed = json.loads(stripped)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, flags=re.DOTALL)
    if fenced:
        try:
            parsed = json.loads(fenced.group(1))
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass

    match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass

    return None


def _build_adapter(config: GenerationConfig) -> GroqAdapter:
    """Create the configured Groq adapter."""
    return GroqAdapter(
        AdapterConfig(
            model_id=config.model_id,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
    )


def _safe_task_name(task: str) -> str:
    """Create filesystem-safe task segment."""
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", task).strip("_")


def _output_path(config: GenerationConfig, timestamp: str) -> Path:
    """Build output path for one generation run."""
    task_name = _safe_task_name(config.tasks[0]) if len(config.tasks) == 1 else "mixed"
    return config.output_dir / f"synthetic_{task_name}_{timestamp}.jsonl"


def _make_case_id(task: str, language: str, counter: int) -> str:
    """Create stable synthetic case identifier."""
    safe_language = language.replace("-", "").lower()
    safe_task = task.replace("_", "-")
    return f"{safe_task}-{safe_language}-syn-{counter:03d}"


def _build_prompt(task: str, language: str, case_id: str, patient_profile: str) -> str:
    """Build one filled generation prompt."""
    return (
        get_generation_prompt(task, language)
        .replace("{case_id}", case_id)
        .replace("{patient_profile}", patient_profile)
    )


def generate_dataset(config: GenerationConfig) -> list[GeneratedCase]:
    """Generate synthetic draft cases and write them incrementally to JSONL."""
    load_dotenv()
    config.output_dir.mkdir(parents=True, exist_ok=True)
    adapter = None if config.dry_run else _build_adapter(config)

    if adapter is not None and not adapter.health_check():
        raise RuntimeError(f"Groq adapter health check failed for {config.model_id}")

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    output_path = _output_path(config, timestamp)
    results: list[GeneratedCase] = []
    successes = 0
    parse_failures = 0
    counter = 0

    with jsonlines.open(output_path, mode="w") as writer:
        for task in config.tasks:
            for language in config.languages:
                for _ in range(config.cases_per_task_per_language):
                    counter += 1
                    case_id = _make_case_id(task, language, counter)
                    patient_profile = random.choice(PATIENT_PROFILES)
                    prompt = _build_prompt(task, language, case_id, patient_profile)

                    if config.dry_run:
                        raw_output = ""
                        parsed_case = None
                        generation_success = True
                    else:
                        raw_output = adapter.generate(prompt) if adapter is not None else ""
                        parsed_case = _parse_json_object(raw_output)
                        generation_success = parsed_case is not None
                        if generation_success:
                            successes += 1
                        else:
                            parse_failures += 1

                    generated_case = GeneratedCase(
                        case_id=case_id,
                        task=task,
                        language=language,
                        raw_llm_output=raw_output,
                        parsed_case=parsed_case,
                        generation_success=generation_success,
                        generator_model=config.model_id,
                        generation_prompt=prompt,
                    )
                    results.append(generated_case)
                    writer.write(generated_case.model_dump(mode="json"))

                    logger.info(
                        "synthetic_case_generated",
                        case_id=case_id,
                        task=task,
                        language=language,
                        generation_success=generation_success,
                    )
                    if not config.dry_run:
                        time.sleep(0.5)

    logger.info(
        "synthetic_generation_summary",
        output_path=str(output_path),
        total=len(results),
        successes=successes if not config.dry_run else len(results),
        parse_failures=parse_failures,
        dry_run=config.dry_run,
    )
    return results


def _parse_args() -> argparse.Namespace:
    """Parse CLI flags."""
    defaults = GenerationConfig()
    parser = argparse.ArgumentParser(description="Generate synthetic PRANIK draft cases.")
    parser.add_argument("--dry-run", action="store_true", help="Generate prompts only.")
    parser.add_argument("--cases-per-combo", type=int, default=defaults.cases_per_task_per_language)
    parser.add_argument("--tasks", nargs="+", default=defaults.tasks)
    parser.add_argument("--languages", nargs="+", default=defaults.languages)
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    generation_config = GenerationConfig(
        cases_per_task_per_language=args.cases_per_combo,
        dry_run=args.dry_run,
        tasks=args.tasks,
        languages=args.languages,
    )
    generated = generate_dataset(generation_config)
    print(f"Generated: {len(generated)} cases")
