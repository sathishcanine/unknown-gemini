# Sollagarathi — Source Map (Unit 2 · 16 topics)

**Primary notes book:** SM Tamil Full Book (Santhosh Mani Academy)  
**Page numbers below are printed book pages** (bottom of page).  
**PDF index:** `pdf_page = printed_page + 5`  
(TOC is PDF pp.1–5; printed p.01 starts at PDF p.6.)

---

## Source files

| Key | Path | Role |
|---|---|---|
| `sm` | `Data/Tamil/ilakanam/SM TAMIL FULL BOOK 570 PAGES.pdf` (570 pp) | **Primary** lists + examples for all 16 topics |
| `pyq` | `Data/Tamil/ilakanam/Tamil Part A illakanam previous.pdf` (344 pp) | Exam **style** PYQ samples (vocab sections where present) |
| `samacheer` | `Data/Tamil/ilakanam/6 to 10 new book ilakanam.pdf` | Secondary / backup only |
| `gov` | `Data/Tamil/ilakanam/பகுதி -1 இலக்கணம் Government Notes.pdf` | Optional lists only |

SM notes: mostly **scanned images** → extract rules/examples via Gemini OCR.

---

## SM TOC — Unit 2 சொல்லகராதி (15 Q) — exact syllabus map

From SM பொதுத் தமிழ் TOC (அலகு 2):

| # | Topic ID | Topic (TA) | Printed start | Printed range (est.) | PDF range |
|---|---|---|---:|---|---|
| 1 | `ethirchol_eduthelzhuthal` | எதிர்ச்சொல்லை எடுத்தெழுதுதல் | 84 | 84–84 | 89–89 |
| 2 | `orezhuthu_orumozhi` | ஓரெழுத்து ஒரு மொழி & பொருள் தரும் ஓர் எழுத்து | 85 | 85–91 | 90–96 |
| 3 | `uriya_porul_kandarithal` | உரிய பொருளைக் கண்டறிதல் & சொல்லும் பொருளும் அறிதல் | 92 | 92–129 | 97–134 |
| 4 | `oruporul_pala_sorkal` | ஒருபொருள் தரும் பல சொற்கள் & ஒரு சொல்லிற்கு இணையான வேறு சொல் | 130 | 130–132 | 135–137 |
| 5 | `poruntha_sol_kandarithal` | பொருந்தா சொல்லைக் கண்டறிதல் | 133 | 133–154 | 138–159 |
| 6 | `agara_varisai` | அகர வரிசைப்படி சொற்களைச் சீர்செய்தல் | 155 | 155–161 | 160–166 |
| 7 | `oruporul_panmozhi` | ஒருபொருள் பன்மொழி | 162 | 162–162 | 167–167 |
| 8 | `iruporul_kurikkum_sorkal` | இருபொருள் குறிக்கும் சொற்கள் | 163 | 163–165 | 168–170 |
| 9 | `pechu_ezhuthu_vazhakku` | பேச்சு வழக்கு, எழுத்து வழக்கு | 166 | 166–176 | 171–181 |
| 10 | `koditta_idam_sariya_sol` | கோடிட்ட இடத்தில் சரியான சொல்லைத் தேர்ந்தெடுத்து எழுதுதல் | 177 | 177–185 | 182–190 |
| 11 | `poruthamana_porul` | பொருத்தமான பொருளைத் தெரிவு செய்தல் | 186 | 186–187 | 191–192 |
| 12 | `oor_peyar_maruu` | ஊர்ப் பெயர்களின் மரூஉவை எழுதுக | 188 | 188–189 | 193–194 |
| 13 | `pizhai_thiruthugal` | பிழை திருத்துக | 190 | 190–194 | 195–199 |
| 14 | `sorkalai_inaithu_puthiya_sol` | சொற்களை இணைத்துப் புதிய சொல் உருவாக்குதல் | 195 | 195–196 | 200–201 |
| 15 | `adaippukkul_sol_serthal` | அடைப்புக்குள் உள்ள சொல்லைத் தகுந்த இடத்தில் சேர்த்தல் | 197 | 197–201 | 202–206 |
| 16 | `pala_porul_oru_sol` | பல பொருள் தரும் ஒரு சொல்லைக் கூறுக | 202 | 202–204 | 207–209 |

Ranges = start of topic → page before next TOC entry. Topic 16 ends at printed 204; Unit 3 starts printed 205.

**Note:** Unit 1 topic 12 `ethirchol` (grammar antonyms) ≠ Unit 2 topic 1 `ethirchol_eduthelzhuthal` (vocab pick-the-antonym). Keep separate topic packs.

---

## How we use sources

```
SM book (lists + examples) ─┐
PYQ PDF (style samples)    ─┼─→ sollagarathi_notes.json
samacheer/gov (backup)     ─┘
                              ↓
                    generate practice batches
                              ↓
                    spot-check answers vs SM
                              ↓
                    import → local Postgres (subject Tamil)
```

1. **SM** = answer truth  
2. **PYQ** = how exam asks (style only; do not copy verbatim)  
3. Gemini = quality gate only (not second answer key)

---

## Generation priority

Follow **SM TOC order 1 → 16** (no jumping).

Topic IDs in order:  
`ethirchol_eduthelzhuthal` → `orezhuthu_orumozhi` → `uriya_porul_kandarithal` → `oruporul_pala_sorkal` → `poruntha_sol_kandarithal` → `agara_varisai` → `oruporul_panmozhi` → `iruporul_kurikkum_sorkal` → `pechu_ezhuthu_vazhakku` → `koditta_idam_sariya_sol` → `poruthamana_porul` → `oor_peyar_maruu` → `pizhai_thiruthugal` → `sorkalai_inaithu_puthiya_sol` → `adaippukkul_sol_serthal` → `pala_porul_oru_sol`
