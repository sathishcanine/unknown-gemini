#!/usr/bin/env python3
"""
Extract Tenses notes from:
  1) Asan PDF pp.7–39 (scanned → Gemini)
  2) Grammer.pdf pp.11–50 (text → Gemini structure; tense-only)
  3) Govt notes pp.50–59 (text; tense forms; light modals if tied to tense)

Output: English/Grammar/tenses_notes.json

Usage:
  python3 English/Grammar/extract_tenses_notes.py
  python3 English/Grammar/extract_tenses_notes.py --skip-asan
  python3 English/Grammar/extract_tenses_notes.py --asan-only
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
NOTES_PATH = os.path.join(BASE_DIR, "English", "Grammar", "tenses_notes.json")
CACHE_DIR = os.path.join(BASE_DIR, "English", "Grammar", "_tmp_tenses_extract_cache")

MODEL = "gemini-3.1-flash-lite"
ASAN_PAGES = list(range(7, 40))  # 7–39
GRAMMER_PAGES = list(range(11, 51))  # 11–50
GOVT_PAGES = list(range(50, 60))  # 50–59

TENSE_FORMS = [
    "simple_present",
    "present_continuous",
    "present_perfect",
    "present_perfect_continuous",
    "simple_past",
    "past_continuous",
    "past_perfect",
    "past_perfect_continuous",
    "simple_future",
    "future_continuous",
    "future_perfect",
    "future_perfect_continuous",
    "overview",
    "mixed",
    "other",
]


def save_json(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def call_gemini_json(parts, api_key, label=""):
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}"
        f":generateContent?key={api_key}"
    )
    headers = {"Content-Type": "application/json"}
    retries = 6
    delay = 10
    attempt = 0
    while attempt < retries:
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=150) as response:
                res_json = json.loads(response.read().decode("utf-8"))
                raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                if raw_text.startswith("```"):
                    raw_text = raw_text.split("\n", 1)[1]
                    if raw_text.endswith("```"):
                        raw_text = raw_text.rsplit("\n", 1)[0]
                start_obj = raw_text.find("{")
                if start_obj != -1:
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
                        "page_heading": data.get("page_heading") or "",
                        "rules": data.get("rules") or [],
                        "examples": data.get("examples") or [],
                        "worked_exercises": data.get("worked_exercises") or [],
                    }
                return {"page_heading": "", "rules": [], "examples": [], "worked_exercises": []}
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            if e.code in (429, 503):
                print(f"    {label} HTTP {e.code}; retry in {delay}s...")
                time.sleep(delay)
                delay = min(delay * 2, 90)
            else:
                attempt += 1
                print(f"    {label} [Attempt {attempt}/{retries}] HTTP {e.code}: {body[:140]}")
                time.sleep(5)
        except Exception as e:
            attempt += 1
            print(f"    {label} [Attempt {attempt}/{retries}] Error: {e}")
            time.sleep(5)
    return {"page_heading": "", "rules": [], "examples": [], "worked_exercises": []}


SCHEMA = """
Return ONLY JSON:
{
  "page_heading": "short heading if visible",
  "rules": [
    {"rule_en": "...", "tense_form": "simple_present|present_continuous|present_perfect|present_perfect_continuous|simple_past|past_continuous|past_perfect|past_perfect_continuous|simple_future|future_continuous|future_perfect|future_perfect_continuous|overview|mixed|other", "source": "...", "source_page": N}
  ],
  "examples": [
    {"input": "...", "output": "...", "kind": "example|transform", "note_en": "...", "tense_form": "...", "source": "...", "source_page": N}
  ],
  "worked_exercises": [
    {"prompt_en": "...", "answer_en": "...", "tense_form": "...", "source": "...", "source_page": N}
  ]
}
Use the most specific tense_form. Charts covering many forms → overview or per-row tags.
Mixed fill-in / identify-the-tense drills → mixed.
"""


def extract_asan_page(doc, pdf_page: int, api_key: str) -> dict:
    cache = os.path.join(CACHE_DIR, f"asan_p{pdf_page:03d}.json")
    if os.path.exists(cache):
        with open(cache, "r", encoding="utf-8") as f:
            return json.load(f)
    page = doc[pdf_page - 1]
    pix = page.get_pixmap(matrix=fitz.Matrix(1.3, 1.3))
    img_b64 = base64.b64encode(pix.tobytes("jpg")).decode("utf-8")
    prompt = f"""
Extract TNPSC General English TENSES notes from this scanned ASAN Academy page.
PDF page: {pdf_page}. Topic: English verb tenses (Present/Past/Future × Simple/Continuous/Perfect/Perfect Continuous).

