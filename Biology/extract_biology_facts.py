"""
Fact extraction from TN Govt Biology English notes (TNPSC Group II).

Source: Data/Biology/Biology tn govt eng.pdf
Prefer page TEXT (Unicode English). Skip telegram watermarks / copyright covers.

Usage:
  python3 Biology/extract_biology_facts.py --topic "The Cell — Basic Unit of Life"
  python3 Biology/extract_biology_facts.py --topic "The Cell — Basic Unit of Life" --force
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

import fitz

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from gemini_keys import DEFAULT_KEY, FALLBACK_KEYS  # noqa: E402

PDF_PATH = os.path.join(BASE_DIR, "Data", "Biology", "Biology tn govt eng.pdf")
OUTPUT_JSON = os.path.join(BASE_DIR, "Biology", "biology_facts.json")
MODEL = "gemini-3.1-flash-lite"
BOOK_NAME = "Biology TN Govt Eng (Employment & Training)"

# User-approved pool: DEFAULT_KEY + 4× AQ keys only
KEY_POOL = [DEFAULT_KEY] + [k for k in FALLBACK_KEYS if k.startswith("AQ.")]

# Syllabus topics (user Tamil TOC) → 0-indexed pages in TN govt PDF
# Skip cover-only / telegram-only pages inside each range at runtime.
topics_mapping = {
    "The Cell — Basic Unit of Life": list(range(39, 60)),  # PDF 40–60 Cell Biology
    "Classification of Living Organisms": list(range(0, 39)),  # PDF 1–39
    "Nutrition and Food Habits": list(range(128, 137)),  # PDF 129–137 Nutrition & Dietetics
    "Respiration": list(range(60, 71)),  # PDF 61–71
    "Blood and Circulation": list(range(71, 91)),  # PDF 72–91 Circulation + Blood
    "Endocrine System": list(range(91, 103)),  # PDF 92–103
    "Reproductive System": list(range(103, 116)),  # PDF 104–116
    "Genetics — Mendelism": list(range(116, 128)),  # PDF 117–128 Genetics
    "Environment and Organism Life": list(range(162, 206)),  # PDF 163–206 Ecology
    "Biodiversity and Conservation": list(range(154, 162)),  # PDF 155–162
    "Human Diseases — Prevention and Control": list(range(137, 147)),  # PDF 138–147
    # Book has no dedicated alcohol chapter; closest = Health & Hygiene (vaccines/nutrition)
    "Alcoholism and Drug Addiction": list(range(147, 154)),  # PDF 148–154 Health & Hygine
}

_key_idx = 0
_rate_limit_hits = 0
_disabled_keys = set()


def next_api_key() -> str:
    global _key_idx
    if not KEY_POOL:
        raise SystemExit("KEY_POOL empty")
    for _ in range(len(KEY_POOL) * 2):
        key = KEY_POOL[_key_idx % len(KEY_POOL)]
        _key_idx += 1
        if key not in _disabled_keys:
            return key
    raise SystemExit(f"All {len(KEY_POOL)} keys disabled for model {MODEL}")


def disable_key(api_key: str, reason: str):
    if api_key in _disabled_keys:
        return
    _disabled_keys.add(api_key)
    tag = "DEFAULT" if api_key == DEFAULT_KEY else ("AQ" if api_key.startswith("AQ.") else "key")
    print(f"    ⚠ Disabling {tag}…{api_key[-6:]} for {MODEL}: {reason}")


def note_rate_limit(page_num: int, code: int, delay: int):
    global _rate_limit_hits
    _rate_limit_hits += 1
    print(
        f"    ⚠ RATE LIMIT HTTP {code} on P{page_num} "
        f"(hit #{_rate_limit_hits}); rotate key, sleep {delay}s..."
    )


def clean_page_text(raw: str) -> str:
    lines = []
    for ln in (raw or "").splitlines():
        s = ln.strip()
        if not s:
            continue
        if "t.me/tnpscfree" in s.lower():
            continue
        if "virtual learning portal" in s.lower():
            continue
        lines.append(s)
    return "\n".join(lines)


def is_skip_page(text: str) -> bool:
    t = (text or "").strip()
    if len(t) < 80:
        return True
    if "Department of Employment and Training" in t and "Topic" in t and len(t) < 1200:
        # copyright cover with little content
        if "Copyright" in t and t.count("\n") < 25:
            return True
    return False


def call_gemini_extraction_text(topic_name: str, page_num: int, page_text: str, api_key: str):
    prompt = f"""
You are an expert TNPSC Group exam Biology question setter (Botany + Zoology).
This is Page {page_num} text from "{BOOK_NAME}" for topic: "{topic_name}".

Perform exhaustive, line-by-line fact extraction. Do not summarize or skip bullets/tables.

EXTRACT EVERY SINGLE:
1. Definitions, classifications, comparisons, kingdom/criteria tables.
2. Scientist names, discovery years, theories/laws.
3. Structure/function of organelles, organs, systems, hormones, pathogens.
4. Processes, pathways, equations, cycles, Mendelian ratios.
5. Numbers, percentages, chromosome counts, sizes (nm), BP, vaccine schedules.
6. Disease names, pathogens, hosts, symptoms, prevention, vaccines, drugs.
7. Ecological terms, biodiversity, conservation acts/movements when listed.

INSTRUCTIONS:
- Prefer 8–20 distinct factual points per content-rich page.
- Each fact MUST be a specific, testable statement.
- Fix obvious typos in the English fact (e.g. Kindgoms→Kingdoms) but keep meaning.
- Skip headers/footers, copyright, telegram links.
- Output bilingual facts: accurate English + accurate Tamil Unicode.
- Short biology context in both languages.

