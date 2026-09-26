# Physics Fact Extraction Guide (TNPSC GS)

Adapted from `Biology/BIOLOGY_FACT_EXTRACTION_GUIDE.md` for the Physics source book.

## Source
- PDF: `Data/Physics/STUDY MATERIAL - PHYSICS ( TAMIL).pdf`
- Publisher: Trichy Race Academy
- Language: Tamil in **Bamini encoding**.
- Method: render each source page as an image and use vision extraction. Do not trust the PDF text layer as Tamil Unicode.
- Skip academy headers, address, contact number, footers and page-number noise.

## Syllabus Topics ↔ Book Start Pages

| # | Topic | TOC start |
|---|-------|-----------|
| 1 | Universe (பேரண்டம்) | 3 |
| 2 | Laws of Physics (பொது அறிவியல் விதிகள்) | 12 |
| 3 | Scientific Instruments (அறிவியல் கருவிகள்) | 26 |
| 4 | Discoveries and National Scientific Laboratories | 30 (mid-page) |
| 5 | Mechanics and Properties of Matter | 40 |
| 6 | Physical Quantities, Standards and Units | 44 (mid-page) |
| 7 | Force, Motion and Energy | 61 (mid-page) |
| 8 | Magnetism | 95 |
| 9 | Solid-State Physics, Electronics and Communications | 102 |
| 10 | Heat, Light and Sound | 124 |

### Confirmed topic ranges
- **Universe**: physical PDF pages **3–11**.
- **Laws of Physics (பொது அறிவியல் விதிகள்)**: physical PDF pages **12–25**.
- **Scientific Instruments (அறிவியல் கருவிகள்)**: physical PDF pages **26–30**.
- Physical page 30 is shared: extract instruments only through **Wavemeter**;
  Topic 4 starts below it on the same page.
- **Discoveries and National Scientific Laboratories**: physical PDF pages
  **30–39**. On page 30, start below the Scientific Instruments list at the
  discoveries heading.
- **Mechanics and Properties of Matter**: physical PDF pages **40–44**.
- On page 44, extract only the surface-tension application bullets at the top;
  Topic 6 starts below on the same page.
- **Physical Quantities, Standards and Units**: physical PDF pages **44–61**.
- On page 44, start below the Mechanics surface-tension bullets; on page 61,
  stop before Force, Motion and Energy begins mid-page.
- **Force, Motion and Energy (விசை, இயக்கம் மற்றும் ஆற்றல்)**: physical PDF
  pages **61–78**.
- On page 61, start below the Physical Quantities density bullets at the
  **IX. Force, Motion and Energy** heading; on page 78, stop after Nuclear
  Energy before Chapter X (Electricity and Magnetism) on page 79.
- Always inspect boundary pages before adding another topic mapping.

## Mandatory Extraction Rules
1. Process one topic at a time.
2. Read every bullet, numbered list, table and comparison on every mapped page.
3. Extract only specific, independently testable TNPSC facts.
4. Preserve names, years, measurements, distances, durations, counts and classifications.
5. Preserve scientifically relevant formulas and relationships.
6. Split compound paragraphs into distinct facts without losing qualifiers.
7. Do not invent, modernize or silently correct the source’s factual claims.
8. Produce accurate English and Tamil Unicode for every fact.
9. Remove exact duplicates and obvious paraphrase duplicates.
10. Every fact must contain the physical PDF page in `source`.

## Fact Shape
```json
{
  "fact_en": "The Milky Way is the galaxy to which the Solar System belongs.",
  "fact_ta": "சூரியக் குடும்பம் பால்வெளி அண்டத்தைச் சேர்ந்தது.",
  "source": "Physics Tamil Study Material Page 3",
  "context_en": "Universe",
  "context_ta": "பேரண்டம்"
}
```

## Extraction Workflow
1. Run **one vision pass** per mapped page for the topic.
2. Do **not** re-run `--force` when the topic already has facts in
   `physics_facts.json`.
3. Do **not** run a second vision pass (`--audit-missing`) in the normal
   workflow. Use it only when a specific page is known to be incomplete.
4. Re-run `--qc-only` after extraction; proceed to question generation only
   when page coverage is complete and there are no hard QC issues.

## Commands
```bash
# New topic — first extraction only
python3 Physics/extract_physics_facts.py --topic "Force, Motion and Energy"

# Re-run structural QC only
python3 Physics/extract_physics_facts.py --qc-only

# Re-extract from scratch only when the stored facts must be replaced entirely
python3 Physics/extract_physics_facts.py --topic "Force, Motion and Energy" --force
```

## Outputs
- `Physics/physics_facts.json`
- `Physics/physics_facts_qc_report.json`
- `Physics/_tmp_fact_extract_cache/universe_page_XXX.json`

## Model and Keys
- Follow the project model lock; do not change the model without current-chat user permission.
- Current extractor model: `gemini-3.1-flash-lite`.
- Key rotation must use the complete ordered pool from `gemini_keys()`.