Extract rules, examples, worked exercises WITH answers.
Do NOT invent. Skip watermarks/ads. Include readable handwritten notes if they teach a rule.
Skip Sentence Pattern / Question Tag / Concord if they appear.
{SCHEMA}
Set source="asan" and source_page={pdf_page} on every item.
"""
    data = call_gemini_json(
        [
            {"text": prompt},
            {"inlineData": {"mimeType": "image/jpeg", "data": img_b64}},
        ],
        api_key,
        label=f"asan p{pdf_page}",
    )
    os.makedirs(CACHE_DIR, exist_ok=True)
    save_json(cache, data)
    return data


def extract_text_page(text: str, source: str, pdf_page: int, api_key: str, extra: str = "") -> dict:
    cache = os.path.join(CACHE_DIR, f"{source}_p{pdf_page:03d}.json")
    if os.path.exists(cache):
        with open(cache, "r", encoding="utf-8") as f:
            return json.load(f)
    if not (text or "").strip():
        return {"page_heading": "", "rules": [], "examples": [], "worked_exercises": []}
    prompt = f"""
Structure TNPSC General English TENSES notes from textbook/govt text.
Source={source}, PDF page={pdf_page}.
{extra}

TEXT:
\"\"\"
{text[:14000]}
\"\"\"

