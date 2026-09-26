#!/usr/bin/env python3
"""
Extract Punctuation notes from Grammer.pdf.

Primary: Grammer.pdf pp.130–134, 136–139 (book Punctuation ch. + appendix)

Output: English/Grammar/punctuation_notes.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from collections import defaultdict

import fitz

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GRAMMER_PDF = os.path.join(BASE_DIR, "Data", "General-English", "Grammer.pdf")
NOTES_PATH = os.path.join(BASE_DIR, "English", "Grammar", "punctuation_notes.json")
CACHE_DIR = os.path.join(BASE_DIR, "English", "Grammar", "_tmp_punctuation_extract_cache")

MODEL = "gemini-3.1-flash-lite"
GRAMMER_PAGES = [130, 131, 132, 133, 134, 136, 137, 138, 139]

MARK_TAGS = [
    "full_stop",
    "question_mark",
    "exclamation",
    "comma",
    "semicolon",
    "colon",
    "apostrophe",
    "quotation",
    "brackets",
    "dash",
    "hyphen",
    "capitalization",
    "spot_error",
    "overview",
    "other",
]

SCHEMA = """
Return ONLY JSON:
{
  "page_heading": "short heading if visible",
  "rules": [{"rule_en": "...", "mark_tag": "full_stop|question_mark|exclamation|comma|semicolon|colon|apostrophe|quotation|brackets|dash|hyphen|capitalization|spot_error|overview|other", "source": "grammer", "source_page": N}],
  "examples": [{"input": "...", "output": "...", "mark_tag": "...", "note_en": "...", "source": "grammer", "source_page": N}],
  "worked_exercises": [{"prompt_en": "...", "answer_en": "...", "mark_tag": "...", "source": "grammer", "source_page": N}]
}
Punctuate / choose-mark / spot-error exercises WITH answers → worked_exercises.
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
            with urllib.request.urlopen(req, timeout=150) as response:
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
    return {"page_heading": "", "rules": [], "examples": [], "worked_exercises": []}


def extract_text_page(text: str, pdf_page: int, api_key: str) -> dict:
    cache = os.path.join(CACHE_DIR, f"grammer_punct_p{pdf_page:03d}.json")
    if os.path.exists(cache):
        with open(cache, "r", encoding="utf-8") as f:
            return json.load(f)
    if not text.strip():
        return {"page_heading": "", "rules": [], "examples": [], "worked_exercises": []}
    prompt = f"""
Structure TNPSC General English PUNCTUATION notes from Grammer.pdf page {pdf_page}.

Keep ONLY punctuation marks, capitalization, and punctuate/spot-error exercises.
Skip spelling, homophones, letter writing unless punctuation examples.
Do NOT invent.
{SCHEMA}

TEXT:
\"\"\"
{text[:14000]}
\"\"\"
"""
    data = call_gemini_json([{"text": prompt}], api_key, label=f"grammer punct p{pdf_page}")
    os.makedirs(CACHE_DIR, exist_ok=True)
    save_json(cache, data)
    return data


def normalize_tag(item: dict) -> dict:
    item = dict(item)
    mt = (item.get("mark_tag") or "other").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "fullstop": "full_stop",
        "period": "full_stop",
        "question": "question_mark",
        "exclamation_mark": "exclamation",
        "inverted_commas": "quotation",
        "quotes": "quotation",
        "capitalisation": "capitalization",
        "capital_letter": "capitalization",
        "spot_punctuation": "spot_error",
        "error_spotting": "spot_error",
    }
    mt = aliases.get(mt, mt)
    if mt not in MARK_TAGS:
        mt = "other"
    item["mark_tag"] = mt
    item.setdefault("source", "grammer")
    return item


def dedupe_items(items, key_fn):
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

    bucket = {"rules": [], "examples": [], "worked_exercises": []}
    print(f"GRAMMER pages {GRAMMER_PAGES}")
    doc = fitz.open(GRAMMER_PDF)
    for p in GRAMMER_PAGES:
        text = doc[p - 1].get_text("text")
        print(f"  grammer p{p} ({len(text)} chars)...")
        chunk = extract_text_page(text, p, api_key)
        for key in bucket:
            bucket[key].extend(
                normalize_tag(x) for x in (chunk.get(key) or []) if isinstance(x, dict)
            )
        print(
            f"    → R={len(chunk.get('rules') or [])} "
            f"E={len(chunk.get('examples') or [])} "
            f"W={len(chunk.get('worked_exercises') or [])}"
        )
        time.sleep(0.8)
    doc.close()

    bucket["rules"] = dedupe_items(
        bucket["rules"], lambda r: re.sub(r"\s+", " ", (r.get("rule_en") or "").lower())
    )
    bucket["examples"] = dedupe_items(
        bucket["examples"],
        lambda e: re.sub(r"\s+", " ", f"{e.get('input')}|{e.get('output')}".lower()),
    )
    bucket["worked_exercises"] = dedupe_items(
        bucket["worked_exercises"],
        lambda w: re.sub(r"\s+", " ", f"{w.get('prompt_en')}|{w.get('answer_en')}".lower()),
    )

    by_mark = defaultdict(lambda: {"rules": 0, "examples": 0, "worked": 0})
    for r in bucket["rules"]:
        by_mark[r.get("mark_tag") or "other"]["rules"] += 1
    for e in bucket["examples"]:
        by_mark[e.get("mark_tag") or "other"]["examples"] += 1
    for w in bucket["worked_exercises"]:
        by_mark[w.get("mark_tag") or "other"]["worked"] += 1

    out = {
        "subject_id": "English",
        "menu": "punctuation",
        "sources": [f"Grammer.pdf pp.{GRAMMER_PAGES} (primary)"],
        **bucket,
        "stats": {
            "totals": {
                "rules": len(bucket["rules"]),
                "examples": len(bucket["examples"]),
                "worked_exercises": len(bucket["worked_exercises"]),
            },
            "by_mark_tag": dict(by_mark),
        },
    }
    save_json(NOTES_PATH, out)
    print(f"\nSaved {NOTES_PATH}")
    print(
        f"  rules={len(out['rules'])} examples={len(out['examples'])} "
        f"worked={len(out['worked_exercises'])}"
    )
    print("  by mark_tag:", dict(by_mark))


if __name__ == "__main__":
    main()
