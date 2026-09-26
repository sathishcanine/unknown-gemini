#!/usr/bin/env python3
"""
Extract Synthesis of Sentences notes.

Primary:   asan-remaining-grammar.pdf pp.21–26 (scanned, vision)
Primary:   Grammer.pdf pp.357–363, 360, 365
Secondary: Govt pp.112–115

Output: English/Grammar/synthesis_notes.json
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
ASAN_PDF = os.path.join(BASE_DIR, "Data", "General-English", "asan-remaining-grammar.pdf")
GRAMMER_PDF = os.path.join(BASE_DIR, "Data", "General-English", "Grammer.pdf")
GOVT_PDF = os.path.join(
    BASE_DIR,
    "Data",
    "General-English",
    "General_English_Part_A_Grammar_Group_2_Govt_Notes_for_TNPSC_Group.pdf",
)
NOTES_PATH = os.path.join(BASE_DIR, "English", "Grammar", "synthesis_notes.json")
CACHE_DIR = os.path.join(BASE_DIR, "English", "Grammar", "_tmp_synthesis_extract_cache")

MODEL = "gemini-3.1-flash-lite"
ASAN_PAGES = list(range(21, 27))
GRAMMER_PAGES = [357, 358, 359, 360, 361, 362, 363, 365]
GOVT_PAGES = [112, 113, 114, 115]

SYNTHESIS_TOPICS = [
    "combining_two_sentences",
    "using_conjunctions",
    "using_participles",
    "using_infinitives",
    "using_phrases",
    "using_clauses",
    "overview",
    "other",
]

SCHEMA = """
Return ONLY JSON:
{
  "page_heading": "short heading if visible",
  "rules": [{"rule_en": "...", "synthesis_topic": "combining_two_sentences|using_conjunctions|using_participles|using_infinitives|using_phrases|using_clauses|overview|other", "source": "...", "source_page": N}],
  "examples": [{"input_en": "...", "output_en": "...", "synthesis_topic": "...", "note_en": "...", "source": "...", "source_page": N}],
  "worked_exercises": [{"prompt_en": "...", "answer_en": "...", "synthesis_topic": "...", "source": "...", "source_page": N}]
}
Tag synthesis_topic precisely. Combine/transform exercises WITH answers → worked_exercises.
Skip punctuation-only content.
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


def extract_asan_page(doc, pdf_page: int, api_key: str) -> dict:
    cache = os.path.join(CACHE_DIR, f"asan_syn_p{pdf_page:03d}.json")
    if os.path.exists(cache):
        with open(cache, "r", encoding="utf-8") as f:
            return json.load(f)
    page = doc[pdf_page - 1]
    pix = page.get_pixmap(matrix=fitz.Matrix(1.45, 1.45))
    img_b64 = base64.b64encode(pix.tobytes("jpg")).decode("utf-8")
    prompt = f"""
Extract TNPSC General English SYNTHESIS OF SENTENCES notes from this scanned ASAN page.
PDF page: {pdf_page}. Skip punctuation/direct-indirect speech if present.

Extract rules, before/after combine examples, and worked exercises WITH answers.
Tag synthesis_topic:
- combining_two_sentences (merge two sentences into one; pair to single)
- using_conjunctions (and, but, or, yet, so, compound with coordinators)
- using_participles (V+ing, having+V3, present/past/perfect participle)
- using_infinitives (to-infinitive, in order to, too...to)
- using_phrases (despite, in spite of, apposition, nominative absolute, preposition+gerund, on+V+ing)
- using_clauses (noun/adj/adverb clause, relative pronoun, subordinate conjunction, complex)
- overview (simple/compound/complex intro)
- other

Do NOT invent content.
{SCHEMA}
Set source="asan" and source_page={pdf_page} on every item.
"""
    data = call_gemini_json(
        [
            {"text": prompt},
            {"inlineData": {"mimeType": "image/jpeg", "data": img_b64}},
        ],
        api_key,
        label=f"asan syn p{pdf_page}",
    )
    os.makedirs(CACHE_DIR, exist_ok=True)
    save_json(cache, data)
    return data


