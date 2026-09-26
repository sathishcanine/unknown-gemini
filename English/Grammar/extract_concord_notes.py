#!/usr/bin/env python3
"""
Extract Concord (Subject–Verb Agreement) notes from:
  1) Asan PDF pp.1–6 (scanned images → Gemini)
  2) Grammer.pdf pp.326–330 (text extract → Gemini structure)
  3) Govt notes pp.77–80 (text; keep Concord/SVA/number items)

Output: English/Grammar/concord_notes.json

Usage:
  python3 English/Grammar/extract_concord_notes.py
  python3 English/Grammar/extract_concord_notes.py --asan-only
  python3 English/Grammar/extract_concord_notes.py --skip-asan
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
NOTES_PATH = os.path.join(BASE_DIR, "English", "Grammar", "concord_notes.json")

MODEL = "gemini-3.1-flash-lite"
ASAN_PAGES = list(range(1, 7))  # 1–6
GRAMMER_PAGES = list(range(326, 331))  # 326–330
GOVT_PAGES = list(range(77, 81))  # 77–80


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


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
    retries = 5
    delay = 10
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
                        "rules": data.get("rules") or [],
                        "examples": data.get("examples") or [],
                        "worked_exercises": data.get("worked_exercises") or [],
                    }
                return {"rules": [], "examples": [], "worked_exercises": []}
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            if e.code in (429, 503):
                print(f"    {label} HTTP {e.code}; retry in {delay}s...")
                time.sleep(delay)
                delay = min(delay * 2, 60)
            else:
                attempt += 1
                print(f"    {label} [Attempt {attempt}/{retries}] HTTP {e.code}: {body[:160]}")
                time.sleep(5)
        except Exception as e:
            attempt += 1
            print(f"    {label} [Attempt {attempt}/{retries}] Error: {e}")
            time.sleep(5)
    return {"rules": [], "examples": [], "worked_exercises": []}


SCHEMA_HINT = """
Return ONLY JSON:
{
  "rules": [{"rule_en": "...", "source": "...", "source_page": N, "tag": "optional_subtopic"}],
  "examples": [{"input": "...", "output": "...", "kind": "example|transform", "note_en": "...", "source": "...", "source_page": N}],
  "worked_exercises": [{"prompt_en": "...", "answer_en": "...", "source": "...", "source_page": N}]
}
Tags if clear: basic_singular_plural | and_plural | one_idea_singular | as_well_as_with |
either_or_neither_nor | each_every_indefinite | collective_nouns | plural_form_singular_meaning |
units_money_time_distance | titles_same_vs_different | intervening_phrase | always_plural_set | error_spotting
"""


def extract_asan_page(doc, pdf_page: int, api_key: str) -> dict:
    page = doc[pdf_page - 1]
    pix = page.get_pixmap(matrix=fitz.Matrix(1.35, 1.35))
    img_b64 = base64.b64encode(pix.tobytes("jpg")).decode("utf-8")
    prompt = f"""
You are extracting TNPSC General English CONCORD (Subject–Verb Agreement) NOTES
from a scanned ASAN Academy page. PDF page: {pdf_page}.

Extract rules, examples, and worked exercises WITH answers.
Do NOT invent content. Skip watermarks/ads.
Include readable handwritten margin notes if they teach a rule.
{SCHEMA_HINT}
Set source="asan" and source_page={pdf_page} on every item.
"""
    return call_gemini_json(
        [
            {"text": prompt},
            {"inlineData": {"mimeType": "image/jpeg", "data": img_b64}},
        ],
        api_key,
        label=f"asan p{pdf_page}",
    )


def extract_text_chunk(text: str, source: str, pdf_page: int, api_key: str, extra: str = "") -> dict:
    if not (text or "").strip():
        return {"rules": [], "examples": [], "worked_exercises": []}
    prompt = f"""
You are structuring TNPSC General English CONCORD (Subject–Verb Agreement) notes
from textbook/govt text. Source={source}, PDF page={pdf_page}.

{extra}

TEXT:
\"\"\"
{text[:12000]}
\"\"\"

