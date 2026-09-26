# Physics PYQ Extraction Guide (TNPSC GS)

**Source folder**: `Data/physics/` (Nayakan Academy PYQ series)

| ID | PDF | Series topic | Default syllabus topic |
|----|-----|--------------|------------------------|
| phys02 | `(QUN)- (PHYSICS 2 PYQ).pdf` | Topic 79 | Units and Measurements (அளவியல்) |
| phys03 | `(QUN)- (PHYSICS 3 PYQ) (1).pdf` | Topic 80 | Force, Motion and Energy |
| phys04 | `(QUN)- (PHYSICS 4 PYQ).pdf` | Topic 81 | Electricity (மின்னியல்) |
| phys05 | `(QUN)- (PHYSICS 5 PYQ).pdf` | Topic 82 | Magnetism / Light / Sound / Heat / Nuclear (classified per Q) |

**Missing**: `PHYSICS 01` was not in `Data/physics/` when this guide was written. Drop it in and re-run with a new entry in `PHYSICS_PDFS` if it appears.

---

## Extract

```bash
# All PDFs (skips cover page 1)
python3 Physics/transcribe_physics_pyqs.py

# One PDF / page range
python3 Physics/transcribe_physics_pyqs.py --pdf phys03 --start 2 --end 10

# Re-OCR (ignore cache)
python3 Physics/transcribe_physics_pyqs.py --pdf phys02 --force

# QC only
python3 Physics/transcribe_physics_pyqs.py --qc-only
```

**Model / keys**: `gemini-3.1-flash-lite`; pool = `DEFAULT_KEY` + 4× `AQ.` (do not change model without user permission).

**Outputs**
- `Physics/physics_questions_db.json` — `"type": "pyq"`
- `Physics/_tmp_pyq_extract_cache/{pdf_id}_page_XXX.json`
- `Physics/physics_pyq_qc_report.json`

**Notes**
- Pages are bilingual; Tamil in the PDF text layer is often garbled → vision + text hybrid.
- These PDFs usually have **no answer ticks**; the model deduces the correct option from physics.
- Skip Telegram / cover ads automatically.
