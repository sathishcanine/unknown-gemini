"""
Fact extraction for TVK-Government Policies usable PDFs.

Follows INM/Chemistry page-by-page rules (see TVK_FACT_EXTRACTION_GUIDE.md).
Prefer page text when available; fall back to image OCR for blank pages.

Usage:
  export GEMINI_API_KEY=...
  python3 TVK/extract_tvk_facts.py --topic "TVK Leaders"
  python3 TVK/extract_tvk_facts.py
"""

import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

import fitz  # PyMuPDF

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "Data", "TVK-Government-Data")
OUTPUT_JSON = os.path.join(BASE_DIR, "TVK", "tvk_facts.json")

MODEL = "gemini-3.5-flash-lite"

books = {
    "Leaders": os.path.join(DATA_DIR, "TVK_Govt_LEADERS_Policy_Notes_1_usable.pdf"),
    "SchemesPart2": os.path.join(DATA_DIR, "TVK_govt_Policy_Scheme_part_2_usable.pdf"),
    "SchemesPart3": os.path.join(DATA_DIR, "Tvk_govt_policy_Scheme_part_3_usable.pdf"),
}

# Two syllabus topics: Leaders now; Policies & Schemes later (parts 2+3)
topics_mapping = {
    "TVK Leaders": {
        "Leaders": list(range(0, 15)),
    },
    "TVK Policies & Schemes": {
        "SchemesPart2": list(range(0, 20)),
        "SchemesPart3": list(range(0, 49)),
    },
}


def call_gemini_extraction_text(topic_name, book_name, page_num, page_text, api_key):
    prompt = f"""
You are an expert TNPSC Group exam question setter specializing in Tamil Nadu /
TVK (Tamilaga Vettri Kazhagam) Government policies, schemes, and leaders.
I have extracted a single page of text from the book "{book_name}" (Page {page_num}) for the topic: "{topic_name}".
Your task is to perform an exhaustive, line-by-line fact extraction of this page. Do not summarize or skip anything.

EXTRACT EVERY SINGLE:
1. Leader names, designations, portfolios, titles, and key statements or announcements.
2. Scheme / welfare program names, launch dates, objectives, target beneficiaries, eligibility, and benefits.
3. Budget allocations, subsidies, loan waivers, and exact ₹ / crore figures.
4. Departments, boards, agencies, task forces, and administrative roles.
5. Statistics, districts covered, survey results, targets, acts, rules, and policy documents.

INSTRUCTIONS:
- Pull out at least 8-15 distinct factual points if present in the text.
- Keep each fact extremely concise, factual, and clear.
- Exclude verbose explanations, conversational descriptions, social-media chrome, and generic commentary.
- Each fact MUST contain a specific entity (name, date, amount, scheme, department, or statistic).
- Provide accurate bilingual translations: both English and Tamil.
- Provide short policy context in both English and Tamil.

Format the output as a JSON array of objects:
[
  {{
    "fact_en": "Verifiable fact statement in English",
    "fact_ta": "Verifiable fact statement in Tamil",
    "source": "{book_name}",
    "context_en": "Short policy context in English",
    "context_ta": "Short policy context in Tamil"
  }}
]

Return ONLY the raw JSON string as output. Do not add markdown backticks.

---
PAGE TEXT:
{page_text}
"""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    headers = {"Content-Type": "application/json"}
    return post_request(payload, headers, book_name, page_num, api_key)


