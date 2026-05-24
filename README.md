<div align="center">

<!-- BANNER -->
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0f2027,50:203a43,100:2c5364&height=200&section=header&text=PRANIK&fontSize=80&fontColor=ffffff&fontAlignY=38&desc=Indic%20Healthcare%20LLM%20Benchmark%20System&descAlignY=60&descSize=22&animation=fadeIn" width="100%"/>

<br/>

[![Status](https://img.shields.io/badge/Status-Phase%202%20→%203-orange?style=for-the-badge&logo=statuspage&logoColor=white)](https://github.com)
[![Languages](https://img.shields.io/badge/Languages-6%20Indic%20Variants-blueviolet?style=for-the-badge&logo=googletranslate&logoColor=white)](https://github.com)
[![Tasks](https://img.shields.io/badge/Clinical%20Tasks-9-critical?style=for-the-badge&logo=medrt&logoColor=white)](https://github.com)
[![Models](https://img.shields.io/badge/LLMs%20Targeted-10%2B-blue?style=for-the-badge&logo=openai&logoColor=white)](https://github.com)
[![Compliance](https://img.shields.io/badge/Compliance-DPDP%202025%20%7C%20CDSCO%20%7C%20ICMR-green?style=for-the-badge&logo=shield&logoColor=white)](https://github.com)
[![Gold Cases](https://img.shields.io/badge/Gold%20Cases-23%20Pilot%20(Target%201000%2B)-yellow?style=for-the-badge&logo=database&logoColor=white)](https://github.com)
[![License](https://img.shields.io/badge/License-Research%20Use%20Only-red?style=for-the-badge&logo=opensourceinitiative&logoColor=white)](https://github.com)

<br/>

> **PRANIK is not a chatbot. It is not a diagnostic tool. It is a rigorous, clinician-verified benchmark system that evaluates whether large language models are safe enough for Indian patient-facing healthcare use cases — across Indic languages, code-mixed speech, and 9 critical clinical task categories.**

<br/>

---

</div>

## 📋 Table of Contents

<details open>
<summary><strong>Click to expand full table of contents</strong></summary>

- [🧭 What Is PRANIK?](#-what-is-pranik)
- [⚡ The One-Sentence Summary](#-the-one-sentence-summary)
- [🏥 Why This Matters](#-why-this-matters)
- [🗺️ Executive Summary](#️-executive-summary)
- [🔬 Technical Summary](#-technical-summary)
- [🏗️ System Architecture](#️-system-architecture)
  - [Current State](#current-state-architecture)
  - [Future State](#future-state-architecture)
- [📊 Clinical Tasks & Languages](#-clinical-tasks--languages)
- [🔄 Complete Data Lifecycle](#-complete-data-lifecycle)
- [🏷️ Annotation Workflow](#️-annotation-workflow)
- [🧪 Evaluation Workflow](#-evaluation-workflow)
- [🛡️ Safety & Compliance Pipeline](#️-safety--compliance-pipeline)
- [📁 Repository Structure](#-repository-structure)
- [🗓️ Roadmap](#️-roadmap)
- [⚠️ Honest Gaps & Limitations](#️-honest-gaps--limitations)
- [🤔 How Labeling Works (Plain English)](#-how-labeling-works-plain-english)
- [🔭 LLMs Being Evaluated](#-llms-being-evaluated)
- [📏 Key Metrics](#-key-metrics)
- [⚖️ Compliance Framework](#️-compliance-framework)
- [🚀 Getting Started](#-getting-started)
- [🤝 Contributing & Partnerships](#-contributing--partnerships)
- [📬 Contact](#-contact)

</details>

---

## 🧭 What Is PRANIK?

```
PRANIK ≠ A healthcare chatbot
PRANIK ≠ A clinical decision support tool
PRANIK ≠ A diagnostic system

PRANIK = A benchmark + safety evaluation system for healthcare LLMs
```

**PRANIK**  is an independent benchmark and safety evaluation system purpose-built for the Indian healthcare AI landscape. It answers one critical question:

> *"Is this LLM actually safe for Indian patients speaking in Hindi, Telugu, Kannada, Bengali, Indian English, or code-mixed speech?"*

PRANIK creates structured, clinician-reviewed test cases → runs LLMs through those cases → scores them rigorously → flags dangerous failures → publishes transparent results.

No model passes PRANIK because it sounds confident. It passes because clinicians verified it is correct.

---

## ⚡ The One-Sentence Summary

> **PRANIK turns raw medical scenarios into doctor-verified gold test cases, then uses those cases to test whether LLMs are safe enough for Indian clinical use — before any real patient sees them.**

---

## 🏥 Why This Matters

| Problem | Reality |
|---|---|
| 🌍 1.4B people, 22 official languages | Most healthcare AI is English-only |
| 🧬 Code-mixed speech is the norm | "Mujhe *chest pain* ho raha hai" — no benchmark handles this |
| ⚕️ LLMs fail silently on medical tasks | A wrong triage answer can delay life-saving care |
| 📋 No Indian clinical safety standard | No published benchmark for Indic healthcare LLMs exists |
| 🔒 DPDP 2025 + CDSCO SaMD incoming | Regulatory compliance is not optional anymore |
| 🏥 Hospital AI adoption is accelerating | Without benchmarks, unsafe models will reach patients |

**PRANIK fills this gap.** Systematically. With clinician oversight. With transparent scoring. With public accountability.

---

## 🗺️ Executive Summary

<table>
<tr>
<td width="50%" valign="top">

### 🎯 What PRANIK Does
- Generates synthetic + real patient-facing healthcare scenarios
- Preprocesses, validates, and scrubs PII from all cases
- Routes cases through a 4-tier clinical annotation pipeline
- Enforces inter-annotator agreement (Cohen's κ > 0.70) before any case enters the gold dataset
- Evaluates 10+ LLMs — including Indian models — on those gold cases
- Scores outputs across clinical accuracy, safety, refusal behavior, and escalation detection
- Flags dangerous failures for clinician review
- Publishes model scorecards and a public leaderboard

</td>
<td width="50%" valign="top">

### 📍 Current Status
| Milestone | Status |
|---|---|
| Engineering foundation | ✅ Complete |
| Synthetic generation pipeline | ✅ Complete |
| Preprocessing + PII scrub | ✅ Complete |
| Label Studio integration | ✅ Active |
| 23 Triage pilot cases uploaded | ✅ Done |
| First annotation pass | 🔄 In Progress |
| Second independent reviewer | ❌ Needed |
| Cohen's κ computation | ❌ Pending |
| First gold file created | ❌ Pending |
| Model evaluation at scale | ❌ Pending |
| Public leaderboard | ❌ Future |

</td>
</tr>
</table>

> **Honest statement:** PRANIK is a serious, well-architected system with a real engineering foundation and a clear clinical methodology. It is currently between Phase 2 and Phase 3. The biggest gap is not code — it is clinician-reviewed gold data. This README reflects what is real, not what is aspirational.

---

## 🔬 Technical Summary

```
Stack:        Python 3.11+ · FastAPI · Pydantic v2 · Label Studio
Generation:   Groq adapter (synthetic) · Open-weight models (future)
Annotation:   Label Studio · 4-tier clinical pipeline · Cohen's κ gate
Evaluation:   Custom prompt builder · Model adapter abstraction · Per-task metrics
Safety:       Presidio-based PII scrub · Indian PII patterns · Audit log
Observability: W&B · MLflow · DVC (future)
Compliance:   DPDP 2025 · CDSCO SaMD Class C · ICMR AI Ethics 2023
Deployment:   FastAPI · Docker (planned) · Monthly regression pipeline
Leaderboard:  HuggingFace public leaderboard (future)
```

### Core Schema — `BenchmarkCase`

Every case in PRANIK is a `BenchmarkCase` Pydantic v2 object containing:

| Field | Purpose |
|---|---|
| `input` | Patient scenario in target language |
| `gold_label` | Clinician-verified correct answer |
| `code_mix_metadata` | Language mixing analysis |
| `annotation_metadata` | Reviewer IDs, timestamps, kappa score |
| `evidence` | Clinical evidence supporting gold label |
| `acceptable_range` | Tolerated answer variations |
| `unsafe_answer` | Answers that must NEVER be produced |
| `validation_notes` | QA notes from clinical review |

---

## 🏗️ System Architecture

### Current State Architecture

```mermaid
graph TB
    subgraph SOURCES["📥 DATA SOURCES"]
        SG["🤖 Synthetic Generator<br/>(Groq Adapter)<br/>9 tasks × 6 languages<br/>540 draft targets"]
        FD["📝 Friend/Team<br/>Draft Cases<br/>(Current)"]
    end

    subgraph PREPROCESS["🔧 PREPROCESSING"]
        NRM["Normalize Text"]
        LD["Language Detection"]
        PII["PII Scrubber<br/>(Indian Patterns)"]
        AUD["Audit Log Writer"]
        VAL["Schema Validation<br/>(Pydantic v2)"]
    end

    subgraph DATASTORES["💾 DATA STORES"]
        DRAFT["datasets/synthetic/<br/>Draft Cases"]
        PROC["datasets/processed/<br/>Cleaned (NOT gold)"]
        REJ["datasets/rejected/<br/>Failed Validation"]
        GOLD["datasets/gold/<br/>✅ Clinician Approved<br/>(κ > 0.70 only)"]
        AUDIT["datasets/audit/<br/>Audit Logs"]
    end

    subgraph ANNOTATION["🏥 ANNOTATION — Label Studio"]
        LS["Label Studio<br/>Project (Triage)<br/>23 cases uploaded"]
        R1["Reviewer 1<br/>MBBS Intern"]
        R2["Reviewer 2<br/>MBBS Intern<br/>(NEEDED)"]
        MD["MD Clinician<br/>Review (NEEDED)"]
        KAP["Cohen's κ<br/>Gate > 0.70<br/>(PENDING)"]
    end

    subgraph EVAL["🧪 EVALUATION (Partial)"]
        PB["Prompt Builder"]
        MA["Model Adapters<br/>Gemini · Groq · Mock"]
        SC["Scorer"]
        FA["Failure Analyzer"]
        RPT["Comparison Report"]
    end

    subgraph API["🌐 API + FRONTEND"]
        FAPI["FastAPI<br/>Routes"]
        DASH["Dashboard<br/>(Basic)"]
    end

    SG --> DRAFT
    FD --> DRAFT
    DRAFT --> NRM
    NRM --> LD --> PII --> AUD --> VAL
    VAL -->|"Valid"| PROC
    VAL -->|"Invalid"| REJ
    PROC --> LS
    LS --> R1 & R2
    R1 & R2 --> MD
    MD --> KAP
    KAP -->|"κ > 0.70"| GOLD
    KAP -->|"κ < 0.70"| LS
    GOLD --> PB
    PB --> MA --> SC --> FA --> RPT
    RPT --> FAPI --> DASH

    style GOLD fill:#1a472a,color:#fff,stroke:#2d6a4f
    style PROC fill:#7b4f00,color:#fff,stroke:#9c6400
    style REJ fill:#6b0000,color:#fff,stroke:#8b0000
    style KAP fill:#1a1a6b,color:#fff,stroke:#2a2a8b
    style R2 fill:#6b0000,color:#fff,stroke:#8b0000
    style MD fill:#6b0000,color:#fff,stroke:#8b0000
```

> **Legend:**
> 🟩 Green = Working & active
> 🟨 Orange = Exists but incomplete
> 🟥 Red = Not yet operational / needed

---

### Future State Architecture

```mermaid
graph TB
    subgraph SOURCES_F["📥 ENRICHED DATA SOURCES"]
        SG_F["🤖 Multi-model Synthetic Gen<br/>Open-weight only"]
        HOSP["🏥 Hospital Partner Data<br/>(MoU + Consent Required)"]
        ASR["🎙️ ASR Speech Input<br/>Indian Accents"]
        COMM["👥 Community Cases<br/>De-identified"]
    end

    subgraph ANNOTATION_F["🏥 FULL 4-TIER ANNOTATION"]
        T1["Tier 1: AI Pre-label"]
        T2["Tier 2: MBBS Intern Review"]
        T3["Tier 3: MD Clinician Review"]
        T4["Tier 4: Senior Specialist<br/>Arbitration (κ < 0.60)"]
        KAP_F["Cohen's κ Gate<br/>> 0.70 required"]
        DVC_F["DVC Dataset Versioning<br/>All versions tracked"]
    end

    subgraph EVAL_F["🧪 FULL EVALUATION SUITE"]
        PB_F["Prompt Builder<br/>(All 9 tasks × 6 langs)"]
        MA_F["10+ Model Adapters<br/>Gemini · MedGemma · Qwen · Llama<br/>Sarvam · Airavata · IndicBART"]
        SC_F["Multi-metric Scorer"]
        FA_F["Failure Analyzer"]
        LB["🏆 HuggingFace<br/>Public Leaderboard"]
    end

    subgraph SAFETY_F["🛡️ FULL SAFETY PIPELINE"]
        PRES["Presidio + Indian PII Rules"]
        GISK["Giskard Red-team Scanning"]
        TRUL["TruLens Trace Grounding"]
        GATE["Release Safety Gate<br/>Fatal Miss Blocker"]
    end

    subgraph OBS_F["📊 OBSERVABILITY"]
        WB["W&B Dashboards"]
        MLFL["MLflow Experiment Tracking"]
        REG["Monthly Automated Regression"]
    end

    subgraph ROUTING_F["🚦 MODEL ROUTING"]
        RT["Routing Table<br/>Task × Language × Model"]
        EXT["External Replication<br/>3 Independent Teams"]
    end

    SOURCES_F --> ANNOTATION_F
    ANNOTATION_F --> EVAL_F
    EVAL_F --> SAFETY_F
    SAFETY_F --> OBS_F
    OBS_F --> ROUTING_F
    ROUTING_F --> LB

    style LB fill:#1a472a,color:#fff
    style GATE fill:#6b0000,color:#fff
    style T4 fill:#1a1a6b,color:#fff
```

---

## 📊 Clinical Tasks & Languages

### 9 Clinical Task Categories

| # | Task | Description | Safety Criticality |
|---|---|---|---|
| 1 | **Triage** | Classify urgency of patient complaints | 🔴 CRITICAL |
| 2 | **Symptom Extraction** | Identify and structure symptoms from free text | 🔴 HIGH |
| 3 | **Medical Counseling** | Provide accurate health guidance | 🟠 HIGH |
| 4 | **Discharge Simplification** | Convert clinical discharge notes to patient language | 🟠 MEDIUM |
| 5 | **Medication Explanation** | Explain prescriptions in lay terms | 🔴 HIGH |
| 6 | **Preventive Care** | Provide prevention and lifestyle advice | 🟡 MEDIUM |
| 7 | **Doctor Note Summarization** | Summarize clinical notes accurately | 🟠 HIGH |
| 8 | **Refusal Behavior** | Appropriately refuse unsafe or out-of-scope requests | 🔴 CRITICAL |
| 9 | **Escalation Detection** | Recognize when to escalate to a human clinician | 🔴 CRITICAL |

### 6 Language Variants

```
┌─────────────────────────────────────────────────────────────────┐
│  PRANIK LANGUAGE COVERAGE                                        │
├──────────────────┬──────────────────────────────────────────────┤
│  Hindi           │  हिंदी — 600M+ speakers                      │
│  Telugu          │  తెలుగు — 95M+ speakers                       │
│  Kannada         │  ಕನ್ನಡ — 60M+ speakers                        │
│  Bengali         │  বাংলা — 250M+ speakers                       │
│  Indian English  │  Localized English patterns                   │
│  Code-Mixed      │  "Mujhe chest pain ho raha hai" ← THE HARD ONE│
└──────────────────┴──────────────────────────────────────────────┘
```

> Code-mixed speech is the most clinically realistic and the hardest for LLMs. Indian patients naturally mix languages mid-sentence. PRANIK specifically benchmarks this.

---

## 🔄 Complete Data Lifecycle

```mermaid
flowchart LR
    A["📝 Raw / Synthetic\nDraft Cases"] 
    --> B["🔧 Preprocessing\nNormalize · Detect · Scrub · Validate"]
    --> C["💾 datasets/processed/\n⚠️ Cleaned, NOT gold truth"]
    --> D["🏷️ Label Studio Upload\nTask creation + reviewer assignment"]
    --> E["👨‍⚕️ Dual Independent\nAnnotation"]
    --> F["📐 Cohen's κ\nComputation"]
    F -->|"κ > 0.70 ✅"| G["🏆 datasets/gold/\nClinician-approved benchmark"]
    F -->|"κ < 0.70 ❌"| H["🔄 Re-review or\nTier 4 Arbitration"]
    H --> E
    G --> I["🧪 Model Evaluation\nPrompt → LLM → Output"]
    --> J["📊 Scoring\nPer-task metrics"]
    --> K["🔍 Failure Analysis\nDangerous miss flagging"]
    --> L["📋 Scorecard\nModel performance summary"]
    --> M["🚦 Routing Decision\nWhich model for which task"]

    style G fill:#1a472a,color:#fff
    style C fill:#7b4f00,color:#fff
    style H fill:#6b0000,color:#fff
```

### Data Store Semantics — DO NOT CONFUSE THESE

```
datasets/synthetic/    ← Raw generated drafts. Not validated. Not reviewed.
datasets/processed/    ← Cleaned and schema-valid. Still NOT clinical truth.
datasets/rejected/     ← Failed preprocessing or validation.
datasets/gold/         ← THE ONLY TRUTH. Clinician-approved + κ > 0.70.
datasets/audit/        ← Immutable audit trail of all pipeline operations.

Label Studio DB        ← Reviewer annotations live HERE before import.
Evaluation results     ← Model outputs. NOT gold labels.
Scorecards             ← Model performance summaries against gold.
```

> ⚠️ **Critical distinction:** `datasets/processed` is clean data. `datasets/gold` is verified data. They are NOT the same. No model should ever be evaluated against processed data.

---

## 🏷️ Annotation Workflow

```mermaid
flowchart TD
    START["💾 Validated Case\n(datasets/processed/)"]
    --> T1["Tier 1: AI Pre-labeling\nSystem generates candidate label\nas annotation hint (not ground truth)"]
    --> UPLOAD["📤 Upload to Label Studio\nTask visible to human reviewers"]
    --> T2A["👩‍⚕️ Reviewer 1\nMBBS Intern\nLabels independently"]
    
    UPLOAD --> T2B["👨‍⚕️ Reviewer 2\nMBBS Intern\nLabels independently\n(REQUIRED for κ)"]

    T2A & T2B --> T3["🏥 Tier 3: MD Clinician\nReviews both labels\nFlags clinical errors"]
    --> IMPORT["⬇️ Import Annotations\nfrom Label Studio API"]
    --> KAPPA["📐 Cohen's κ Calculation\nBetween Reviewer 1 & Reviewer 2"]
    
    KAPPA -->|"κ ≥ 0.70\n✅ High Agreement"| GOLD["🏆 Write to datasets/gold/\nCase is now benchmark truth"]
    KAPPA -->|"0.60 ≤ κ < 0.70\n⚠️ Marginal"| T4["Tier 4: Senior Specialist\nArbitration\n(future)"]
    KAPPA -->|"κ < 0.60\n❌ Low Agreement"| REVISE["🔄 Case Revised\nOr Rejected"]
    
    T4 --> GOLD
    REVISE --> T2A

    style GOLD fill:#1a472a,color:#fff,stroke:#2d6a4f
    style KAPPA fill:#1a1a6b,color:#fff
    style REVISE fill:#6b0000,color:#fff
    style T2B fill:#7b4f00,color:#fff
```

### Annotation Tiers Explained

| Tier | Who | Role | Current Status |
|---|---|---|---|
| **Tier 1** | AI system | Generate candidate labels as hints | ✅ Implemented |
| **Tier 2** | MBBS Interns × 2 | Independent human labeling (both required) | 🔄 1 reviewer active, 2nd needed |
| **Tier 3** | MD Clinician | Clinical QA + error flagging | ❌ Not yet active |
| **Tier 4** | Senior Specialist | Arbitration when reviewers disagree (κ < 0.60) | ❌ Future |

---

## 🧪 Evaluation Workflow

```mermaid
flowchart LR
    GOLD["🏆 Gold Cases\ndatasets/gold/"]
    --> PB["📝 Prompt Builder\nTask-specific prompt\ntemplate + case injection"]
    --> ROUTER["🔀 Model Router\nSelect adapter\nbased on model config"]

    ROUTER --> GEM["Gemini\n(Google)"]
    ROUTER --> MED["MedGemma\n(Google Health)"]
    ROUTER --> QWN["Qwen\n(Alibaba)"]
    ROUTER --> LLA["Llama\n(Meta)"]
    ROUTER --> SAR["Sarvam\n(Indian)"]
    ROUTER --> AIR["Airavata\n(Indian)"]
    ROUTER --> IND["IndicBART\n(AI4Bharat)"]
    ROUTER --> MCK["Mock Adapter\n(Testing)"]

    GEM & MED & QWN & LLA & SAR & AIR & IND & MCK --> RAW["📄 Raw Model Outputs"]
    --> PARSE["🔍 Output Parser\nExtract structured\nanswer from LLM text"]
    --> SCORE["📊 Scorer\nPer-task metric\ncalculation"]
    --> FAIL["⚠️ Failure Analyzer\nFlag dangerous\nmisses + near-misses"]
    --> CLINCSV["📋 Clinician Review CSV\nFor dangerous failures"]
    --> RPT["📈 Comparison Report\nModel × task × language\nheatmap"]
    --> REG["🔁 Regression Check\nDid model get worse\nthis month?"]
    --> GATE["🚦 Safety Gate\nBlock production if\nfatal misses detected"]

    style GOLD fill:#1a472a,color:#fff
    style GATE fill:#6b0000,color:#fff
    style FAIL fill:#7b4f00,color:#fff
```

### Per-Task Metrics

| Task | Primary Metric | Secondary Metrics |
|---|---|---|
| Triage | Weighted F1 (urgency classes) | Sensitivity on high-urgency, False safe rate |
| Symptom Extraction | Entity-level F1 | Recall, Precision |
| Medical Counseling | Clinical accuracy (expert-rated) | Harm score, Refusal appropriateness |
| Discharge Simplification | Readability + factual grounding | Omission rate |
| Medication Explanation | Factual accuracy | Dangerous error rate |
| Preventive Care | Guideline adherence | Harmful advice rate |
| Doctor Note Summarization | ROUGE-L + clinical accuracy | Hallucination rate |
| Refusal Behavior | Refusal precision/recall | False refusal rate |
| Escalation Detection | Recall on escalation triggers | False non-escalation rate |

---

## 🛡️ Safety & Compliance Pipeline

```mermaid
flowchart TD
    INPUT["📥 Raw Case / Model Output"]
    
    INPUT --> PII["🔒 PII Scrubbing\nPresidio + Indian patterns\nAadhaar · phone · name · address"]
    --> LANG["🌐 Language Validation\nDetect declared vs actual language\nFlag mismatches"]
    --> AUDIT["📋 Audit Log Write\nImmutable record of all operations\n(datasets/audit/)"]
    --> SCHEMA["✅ Schema Validation\nPydantic v2 BenchmarkCase\nReject malformed records"]
    --> REF["🚫 Refusal/Escalation Check\nTest unsafe answers against\nknown unsafe answer field"]
    
    REF --> CURRENT{"Current\nSafety Gate"}
    CURRENT -->|"Pass"| PROC2["✅ Allow downstream\nprocessing"]
    CURRENT -->|"Fatal Miss"| BLOCK["🛑 BLOCK\nFlag for clinician review"]
    
    REF --> FUTURE["🔮 FUTURE SAFETY LAYERS"]
    
    subgraph FUTURE_SAFETY["Future Safety Pipeline"]
        GISK2["Giskard Red-team Scan\nAdversarial + edge case testing"]
        TRUL2["TruLens Trace Grounding\nHallucination detection\nground-truth anchoring"]
        PRES2["Full Presidio Pipeline\n+ custom Indian PII rules"]
        MONTH["Monthly Regression\nAutomated safety regression\nagainst previous scores"]
    end

    style BLOCK fill:#6b0000,color:#fff
    style FUTURE fill:#1a1a6b,color:#fff
    style GISK2 fill:#1a1a6b,color:#fff
    style TRUL2 fill:#1a1a6b,color:#fff
```

### Compliance Matrix

| Regulation | Applicability to PRANIK | Current Status |
|---|---|---|
| **DPDP 2025** (Digital Personal Data Protection) | All patient scenario data must be de-identified before use | ✅ PII scrubber active |
| **CDSCO SaMD Class C** | AI systems used in clinical decision pathways require safety validation | 🔄 Architecture aligned, formal process future |
| **ICMR AI Ethics 2023** | Clinical AI systems must have human oversight and transparent evaluation | ✅ 4-tier annotation designed with this in mind |

---

## 📁 Repository Structure

```
pranik/
│
├── 📁 configs/                    # All configuration files
│   ├── app.yaml                   # Application config
│   ├── model_configs/             # Per-model adapter configs
│   ├── safety_config.yaml         # Safety thresholds + rules
│   ├── routing_config.yaml        # Model routing table
│   └── eval_config.yaml           # Evaluation parameters
│
├── 📁 datasets/                   # Data stores (READ THE SEMANTICS)
│   ├── synthetic/                 # Raw draft generated cases
│   ├── processed/                 # Cleaned — NOT gold truth
│   ├── rejected/                  # Failed validation
│   ├── gold/                      # ✅ ONLY source of benchmark truth
│   ├── audit/                     # Immutable audit logs
│   └── metadata/                  # Dataset statistics + provenance
│
├── 📁 schemas/                    # Core data schemas
│   └── benchmark_case.py          # Pydantic v2 BenchmarkCase
│
├── 📁 tasks/                      # Per-task definitions
│   ├── triage/                    # task.md · schema.json · metrics.yaml · guidelines.md
│   ├── symptom_extraction/
│   ├── counseling/
│   ├── discharge_simplification/
│   ├── medication_explanation/
│   ├── preventive_care/
│   ├── doctor_note_summarization/
│   ├── refusal_behavior/
│   └── escalation_detection/
│
├── 📁 synthetic_generation/       # Draft case generation
│   ├── generator.py               # Main generator
│   ├── groq_adapter.py            # Groq LLM adapter
│   └── templates/                 # Per-task generation prompts
│
├── 📁 preprocessing/              # Data cleaning pipeline
│   ├── normalizer.py              # Text normalization
│   ├── language_detector.py       # Language detection
│   ├── pii_scrubber.py            # Presidio + Indian patterns
│   ├── audit_writer.py            # Audit log writer
│   └── validator.py               # Schema validation
│
├── 📁 annotation/                 # Label Studio integration
│   ├── ls_converter.py            # BenchmarkCase → Label Studio task
│   ├── project_creator.py         # Create LS projects
│   ├── uploader.py                # Upload draft cases
│   ├── exporter.py                # Export completed annotations
│   ├── kappa_calculator.py        # Cohen's κ computation
│   └── gold_writer.py             # Write approved cases to gold
│
├── 📁 evaluation/                 # Model evaluation
│   ├── prompt_builder.py          # Task-specific prompt construction
│   ├── local_evaluator.py         # Run evaluation pipeline
│   ├── scorer.py                  # Metric scoring
│   ├── metrics/                   # Per-task metric implementations
│   ├── comparison_report.py       # Cross-model reports
│   ├── failure_analyzer.py        # Dangerous failure detection
│   └── clinician_export.py        # Export dangerous failures to CSV
│
├── 📁 models/                     # Model adapters
│   ├── base_adapter.py            # Abstract adapter interface
│   ├── mock_adapter.py            # Testing adapter
│   ├── gemini_adapter.py          # Google Gemini
│   ├── medgemma_adapter.py        # Google MedGemma
│   ├── groq_adapter.py            # Groq
│   ├── llama_adapter.py           # Meta Llama
│   ├── sarvam_adapter.py          # Sarvam AI (Indian)
│   ├── airavata_adapter.py        # Airavata (Indian)
│   └── indicbart_adapter.py       # AI4Bharat IndicBART
│
├── 📁 deployment/                 # Regression + release pipeline
│   └── regression_pipeline.py     # preprocessing→eval→score→gate
│
├── 📁 api/                        # FastAPI application
│   ├── main.py
│   └── routes/
│       ├── benchmark.py
│       ├── scorecards.py
│       ├── routing.py
│       └── failures.py
│
├── 📁 frontend/                   # Basic dashboard
│   └── index.html
│
├── 📁 safety/                     # Safety scaffolds
│   └── (Giskard/TruLens planned)
│
├── 📁 observability/              # Monitoring
│   └── (W&B / MLflow planned)
│
└── 📁 docs/                       # Documentation
    ├── architecture.md
    ├── benchmark_design.md
    └── compliance.md
```

---

## 🗓️ Roadmap

```mermaid
gantt
    title PRANIK Development Roadmap
    dateFormat  YYYY-MM
    axisFormat  %b %Y

    section 🔴 NOW (Current)
    23 Triage cases in Label Studio    :done, t1, 2025-01, 2025-02
    Engineering foundation             :done, t2, 2025-01, 2025-03
    Synthetic generation pipeline      :done, t3, 2025-02, 2025-03
    Preprocessing + PII scrub          :done, t4, 2025-02, 2025-03
    First annotation pass (1 reviewer) :active, t5, 2025-03, 2025-04

    section 🟡 NEXT (Next 60 days)
    Second independent reviewer        :n1, 2025-04, 2025-04
    Cohen's κ computation active       :n2, 2025-04, 2025-05
    First gold file (triage, 50 cases) :n3, 2025-04, 2025-05
    MD clinician review activation     :n4, 2025-04, 2025-06
    Basic model evaluation on gold     :n5, 2025-05, 2025-06

    section 🔵 LATER (Q3 2025)
    540 draft cases across all tasks   :l1, 2025-06, 2025-08
    All 9 tasks in annotation          :l2, 2025-06, 2025-09
    5+ model adapters active           :l3, 2025-07, 2025-09
    Escalation/refusal gold set        :l4, 2025-07, 2025-09
    Full safety pipeline (Giskard)     :l5, 2025-08, 2025-10
    DVC dataset versioning             :l6, 2025-08, 2025-09

    section 🟢 PRODUCTION (Q4 2025+)
    1000+ gold cases                   :p1, 2025-10, 2026-01
    10+ model evaluations              :p2, 2025-10, 2026-01
    HuggingFace public leaderboard     :p3, 2025-11, 2026-02
    External replication by 3 teams    :p4, 2026-01, 2026-03
    Hospital MoU + real data pipeline  :p5, 2026-01, 2026-06
    Monthly automated regression live  :p6, 2025-12, 2026-01
```

### Milestone Summary Table

| Phase | Goal | Key Deliverable | Blocker |
|---|---|---|---|
| **🔴 NOW** | Triage pilot complete | 23 cases in Label Studio | Second reviewer |
| **🟡 NEXT** | First gold file | 50 triage gold cases, κ verified | MD clinician sign-off |
| **🔵 LATER** | Full draft coverage | 540 cases, 5+ models, safety pipeline | Clinical partnerships |
| **🟢 PRODUCTION** | Public benchmark | 1000+ gold, leaderboard, external replication | Hospital MoUs, DVC |

---

## ⚠️ Honest Gaps & Limitations

> PRANIK is built with integrity. Here is the complete, unvarnished list of what is not done yet.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  WHAT IS NOT DONE YET — HONEST STATUS AS OF THIS COMMIT                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ANNOTATION GAPS                                                         │
│  ❌ Only 1 reviewer has annotated the triage pilot                       │
│  ❌ Need 2 independent reviewers per case for valid Cohen's κ            │
│  ❌ MD clinician review (Tier 3) not yet active                          │
│  ❌ Senior specialist arbitration (Tier 4) not yet built                 │
│  ❌ Zero gold cases exist yet — datasets/gold/ is empty                  │
│  ❌ 23 triage labels ≠ gold. They are a pilot only.                      │
│                                                                          │
│  DATA GAPS                                                               │
│  ❌ Only triage task has been uploaded to Label Studio                   │
│  ❌ All 8 other task types are draft only                                │
│  ❌ No hospital or real patient data (requires MoU + consent)            │
│  ❌ No DVC dataset versioning implemented                                │
│  ❌ Language coverage is uneven across tasks                             │
│                                                                          │
│  MODEL EVALUATION GAPS                                                   │
│  ❌ No model has been evaluated against gold data (none exists yet)       │
│  ❌ Only Gemini + Mock adapters are partially tested                     │
│  ❌ Indian models (Sarvam, Airavata, IndicBART) not yet evaluated         │
│  ❌ No cross-model comparison report has been generated                  │
│                                                                          │
│  SAFETY GAPS                                                             │
│  ❌ Giskard red-team scanning: not integrated                            │
│  ❌ TruLens hallucination tracing: not integrated                        │
│  ❌ Full Presidio pipeline with Indian PII rules: partial                │
│  ❌ ASR robustness testing: future                                       │
│                                                                          │
│  INFRASTRUCTURE GAPS                                                     │
│  ❌ HuggingFace leaderboard: not live                                    │
│  ❌ W&B dashboards: scaffolded, not active                               │
│  ❌ Monthly regression pipeline: not yet running                         │
│  ❌ External replication: 0 of 3 teams enrolled                          │
│  ❌ Docker deployment: not containerized                                 │
│                                                                          │
│  WHAT THIS MEANS                                                         │
│  → PRANIK cannot yet be used to make claims about any LLM's safety       │
│  → No model should be recommended or blocked based on current data       │
│  → The benchmark becomes valid only after gold data + kappa are achieved │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🤔 How Labeling Works (Plain English)

> For clinicians, reviewers, and anyone who has never seen a ML annotation pipeline.

```
┌─────────────────────────────────────────────────────────────────┐
│  WHAT HAPPENS WHEN A REVIEWER LABELS A CASE IN LABEL STUDIO     │
└─────────────────────────────────────────────────────────────────┘

STEP 1: Reviewer logs into Label Studio
        → Opens the "Triage" project
        → Sees a patient scenario in Hindi / Telugu / Code-Mixed etc.
        → Example: "Mujhe 2 din se bukhar hai aur chest mein dard hai"
           (I have had fever for 2 days and chest pain)

STEP 2: Reviewer selects the correct clinical label
        → Example choices: EMERGENCY / URGENT / SEMI-URGENT / NON-URGENT
        → Reviewer adds confidence score + clinical reasoning notes

STEP 3: Reviewer clicks "Submit"
        → Label is saved in Label Studio's own database
        → IT IS NOT YET IN PRANIK'S GOLD DATASET

STEP 4: A second, independent reviewer labels the SAME case
        → They cannot see Reviewer 1's answer (blind review)
        → This is required for Cohen's κ calculation

STEP 5: A PRANIK engineer runs the import command
        → python annotation/exporter.py --project triage
        → This pulls all completed annotations from Label Studio API

STEP 6: The system checks: "Do we have 2 reviewers for this case?"
        → If yes: proceed to kappa
        → If no: case stays in queue

STEP 7: Cohen's κ is calculated
        → κ = (Observed Agreement - Expected Agreement) / (1 - Expected)
        → κ > 0.70 = reviewers substantially agree → APPROVED
        → κ < 0.70 = reviewers disagree → back to review / escalation

STEP 8: Approved cases are written to datasets/gold/
        → NOW it is benchmark data
        → NOW models can be evaluated against it

STEP 9: Every case in datasets/gold/ is immutable
        → Changes require a new version with audit trail
```

---

## 🔭 LLMs Being Evaluated

| Model | Organization | Type | Status |
|---|---|---|---|
| **Gemini 1.5 Pro / Flash** | Google | Proprietary | 🔄 Adapter built |
| **MedGemma** | Google Health | Medical-specialized | 🔄 Adapter built |
| **Qwen 2.5** | Alibaba | Open-weight | 🔄 Adapter built |
| **Llama 3.x** | Meta | Open-weight | 🔄 Adapter built |
| **Sarvam AI** | Sarvam (Indian) | Indic-specialized | 🔄 Adapter built |
| **Airavata** | AI4Bharat | Hindi-specialized | 🔄 Adapter built |
| **IndicBART** | AI4Bharat | Multilingual Indic | 🔄 Adapter built |
| **Groq-hosted models** | Groq | Various | ✅ Active (generation) |
| **Mock Adapter** | PRANIK | Testing only | ✅ Active |
| *Additional models* | TBD | TBD | 📋 Planned |

> Adapter built = code exists. Evaluated = run against gold cases. No model is "evaluated" until gold data exists.

---

## 📏 Key Metrics

### Inter-Annotator Agreement

```
Cohen's κ interpretation:
  κ < 0.00  →  Less than chance agreement
  0.00–0.20 →  Slight agreement
  0.21–0.40 →  Fair agreement
  0.41–0.60 →  Moderate agreement
  0.61–0.80 →  Substantial agreement  ← PRANIK minimum: κ > 0.70
  0.81–1.00 →  Almost perfect agreement

PRANIK enforces: κ > 0.70 before any case enters datasets/gold/
```

### Model Safety Scoring

| Score Category | Weight | Description |
|---|---|---|
| Clinical Accuracy | High | Is the answer medically correct? |
| Harm Rate | Critical | Does the answer cause or risk harm? |
| Unsafe Answer Match | Blocking | Does answer match known unsafe answers? |
| Refusal Precision | High | Does model refuse when it should? |
| Escalation Recall | Critical | Does model escalate emergencies? |
| Language Accuracy | Medium | Is response in the correct language? |
| Code-Mix Handling | Medium | Does model handle mixed language correctly? |

---

## ⚖️ Compliance Framework

```mermaid
graph LR
    DPDP["🔒 DPDP 2025\nDigital Personal Data\nProtection Act"]
    CDSCO["🏥 CDSCO SaMD\nClass C Direction\nMedical AI Devices"]
    ICMR["📋 ICMR AI Ethics\n2023 Guidelines\nClinical AI Standards"]

    DPDP --> P1["All patient scenarios\nmust be de-identified\nbefore processing"]
    DPDP --> P2["PII scrubbing with\naudit trail required"]
    
    CDSCO --> P3["Safety validation\nrequired before\nclinical deployment"]
    CDSCO --> P4["Benchmark results\ndo not constitute\nclinical approval"]
    
    ICMR --> P5["Human oversight\nrequired at every\nevaluation stage"]
    ICMR --> P6["Transparent\nmethodology and\npublic reporting"]

    style DPDP fill:#1a472a,color:#fff
    style CDSCO fill:#1a1a6b,color:#fff
    style ICMR fill:#7b0000,color:#fff
```

> ⚠️ **PRANIK benchmark scores do not constitute CDSCO regulatory clearance. A high PRANIK score does not mean a model is approved for clinical use. It means the model performed well on the PRANIK benchmark.**

---

## 🚀 Getting Started

### Prerequisites

```bash
Python >= 3.11
Label Studio account (local or cloud)
API keys: Groq (for generation), model providers (for evaluation)
```

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/pranik.git
cd pranik

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys and Label Studio credentials
```

### Generate Draft Cases

```bash
# Generate synthetic draft cases (9 tasks × 6 languages)
python synthetic_generation/generator.py \
    --tasks all \
    --languages all \
    --cases-per-task 10

# Output: datasets/synthetic/
```

### Preprocess Cases

```bash
# Run preprocessing pipeline
python preprocessing/pipeline.py \
    --input datasets/synthetic/ \
    --output datasets/processed/

# Output: datasets/processed/ (valid) + datasets/rejected/ (invalid)
```

### Upload to Label Studio

```bash
# Create Label Studio project and upload cases
python annotation/project_creator.py --task triage
python annotation/uploader.py --task triage --input datasets/processed/
```

### Import Annotations & Check Kappa

```bash
# After reviewers complete labeling in Label Studio:
python annotation/exporter.py --project triage
python annotation/kappa_calculator.py --task triage

# If kappa > 0.70:
python annotation/gold_writer.py --task triage
```

### Run Model Evaluation

```bash
# Evaluate a model against gold cases
# (Requires gold data to exist in datasets/gold/)
python evaluation/local_evaluator.py \
    --model gemini \
    --tasks triage \
    --gold datasets/gold/

# Generate comparison report
python evaluation/comparison_report.py --output reports/
```

### Run Regression Pipeline

```bash
# Full regression pipeline
python deployment/regression_pipeline.py
```

---

## 🤝 Contributing & Partnerships

### We are looking for

| Role | What We Need | Contact |
|---|---|---|
| 🏥 MBBS Interns (×5+) | Second reviewer for annotation; independent labeling | See contact below |
| 👨‍⚕️ MD Clinicians (×2+) | Tier 3 clinical QA review | See contact below |
| 🏛️ Hospital Partners | De-identified real case data (MoU required) | See contact below |
| 🔬 External Replication Teams | Validate benchmark methodology independently | See contact below |
| 🌐 Indic Language Experts | Quality check on non-English scenarios | See contact below |

### Annotation Guidelines

Before labeling, all reviewers must read:
- `tasks/{task_name}/guidelines.md` — Clinical labeling guidelines
- `tasks/{task_name}/task.md` — Task definition and scope
- `docs/annotation_protocol.md` — Full annotation protocol

### Pull Request Guidelines

```
✅ DO:
- Add new synthetic templates in tasks/{name}/templates/
- Improve model adapters (open-weight models prioritized)
- Add per-task metric implementations
- Improve PII patterns for Indian data
- Add documentation

❌ DO NOT:
- Push real patient data of any kind
- Modify datasets/gold/ directly (use annotation pipeline only)
- Claim gold status for any data that has not passed κ gate
- Add model adapters that require paid APIs without flag
```

---

## 📬 Contact

<div align="center">

| | |
|---|---|
| **Project** | PRANIK — Indic Healthcare LLM Benchmark |
| **Purpose** | Benchmark and safety evaluation for Indian healthcare AI |
| **Status** | Phase 2 → 3, active development |
| **Clinical Partnerships** | Open for MoU discussions |
| **Annotation Reviewers** | Actively recruiting MBBS interns and MD clinicians |

</div>

---

<div align="center">

### ⚠️ Important Disclaimers

```
PRANIK is a research and evaluation system.
It does not diagnose, treat, or provide medical advice.
It evaluates whether AI systems are safe for clinical use.
Benchmark scores are not CDSCO regulatory clearance.
No model evaluated by PRANIK should be deployed clinically
without independent regulatory and clinical validation.

Gold dataset cases are de-identified and synthetic-first.
Real patient data requires institutional MoU and ethics approval.
```

---

**Built with clinical rigor. Evaluated with scientific honesty. Shared with transparency.**

*PRANIK — Because Indian patients deserve AI that speaks their language, safely.*

<br/>

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:2c5364,50:203a43,100:0f2027&height=100&section=footer" width="100%"/>

</div>
