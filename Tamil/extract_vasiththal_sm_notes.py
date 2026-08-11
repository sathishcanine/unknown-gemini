#!/usr/bin/env python3
"""
Extract Tamil Unit 5 வாசித்தல் / Reading Comprehension (SM Tamil Full Book) rules + examples via Gemini OCR.

Writes into Tamil/vasiththal_notes.json → topics[<id>].rules / .examples
Preserves existing pyq_samples (if any later).

Usage:
  python3 Tamil/extract_vasiththal_sm_notes.py --topic pathiyil_vinaigal
  python3 Tamil/extract_vasiththal_sm_notes.py --list
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

NOTES_PATH = os.path.join(BASE_DIR, "Tamil", "vasiththal_notes.json")
TOPICS_PATH = os.path.join(BASE_DIR, "Tamil", "vasiththal_topics.json")
SOURCE_MAP_PATH = os.path.join(BASE_DIR, "Tamil", "vasiththal_source_map.json")

MODELS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite"]
MAX_WORKERS = 2
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
        if pages and len(pages) == 2 and pages[0] is not None and pages[1] is not None:
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


def render_page_jpg_b64(doc, page_idx_0: int) -> str:
    page = doc[page_idx_0]
    pix = page.get_pixmap(dpi=160)
    return base64.b64encode(pix.tobytes("jpg")).decode("utf-8")


def call_gemini_sm_page(topic_name, pdf_page, printed_page, img_base64, api_key):
    prompt = f"""
You are extracting TNPSC General Tamil Unit 5 வாசித்தல் / Reading Comprehension (SM Tamil Full Book) NOTES from a scanned textbook page.

Topic focus: "{topic_name}"
PDF page: {pdf_page} | Printed page (footer): {printed_page}

Extract teaching content useful for MCQ practice:
1) RULES — how to answer comprehension MCQs:
   - how to pick correct answer from a given paragraph
   - how to infer meaning/detail/tone from text
   - how to read news/editorial/document content (where to find purpose, main point)
   - how to interpret simile/idiom/proverb meanings using given examples
2) EXAMPLES — any short sample passage/quote + the explanation/meaning shown on the same page.
   - For passage-based sections: keep short excerpts and the stated correct inference/answer.
   - For simile/idiom/proverb: keep input phrase and correct meaning/output.

Rules for extraction:
- Keep Tamil accurate. Prefer Tamil for rule_ta / note_ta.
- rule_en / short English gloss when clear; else "".
- Skip pure ads/branding/TOC-only lines.
- Skip full multi-page exam dumps (A–E options) if they are actually exam PYQ blocks.
  Still keep short worked examples that teach the comprehension strategy or meaning mapping.
- Do NOT invent rules/examples not visible on the page.

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
      "kind": "passage_example" | "inference_example" | "simile" | "idiom" | "proverb" | "document" | "other",
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

    last_err = None
    for model in MODELS:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
            f":generateContent?key={api_key}"
        )
        headers = {"Content-Type": "application/json"}
        retries = 4
        delay = 8
        attempt = 0
        while attempt < retries:
            req = urllib.request.Request(
                url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=120) as response:
                    res_json = json.loads(response.read().decode("utf-8"))
                    raw_text = (
                        res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                    )
                    if raw_text.startswith("```"):
                        raw_text = raw_text.split("\n", 1)[1]
                        if raw_text.endswith("```"):
                            raw_text = raw_text.rsplit("\n", 1)[0]
                    start_obj = raw_text.find("{")
                    if start_obj == -1:
                        raise ValueError("no json object")
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
                        data["_model"] = model
                        return {
                            "rules": data.get("rules") or [],
                            "examples": data.get("examples") or [],
                            "_model": model,
                        }
                    raise ValueError("not a dict")
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="ignore")
                last_err = f"HTTP {e.code}: {body[:120]}"
                if e.code in (429, 503):
                    print(f"    P{pdf_page} {model} HTTP {e.code}; retry in {delay}s...")
                    time.sleep(delay)
                    delay = min(delay * 2, 60)
                    attempt += 1
                    continue
                print(f"    P{pdf_page} {model} HTTP {e.code}; try next model")
                break
            except Exception as e:
                last_err = str(e)
                attempt += 1
                print(f"    P{pdf_page} {model} err: {e}; retry...")
                time.sleep(5)

    print(f"    P{pdf_page} FAILED: {last_err}")
    return {"rules": [], "examples": []}


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
        out.append(r)
    return out


