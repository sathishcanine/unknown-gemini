# Tamil — Ilakkanam (Unit 1) Generation Guide

Subject: **Tamil** / **தமிழ்**  
Unit: **Ilakkanam** / **இலக்கணம்** (25 exam Qs — எழுத்து + சொல்)

This is **not** a History/CGS fact pipeline. Ilakkanam is **rule + example + PYQ-pattern** generation.

---

## 1. Topics (14) — app syllabus

See `ilakkanam_topics.json`.

| # | Topic (TA) |
|---|---|
| 1 | பிரித்து எழுதுதல் / சேர்த்து எழுதுதல் |
| 2 | சந்திப்பிழை & ஒற்றுப்பிழை அறிதல் |
| 3 | குறில், நெடில் வேறுபாடு |
| 4 | லகர–ளகர–ழகர / னகர–ணகர / ரகர–றகர வேறுபாடு |
| 5 | இனவெழுத்துக்கள் அறிதல் |
| 6 | சுட்டு எழுத்துக்கள் |
| 7 | வினா எழுத்துக்கள் |
| 8 | ஒருமைப் பன்மை அறிதல் |
| 9 | வேர்ச்சொல் அறிதல் |
| 10 | வேர்ச்சொல் → வினைமுற்று, வினையெச்சம், வினையாலணையும் பெயர், பெயரெச்சம் |
| 11 | அயற்சொல் – தமிழ்ச்சொல் |
| 12 | எதிர்ச்சொல் |
| 13 | வினைச்சொல் |
| 14 | இரண்டு வினைச் சொற்களின் வேறுபாடு அறிதல் |

---

## 2. Sources (priority)

1. **SM Tamil Full Book** — `Data/Tamil/ilakanam/SM TAMIL FULL BOOK 570 PAGES.pdf`  
   → **primary** rules + examples for all 14 topics (TOC page 2; `pdf = printed + 5`)  
2. **PYQs** — `Data/Tamil/ilakanam/Tamil Part A illakanam previous.pdf`  
   → exam style, traps, Option E habit (do not copy verbatim into bank)  
3. **Samacheer 6–10** — `Data/Tamil/ilakanam/6 to 10 new book ilakanam.pdf`  
   → secondary / backup only  
4. **Gov Notes** — `Data/Tamil/ilakanam/பகுதி -1 இலக்கணம் Government Notes.pdf`  
   → optional lists only  

Page mapping: `ILAKKANAM_SOURCE_MAP.md` + `ilakkanam_source_map.json`.

---

## 3. Pipeline (Ilakkanam-specific)

```
Sources → topic pack (rules + examples + PYQ samples)
       → generate practice batch (30 Q)
       → human spot-check
       → ilakkanam_questions_db.json
```

### Topic pack schema (`ilakkanam_notes.json`)

Per topic:

```json
{
  "topic_id": "pirithu_sertthu",
  "rules": [
    {"rule_ta": "...", "rule_en": "...", "source": "sm"}
  ],
  "examples": [
    {"input": "...", "output": "...", "note_ta": "..."}
  ],
  "pyq_samples": [
    {
      "question_ta": "...",
      "options": [{"key":"A","text_ta":"..."}],
      "correct_option": "B",
      "source_exam": "PYQ"
    }
  ]
}
```

- Do **not** invent “facts” like History.
- Prefer **transform / error-spot / choose-correct-form** items.

---

## 4. Batch generation rules

1. **One topic per batch run** (never mix Unit-1 topics in one batch).  
2. **30 questions** final (generate ~32, prune).  
3. **No Medium/Hard force** for Tamil (Ilakkanam and later Tamil units).  
   `difficulty` may default to `"Medium"` for schema compatibility; do not block a batch on Hard count.  
4. **Option E** on every Q: `Answer not known / விடை தெரியவில்லை`.  
5. **Bilingual** `question_en`/`question_ta`, options, explanation (Tamil-first OK for Ilakkanam).  
6. Set `"batch": "Batch 1"`, `"type": "practice"`, `"subject": "Tamil"`, `"topic": "<name_ta or id>"`.  
7. **Zero duplicates** vs existing `question_ta`/`question_en` for that topic.  
8. PYQ samples = **style only** — do not copy PYQ text verbatim into the bank.  
9. After each batch: **spot-check ≥ 5 answers** against SM notes (primary).  
10. Quality focus: correct vs SM, clean Tamil, TNPSC-style stems, plausible distractors.

### Preferred question shapes (by topic family)

- பிரித்து/சேர்த்து, சந்தி, ஒற்று → correction / choose correct form  
- குறில்–நெடில், லளழ/னண/ரற → pick correct spelling/meaning in context  
- வேர்ச்சொல் / derivatives → identify root or derived form  
- எதிர்ச்சொல் / அயற்சொல் → direct MCQ + odd traps  
- ஒருமை–பன்மை → fix agreement in sentence  

Avoid overusing Polity-style Assertion–Reason unless natural.

---

## 5. Files

| File | Role |
|---|---|
| `Tamil/ilakkanam_topics.json` | Canonical 14 topics |
| `Tamil/ILAKKANAM_SOURCE_MAP.md` | Human page map |
| `Tamil/ilakkanam_source_map.json` | Machine page hits + PYQ sections |
| `Tamil/ilakkanam_notes.json` | Rules/examples/PYQ samples per topic |
| `Tamil/ilakkanam_questions_db.json` | Practice questions DB |
| `Tamil/ILAKKANAM_GENERATION_GUIDE.md` | This guide |

---

## 6. Rollout plan

1. ✅ Scaffold + topic list  
2. ✅ Source map = **SM TOC** (primary notes)  
3. ✅ PYQ samples for topic 1 (பிரித்து/சேர்த்து) and topic 12 (எதிர்ச்சொல்) — early pilots; **resume in TOC order 1→14**  
4. For each topic **1 → 14** in order:  
   - Extract SM rules + examples  
   - Extract/fill PYQ samples if missing  
   - (Later, on approval) Batch 1 → spot-check vs SM  
5. Import to Postgres + app menu: Tamil → Ilakkanam → 14 topics  

---

## 7. Out of scope (for now)

- Tamil Units 2–7 (சொல்லகராதி, இலக்கியம், …)  
- PYQ extras: பொருத்துதல், நூல்/ஆசிரியர், மரபுப் பிழை, யாப்பு-heavy sections  
