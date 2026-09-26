#!/usr/bin/env python3
"""
Extract Jumbled Sentences notes for Unit III Writing Skills.

Primary:   Unit3,4/asan-unit3-eng.pdf pp.12–16 (vision)
           — word order, jumbled sentences, process/paragraph sequencing
Secondary: Grammer.pdf rearrange pages (text)

Output: English/WritingSkills/jumbled_sentences_notes.json
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
ASAN_PDF = os.path.join(BASE_DIR, "Data", "General-English", "Unit3,4", "asan-unit3-eng.pdf")
GRAMMER_PDF = os.path.join(BASE_DIR, "Data", "General-English", "Grammer.pdf")
NOTES_PATH = os.path.join(BASE_DIR, "English", "WritingSkills", "jumbled_sentences_notes.json")
CACHE_DIR = os.path.join(BASE_DIR, "English", "WritingSkills", "_tmp_jumbled_extract_cache")

MODEL = "gemini-3.1-flash-lite"
ASAN_PAGES = [12, 13, 14, 15, 16]
GRAMMER_PAGES = [299, 302, 303, 304, 305, 307, 308]

SCHEMA = """
Return ONLY JSON:
{
  "page_heading": "short heading if visible",
  "rules": [{"rule_en": "...", "js_tag": "word_order|sentence_order|process|coherence|tip|other", "source": "asan|grammer", "source_page": N}],
  "examples": [{"kind_en": "word_jumble|sentence_jumble|process_sequence", "prompt_en": "jumbled items as shown", "answer_en": "correct order / sentence", "note_en": "...", "js_tag": "word_order|sentence_order|process|other", "source": "...", "source_page": N}],
  "worked_exercises": [{"prompt_en": "...", "answer_en": "...", "options_en": ["A","B","C","D"], "js_tag": "choose_correct|rearrange|match|other", "source": "...", "source_page": N}]
}
Extract ONLY jumbled / rearrange / sentence-order / process-sequence content.
MCQ WITH answers → worked_exercises (full options when visible).
Word/sentence sets WITH correct order → examples.
Tips/rules for ordering → rules.
Skip letter writing, queries, inferences, blanks, substitutions, unrelated grammar.
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


def extract_vision_page(doc, pdf_page: int, source: str, api_key: str) -> dict:
    cache = os.path.join(CACHE_DIR, f"{source}_js_p{pdf_page:03d}.json")
    if os.path.exists(cache):
        with open(cache, "r", encoding="utf-8") as f:
            return json.load(f)
    page = doc[pdf_page - 1]
    pix = page.get_pixmap(matrix=fitz.Matrix(1.4, 1.4))
    img_b64 = base64.b64encode(pix.tobytes("jpg")).decode("utf-8")
    prompt = f"""
Extract TNPSC Unit III Jumbled Sentences / sentence-order notes from {source} PDF page {pdf_page}.
Keep ONLY: jumbled words → sentence, rearrange jumbled sentences, process/paragraph sequencing, coherence tips.
Skip letter writing, making queries, inferences, blanks, substitutions.

Extract:
- Rules/tips for word order and sentence order
- Worked jumbles with correct answers → examples
- MCQs with answers → worked_exercises

Do NOT invent.
{SCHEMA}
Set source="{source}" and source_page={pdf_page} on every item.
"""
    data = call_gemini_json(
        [{"text": prompt}, {"inlineData": {"mimeType": "image/jpeg", "data": img_b64}}],
        api_key,
        label=f"{source} js p{pdf_page}",
    )
    os.makedirs(CACHE_DIR, exist_ok=True)
    save_json(cache, data)
    return data


