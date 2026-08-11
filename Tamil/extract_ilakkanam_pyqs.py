#!/usr/bin/env python3
"""
Extract TNPSC Ilakkanam PYQ samples from scanned PDF pages via Gemini OCR.

Writes into Tamil/ilakkanam_notes.json → topics[<id>].pyq_samples

Usage:
  python3 Tamil/extract_ilakkanam_pyqs.py --topic pirithu_sertthu
  python3 Tamil/extract_ilakkanam_pyqs.py --topic ethirchol
  python3 Tamil/extract_ilakkanam_pyqs.py --all-pilots
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

import fitz

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_PATH = os.path.join(
    BASE_DIR, "Data", "Tamil", "ilakanam", "Tamil Part A illakanam previous.pdf"
)
NOTES_PATH = os.path.join(BASE_DIR, "Tamil", "ilakkanam_notes.json")
TOPICS_PATH = os.path.join(BASE_DIR, "Tamil", "ilakkanam_topics.json")

MODEL = "gemini-3.1-flash-lite"
MAX_WORKERS = 2

# 1-based inclusive page ranges from ILAKKANAM_SOURCE_MAP.md
TOPIC_PAGES = {
    "pirithu_sertthu": (58, 71),
    "ethirchol": (72, 80),
    "sandhi_otru_pizhai": (95, 101),
    "orumai_panmai": (102, 108),
    "ayarchol_tamilchol": (125, 145),
    "kuril_nedil": (146, 157),  # ஒலி வேறுபாடு section — filter to குறில்/நெடில்
    "la_na_ra_bedham": (146, 157),
    "verchol": (169, 178),
    "verchol_derivatives": (179, 188),
}

PILOT_TOPICS = ["pirithu_sertthu", "ethirchol"]


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def topic_display_name(topic_id: str) -> str:
    topics = load_json(TOPICS_PATH, {})
    for t in topics.get("topics", []):
        if t.get("id") == topic_id:
            return t.get("name_ta") or topic_id
    notes = load_json(NOTES_PATH, {})
    block = (notes.get("topics") or {}).get(topic_id) or {}
    return block.get("name_ta") or topic_id


def call_gemini_pyq_page(topic_name, page_num, img_base64, api_key):
    prompt = f"""
You are extracting TNPSC General Tamil (Ilakkanam) PREVIOUS YEAR MCQs from a scanned page image.
Topic focus: "{topic_name}"
PDF page number: {page_num}

Extract EVERY multiple-choice question visible on this page.

Rules:
- Keep Tamil text accurate (do not translate away the question stem).
- Options are usually A–E. Option E is often "விடை தெரியவில்லை" / "Answer not known".
- If a handwritten checkmark / tick marks the correct option, set correct_option to that key.
- If correct answer is unclear, set correct_option to "".
- Ignore headers like WISDOM KRISHNA ACADEMY, TOTAL QUESTIONS, YouTube ads.
- Ignore partial questions cut off at page edges if stem+options are incomplete.
- Do NOT invent questions not visible on the page.

