# Concord (Subject–Verb Agreement) — Source Map

## App placement

```
General English
└── Unit I — Grammar
    ├── Parts of Speech
    └── Concord
        └── Concord   (practice topic + rule tags)
```

## Sources (same 3-book pattern as Parts of Speech)

| Priority | File | Concord coverage | Role |
|:--------:|------|------------------|------|
| **1 Primary** | `asan - concord,tense, sentence pattern, question tag.pdf` | **PDF pp. 1–6** (book ~45–50). Tense starts p.7 | Full rules + exercises + answer key |
| **2 Secondary** | `Grammer.pdf` | **PDF pp. 326–330** (index: Concord → 324; content block starts 326) | Textbook rules + Always Singular/Plural + tasks (overlaps Asan exercises) |
| **3 Secondary** | `General_English_Part_A_Grammar_Group_2_Govt_Notes_for_TNPSC_Group.pdf` | **No dedicated Concord chapter.** Listed under Find-out-the-Error areas (**p.77**): “Concord (agreement of the verb with its subject)”. Error chapter continues ~pp.77–80+ (mostly articles/prepositions; harvest any number/SVA items) | Exam-style error framing; fill gaps if Asan/`Grammer` miss a trap |

**Do not use** `asan parts of speech (1).pdf` for Concord.

**Filename note:** repo file is `Grammer.pdf` (spelling as on disk).

## Page detail

### Asan (primary)
| PDF | Content |
|----:|---------|
| 1–3 | Rules (and / as well as / either–neither / each–every / collective / units / titles…) |
| 4–5 | Exercises |
| 6 | Answer key |
| 7+ | **Out of scope** (Tense → later) |

### Grammer.pdf
| PDF | Content |
|----:|---------|
| 326 | Subject and Verb Agreement (Concord) intro + Always Plural start |
| 327 | Always Singular + underline/correct exercises |
| 328–330 | Agreement of subject with verb + more rules/tasks |
| 331+ | Leaves Concord (process writing / Question Tag) |

### Govt notes
| PDF | Content |
|----:|---------|
| 77 | Error-spotting intro **explicitly lists Concord** as a tested area |
| 77–80+ | Find-out-the-Error chapter — extract Concord/number items only; ignore pure article/prep noise |

## Extraction / merge order

1. Extract **Asan pp.1–6** → `concord_notes.json` (base)  
2. Merge **Grammer.pdf pp.326–330** (dedupe overlapping examples)  
3. Merge **Govt** error items that are true SVA/Concord  
4. PYQ PDFs = **style only** (do not copy into bank)  
5. Generate practice batches grounded in merged notes  

## Phase-1 batches (proposed)

| Topic | Batches | Q/batch | Total |
|-------|--------:|--------:|------:|
| Concord | 2 | 25 | 50 |

## Subtopic tags (generation only)

`basic_singular_plural`, `and_plural`, `one_idea_singular`, `as_well_as_with`, `either_or_neither_nor`, `each_every_indefinite`, `collective_nouns`, `plural_form_singular_meaning`, `units_money_time_distance`, `titles_same_vs_different`, `intervening_phrase`, `always_plural_set`, `error_spotting`
