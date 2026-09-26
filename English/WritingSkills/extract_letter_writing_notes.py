#!/usr/bin/env python3
"""
Extract Letter Writing (Formal & Informal — Types of Letters) notes for Unit III.

Primary:   Unit3,4/vetrii english unit 3 and unit 4.pdf pp.1–14 (vision)
Secondary: Unit3,4/asan-unit3-eng.pdf pp.1–14 (vision)
           Grammer.pdf letter-writing pages (text)

Output: English/WritingSkills/letter_writing_notes.json
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
from collections import defaultdict

import fitz

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VETRII_PDF = os.path.join(
    BASE_DIR, "Data", "General-English", "Unit3,4", "vetrii english unit 3 and unit 4.pdf"
)
ASAN_PDF = os.path.join(BASE_DIR, "Data", "General-English", "Unit3,4", "asan-unit3-eng.pdf")
GRAMMER_PDF = os.path.join(BASE_DIR, "Data", "General-English", "Grammer.pdf")
NOTES_PATH = os.path.join(BASE_DIR, "English", "WritingSkills", "letter_writing_notes.json")
CACHE_DIR = os.path.join(BASE_DIR, "English", "WritingSkills", "_tmp_letter_writing_extract_cache")

MODEL = "gemini-3.1-flash-lite"
VETRII_PAGES = list(range(1, 15))
ASAN_PAGES = list(range(1, 15))
GRAMMER_PAGES = [274, 275, 276, 277, 278, 279, 280, 282, 287]

SCHEMA = """
Return ONLY JSON:
{
  "page_heading": "short heading if visible",
  "rules": [{"rule_en": "...", "lw_tag": "definition|format|formal|informal|complimentary_close|salutation|date|other", "source": "vetrii|asan|grammer", "source_page": N}],
  "examples": [{"letter_type_en": "Enquiry letter", "category_en": "formal|informal", "note_en": "...", "lw_tag": "enquiry|complaint|business|invitation|apology|order|resignation|job_application|permission|editor|informal|other", "source": "...", "source_page": N}],
  "letter_parts": [{"part_en": "Sender's address", "order_num": 1, "applies_to": "formal|informal|both", "note_en": "...", "source": "...", "source_page": N}],
  "worked_exercises": [{"prompt_en": "...", "answer_en": "...", "options_en": ["A","B","C","D"], "lw_tag": "choose_correct|fill_blank|match|statement|other", "source": "...", "source_page": N}]
}
Extract letter-writing content ONLY: formal/informal types, parts/order, complimentary closes, formats.
MCQ / match / fill WITH answers → worked_exercises (include full options when visible).
Letter type examples → examples. Part sequence → letter_parts. Tips → rules.
Do NOT invent content not on the page.
"""


def save_json(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def call_gemini_json(parts, api_key, label="") -> dict:
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}"
        f":generateContent?key={api_key}"
    )
    delay = 10
    for attempt in range(6):
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as response:
                raw = json.loads(response.read().decode("utf-8"))["candidates"][0]["content"]["parts"][0]["text"].strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1]
                if raw.endswith("```"):
                    raw = raw.rsplit("\n", 1)[0]
            start = raw.find("{")
            if start >= 0:
                depth = 0
                for i, ch in enumerate(raw[start:], start):
                    if ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0:
                            raw = raw[start : i + 1]
                            break
            data = json.loads(raw)
            return {
                "page_heading": data.get("page_heading") or "",
                "rules": data.get("rules") or [],
                "examples": data.get("examples") or [],
                "letter_parts": data.get("letter_parts") or [],
                "worked_exercises": data.get("worked_exercises") or [],
            }
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                print(f"    {label} HTTP {e.code}; retry {delay}s")
                time.sleep(delay)
                delay = min(delay * 2, 90)
            else:
                time.sleep(5)
        except Exception as e:
            print(f"    {label} attempt {attempt+1}: {e}")
            time.sleep(delay)
            delay = min(delay * 2, 60)
    return {"page_heading": "", "rules": [], "examples": [], "letter_parts": [], "worked_exercises": []}


def extract_vision_page(doc, pdf_page: int, source: str, api_key: str) -> dict:
    cache = os.path.join(CACHE_DIR, f"{source}_lw_p{pdf_page:03d}.json")
    if os.path.exists(cache):
        with open(cache, "r", encoding="utf-8") as f:
            return json.load(f)
    page = doc[pdf_page - 1]
    pix = page.get_pixmap(matrix=fitz.Matrix(1.4, 1.4))
    img_b64 = base64.b64encode(pix.tobytes("jpg")).decode("utf-8")
    prompt = f"""