def dedupe_examples(examples: list) -> list:
    seen = set()
    out = []
    for e in examples:
        if not isinstance(e, dict):
            continue
        inp = (e.get("input") or "").strip()
        outv = (e.get("output") or "").strip()
        kind = (e.get("kind") or "").strip()
        if not inp or not outv:
            continue
        key = normalize_key(inp) + "->" + normalize_key(outv) + ":" + normalize_key(kind)
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out


def extract_topic(topic_id: str, api_key: str):
    ranges = sm_page_ranges()
    if topic_id not in ranges:
        raise SystemExit(f"Topic '{topic_id}' not found in {SOURCE_MAP_PATH}")

    start_1, end_1 = ranges[topic_id]
    topic_name = topic_display_name(topic_id)

    doc = fitz.open(PDF_PATH)
    all_rules = []
    all_examples = []
    used_model = None

    # Keep extraction simple: per-topic small ranges; run per-page calls in parallel.
    def extract_one(pdf_page):
        printed = pdf_page - PDF_OFFSET
        b64 = render_page_jpg_b64(doc, pdf_page - 1)
        res = call_gemini_sm_page(topic_name, pdf_page, printed, b64, api_key)
        return pdf_page, res

    pages = list(range(start_1, end_1 + 1))
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(extract_one, p): p for p in pages}
        for fut in as_completed(futures):
            pdf_page, res = fut.result()
            used_model = used_model or res.get("_model")
            rules = res.get("rules") or []
            examples = res.get("examples") or []
            rules = [r for r in rules if isinstance(r, dict)]
            examples = [e for e in examples if isinstance(e, dict)]
            if not rules and not examples:
                continue
            printed = pdf_page - PDF_OFFSET
            print(f"  PDF p{pdf_page} (printed {printed:02d}): {len(rules)} rules, {len(examples)} examples")
            all_rules.extend(rules)
            all_examples.extend(examples)

    doc.close()

    rules = dedupe_rules(all_rules)
    examples = dedupe_examples(all_examples)

    notes = load_json(
        NOTES_PATH,
        {
            "subject": "Tamil",
            "unit": "Vasiththal",
            "version": 1,
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
        "model": used_model or MODELS[0],
    }

    has_pyq = bool(block.get("pyq_samples"))
    if rules or examples:
        block["status"] = "sm_notes_ready" if has_pyq else "sm_extracted"
        if len(examples) < 20:
            block["status"] = "notes_gap"
            block["gap_note"] = (
                "Thin SM pages for this topic. May need wider SM range or enrich from related SM lists."
            )
    elif has_pyq:
        block["status"] = "pyq_extracted"
    else:
        block["status"] = "empty"

    save_json(NOTES_PATH, notes)
    print(
        f"Saved {len(rules)} rules + {len(examples)} examples → {NOTES_PATH} [{topic_id}] status={block['status']}"
    )

    return len(rules), len(examples), block["status"]


def main():
    parser = argparse.ArgumentParser(
        description="Extract Unit 5 Vasiththal SM notes (rules+examples) via Gemini OCR"
    )
    parser.add_argument("--topic", help="topic id, e.g. pathiyil_vinaigal")
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

    n_rules, n_ex, status = extract_topic(args.topic, api_key)
    print(f"\nDone. rules={n_rules} examples={n_ex} status={status}")


if __name__ == "__main__":
    main()

