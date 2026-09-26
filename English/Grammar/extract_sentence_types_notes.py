#!/usr/bin/env python3
"""
Extract Types of Sentences notes.

Primary:   Asan `asan - concord,tense, sentence pattern, question tag.pdf` pp.40–44 (scanned)
Secondary: Grammer.pdf pp.60, 137, 453 (assertive/interrogative/imperative/exclamatory)
Secondary: Govt pp.44–46 (question tag context — assertive statements)

Output: English/Grammar/sentence_types_notes.json
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
from collections import Counter, defaultdict

import fitz

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASAN_PDF = os.path.join(
    BASE_DIR,
    "Data",
    "General-English",
    "asan - concord,tense, sentence pattern, question tag.pdf",
)
GRAMMER_PDF = os.path.join(BASE_DIR, "Data", "General-English", "Grammer.pdf")
GOVT_PDF = os.path.join(
    BASE_DIR,
    "Data",
    "General-English",
    "General_English_Part_A_Grammar_Group_2_Govt_Notes_for_TNPSC_Group.pdf",
)
NOTES_PATH = os.path.join(BASE_DIR, "English", "Grammar", "sentence_types_notes.json")
CACHE_DIR = os.path.join(BASE_DIR, "English", "Grammar", "_tmp_sentence_types_extract_cache")

MODEL = "gemini-3.1-flash-lite"
ASAN_PAGES = list(range(40, 45))
GRAMMER_PAGES = [60, 137, 453]
GOVT_PAGES = [44, 45, 46]

SENTENCE_TOPICS = [
    "statement_assertive",
    "interrogative",
    "imperative",
    "exclamatory",
    "overview",
    "other",
]

SCHEMA = """
Return ONLY JSON:
{
  "page_heading": "short heading if visible",
  "rules": [{"rule_en": "...", "sentence_topic": "statement_assertive|interrogative|imperative|exclamatory|overview|other", "source": "...", "source_page": N}],
  "examples": [{"input": "...", "output": "...", "kind": "example|identify|transform", "sentence_topic": "...", "note_en": "...", "source": "...", "source_page": N}],
  "worked_exercises": [{"prompt_en": "...", "answer_en": "...", "sentence_topic": "...", "source": "...", "source_page": N}]
}
Tag sentence_topic precisely. MCQ/fill-in with answers → worked_exercises.
Assertive = declarative = statement.
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
                print(f"    {label} HTTP {e.code}")
                time.sleep(5)
        except Exception as e:
            print(f"    {label} attempt {attempt+1}: {e}")
            time.sleep(delay)
            delay = min(delay * 2, 60)
    return {"page_heading": "", "rules": [], "examples": [], "worked_exercises": []}


def extract_asan_page(doc, pdf_page: int, api_key: str) -> dict:
    cache = os.path.join(CACHE_DIR, f"asan_st_p{pdf_page:03d}.json")
    if os.path.exists(cache):
        with open(cache, "r", encoding="utf-8") as f:
            return json.load(f)
    page = doc[pdf_page - 1]
    pix = page.get_pixmap(matrix=fitz.Matrix(1.35, 1.35))
    img_b64 = base64.b64encode(pix.tobytes("jpg")).decode("utf-8")
    prompt = f"""
Extract TNPSC General English TYPES OF SENTENCES notes from this scanned ASAN page.
PDF page: {pdf_page} (sentence pattern / types of sentences section).

Extract rules, example sentences, and worked exercises WITH answers.
Tag each item sentence_topic:
- statement_assertive (declarative / assertive / statement — states a fact)
- interrogative (asks a question; ends with ?)
- imperative (command, request, advice; subject you omitted)
- exclamatory (strong feeling; What/How; ends with !)
- overview (four kinds of sentences, punctuation)
- other

Skip pure sentence-pattern SV/SVO drills unless they identify sentence type.
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
        label=f"asan st p{pdf_page}",
    )
    os.makedirs(CACHE_DIR, exist_ok=True)
    save_json(cache, data)
    return data


def extract_text_page(text: str, source: str, pdf_page: int, api_key: str) -> dict:
    cache = os.path.join(CACHE_DIR, f"{source}_st_p{pdf_page:03d}.json")
    if os.path.exists(cache):
        with open(cache, "r", encoding="utf-8") as f:
            return json.load(f)
    if not text.strip():
        return {"page_heading": "", "rules": [], "examples": [], "worked_exercises": []}
    prompt = f"""
Structure TNPSC General English TYPES OF SENTENCES notes.
Source={source}, PDF page={pdf_page}.

