# pranik/schemas/gold_label/gold_schema_v1.py
# Status: review
# Clinical Reviewer Required: yes
# TODO: Confirm final enum coverage and escalation levels before production-ready schema freeze.
"""Pydantic v2 gold-label schema for PRANIK benchmark cases.

This module defines the canonical annotation-ready case format used by task specs,
JSONL benchmark files, and downstream evaluation pipelines.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TriageSeverity(str, Enum):
    """Exact triage severity labels used by the benchmark."""

    EMERGENCY = "EMERGENCY"
    URGENT = "URGENT"
    ROUTINE = "ROUTINE"
    SELF_CARE = "SELF_CARE"


class EscalationLevel(str, Enum):
    """Escalation levels used for safety routing evaluation."""

    NONE = "NONE"
    CLINICIAN = "CLINICIAN"
    URGENT = "URGENT"
    EMERGENCY = "EMERGENCY"
    CRISIS = "CRISIS"


class TriggerCategory(str, Enum):
    """Dominant escalation trigger category for audit and scoring."""

    NONE = "none"
    NEUROLOGIC_EMERGENCY = "neurologic_emergency"
    PREGNANCY_EMERGENCY = "pregnancy_emergency"
    CARDIAC_RED_FLAGS = "cardiac_red_flags"
    POISONING_OR_OVERDOSE = "poisoning_or_overdose"
    MENTAL_HEALTH_CRISIS = "mental_health_crisis"
    SEVERE_INFECTION = "severe_infection"
    MEDICATION_RISK = "medication_risk"
    OTHER_RED_FLAG = "other_red_flag"


class FalseNegativeRisk(str, Enum):
    """Risk severity if the model fails to escalate the case."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    FATAL = "FATAL"


class LanguageCode(str, Enum):
    """Supported benchmark language labels."""

    HI = "hi"
    TE = "te"
    KN = "kn"
    BN = "bn"
    EN_IN = "en-IN"
    MIX = "mix"


class ContextType(str, Enum):
    """Who generated or reported the medical query."""

    PATIENT_REPORTED = "patient_reported"
    FAMILY_REPORTED = "family_reported"
    PROVIDER_GENERATED = "provider_generated"


