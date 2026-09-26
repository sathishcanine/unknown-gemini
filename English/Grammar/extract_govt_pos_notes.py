#!/usr/bin/env python3
"""
Extract TNPSC Govt Notes (Group 2) Parts-of-Speech content into
English/Grammar/parts_of_speech_notes.json (merge; do not wipe Asan).

PDF: Data/General-English/General_English_Part_A_Grammar_Group_2_Govt_Notes_for_TNPSC_Group.pdf
Mostly text-extractable — uses page text + Gemini structuring (no OCR images).

Usage:
  python3 English/Grammar/extract_govt_pos_notes.py --all
  python3 English/Grammar/extract_govt_pos_notes.py --topic verb
  python3 English/Grammar/extract_govt_pos_notes.py --list
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

import fitz

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PDF_PATH = os.path.join(
    BASE_DIR,
    "Data",
    "General-English",
    "General_English_Part_A_Grammar_Group_2_Govt_Notes_for_TNPSC_Group.pdf",
)
NOTES_PATH = os.path.join(BASE_DIR, "English", "Grammar", "parts_of_speech_notes.json")
SOURCE_MAP_PATH = os.path.join(
    BASE_DIR, "English", "Grammar", "parts_of_speech_source_map.json"
)

MODEL = "gemini-3.1-flash-lite"
MAX_WORKERS = 3

# 1-based inclusive PDF pages (covers/blanks skipped)
TOPIC_PAGES = {
    "noun": [83, 100, 101],  # POS noun notes + Plural Forms
    "pronoun": [84, 85],
    "adjective": [86, 87, 88, 89, 90],  # adj continues onto p90 before Verb
    "verb": [90, 91],  # Verb starts end of p90
    "adverb": [92, 93, 94, 95],
    "preposition": list(range(31, 42)) + [96],  # dedicated topic + POS chapter
    "conjunction": [96],
    "interjection": [96],
    "mixed_pos": [77, 78, 79, 80, 97],  # error drills + odd-word list
}

TOPIC_NAMES = {
    "noun": "Noun",
    "pronoun": "Pronoun",
    "adjective": "Adjective",
    "verb": "Verb",
    "adverb": "Adverb",
    "preposition": "Preposition",
    "conjunction": "Conjunction",
    "interjection": "Interjection",
    "mixed_pos": "Mixed Parts of Speech / error & odd-word drills",
}


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


def page_text(doc, page_1: int) -> str:
    t = doc[page_1 - 1].get_text("text") or ""
    # Drop repeated running headers noise lightly
    lines = []
    for ln in t.splitlines():
        s = ln.strip()
        if not s:
            continue
        if s.startswith("FIND THE ODD WORDS") and len(s) > 40:
            continue
        if s.startswith("FIND OUT THE ERROR") and len(s) > 40:
            continue
        lines.append(s)
    return "\n".join(lines)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def call_gemini_text(topic_name, pdf_page, text, api_key):
    if len(text.strip()) < 40:
        return {"rules": [], "examples": [], "worked_exercises": []}

    prompt = f"""
You are extracting TNPSC General English grammar NOTES from Tamil Nadu
Government (Department of Employment and Training) Group-II study material.

Topic focus: "{topic_name}"
PDF page: {pdf_page}

PAGE TEXT:
\"\"\"
{text[:12000]}
\"\"\"

Extract teaching content useful for MCQ practice for "{topic_name}" ONLY.
Ignore other parts of speech if they appear on a shared page.

Return:
1) RULES — definitions, classifications, usage tips
2) EXAMPLES — word/sentence illustrations
3) WORKED_EXERCISES — incorrect→correct or odd-word items WITH answers when given

Rules:
- Keep English accurate.
- Do NOT invent content not in the page text.
- Skip copyright/cover boilerplate.
- kind: definition|classification|transform|example|exercise|other