Extract TNPSC Unit III Letter Writing notes from {source} PDF page {pdf_page}.
Keep ONLY formal/informal letter writing: types, format, parts order, complimentary closes, sample letters.
Skip jumbled sentences, prose, unrelated topics.

Extract:
- Rules/tips about letter writing
- Letter types (enquiry, complaint, invitation, etc.) with formal/informal category
- Letter parts with order number (sender address, date, salutation, body, subscription, signature, etc.)
- MCQ/match/fill WITH answers into worked_exercises

Do NOT invent.
{SCHEMA}
Set source="{source}" and source_page={pdf_page} on every item.
"""
    data = call_gemini_json(
        [{"text": prompt}, {"inlineData": {"mimeType": "image/jpeg", "data": img_b64}}],
        api_key,
        label=f"{source} lw p{pdf_page}",
    )
    os.makedirs(CACHE_DIR, exist_ok=True)
    save_json(cache, data)
    return data


def extract_text_page(text: str, pdf_page: int, source: str, api_key: str) -> dict:
    cache = os.path.join(CACHE_DIR, f"{source}_id_p{pdf_page:03d}.json")
    if os.path.exists(cache):
        with open(cache, "r", encoding="utf-8") as f:
            return json.load(f)
    if not text.strip():
        return {"page_heading": "", "rules": [], "examples": [], "letter_parts": [], "worked_exercises": []}
    prompt = f"""
Structure TNPSC Unit III Letter Writing notes from {source} page {pdf_page}.
Keep ONLY letter writing content.
Rules → rules. Letter types → examples. Parts/order → letter_parts.
MCQs with answers → worked_exercises.
Do NOT invent.
{SCHEMA}
Set source="{source}" and source_page={pdf_page} on every item.

