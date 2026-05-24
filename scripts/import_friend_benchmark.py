# pranik/scripts/import_friend_benchmark.py
# Status: draft
# Clinical Reviewer Required: yes
# TODO: Replace heuristic urgency/task mapping with clinician-reviewed labels before gold release.
"""Import friend-generated JSONL benchmark drafts into PRANIK schema.

This importer accepts the external flat JSONL format:
id, language, category, prompt, expected_answer, acceptable_answer_range, ...

All categories are converted into the canonical PRANIK BenchmarkCase shape.
Rows that fail schema validation are preserved in datasets/interim with an
import error for review.
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from schemas.gold_label.gold_schema_v1 import BenchmarkCase, get_gold_label_class


SOURCE_FILES = [
    Path(r"C:\Users\rahul\Downloads\pranik_benchmark.jsonl"),
    Path(r"C:\Users\rahul\Downloads\pranik_benchmark_v2.jsonl"),
]
OUTPUT_PATH = Path("datasets/synthetic/friend_pranik_supported_20260522.jsonl")
UNSUPPORTED_PATH = Path("datasets/interim/friend_pranik_unsupported_20260522.jsonl")
REPORT_PATH = Path("datasets/metadata/friend_benchmark_import_report.json")

CATEGORY_TASK_MAP = {
    "Triage and urgency detection": "triage",
    "Escalation behavior": "escalation",
    "Refusal behavior": "refusal_behavior",
    "Symptom extraction": "symptom_extraction",
    "Medication explanation": "medication_explanation",
    "Medical counseling": "counseling",
    "Preventive care guidance": "preventive_care",
    "Preventive care advice": "preventive_care",
    "Discharge-summary simplification": "discharge_simplification",
    "Discharge summary simplification": "discharge_simplification",
    "Doctor-note summarization": "doctor_note_summary",
    "Doctor note summarization": "doctor_note_summary",
}

LANGUAGE_MAP = {
    "Hindi": "hi",
    "Telugu": "te",
    "Kannada": "kn",
    "Bengali": "bn",
    "Indian English": "en-IN",
    "Hindi (Code-mixed)": "mix",
    "Telugu (Code-mixed)": "mix",
    "Kannada (Code-mixed)": "mix",
    "Bengali (Code-mixed)": "mix",
    "Indian English (Code-mixed)": "mix",
}

SECONDARY_BY_LANGUAGE = {
    "Hindi (Code-mixed)": ["hi", "en-IN"],
    "Telugu (Code-mixed)": ["te", "en-IN"],
    "Kannada (Code-mixed)": ["kn", "en-IN"],
    "Bengali (Code-mixed)": ["bn", "en-IN"],
    "Indian English (Code-mixed)": ["en-IN"],
}

FAMILY_CONTEXT_TERMS = {
    "amma",
    "nanna",
    "baba",
    "mother",
    "father",
    "child",
    "wife",
    "husband",
    "spouse",
    "daughter",
    "son",
    "papa",
    "maa",
}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            record = json.loads(stripped)
            record["_source_file"] = path.name
            record["_source_line"] = line_number
            records.append(record)
    return records


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def _infer_context_type(prompt: str, patterns: list[str]) -> str:
    if "provider_generated" in patterns:
        return "provider_generated"
    if "family_reported" in patterns:
        return "family_reported"
    lowered = prompt.lower()
    if any(term in lowered for term in FAMILY_CONTEXT_TERMS):
        return "family_reported"
    return "patient_reported"


def _infer_age(prompt: str) -> int | None:
    match = re.search(r"\b(?:age\s*)?(\d{1,3})(?:\s*[- ]?year|\s*yrs?|\s*age)?\b", prompt, re.I)
    if not match:
        return None
    age = int(match.group(1))
    return age if 0 <= age <= 125 else None


def _infer_duration(prompt: str) -> str | None:
    match = re.search(
        r"\b((?:since|for|last)\s+[^,.?;]{1,40}|[0-9]+\s*(?:mins?|minutes?|hours?|days?|weeks?))",
        prompt,
        re.I,
    )
    return match.group(1).strip() if match else None


def _canonical_language(source_language: str) -> str:
    try:
        return LANGUAGE_MAP[source_language]
    except KeyError as exc:
        raise ValueError(f"Unsupported source language: {source_language}") from exc


def _code_mix_metadata(row: dict[str, Any]) -> dict[str, Any]:
    source_language = str(row["language"])
    pranik_language = _canonical_language(source_language)
    is_code_mixed = pranik_language == "mix"
    source_primary = source_language.replace(" (Code-mixed)", "")

    return {
        "primary_language": pranik_language,
        "secondary_languages": SECONDARY_BY_LANGUAGE.get(source_language, []),
        "code_mix_percent": 50.0 if is_code_mixed else 0.0,
        "script_notes": (
            f"Imported friend-generated synthetic case; source language={source_language}; "
            f"source primary={source_primary}."
        ),
    }


def _annotation(row: dict[str, Any]) -> dict[str, Any]:
    reviewed = bool(row.get("clinician_reviewed"))
    return {
        "annotator_tier": 1,
        "iaa_score": None,
        "validation_status": "reviewed" if reviewed else "draft",
        "clinical_reviewer_required": not reviewed,
        "reviewer_notes": [
            "Friend-generated synthetic draft imported from external JSONL.",
            "Requires schema, language, and clinician review before gold release.",
        ],
    }


def _input(row: dict[str, Any]) -> dict[str, Any]:
    prompt = str(row["prompt"]).strip()
    patterns = row.get("clinical_patterns")
    clinical_patterns = patterns if isinstance(patterns, list) else []
    return {
        "patient_query": prompt,
        "context_type": _infer_context_type(prompt, clinical_patterns),
        "literacy_level": "medium",
        "patient_age": _infer_age(prompt),
        "sex_or_context": None,
        "duration": _infer_duration(prompt),
    }


def _base_case(row: dict[str, Any], task: str) -> dict[str, Any]:
    source_name = str(row["_source_file"]).replace(".jsonl", "")
    acceptable = row.get("acceptable_answer_range")
    acceptable_range = acceptable if isinstance(acceptable, list) else [str(row["expected_answer"])]
    return {
        "case_id": f"{source_name}-{row['id']}",
        "task": task,
        "language": _canonical_language(str(row["language"])),
        "input": _input(row),
        "code_mix": _code_mix_metadata(row),
        "annotation": _annotation(row),
        "unsafe_answer": row.get("unsafe_answer"),
        "acceptable_range": acceptable_range,
        "evidence": [str(row.get("evidence_source", "External synthetic dataset"))],
        "validation_notes": [
            f"Imported from {row['_source_file']} line {row['_source_line']}.",
            f"Source category={row.get('category')}; risk_tier={row.get('risk_tier')}.",
            "Synthetic draft, not gold.",
        ],
    }


def _urgency(row: dict[str, Any]) -> str:
    expected = str(row.get("expected_answer", "")).lower()
    risk_tier = str(row.get("risk_tier", "")).lower()
    escalation_required = bool(row.get("escalation_required"))
    if "emergency" in expected or risk_tier == "critical":
        return "EMERGENCY"
    if "urgent" in expected or escalation_required:
        return "URGENT"
    if risk_tier == "low" and any(term in expected for term in ("home", "monitor", "usually")):
        return "SELF_CARE"
    return "ROUTINE"


def _false_negative_risk(row: dict[str, Any], escalation_level: str) -> str:
    risk_tier = str(row.get("risk_tier", "")).lower()
    if escalation_level in {"EMERGENCY", "CRISIS"} or risk_tier == "critical":
        return "FATAL"
    if risk_tier == "medium":
        return "HIGH"
    return "LOW"


def _matched_triggers(row: dict[str, Any]) -> list[str]:
    patterns = row.get("clinical_patterns")
    if isinstance(patterns, list) and patterns:
        return [str(pattern) for pattern in patterns]
    triggers = []
    if bool(row.get("escalation_required")):
        triggers.append(f"source_escalation_required_{row.get('risk_tier', 'unknown')}")
    if str(row.get("risk_tier", "")).lower() == "critical":
        triggers.append("source_critical_risk_tier")
    return triggers or ["source_synthetic_label"]


def _clinical_patterns(row: dict[str, Any]) -> list[str]:
    patterns = row.get("clinical_patterns")
    return [str(pattern) for pattern in patterns] if isinstance(patterns, list) else []


def _split_expected_items(row: dict[str, Any]) -> list[str]:
    expected = str(row.get("expected_answer", "")).strip()
    symptoms_match = re.search(r"symptoms extracted:\s*(.*?)(?:\.\s|$)", expected, re.I)
    text = symptoms_match.group(1) if symptoms_match else expected
    text = re.sub(r"\b\d+\.\s*", "", text)
    items = [
        item.strip(" .:-")
        for item in re.split(r",|;|\band\b|\n", text)
        if item.strip(" .:-")
    ]
    return items or [expected]


def _body_locations(text: str) -> list[str]:
    location_terms = {
        "chest",
        "throat",
        "neck",
        "head",
        "sir",
        "pet",
        "stomach",
        "abdomen",
        "knee",
        "joint",
        "back",
        "skin",
        "eye",
        "ear",
    }
    lowered = text.lower()
    return sorted(term for term in location_terms if term in lowered)


def _severity(row: dict[str, Any]) -> str | None:
    text = f"{row.get('prompt', '')} {row.get('expected_answer', '')}".lower()
    if any(term in text for term in ("severe", "bahut", "critical", "emergency")):
        return "severe"
    if any(term in text for term in ("moderate", "urgent", "worse")):
        return "moderate"
    if "mild" in text:
        return "mild"
    risk_tier = str(row.get("risk_tier", "")).lower()
    if risk_tier == "critical":
        return "severe"
    if risk_tier == "medium":
        return "moderate"
    if risk_tier == "low":
        return "mild"
    return None


def _medication_name(row: dict[str, Any]) -> str:
    text = f"{row.get('prompt', '')} {row.get('expected_answer', '')}"
    dose_match = re.search(r"\b([A-Z][A-Za-z-]+)\s*\d+\s*(?:mg|mcg|g|ml)\b", text)
    if dose_match:
        return dose_match.group(1)
    known = (
        "Paracetamol",
        "Azithromycin",
        "Levothyroxine",
        "Alprazolam",
        "Escitalopram",
        "Metformin",
        "Insulin",
        "Antibiotic",
    )
    lowered = text.lower()
    for medication in known:
        if medication.lower() in lowered:
            return medication
    return "unspecified medication"


def _dosage(row: dict[str, Any]) -> str:
    text = f"{row.get('prompt', '')} {row.get('expected_answer', '')}"
    match = re.search(r"\b\d+\s*(?:mg|mcg|g|ml)(?:\s+[A-Za-z]+){0,4}", text, re.I)
    return match.group(0).strip() if match else "as prescribed by clinician"


def _timing(row: dict[str, Any]) -> str:
    expected = str(row.get("expected_answer", ""))
    timing_terms = ("with food", "after food", "before food", "morning", "night", "as needed", "SOS")
    for term in timing_terms:
        if term.lower() in expected.lower():
            return term
    return "follow clinician instructions; timing not fully specified in source record"


def _side_effects(row: dict[str, Any]) -> list[str]:
    expected = str(row.get("expected_answer", "")).lower()
    found = []
    for term in ("dependency", "palpitations", "bone loss", "anxiety", "allergy", "side effects"):
        if term in expected:
            found.append(term)
    return found or ["explain relevant side effects and warning signs when clinically applicable"]


def _source_list(row: dict[str, Any]) -> list[str]:
    source = str(row.get("evidence_source", "External synthetic dataset"))
    return [source] if source else ["External synthetic dataset"]


def _triage_gold_label(row: dict[str, Any]) -> dict[str, Any]:
    urgency = _urgency(row)
    return {
        "label_type": "triage",
        "urgency": urgency,
        "action": str(row["expected_answer"]),
        "detected_red_flags": _matched_triggers(row) if urgency == "EMERGENCY" else [],
        "reasoning": (
            "Imported synthetic triage label. "
            f"Source risk_tier={row.get('risk_tier')}; "
            f"escalation_required={row.get('escalation_required')}."
        ),
        "escalation_required": bool(row.get("escalation_required")),
        "escalation_reasoning": (
            "Source record marks escalation_required=true."
            if row.get("escalation_required")
            else None
        ),
        "is_ambiguous": False,
        "ambiguity_reason": None,
        "arbitration_rule": None,
        "failure_modes": ["external_synthetic_import", f"risk_tier_{row.get('risk_tier')}"],
        "reviewer_todo": "Clinician must verify imported urgency/action before gold release.",
        "validation_notes": ["Heuristic conversion from flat external benchmark format."],
        "future_improvements": ["Replace heuristic urgency mapping with adjudicated gold label."],
    }


def _escalation_gold_label(row: dict[str, Any]) -> dict[str, Any]:
    should_escalate = bool(row.get("escalation_required"))
    if not should_escalate:
        escalation_level = "NONE"
    elif str(row.get("risk_tier", "")).lower() == "critical":
        escalation_level = "EMERGENCY"
    elif str(row.get("risk_tier", "")).lower() == "medium":
        escalation_level = "URGENT"
    else:
        escalation_level = "CLINICIAN"

    return {
        "label_type": "escalation",
        "should_escalate": should_escalate,
        "escalation_level": escalation_level,
        "trigger_category": "other_red_flag" if should_escalate else "none",
        "matched_triggers": _matched_triggers(row) if should_escalate else [],
        "reasoning": (
            "Imported synthetic escalation label. "
            f"Source risk_tier={row.get('risk_tier')}; "
            f"escalation_required={row.get('escalation_required')}."
        ),
        "false_negative_risk": _false_negative_risk(row, escalation_level),
        "failure_modes": ["external_synthetic_import", f"risk_tier_{row.get('risk_tier')}"],
        "reviewer_todo": "Clinician must verify escalation level before gold release.",
        "validation_notes": ["Heuristic conversion from flat external benchmark format."],
        "future_improvements": ["Replace heuristic escalation mapping with adjudicated gold label."],
    }


def _should_refuse(row: dict[str, Any]) -> bool:
    expected = str(row.get("expected_answer", "")).lower()
    refusal_markers = (
        "cannot",
        "can't",
        "do not",
        "don't",
        "should not",
        "must not",
        "beda",
        "prescribe",
        "diagnose",
        "decide",
        "consult",
        "doctor",
    )
    return any(marker in expected for marker in refusal_markers)


def _refusal_gold_label(row: dict[str, Any]) -> dict[str, Any]:
    should_refuse = _should_refuse(row)
    return {
        "label_type": "refusal",
        "should_refuse": should_refuse,
        "refusal_reason": (
            "Request requires diagnosis, prescription, or treatment decision beyond assistant scope."
            if should_refuse
            else None
        ),
        "safe_alternative": str(row.get("expected_answer")) if should_refuse else None,
        "unsafe_content_categories": ["medical_advice_beyond_scope"] if should_refuse else [],
        "reasoning": (
            "Imported synthetic refusal label. "
            f"Heuristic should_refuse={should_refuse}; source risk_tier={row.get('risk_tier')}."
        ),
        "reviewer_todo": "Clinician/safety reviewer must verify refusal label before gold release.",
        "validation_notes": ["Heuristic conversion from flat external benchmark format."],
        "future_improvements": ["Replace heuristic refusal mapping with adjudicated gold label."],
    }


def _symptom_extraction_gold_label(row: dict[str, Any]) -> dict[str, Any]:
    prompt = str(row.get("prompt", ""))
    symptoms = _split_expected_items(row)
    return {
        "label_type": "symptom_extraction",
        "symptoms": symptoms,
        "onset": None,
        "duration": _infer_duration(prompt),
        "severity": _severity(row),
        "negated_symptoms": [
            symptom
            for symptom in ("fever", "bleeding", "vomiting", "breathlessness")
            if re.search(rf"\bno\s+{symptom}\b|\bwithout\s+{symptom}\b", prompt, re.I)
        ],
        "body_locations": _body_locations(prompt),
        "associated_symptoms": symptoms[1:] if len(symptoms) > 1 else [],
        "family_reported": _infer_context_type(prompt, _clinical_patterns(row)) == "family_reported",
        "extraction_confidence": "medium",
        "reasoning": "Imported synthetic symptom-extraction label from expected answer.",
        "reviewer_todo": "Clinician must verify extracted entities before gold release.",
        "validation_notes": ["Heuristic conversion from flat external benchmark format."],
        "future_improvements": ["Replace expected-answer parsing with adjudicated extraction spans."],
    }


def _medication_explanation_gold_label(row: dict[str, Any]) -> dict[str, Any]:
    risk_tier = str(row.get("risk_tier", "")).lower()
    return {
        "label_type": "medication_explanation",
        "medication_name": _medication_name(row),
        "correct_dosage": _dosage(row),
        "correct_timing": _timing(row),
        "side_effects_to_mention": _side_effects(row),
        "contraindications": [],
        "interaction_warning": None,
        "literacy_appropriate": True,
        "dangerous_if_missed": risk_tier in {"critical", "medium"} or bool(row.get("escalation_required")),
        "unsafe_advice": str(row.get("unsafe_answer", "")),
        "reasoning": "Imported synthetic medication-explanation label from expected answer.",
        "reviewer_todo": "Clinician/pharmacist must verify medication fields before gold release.",
        "validation_notes": ["Heuristic conversion from flat external benchmark format."],
        "future_improvements": ["Add medication ontology extraction for dose/timing/interaction fields."],
    }


def _medical_counseling_gold_label(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "label_type": "counseling",
        "clinical_accuracy_required": [str(row.get("expected_answer", ""))],
        "cultural_considerations": _clinical_patterns(row) or ["Indian patient context"],
        "empathy_required": True,
        "referral_required": bool(row.get("escalation_required"))
        or "doctor" in str(row.get("expected_answer", "")).lower()
        or "consult" in str(row.get("expected_answer", "")).lower(),
        "unsafe_advice": str(row.get("unsafe_answer", "")),
        "acceptable_tone": "empathetic",
        "avoid_phrases": [],
        "reasoning": "Imported synthetic counseling label from expected answer.",
        "reviewer_todo": "Clinician/language reviewer must verify counseling requirements.",
        "validation_notes": ["Heuristic conversion from flat external benchmark format."],
        "future_improvements": ["Split expected answer into atomic counseling rubric items."],
    }


def _preventive_care_gold_label(row: dict[str, Any]) -> dict[str, Any]:
    expected = str(row.get("expected_answer", ""))
    return {
        "label_type": "preventive_care",
        "recommended_actions": _split_expected_items(row),
        "guideline_source": _source_list(row),
        "india_specific": True,
        "culturally_feasible": True,
        "vaccination_relevant": bool(re.search(r"\bvaccin|immuni[sz]ation|shot\b", expected, re.I)),
        "dietary_guidance": expected if re.search(r"\bdiet|fiber|meat|sugar|salt|food\b", expected, re.I) else None,
        "unsafe_advice": str(row.get("unsafe_answer", "")),
        "misinformation_to_avoid": [],
        "reasoning": "Imported synthetic preventive-care label from expected answer.",
        "reviewer_todo": "Clinician must verify preventive guidance against Indian guideline sources.",
        "validation_notes": ["Heuristic conversion from flat external benchmark format."],
        "future_improvements": ["Map source labels to exact ICMR/WHO/NHP references."],
    }


def _discharge_simplification_gold_label(row: dict[str, Any]) -> dict[str, Any]:
    text = f"{row.get('prompt', '')} {row.get('expected_answer', '')}"
    danger_signs = [
        sign
        for sign in ("fever", "bleeding", "breathlessness", "chest pain", "severe pain", "vomiting")
        if sign in text.lower()
    ] or ["danger signs stated in source note"]
    medications = [
        med
        for med in ("Paracetamol", "Azithromycin", "Levothyroxine", "Metformin", "Insulin")
        if med.lower() in text.lower()
    ] or ["medications stated in source note"]
    return {
        "label_type": "discharge_simplification",
        "original_complexity": "high",
        "target_literacy_level": "low",
        "danger_signs_to_include": danger_signs,
        "medications_to_explain": medications,
        "followup_instructions": str(row.get("expected_answer", "")),
        "readability_target": "5th_grade",
        "missing_danger_sign_is_fatal": str(row.get("risk_tier", "")).lower() == "critical",
        "unsafe_simplification": str(row.get("unsafe_answer", "")),
        "reasoning": "Imported synthetic discharge-simplification label from expected answer.",
        "reviewer_todo": "Clinician must verify danger signs and follow-up instructions.",
        "validation_notes": ["Heuristic conversion from flat external benchmark format."],
        "future_improvements": ["Extract medication and danger-sign spans from real discharge notes."],
    }


def _doctor_note_summarization_gold_label(row: dict[str, Any]) -> dict[str, Any]:
    expected = str(row.get("expected_answer", ""))
    prompt = str(row.get("prompt", ""))
    return {
        "label_type": "doctor_note_summary",
        "subjective_required": [prompt],
        "objective_required": ["objective findings if stated in source"],
        "assessment_required": [expected],
        "plan_required": [expected],
        "critical_info_must_retain": _matched_triggers(row),
        "hallucination_risk_fields": [
            "diagnosis",
            "medications",
            "test_results",
            "followup_timeline",
        ],
        "temporal_accuracy_required": True,
        "unsafe_summary": str(row.get("unsafe_answer", "")),
        "reasoning": "Imported synthetic doctor-note summarization label from expected answer.",
        "reviewer_todo": "Clinician must verify SOAP section requirements before gold release.",
        "validation_notes": ["Heuristic conversion from flat external benchmark format."],
        "future_improvements": ["Replace full expected answer fields with adjudicated SOAP rubrics."],
    }


def _gold_label(row: dict[str, Any], task: str) -> dict[str, Any]:
    if task == "triage":
        return _triage_gold_label(row)
    if task == "escalation":
        return _escalation_gold_label(row)
    if task == "refusal_behavior":
        return _refusal_gold_label(row)
    if task == "symptom_extraction":
        return _symptom_extraction_gold_label(row)
    if task == "medication_explanation":
        return _medication_explanation_gold_label(row)
    if task == "counseling":
        return _medical_counseling_gold_label(row)
    if task == "preventive_care":
        return _preventive_care_gold_label(row)
    if task == "discharge_simplification":
        return _discharge_simplification_gold_label(row)
    if task == "doctor_note_summary":
        return _doctor_note_summarization_gold_label(row)
    raise ValueError(f"Unsupported task: {task}")


def _convert_supported(row: dict[str, Any]) -> dict[str, Any]:
    task = CATEGORY_TASK_MAP[str(row["category"])]
    converted = _base_case(row, task)
    converted["gold_label"] = _gold_label(row, task)

    gold_label_cls = get_gold_label_class(task)
    gold_label_cls.model_validate(converted["gold_label"])
    return BenchmarkCase.model_validate(converted).model_dump(mode="json")


def main() -> None:
    converted: list[dict[str, Any]] = []
    unsupported: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    category_counts: Counter[str] = Counter()
    supported_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()

    for source_path in SOURCE_FILES:
        for row in _read_jsonl(source_path):
            source_counts[str(row["_source_file"])] += 1
            category = str(row.get("category"))
            category_counts[category] += 1
            if category not in CATEGORY_TASK_MAP:
                row["_import_error"] = f"Unsupported source category: {category}"
                unsupported.append(row)
                continue
            try:
                record = _convert_supported(row)
            except Exception as exc:
                row["_import_error"] = str(exc)
                unsupported.append(row)
                errors.append(
                    {
                        "source_file": row.get("_source_file"),
                        "source_line": row.get("_source_line"),
                        "id": row.get("id"),
                        "error": str(exc),
                    }
                )
                continue
            converted.append(record)
            supported_counts[str(record["task"])] += 1

    _write_jsonl(OUTPUT_PATH, converted)
    _write_jsonl(UNSUPPORTED_PATH, unsupported)

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_files": [str(path) for path in SOURCE_FILES],
        "source_record_counts": dict(source_counts),
        "category_counts": dict(category_counts),
        "converted_records": len(converted),
        "unsupported_records": len(unsupported),
        "conversion_errors": len(errors),
        "converted_task_counts": dict(supported_counts),
        "output_path": str(OUTPUT_PATH),
        "unsupported_path": str(UNSUPPORTED_PATH),
        "errors": errors,
        "notes": [
            "All known friend-generated categories are converted into schemas supported by gold_schema_v1.py.",
            "Rows that fail conversion are preserved verbatim in datasets/interim with _import_error.",
            "All converted rows are validated with BenchmarkCase before writing.",
            "Converted labels remain synthetic drafts and require clinician review before gold release.",
        ],
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
