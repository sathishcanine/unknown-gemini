#!/usr/bin/env python3
"""
Extract Synonyms notes for Unit II Vocabulary.

Primary:   Vocab/vetrii-english-vocabulary.pdf pp.1–12, 35–43 (scanned, vision)
Primary:   race academy Part A pp.7–20 (text word lists)
Secondary: Grammer.pdf synonym MCQ pages 159, 162, 164, 169, 171

Output: English/Vocabulary/synonyms_notes.json
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
VETRII_PDF = os.path.join(BASE_DIR, "Data", "General-English", "Vocab", "vetrii-english-vocabulary.pdf")
RACE_PDF = os.path.join(
    BASE_DIR, "Data", "General-English", "race academy general english part A  (1).pdf"
)
GRAMMER_PDF = os.path.join(BASE_DIR, "Data", "General-English", "Grammer.pdf")
NOTES_PATH = os.path.join(BASE_DIR, "English", "Vocabulary", "synonyms_notes.json")
CACHE_DIR = os.path.join(BASE_DIR, "English", "Vocabulary", "_tmp_synonyms_extract_cache")

MODEL = "gemini-3.1-flash-lite"
VETRII_PAGES = list(range(1, 13)) + list(range(35, 44))  # lists + exercises
RACE_PAGES = list(range(7, 21))
GRAMMER_PAGES = [159, 162, 164, 169, 171]

SCHEMA = """
Return ONLY JSON:
{
  "page_heading": "short heading if visible",
  "rules": [{"rule_en": "...", "syn_tag": "definition|choose_synonym|match_pair|context_sentence|overview|other", "source": "vetrii|race|grammer", "source_page": N}],
  "examples": [{"word_en": "...", "synonym_en": "...", "note_en": "...", "syn_tag": "...", "source": "...", "source_page": N}],
  "worked_exercises": [{"prompt_en": "...", "answer_en": "...", "options_en": ["..."], "syn_tag": "...", "source": "...", "source_page": N}]
}
Extract synonym word↔synonym pairs as examples.
MCQ / fill-in WITH answers → worked_exercises.
Skip antonyms, homophones, idioms unless they are synonym items.
Do NOT invent pairs.
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


def extract_vetrii_page(doc, pdf_page: int, api_key: str) -> dict:
    cache = os.path.join(CACHE_DIR, f"vetrii_syn_p{pdf_page:03d}.json")
    if os.path.exists(cache):
        with open(cache, "r", encoding="utf-8") as f:
            return json.load(f)
    page = doc[pdf_page - 1]
    pix = page.get_pixmap(matrix=fitz.Matrix(1.4, 1.4))
    img_b64 = base64.b64encode(pix.tobytes("jpg")).decode("utf-8")
    prompt = f"""
Extract TNPSC General English SYNONYMS notes from Vetrii Vocabulary PDF page {pdf_page}.
Keep ONLY synonyms (same-meaning words). Skip antonyms/homophones/idioms.

Extract:
- Definition/rules about synonyms
- Word → synonym pairs (as many as visible) into examples
- MCQ/exercises WITH answers into worked_exercises

Do NOT invent.
{SCHEMA}
Set source="vetrii" and source_page={pdf_page} on every item.
"""
    data = call_gemini_json(
        [{"text": prompt}, {"inlineData": {"mimeType": "image/jpeg", "data": img_b64}}],
        api_key,
        label=f"vetrii syn p{pdf_page}",
    )
    os.makedirs(CACHE_DIR, exist_ok=True)
    save_json(cache, data)
    return data


def extract_text_page(text: str, pdf_page: int, source: str, api_key: str) -> dict:
    cache = os.path.join(CACHE_DIR, f"{source}_syn_p{pdf_page:03d}.json")
    if os.path.exists(cache):
        with open(cache, "r", encoding="utf-8") as f:
            return json.load(f)
    if not text.strip():
        return {"page_heading": "", "rules": [], "examples": [], "worked_exercises": []}
    prompt = f"""
Structure TNPSC General English SYNONYMS notes from {source} page {pdf_page}.
Keep ONLY synonyms. Skip antonyms unless the item is clearly a synonym MCQ.
Word lists → examples (word_en + synonym_en).
MCQs with answers → worked_exercises.
Do NOT invent.
{SCHEMA}
Set source="{source}" and source_page={pdf_page} on every item.

TEXT:
\"\"\"
{text[:14000]}
\"\"\"
"""
    data = call_gemini_json([{"text": prompt}], api_key, label=f"{source} syn p{pdf_page}")
    os.makedirs(CACHE_DIR, exist_ok=True)
    save_json(cache, data)
    return data


