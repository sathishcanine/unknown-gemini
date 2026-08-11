# Tamil — Unit 4 கலைச் சொற்கள் Generation Guide

Subject: **Tamil** / **தமிழ்**  
Unit: **Kalaichorkal** / **கலைச் சொற்கள்** (10 exam Qs)

**SM notes = answer truth**, Gemini = quality gate only.

---

## Topics (6)

See `kalaichorkal_topics.json`.

| # | Topic (TA) |
|---|---|
| 1 | வகுப்புவாரி கலைச்சொற்கள் (6–12) |
| 2 | அறிவியல் & தொழில்நுட்பம் கலைச்சொற்கள் |
| 3 | கல்வி சார்ந்த கலைச்சொற்கள் |
| 4 | மருத்துவம் சார்ந்த கலைச்சொற்கள் |
| 5 | சட்டம் & மேலாண்மை கலைச்சொற்கள் |
| 6 | புவியியல், ஊடகம் & தகவல் தொழில்நுட்பம் |

---

## Question shapes

- English technical term → choose correct Tamil equivalent
- Tamil term → choose English / meaning
- Spot wrong EN↔TA pair among close distractors
- Domain-tagged fill / match (optional, sparse)

Use **only** SM pairs. Pure Tamil options preferred for answers. No academy branding.

---

## Files

| File | Role |
|------|------|
| `kalaichorkal_topics.json` | 6 topic IDs |
| `kalaichorkal_source_map.json` / `.md` | page ranges |
| `kalaichorkal_notes.json` | EN→TA pairs |
| `kalaichorkal_questions_db.json` | practice questions |
| `extract_kalaichorkal_sm_notes.py` | SM OCR extract |
| `generate_kalaichorkal_questions.py` | batch generator |
| `backend/import_kalaichorkal_questions.py` | import → Tamil |

---

## Order

**1 → 6 only.** Start Topic 1 after SM extract is ready.