Keep ONLY content about assertive/declarative, interrogative, imperative, exclamatory sentences.
Include identification exercises and punctuation rules if present.
Skip unrelated grammar (tenses, voice, reported speech details).
Do NOT invent.
{SCHEMA}
Set source="{source}" and source_page={pdf_page} on every item.

TEXT:
\"\"\"
{text[:14000]}
\"\"\"
"""
    data = call_gemini_json([{"text": prompt}], api_key, label=f"{source} st p{pdf_page}")
    os.makedirs(CACHE_DIR, exist_ok=True)
    save_json(cache, data)
    return data


def normalize_tag(item: dict) -> dict:
    item = dict(item)
    st = (item.get("sentence_topic") or "other").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "declarative": "statement_assertive",
        "assertive": "statement_assertive",
        "statement": "statement_assertive",
        "statements": "statement_assertive",
    }
    st = aliases.get(st, st)
    if st not in SENTENCE_TOPICS:
        st = "other"
    item["sentence_topic"] = st
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
    parser.add_argument("--asan-only", action="store_true")
    parser.add_argument("--skip-asan", action="store_true")
    parser.add_argument("--skip-grammer", action="store_true")
    parser.add_argument("--skip-govt", action="store_true")
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY not set")

    if args.fresh and os.path.isdir(CACHE_DIR):
        for name in os.listdir(CACHE_DIR):
            if name.endswith(".json"):
                os.remove(os.path.join(CACHE_DIR, name))
        print("Cleared sentence-types extract cache")

    bucket = {"rules": [], "examples": [], "worked_exercises": []}

    if not args.skip_asan:
        if not os.path.exists(ASAN_PDF):
            raise SystemExit(f"Missing {ASAN_PDF}")
        print(f"ASAN pages {ASAN_PAGES[0]}–{ASAN_PAGES[-1]}")
        doc = fitz.open(ASAN_PDF)
        for p in ASAN_PAGES:
            print(f"  asan p{p}...")
            chunk = extract_asan_page(doc, p, api_key)
            for key in bucket:
                bucket[key].extend(
                    normalize_tag(x) for x in (chunk.get(key) or []) if isinstance(x, dict)
                )
            print(
                f"    → R={len(chunk.get('rules') or [])} "
                f"E={len(chunk.get('examples') or [])} "
                f"W={len(chunk.get('worked_exercises') or [])} | {chunk.get('page_heading')}"
            )
            time.sleep(1.0)
        doc.close()

    if not args.asan_only:
        if not args.skip_grammer:
            print(f"GRAMMER pages {GRAMMER_PAGES}")
            doc = fitz.open(GRAMMER_PDF)
            for p in GRAMMER_PAGES:
                text = doc[p - 1].get_text("text")
                print(f"  grammer p{p} ({len(text)} chars)...")
                chunk = extract_text_page(text, "grammer", p, api_key)
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

        if not args.skip_govt:
            print(f"GOVT pages {GOVT_PAGES}")
            doc = fitz.open(GOVT_PDF)
            for p in GOVT_PAGES:
                text = doc[p - 1].get_text("text")
                print(f"  govt p{p} ({len(text)} chars)...")
                chunk = extract_text_page(text, "govt", p, api_key)
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

    by_topic = defaultdict(lambda: {"rules": 0, "examples": 0, "worked": 0})
    for r in bucket["rules"]:
        by_topic[r.get("sentence_topic") or "other"]["rules"] += 1
    for e in bucket["examples"]:
        by_topic[e.get("sentence_topic") or "other"]["examples"] += 1
    for w in bucket["worked_exercises"]:
        by_topic[w.get("sentence_topic") or "other"]["worked"] += 1

    out = {
        "subject_id": "English",
        "menu": "types_of_sentences",
        "sources": [
            f"asan - concord,tense, sentence pattern, question tag.pdf pp.{ASAN_PAGES[0]}–{ASAN_PAGES[-1]} (primary)",
            f"Grammer.pdf pp.{GRAMMER_PAGES} (secondary)",
            f"Govt question-tag pp.{GOVT_PAGES[0]}–{GOVT_PAGES[-1]} (secondary)",
        ],
        **bucket,
        "stats": {
            "totals": {
                "rules": len(bucket["rules"]),
                "examples": len(bucket["examples"]),
                "worked_exercises": len(bucket["worked_exercises"]),
            },
            "by_sentence_topic": dict(by_topic),
        },
    }
    save_json(NOTES_PATH, out)

    print(f"\nSaved {NOTES_PATH}")
    print(
        f"  rules={len(out['rules'])} examples={len(out['examples'])} "
        f"worked={len(out['worked_exercises'])}"
    )
    print("  by sentence_topic:", dict(by_topic))


if __name__ == "__main__":
    main()
