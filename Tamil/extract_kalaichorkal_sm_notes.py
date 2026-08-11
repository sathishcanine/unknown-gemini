#!/usr/bin/env python3
"""
Extract Kalaichorkal / Technical Terms (Unit 4) rules + examples from SM Tamil Full Book via Gemini OCR.

Writes into Tamil/kalaichorkal_notes.json → topics[<id>].rules / .examples
Preserves existing pyq_samples.

Usage:
  python3 Tamil/extract_sollagarathi_sm_notes.py --topic vakuppu_kalaichorkal
  python3 Tamil/extract_sollagarathi_sm_notes.py --list
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
NOTES_PATH = os.path.join(BASE_DIR, "Tamil", "kalaichorkal_notes.json")
TOPICS_PATH = os.path.join(BASE_DIR, "Tamil", "kalaichorkal_topics.json")
SOURCE_MAP_PATH = os.path.join(BASE_DIR, "Tamil", "kalaichorkal_source_map.json")

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


def call_gemini_sm_page(topic_name, pdf_page, printed_page, img_base64, api_key):
    prompt = f"""
You are extracting TNPSC General Tamil Unit 2 (கலைச் சொற்கள் (Technical Terms)) NOTES from a scanned textbook page.
Book: Santhosh Mani Academy — SM Tamil Full Book
Topic focus: "{topic_name}"
PDF page: {pdf_page}  |  Printed page (footer): {printed_page}

Extract teaching content useful for MCQ practice:

1) RULES — definitions, how to pick English↔Tamil technical term pairs across science, education, medicine, law, geography, media, IT.
2) EXAMPLES — EN→TA (or TA→EN) technical term pairs and domain headings.

Rules for extraction:
- Keep Tamil accurate. Prefer Tamil for rule_ta / note_ta.
- rule_en / short English gloss when clear; else "".
- For examples (antonyms / meaning pairs):
  - "input" = given word / left side
  - "output" = antonym / meaning / right side / correct form
  - "kind" = "term_pair" | "domain" | "example" | "other"
  - "note_ta" = brief Tamil note if the page explains why
- Skip pure ads, academy branding, TOC-only lines, blank decorative headers.
- Skip full multi-page practice MCQ dumps if they are only exam questions with A–E
  (those belong to PYQ extract). Still keep short worked examples that teach a rule.
- Do NOT invent rules or examples not visible on the page.
- Extract EVERY visible EN↔TA technical term pair. input=English (or left), output=Tamil (or right). note_ta=domain heading if present.

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
      "kind": "term_pair",
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
                    raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
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


ALLOWED_KINDS = {
    "term_pair",
    "domain",
    "meaning",
    "example",
    "other",
}


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
        if kind not in ALLOWED_KINDS:
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
    used_model = None

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
            used_model = data.get("_model") or used_model
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
            "unit": "Kalaichorkal",
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
                "Thin SM page for this topic; may enrich from related SM antonym lists "
                "or Unit-1 ethirchol pairs (same book) before generating many batches."
            )
    elif has_pyq:
        block["status"] = "pyq_extracted"
    else:
        block["status"] = "empty"

    save_json(NOTES_PATH, notes)
    print(
        f"Saved {len(rules)} rules + {len(examples)} examples → "
        f"{NOTES_PATH} [{topic_id}] status={block['status']}"
    )
    return len(rules), len(examples), block["status"]


def main():
    parser = argparse.ArgumentParser(
        description="Extract Unit 4 Kalaichorkal SM notes (rules+examples) via Gemini OCR"
    )
    parser.add_argument("--topic", help="topic id, e.g. vakuppu_kalaichorkal")
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
