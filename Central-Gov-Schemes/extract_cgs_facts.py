import fitz
import os
import sys
import json
import urllib.request
import urllib.error
import time
import re
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

api_key = os.environ.get("GEMINI_API_KEY")
output_json = "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/Central-Gov-Schemes/cgs_facts.json"

books = {
    "VetriIAS": "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/Data/Central-Gov-Schemes/Value Addition - Union Government Schemes - Final Print.pdf",
}

SUBJECT_EN = "Central Government Schemes"
SUBJECT_TA = "மத்திய அரசுத் திட்டங்கள்"

# 0-indexed PDF pages. Boundary pages may include the next ministry — prompt filters by topic.
topics_mapping = {
    "Ministry of Agriculture & Farmers Welfare": {
        "VetriIAS": [8, 9, 10, 11],
    },
    "Ministry of Consumer Affairs, Food and Public Distribution": {
        "VetriIAS": [11, 12],
    },
    "Ministry of Commerce & Industry": {
        "VetriIAS": [12, 13],
    },
    "Ministry of Chemicals and Fertilisers": {
        "VetriIAS": [13],
    },
    "Ministry of Corporate Affairs": {
        "VetriIAS": [13, 14],
    },
    "Ministry of Culture": {
        "VetriIAS": [14],
    },
    "Ministry of Communications": {
        "VetriIAS": [14],
    },
    "Ministry of Civil Aviation": {
        "VetriIAS": [14, 15],
    },
    "Ministry of Development of the North Eastern Region": {
        "VetriIAS": [15],
    },
    "Ministry of Earth Sciences": {
        "VetriIAS": [15, 16],
    },
    "Ministry of Education": {
        "VetriIAS": [16, 17, 18],
    },
    "Ministry of Electronics and Information Technology": {
        "VetriIAS": [18],
    },
    "Ministry of Environment, Forest and Climate Change": {
        "VetriIAS": [18, 19],
    },
    "Ministry of Finance": {
        "VetriIAS": [19, 20, 21],
    },
    "Ministry of Fisheries, Animal Husbandry and Dairying": {
        "VetriIAS": [21, 22],
    },
    "Ministry of Health & Family Welfare": {
        "VetriIAS": [22, 23, 24],
    },
    "Ministry of Heavy Industries": {
        "VetriIAS": [24, 25],
    },
    "Ministry of Home Affairs": {
        "VetriIAS": [25],
    },
    "Ministry of Housing and Urban Affairs (MOHUA)": {
        "VetriIAS": [25, 26, 27],
    },
    "Ministry of Jal Shakti": {
        "VetriIAS": [27, 28],
    },
    "Ministry of Labour & Employment": {
        "VetriIAS": [28, 29, 30],
    },
    "Ministry of Micro, Small & Medium Enterprises": {
        "VetriIAS": [30, 31, 32, 33],
    },
    "Ministry of Mines": {
        "VetriIAS": [33, 34],
    },
    "Ministry of Minority Affairs": {
        "VetriIAS": [34, 35],
    },
    "Ministry of New and Renewable Energy": {
        "VetriIAS": [35, 36, 37, 38],
    },
    "NITI Aayog": {
        "VetriIAS": [38, 39, 40, 41],
    },
    "Ministry of Panchayati Raj": {
        "VetriIAS": [41, 42, 43],
    },
    "Ministry of Petroleum and Natural Gas": {
        "VetriIAS": [43, 44, 45, 46],
    },
    "Ministry of Rural Development": {
        "VetriIAS": [46, 47, 48, 49, 50, 51],
    },
    "Ministry of Skill Development and Entrepreneurship": {
        "VetriIAS": [51, 52, 53],
    },
    "Ministry of Social Justice and Empowerment": {
        "VetriIAS": [53, 54, 55, 56],
    },
    "Ministry of Tribal Affairs": {
        "VetriIAS": [56, 57, 58, 59],
    },
    "Ministry of Women & Child Development": {
        "VetriIAS": [59, 60, 61],
    },
}

if not api_key:
    print("GEMINI_API_KEY not found.")
    sys.exit(1)

model = "gemini-3.1-flash-lite"
url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"


