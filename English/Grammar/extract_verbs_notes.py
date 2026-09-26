#!/usr/bin/env python3
"""
Extract Verbs notes (Main / Auxiliary / Regular / Irregular).

Primary:   verb-fully.pdf pp.1–14 (scanned, vision)
Primary:   race academy general english part A (1).pdf pp.51–52
Secondary: Grammer.pdf pp.52, 54, 223, 370, 374–376
Secondary: Govt pp.91 (transitive/intransitive)

Output: English/Grammar/verbs_notes.json
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
VERB_FULLY_PDF = os.path.join(BASE_DIR, "Data", "General-English", "verb-fully.pdf")
RACE_PDF = os.path.join(
    BASE_DIR, "Data", "General-English", "race academy general english part A  (1).pdf"
)
GRAMMER_PDF = os.path.join(BASE_DIR, "Data", "General-English", "Grammer.pdf")
GOVT_PDF = os.path.join(
    BASE_DIR,
    "Data",
    "General-English",
    "General_English_Part_A_Grammar_Group_2_Govt_Notes_for_TNPSC_Group.pdf",
)
NOTES_PATH = os.path.join(BASE_DIR, "English", "Grammar", "verbs_notes.json")
CACHE_DIR = os.path.join(BASE_DIR, "English", "Grammar", "_tmp_verbs_extract_cache")

MODEL = "gemini-3.1-flash-lite"
VERB_FULLY_PAGES = list(range(1, 15))
RACE_PAGES = [51, 52]
GRAMMER_PAGES = [52, 54, 223, 370, 374, 375, 376]
GOVT_PAGES = [91]

VERB_TOPICS = [
    "main_verbs",
    "auxiliary_verbs",
    "regular_verbs",
    "irregular_verbs",
    "overview",
    "other",
]

SCHEMA = """
Return ONLY JSON:
{
  "page_heading": "short heading if visible",
  "rules": [{"rule_en": "...", "verb_topic": "main_verbs|auxiliary_verbs|regular_verbs|irregular_verbs|overview|other", "source": "race|grammer|govt", "source_page": N}],
  "examples": [{"input_en": "...", "output_en": "...", "verb_topic": "...", "note_en": "...", "source": "...", "source_page": N}],
  "worked_exercises": [{"prompt_en": "...", "answer_en": "...", "verb_topic": "...", "source": "...", "source_page": N}]
}
Tag verb_topic precisely. MCQ/fill-in exercises WITH answers → worked_exercises.
Skip non-finite verbs (gerund/infinitive/participle), tense usage drills, question tags, voice, reported speech.
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


def extract_verb_fully_page(doc, pdf_page: int, api_key: str) -> dict:
    cache = os.path.join(CACHE_DIR, f"verb_fully_p{pdf_page:03d}.json")
    if os.path.exists(cache):
        with open(cache, "r", encoding="utf-8") as f:
            return json.load(f)
    page = doc[pdf_page - 1]
    pix = page.get_pixmap(matrix=fitz.Matrix(1.45, 1.45))
    img_b64 = base64.b64encode(pix.tobytes("jpg")).decode("utf-8")
    prompt = f"""
Extract TNPSC General English VERBS notes from this scanned verb-fully.pdf page.
PDF page: {pdf_page}/14.

Extract rules, examples, and worked exercises WITH answers for:
- Main verbs (action/state; transitive/intransitive)
- Auxiliary/helping verbs (be, do, have; primary auxiliaries)
- Modals and semi-modals (can, may, must, shall, should, will, would, need, dare, used to, ought to)
- Regular verbs (V1→V2/V3 with -ed)
- Irregular verbs (V1/V2/V3 tables and types)

SKIP non-finite verbs (gerunds, infinitives, participles) — those belong to a separate menu.
SKIP tense usage drills and question tags.

Tag verb_topic: main_verbs | auxiliary_verbs | regular_verbs | irregular_verbs | overview | other
Do NOT invent content.
{SCHEMA}
Set source="verb_fully" and source_page={pdf_page} on every item.
"""
    data = call_gemini_json(
        [
            {"text": prompt},
            {"inlineData": {"mimeType": "image/jpeg", "data": img_b64}},
        ],
        api_key,
        label=f"verb_fully p{pdf_page}",
    )
    os.makedirs(CACHE_DIR, exist_ok=True)
    save_json(cache, data)
    return data


def extract_text_page(text: str, pdf_page: int, source: str, api_key: str) -> dict:
    cache = os.path.join(CACHE_DIR, f"{source}_v_p{pdf_page:03d}.json")
    if os.path.exists(cache):
        with open(cache, "r", encoding="utf-8") as f:
            return json.load(f)
    if not text.strip():
        return {"page_heading": "", "rules": [], "examples": [], "worked_exercises": []}
    prompt = f"""
Structure TNPSC General English VERBS notes from {source} page {pdf_page}.

Keep ONLY:
- Main verbs (action/state; transitive/intransitive)
- Auxiliary/helping verbs (be, do, have; modals)
- Regular verbs (V1→V2/V3 with -ed)
- Irregular verbs (V1/V2/V3 table)
- V1/V2/V3 definitions

Do NOT include tense exercises, question tags, voice, direct speech, non-finite verbs.
Do NOT invent.
{SCHEMA}

TEXT:
\"\"\"
{text[:14000]}
\"\"\"
"""
    data = call_gemini_json([{"text": prompt}], api_key, label=f"{source} p{pdf_page}")
    os.makedirs(CACHE_DIR, exist_ok=True)
    save_json(cache, data)
    return data


