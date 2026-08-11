#!/usr/bin/env python3
"""
Extract Ilakkanam rules + examples from SM Tamil Full Book (scanned) via Gemini OCR.

Writes into Tamil/ilakkanam_notes.json → topics[<id>].rules / .examples
Preserves existing pyq_samples.

Usage:
  python3 Tamil/extract_ilakkanam_sm_notes.py --topic pirithu_sertthu
  python3 Tamil/extract_ilakkanam_sm_notes.py --list
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
    BASE_DIR, "Data", "Tamil", "ilakanam", "SM TAMIL FULL BOOK 570 PAGES.pdf"
)
NOTES_PATH = os.path.join(BASE_DIR, "Tamil", "ilakkanam_notes.json")
TOPICS_PATH = os.path.join(BASE_DIR, "Tamil", "ilakkanam_topics.json")
SOURCE_MAP_PATH = os.path.join(BASE_DIR, "Tamil", "ilakkanam_source_map.json")

MODEL = "gemini-3.1-flash-lite"
MAX_WORKERS = 2
# SM: pdf_page = printed_page + 5
PDF_OFFSET = 5


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def sm_page_ranges() -> dict:
    """topic_id -> (pdf_start_1, pdf_end_1) inclusive."""
    smap = load_json(SOURCE_MAP_PATH, {})
    out = {}
    for tid, block in (smap.get("topics") or {}).items():
        pages = block.get("sm_pdf")
        if pages and len(pages) == 2:
            out[tid] = (int(pages[0]), int(pages[1]))
    return out


def topic_display_name(topic_id: str) -> str:
    topics = load_json(TOPICS_PATH, {})
    for t in topics.get("topics", []):
        if t.get("id") == topic_id:
            return t.get("name_ta") or topic_id
    notes = load_json(NOTES_PATH, {})
    block = (notes.get("topics") or {}).get(topic_id) or {}
    return block.get("name_ta") or topic_id


def call_gemini_sm_page(topic_name, pdf_page, printed_page, img_base64, api_key):
    prompt = f"""
You are extracting TNPSC General Tamil (Ilakkanam / இலக்கணம்) NOTES from a scanned textbook page.
Book: Santhosh Mani Academy — SM Tamil Full Book
Topic focus: "{topic_name}"
PDF page: {pdf_page}  |  Printed page (footer): {printed_page}

Extract teaching content useful for MCQ practice:

1) RULES — grammar principles, sandhi/join/split formulas, definitions, tip boxes.
2) EXAMPLES — word pairs / transforms shown as பிரித்து / சேர்த்து / before→after.

Rules for extraction:
- Keep Tamil accurate. Prefer Tamil for rule_ta / note_ta.
- rule_en / short English gloss when clear; else "".
- For examples:
  - "input" = joined form OR left side of → / = / +
  - "output" = split form (e.g. "கல் + அம்பகம்") OR joined result
  - "kind" = "pirithu" | "sertthu" | "both" | "other"
  - "note_ta" = brief Tamil note if the page explains why
- Skip pure ads, academy branding, TOC-only lines, blank decorative headers.
- Skip full multi-page practice MCQ dumps if they are only exam questions with A–E
  (those belong to PYQ extract). Still keep short worked examples that teach a rule.
- Do NOT invent rules or examples not visible on the page.
- If the page is mostly tables of examples, extract many examples; rules may be few.

Return ONLY JSON object:
{{
  "rules": [
    {{
      "rule_ta": "...",
      "rule_en": "...",
      "source": "sm",
      "source_page": {printed_page}
    }}
  ],
  "examples": [
    {{
      "input": "...",
      "output": "...",
      "kind": "pirithu",
      "note_ta": "...",
      "source": "sm",
      "source_page": {printed_page}
    }}
  ]
}}
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
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}"
        f":generateContent?key={api_key}"
    )
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
                # Prefer object {...}
                start_obj = raw_text.find("{")
                start_arr = raw_text.find("[")
                if start_obj != -1 and (start_arr == -1 or start_obj < start_arr):
                    count = 0
                    for idx in range(start_obj, len(raw_text)):
                        if raw_text[idx] == "{":
                            count += 1
                        elif raw_text[idx] == "}":
                            count -= 1
                            if count == 0:
                                raw_text = raw_text[start_obj : idx + 1]
                                break
                    data = json.loads(raw_text.strip())
                    if isinstance(data, dict):
                        return {
                            "rules": data.get("rules") or [],
                            "examples": data.get("examples") or [],
                        }
                return {"rules": [], "examples": []}
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            if e.code in (429, 503):
                print(f"    P{pdf_page} HTTP {e.code}; retry in {delay}s...")
                time.sleep(delay)
                delay = min(delay * 2, 60)
            else:
                attempt += 1
                print(f"    P{pdf_page} [Attempt {attempt}/{retries}] HTTP {e.code}: {body[:180]}")
                time.sleep(5)
        except Exception as e:
            attempt += 1
            print(f"    P{pdf_page} [Attempt {attempt}/{retries}] Error: {e}")
            time.sleep(5)
    return {"rules": [], "examples": []}


def render_page_jpg_b64(doc, page_idx_0: int) -> str:
    page = doc[page_idx_0]
    pix = page.get_pixmap(dpi=160)
    return base64.b64encode(pix.tobytes("jpg")).decode("utf-8")


def normalize_key(text: str) -> str:
    return re.sub(r"\s+", "", (text or "")).lower()