def extract_text_page(text: str, pdf_page: int, source: str, api_key: str) -> dict:
    cache = os.path.join(CACHE_DIR, f"{source}_js_p{pdf_page:03d}.json")
    if os.path.exists(cache):
        with open(cache, "r", encoding="utf-8") as f:
            return json.load(f)
    if not text.strip():
        return {"page_heading": "", "rules": [], "examples": [], "worked_exercises": []}
    prompt = f"""
Structure TNPSC Unit III Jumbled Sentences notes from {source} page {pdf_page}.
Keep ONLY rearrange / jumbled words / jumbled sentences / process sequence content.
Rules → rules. Solved jumbles → examples. MCQs with answers → worked_exercises.
Do NOT invent.
{SCHEMA}
Set source="{source}" and source_page={pdf_page} on every item.

TEXT:
\"\"\"
{text[:14000]}
\"\"\"
"""
    data = call_gemini_json([{"text": prompt}], api_key, label=f"{source} js p{pdf_page}")
    os.makedirs(CACHE_DIR, exist_ok=True)
    save_json(cache, data)
    return data


def normalize(item: dict, default_source: str) -> dict:
    item = dict(item)
    tag = (item.get("js_tag") or "other").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "word": "word_order",
        "words": "word_order",
        "sentence": "sentence_order",
        "sentences": "sentence_order",
        "order": "sentence_order",
        "process": "process",
        "sequence": "process",
        "mcq": "choose_correct",
        "choose": "choose_correct",
        "rearrange": "rearrange",
    }
    tag = aliases.get(tag, tag)
    item["js_tag"] = tag
    src = (item.get("source") or default_source).strip().lower()
    if src not in ("asan", "grammer"):
        src = default_source
    item["source"] = src
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
    for key in ("rules", "examples", "worked_exercises"):
        bucket[key].extend(
            normalize(x, source) for x in (chunk.get(key) or []) if isinstance(x, dict)
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

    bucket = {"rules": [], "examples": [], "worked_exercises": []}

    print(f"ASAN pages {ASAN_PAGES}")
    asan = fitz.open(ASAN_PDF)
    for p in ASAN_PAGES:
        print(f"  asan p{p} (vision)...")
        chunk = extract_vision_page(asan, p, "asan", api_key)
        merge_chunk(bucket, chunk, "asan")
        print(
            f"    → R={len(chunk.get('rules') or [])} E={len(chunk.get('examples') or [])} "
            f"W={len(chunk.get('worked_exercises') or [])}"
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
            f"W={len(chunk.get('worked_exercises') or [])}"
        )
        time.sleep(0.7)
    grammer.close()

    bucket["rules"] = dedupe(
        bucket["rules"], lambda r: re.sub(r"\s+", " ", (r.get("rule_en") or "").lower())
    )
    bucket["examples"] = dedupe(
        bucket["examples"],
        lambda e: re.sub(
            r"\s+",
            " ",
            f"{e.get('prompt_en') or ''}|{e.get('answer_en') or ''}".lower(),
        ),
    )
    bucket["worked_exercises"] = dedupe(
        bucket["worked_exercises"],
        lambda w: re.sub(r"\s+", " ", f"{w.get('prompt_en')}|{w.get('answer_en')}".lower()),
    )

    by_tag = defaultdict(lambda: {"rules": 0, "examples": 0, "worked": 0})
    for r in bucket["rules"]:
        by_tag[r.get("js_tag") or "other"]["rules"] += 1
    for e in bucket["examples"]:
        by_tag[e.get("js_tag") or "other"]["examples"] += 1
    for w in bucket["worked_exercises"]:
        by_tag[w.get("js_tag") or "other"]["worked"] += 1

    out = {
        "subject_id": "English",
        "unit": "Writing Skills",
        "menu": "jumbled_sentences",
        "topic": "Jumbled Sentences",
        "sources": [
            f"Asan Unit3 pp.{ASAN_PAGES} (primary, vision)",
            f"Grammer.pdf pp.{GRAMMER_PAGES} (secondary, text)",
        ],
        **bucket,
        "stats": {
            "totals": {
                "rules": len(bucket["rules"]),
                "examples": len(bucket["examples"]),
                "worked_exercises": len(bucket["worked_exercises"]),
            },
            "by_js_tag": dict(by_tag),
        },
    }
    save_json(NOTES_PATH, out)
    print(f"\nSaved {NOTES_PATH}")
    print(
        f"  rules={len(out['rules'])} examples={len(out['examples'])} "
        f"worked={len(out['worked_exercises'])}"
    )
    print("  by js_tag:", dict(by_tag))


if __name__ == "__main__":
    main()
