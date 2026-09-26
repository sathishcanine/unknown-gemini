#!/usr/bin/env python3
"""
Extract ASAN Academy Parts-of-Speech notes (45-page PDF) via Gemini OCR.

Writes: English/Grammar/parts_of_speech_notes.json

Usage:
  python3 English/Grammar/extract_asan_pos_notes.py --all
  python3 English/Grammar/extract_asan_pos_notes.py --topic noun
  python3 English/Grammar/extract_asan_pos_notes.py --list
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
from concurrent.futures import ThreadPoolExecutor, as_completed

import fitz

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PDF_PATH = os.path.join(
    BASE_DIR, "Data", "General-English", "asan parts of speech (1).pdf"
)
NOTES_PATH = os.path.join(BASE_DIR, "English", "Grammar", "parts_of_speech_notes.json")
TOPICS_PATH = os.path.join(
    BASE_DIR, "English", "Grammar", "parts_of_speech_topics.json"
)
SOURCE_MAP_PATH = os.path.join(
    BASE_DIR, "English", "Grammar", "parts_of_speech_source_map.json"
)

MODEL = "gemini-3.1-flash-lite"
MAX_WORKERS = 2

# PDF page numbers are 1-based inclusive (from asan_page_map.json scan).
# Note: ASAN chapter says Verb is discussed separately — no Verb pages here.
TOPIC_PAGES = {
    "noun": (2, 7),
    "adjective": (8, 12),
    "adverb": (13, 18),
    "mixed_pos": (19, 19),  # POS identification exercises spanning multiple POS
    "preposition": (20, 32),
    "pronoun": (33, 36),
    "conjunction": (37, 44),
    "interjection": (45, 45),
    # verb intentionally absent from this PDF
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
    "mixed_pos": "Mixed Parts of Speech exercises",
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


def render_page_jpg_b64(doc, page_idx_0: int, scale: float = 1.35) -> str:
    page = doc[page_idx_0]
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
    return base64.b64encode(pix.tobytes("jpg")).decode("utf-8")


def call_gemini_page(topic_name, pdf_page, img_base64, api_key):
    prompt = f"""
You are extracting TNPSC General English grammar NOTES from a scanned ASAN Academy page.
Book: ASAN Academy — Parts of Speech
Topic focus: "{topic_name}"
PDF page: {pdf_page}

Extract teaching content useful for MCQ practice:

1) RULES — definitions, classifications, usage tips, comparison notes (e.g. since vs for).
2) EXAMPLES — word lists, sentence examples, transformations, tables of forms.
3) WORKED_EXERCISES — short exercise items WITH clear answers (printed or handwritten).
   Skip long unanswered exercise dumps; keep items that teach a rule with an answer.

Rules:
- Keep English accurate. Include useful handwritten margin notes when readable.
- Do NOT invent content not visible on the page.
- Skip pure ads / watermarks / blank decoration.
- For examples use input→output when it is a transform; else put the example text in "input"
  and leave "output" empty, with kind="example".
- kind values: "definition" | "classification" | "transform" | "example" | "exercise" | "other"

