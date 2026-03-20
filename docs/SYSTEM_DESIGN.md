# System Design — Resume Shortlister

## Table of Contents
1. [Overview](#overview)
2. [Component Architecture](#component-architecture)
3. [Data Flow](#data-flow)
4. [Data Models](#data-models)
5. [AI Strategy](#ai-strategy)
6. [Scoring Design](#scoring-design)
7. [Error Handling Strategy](#error-handling-strategy)
8. [Scalability Plan](#scalability-plan)
9. [Key Design Decisions](#key-design-decisions)

---

## Overview

Resume Shortlister is a backend pipeline that takes an unstructured resume PDF
and a job description, and produces a structured candidate assessment with
tier classification and a tailored interview plan.

The system is designed around three principles:
- **Explainability** — every score comes with a plain-English reason and evidence
- **Modularity** — each component is independently testable and replaceable
- **Fail-safety** — LLM failures, bad PDFs, and malformed outputs are all handled gracefully

---

## Component Architecture
![Architecture Diagram](High-level_flow_diagram.png)

---

## Data Flow
```
Resume PDF
    │
    ▼
pdfplumber extracts raw text
    │
    ▼
Claude structures text → CandidateProfile (JSON)
    │
    ├── full_name, email, linkedin_url, github_url
    ├── skills[]  (name, level, years)
    ├── experience[]  (company, role, duration, achievements, keywords)
    ├── education[]
    └── total_experience_years, summary, raw_text

Job Description Text
    │
    ▼
Claude structures text → JobDescription (JSON)
    │
    ├── title, company, domain
    ├── required_skills[]  (name, is_mandatory, level, years)
    ├── preferred_skills[]
    ├── responsibilities[]
    └── min_experience_years, raw_text

CandidateProfile + JobDescription
    │
    ▼
ExactMatchScorer  →  DimensionScore (score, explanation, evidence)
                  →  list[SkillMatchDetail]  (per-skill match records)
    │
    ▼ (passes exact match details to avoid double-counting)
SemanticSimilarityScorer  →  DimensionScore
                          →  list[SkillMatchDetail]
    │
AchievementScorer   →  DimensionScore
OwnershipScorer     →  DimensionScore
    │
    ▼
ScoringEngine aggregates  →  ScoringResult
    │
    ├── overall_score  (weighted average)
    ├── exact_match, semantic_similarity, achievement, ownership
    ├── skill_matches[]  (full per-skill audit trail)
    ├── strengths[]
    └── gaps[]

ScoringResult
    │
    ▼
TierClassifier  →  TierClassification
    │
    ├── tier  (A / B / C)
    ├── decision_label
    ├── reasoning
    ├── recommended_action
    ├── focus_areas[]
    └── scoring_result  (embedded for full auditability)

TierClassification + CandidateProfile
    │
    ▼
QuestionGenerator  →  InterviewPlan
    │
    ├── interviewer_briefing
    ├── questions[]
    │     ├── question
    │     ├── rationale
    │     ├── dimension  (technical_depth / skill_gap / ownership / achievement)
    │     ├── difficulty  (easy / medium / hard)
    │     └── follow_up
    ├── red_flags[]
    ├── green_flags[]
    └── recommended_duration_minutes
```

---

## Data Models

All data contracts are defined as Pydantic models in `src/models/`.
Every function in the system uses these types — no raw dicts cross
component boundaries.
```
enums.py
   ├── Tier              (A, B, C)
   ├── MatchType         (exact, semantic, partial, none)
   ├── SkillLevel        (beginner, intermediate, advanced, unknown)
   └── ScoreDimension    (exact_match, semantic_similarity, achievement, ownership)

candidate.py
   ├── CandidateSkill    (name, level, years)
   ├── Experience        (company, role, duration, description, achievements, keywords)
   ├── Education         (institution, degree, field, year)
   └── CandidateProfile  (identity + skills + experience + education + raw_text)

job.py
   ├── RequiredSkill     (name, is_mandatory, minimum_level, minimum_years)
   └── JobDescription    (title + required_skills + preferred_skills + responsibilities)

scoring.py
   ├── SkillMatchDetail  (jd_skill, candidate_skill, match_type, explanation)
   ├── DimensionScore    (dimension, score, explanation, evidence[])
   └── ScoringResult     (4 x DimensionScore + overall_score + skill_matches + strengths + gaps)

tier.py
   ├── TierThresholds    (tier_a_min, tier_b_min)
   └── TierClassification (tier + reasoning + focus_areas + scoring_result)

interview.py
   ├── InterviewQuestion (question + rationale + dimension + difficulty + follow_up)
   └── InterviewPlan     (briefing + 5–8 questions + red_flags + green_flags)
```

### Dependency order
```
enums.py
    ↑
candidate.py    job.py
         ↑     ↑
         scoring.py
              ↑
            tier.py
              ↑
          interview.py
```

---

## AI Strategy

### Model used
All LLM tasks use `claude-sonnet-4-20250514` via the Anthropic API.

### Task assignment

| Task | Approach | Reasoning |
|---|---|---|
| Resume → CandidateProfile | Claude | Resumes have no standard format — rule-based parsing fails on real-world variety |
| JD → JobDescription | Claude | Same — JD formats vary wildly across companies |
| Exact Match Score | Pure Python (set intersection) | Deterministic, fast, free, no LLM needed |
| Semantic Similarity Score | Claude | Requires reasoning about technology equivalence |
| Achievement Score | Claude | Requires understanding quantified impact in natural language |
| Ownership Score | Claude | Requires detecting language nuance — "led" vs "assisted" |
| Interview Questions | Claude | Requires synthesising profile + gaps into contextual questions |

### Semantic similarity approach

**Chosen: LLM-based reasoning (Claude)**
**Rejected: Embedding-based (vector similarity)**

Reasons:
- Embeddings require a vector database and embedding model infrastructure
- Cosine similarity gives a number — not an explanation
- Claude can reason: "RabbitMQ is similar to Kafka but lacks log compaction,
  which matters in a data pipeline role" — this is the explainability the system needs
- For this scale (single candidate at a time), LLM latency is acceptable

### How tech equivalences are handled

The semantic similarity scorer sends all unmatched JD skills and all candidate
skills to Claude with the job domain as context. Claude returns a `match_type`
per JD skill:

- `exact` — identical or trivially same ("JS" == "JavaScript")
- `semantic` — functionally equivalent ("Kafka" ~ "RabbitMQ")
- `partial` — adjacent but not equivalent ("SQL" for "PostgreSQL")
- `none` — no relevant match

Mandatory skills are weighted 1.5x in the semantic score average.
The exact match scorer runs first and passes matched skills to the semantic scorer
so no skill is double-counted.

---

## Scoring Design

### Four dimensions

| Dimension | Weight | What it measures |
|---|---|---|
| Exact Match | 30% | Literal keyword overlap with JD requirements |
| Semantic Similarity | 30% | Functional technology equivalence |
| Achievement | 20% | Quantified, measurable impact in work history |
| Ownership | 20% | Leadership and decision-making signals in language |

### Score computation
```
overall_score = (exact    × 0.30)
              + (semantic × 0.30)
              + (achievement × 0.20)
              + (ownership  × 0.20)
```

Weights are configurable in `src/config.py` and must sum to 1.0.
Validated at startup by `Config.validate()`.

### Tier thresholds

| Score | Tier | Label |
|---|---|---|
| ≥ 80 | A | Fast-track to final round |
| 55–79 | B | Proceed to technical screen |
| < 55 | C | Needs further evaluation |

Thresholds are configurable per-call via `TierThresholds` model.
This allows different thresholds for senior vs junior roles without
changing global config.

### Explainability

Every `DimensionScore` carries:
- `score` — numeric value 0–100
- `explanation` — why this score was given (sentence)
- `evidence` — direct quotes or paraphrases from the resume

Every `SkillMatchDetail` carries:
- `match_type` — exact / semantic / partial / none
- `explanation` — why the match was or was not made

This means every number in the output has a traceable reason.

---

## Error Handling Strategy

| Layer | Failure | Handling |
|---|---|---|
| PDF Parser | Scanned / image PDF | Raises `ValueError` with clear message |
| PDF Parser | File not found | Raises `FileNotFoundError` |
| LLM Client | Rate limit | Retries with exponential backoff (3 attempts) |
| LLM Client | Timeout | Retries with exponential backoff |
| LLM Client | 4xx API error | Fails immediately — retrying a bad request wastes budget |
| LLM Client | JSON parse failure | Raises `ValueError` with first 500 chars of raw response |
| Resume Extractor | Malformed skill entry | Skips silently, continues with rest of profile |
| Resume Extractor | Malformed experience entry | Skips silently, continues |
| Scorers | Empty experience list | Returns zero score with explanation — does not crash |
| Scorers | Claude returns out-of-range score | Clamped to 0–100 |
| Question Generator | Fewer than 5 questions returned | Raises `ValueError` |
| Question Generator | Invalid dimension/difficulty | Snapped to valid default |
| Config | Missing API key | Raises `EnvironmentError` at startup |
| Config | Weights don't sum to 1.0 | Raises `ValueError` at startup |

The design principle is: **fail fast at startup, fail gracefully at runtime**.
Config problems are caught before any resume is processed.
Malformed LLM outputs for individual fields are handled without crashing the pipeline.

---

## Scalability Plan

The current implementation is synchronous and single-candidate.
Here is how it would be extended for production:

### Short term — caching
```
JD text  →  hash(JD text)  →  cache lookup
                               hit  → return cached JobDescription
                               miss → LLM call → store in cache
```

The same JD is parsed once regardless of how many resumes are screened against it.

### Medium term — async batch processing
```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│  API / UI    │────▶│  Task Queue  │────▶│  Worker Pool     │
│  (FastAPI)   │     │  (Redis)     │     │  (Celery)        │
└──────────────┘     └──────────────┘     │  N workers       │
                                          │  each runs the   │
                                          │  full pipeline   │
                                          └──────────────────┘
```

Each resume becomes a task on the queue.
Workers process tasks in parallel.
Results are stored and retrieved asynchronously.

### Long term — score calibration

Recruiter accept/reject decisions are logged per candidate.
Dimension weights are re-optimised periodically based on hiring outcomes.
This closes the feedback loop between the scoring model and real-world results.

---

## Key Design Decisions

### 1. Separate LLM calls per dimension vs. one large prompt
**Decision:** 4 separate calls
**Reason:** Each scorer is independently testable, produces cleaner structured
output, and is easier to debug. A single large prompt produces entangled outputs
that are harder to parse and harder to attribute errors to.

### 2. Manual model construction vs. `Model(**raw_json)`
**Decision:** Manual field-by-field construction in all extractors
**Reason:** Direct Pydantic unpacking crashes on any unexpected field from Claude.
Manual construction gives per-field fallbacks and clear error attribution.

### 3. ExactMatch runs before SemanticSimilarity
**Decision:** ExactMatch results are passed to SemanticSimilarity
**Reason:** Prevents double-counting. If "Python" is already an exact match,
the semantic scorer doesn't re-evaluate it. The two scorers are additive and
non-overlapping.

### 4. Prompts as separate files vs. inline strings
**Decision:** All prompts in `src/llm/prompts/`
**Reason:** Prompts are code. Separate files make them reviewable, versionable,
and iterable independently from the scorer logic.

### 5. Singleton pattern for all major components
**Decision:** `scoring_engine`, `llm_client`, `pdf_parser` etc. are singletons
**Reason:** Simple and predictable for a single-process system. For multi-worker
deployment, these would be replaced with connection pools and stateless functions.