def call_gemini_extraction_image(topic_name, book_name, page_num, img_base64, api_key):
    prompt = f"""
You are an expert TNPSC Group exam question setter specializing in Tamil Nadu /
TVK (Tamilaga Vettri Kazhagam) Government policies, schemes, and leaders.
This is an image of a page from "{book_name}" (Page {page_num}) for the topic: "{topic_name}".
Your task is to perform an exhaustive, line-by-line fact extraction of this page. Do not summarize or skip anything.

EXTRACT EVERY SINGLE:
1. Leader names, designations, portfolios, titles, and key statements or announcements.
2. Scheme / welfare program names, launch dates, objectives, target beneficiaries, eligibility, and benefits.
3. Budget allocations, subsidies, loan waivers, and exact ₹ / crore figures.
4. Departments, boards, agencies, task forces, and administrative roles.
5. Statistics, districts covered, survey results, targets, acts, rules, and policy documents.

INSTRUCTIONS:
- Pull out at least 8-15 distinct factual points if present in the image.
- Keep each fact extremely concise, factual, and clear.
- Exclude verbose explanations, conversational descriptions, social-media chrome, and generic commentary.
- Each fact MUST contain a specific entity (name, date, amount, scheme, department, or statistic).
- Provide accurate bilingual translations: both English and Tamil.
- Provide short policy context in both English and Tamil.

Format the output as a JSON array of objects:
[
  {{
    "fact_en": "Verifiable fact statement in English",
    "fact_ta": "Verifiable fact statement in Tamil",
    "source": "{book_name}",
    "context_en": "Short policy context in English",
    "context_ta": "Short policy context in Tamil"
  }}
]

Return ONLY the raw JSON string as output. Do not add markdown backticks.
"""
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": img_base64,
                        }
                    },
                ]
            }
        ],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    headers = {"Content-Type": "application/json"}
    return post_request(payload, headers, book_name, page_num, api_key)


def post_request(payload, headers, book_name, page_num, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
    retries = 5
    delay = 10
    attempt = 0
    while attempt < retries:
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                res_data = response.read().decode("utf-8")
                res_json = json.loads(res_data)
                raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                if raw_text.startswith("```"):
                    raw_text = raw_text.split("\n", 1)[1]
                    if raw_text.endswith("```"):
                        raw_text = raw_text.rsplit("\n", 1)[0]

                start_idx = raw_text.find("[")
                if start_idx != -1:
                    count = 0
                    for idx in range(start_idx, len(raw_text)):
                        if raw_text[idx] == "[":
                            count += 1
                        elif raw_text[idx] == "]":
                            count -= 1
                            if count == 0:
                                raw_text = raw_text[start_idx : idx + 1]
                                break
                return json.loads(raw_text.strip())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"    {book_name} P{page_num} Rate limited (429). Retrying in {delay}s...")
                time.sleep(delay)
                delay = min(delay * 2, 60)
            elif e.code == 503:
                print(f"    {book_name} P{page_num} Service unavailable (503). Retrying in {delay}s...")
                time.sleep(delay)
                delay = min(delay * 2, 60)
            else:
                attempt += 1
                body = e.read().decode("utf-8", errors="ignore")
                print(f"    {book_name} P{page_num} [Attempt {attempt}/{retries}] HTTP {e.code}: {body[:200]}")
                time.sleep(5)
        except Exception as e:
            attempt += 1
            print(f"    {book_name} P{page_num} [Attempt {attempt}/{retries}] Error: {e}")
            time.sleep(5)
    return []


def normalize_text(text):
    return re.sub(r"[^a-zA-Z0-9\u0b80-\u0bff]", "", text).lower()


def deduplicate_facts(facts_list):
    seen = set()
    deduped = []
    for f in facts_list:
        f_en = (f.get("fact_en") or "").strip()
        if not f_en:
            continue
        lower = f_en.lower()
        if "provided text does not contain" in lower or "no factual information" in lower:
            continue
        if "cannot extract" in lower or "image is blank" in lower:
            continue
        norm = normalize_text(f_en)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        deduped.append(
            {
                "fact_en": f_en,
                "fact_ta": (f.get("fact_ta") or "").strip(),
                "source": (f.get("source") or "").strip(),
                "context_en": (f.get("context_en") or "").strip(),
                "context_ta": (f.get("context_ta") or "").strip(),
            }
        )
    return deduped