Return ONLY JSON object:
{{
  "rules": [
    {{
      "rule_en": "...",
      "source": "asan",
      "source_page": {pdf_page}
    }}
  ],
  "examples": [
    {{
      "input": "...",
      "output": "...",
      "kind": "example",
      "note_en": "...",
      "source": "asan",
      "source_page": {pdf_page}
    }}
  ],
  "worked_exercises": [
    {{
      "prompt_en": "...",
      "answer_en": "...",
      "source": "asan",
      "source_page": {pdf_page}
    }}
  ]
}}
"""
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {"inlineData": {"mimeType": "image/jpeg", "data": img_base64}},
                ]
            }
        ],
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
                print(f"    P{pdf_page} HTTP {e.code}; retry in {delay}s...")
                time.sleep(delay)
                delay = min(delay * 2, 60)
            else:
                attempt += 1
                print(f"    P{pdf_page} [Attempt {attempt}/{retries}] HTTP {e.code}: {body[:160]}")
                time.sleep(5)
        except Exception as e:
            attempt += 1
            print(f"    P{pdf_page} [Attempt {attempt}/{retries}] Error: {e}")
            time.sleep(5)
    return {"rules": [], "examples": [], "worked_exercises": []}


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
        out.append(
            {
                "rule_en": en,
                "source": r.get("source") or "asan",
                "source_page": r.get("source_page"),
            }
        )
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
        key = normalize_rule(inp + "→" + outp)
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
    for e in items:
        if not isinstance(e, dict):
            continue
        prompt = (e.get("prompt_en") or "").strip()
        ans = (e.get("answer_en") or "").strip()
        if not prompt:
            continue
        key = normalize_rule(prompt + "|" + ans)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "prompt_en": prompt,
                "answer_en": ans,
                "source": e.get("source") or "asan",
                "source_page": e.get("source_page"),
            }
        )
    return out


def empty_notes_shell() -> dict:
    topics = {}
    for tid, name in TOPIC_NAMES.items():
        if tid == "mixed_pos":
            continue
        topics[tid] = {
            "name_en": name,
            "rules": [],
            "examples": [],
            "worked_exercises": [],
            "pyq_samples": [],
            "sources": {},
            "status": "empty",
        }
    topics["verb"]["status"] = "no_asan_pages"
    topics["verb"]["notes_gap"] = (
        "ASAN Parts of Speech PDF states Verb is discussed separately; "
        "fill later from Grammer.pdf / Verbs chapter."
    )
    return {
        "menu": "parts_of_speech",
        "primary_notes": "asan",
        "pdf": "Data/General-English/asan parts of speech (1).pdf",
        "model": MODEL,
        "topics": topics,
        "mixed_pos": {
            "name_en": TOPIC_NAMES["mixed_pos"],
            "rules": [],
            "examples": [],
            "worked_exercises": [],
            "sources": {},
            "status": "empty",
        },
    }


def extract_topic(topic_id: str, api_key: str):
    if topic_id not in TOPIC_PAGES:
        if topic_id == "verb":
            notes = load_json(NOTES_PATH, empty_notes_shell())
            block = notes["topics"]["verb"]
            block["status"] = "no_asan_pages"
            block["notes_gap"] = (
                "ASAN Parts of Speech PDF states Verb is discussed separately; "
                "fill later from Grammer.pdf / Verbs chapter."
            )
            save_json(NOTES_PATH, notes)
            print("Verb: no pages in ASAN POS PDF — marked notes_gap.")
            return 0
        raise SystemExit(f"Unknown topic_id: {topic_id}")

    if not os.path.exists(PDF_PATH):
        raise SystemExit(f"Missing PDF: {PDF_PATH}")

    start_1, end_1 = TOPIC_PAGES[topic_id]
    topic_name = TOPIC_NAMES.get(topic_id, topic_id)
    print(f"\n=== {topic_id} ({topic_name}) PDF pages {start_1}-{end_1} ===")

    doc = fitz.open(PDF_PATH)
    rendered = []
    for page_1 in range(start_1, end_1 + 1):
        print(f"  Render page {page_1}...")
        rendered.append((page_1, render_page_jpg_b64(doc, page_1 - 1)))
    doc.close()

    all_rules, all_examples, all_ex = [], [], []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = {
            ex.submit(call_gemini_page, topic_name, page_1, img_b64, api_key): page_1
            for page_1, img_b64 in rendered
        }
        for fut in as_completed(futs):
            page_1 = futs[fut]
            try:
                data = fut.result() or {}
            except Exception as e:
                print(f"  P{page_1} failed: {e}")
                data = {}
            rules = data.get("rules") or []
            examples = data.get("examples") or []
            exercises = data.get("worked_exercises") or []
            print(
                f"  P{page_1}: {len(rules)} rules, {len(examples)} examples, "
                f"{len(exercises)} worked"
            )
            all_rules.extend(rules)
            all_examples.extend(examples)
            all_ex.extend(exercises)

    rules = dedupe_rules(all_rules)
    examples = dedupe_examples(all_examples)
    exercises = dedupe_exercises(all_ex)

    notes = load_json(NOTES_PATH, empty_notes_shell())
    if topic_id == "mixed_pos":
        block = notes.setdefault("mixed_pos", {})
        block["name_en"] = topic_name
        block["rules"] = rules
        block["examples"] = examples
        block["worked_exercises"] = exercises
        block["sources"] = {"asan_pdf_pages": [start_1, end_1]}
        block["status"] = "asan_extracted" if (rules or examples or exercises) else "empty"
        block["extract_meta"] = {
            "pdf": "asan parts of speech (1).pdf",
            "pages": [start_1, end_1],
            "rules": len(rules),
            "examples": len(examples),
            "worked_exercises": len(exercises),
            "model": MODEL,
        }
    else:
        if "topics" not in notes:
            notes["topics"] = {}
        if topic_id not in notes["topics"]:
            notes["topics"][topic_id] = {
                "name_en": topic_name,
                "rules": [],
                "examples": [],
                "worked_exercises": [],
                "pyq_samples": [],
                "sources": {},
                "status": "empty",
            }
        block = notes["topics"][topic_id]
        # Preserve any existing pyq_samples
        pyq = block.get("pyq_samples") or []
        block["name_en"] = topic_name
        block["rules"] = rules
        block["examples"] = examples
        block["worked_exercises"] = exercises
        block["pyq_samples"] = pyq
        block.setdefault("sources", {})["asan_pdf_pages"] = [start_1, end_1]
        if rules or examples or exercises:
            block["status"] = "asan_extracted" if not pyq else "asan_and_pyq"
        else:
            block["status"] = "empty"
        block["extract_meta"] = {
            "pdf": "asan parts of speech (1).pdf",
            "pages": [start_1, end_1],
            "rules": len(rules),
            "examples": len(examples),
            "worked_exercises": len(exercises),
            "model": MODEL,
        }

    notes["model"] = MODEL
    notes["primary_notes"] = "asan"
    save_json(NOTES_PATH, notes)
    print(
        f"Saved {topic_id}: {len(rules)} rules, {len(examples)} examples, "
        f"{len(exercises)} worked → {NOTES_PATH}"
    )
    return len(rules) + len(examples) + len(exercises)


def update_source_map():
    smap = load_json(
        SOURCE_MAP_PATH,
        {
            "menu": "parts_of_speech",
            "files": {},
            "pyq_sections": {},
        },
    )
    smap["asan_topics"] = {
        tid: {"pdf_pages": list(pages), "name_en": TOPIC_NAMES[tid]}
        for tid, pages in TOPIC_PAGES.items()
    }
    smap["asan_topics"]["verb"] = {
        "pdf_pages": None,
        "name_en": "Verb",
        "note": "Not in ASAN Parts of Speech chapter — discussed separately.",
    }
    smap["files"] = smap.get("files") or {}
    smap["files"]["asan"] = {
        "path": "Data/General-English/asan parts of speech (1).pdf",
        "pages": 45,
        "role": "primary_notes",
    }
    save_json(SOURCE_MAP_PATH, smap)


def main():
    parser = argparse.ArgumentParser(description="Extract ASAN Parts of Speech notes")
    parser.add_argument("--topic", help="topic id, e.g. noun")
    parser.add_argument("--all", action="store_true", help="Extract all mapped topics")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    if args.list:
        for tid, pages in TOPIC_PAGES.items():
            print(f"{tid}: PDF pages {pages[0]}-{pages[1]}")
        print("verb: NO PAGES in this PDF")
        return

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY not found.")

    update_source_map()

    if args.all:
        # Menu order preference, but extract in PDF order for cache warmth
        topics = [
            "noun",
            "adjective",
            "adverb",
            "mixed_pos",
            "preposition",
            "pronoun",
            "conjunction",
            "interjection",
            "verb",  # marks gap only
        ]
    elif args.topic:
        topics = [args.topic]
    else:
        raise SystemExit("Pass --topic <id> or --all")

    # Ensure shell exists
    if not os.path.exists(NOTES_PATH):
        save_json(NOTES_PATH, empty_notes_shell())

    total = 0
    for tid in topics:
        total += extract_topic(tid, api_key)
    print(f"\nDone. Total extracted items this run: {total}")


if __name__ == "__main__":
    main()
