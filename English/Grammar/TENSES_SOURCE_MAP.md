# Tenses — Source Map

## App placement (matches requested tree)

```
General English → Unit I — Grammar → Tenses
  ├── Present Tense
  │   ├── Simple Present
  │   ├── Present Continuous
  │   ├── Present Perfect
  │   └── Present Perfect Continuous
  ├── Past Tense
  │   ├── Simple Past
  │   ├── Past Continuous
  │   ├── Past Perfect
  │   └── Past Perfect Continuous
  ├── Future Tense
  │   ├── Simple Future
  │   ├── Future Continuous
  │   ├── Future Perfect
  │   └── Future Perfect Continuous
  └── Mixed Tense Questions
```

Hub: **menu `tenses`** → **groups** (Present / Past / Future / Mixed) → **topic syllabus** → batches.

## Sources (3 books — same as Concord / POS)

| Priority | File | Tenses coverage | Role |
|:--------:|------|-----------------|------|
| **1** | `asan - concord,tense, sentence pattern, question tag.pdf` | **PDF pp. 7–39** (Tense + exercises + answer keys). Sentence Pattern ≈ p.40+ | Primary |
| **2** | `Grammer.pdf` | Index **Tenses → 1**; chapter from **PDF ~11**; next topic Transformation (index 58) | Secondary textbook |
| **3** | `General_English_Part_A_…Govt_Notes….pdf` | **TENSE chapter pp. 50–59** (forms + auxiliaries/modals — harvest tense-form items; skip pure modal trivia if off-brief) | Secondary |

**Out of scope for Tenses:** Asan POS PDF; Asan Concord pp.1–6; Sentence Pattern / Question Tag (later menus).

## Phase-1 batches (proposed)

| Leaf topic | Batches | Q |
|------------|--------:|--:|
| Each of 12 forms | 1 × 25 | 300 |
| Mixed Tense Questions | 2 × 25 | 50 |
| **Total** | | **350** |

Generate Present group first if we phase delivery; same pipeline for Past / Future / Mixed.

## Pipeline

1. Scaffold topics + source map + hub `groups`  
2. Extract Asan 7–39 → merge Grammer + Govt → `tenses_notes.json` (keyed by form)  
3. Generate per leaf topic → verify → import  
4. Build Mixed from pool (like POS Mixed)  
5. Wire `english_units.json` menu `tenses` with groups  