def dedupe_rules(rules: list) -> list:
    seen = set()
    out = []
    for r in rules:
        if not isinstance(r, dict):
            continue
        ta = (r.get("rule_ta") or "").strip()
        if not ta:
            continue
        key = normalize_key(ta)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "rule_ta": ta,
                "rule_en": (r.get("rule_en") or "").strip(),
                "source": r.get("source") or "sm",
                "source_page": r.get("source_page"),
            }
        )
    return out


def dedupe_examples(examples: list) -> list:
    seen = set()
    out = []
    for e in examples:
        if not isinstance(e, dict):
            continue
        inp = (e.get("input") or "").strip()
        outp = (e.get("output") or "").strip()
        if not inp and not outp:
            continue
        key = normalize_key(f"{inp}|{outp}")
        if key in seen:
            continue
        seen.add(key)
        kind = (e.get("kind") or "other").strip().lower()
        if kind not in ("pirithu", "sertthu", "both", "other"):
            kind = "other"
        out.append(
            {
                "input": inp,
                "output": outp,
                "kind": kind,
                "note_ta": (e.get("note_ta") or "").strip(),
                "source": e.get("source") or "sm",
                "source_page": e.get("source_page"),
            }
        )
    return out


def extract_topic(topic_id: str, api_key: str):
    ranges = sm_page_ranges()
    if topic_id not in ranges:
        raise SystemExit(f"Unknown topic_id / no SM page map: {topic_id}")
    if not os.path.exists(PDF_PATH):
        raise SystemExit(f"Missing PDF: {PDF_PATH}")

    start_1, end_1 = ranges[topic_id]
    topic_name = topic_display_name(topic_id)
    print(f"\n=== SM {topic_id} ({topic_name}) PDF pages {start_1}-{end_1} ===")

    doc = fitz.open(PDF_PATH)
    page_indices = list(range(start_1 - 1, min(end_1, len(doc))))

    rendered = []
    for idx in page_indices:
        pdf_page = idx + 1
        printed = pdf_page - PDF_OFFSET
        print(f"  Render PDF p{pdf_page} (printed {printed:02d})...")
        rendered.append((pdf_page, printed, render_page_jpg_b64(doc, idx)))
    doc.close()

    all_rules = []
    all_examples = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = {
            ex.submit(
                call_gemini_sm_page, topic_name, pdf_page, printed, img_b64, api_key
            ): (pdf_page, printed)
            for pdf_page, printed, img_b64 in rendered
        }
        for fut in as_completed(futs):
            pdf_page, printed = futs[fut]
            try:
                data = fut.result() or {"rules": [], "examples": []}
            except Exception as e:
                print(f"  PDF p{pdf_page} failed: {e}")
                data = {"rules": [], "examples": []}
            rules = data.get("rules") or []
            examples = data.get("examples") or []
            # ensure source_page stamped
            for r in rules:
                if isinstance(r, dict) and r.get("source_page") is None:
                    r["source_page"] = printed
            for e in examples:
                if isinstance(e, dict) and e.get("source_page") is None:
                    e["source_page"] = printed
            print(
                f"  PDF p{pdf_page} (printed {printed:02d}): "
                f"{len(rules)} rules, {len(examples)} examples"
            )
            all_rules.extend(rules)
            all_examples.extend(examples)

    rules = dedupe_rules(all_rules)
    examples = dedupe_examples(all_examples)

    notes = load_json(
        NOTES_PATH,
        {
            "subject": "Tamil",
            "unit": "Ilakkanam",
            "version": 2,
            "topics": {},
        },
    )
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
    block["name_ta"] = block.get("name_ta") or topic_name
    block["rules"] = rules
    block["examples"] = examples
    # preserve pyq_samples
    block.setdefault("pyq_samples", block.get("pyq_samples") or [])
    block.setdefault("sources", {})
    block["sources"]["sm_pdf_pages"] = [start_1, end_1]
    block["sources"]["sm_printed_pages"] = [
        start_1 - PDF_OFFSET,
        end_1 - PDF_OFFSET,
    ]
    block["sm_extract_meta"] = {
        "pdf": "SM TAMIL FULL BOOK 570 PAGES.pdf",
        "pdf_pages": [start_1, end_1],
        "printed_pages": [start_1 - PDF_OFFSET, end_1 - PDF_OFFSET],
        "rules_count": len(rules),
        "examples_count": len(examples),
        "model": MODEL,
    }
    has_pyq = bool(block.get("pyq_samples"))
    if rules or examples:
        block["status"] = "sm_notes_ready" if has_pyq else "sm_extracted"
    elif has_pyq:
        block["status"] = "pyq_extracted"
    else:
        block["status"] = "empty"

    save_json(NOTES_PATH, notes)
    print(
        f"Saved {len(rules)} rules + {len(examples)} examples → "
        f"{NOTES_PATH} [{topic_id}] (pyq_samples={len(block.get('pyq_samples') or [])})"
    )
    return len(rules), len(examples)


def main():
    parser = argparse.ArgumentParser(
        description="Extract Ilakkanam SM notes (rules+examples) via Gemini OCR"
    )
    parser.add_argument("--topic", help="topic id, e.g. pirithu_sertthu")
    parser.add_argument("--list", action="store_true", help="List SM-mapped topic ids")
    args = parser.parse_args()

    ranges = sm_page_ranges()
    if args.list:
        for tid, pages in ranges.items():
            print(f"{tid}: PDF {pages[0]}-{pages[1]}")
        return

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY not found.")

    if not args.topic:
        raise SystemExit("Pass --topic <id>")

    n_rules, n_ex = extract_topic(args.topic, api_key)
    print(f"\nDone. rules={n_rules} examples={n_ex}")


if __name__ == "__main__":
    main()
