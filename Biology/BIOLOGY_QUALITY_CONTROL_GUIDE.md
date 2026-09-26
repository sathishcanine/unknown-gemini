# Biology Quality Control Guide (TNPSC GS)

For **the User** and **future AI Agents**. Run this after every Biology practice-batch generation (and before importing to prod).

**Companion guides**
- `Biology/BIOLOGY_BATCH_GENERATION_GUIDE.md` — how to generate batches
- `Biology/BIOLOGY_FACT_EXTRACTION_GUIDE.md` — how to extract facts

**Database**: `Biology/biology_questions_db.json`  
**Subject**: `"Biology"` · **Difficulty**: all `"Medium"` · **Batch size**: exactly **25**

---

## 1. When to Run QC

1. After generating Batch 1 / 2 / 3 for any Biology topic.
2. After a bulk multi-topic generation.
3. After Biology PYQ transcription (`transcribe_biology_pyqs.py` / `--qc-only`).
4. Anytime the user says “double-check”, “quality”, or “audit Biology”.

**Do not ship / import to Postgres until QC passes.**

---

## 2. User Prompt (copy-paste)

> Run Biology QC on `Biology/biology_questions_db.json` using `Biology/BIOLOGY_QUALITY_CONTROL_GUIDE.md`.
> 1. Audit all questions for the hard-fail list below.
> 2. Delete broken / duplicate items.
> 3. Top up every short batch back to **25**.
> 4. Re-audit until zero hard fails (ignore the false-positive exceptions).
> 5. Report deleted counts + final per-topic batch sizes.

---

## 3. Pre-QC Snapshot

```bash
python3 -c "
import json
from collections import Counter
db=json.load(open('Biology/biology_questions_db.json'))
print('total', len(db))
print('difficulty', Counter(q.get('difficulty') for q in db))
c=Counter((q.get('topic'), q.get('batch')) for q in db)
shorts=[(k,n) for k,n in c.items() if n!=25]
print('non-25 batches', shorts or 'none')
"
```

---

## 4. Hard-Fail Checklist (DELETE these)

Strip HTML before stem checks (`<br>`, `match-container`, etc.).

| Code | Fail if |
|------|---------|
| `missing_options` | Fewer than 4 of A–D |
| `missing_option_E` | No Option E (`Answer not known` / `விடை தெரியவில்லை`) |
| `bad_correct` | `correct_option` not in A–D or not present in options |
| `empty_option` | Any A–D `text_en` empty |
| `duplicate_options` | Two A–D English options normalize equal |
| `stem_too_short` | Plain stem &lt; ~15 chars |
| `missing_tamil_stem` | `question_ta` missing / &lt; ~8 chars |
| `missing_tamil_opts` | ≥2 of A–D Tamil options empty **and** English is real prose (not numbers/acronyms — see §6) |
| `untranslated_options` | ≥3 A–D options have `text_en == text_ta` with Latin words **and** are not acronyms/numbers (§6) |
| `match_incomplete` / `match_not_4x4` | Match Q without 4 left (`a)–d)`) **and** 4 right (`1.–4.`) items (HTML `match-container` OK if both columns have 4) |
| `match_bad_options` | Match Q whose options are not code/combo style (`a-2, b-1…`) |
| `statements_missing` | Options are `1 only` / `1, 2 only` / `All the above` style **but** stem has &lt;2 numbered statements |
| `assertion_thin` / `reason_thin` | Assertion–Reason stem without substantive (A) and (R) bodies |
| `placeholder` | Contains TODO / placeholder / lorem / xxx |
| `thin_explanation` | English explanation &lt; ~25 chars |
| `near_duplicate` / `exact_duplicate` | Same topic + near-identical stem (keep the longer explanation; delete the other) |

### Also delete
- Questions **not grounded** in `biology_facts.json` (invented scientists/years/ATP counts).
- Any leftover **Hard/Easy** labels — either retag to Medium (if content OK) or regenerate.

---

## 5. Soft Warnings (fix or regenerate if easy; don’t bulk-delete blindly)