Return ONLY a raw JSON array:
[
  {{
    "fact_en": "...",
    "fact_ta": "...",
    "source": "{BOOK_NAME} Page {page_num}",
    "context_en": "Short context",
    "context_ta": "சுருங்கிய சூழல்"
  }}
]

---
PAGE TEXT:
{page_text}
"""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    return post_request(payload, page_num, api_key)


def post_request(payload, page_num, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    retries = 5
    delay = 8
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                res_json = json.loads(response.read().decode("utf-8"))
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
            body = e.read().decode("utf-8", errors="ignore")
            if e.code in (429, 503):
                note_rate_limit(page_num, e.code, delay)
                time.sleep(delay)
                delay = min(delay * 2, 60)
                api_key = next_api_key()
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
            elif e.code == 404 and "no longer available" in body.lower():
                disable_key(api_key, "model not available to this key")
                try:
                    api_key = next_api_key()
                except SystemExit as se:
                    print(f"    P{page_num}: {se}")
                    return []
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
                continue
            else:
                print(f"    P{page_num} [Attempt {attempt}/{retries}] HTTP {e.code}: {body[:180]}")
                time.sleep(4)
                api_key = next_api_key()
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
        except Exception as e:
            print(f"    P{page_num} [Attempt {attempt}/{retries}] Error: {e}")
            time.sleep(4)
            try:
                api_key = next_api_key()
            except SystemExit as se:
                print(f"    P{page_num}: {se}")
                return []
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
    return []


def normalize_text(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9\u0b80-\u0bff]", "", text).lower()


def deduplicate_facts(facts_list):
    seen = set()
    deduped = []
    for f in facts_list:
        f_en = (f.get("fact_en") or "").strip()
        if not f_en:
            continue
        lower = f_en.lower()
        if any(
            x in lower
            for x in (
                "provided text does not contain",
                "no factual information",
                "cannot extract",
                "image is blank",
                "unable to read",
            )
        ):
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


def process_page_task(topic_name: str, page_idx: int):
    page_num = page_idx + 1
    doc = fitz.open(PDF_PATH)
    try:
        if page_idx >= len(doc):
            print(f"    P{page_num}: out of range")
            return []
        raw = doc[page_idx].get_text("text")
        text = clean_page_text(raw)
        if is_skip_page(text):
            print(f"    P{page_num}: skip (cover/empty/watermark)")
            return []
    finally:
        doc.close()

    api_key = next_api_key()
    print(f"    P{page_num}: Gemini text extract ({len(text)} chars)...")
    return call_gemini_extraction_text(topic_name, page_num, text, api_key)


def main():
    parser = argparse.ArgumentParser(description="Biology fact extraction (TN govt Eng PDF)")
    parser.add_argument("--topic", default=None, help="Extract only this topic (required)")
    parser.add_argument("--force", action="store_true", help="Re-extract even if facts exist")
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()

    if not os.path.exists(PDF_PATH):
        print(f"Error: PDF missing: {PDF_PATH}")
        sys.exit(1)

    if not args.topic:
        print("Extract one topic at a time:")
        for t in topics_mapping:
            print(f"  - {t}")
        sys.exit(1)
    if args.topic not in topics_mapping:
        print(f"Error: Unknown topic. Known:\n  " + "\n  ".join(topics_mapping.keys()))
        sys.exit(1)
    selected = {args.topic: topics_mapping[args.topic]}

    db = {}
    if os.path.exists(OUTPUT_JSON):
        try:
            with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
                db = json.load(f)
            if not isinstance(db, dict):
                db = {}
        except Exception:
            db = {}

    for t in topics_mapping:
        db.setdefault(t, [])

    print(f"PDF: {PDF_PATH}")
    print(f"Output: {OUTPUT_JSON}")
    print(f"Model: {MODEL} | API key pool: {len(KEY_POOL)} keys (DEFAULT + 4× AQ)")
    global _rate_limit_hits, _disabled_keys
    _rate_limit_hits = 0
    _disabled_keys = set()

    for topic_name, pages in selected.items():
        if db.get(topic_name) and not args.force:
            print(f"Topic '{topic_name}' already has {len(db[topic_name])} facts. Use --force to redo.")
            continue

        print(f"\n>>> {topic_name} ({len(pages)} mapped pages)...")
        topic_facts = []
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
            futures = {
                executor.submit(process_page_task, topic_name, idx): idx for idx in pages
            }
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    facts = future.result() or []
                    print(f"    Page {idx + 1}: {len(facts)} facts")
                    topic_facts.extend(facts)
                except Exception as e:
                    print(f"    Page {idx + 1} error: {e}")
                time.sleep(0.5)

        deduped = deduplicate_facts(topic_facts)
        print(f"  Deduped {len(topic_facts)} → {len(deduped)}")
        prev = len(db.get(topic_name) or [])
        if not deduped and prev > 0:
            print(f"  WARN: 0 new facts; keeping previous {prev}.")
        else:
            db[topic_name] = deduped
            with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
                json.dump(db, f, indent=2, ensure_ascii=False)
            print(f"  Saved '{topic_name}' ({len(deduped)} facts)")

    print("\n========== BIOLOGY FACT EXTRACTION ==========")
    for t, facts in db.items():
        print(f"  {t}: {len(facts)} facts")
    if _rate_limit_hits:
        print(f"\n⚠ RATE LIMIT SUMMARY: {_rate_limit_hits} HTTP 429/503 hits.")
    print("=============================================")


if __name__ == "__main__":
    main()