def process_page_task(topic_name, book_name, page_idx, api_key):
    book_path = books[book_name]
    if not os.path.exists(book_path):
        print(f"    Missing PDF: {book_path}")
        return []

    doc = fitz.open(book_path)
    page_num = page_idx + 1
    try:
        if page_idx >= len(doc):
            print(f"    {book_name} P{page_num}: page index out of range (doc has {len(doc)} pages)")
            return []
        page = doc[page_idx]
        page_text = page.get_text().strip()
        if len(page_text) >= 80:
            print(f"    {book_name} P{page_num}: Querying Gemini API (Text)...")
            return call_gemini_extraction_text(
                topic_name, book_name, page_num, page_text, api_key
            )

        print(f"    {book_name} P{page_num}: Little/no text; rendering page as image...")
        pix = page.get_pixmap(dpi=150)
        image_bytes = pix.tobytes("jpg")
        img_base64 = base64.b64encode(image_bytes).decode("utf-8")
    finally:
        doc.close()

    print(f"    {book_name} P{page_num}: Querying Gemini API (Image OCR)...")
    return call_gemini_extraction_image(topic_name, book_name, page_num, img_base64, api_key)


def main():
    parser = argparse.ArgumentParser(description="TVK fact extraction from usable PDFs")
    parser.add_argument(
        "--topic",
        default=None,
        help='Extract only this topic (e.g. "TVK Leaders"). Default: all empty topics.',
    )
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        sys.exit(1)

    print("Starting TVK fact extraction from usable PDFs...")
    print(f"Output: {OUTPUT_JSON}")
    print(f"Model: {MODEL}")

    selected = topics_mapping
    if args.topic:
        if args.topic not in topics_mapping:
            print(f"Error: Unknown topic '{args.topic}'. Known: {list(topics_mapping.keys())}")
            sys.exit(1)
        selected = {args.topic: topics_mapping[args.topic]}

    needed_books = set()
    for sources in selected.values():
        needed_books.update(sources.keys())
    for book_name in needed_books:
        path = books[book_name]
        exists = os.path.exists(path)
        print(f"  PDF [{book_name}]: {'OK' if exists else 'MISSING'} -> {path}")
        if not exists:
            sys.exit(1)

    db = {}
    if os.path.exists(OUTPUT_JSON):
        try:
            with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
                db = json.load(f)
            if not isinstance(db, dict):
                db = {}
            print(f"Loaded existing database with {len(db)} topics.")
        except Exception:
            print("Starting fresh database.")
            db = {}

    # Ensure second topic key exists (empty) when doing Leaders-first pass
    if "TVK Policies & Schemes" not in db:
        db["TVK Policies & Schemes"] = []

    for topic_name, sources in selected.items():
        if topic_name in db and len(db[topic_name]) > 0:
            print(f"Topic '{topic_name}' already has {len(db[topic_name])} facts. Skipping.")
            continue

        print(f"\n>>> Processing topic: '{topic_name}'...")
        tasks = []
        for book_name, page_indices in sources.items():
            for idx in page_indices:
                tasks.append((book_name, idx))

        if not tasks:
            print(f"  No pages mapped for '{topic_name}'.")
            continue

        print(f"  Spawning {len(tasks)} page extraction tasks for '{topic_name}'...")
        topic_facts = []

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                executor.submit(process_page_task, topic_name, book, idx, api_key): (book, idx)
                for book, idx in tasks
            }
            for future in as_completed(futures):
                book, idx = futures[future]
                try:
                    facts = future.result()
                    if not isinstance(facts, list):
                        facts = []
                    print(f"    Page {idx + 1} of {book}: Extracted {len(facts)} facts.")
                    topic_facts.extend(facts)
                except Exception as e:
                    print(f"    Error processing Page {idx + 1} of {book}: {e}")
                time.sleep(1)

        initial_count = len(topic_facts)
        deduped = deduplicate_facts(topic_facts)
        print(f"  Deduplicated for '{topic_name}': {initial_count} -> {len(deduped)} unique facts.")

        db[topic_name] = deduped
        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2, ensure_ascii=False)
        print(f"  Saved facts for '{topic_name}' to {OUTPUT_JSON}")

    print("\n==========================================")
    print("TVK FACT EXTRACTION COMPLETE!")
    for t, facts in db.items():
        print(f"  {t}: {len(facts)} facts")
    print("==========================================")


if __name__ == "__main__":
    main()