def normalize_tag(item: dict, default_source: str) -> dict:
    item = dict(item)
    tag = (item.get("verb_topic") or "other").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "main_verb": "main_verbs",
        "principal_verb": "main_verbs",
        "helping_verb": "auxiliary_verbs",
        "modal_verb": "auxiliary_verbs",
        "modal_auxiliary": "auxiliary_verbs",
        "primary_auxiliary": "auxiliary_verbs",
        "regular_verb": "regular_verbs",
        "irregular_verb": "irregular_verbs",
        "transitive": "main_verbs",
        "intransitive": "main_verbs",
        "v1_v2_v3": "irregular_verbs",
    }
    tag = aliases.get(tag, tag)
    if tag not in VERB_TOPICS:
        tag = "other"
    item["verb_topic"] = tag
    src = (item.get("source") or default_source).strip().lower()
    if src not in ("verb_fully", "race", "grammer", "govt"):
        src = default_source
    item["source"] = src
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

    print(f"VERB-FULLY pages {VERB_FULLY_PAGES}")
    verb_fully = fitz.open(VERB_FULLY_PDF)
    for p in VERB_FULLY_PAGES:
        print(f"  verb_fully p{p} (vision)...")
        chunk = extract_verb_fully_page(verb_fully, p, api_key)
        for key in bucket:
            bucket[key].extend(
                normalize_tag(x, "verb_fully") for x in (chunk.get(key) or []) if isinstance(x, dict)
            )
        print(
            f"    → R={len(chunk.get('rules') or [])} "
            f"E={len(chunk.get('examples') or [])} "
            f"W={len(chunk.get('worked_exercises') or [])}"
        )
        time.sleep(1.0)
    verb_fully.close()

    print(f"RACE pages {RACE_PAGES}")
    race = fitz.open(RACE_PDF)
    for p in RACE_PAGES:
        text = race[p - 1].get_text("text")
        print(f"  race p{p} ({len(text)} chars)...")
        chunk = extract_text_page(text, p, "race", api_key)
        for key in bucket:
            bucket[key].extend(
                normalize_tag(x, "race") for x in (chunk.get(key) or []) if isinstance(x, dict)
            )
        print(
            f"    → R={len(chunk.get('rules') or [])} "
            f"E={len(chunk.get('examples') or [])} "
            f"W={len(chunk.get('worked_exercises') or [])}"
        )
        time.sleep(0.8)
    race.close()

    print(f"GRAMMER pages {GRAMMER_PAGES}")
    grammer = fitz.open(GRAMMER_PDF)
    for p in GRAMMER_PAGES:
        text = grammer[p - 1].get_text("text")
        print(f"  grammer p{p} ({len(text)} chars)...")
        chunk = extract_text_page(text, p, "grammer", api_key)
        for key in bucket:
            bucket[key].extend(
                normalize_tag(x, "grammer") for x in (chunk.get(key) or []) if isinstance(x, dict)
            )
        print(
            f"    → R={len(chunk.get('rules') or [])} "
            f"E={len(chunk.get('examples') or [])} "
            f"W={len(chunk.get('worked_exercises') or [])}"
        )
        time.sleep(0.8)
    grammer.close()

    print(f"GOVT pages {GOVT_PAGES}")
    govt = fitz.open(GOVT_PDF)
    for p in GOVT_PAGES:
        text = govt[p - 1].get_text("text")
        print(f"  govt p{p} ({len(text)} chars)...")
        chunk = extract_text_page(text, p, "govt", api_key)
        for key in bucket:
            bucket[key].extend(
                normalize_tag(x, "govt") for x in (chunk.get(key) or []) if isinstance(x, dict)
            )
        print(
            f"    → R={len(chunk.get('rules') or [])} "
            f"E={len(chunk.get('examples') or [])} "
            f"W={len(chunk.get('worked_exercises') or [])}"
        )
        time.sleep(0.8)
    govt.close()

    bucket["rules"] = dedupe_items(
        bucket["rules"], lambda r: re.sub(r"\s+", " ", (r.get("rule_en") or "").lower())
    )
    bucket["examples"] = dedupe_items(
        bucket["examples"],
        lambda e: re.sub(r"\s+", " ", f"{e.get('input_en')}|{e.get('output_en')}".lower()),
    )
    bucket["worked_exercises"] = dedupe_items(
        bucket["worked_exercises"],
        lambda w: re.sub(r"\s+", " ", f"{w.get('prompt_en')}|{w.get('answer_en')}".lower()),
    )

    by_tag = defaultdict(lambda: {"rules": 0, "examples": 0, "worked": 0})
    for r in bucket["rules"]:
        by_tag[r.get("verb_topic") or "other"]["rules"] += 1
    for e in bucket["examples"]:
        by_tag[e.get("verb_topic") or "other"]["examples"] += 1
    for w in bucket["worked_exercises"]:
        by_tag[w.get("verb_topic") or "other"]["worked"] += 1

    out = {
        "subject_id": "English",
        "menu": "verbs",
        "sources": [
            f"verb-fully.pdf pp.{VERB_FULLY_PAGES} (primary, vision)",
            f"Race Part A pp.{RACE_PAGES} (secondary)",
            f"Grammer.pdf pp.{GRAMMER_PAGES} (secondary)",
            f"Govt pp.{GOVT_PAGES} (secondary)",
        ],
        **bucket,
        "stats": {
            "totals": {
                "rules": len(bucket["rules"]),
                "examples": len(bucket["examples"]),
                "worked_exercises": len(bucket["worked_exercises"]),
            },
            "by_verb_topic": dict(by_tag),
        },
    }
    save_json(NOTES_PATH, out)
    print(f"\nSaved {NOTES_PATH}")
    print(
        f"  rules={len(out['rules'])} examples={len(out['examples'])} "
        f"worked={len(out['worked_exercises'])}"
    )
    print("  by verb_topic:", dict(by_tag))


if __name__ == "__main__":
    main()
