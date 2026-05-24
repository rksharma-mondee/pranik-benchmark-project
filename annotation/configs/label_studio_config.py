# pranik/annotation/configs/label_studio_config.py
# Status: draft
# Clinical Reviewer Required: yes - this is the clinical review system
# TODO: Validate interface copy with the first MBBS/MD reviewer cohort.
"""Label Studio XML labeling interfaces for PRANIK clinical review."""

from __future__ import annotations

# TODO(tier4): add arbitration workflow for kappa < 0.60 cases
# TODO(audit): export full annotation audit trail for ICMR compliance
# TODO(credits): integrate NMC CME credit tracking for annotators
# FUTURE: replace manual Label Studio with automated annotation API


TRIAGE_INTERFACE = """
<View>
  <Header value="Patient Query"/>
  <Text name="patient_query" value="$patient_query"/>

  <Header value="Context"/>
  <Text name="context" value="Task: $task | Language: $language | Type: $context_type"/>

  <Header value="AI Pre-label (Tier 1 suggestion - verify this)"/>
  <Text name="ai_prelabel" value="$ai_prelabel"/>

  <Header value="Your Assessment"/>
  <Choices name="urgency" toName="patient_query" choice="single" required="true">
    <Choice value="EMERGENCY" style="color: red; font-weight: bold;"/>
    <Choice value="URGENT" style="color: orange;"/>
    <Choice value="ROUTINE" style="color: green;"/>
    <Choice value="SELF_CARE" style="color: blue;"/>
  </Choices>

  <Header value="Escalation Required?"/>
  <Choices name="escalation_required" toName="patient_query" choice="single" required="true">
    <Choice value="yes"/>
    <Choice value="no"/>
  </Choices>

  <Header value="Red Flags Detected (comma separated)"/>
  <TextArea name="red_flags" toName="patient_query" placeholder="e.g. chest pain, arm weakness"/>

  <Header value="Reviewer Notes"/>
  <TextArea name="notes" toName="patient_query" placeholder="Clinical reasoning..."/>

  <Header value="AI Pre-label Correct?"/>
  <Choices name="ai_correct" toName="patient_query" choice="single">
    <Choice value="correct"/>
    <Choice value="partially_correct"/>
    <Choice value="incorrect"/>
  </Choices>
</View>
""".strip()


ESCALATION_INTERFACE = """
<View>
  <Header value="Patient Query"/>
  <Text name="patient_query" value="$patient_query"/>

  <Header value="Context"/>
  <Text name="context" value="Task: $task | Language: $language | Type: $context_type"/>

  <Header value="AI Pre-label (Tier 1 suggestion - verify this)"/>
  <Text name="ai_prelabel" value="$ai_prelabel"/>

  <Header value="Escalation Required?"/>
  <Choices name="escalation_required" toName="patient_query" choice="single" required="true">
    <Choice value="yes"/>
    <Choice value="no"/>
  </Choices>

  <Header value="Escalation Level"/>
  <Choices name="escalation_level" toName="patient_query" choice="single" required="true">
    <Choice value="NONE"/>
    <Choice value="CLINICIAN"/>
    <Choice value="URGENT"/>
    <Choice value="EMERGENCY"/>
    <Choice value="CRISIS"/>
  </Choices>

  <Header value="Matched Triggers (comma separated)"/>
  <TextArea name="red_flags" toName="patient_query"
    placeholder="e.g. stroke symptoms, suicidal intent"/>

  <Header value="Reviewer Notes"/>
  <TextArea name="notes" toName="patient_query" placeholder="Clinical reasoning..."/>

  <Header value="AI Pre-label Correct?"/>
  <Choices name="ai_correct" toName="patient_query" choice="single">
    <Choice value="correct"/>
    <Choice value="partially_correct"/>
    <Choice value="incorrect"/>
  </Choices>
</View>
""".strip()


GENERAL_REVIEW_INTERFACE = """
<View>
  <Header value="Patient Query"/>
  <Text name="patient_query" value="$patient_query"/>

  <Header value="Context"/>
  <Text name="context" value="Task: $task | Language: $language | Type: $context_type"/>

  <Header value="AI Pre-label (Tier 1 suggestion - verify this)"/>
  <Text name="ai_prelabel" value="$ai_prelabel"/>

  <Header value="Clinical Correctness"/>
  <Choices name="clinical_correctness" toName="patient_query" choice="single" required="true">
    <Choice value="correct"/>
    <Choice value="partially_correct"/>
    <Choice value="incorrect"/>
  </Choices>

  <Header value="Safety Risk"/>
  <Choices name="safety_risk" toName="patient_query" choice="single" required="true">
    <Choice value="none"/>
    <Choice value="low"/>
    <Choice value="medium"/>
    <Choice value="high"/>
  </Choices>

  <Header value="Reviewer Notes"/>
  <TextArea name="notes" toName="patient_query" placeholder="Clinical reasoning..."/>
</View>
""".strip()


TASK_INTERFACE_CONFIGS: dict[str, str] = {
    "triage": TRIAGE_INTERFACE,
    "escalation": ESCALATION_INTERFACE,
    "refusal_behavior": GENERAL_REVIEW_INTERFACE,
    "symptom_extraction": GENERAL_REVIEW_INTERFACE,
    "medication_explanation": GENERAL_REVIEW_INTERFACE,
    "medical_counseling": GENERAL_REVIEW_INTERFACE,
    "counseling": GENERAL_REVIEW_INTERFACE,
    "preventive_care": GENERAL_REVIEW_INTERFACE,
    "discharge_simplification": GENERAL_REVIEW_INTERFACE,
    "doctor_note_summary": GENERAL_REVIEW_INTERFACE,
    "doctor_note_summarization": GENERAL_REVIEW_INTERFACE,
}


def get_label_config(task: str) -> str:
    """Return the Label Studio XML interface for a benchmark task."""

    return TASK_INTERFACE_CONFIGS.get(task, GENERAL_REVIEW_INTERFACE)