Return ONLY a JSON array:
[
  {{
    "question_ta": "full question stem in Tamil (and English fragments if printed)",
    "question_en": "short English gloss of the task if possible, else empty string",
    "options": [
      {{"key": "A", "text_ta": "...", "text_en": ""}},
      {{"key": "B", "text_ta": "...", "text_en": ""}}
    ],
    "correct_option": "A",
    "source_exam": "PYQ",
    "source_page": {page_num}
  }}
]
"""
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {"inlineData": {"mimeType": "image/jpeg", "data": img_base64}},
                ]
            }
        ],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    retries = 5
    delay = 10
    attempt = 0
    while attempt < retries:
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
                data = json.loads(raw_text.strip())
                return data if isinstance(data, list) else []
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            if e.code in (429, 503):
                print(f"    P{page_num} HTTP {e.code}; retry in {delay}s...")
                time.sleep(delay)
                delay = min(delay * 2, 60)
            else:
                attempt += 1
                print(f"    P{page_num} [Attempt {attempt}/{retries}] HTTP {e.code}: {body[:180]}")
                time.sleep(5)
        except Exception as e:
            attempt += 1
            print(f"    P{page_num} [Attempt {attempt}/{retries}] Error: {e}")
            time.sleep(5)
    return []


def render_page_jpg_b64(doc, page_idx_0: int) -> str:
    page = doc[page_idx_0]
    pix = page.get_pixmap(dpi=160)
    return base64.b64encode(pix.tobytes("jpg")).decode("utf-8")


def normalize_q(text: str) -> str:
    return re.sub(r"\s+", "", (text or "")).lower()


def dedupe_samples(samples: list) -> list:
    seen = set()
    out = []
    for s in samples:
        q = (s.get("question_ta") or s.get("question_en") or "").strip()
        if not q:
            continue
        key = normalize_q(q)
        if key in seen:
            continue
        seen.add(key)
        opts = s.get("options") or []
        norm_opts = []
        for o in opts:
            if isinstance(o, dict):
                norm_opts.append(
                    {
                        "key": str(o.get("key") or "").strip().upper()[:1],
                        "text_ta": (o.get("text_ta") or o.get("text_en") or "").strip(),
                        "text_en": (o.get("text_en") or "").strip(),
                    }
                )
        out.append(
            {
                "question_ta": (s.get("question_ta") or "").strip(),
                "question_en": (s.get("question_en") or "").strip(),
                "options": norm_opts,
                "correct_option": str(s.get("correct_option") or "").strip().upper()[:1],
                "source_exam": s.get("source_exam") or "PYQ",
                "source_page": s.get("source_page"),
            }
        )
    return out


def extract_topic(topic_id: str, api_key: str):
    if topic_id not in TOPIC_PAGES:
        raise SystemExit(f"Unknown topic_id / no page map: {topic_id}")
    if not os.path.exists(PDF_PATH):
        raise SystemExit(f"Missing PDF: {PDF_PATH}")

    start_1, end_1 = TOPIC_PAGES[topic_id]
    topic_name = topic_display_name(topic_id)
    print(f"\n=== {topic_id} ({topic_name}) pages {start_1}-{end_1} ===")

    doc = fitz.open(PDF_PATH)
    page_indices = list(range(start_1 - 1, min(end_1, len(doc))))
    collected = []

    def job(page_idx_0):
        page_num = page_idx_0 + 1
        print(f"  Rendering+OCR page {page_num}...")
        img_b64 = render_page_jpg_b64(doc, page_idx_0)
        qs = call_gemini_pyq_page(topic_name, page_num, img_b64, api_key)
        print(f"  P{page_num}: got {len(qs)} questions")
        return qs

    # Sequential render is safer with shared doc; parallelize API calls via pre-render
    rendered = []
    for idx in page_indices:
        page_num = idx + 1
        print(f"  Render page {page_num}...")
        rendered.append((page_num, render_page_jpg_b64(doc, idx)))
    doc.close()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = {
            ex.submit(call_gemini_pyq_page, topic_name, page_num, img_b64, api_key): page_num
            for page_num, img_b64 in rendered
        }
        for fut in as_completed(futs):
            page_num = futs[fut]
            try:
                qs = fut.result() or []
            except Exception as e:
                print(f"  P{page_num} failed: {e}")
                qs = []
            print(f"  P{page_num}: {len(qs)} questions")
            collected.extend(qs)

    samples = dedupe_samples(collected)
    notes = load_json(NOTES_PATH, {"topics": {}})
    if "topics" not in notes:
        notes["topics"] = {}
    if topic_id not in notes["topics"]:
        notes["topics"][topic_id] = {
            "name_ta": topic_name,
            "rules": [],
            "examples": [],
            "pyq_samples": [],
            "sources": {},
            "status": "empty",
        }

    block = notes["topics"][topic_id]
    # replace pyq_samples for this topic (re-run safe)
    block["pyq_samples"] = samples
    block["name_ta"] = block.get("name_ta") or topic_name
    has_sm = bool(block.get("rules") or block.get("examples"))
    if samples and has_sm:
        block["status"] = "sm_notes_ready"
    elif samples:
        block["status"] = "pyq_extracted"
    elif has_sm:
        block["status"] = "sm_extracted"
    else:
        block["status"] = "empty"
    block.setdefault("sources", {})["pyq_pages"] = [start_1, end_1]
    block["pyq_extract_meta"] = {
        "pdf": "Tamil Part A illakanam previous.pdf",
        "pages": [start_1, end_1],
        "count": len(samples),
        "model": MODEL,
    }
    save_json(NOTES_PATH, notes)
    print(f"Saved {len(samples)} PYQ samples → {NOTES_PATH} [{topic_id}]")
    return len(samples)


def main():
    parser = argparse.ArgumentParser(description="Extract Ilakkanam PYQ samples via Gemini OCR")
    parser.add_argument("--topic", help="topic id, e.g. pirithu_sertthu")
    parser.add_argument("--all-pilots", action="store_true", help="Extract pirithu_sertthu + ethirchol")
    parser.add_argument(
        "--list",
        action="store_true",
        help="List mapped topic ids",
    )
    args = parser.parse_args()

    if args.list:
        for tid, pages in TOPIC_PAGES.items():
            print(f"{tid}: pages {pages[0]}-{pages[1]}")
        return

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY not found.")

    if args.all_pilots:
        topics = PILOT_TOPICS
    elif args.topic:
        topics = [args.topic]
    else:
        raise SystemExit("Pass --topic <id> or --all-pilots")

    total = 0
    for tid in topics:
        total += extract_topic(tid, api_key)
    print(f"\nDone. Total PYQ samples extracted this run: {total}")


if __name__ == "__main__":
    main()