Keep ONLY verb-tense content (forms, uses, signal words, examples, tense exercises).
Skip: Concord/SVA, Voice (except tense labels inside voice), pure Discourse/Speech chapters,
Sentence Pattern, Question Tags, vocabulary, reading comprehension.
Do NOT invent.
{SCHEMA}
Set source="{source}" and source_page={pdf_page} on every item.
"""
    data = call_gemini_json([{"text": prompt}], api_key, label=f"{source} p{pdf_page}")
    os.makedirs(CACHE_DIR, exist_ok=True)
    save_json(cache, data)
    return data


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def stamp_and_collect(bucket, chunk, default_source, page):
    for key in ("rules", "examples", "worked_exercises"):
        for item in chunk.get(key) or []:
            if not isinstance(item, dict):
                continue
            item = dict(item)
            item["source"] = item.get("source") or default_source
            item["source_page"] = item.get("source_page") or page
            tf = (item.get("tense_form") or "other").strip().lower().replace(" ", "_").replace("-", "_")
            if tf not in TENSE_FORMS:
                tf = "other"
            item["tense_form"] = tf
            bucket[key].append(item)


def dedupe_rules(rules):
    seen, out = set(), []
    for r in rules:
        en = (r.get("rule_en") or "").strip()
        if not en:
            continue
        key = normalize(en)
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def dedupe_examples(examples):
    seen, out = set(), []
    for e in examples:
        inp = (e.get("input") or "").strip()
        outp = (e.get("output") or "").strip()
        if not inp and not outp:
            continue
        key = normalize(f"{inp}|{outp}")
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out


def dedupe_exercises(items):
    seen, out = set(), []
    for x in items:
        p = (x.get("prompt_en") or "").strip()
        a = (x.get("answer_en") or "").strip()
        if not p:
            continue
        key = normalize(f"{p}|{a}")
        if key in seen:
            continue
        seen.add(key)
        out.append(x)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--asan-only", action="store_true")
    parser.add_argument("--skip-asan", action="store_true")
    parser.add_argument("--skip-grammer", action="store_true")
    parser.add_argument("--skip-govt", action="store_true")
    parser.add_argument("--fresh", action="store_true", help="Ignore page cache")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY not set")

    if args.fresh and os.path.isdir(CACHE_DIR):
        for name in os.listdir(CACHE_DIR):
            if name.endswith(".json"):
                os.remove(os.path.join(CACHE_DIR, name))
        print("Cleared extract cache")

    bucket = {"rules": [], "examples": [], "worked_exercises": []}
    page_log = []

    if not args.skip_asan:
        print(f"ASAN pages {ASAN_PAGES[0]}–{ASAN_PAGES[-1]} ({len(ASAN_PAGES)} pages)")
        doc = fitz.open(ASAN_PDF)
        for p in ASAN_PAGES:
            print(f"  asan p{p}...")
            chunk = extract_asan_page(doc, p, api_key)
            stamp_and_collect(bucket, chunk, "asan", p)
            page_log.append(
                {
                    "source": "asan",
                    "page": p,
                    "heading": chunk.get("page_heading"),
                    "rules": len(chunk.get("rules") or []),
                    "examples": len(chunk.get("examples") or []),
                    "worked": len(chunk.get("worked_exercises") or []),
                }
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
            print(f"GRAMMER pages {GRAMMER_PAGES[0]}–{GRAMMER_PAGES[-1]}")
            doc = fitz.open(GRAMMER_PDF)
            for p in GRAMMER_PAGES:
                text = doc[p - 1].get_text("text")
                print(f"  grammer p{p} ({len(text)} chars)...")
                chunk = extract_text_page(
                    text,
                    "grammer",
                    p,
                    api_key,
                    extra="Primary Tenses chapter / tense charts / form usage.",
                )
                stamp_and_collect(bucket, chunk, "grammer", p)
                page_log.append(
                    {
                        "source": "grammer",
                        "page": p,
                        "heading": chunk.get("page_heading"),
                        "rules": len(chunk.get("rules") or []),
                        "examples": len(chunk.get("examples") or []),
                        "worked": len(chunk.get("worked_exercises") or []),
                    }
                )
                print(
                    f"    → R={len(chunk.get('rules') or [])} "
                    f"E={len(chunk.get('examples') or [])} "
                    f"W={len(chunk.get('worked_exercises') or [])}"
                )
                time.sleep(0.8)
            doc.close()

        if not args.skip_govt:
            print(f"GOVT pages {GOVT_PAGES[0]}–{GOVT_PAGES[-1]}")
            doc = fitz.open(GOVT_PDF)
            for p in GOVT_PAGES:
                text = doc[p - 1].get_text("text")
                print(f"  govt p{p} ({len(text)} chars)...")
                chunk = extract_text_page(
                    text,
                    "govt",
                    p,
                    api_key,
                    extra="Govt TENSE chapter. Keep tense forms/uses; keep modals only if clearly tense-related.",
                )
                stamp_and_collect(bucket, chunk, "govt", p)
                page_log.append(
                    {
                        "source": "govt",
                        "page": p,
                        "heading": chunk.get("page_heading"),
                        "rules": len(chunk.get("rules") or []),
                        "examples": len(chunk.get("examples") or []),
                        "worked": len(chunk.get("worked_exercises") or []),
                    }
                )
                print(
                    f"    → R={len(chunk.get('rules') or [])} "
                    f"E={len(chunk.get('examples') or [])} "
                    f"W={len(chunk.get('worked_exercises') or [])}"
                )
                time.sleep(0.8)
            doc.close()

    rules = dedupe_rules(bucket["rules"])
    examples = dedupe_examples(bucket["examples"])
    worked = dedupe_exercises(bucket["worked_exercises"])

    by_form = defaultdict(lambda: {"rules": 0, "examples": 0, "worked": 0})
    for r in rules:
        by_form[r.get("tense_form") or "other"]["rules"] += 1
    for e in examples:
        by_form[e.get("tense_form") or "other"]["examples"] += 1
    for w in worked:
        by_form[w.get("tense_form") or "other"]["worked"] += 1

    by_source = defaultdict(lambda: {"rules": 0, "examples": 0, "worked": 0})
    for r in rules:
        by_source[r.get("source") or "?"]["rules"] += 1
    for e in examples:
        by_source[e.get("source") or "?"]["examples"] += 1
    for w in worked:
        by_source[w.get("source") or "?"]["worked"] += 1

    notes = {
        "subject_id": "English",
        "menu": "tenses",
        "sources": [
            "asan - concord,tense,...pdf pp.7-39",
            "Grammer.pdf pp.11-50",
            "Govt notes TENSE pp.50-59",
        ],
        "rules": rules,
        "examples": examples,
        "worked_exercises": worked,
        "stats": {
            "totals": {
                "rules": len(rules),
                "examples": len(examples),
                "worked_exercises": len(worked),
            },
            "by_source": dict(by_source),
            "by_tense_form": dict(by_form),
            "pages_processed": len(page_log),
        },
        "page_log": page_log,
    }
    save_json(NOTES_PATH, notes)

    print("\n======== EXTRACTION SUMMARY ========")
    print(f"Saved {NOTES_PATH}")
    print(
        f"TOTALS  rules={len(rules)}  examples={len(examples)}  worked={len(worked)}"
    )
    print("\nBy source:")
    for src, s in sorted(by_source.items()):
        print(f"  {src:10}  R={s['rules']:4}  E={s['examples']:4}  W={s['worked']:4}")
    print("\nBy tense_form:")
    for form in TENSE_FORMS:
        s = by_form.get(form)
        if not s:
            continue
        print(f"  {form:32}  R={s['rules']:3}  E={s['examples']:3}  W={s['worked']:3}")
    leftover = [k for k in by_form if k not in TENSE_FORMS]
    for form in leftover:
        s = by_form[form]
        print(f"  {form:32}  R={s['rules']:3}  E={s['examples']:3}  W={s['worked']:3}")


if __name__ == "__main__":
    main()
