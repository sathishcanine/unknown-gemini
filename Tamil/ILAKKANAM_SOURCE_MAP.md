# Ilakkanam — Source Map (14 topics)

**Primary notes book:** SM Tamil Full Book (Santhosh Mani Academy)  
**Page numbers below are printed book pages** (bottom of page).  
**PDF index:** `pdf_page = printed_page + 5`  
(TOC is PDF pp.1–5; printed p.01 starts at PDF p.6.)

---

## Source files

| Key | Path | Role |
|---|---|---|
| `sm` | `Data/Tamil/ilakanam/SM TAMIL FULL BOOK 570 PAGES.pdf` (570 pp) | **Primary rules + examples** for all 14 topics |
| `pyq` | `Data/Tamil/ilakanam/Tamil Part A illakanam previous.pdf` (344 pp) | Exam **style** PYQ samples |
| `samacheer` | `Data/Tamil/ilakanam/6 to 10 new book ilakanam.pdf` (106 pp) | Secondary / backup only |
| `gov` | `Data/Tamil/ilakanam/பகுதி -1 இலக்கணம் Government Notes.pdf` (165 pp) | Optional lists only |

SM notes: mostly **scanned images** → extract rules/examples via Gemini OCR.

---

## SM TOC — Unit 1 இலக்கணம் (25 Q) — exact syllabus map

From SM PDF page 2 (பொதுத் தமிழ் TOC):

| # | Topic ID | Topic (TA) | Printed pages | PDF pages |
|---|---|---|---:|---:|
| 1 | `pirithu_sertthu` | பிரித்து எழுதுதல், சேர்த்து எழுதுதல் | 01–20 | 6–25 |
| 2 | `sandhi_otru_pizhai` | சந்திப்பிழை & ஒற்றுப்பிழை அறிதல் | 21–35 | 26–40 |
| 3 | `kuril_nedil` | குறில், நெடில் வேறுபாடு | 36–39 | 41–44 |
| 4 | `la_na_ra_bedham` | லகர, ளகர, ழகர – னகர ணகர – ரகர, றகர வேறுபாடு | 40–49 | 45–54 |
| 5 | `ina_ezhuthu` | இனவெழுத்துக்கள் அறிதல் | 50–51 | 55–56 |
| 6 | `suttu_ezhuthu` | சுட்டு எழுத்துக்கள் | 52–53 | 57–58 |
| 7 | `vina_ezhuthu` | வினா எழுத்துக்கள் | 54–57 | 59–62 |
| 8 | `orumai_panmai` | ஒருமைப் பன்மை அறிதல் | 58–60 | 63–65 |
| 9 | `verchol` | வேர்ச்சொல் அறிதல் | 61–61 | 66–66 |
| 10 | `verchol_derivatives` | வேர்ச்சொல் → வினைமுற்று, வினையெச்சம், வினையாலணையும் பெயர், பெயரெச்சம் | 62–70 | 67–75 |
| 11 | `ayarchol_tamilchol` | அயற்சொல் – தமிழ்ச்சொல் | 71–71 | 76–76 |
| 12 | `ethirchol` | எதிர்ச்சொல் | 72–75 | 77–80 |
| 13 | `vinaichol` | வினைச்சொல் | 76–79 | 81–84 |
| 14 | `irandu_vinai_bedham` | இரண்டு வினைச் சொற்களின் வேறுபாடு அறிதல் | 80–83 | 85–88 |

Verified spots: printed 01 = பிரித்து; 21 = சந்திப்பிழை; 61 = வேர்ச்சொல்.

Unit 1 ends ~printed p.83; Unit 2 (சொல்லகராதி) starts p.84 — **out of scope for Ilakkanam menu**.

---

## PYQ section index (style samples only)

| Start–End (PDF) | Section | Maps to topic |
|---:|---|---|
| 58–71 | பிரித்தெழுதுக / சேர்த்தெழுதுக | 1 |
| 72–80 | எதிர்ச்சொல் | 12 |
| 95–101 | சந்திப்பிழை | 2 |
| 102–108 | ஒருமை பன்மை | 8 |
| 125–145 | பிறமொழி / ஆங்கில→தமிழ் | 11 |
| 146–157 | ஒலி வேறுபாடு | 4 (+ help 3) |
| 169–178 | வேர்ச்சொல் | 9 |
| 179–188 | வேர்ச்சொல் derivatives | 10 |

Skip PYQ extras (பொருத்துதல், மரபு, யாப்பு…) for Unit-1.

---

## How we use sources

```
SM book (rules+examples)  ─┐
PYQ PDF (style samples)   ─┼─→ ilakkanam_notes.json
samacheer/gov (backup)    ─┘
                              ↓
                    (later) generate practice batches
                              ↓
                    spot-check answers vs SM rules
```

1. **SM** = what to teach / correct answers  
2. **PYQ** = how exam asks  
3. Do **not** copy PYQ text into the question bank  

---

## Generation priority

Follow **SM TOC order 1 → 14** (no jumping to topic 12 first).

1. Extract SM rules+examples + PYQ samples topic-by-topic in order  
2. After each topic pack is ready → Batch 1 (when you approve generation)  
3. Spot-check vs SM rules before next topic  

Topic IDs in order:  
`pirithu_sertthu` → `sandhi_otru_pizhai` → `kuril_nedil` → `la_na_ra_bedham` → `ina_ezhuthu` → `suttu_ezhuthu` → `vina_ezhuthu` → `orumai_panmai` → `verchol` → `verchol_derivatives` → `ayarchol_tamilchol` → `ethirchol` → `vinaichol` → `irandu_vinai_bedham`

Machine-readable twin: `ilakkanam_source_map.json`