TEXT:
\"\"\"
{text[:14000]}
\"\"\"
"""
    data = call_gemini_json([{"text": prompt}], api_key, label=f"{source} lw p{pdf_page}")
    os.makedirs(CACHE_DIR, exist_ok=True)
    save_json(cache, data)
    return data


def normalize(item: dict, default_source: str, bucket_key: str) -> dict:
    item = dict(item)
    tag_field = "lw_tag"
    tag = (item.get(tag_field) or "other").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "def": "definition",
        "complaint": "complaint",
        "enquiry": "enquiry",
        "inquiry": "enquiry",
        "business": "business",
        "invitation": "invitation",
        "apology": "apology",
        "order": "order",
        "resignation": "resignation",
        "job": "job_application",
        "formal": "formal",
        "informal": "informal",
        "mcq": "choose_correct",
        "choose": "choose_correct",
        "fill": "fill_blank",
        "match": "match",
        "statement": "statement",
    }
    tag = aliases.get(tag, tag)
    item[tag_field] = tag
    src = (item.get("source") or default_source).strip().lower()
    if src not in ("vetrii", "asan", "grammer"):
        src = default_source
    item["source"] = src
    if bucket_key == "examples" and not item.get("category_en"):
        lt = (item.get("letter_type_en") or "").lower()
        if any(x in lt for x in ("friend", "family", "informal")):
            item["category_en"] = "informal"
        elif lt:
            item["category_en"] = "formal"
    return item


def dedupe(items, key_fn):
    seen = set()
    out = []
    for x in items:
        if not isinstance(x, dict):
            continue
        k = key_fn(x)
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(x)
    return out


def merge_chunk(bucket, chunk, source):
    for key in ("rules", "examples", "letter_parts", "worked_exercises"):
        bucket[key].extend(
            normalize(x, source, key) for x in (chunk.get(key) or []) if isinstance(x, dict)
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY not set")

    if args.fresh and os.path.isdir(CACHE_DIR):
        for name in os.listdir(CACHE_DIR):
            if name.endswith(".json"):
                os.remove(os.path.join(CACHE_DIR, name))

    bucket = {"rules": [], "examples": [], "letter_parts": [], "worked_exercises": []}

    print(f"VETRII pages {VETRII_PAGES}")
    vetrii = fitz.open(VETRII_PDF)
    for p in VETRII_PAGES:
        print(f"  vetrii p{p} (vision)...")
        chunk = extract_vision_page(vetrii, p, "vetrii", api_key)
        merge_chunk(bucket, chunk, "vetrii")
        print(
            f"    → R={len(chunk.get('rules') or [])} E={len(chunk.get('examples') or [])} "
            f"P={len(chunk.get('letter_parts') or [])} W={len(chunk.get('worked_exercises') or [])}"
        )
        time.sleep(1.0)
    vetrii.close()

    print(f"ASAN pages {ASAN_PAGES}")
    asan = fitz.open(ASAN_PDF)
    for p in ASAN_PAGES:
        print(f"  asan p{p} (vision)...")
        chunk = extract_vision_page(asan, p, "asan", api_key)
        merge_chunk(bucket, chunk, "asan")
        print(
            f"    → R={len(chunk.get('rules') or [])} E={len(chunk.get('examples') or [])} "
            f"P={len(chunk.get('letter_parts') or [])} W={len(chunk.get('worked_exercises') or [])}"
        )
        time.sleep(1.0)
    asan.close()

    print(f"GRAMMER pages {GRAMMER_PAGES}")
    grammer = fitz.open(GRAMMER_PDF)
    for p in GRAMMER_PAGES:
        text = grammer[p - 1].get_text("text")
        print(f"  grammer p{p} ({len(text)} chars)...")
        chunk = extract_text_page(text, p, "grammer", api_key)
        merge_chunk(bucket, chunk, "grammer")
        print(
            f"    → R={len(chunk.get('rules') or [])} E={len(chunk.get('examples') or [])} "
            f"P={len(chunk.get('letter_parts') or [])} W={len(chunk.get('worked_exercises') or [])}"
        )
        time.sleep(0.7)
    grammer.close()

    bucket["rules"] = dedupe(
        bucket["rules"], lambda r: re.sub(r"\s+", " ", (r.get("rule_en") or "").lower())
    )
    bucket["examples"] = dedupe(
        bucket["examples"],
        lambda e: re.sub(r"\s+", " ", (e.get("letter_type_en") or "").lower()),
    )
    bucket["letter_parts"] = dedupe(
        bucket["letter_parts"],
        lambda p: re.sub(
            r"\s+",
            " ",
            f"{p.get('part_en') or ''}|{p.get('applies_to') or ''}|{p.get('order_num') or ''}".lower(),
        ),
    )
    bucket["worked_exercises"] = dedupe(
        bucket["worked_exercises"],
        lambda w: re.sub(r"\s+", " ", f"{w.get('prompt_en')}|{w.get('answer_en')}".lower()),
    )

    by_tag = defaultdict(lambda: {"rules": 0, "examples": 0, "letter_parts": 0, "worked": 0})
    for r in bucket["rules"]:
        by_tag[r.get("lw_tag") or "other"]["rules"] += 1
    for e in bucket["examples"]:
        by_tag[e.get("lw_tag") or "other"]["examples"] += 1
    for p in bucket["letter_parts"]:
        by_tag[p.get("lw_tag") or "other"]["letter_parts"] += 1
    for w in bucket["worked_exercises"]:
        by_tag[w.get("lw_tag") or "other"]["worked"] += 1

    out = {
        "subject_id": "English",
        "unit": "Writing Skills",
        "menu": "letter_writing_types",
        "topic": "Types of Letters (Formal & Informal)",
        "sources": [
            f"Vetrii Unit3,4 pp.{VETRII_PAGES} (primary, vision)",
            f"Asan Unit3 pp.{ASAN_PAGES} (secondary, vision)",
            f"Grammer.pdf pp.{GRAMMER_PAGES} (secondary, text)",
        ],
        **bucket,
        "stats": {
            "totals": {
                "rules": len(bucket["rules"]),
                "examples": len(bucket["examples"]),
                "letter_parts": len(bucket["letter_parts"]),
                "worked_exercises": len(bucket["worked_exercises"]),
            },
            "by_lw_tag": dict(by_tag),
        },
    }
    save_json(NOTES_PATH, out)
    print(f"\nSaved {NOTES_PATH}")
    print(
        f"  rules={len(out['rules'])} examples={len(out['examples'])} "
        f"parts={len(out['letter_parts'])} worked={len(out['worked_exercises'])}"
    )
    print("  by lw_tag:", dict(by_tag))


if __name__ == "__main__":
    main()