def normalize(item: dict, default_source: str) -> dict:
    item = dict(item)
    tag = (item.get("syn_tag") or "other").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "pair": "match_pair",
        "word_pair": "match_pair",
        "mcq": "choose_synonym",
        "choose": "choose_synonym",
        "context": "context_sentence",
        "sentence": "context_sentence",
        "def": "definition",
    }
    tag = aliases.get(tag, tag)
    if tag not in ("definition", "choose_synonym", "match_pair", "context_sentence", "overview", "other"):
        tag = "other"
    item["syn_tag"] = tag
    src = (item.get("source") or default_source).strip().lower()
    if src not in ("vetrii", "race", "grammer"):
        src = default_source
    item["source"] = src
    # unify example fields
    if "word_en" not in item and item.get("input"):
        item["word_en"] = item.get("input")
    if "synonym_en" not in item and item.get("output"):
        item["synonym_en"] = item.get("output")
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

    print(f"VETRII pages {VETRII_PAGES}")
    vetrii = fitz.open(VETRII_PDF)
    for p in VETRII_PAGES:
        print(f"  vetrii p{p} (vision)...")
        chunk = extract_vetrii_page(vetrii, p, api_key)
        for key in bucket:
            bucket[key].extend(
                normalize(x, "vetrii") for x in (chunk.get(key) or []) if isinstance(x, dict)
            )
        print(
            f"    → R={len(chunk.get('rules') or [])} "
            f"E={len(chunk.get('examples') or [])} "
            f"W={len(chunk.get('worked_exercises') or [])}"
        )
        time.sleep(0.9)
    vetrii.close()

    print(f"RACE pages {RACE_PAGES}")
    race = fitz.open(RACE_PDF)
    for p in RACE_PAGES:
        text = race[p - 1].get_text("text")
        print(f"  race p{p} ({len(text)} chars)...")
        chunk = extract_text_page(text, p, "race", api_key)
        for key in bucket:
            bucket[key].extend(
                normalize(x, "race") for x in (chunk.get(key) or []) if isinstance(x, dict)
            )
        print(
            f"    → R={len(chunk.get('rules') or [])} "
            f"E={len(chunk.get('examples') or [])} "
            f"W={len(chunk.get('worked_exercises') or [])}"
        )
        time.sleep(0.7)
    race.close()

    print(f"GRAMMER pages {GRAMMER_PAGES}")
    grammer = fitz.open(GRAMMER_PDF)
    for p in GRAMMER_PAGES:
        text = grammer[p - 1].get_text("text")
        print(f"  grammer p{p} ({len(text)} chars)...")
        chunk = extract_text_page(text, p, "grammer", api_key)
        for key in bucket:
            bucket[key].extend(
                normalize(x, "grammer") for x in (chunk.get(key) or []) if isinstance(x, dict)
            )
        print(
            f"    → R={len(chunk.get('rules') or [])} "
            f"E={len(chunk.get('examples') or [])} "
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
            f"{e.get('word_en') or e.get('input')}|{e.get('synonym_en') or e.get('output')}".lower(),
        ),
    )
    bucket["worked_exercises"] = dedupe(
        bucket["worked_exercises"],
        lambda w: re.sub(r"\s+", " ", f"{w.get('prompt_en')}|{w.get('answer_en')}".lower()),
    )

    by_tag = defaultdict(lambda: {"rules": 0, "examples": 0, "worked": 0})
    for r in bucket["rules"]:
        by_tag[r.get("syn_tag") or "other"]["rules"] += 1
    for e in bucket["examples"]:
        by_tag[e.get("syn_tag") or "other"]["examples"] += 1
    for w in bucket["worked_exercises"]:
        by_tag[w.get("syn_tag") or "other"]["worked"] += 1

    out = {
        "subject_id": "English",
        "unit": "Vocabulary",
        "menu": "synonyms",
        "sources": [
            f"Vetrii Vocabulary pp.{VETRII_PAGES} (primary, vision)",
            f"Race Part A pp.{RACE_PAGES} (primary)",
            f"Grammer.pdf pp.{GRAMMER_PAGES} (secondary)",
        ],
        **bucket,
        "stats": {
            "totals": {
                "rules": len(bucket["rules"]),
                "examples": len(bucket["examples"]),
                "worked_exercises": len(bucket["worked_exercises"]),
            },
            "by_syn_tag": dict(by_tag),
        },
    }
    save_json(NOTES_PATH, out)
    print(f"\nSaved {NOTES_PATH}")
    print(
        f"  rules={len(out['rules'])} examples={len(out['examples'])} "
        f"worked={len(out['worked_exercises'])}"
    )
    print("  by syn_tag:", dict(by_tag))


if __name__ == "__main__":
    main()
