#!/usr/bin/env python3
"""
Extract Vetrii Unit III + IV notes/MCQs (image PDF) by page ranges.

Output: English/WritingSkills/vetri_extract/<topic_id>.json
        English/TechnicalTerms/vetri_extract/<topic_id>.json
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

import fitz

BASE = Path(__file__).resolve().parents[2]
PDF = BASE / "Data" / "General-English" / "Unit3,4" / "vetrii english unit 3 and unit 4 (1).pdf"
WS = BASE / "English" / "WritingSkills" / "vetri_extract"
TT = BASE / "English" / "TechnicalTerms" / "vetri_extract"
CACHE = BASE / "English" / "WritingSkills" / "_tmp_vetri_page_cache"
MODEL = "gemini-3.1-flash-lite"

# page ranges inclusive (1-indexed), batch_target informs generators later
TOPICS = [
    {
        "id": "letter_writing",
        "unit": 3,
        "title": "Types of Letters (Formal & Informal)",
        "pages": (1, 14),
        "batches": 3,
        "out": WS,
    },
    {
        "id": "jumbled_sentences",
        "unit": 3,
        "title": "Jumbled Sentences",
        "pages": (15, 21),
        "batches": 3,
        "out": WS,
    },
    {
        "id": "making_queries",
        "unit": 3,
        "title": "Making Queries",
        "pages": (22, 24),
        "batches": 1,
        "out": WS,
    },
    {
        "id": "inferences_blanks_substitutions",
        "unit": 3,
        "title": "Inferences, Blanks & Substitutions",
        "pages": (25, 29),
        "batches": 2,
        "out": WS,
    },
    {
        "id": "administrative_terms",
        "unit": 4,
        "title": "Administrative Terms",
        "pages": (30, 55),
        "batches": 3,
        "out": TT,
    },
    {
        "id": "department_related_terms",
        "unit": 4,
        "title": "Department-related Terms",
        "pages": (56, 70),
        "batches": 2,
        "out": TT,
    },
    {
        "id": "general_official_terms",
        "unit": 4,
        "title": "General & Official Terms",
        "pages": (71, 84),
        "batches": 2,
        "out": TT,
    },
    {
        "id": "official_correspondence",
        "unit": 4,
        "title": "Basics of Official Correspondence",
        "pages": (85, 105),
        "batches": 3,
        "out": TT,
    },
]

SCHEMA = """
Return ONLY JSON:
{
  "rules": [{"rule_en":"fact useful for TNPSC MCQ","tag":"format|type|vocab|definition|other"}],
  "glossary": [{"term_en":"...","meaning_en":"..."}],
  "examples": [{"note_en":"...","tag":"..."}],
  "pyq": [
    {
      "question_en":"stem",
      "options_en":["A","B","C","D"],
      "answer_en":"exact option text or letter",
      "answer_letter":"A|B|C|D|null",
      "has_marked_answer":true/false
    }
  ],
  "notes_en":"short paragraph summary of this page"
}
Extract ALL visible MCQs and useful notes/definitions. Do NOT invent.
"""


def load_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default if default is not None else {}
    return json.loads(p.read_text(encoding="utf-8"))


def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def call_gemini(parts, api_key, label=""):
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
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                raw = json.loads(resp.read().decode())["candidates"][0]["content"]["parts"][0][
                    "text"
                ].strip()
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
            return data if isinstance(data, dict) else {}
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
    return {}


def extract_page(doc, page_num: int, api_key: str, topic: str) -> dict:
    cache = CACHE / f"p{page_num:03d}.json"
    if cache.exists():
        return load_json(cache)
    pix = doc[page_num - 1].get_pixmap(matrix=fitz.Matrix(1.0, 1.0))
    b64 = base64.b64encode(pix.tobytes("jpg")).decode()
    prompt = f"""
Extract TNPSC General English content from Vetrii IAS book page {page_num}.
Topic focus: {topic}
{SCHEMA}
"""
    data = call_gemini(
        [{"text": prompt}, {"inlineData": {"mimeType": "image/jpeg", "data": b64}}],
        api_key,
        label=f"p{page_num}",
    )
    data["page"] = page_num
    save_json(cache, data)
    return data


def merge_topic(pages_data: list, meta: dict) -> dict:
    rules, gloss, examples, pyq, notes = [], [], [], [], []
    seen_stem = set()
    for d in pages_data:
        rules.extend(d.get("rules") or [])
        gloss.extend(d.get("glossary") or [])
        examples.extend(d.get("examples") or [])
        if d.get("notes_en"):
            notes.append(f"p{d.get('page')}: {d['notes_en']}")
        for q in d.get("pyq") or []:
            stem = (q.get("question_en") or "").strip().lower()
            if not stem or stem in seen_stem:
                continue
            seen_stem.add(stem)
            pyq.append(q)
    # dedupe glossary by term
    gseen = set()
    gloss_u = []
    for g in gloss:
        t = (g.get("term_en") or "").strip().lower()
        if not t or t in gseen:
            continue
        gseen.add(t)
        gloss_u.append(g)
    return {
        "topic_id": meta["id"],
        "topic_title": meta["title"],
        "unit": meta["unit"],
        "batches_target": meta["batches"],
        "pages": list(meta["pages"]),
        "rules": rules[:80],
        "glossary": gloss_u[:200],
        "examples": examples[:60],
        "pyq": pyq,
        "notes_en": "\n".join(notes)[:8000],
        "source": str(PDF.relative_to(BASE)),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", type=str, help="topic id or all")
    parser.add_argument("--unit", type=int, choices=[3, 4])
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()

    api = os.environ.get("GEMINI_API_KEY")
    if not api:
        raise SystemExit("GEMINI_API_KEY missing")

    if args.fresh and CACHE.exists():
        for p in CACHE.glob("*.json"):
            p.unlink()

    topics = TOPICS
    if args.unit:
        topics = [t for t in topics if t["unit"] == args.unit]
    if args.topic:
        key = args.topic.strip()
        topics = [t for t in topics if t["id"] == key or t["title"].lower() == key.lower()]
        if not topics:
            raise SystemExit(f"topic not found: {key}")

    CACHE.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(PDF)
    for meta in topics:
        start, end = meta["pages"]
        print(f"\n=== U{meta['unit']} {meta['title']} pages {start}-{end} (batches={meta['batches']}) ===")
        pages_data = []
        for p in range(start, end + 1):
            if p > doc.page_count:
                break
            print(f"  page {p}...")
            d = extract_page(doc, p, api, meta["title"])
            pages_data.append(d)
            print(
                f"    rules={len(d.get('rules') or [])} gloss={len(d.get('glossary') or [])} "
                f"pyq={len(d.get('pyq') or [])}"
            )
            time.sleep(0.5)
        merged = merge_topic(pages_data, meta)
        out_path = Path(meta["out"]) / f"{meta['id']}.json"
        save_json(out_path, merged)
        print(
            f"  → {out_path.name}: rules={len(merged['rules'])} gloss={len(merged['glossary'])} "
            f"pyq={len(merged['pyq'])} notes={len(merged['notes_en'])}c"
        )
    doc.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