class LiteracyLevel(str, Enum):
    """Approximate health literacy level used for case stratification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ValidationStatus(str, Enum):
    """Lifecycle status for a benchmark case."""

    DRAFT = "draft"
    REVIEWED = "reviewed"
    APPROVED = "approved"


class GoldLabelBase(BaseModel):
    """Base class for all gold labels.

    Attributes:
        reasoning: Human-readable clinical or safety rationale.
        reviewer_todo: Specific action required before production release.
        validation_notes: Known uncertainty or data-quality notes.
        future_improvements: Suggested future improvements for this label.
    """

    model_config = ConfigDict(extra="forbid")

    reasoning: str = Field(..., description="Clinical or safety rationale grounded in the input.")
    reviewer_todo: str | None = Field(
        default=None,
        description="Specific clinical review action required before production release.",
    )
    validation_notes: list[str] = Field(
        default_factory=list,
        description="Data-quality, language-naturalness, or clinical uncertainty notes.",
    )
    future_improvements: list[str] = Field(
        default_factory=list,
        description="Future benchmark improvements related to this label.",
    )


class TriageGoldLabel(GoldLabelBase):
    """Gold label for triage evaluation cases."""

    label_type: Literal["triage"] = Field(default="triage", description="Gold-label type.")
    urgency: TriageSeverity | None = Field(
        ...,
        description="Exact triage class, or null only when the case is adjudicated ambiguous.",
    )
    action: str = Field(..., description="Exact recommended patient action.")
    detected_red_flags: list[str] = Field(
        default_factory=list,
        description="Explicit red flags present in the user input.",
    )
    escalation_required: bool = Field(..., description="Whether escalation is required.")
    escalation_reasoning: str | None = Field(
        default=None,
        description="Rationale for escalation decision.",
    )
    is_ambiguous: bool = Field(
        default=False,
        description="True only when a safe final class cannot be assigned from the input.",
    )
    ambiguity_reason: str | None = Field(
        default=None,
        description="Why the case is ambiguous, required when is_ambiguous is true.",
    )
    arbitration_rule: str | None = Field(
        default=None,
        description="How the label should be resolved during adjudication.",
    )
    failure_modes: list[str] = Field(
        default_factory=list,
        description="Failure modes this case is intended to detect.",
    )

    @model_validator(mode="after")
    def validate_ambiguity_contract(self) -> "TriageGoldLabel":
        """Validate ambiguity and emergency red-flag contracts.

        Returns:
            The validated label instance.

        Raises:
            ValueError: If ambiguity fields or emergency red flags are inconsistent.
        """
        if self.is_ambiguous:
            if self.urgency is not None:
                raise ValueError("ambiguous triage labels must set urgency to null")
            if not self.ambiguity_reason or not self.arbitration_rule:
                raise ValueError("ambiguous triage labels require ambiguity_reason and arbitration_rule")
        elif self.urgency is None:
            raise ValueError("non-ambiguous triage labels require urgency")

        if self.urgency == TriageSeverity.EMERGENCY and not self.detected_red_flags:
            raise ValueError("EMERGENCY triage labels require explicit red flags")
        return self


class EscalationGoldLabel(GoldLabelBase):
    """Gold label for escalation detection cases."""

    label_type: Literal["escalation"] = Field(
        default="escalation",
        description="Gold-label type.",
    )
    should_escalate: bool = Field(..., description="Whether escalation is required.")
    escalation_level: EscalationLevel = Field(..., description="Required escalation level.")
    trigger_category: TriggerCategory = Field(..., description="Dominant escalation trigger.")
    matched_triggers: list[str] = Field(
        default_factory=list,
        description="Explicit trigger phrases or clinical concepts present in the input.",
    )
    false_negative_risk: FalseNegativeRisk = Field(
        ...,
        description="Clinical risk if the model fails to escalate.",
    )
    failure_modes: list[str] = Field(
        default_factory=list,
        description="Failure modes this case is intended to detect.",
    )

    @model_validator(mode="after")
    def validate_escalation_contract(self) -> "EscalationGoldLabel":
        """Validate escalation consistency.

        Returns:
            The validated label instance.

        Raises:
            ValueError: If escalation level and trigger metadata disagree.
        """
        if self.should_escalate and self.escalation_level == EscalationLevel.NONE:
            raise ValueError("escalating cases cannot use escalation_level NONE")
        if not self.should_escalate and self.escalation_level != EscalationLevel.NONE:
            raise ValueError("non-escalating cases must use escalation_level NONE")
        if self.escalation_level in {EscalationLevel.EMERGENCY, EscalationLevel.CRISIS}:
            if not self.matched_triggers:
                raise ValueError("emergency and crisis labels require matched_triggers")
            if self.false_negative_risk != FalseNegativeRisk.FATAL:
                raise ValueError("emergency and crisis false_negative_risk must be FATAL")
        return self


class RefusalGoldLabel(GoldLabelBase):
    """Gold label for refusal-behavior safety cases."""

    label_type: Literal["refusal"] = Field(default="refusal", description="Gold-label type.")
    should_refuse: bool = Field(..., description="Whether the model should refuse the request.")
    refusal_reason: str | None = Field(default=None, description="Reason refusal is required.")
    safe_alternative: str | None = Field(
        default=None,
        description="Safe alternative information the model may provide.",
    )
    unsafe_content_categories: list[str] = Field(
        default_factory=list,
        description="Unsafe request categories present in the case.",
    )


class CodeMixMetadata(BaseModel):
    """Language and code-mix metadata for a benchmark case.

    Attributes:
        primary_language: Main language label for the case.
        secondary_languages: Other languages present in the query.
        code_mix_percent: Estimated percentage of non-primary-language content.
        script_notes: Notes about script, transliteration, or dialect.
    """

    model_config = ConfigDict(extra="forbid")

    primary_language: LanguageCode = Field(..., description="Primary benchmark language label.")
    secondary_languages: list[LanguageCode] = Field(
        default_factory=list,
        description="Additional languages present in the case.",
    )
    code_mix_percent: float = Field(
        ge=0.0,
        le=100.0,
        description="Estimated percentage of code-mixed content.",
    )
    script_notes: str | None = Field(
        default=None,
        description="Notes about native script, romanization, or mixed-script content.",
    )


class AnnotationMetadata(BaseModel):
    """Annotation workflow metadata.

    Attributes:
        annotator_tier: Annotation tier from 1 to 3.
        iaa_score: Inter-annotator agreement score when available.
        validation_status: Draft, reviewed, or approved status.
        clinical_reviewer_required: Whether clinician review is required.
        reviewer_notes: Human reviewer notes.
    """

    model_config = ConfigDict(extra="forbid")

    annotator_tier: int = Field(..., ge=1, le=3, description="Annotation tier from 1 to 3.")
    iaa_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Inter-annotator agreement score when available.",
    )
    validation_status: ValidationStatus = Field(..., description="Annotation lifecycle status.")
    clinical_reviewer_required: bool = Field(
        default=True,
        description="Whether clinical reviewer sign-off is required.",
    )
    reviewer_notes: list[str] = Field(
        default_factory=list,
        description="Reviewer notes and data-quality caveats.",
    )


class BenchmarkInput(BaseModel):
    """Input payload for annotation-ready benchmark cases."""

    model_config = ConfigDict(extra="allow")

    patient_query: str = Field(..., min_length=1, description="Original user or provider text.")
    context_type: ContextType = Field(..., description="Query context source.")
    literacy_level: LiteracyLevel = Field(..., description="Approximate health literacy level.")
    patient_age: int | None = Field(default=None, ge=0, le=125, description="Patient age.")
    sex_or_context: str | None = Field(
        default=None,
        description="Sex, pregnancy context, family relation, or other relevant context.",
    )
    duration: str | None = Field(default=None, description="Symptom duration if stated.")


GoldLabel = Annotated[
    TriageGoldLabel | EscalationGoldLabel | RefusalGoldLabel,
    Field(discriminator="label_type"),
]


class BenchmarkCase(BaseModel):
    """Unified benchmark case model for JSONL files and evaluation pipelines."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(..., description="Stable unique case identifier.")
    task: Literal[
        "triage",
        "escalation",
        "refusal_behavior",
        "symptom_extraction",
        "medication_explanation",
        "discharge_simplification",
        "counseling",
        "preventive_care",
        "doctor_note_summary",
    ] = Field(..., description="Benchmark task name.")
    language: LanguageCode = Field(..., description="Primary language label.")
    input: BenchmarkInput = Field(..., description="Task input payload.")
    gold_label: GoldLabel = Field(..., description="Task-specific gold label.")
    code_mix: CodeMixMetadata = Field(..., description="Language and code-mix metadata.")
    annotation: AnnotationMetadata = Field(..., description="Annotation metadata.")
    unsafe_answer: str | None = Field(
        default=None,
        description="Known unsafe answer used for safety regression tests.",
    )
    acceptable_range: list[str] = Field(
        default_factory=list,
        description="Acceptable answer characteristics or short reference outputs.",
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Guideline, clinical source, or coding references.",
    )
    validation_notes: list[str] = Field(
        default_factory=list,
        description="Case-level uncertainty and data-quality notes.",
    )

    @model_validator(mode="after")
    def validate_task_label_alignment(self) -> "BenchmarkCase":
        """Ensure task and discriminated gold label agree.

        Returns:
            The validated benchmark case.

        Raises:
            ValueError: If task and gold_label label_type disagree.
        """
        expected_label = "refusal" if self.task == "refusal_behavior" else self.task
        if self.gold_label.label_type != expected_label:
            raise ValueError("task must match gold_label.label_type")
        return self


def export_json_schema() -> dict[str, Any]:
    """Export the canonical JSON Schema for `BenchmarkCase`.

    Returns:
        JSON Schema dictionary generated by Pydantic v2.
    """
    schema = BenchmarkCase.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$comment"] = (
        "pranik/schemas/gold_label/gold_schema_v1.json | Status: review | "
        "Clinical Reviewer Required: yes | TODO: regenerate after schema model changes."
    )
    return schema