def extract_text_page(text: str, source: str, pdf_page: int, api_key: str) -> dict:
    cache = os.path.join(CACHE_DIR, f"{source}_syn_p{pdf_page:03d}.json")
    if os.path.exists(cache):
        with open(cache, "r", encoding="utf-8") as f:
            return json.load(f)
    if not text.strip():
        return {"page_heading": "", "rules": [], "examples": [], "worked_exercises": []}
    prompt = f"""
Structure TNPSC General English SYNTHESIS OF SENTENCES notes.
Source={source}, PDF page={pdf_page}.

Keep ONLY sentence synthesis: combine pairs, simple/compound/complex transform, participles, infinitives, phrases, clauses.
Skip unrelated prose passages unless they contain synthesis exercises.
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


def normalize_topic(item: dict, default_source: str) -> dict:
    item = dict(item)
    st = (item.get("synthesis_topic") or "other").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "combine": "combining_two_sentences",
        "combining": "combining_two_sentences",
        "conjunction": "using_conjunctions",
        "coordinating": "using_conjunctions",
        "participle": "using_participles",
        "infinitive": "using_infinitives",
        "phrase": "using_phrases",
        "apposition": "using_phrases",
        "clause": "using_clauses",
        "complex": "using_clauses",
        "compound": "using_conjunctions",
        "simple_compound_complex": "using_clauses",
    }
    st = aliases.get(st, st)
    if st not in SYNTHESIS_TOPICS:
        st = "other"
    item["synthesis_topic"] = st
    item.setdefault("source", default_source)
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

    print(f"ASAN pages {ASAN_PAGES} (vision)")
    adoc = fitz.open(ASAN_PDF)
    for p in ASAN_PAGES:
        print(f"  asan p{p}...")
        chunk = extract_asan_page(adoc, p, api_key)
        for key in bucket:
            bucket[key].extend(
                normalize_topic(x, "asan") for x in (chunk.get(key) or []) if isinstance(x, dict)
            )
        print(
            f"    → R={len(chunk.get('rules') or [])} "
            f"E={len(chunk.get('examples') or [])} "
            f"W={len(chunk.get('worked_exercises') or [])}"
        )
        time.sleep(1.2)
    adoc.close()

    print(f"GRAMMER pages {GRAMMER_PAGES}")
    gdoc = fitz.open(GRAMMER_PDF)
    for p in GRAMMER_PAGES:
        text = gdoc[p - 1].get_text("text")
        print(f"  grammer p{p} ({len(text)} chars)...")
        chunk = extract_text_page(text, "grammer", p, api_key)
        for key in bucket:
            bucket[key].extend(
                normalize_topic(x, "grammer") for x in (chunk.get(key) or []) if isinstance(x, dict)
            )
        print(
            f"    → R={len(chunk.get('rules') or [])} "
            f"E={len(chunk.get('examples') or [])} "
            f"W={len(chunk.get('worked_exercises') or [])}"
        )
        time.sleep(0.8)
    gdoc.close()

    print(f"GOVT pages {GOVT_PAGES}")
    govdoc = fitz.open(GOVT_PDF)
    for p in GOVT_PAGES:
        text = govdoc[p - 1].get_text("text")
        print(f"  govt p{p} ({len(text)} chars)...")
        chunk = extract_text_page(text, "govt", p, api_key)
        for key in bucket:
            bucket[key].extend(
                normalize_topic(x, "govt") for x in (chunk.get(key) or []) if isinstance(x, dict)
            )
        print(
            f"    → R={len(chunk.get('rules') or [])} "
            f"E={len(chunk.get('examples') or [])} "
            f"W={len(chunk.get('worked_exercises') or [])}"
        )
        time.sleep(0.8)
    govdoc.close()

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

    by_topic = defaultdict(lambda: {"rules": 0, "examples": 0, "worked": 0})
    for r in bucket["rules"]:
        by_topic[r.get("synthesis_topic") or "other"]["rules"] += 1
    for e in bucket["examples"]:
        by_topic[e.get("synthesis_topic") or "other"]["examples"] += 1
    for w in bucket["worked_exercises"]:
        by_topic[w.get("synthesis_topic") or "other"]["worked"] += 1

    out = {
        "subject_id": "English",
        "menu": "synthesis_of_sentences",
        "sources": [
            f"asan-remaining-grammar.pdf pp.{ASAN_PAGES} (primary, vision)",
            f"Grammer.pdf pp.{GRAMMER_PAGES} (primary)",
            f"Govt pp.{GOVT_PAGES} (secondary)",
        ],
        **bucket,
        "stats": {
            "totals": {
                "rules": len(bucket["rules"]),
                "examples": len(bucket["examples"]),
                "worked_exercises": len(bucket["worked_exercises"]),
            },
            "by_synthesis_topic": dict(by_topic),
        },
    }
    save_json(NOTES_PATH, out)
    print(f"\nSaved {NOTES_PATH}")
    print(
        f"  rules={len(out['rules'])} examples={len(out['examples'])} "
        f"worked={len(out['worked_exercises'])}"
    )
    print("  by synthesis_topic:", dict(by_topic))


if __name__ == "__main__":
    main()
