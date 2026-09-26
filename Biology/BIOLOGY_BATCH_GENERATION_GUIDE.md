# Biology MCQ Batch Generation Guide (TNPSC GS)

**Companion guides**
- `Biology/BIOLOGY_FACT_EXTRACTION_GUIDE.md` — fact extraction from TN govt PDF
- `Biology/BIOLOGY_QUALITY_CONTROL_GUIDE.md` — **mandatory QC** after every batch generation (delete broken / top up to 25)

**Source PDF**: `Data/Biology/Biology tn govt eng.pdf` (TN Employment & Training — English Unicode text).

| # | Topic (EN) | PDF pages (approx) |
|---|------------|---------------------|
| 1 | The Cell — Basic Unit of Life | 40–60 |
| 2 | Classification of Living Organisms | 1–39 |
| 3 | Nutrition and Food Habits | 129–137 |
| 4 | Respiration | 61–71 |
| 5 | Blood and Circulation | 72–91 |
| 6 | Endocrine System | 92–103 |
| 7 | Reproductive System | 104–116 |
| 8 | Genetics — Mendelism | 117–128 |
| 9 | Environment and Organism Life | 163–206 |
| 10 | Biodiversity and Conservation | 155–162 |
| 11 | Human Diseases — Prevention and Control | 138–147 |
| 12 | Alcoholism and Drug Addiction | 148–154 (Health; no dedicated alcohol chapter) |

Topics 1–4 are **Botany**; 5–12 are mostly **Zoology** / applied biology.

---

## 3. Generation Rules for the AI Agent

### Rule 1: Source of Truth
* Learn facts **only** from `biology_facts.json` (extracted from `Biology tn govt eng.pdf`).
* Do **not** invent organs, enzymes, years, scientists, or disease names not present in the facts.

### Rule 2: Complete Pool Analysis, TNPSC Fact Filter & Zero Duplicates
* Load facts for the topic from `biology_facts.json`, then **keep only TNPSC-standard facts** (scientists/years, organelles, processes, pathogens, hormones, schemes, concrete definitions). Drop vague hierarchy fluff (“organs are made of tissues…”).
* For every batch, use that **filtered full pool** (no slicing).
* Load all existing questions for the topic from `biology_questions_db.json` and pass English stems as a strict exclusion list.
* **Batch count**: Prefer **3** batches of 25 if filtered facts ≥ ~70; otherwise **2** batches (short topics). Thin topics may get 2 with denser reuse of formats.

### Rule 3: Batch Structure
* **Final count**: Exactly **25** questions.
* **Difficulty**: **All Medium** — do not generate Hard / Easy splits.
* **Over-provision**: Generate **28 Medium** candidates, score by `len(question_en) + len(explanation)`, then select the best **25**.

### Rule 4: Plausible Distractors
* Wrong options must be closely related biology (adjacent organelles, similar enzymes, related diseases, nearby taxonomic ranks, realistic percentages).

### Rule 5: Advanced Formats (every 25-Q batch)
1. **Paragraph-Based Inference (Min 4)**: 2–3 sentence data-rich premise; options use logical qualifiers (*only*, *more than*, *less than*).
2. **Contextual Connect (Min 3)**: Core biology hooked to modern context (WHO campaigns, recent Nobel work when grounded in facts, TNPSC CA-style environment/health schemes **only if present in facts** — otherwise hook to applied human physiology / agriculture contexts from the material).

### Rule 6: Patterns Mix
* **Statement-Evaluation** (~30–40%): 2–4 numbered statements → "1 and 2 only" style options.
* **Match the Following** (~15–20%): **Strict 4×4** HTML layout only:
  ```html
  Match the following:<br><div class='match-container'><div class='match-col-left'>a) Item A<br>b) Item B<br>c) Item C<br>d) Item D</div><div class='match-col-right'>1. Match 1<br>2. Match 2<br>3. Match 3<br>4. Match 4</div></div>
  ```
  Options like `a-2, b-1, c-4, d-3`.
* **Assertion & Reason** (~15–20%): Standard A/R five-option set including Option E.
* **Direct MCQ** (~20–30%).

### Rule 7: Formatting
* Every question bilingual (EN + TA).
* Every question includes Option E: `"Answer not known"` / `"விடை தெரியவில்லை"`.
* Shuffle once before saving.

### Rule 8: Fact Source
* Facts come from `Biology tn govt eng.pdf` via text extraction (`extract_biology_facts.py`). Do not invent facts outside the filtered pool.

---

## 4. Pre-Generation Check (Guardrail)

Before generating any practice batch:

1. **Facts exist** for the topic in `Biology/biology_facts.json` (non-empty list).
2. Prefer **≥ 40 facts** before Batch 1 (short chapters may have fewer — proceed only if user confirms).

**If facts are missing, DO NOT GENERATE.** Stop and report.

---

## 5. Database Location
* **Facts**: `Biology/biology_facts.json`
* **Questions DB**: `Biology/biology_questions_db.json`
* **Subject key**: `"Biology"`
* **Types**: `"practice"` (batches) and `"pyq"` (from official papers)
* **Generator**: `python3 Biology/generate_biology_questions.py --topic "The Cell — Basic Unit of Life" --batch 1`
* **Extractor**: `python3 Biology/extract_biology_facts.py --topic "The Cell — Basic Unit of Life"`
* **PYQ transcription**: `python3 Biology/transcribe_biology_pyqs.py` (source: `Data/Biology/BIOLOGY PYQ PDF 2020 -2025.pdf`, page cache in `Biology/_tmp_pyq_extract_cache/`)
* **PYQ QC**: `python3 Biology/transcribe_biology_pyqs.py --qc-only` → `Biology/biology_pyq_qc_report.json`
* **QC (required after generate)**: follow `Biology/BIOLOGY_QUALITY_CONTROL_GUIDE.md`
