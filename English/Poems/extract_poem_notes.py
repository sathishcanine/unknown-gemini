#!/usr/bin/env python3
"""
Extract per-poem notes from TNPSC_Poem_Prose.pdf (Unit VII).

Output: English/Poems/notes/<poem_id>.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

import fitz

BASE_DIR = Path(__file__).resolve().parents[2]
PDF = BASE_DIR / "Data" / "General-English" / "Unit-7" / "TNPSC_Poem_Prose.pdf"
OUT_DIR = BASE_DIR / "English" / "Poems" / "notes"
INDEX_PATH = BASE_DIR / "English" / "Poems" / "poems_index.json"
CACHE_DIR = BASE_DIR / "English" / "Poems" / "_tmp_poem_notes_cache"
MODEL = "gemini-3.1-flash-lite"

SCHEMA = """
Return ONLY JSON:
{
  "poem_text_en": "full poem lines if visible (preserve line breaks as \\n)",
  "summary_en": "2-4 sentence summary of theme/message",
  "glossary": [{"word_en":"...","meaning_en":"..."}],
  "figures_of_speech": [{"device_en":"simile|metaphor|alliteration|personification|...","example_en":"quoted line","note_en":"..."}],
  "rules": [{"rule_en":"poet/title/theme/fact useful for MCQ","tag":"poet|title|theme|line_meaning|fos|vocab|other"}],
  "worked_exercises": [{"prompt_en":"...","answer_en":"...","options_en":["A","B","C","D"],"tag":"choose_correct|short_answer|fos|other"}]
}
Extract ONLY this poem's content from the page text. Do NOT invent.
Include textbook MCQs WITH answers when present.
"""


def load_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default if default is not None else {}
    return json.loads(p.read_text(encoding="utf-8"))


def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def call_gemini(prompt: str, api_key: str, label: str = "") -> dict:
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
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
            with urllib.request.urlopen(req, timeout=180) as resp:
                raw = json.loads(resp.read().decode("utf-8"))["candidates"][0]["content"]["parts"][0]["text"].strip()
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
            return json.loads(raw)
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


def extract_poem(poem: dict, doc, api_key: str) -> dict:
    pid = poem["id"]
    cache = CACHE_DIR / f"{pid}.json"
    if cache.exists():
        return load_json(cache)

    start, end = poem.get("pdf_start"), poem.get("pdf_end")
    if not start or not end:
        return {"error": "missing page range"}
    texts = []
    for p in range(start, end + 1):
        if 1 <= p <= doc.page_count:
            texts.append(f"--- PDF p{p} ---\n{(doc[p - 1].get_text() or '').strip()}")
    blob = "\n\n".join(texts)[:16000]
    prompt = f"""
Extract TNPSC Unit VII poem notes for "{poem['title']}" by {poem['author']}.
Pages {start}-{end} of the Poem & Prose PDF.
{SCHEMA}

TEXT:
\"\"\"
{blob}
\"\"\"
"""
    data = call_gemini(prompt, api_key, label=pid)
    out = {
        "poem_id": pid,
        "poem_title": poem["title"],
        "author": poem["author"],
        "num": poem["num"],
        "pdf_pages": [start, end],
        "poem_text_en": data.get("poem_text_en") or "",
        "summary_en": data.get("summary_en") or "",
        "glossary": data.get("glossary") or [],
        "figures_of_speech": data.get("figures_of_speech") or [],
        "rules": data.get("rules") or [],
        "worked_exercises": data.get("worked_exercises") or [],
    }
    save_json(cache, out)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--poem", type=str, help="poem id or num")
    parser.add_argument("--with-pyq-only", action="store_true")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY not set")

    if args.fresh and CACHE_DIR.exists():
        for p in CACHE_DIR.glob("*.json"):
            p.unlink()

    index = load_json(INDEX_PATH)
    poems = index["poems"]
    pyq_dir = BASE_DIR / "English" / "Poems" / "pyq"
    if args.with_pyq_only:
        have = {p.stem for p in pyq_dir.glob("*.json")}
        poems = [p for p in poems if p["id"] in have]

    if args.poem:
        key = args.poem.strip()
        poems = [p for p in poems if p["id"] == key or str(p["num"]) == key]
        if not poems:
            raise SystemExit(f"poem not found: {key}")

    doc = fitz.open(PDF)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for poem in poems:
        print(f"\n=== {poem['num']}. {poem['title']} (pdf {poem['pdf_start']}-{poem['pdf_end']}) ===")
        out = extract_poem(poem, doc, api_key)
        save_json(OUT_DIR / f"{poem['id']}.json", out)
        print(
            f"  text={len(out.get('poem_text_en') or '')}c "
            f"gloss={len(out.get('glossary') or [])} "
            f"fos={len(out.get('figures_of_speech') or [])} "
            f"rules={len(out.get('rules') or [])} "
            f"worked={len(out.get('worked_exercises') or [])}"
        )
        time.sleep(0.8)
    doc.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