Return ONLY JSON object:
{{
  "rules": [{{"rule_en": "...", "source": "govt", "source_page": {pdf_page}}}],
  "examples": [{{
    "input": "...", "output": "...", "kind": "example",
    "note_en": "", "source": "govt", "source_page": {pdf_page}
  }}],
  "worked_exercises": [{{
    "prompt_en": "...", "answer_en": "...",
    "source": "govt", "source_page": {pdf_page}
  }}]
}}
"""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}"
        f":generateContent?key={api_key}"
    )
    headers = {"Content-Type": "application/json"}
    retries = 5
    delay = 8
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
                print(f"    P{pdf_page} HTTP {e.code}; retry in {delay}s...")
                time.sleep(delay)
                delay = min(delay * 2, 60)
            else:
                attempt += 1
                print(f"    P{pdf_page} [Attempt {attempt}/{retries}] HTTP {e.code}: {body[:140]}")
                time.sleep(4)
        except Exception as e:
            attempt += 1
            print(f"    P{pdf_page} [Attempt {attempt}/{retries}] Error: {e}")
            time.sleep(4)
    return {"rules": [], "examples": [], "worked_exercises": []}


def dedupe_rules(rules: list) -> list:
    seen, out = set(), []
    for r in rules:
        if not isinstance(r, dict):
            continue
        en = (r.get("rule_en") or "").strip()
        if not en:
            continue
        key = normalize(en)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "rule_en": en,
                "source": r.get("source") or "govt",
                "source_page": r.get("source_page"),
            }
        )
    return out


def dedupe_examples(examples: list) -> list:
    seen, out = set(), []
    for e in examples:
        if not isinstance(e, dict):
            continue
        inp = (e.get("input") or "").strip()
        outp = (e.get("output") or "").strip()
        if not inp and not outp:
            continue
        key = normalize(inp + "→" + outp)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "input": inp,
                "output": outp,
                "kind": e.get("kind") or "example",
                "note_en": (e.get("note_en") or "").strip(),
                "source": e.get("source") or "govt",
                "source_page": e.get("source_page"),
            }
        )
    return out


def dedupe_exercises(items: list) -> list:
    seen, out = set(), []
    for e in items:
        if not isinstance(e, dict):
            continue
        prompt = (e.get("prompt_en") or "").strip()
        ans = (e.get("answer_en") or "").strip()
        if not prompt:
            continue
        key = normalize(prompt + "|" + ans)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "prompt_en": prompt,
                "answer_en": ans,
                "source": e.get("source") or "govt",
                "source_page": e.get("source_page"),
            }
        )
    return out


def merge_lists(existing: list, new_items: list, kind: str) -> list:
    """Append govt items; dedupe against existing by normalized text."""
    if kind == "rules":
        base = list(existing or [])
        seen = {normalize(r.get("rule_en", "")) for r in base if isinstance(r, dict)}
        for r in new_items:
            key = normalize(r.get("rule_en", ""))
            if key and key not in seen:
                base.append(r)
                seen.add(key)
        return base
    if kind == "examples":
        base = list(existing or [])
        seen = {
            normalize((e.get("input") or "") + "→" + (e.get("output") or ""))
            for e in base
            if isinstance(e, dict)
        }
        for e in new_items:
            key = normalize((e.get("input") or "") + "→" + (e.get("output") or ""))
            if key and key not in seen:
                base.append(e)
                seen.add(key)
        return base
    # exercises
    base = list(existing or [])
    seen = {
        normalize((e.get("prompt_en") or "") + "|" + (e.get("answer_en") or ""))
        for e in base
        if isinstance(e, dict)
    }
    for e in new_items:
        key = normalize((e.get("prompt_en") or "") + "|" + (e.get("answer_en") or ""))
        if key and key not in seen:
            base.append(e)
            seen.add(key)
    return base


def get_block(notes: dict, topic_id: str) -> dict:
    if topic_id == "mixed_pos":
        return notes.setdefault(
            "mixed_pos",
            {
                "name_en": TOPIC_NAMES["mixed_pos"],
                "rules": [],
                "examples": [],
                "worked_exercises": [],
                "sources": {},
                "status": "empty",
            },
        )
    topics = notes.setdefault("topics", {})
    if topic_id not in topics:
        topics[topic_id] = {
            "name_en": TOPIC_NAMES.get(topic_id, topic_id),
            "rules": [],
            "examples": [],
            "worked_exercises": [],
            "pyq_samples": [],
            "sources": {},
            "status": "empty",
        }
    return topics[topic_id]


def extract_topic(topic_id: str, api_key: str, doc) -> int:
    pages = TOPIC_PAGES.get(topic_id)
    if not pages:
        raise SystemExit(f"Unknown topic: {topic_id}")
    topic_name = TOPIC_NAMES[topic_id]
    print(f"\n=== {topic_id} ({topic_name}) pages {pages} ===")

    jobs = []
    for p in pages:
        text = page_text(doc, p)
        if len(text.strip()) < 40:
            print(f"  P{p}: skip (empty/boilerplate)")
            continue
        jobs.append((p, text))

    collected_r, collected_e, collected_w = [], [], []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = {
            ex.submit(call_gemini_text, topic_name, p, text, api_key): p
            for p, text in jobs
        }
        for fut in as_completed(futs):
            p = futs[fut]
            try:
                data = fut.result() or {}
            except Exception as e:
                print(f"  P{p} failed: {e}")
                data = {}
            r = data.get("rules") or []
            e = data.get("examples") or []
            w = data.get("worked_exercises") or []
            print(f"  P{p}: {len(r)} rules, {len(e)} examples, {len(w)} worked")
            collected_r.extend(r)
            collected_e.extend(e)
            collected_w.extend(w)

    new_r = dedupe_rules(collected_r)
    new_e = dedupe_examples(collected_e)
    new_w = dedupe_exercises(collected_w)

    notes = load_json(NOTES_PATH, {"topics": {}})
    block = get_block(notes, topic_id)
    before = (
        len(block.get("rules") or []),
        len(block.get("examples") or []),
        len(block.get("worked_exercises") or []),
    )
    block["rules"] = merge_lists(block.get("rules"), new_r, "rules")
    block["examples"] = merge_lists(block.get("examples"), new_e, "examples")
    block["worked_exercises"] = merge_lists(
        block.get("worked_exercises"), new_w, "exercises"
    )
    block["name_en"] = TOPIC_NAMES.get(topic_id, topic_id)
    block.setdefault("sources", {})["govt_pdf_pages"] = pages
    # status
    has_asan = any(
        (x.get("source") == "asan")
        for x in (block.get("rules") or []) + (block.get("examples") or [])
    )
    has_govt = any(
        (x.get("source") == "govt")
        for x in (block.get("rules") or [])
        + (block.get("examples") or [])
        + (block.get("worked_exercises") or [])
    )
    has_pyq = bool(block.get("pyq_samples"))
    if has_asan and has_govt:
        block["status"] = "asan_and_govt" + ("_pyq" if has_pyq else "")
    elif has_govt and has_pyq:
        block["status"] = "govt_and_pyq"
    elif has_govt:
        block["status"] = "govt_extracted"
    elif has_asan:
        block["status"] = "asan_and_pyq" if has_pyq else "asan_extracted"

    # Clear Verb notes_gap if we got govt verb content
    if topic_id == "verb" and has_govt:
        block.pop("notes_gap", None)
        if not has_asan:
            block["status"] = "govt_extracted" + ("_pyq" if has_pyq else "")

    block["govt_extract_meta"] = {
        "pdf": os.path.basename(PDF_PATH),
        "pages": pages,
        "added_rules": len(block.get("rules") or []) - before[0],
        "added_examples": len(block.get("examples") or []) - before[1],
        "added_worked": len(block.get("worked_exercises") or []) - before[2],
        "model": MODEL,
    }
    notes["model_govt"] = MODEL
    save_json(NOTES_PATH, notes)
    added = (
        block["govt_extract_meta"]["added_rules"]
        + block["govt_extract_meta"]["added_examples"]
        + block["govt_extract_meta"]["added_worked"]
    )
    print(
        f"Merged {topic_id}: +{added} new items "
        f"(now R={len(block['rules'])} E={len(block['examples'])} "
        f"W={len(block['worked_exercises'])})"
    )
    return added


def update_source_map():
    smap = load_json(SOURCE_MAP_PATH, {"menu": "parts_of_speech", "files": {}})
    smap.setdefault("files", {})["govt"] = {
        "path": "Data/General-English/General_English_Part_A_Grammar_Group_2_Govt_Notes_for_TNPSC_Group.pdf",
        "pages": 126,
        "role": "secondary_notes_pos",
    }
    smap["govt_topics"] = {
        tid: {"pdf_pages": pages, "name_en": TOPIC_NAMES[tid]}
        for tid, pages in TOPIC_PAGES.items()
    }
    save_json(SOURCE_MAP_PATH, smap)


def main():
    parser = argparse.ArgumentParser(description="Extract Govt Notes POS content")
    parser.add_argument("--topic")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    if args.list:
        for tid, pages in TOPIC_PAGES.items():
            print(f"{tid}: {pages}")
        return

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY not found.")
    if not os.path.exists(PDF_PATH):
        raise SystemExit(f"Missing PDF: {PDF_PATH}")

    update_source_map()

    if args.all:
        topics = [
            "noun",
            "pronoun",
            "adjective",
            "verb",
            "adverb",
            "preposition",
            "conjunction",
            "interjection",
            "mixed_pos",
        ]
    elif args.topic:
        topics = [args.topic]
    else:
        raise SystemExit("Pass --topic <id> or --all")

    doc = fitz.open(PDF_PATH)
    total = 0
    try:
        for tid in topics:
            total += extract_topic(tid, api_key, doc)
    finally:
        doc.close()
    print(f"\nDone. Total new items merged: {total}")


if __name__ == "__main__":
    main()