* Very short definition stems (“What is a bio-chip?”) **with** strong options → usually keep.
* Slight wording overlap across batches on the same fact → keep if stems differ meaningfully.
* Match options using `A-2, B-1` vs `a-2, b-1` → keep (normalize later if needed).

---

## 6. False-Positive Exceptions (DO NOT delete)

These often look “broken” to naive regex but are **valid TNPSC**:

1. **Numeric options** (`2`, `4`, `38`, `2 ATP`) — Tamil may equal English.
2. **Acronym / scheme codes** (`NFCP`, `NLEP`, `BCG`, `DNA`, `ATP`) — often identical in TA.
3. **Direct “how many / what number” MCQs** with single-number options — **not** `statements_missing` (only flag when options are `1 only` / `1, 2 only` combo style **without** listed statements).
4. **Year options** (`1935`, `1900`) as answers to “in which year…” — valid.

---

## 7. QC Workflow (Agent Steps)

### Step A — Audit
Run a Python audit over `biology_questions_db.json` implementing §4–§6.  
Write a report to `Biology/biology_qa_issues.json` (`count`, `issues[]` with topic/batch/reasons/stem).

### Step B — Delete
Remove hard-fail questions. Prefer identity by `question_en` (stable) or index.  
Log deletes to `Biology/biology_deleted_qa.json` (counts by topic/batch).

### Step C — Measure holes
For every `(topic, batch)` with count ≠ 25, record `need = 25 - n`.

### Step D — Regenerate / top up
```bash
python3 Biology/generate_biology_questions.py --topic "TOPIC_NAME" --batch N
```
* Generator already filters TNPSC-valid facts + exclusions.
* Re-run until batch size ≥ 25, then **trim** to exactly 25 (keep longest explanations).
* Model / keys: follow project lock (do **not** change model without user permission). Current Biology default: `gemini-3.1-flash-lite`; key pool: `DEFAULT_KEY` + 4× `AQ.` keys.

### Step E — Re-audit
Repeat Step A until hard fails = 0 (except §6 false positives). Confirm every batch is exactly 25 and difficulty is Medium.

### Step F — Report to user
```
Deleted: N (reasons…)
Topped up: list of topic/batch
Final DB total: …
Per topic: [25,25,25] or [25,25]
```

---

## 8. Batch Integrity Rules

* Every practice batch label (`Batch 1`, `Batch 2`, `Batch 3`) must have **exactly 25** questions after QC.
* Topics with only 2 batches (thin fact pools) stay at 2×25 — do **not** invent a weak Batch 3.
* Never leave a batch at 6–24 after deletes; always top up or drop the whole batch and regenerate.

---

## 9. Fact-Side QC (before generation)

When reviewing `biology_facts.json` for a topic:

**Keep (TNPSC-standard)**
* Scientists + years, organelles, hormones, pathogens, enzymes, pathways, chromosome/ATP numbers, schemes/acts, crisp definitions.

**Drop / don’t generate from**
* Vague hierarchy fluff (“organs are made of tissues…”).
* “Various / many types / important…” with no entity.
* Watermark / copyright / telegram chrome.

The generator’s `filter_tnpsc_facts()` implements this; keep that filter aligned with this guide.

---

## 10. Import Gate (prod)

Only after QC:

1. Confirm `biology_questions_db.json` totals and 25/batch.
2. Import into Postgres (`subject_id` / topic mapping per app conventions).
3. Rebatch on server if needed so last batch &lt; 25 is OK only for non-practice legacy — for Biology practice, force 25.

---

## 11. Quick Regression Commands

```bash
# counts
python3 -c "import json;from collections import Counter;db=json.load(open('Biology/biology_questions_db.json'));print(len(db));print(Counter((q['topic'],q['batch']) for q in db))"

# regenerate one batch
python3 Biology/generate_biology_questions.py --topic "Respiration" --batch 3
```

---

## 12. Change Log Notes for Agents

* 2026-09: First QC pass on TN-govt Biology bank — deleted ~17 (dupes / Tamil / match), topped up to **825** Qs (9 topics × 3 batches + 3 topics × 2 batches).
* Always prefer **delete + regenerate** over silent option rewriting, unless the user asks for an in-place Tamil fill.
