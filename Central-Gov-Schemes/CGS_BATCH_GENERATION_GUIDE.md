# Central Government Schemes — Batch Generation Guide

Subject: **Central Government Schemes** / **மத்திய அரசுத் திட்டங்கள்**

---

## Structure

* **Topic** = Ministry (e.g. Ministry of Agriculture & Farmers Welfare)
* **Practice** = Batch 1 / Batch 2 (30 questions each), mixing all schemes under that ministry
* Schemes are **not** separate syllabus topics

---

## Rules

1. **Source of truth**: Only `cgs_facts.json` for that topic. Do not invent schemes/dates not in facts.
2. **Full fact pool**: Use the entire topic fact list for every batch (no slicing).
3. **Zero duplicates**: Exclude all existing `question_en` for that topic.
4. **Batch size**: Generate ~32 (18 Medium + 14 Hard), prune to exactly **30**.
5. **Difficulty**: ~17 Medium / 13 Hard (flexible 18/12, 16/14, 15/15).
6. **Formats** (mix per batch):
   * Statement-evaluation
   * Assertion & Reason
   * Match-the-following (strict **4×4** HTML `match-container`)
   * Paragraph inference / scheme-connect questions
7. **Option E** on every question: Answer not known / விடை தெரியவில்லை
8. **Bilingual** question, options, explanation
9. Set `"batch": "Batch 1"` (or Batch 2) and `"source_exam": "Practice - Batch 1"`

---

## Files

* Facts: `Central-Gov-Schemes/cgs_facts.json`
* Questions: `Central-Gov-Schemes/cgs_questions_db.json`
* Script: `Central-Gov-Schemes/generate_cgs_batch.py`

```bash
python3 Central-Gov-Schemes/generate_cgs_batch.py \
  --topic "Ministry of Agriculture & Farmers Welfare" \
  --batches 1 2
```
