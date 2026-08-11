# Tamil — Unit 5 வாசித்தல் (Reading Comprehension)

Subject: **Tamil** / **தமிழ்**  
Unit: **Vasiththal** / **வாசித்தல் - புரிந்து கொள்ளும் திறன்** (15 exam Qs)

Same pipeline as Units 1–4:
- **SM notes = answer truth**
- Gemini = quality gate only

## Topics (6)

See `vasiththal_topics.json`.

1. `pathiyil_vinaigal` — கொடுக்கப்பட்ட பத்தியிலிருந்து… சரியான விடை
2. `seithithaal_vasiththal` — செய்தித்தாள் / தலையங்கம் / கட்டுரை வாசிப்பு
3. `uvamai_thodar` — உவமைத் தொடரின் பொருளறிதல்
4. `marabu_thodar` — மரபுத் தொடரின் பொருளறிதல்
5. `pazhamozhigal` — பழமொழிகள் பொருளறிதல்
6. `aavanam_puriththal` — ஆவண உள்ளடக்கங்களைப் புரிந்து கொள்ளும் திறன்

## Question shapes (practice)

Generator will use TNPSC-like MCQ shapes:
- Passage/news/document -> pick correct inference/detail
- Simile/idiom/proverb -> choose the correct meaning (close distractors)
- Always keep answers consistent with SM extracted ground truth

## Files
- `vasiththal_topics.json` — unit + topic metadata
- `vasiththal_source_map.json` — SM printed→PDF page ranges (`pdf_page = printed_page + 5`)
- `extract_vasiththal_sm_notes.py` — SM OCR extract → `vasiththal_notes.json`
- `generate_vasiththal_questions.py` — notes → practice batches
- `backend/import_vasiththal_questions.py` — import `vasiththal_questions_db.json` → Postgres

## Order
Start Topic 1 after SM extract is ready:
1 → 6 only.

