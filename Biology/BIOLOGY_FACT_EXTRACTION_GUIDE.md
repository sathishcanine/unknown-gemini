# Biology Fact Extraction Guide

## Source (current)
- PDF: `Data/Biology/Biology tn govt eng.pdf`
- Publisher: Government of Tamil Nadu — Department of Employment and Training (TNPSC Group II)
- Language: **English Unicode** — use page **text** extraction (not Bamini vision).
- Strip `t.me/tnpscfree` watermarks and copyright cover pages.

## Legacy (do not use for new extracts)
- `Data/Biology/STUDY MATERIAL - BIOLOGY (TAMIL).pdf` — Bamini Tamil Race Academy notes.

## Syllabus Topics (user TOC) ↔ PDF ranges
See `topics_mapping` in `Biology/extract_biology_facts.py`.

| # | Topic | PDF pages (approx) |
|---|-------|--------------------|
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
| 12 | Alcoholism and Drug Addiction | 148–154 (Health & Hygiene — thin / no dedicated alcohol chapter) |

## Method
1. One topic at a time.
2. Clean text → Gemini extract → bilingual facts → dedupe → `biology_facts.json`.
3. Model/keys: follow project lock (`gemini-2.5-flash`, DEFAULT + 4× AQ unless user changes).

## Commands
```bash
python3 Biology/extract_biology_facts.py --topic "The Cell — Basic Unit of Life" --force
python3 Biology/extract_biology_facts.py --topic "Classification of Living Organisms" --force
```

## Fact Shape
```json
{
  "fact_en": "...",
  "fact_ta": "...",
  "source": "Biology TN Govt Eng (Employment & Training) Page N",
  "context_en": "Cell biology",
  "context_ta": "செல்லியல்"
}
```