def call_gemini_extraction(topic_name, book_name, page_num, page_text):
    prompt = f"""
You are an expert TNPSC Group exam question setter specializing in Central / Union Government Schemes
(subject: {SUBJECT_EN} / {SUBJECT_TA}).

I have extracted a single page of text from "{book_name}" (PDF page {page_num}) for the topic:
"{topic_name}".

IMPORTANT: This page may also contain schemes from OTHER ministries. Extract facts ONLY for schemes
that belong to "{topic_name}". Ignore any other ministry's schemes on this page.

Perform an exhaustive, line-by-line fact extraction. Do not summarize or skip details.

EXTRACT EVERY SINGLE:
1. Scheme full name, acronym, launch/announcement date, completion/sunset date.
2. Implementing ministry, department, agency, or regulator.
3. Aim / objective of the scheme.
4. Key features (premium rates, benefit amounts, coverage %, eligibility, DBT, portals, sub-schemes).
5. Beneficiaries / target groups.
6. Budgets, outlays, hectare/cluster targets, statistical figures.
7. What the scheme replaced, converges with, or is linked to.

INSTRUCTIONS:
- Pull out at least 8-15 distinct factual points if present for this topic on the page.
- Keep each fact extremely concise, factual, atomic, and self-contained.
- Provide accurate bilingual translations (English & Tamil).
- For Tamil scheme names, prefer official-style Tamil with the English acronym in parentheses when useful
  (e.g. "பிரதான் மந்திரி கிசான் சம்மான் நிதி (PM-KISAN)").
- Tag each fact with the short scheme name/acronym in "scheme".

Format the output as a JSON array of objects:
[
  {{
    "fact_en": "Verifiable fact statement in English",
    "fact_ta": "Verifiable fact statement in Tamil",
    "scheme": "Short scheme name or acronym",
    "source": "{book_name}",
    "context_en": "Brief context in English",
    "context_ta": "Brief context in Tamil"
  }}
]

Return ONLY the raw JSON array. Do not add markdown backticks.

---
PAGE TEXT:
{page_text}
"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    headers = {"Content-Type": "application/json"}

    retries = 4
    delay = 6
    for attempt in range(retries):
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                res_data = response.read().decode("utf-8")
                res_json = json.loads(res_data)
                raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
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
                parsed = json.loads(raw_text)
                return parsed if isinstance(parsed, list) else []
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"    {book_name} P{page_num} [Attempt {attempt+1}/{retries}] Rate limited. Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2
            else:
                body = e.read().decode("utf-8", errors="ignore")
                print(f"    {book_name} P{page_num} [Attempt {attempt+1}/{retries}] HTTP {e.code}: {body[:200]}")
                time.sleep(3)
        except Exception as e:
            print(f"    {book_name} P{page_num} [Attempt {attempt+1}/{retries}] Error: {e}")
            time.sleep(3)
    return []


def normalize_text(text):
    return re.sub(r"[^a-zA-Z0-9\u0b80-\u0bff]", "", text or "").lower()


def deduplicate_facts(facts_list):
    seen = set()
    deduped = []
    for f in facts_list:
        norm = normalize_text(f.get("fact_en", ""))
        if not norm or norm in seen:
            continue
        seen.add(norm)
        deduped.append(f)
    return deduped


def process_page_task(topic_name, book_name, page_idx):
    book_path = books[book_name]
    doc = fitz.open(book_path)
    page_text = doc[page_idx].get_text()
    doc.close()
    if not page_text.strip():
        return []
    return call_gemini_extraction(topic_name, book_name, page_idx + 1, page_text)


def main():
    parser = argparse.ArgumentParser(description="Extract CGS facts from Vetri IAS English PDF")
    parser.add_argument("--topic", type=str, default="", help="Run only this topic name (exact match)")
    parser.add_argument("--force", action="store_true", help="Re-extract even if topic already has facts")
    args = parser.parse_args()

    print(f"Subject: {SUBJECT_EN} / {SUBJECT_TA}")
    print("Starting page-by-page fact extraction for Central Government Schemes...")

    db = {}
    if os.path.exists(output_json):
        try:
            with open(output_json, "r", encoding="utf-8") as f:
                db = json.load(f)
            print(f"Loaded existing database with {len(db)} topics.")
        except Exception:
            print("Starting fresh database.")

    topics = topics_mapping.items()
    if args.topic:
        if args.topic not in topics_mapping:
            print(f"Unknown topic: {args.topic}")
            print("Available topics:")
            for t in topics_mapping:
                print(f"  - {t}")
            sys.exit(1)
        topics = [(args.topic, topics_mapping[args.topic])]

    for topic_name, sources in topics:
        if (not args.force) and topic_name in db and len(db[topic_name]) > 0:
            print(f"Topic '{topic_name}' already has {len(db[topic_name])} facts. Skipping.")
            continue

        print(f"\n>>> Processing topic: '{topic_name}'...")
        tasks = []
        for book_name, page_indices in sources.items():
            for idx in page_indices:
                tasks.append((book_name, idx))

        if not tasks:
            print(f"  No pages mapped for '{topic_name}'.")
            db[topic_name] = []
            continue

        print(f"  Spawning {len(tasks)} page extraction tasks...")
        topic_facts = []

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                executor.submit(process_page_task, topic_name, book, idx): (book, idx)
                for book, idx in tasks
            }
            for future in as_completed(futures):
                book, idx = futures[future]
                try:
                    facts = future.result()
                    print(f"    Page {idx+1} of {book}: Extracted {len(facts)} facts.")
                    topic_facts.extend(facts)
                except Exception as e:
                    print(f"    Error processing Page {idx+1} of {book}: {e}")
                time.sleep(1)

        initial_count = len(topic_facts)
        deduped = deduplicate_facts(topic_facts)
        print(f"  Deduplicated for '{topic_name}': {initial_count} -> {len(deduped)} unique facts.")

        # Scheme subtopic summary
        schemes = {}
        for f in deduped:
            s = (f.get("scheme") or "General").strip()
            schemes[s] = schemes.get(s, 0) + 1
        print("  Schemes / subtopics:")
        for s, n in sorted(schemes.items(), key=lambda x: (-x[1], x[0])):
            print(f"    - {s}: {n}")

        db[topic_name] = deduped

        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2, ensure_ascii=False)
            f.write("\n")

    print("\nFact extraction finished.")
    print(f"Saved: {output_json}")


if __name__ == "__main__":
    main()