Extract only Concord / subject-verb agreement / singular-plural number agreement content.
Skip unrelated topics (articles-only, pure prepositions, process writing, question tags).
Do NOT invent rules not in the text.
{SCHEMA_HINT}
Set source="{source}" and source_page={pdf_page} on every item.
"""
    return call_gemini_json([{"text": prompt}], api_key, label=f"{source} p{pdf_page}")


def normalize_rule(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def dedupe_rules(rules: list) -> list:
    seen = set()
    out = []
    for r in rules:
        if not isinstance(r, dict):
            continue
        en = (r.get("rule_en") or "").strip()
        if not en:
            continue
        key = normalize_rule(en)
        if key in seen:
            continue
        seen.add(key)
        item = {
            "rule_en": en,
            "source": r.get("source") or "asan",
            "source_page": r.get("source_page"),
        }
        if r.get("tag"):
            item["tag"] = r.get("tag")
        out.append(item)
    return out


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
        key = normalize_rule(f"{inp}|{outp}")
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "input": inp,
                "output": outp,
                "kind": e.get("kind") or "example",
                "note_en": (e.get("note_en") or "").strip(),
                "source": e.get("source") or "asan",
                "source_page": e.get("source_page"),
            }
        )
    return out


def dedupe_exercises(items: list) -> list:
    seen = set()
    out = []
    for x in items:
        if not isinstance(x, dict):
            continue
        p = (x.get("prompt_en") or "").strip()
        a = (x.get("answer_en") or "").strip()
        if not p:
            continue
        key = normalize_rule(f"{p}|{a}")
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "prompt_en": p,
                "answer_en": a,
                "source": x.get("source") or "asan",
                "source_page": x.get("source_page"),
            }
        )
    return out


def merge_into(bucket: dict, chunk: dict):
    bucket["rules"].extend(chunk.get("rules") or [])
    bucket["examples"].extend(chunk.get("examples") or [])
    bucket["worked_exercises"].extend(chunk.get("worked_exercises") or [])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--asan-only", action="store_true")
    parser.add_argument("--skip-asan", action="store_true")
    parser.add_argument("--skip-grammer", action="store_true")
    parser.add_argument("--skip-govt", action="store_true")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY not set")

    bucket = {"rules": [], "examples": [], "worked_exercises": []}

    if not args.skip_asan:
        if not os.path.exists(ASAN_PDF):
            raise SystemExit(f"Missing {ASAN_PDF}")
        print(f"ASAN: {ASAN_PDF} pages {ASAN_PAGES[0]}–{ASAN_PAGES[-1]}")
        doc = fitz.open(ASAN_PDF)
        for p in ASAN_PAGES:
            print(f"  extracting asan p{p}...")
            chunk = extract_asan_page(doc, p, api_key)
            print(
                f"    → rules={len(chunk['rules'])} examples={len(chunk['examples'])} "
                f"ex={len(chunk['worked_exercises'])}"
            )
            merge_into(bucket, chunk)
            time.sleep(1.5)
        doc.close()

    if args.asan_only:
        pass
    else:
        if not args.skip_grammer and os.path.exists(GRAMMER_PDF):
            print(f"GRAMMER: pages {GRAMMER_PAGES[0]}–{GRAMMER_PAGES[-1]}")
            doc = fitz.open(GRAMMER_PDF)
            for p in GRAMMER_PAGES:
                text = doc[p - 1].get_text("text")
                print(f"  structuring grammer p{p} ({len(text)} chars)...")
                chunk = extract_text_chunk(
                    text,
                    "grammer",
                    p,
                    api_key,
                    extra="This is the Subject and Verb Agreement (Concord) section.",
                )
                print(
                    f"    → rules={len(chunk['rules'])} examples={len(chunk['examples'])} "
                    f"ex={len(chunk['worked_exercises'])}"
                )
                merge_into(bucket, chunk)
                time.sleep(1.2)
            doc.close()

        if not args.skip_govt and os.path.exists(GOVT_PDF):
            print(f"GOVT: pages {GOVT_PAGES[0]}–{GOVT_PAGES[-1]}")
            doc = fitz.open(GOVT_PDF)
            for p in GOVT_PAGES:
                text = doc[p - 1].get_text("text")
                print(f"  structuring govt p{p} ({len(text)} chars)...")
                chunk = extract_text_chunk(
                    text,
                    "govt",
                    p,
                    api_key,
                    extra=(
                        "Govt Find-out-the-Error chapter. Keep ONLY Concord / "
                        "singular-plural number / subject-verb agreement items. "
                        "Drop pure article or preposition rules."
                    ),
                )
                print(
                    f"    → rules={len(chunk['rules'])} examples={len(chunk['examples'])} "
                    f"ex={len(chunk['worked_exercises'])}"
                )
                merge_into(bucket, chunk)
                time.sleep(1.2)
            doc.close()

    notes = {
        "subject_id": "English",
        "menu": "concord",
        "topic_id": "concord",
        "topic_en": "Concord",
        "sources": [
            "asan - concord,tense, sentence pattern, question tag.pdf pp.1-6",
            "Grammer.pdf pp.326-330",
            "Govt notes Find-out-the-Error pp.77-80 (Concord/SVA only)",
        ],
        "rules": dedupe_rules(bucket["rules"]),
        "examples": dedupe_examples(bucket["examples"]),
        "worked_exercises": dedupe_exercises(bucket["worked_exercises"]),
    }
    save_json(NOTES_PATH, notes)
    print(
        f"\nSaved {NOTES_PATH}\n"
        f"  rules={len(notes['rules'])} examples={len(notes['examples'])} "
        f"worked={len(notes['worked_exercises'])}"
    )


if __name__ == "__main__":
    main()
