# Active & Passive Voice — Source Map

## App placement

```
General English → Unit I — Grammar → Active & Passive Voice
  ├── Active → Passive
  ├── Passive → Active
  ├── Voice with Different Tenses
  ├── Voice with Modals
  └── Imperative Sentences
```

Hub: **menu `active_passive_voice`** → **5 groups** (one leaf topic each) → batches.

## Sources

| Priority | File | Coverage | Role |
|:--------:|------|----------|------|
| **1** | `asan tense , active and passive voice.pdf` | **PDF pp. 18–23** (Asan book pp.64–90: Voice rules, tense table, imperatives, modals, exercises + keys) | **Primary** |
| **2** | `Grammer.pdf` | **PDF pp. 68–78** (9th–12th voice chapter) | Secondary |
| **3** | `General_English_Part_A_…Govt_Notes….pdf` | **VOICE pp. 62–66** | Secondary |

**Note:** Pages 1–17 of the Asan PDF are **Tenses** (already built). Voice extraction uses **pp.18–23 only**.

## Phase-1 batches

| Leaf topic | Batches | Q |
|------------|--------:|--:|
| Active → Passive | 2 × 25 | 50 |
| Passive → Active | 2 × 25 | 50 |
| Voice with Different Tenses | 2 × 25 | 50 |
| Voice with Modals | 2 × 25 | 50 |
| Imperative Sentences | 2 × 25 | 50 |
| **Total** | | **250** |

## Pipeline

1. `extract_voice_notes.py` → `voice_notes.json`
2. `generate_voice_questions.py` → `voice_questions_db.json`
3. `verify_voice_batches.py` → report
4. `import_voice_questions.py` → Postgres + server deploy
