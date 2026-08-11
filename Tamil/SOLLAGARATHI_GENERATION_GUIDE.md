# Tamil — Sollagarathi (Unit 2) Generation Guide

Subject: **Tamil** / **தமிழ்**  
Unit: **Sollagarathi** / **சொல்லகராதி** (15 exam Qs)

Same pipeline shape as Unit 1 Ilakkanam: **SM notes = answer truth**, PYQ = style, Gemini = quality gate only.

---

## 1. Topics (16) — app syllabus

See `sollagarathi_topics.json`.

| # | Topic (TA) |
|---|---|
| 1 | எதிர்ச்சொல்லை எடுத்தெழுதுதல் |
| 2 | ஓரெழுத்து ஒரு மொழி & பொருள் தரும் ஓர் எழுத்து |
| 3 | உரிய பொருளைக் கண்டறிதல் & சொல்லும் பொருளும் அறிதல் |
| 4 | ஒருபொருள் தரும் பல சொற்கள் & ஒரு சொல்லிற்கு இணையான வேறு சொல் அறிதல் |
| 5 | பொருந்தா சொல்லைக் கண்டறிதல் |
| 6 | அகர வரிசைப்படி சொற்களைச் சீர்செய்தல் |
| 7 | ஒருபொருள் பன்மொழி |
| 8 | இருபொருள் குறிக்கும் சொற்கள் |
| 9 | பேச்சு வழக்கு, எழுத்து வழக்கு |
| 10 | கோடிட்ட இடத்தில் சரியான சொல்லைத் தேர்ந்தெடுத்து எழுதுதல் |
| 11 | பொருத்தமான பொருளைத் தெரிவு செய்தல் |
| 12 | ஊர்ப் பெயர்களின் மரூஉவை எழுதுக |
| 13 | பிழை திருத்துக |
| 14 | சொற்களை இணைத்துப் புதிய சொல் உருவாக்குதல் |
| 15 | அடைப்புக்குள் உள்ள சொல்லைத் தகுந்த இடத்தில் சேர்த்தல் |
| 16 | பல பொருள் தரும் ஒரு சொல்லைக் கூறுக |

---

## 2. Sources (priority)

1. **SM Tamil Full Book** — primary lists + examples (`pdf = printed + 5`)  
2. **PYQs** — style / traps only  
3. Samacheer / Gov — backup only  

Page mapping: `SOLLAGARATHI_SOURCE_MAP.md` + `sollagarathi_source_map.json`.

---

## 3. Pipeline

```
SM extract (topic pack) → PYQ style (optional)
        ↓
  sollagarathi_notes.json
        ↓
  generate batches (30 Q) → verify vs SM → import Postgres
```

Files (Unit 2):

| File | Role |
|------|------|
| `sollagarathi_topics.json` | 16 topic IDs |
| `sollagarathi_source_map.json` | page ranges |
| `sollagarathi_notes.json` | rules / examples / PYQ samples |
| `sollagarathi_questions_db.json` | practice questions |
| `backend/import_sollagarathi_questions.py` | import into subject `Tamil` |

App: topics land under subject **Tamil** (same hub as Ilakkanam). Prefer distinct topic names so Unit 1/2 don’t collide.

---

## 4. Quality rules (same as Unit 1)

- SM = answer truth  
- No SM / எஸ்.எம் / விதி R# branding in stems  
- Unique `question_ta` + `question_en` within topic  
- Option E habit where TNPSC-style  
- Double-verify each topic’s batches before next topic  

---

## 5. Order

**1 → 16 only.** Start with Topic 1 SM extract when approved.
