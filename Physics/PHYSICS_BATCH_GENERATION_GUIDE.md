# Physics MCQ Batch Generation Guide (TNPSC GS)

Adapted from `Biology/BIOLOGY_BATCH_GENERATION_GUIDE.md`.

**Companion guide**
- `Physics/PHYSICS_FACT_EXTRACTION_GUIDE.md` — source-book fact extraction.

**Sources**
- Facts: `Physics/physics_facts.json`
- TNPSC orientation bank: Physics entries with `"type": "pyq"` in `Physics/physics_questions_db.json`

## Topics

| # | Topic | Status |
|---|-------|--------|
| 1 | Universe (பேரண்டம்) | Facts extracted; 3 batches generated |
| 2 | Laws of Physics (பொது அறிவியல் விதிகள்) | 110 facts; 3 batches generated |
| 3 | Scientific Instruments (அறிவியல் கருவிகள்) | 72 facts; 3 batches generated |
| 4 | Discoveries and National Scientific Laboratories | 151 facts extracted; 3 batches generated |
| 5 | Mechanics and Properties of Matter (இயந்திரவியல் மற்றும் பருப்பொருளின் பண்புகள்) | 52 facts; 2 batches generated |
| 6 | Physical Quantities, Standards and Units | 184 facts; 3 batches generated |
| 7 | Force, Motion and Energy (விசை, இயக்கம் மற்றும் ஆற்றல்) | pending |

Add later topics only after their facts pass extraction QC.

---

## Mandatory Generation Rules

### Rule 1: Facts Are the Only Source of Truth
- Every answer, statement, number, year, scientist and explanation must be supported by the selected topic’s entries in `physics_facts.json`.
- Store the supporting English fact verbatim in `source_fact`.
- Do not add outside astronomy or physics knowledge.
- Do not silently update old source-book values.

### Rule 2: Mandatory TNPSC Orientation from Physics PYQs
- Before generating a batch, load all Physics questions with `"type": "pyq"` from `physics_questions_db.json`.
- Use those PYQs to learn **TNPSC question orientation only**:
  - stem length and wording;
  - direct-fact, statement-combination, assertion–reason and match styles;
  - distractor closeness;
  - bilingual option phrasing;
  - numerical and conceptual emphasis.
- PYQs are **not** an additional factual source. A PYQ fact may be used only when the same fact exists in the selected topic’s `physics_facts.json`.
- Never copy a PYQ stem verbatim. Generate a new question from the selected topic facts in the same TNPSC orientation.
- Pass existing practice stems as strict exclusions so batches do not repeat one another.

### Rule 3: Batch Structure
- Exactly **25 questions per batch**.
- Generate **3 batches** when the topic has at least 70 good facts.
- Generate **2 batches** when a topic has 45–69 good facts and the source does
  not support 70 non-duplicate facts.
- All questions must have difficulty exactly `"Medium"`.
- **Preferred workflow:** `--all-batches` makes **one LLM call per planned batch**
  (2 or 3 calls total), with optional **one top-up call per batch** only if local
  QC finds format shortages. Do not use the legacy per-batch retry loop unless
  recovering a partial topic.

### Rule 4: TNPSC-Oriented Format Mix
Each final 25-question batch must contain exactly:
- Direct factual/numerical MCQ: 8
- Statement evaluation: 7
- Assertion and Reason: 3
- Match the following: 3
- Paragraph/inference or applied context: 4

At least 4 questions in each batch must also be marked `contextual: true`.

### Rule 5: Match and Statement Integrity
- Match questions must be strict **4×4**:
  ```html
  Match the following:<br><div class='match-container'><div class='match-col-left'>a) Item A<br>b) Item B<br>c) Item C<br>d) Item D</div><div class='match-col-right'>1. Match 1<br>2. Match 2<br>3. Match 3<br>4. Match 4</div></div>
  ```
- Match options must be complete codes such as `a-2, b-1, c-4, d-3`.
- Every A–D match option must itself be a valid 4×4 bijection: it must use each
  left label `a`–`d` and each right label `1`–`4` exactly once.
- Every match must be a true one-to-one mapping: each left item has exactly one
  unambiguous right-side association. Do not use overlapping roles or descriptions.
- Statement questions require 2–4 visible numbered statements and combination options.
- Assertion–Reason questions require the standard four A–D logical alternatives.

### Rule 6: Distractors
- Wrong options must be plausible and from the same conceptual neighborhood.
- Use nearby source values, related scientists, adjacent planets, theories or units.
- Avoid joke options, obvious category mismatches and unsupported invented facts.

### Rule 7: Bilingual Schema
- Complete English and Tamil Unicode stems, options and explanations.
- Exactly A–D content options plus:
  - E: `Answer not known`
  - E Tamil: `விடை தெரியவில்லை`
- `correct_option` must be A–D.
- Shuffle candidates once before saving.

### Rule 8: Zero Duplication
- Do not repeat English stems within a batch or across practice batches.
- Do not copy PYQ stems.
- Distinct questions may test the same rich fact only through genuinely different reasoning, not paraphrase duplication.
- Reordering the same match columns or options does not create a new question.

### Rule 9: Answer-Position and Prompt Quality
- Across each 25-question batch, distribute correct answers across A–D; each
  position must occur at least 4 times and no more than 8 times.
- Do not place every question of one format (for example, every match question)
  at the same answer position.
- Every statement-combination question must end with an explicit instruction
  asking which statements are correct.
- Assertion–Reason keys must reflect both truth values and whether the reason
  actually explains the assertion.

---

## Pre-Generation Guardrail
1. Topic facts are non-empty and fact QC has zero hard issues.
2. Physics PYQ bank exists and is non-empty.
3. For three batches, prefer at least 70 facts.
4. Existing practice questions for the topic are loaded as exclusions.

If facts or PYQs are missing, stop generation.

## Deterministic QC Contract
- Every generated topic must contain exactly 75 practice questions:
  exactly 25 in each of Batch 1, Batch 2, and Batch 3.
- Every stored `source_fact` must exactly equal a verbatim English `fact_en`
  entry; normalized or approximate matches do not pass QC.
- Empty or missing expected batches fail QC.
- Every bilingual stem, option, and explanation must be non-empty; Tamil stems
  and explanations must contain Tamil Unicode.
- Option E must be exactly `Answer not known` / `விடை தெரியவில்லை`.
- Statement numbering may use either `1.` or `1)` style.
- QC validates deterministic structure and source membership. It does not claim
  to validate semantic truth or English–Tamil equivalence.

## Command
```bash
# Preferred: one LLM call per planned batch (2 or 3 calls, no retry loop)
python3 Physics/generate_physics_questions.py \
  --topic "Force, Motion and Energy" --all-batches --reset-topic-practice

# Structural QC for the whole Physics practice bank
python3 Physics/generate_physics_questions.py --qc-only
```

Legacy per-batch mode (avoid unless recovering a partial topic):
```bash
python3 Physics/generate_physics_questions.py --topic Universe --batch 1
python3 Physics/generate_physics_questions.py --topic Universe --batch 2
python3 Physics/generate_physics_questions.py --topic Universe --batch 3
```

## Database
- Facts: `Physics/physics_facts.json`
- Questions: `Physics/physics_questions_db.json`
- Subject: `"Physics"`
- Types: `"pyq"` and `"practice"`

