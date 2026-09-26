#!/usr/bin/env python3
"""Extract per-prose notes from TNPSC_Poem_Prose.pdf (Unit VII Prose)."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

import fitz

BASE_DIR = Path(__file__).resolve().parents[2]
PDF = BASE_DIR / "Data" / "General-English" / "Unit-7" / "TNPSC_Poem_Prose.pdf"
OUT_DIR = BASE_DIR / "English" / "Prose" / "notes"
INDEX_PATH = BASE_DIR / "English" / "Prose" / "prose_index.json"
CACHE_DIR = BASE_DIR / "English" / "Prose" / "_tmp_prose_notes_cache"
MODEL = "gemini-3.1-flash-lite"

SCHEMA = """
Return ONLY JSON:
{
  "prose_text_en": "key excerpts / condensed narrative of the prose (preserve important quotes)",
  "summary_en": "3-5 sentence summary of plot/theme/message",
  "characters": [{"name_en":"...","role_en":"..."}],
  "glossary": [{"word_en":"...","meaning_en":"..."}],
  "rules": [{"rule_en":"author/title/theme/fact useful for MCQ","tag":"author|title|theme|plot|vocab|quote|other"}],
  "worked_exercises": [{"prompt_en":"...","answer_en":"...","options_en":["A","B","C","D"],"tag":"choose_correct|short_answer|other"}]
}
Extract ONLY this prose lesson. Do NOT invent.
Include textbook MCQs WITH answers when present.
Prefer factual TNPSC-testable points: author, characters, incidents, morals, quotes, glossary.
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
                raw = json.loads(resp.read().decode("utf-8"))["candidates"][0]["content"]["parts"][0][
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


def page_blob(doc, start: int, end: int) -> str:
    """Story pages + last exercise pages for long prose."""
    pages = list(range(start, end + 1))
    if len(pages) <= 10:
        chosen = pages
    else:
        # first 6 + last 4
        chosen = pages[:6] + pages[-4:]
    texts = []
    for p in chosen:
        if 1 <= p <= doc.page_count:
            texts.append(f"--- PDF p{p} ---\n{(doc[p - 1].get_text() or '').strip()}")
    blob = "\n\n".join(texts)
    return blob[:18000]


def extract_item(item: dict, doc, api_key: str) -> dict:
    pid = item["id"]
    cache = CACHE_DIR / f"{pid}.json"
    if cache.exists():
        return load_json(cache)

    start, end = item.get("pdf_start"), item.get("pdf_end")
    if not start or not end:
        return {"error": "missing page range"}
    blob = page_blob(doc, start, end)
    author = item.get("author") or "unknown"
    prompt = f"""
Extract TNPSC Unit VII prose notes for "{item['title']}" by {author}.
Pages {start}-{end} of the Poem & Prose PDF (selected story + exercise pages).
{SCHEMA}

TEXT:
\"\"\"
{blob}
\"\"\"
"""
    data = call_gemini(prompt, api_key, label=pid)
    out = {
        "prose_id": pid,
        "prose_title": item["title"],
        "author": item.get("author"),
        "num": item["num"],
        "pdf_pages": [start, end],
        "prose_text_en": data.get("prose_text_en") or "",
        "summary_en": data.get("summary_en") or "",
        "characters": data.get("characters") or [],
        "glossary": data.get("glossary") or [],
        "rules": data.get("rules") or [],
        "worked_exercises": data.get("worked_exercises") or [],
    }
    save_json(cache, out)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--prose", type=str)
    parser.add_argument("--with-pyq-only", action="store_true")
    parser.add_argument("--phase1", action="store_true", help="prose nums 1-14")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY not set")

    if args.fresh and CACHE_DIR.exists():
        for p in CACHE_DIR.glob("*.json"):
            p.unlink()

    index = load_json(INDEX_PATH)
    items = index["prose"]
    if args.phase1 or args.with_pyq_only:
        pyq_dir = BASE_DIR / "English" / "Prose" / "pyq"
        if args.with_pyq_only and pyq_dir.exists() and any(pyq_dir.glob("*.json")):
            have = {p.stem for p in pyq_dir.glob("*.json")}
            items = [p for p in items if p["id"] in have]
        else:
            items = [p for p in items if p.get("num", 0) <= 14]
    if args.prose:
        key = args.prose.strip()
        items = [p for p in items if p["id"] == key or str(p["num"]) == key]

    doc = fitz.open(PDF)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    for item in items:
        print(f"\n=== {item['num']}. {item['title']} (pdf {item['pdf_start']}-{item['pdf_end']}) ===")
        out = extract_item(item, doc, api_key)
        save_json(OUT_DIR / f"{item['id']}.json", out)
        print(
            f"  text={len(out.get('prose_text_en') or '')}c "
            f"chars={len(out.get('characters') or [])} "
            f"gloss={len(out.get('glossary') or [])} "
            f"rules={len(out.get('rules') or [])} "
            f"worked={len(out.get('worked_exercises') or [])}"
        )
        time.sleep(0.8)
    doc.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
