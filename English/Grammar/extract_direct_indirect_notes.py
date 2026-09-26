#!/usr/bin/env python3
"""
Extract Direct & Indirect Speech notes from Grammer.pdf.

Primary: Grammer.pdf pp.95–108, 111, 113–114, 116, 118–120, 126–127
Secondary: Govt pp.50, 56–57 (modals in reported speech)

Output: English/Grammar/direct_indirect_notes.json
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
GOVT_PDF = os.path.join(
    BASE_DIR,
    "Data",
    "General-English",
    "General_English_Part_A_Grammar_Group_2_Govt_Notes_for_TNPSC_Group.pdf",
)
NOTES_PATH = os.path.join(BASE_DIR, "English", "Grammar", "direct_indirect_notes.json")
CACHE_DIR = os.path.join(BASE_DIR, "English", "Grammar", "_tmp_direct_indirect_extract_cache")

MODEL = "gemini-3.1-flash-lite"
GRAMMER_PAGES = [95, 96, 97, 98, 101, 103, 104, 105, 106, 107, 108, 111, 113, 114, 116, 118, 119, 120, 126, 127]
GOVT_PAGES = [50, 56, 57]

SPEECH_TOPICS = [
    "statements_dti",
    "questions",
    "commands_imperatives",
    "indirect_to_direct",
    "time_pronoun_reporting",
    "overview",
    "other",
]

SCHEMA = """
Return ONLY JSON:
{
  "page_heading": "short heading if visible",
  "rules": [{"rule_en": "...", "speech_topic": "statements_dti|questions|commands_imperatives|indirect_to_direct|time_pronoun_reporting|overview|other", "source": "grammer|govt", "source_page": N}],
  "examples": [{"direct_en": "...", "indirect_en": "...", "speech_topic": "...", "note_en": "...", "source": "...", "source_page": N}],
  "worked_exercises": [{"prompt_en": "...", "answer_en": "...", "speech_topic": "...", "source": "...", "source_page": N}]
}
Tag speech_topic precisely. Conversion drills WITH answers → worked_exercises.
Tense-change table / say-tell / time-place / pronoun rules → time_pronoun_reporting or overview.
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


def extract_text_page(text: str, pdf_page: int, source: str, api_key: str) -> dict:
    cache = os.path.join(CACHE_DIR, f"{source}_di_p{pdf_page:03d}.json")
    if os.path.exists(cache):
        with open(cache, "r", encoding="utf-8") as f:
            return json.load(f)
    if not text.strip():
        return {"page_heading": "", "rules": [], "examples": [], "worked_exercises": []}
    prompt = f"""
Structure TNPSC General English DIRECT & INDIRECT SPEECH notes from {source}.pdf page {pdf_page}.

Keep ONLY reported-speech rules, examples, and conversion exercises.
Skip unrelated grammar (articles, punctuation-only, spelling) unless speech examples.
Do NOT invent.
{SCHEMA}

TEXT:
\"\"\"
{text[:14000]}
\"\"\"
"""
    data = call_gemini_json([{"text": prompt}], api_key, label=f"{source} di p{pdf_page}")
    os.makedirs(CACHE_DIR, exist_ok=True)
    save_json(cache, data)
    return data


def normalize_topic(item: dict, default_source: str) -> dict:
    item = dict(item)
    st = (item.get("speech_topic") or "other").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "statement": "statements_dti",
        "statements": "statements_dti",
        "direct_to_indirect": "statements_dti",
        "question": "questions",
        "wh_questions": "questions",
        "yes_no": "questions",
        "command": "commands_imperatives",
        "imperative": "commands_imperatives",
        "request": "commands_imperatives",
        "indirect_to_direct_speech": "indirect_to_direct",
        "direct_speech": "indirect_to_direct",
        "time_place": "time_pronoun_reporting",
        "pronoun": "time_pronoun_reporting",
        "reporting_verbs": "time_pronoun_reporting",
        "say_tell": "time_pronoun_reporting",
        "tense_change": "time_pronoun_reporting",
    }
    st = aliases.get(st, st)
    if st not in SPEECH_TOPICS:
        st = "other"
    item["speech_topic"] = st
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

    print(f"GRAMMER pages {GRAMMER_PAGES}")
    doc = fitz.open(GRAMMER_PDF)
    for p in GRAMMER_PAGES:
        text = doc[p - 1].get_text("text")
        print(f"  grammer p{p} ({len(text)} chars)...")
        chunk = extract_text_page(text, p, "grammer", api_key)
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
    doc.close()

    print(f"GOVT pages {GOVT_PAGES}")
    gdoc = fitz.open(GOVT_PDF)
    for p in GOVT_PAGES:
        text = gdoc[p - 1].get_text("text")
        print(f"  govt p{p} ({len(text)} chars)...")
        chunk = extract_text_page(text, p, "govt", api_key)
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
    gdoc.close()

    bucket["rules"] = dedupe_items(
        bucket["rules"], lambda r: re.sub(r"\s+", " ", (r.get("rule_en") or "").lower())
    )
    bucket["examples"] = dedupe_items(
        bucket["examples"],
        lambda e: re.sub(
            r"\s+", " ", f"{e.get('direct_en')}|{e.get('indirect_en')}".lower()
        ),
    )
    bucket["worked_exercises"] = dedupe_items(
        bucket["worked_exercises"],
        lambda w: re.sub(r"\s+", " ", f"{w.get('prompt_en')}|{w.get('answer_en')}".lower()),
    )

    by_topic = defaultdict(lambda: {"rules": 0, "examples": 0, "worked": 0})
    for r in bucket["rules"]:
        by_topic[r.get("speech_topic") or "other"]["rules"] += 1
    for e in bucket["examples"]:
        by_topic[e.get("speech_topic") or "other"]["examples"] += 1
    for w in bucket["worked_exercises"]:
        by_topic[w.get("speech_topic") or "other"]["worked"] += 1

    out = {
        "subject_id": "English",
        "menu": "direct_indirect_speech",
        "sources": [
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
            "by_speech_topic": dict(by_topic),
        },
    }
    save_json(NOTES_PATH, out)
    print(f"\nSaved {NOTES_PATH}")
    print(
        f"  rules={len(out['rules'])} examples={len(out['examples'])} "
        f"worked={len(out['worked_exercises'])}"
    )
    print("  by speech_topic:", dict(by_topic))


if __name__ == "__main__":
    main()
