#!/usr/bin/env python3
"""Extract Prose PYQs from tall topicwise scan PDF (1-14)."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

import fitz

BASE_DIR = Path(__file__).resolve().parents[2]
UNIT7 = BASE_DIR / "Data" / "General-English" / "Unit-7"
OUT_DIR = BASE_DIR / "English" / "Prose"
PYQ_DIR = OUT_DIR / "pyq"
CACHE_DIR = OUT_DIR / "_tmp_pyq_extract_cache"
INDEX_PATH = OUT_DIR / "prose_index.json"
PYQ_PDF = UNIT7 / "Prose PYQ Topicwise (1-14).pdf"
MODEL = "gemini-3.1-flash-lite"
BAND_H = 1800
OVERLAP = 200

SCHEMA = """
Return ONLY JSON:
{
  "band_prose_titles": ["prose/lesson title if a section header is visible"],
  "questions": [
    {
      "prose_title": "exact prose title this Q belongs to",
      "question_en": "full stem including any quoted lines",
      "options_en": ["A text","B text","C text","D text"],
      "answer_en": "exact correct option text OR letter A/B/C/D if only letter marked",
      "answer_letter": "A|B|C|D|null",
      "has_marked_answer": true/false,
      "source_note": "short"
    }
  ]
}
Extract ALL visible MCQs. If answer is ticked/circled, set answer_letter and answer_en.
If prose title unclear, use nearest section header above the question.
Do NOT invent questions not visible on the image.
"""


def load_json(path, default=None):
    if not Path(path).exists():
        return default if default is not None else {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


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
    return {"band_prose_titles": [], "questions": []}


def normalize_title(title: str, titles: list[str]) -> str:
    t = re.sub(r"\s+", " ", (title or "").strip())
    if not t:
        return ""
    tl = t.lower().replace("*", "").strip()
    aliases = {
        "his first flight": "His First Flight",
        "the night the ghost got in": "The Night the Ghost Got In",
        "empowered women navigating the world": "Empowered Women Navigating the World",
        "empowered women": "Empowered Women Navigating the World",
        "the attic": "The Attic",
        "tech bloomers": "Tech Bloomers",
        "the last lesson": "The Last Lesson",
        "the dying detective": "The Dying Detective",
        "dying detective": "The Dying Detective",
        "learning the game": "Learning the Game",
        "i can't climb trees anymore": "I Can't Climb Trees Anymore",
        "i cant climb trees anymore": "I Can't Climb Trees Anymore",
        "old man river": "Old Man River",
        "seventeen oranges": "Seventeen Oranges",
        "water the elixir of life": "Water – The Elixir of Life",
        "water – the elixir of life": "Water – The Elixir of Life",
        "from zero to infinity": "From Zero to Infinity",
        "srinivasa ramanujan": "From Zero to Infinity",
        "a birthday letter": "A Birthday Letter",
        "birthday letter": "A Birthday Letter",
    }
    if tl in aliases:
        mapped = aliases[tl]
        for pt in titles:
            if pt.lower() == mapped.lower():
                return pt
        return mapped
    for pt in titles:
        pl = pt.lower()
        if tl == pl or tl in pl or pl in tl:
            return pt
        if tl.replace("the ", "") == pl.replace("the ", ""):
            return pt
    return t


def extract_band(img_b64: str, api_key: str, label: str) -> dict:
    cache = CACHE_DIR / f"{label}.json"
    if cache.exists():
        return load_json(cache)
    prompt = f"""
Extract TNPSC General English Prose PYQ MCQs from this scanned strip ({label}).
Questions are topicwise by prose lesson. Section headers name the prose/lesson.
{SCHEMA}
"""
    data = call_gemini(
        [{"text": prompt}, {"inlineData": {"mimeType": "image/jpeg", "data": img_b64}}],
        api_key,
        label=label,
    )
    save_json(cache, data)
    return data


def slice_pdf_bands(pdf_path: Path):
    doc = fitz.open(pdf_path)
    page = doc[0]
    h = page.rect.height
    w = page.rect.width
    bands = []
    y = 0
    idx = 0
    while y < h:
        y1 = min(y + BAND_H, h)
        clip = fitz.Rect(0, y, w, y1)
        pix = page.get_pixmap(matrix=fitz.Matrix(1.05, 1.05), clip=clip)
        bands.append((idx, y, y1, pix.tobytes("jpg")))
        if y1 >= h:
            break
        y = y1 - OVERLAP
        idx += 1
    doc.close()
    return bands


def letter_from_answer(options, answer_en, answer_letter):
    if answer_letter and str(answer_letter).strip().upper()[:1] in "ABCD":
        return str(answer_letter).strip().upper()[:1]
    ae = (answer_en or "").strip()
    if not ae:
        return None
    if ae.upper()[:1] in "ABCD" and len(ae) <= 2:
        return ae.upper()[:1]
    for i, opt in enumerate(options):
        if (opt or "").strip() == ae:
            return chr(65 + i)
    ae_l = ae.lower()
    for i, opt in enumerate(options):
        if (opt or "").strip().lower() == ae_l:
            return chr(65 + i)
    m = re.match(r"^([A-Da-d])[).:\-\s]+(.*)$", ae)
    if m:
        return m.group(1).upper()
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY not set")

    if args.fresh and CACHE_DIR.exists():
        for p in CACHE_DIR.glob("*.json"):
            p.unlink()

    index = load_json(INDEX_PATH)
    items = index.get("prose") or []
    # Phase 1 = first 14 (PYQ sheet coverage)
    phase1 = [p for p in items if p.get("num", 0) <= 14]
    titles = [p["title"] for p in phase1]
    title_to_id = {p["title"]: p["id"] for p in phase1}

    print(f"\n=== {PYQ_PDF.name} ===")
    bands = slice_pdf_bands(PYQ_PDF)
    print(f"  bands: {len(bands)}")

    all_q = []
    last_title = ""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    for bi, y0, y1, jpg in bands:
        label = f"prose_pyq_b{bi:03d}"
        print(f"  {label} y={y0:.0f}-{y1:.0f}...")
        b64 = base64.b64encode(jpg).decode("utf-8")
        data = extract_band(b64, api_key, label)
        qs = data.get("questions") or []
        headers = data.get("band_prose_titles") or []
        if headers:
            last_title = normalize_title(headers[0], titles) or last_title
        print(f"    → Q={len(qs)} titles={headers}")
        for raw in qs:
            pt = normalize_title(raw.get("prose_title") or last_title, titles) or last_title
            opts = [str(x).strip() for x in (raw.get("options_en") or []) if str(x).strip()][:4]
            if len(opts) < 2:
                continue
            while len(opts) < 4:
                opts.append("")
            letter = letter_from_answer(opts, raw.get("answer_en"), raw.get("answer_letter"))
            all_q.append(
                {
                    "prose_title": pt,
                    "prose_id": title_to_id.get(pt, ""),
                    "question_en": (raw.get("question_en") or "").strip(),
                    "options_en": opts,
                    "answer_en": (raw.get("answer_en") or "").strip(),
                    "answer_letter": letter,
                    "has_marked_answer": bool(raw.get("has_marked_answer") or letter),
                    "source_note": (raw.get("source_note") or "").strip(),
                    "band": label,
                }
            )
            if pt and not last_title:
                last_title = pt
        time.sleep(0.6)

    # group by prose_id
    PYQ_DIR.mkdir(parents=True, exist_ok=True)
    by_id: dict[str, list] = {}
    unknown = []
    for q in all_q:
        pid = q.get("prose_id") or ""
        if not pid:
            # try rematch
            nt = normalize_title(q.get("prose_title") or "", titles)
            pid = title_to_id.get(nt, "")
            q["prose_title"] = nt or q.get("prose_title")
            q["prose_id"] = pid
        if pid:
            by_id.setdefault(pid, []).append(q)
        else:
            unknown.append(q)

    for pid, qs in by_id.items():
        # dedupe by stem
        seen = set()
        uniq = []
        for q in qs:
            stem = re.sub(r"\s+", " ", (q.get("question_en") or "").lower())
            if not stem or stem in seen:
                continue
            seen.add(stem)
            uniq.append(q)
        title = next((p["title"] for p in phase1 if p["id"] == pid), pid)
        save_json(
            PYQ_DIR / f"{pid}.json",
            {"prose_id": pid, "prose_title": title, "questions": uniq},
        )
        print(f"  saved {pid}: {len(uniq)} Q")

    if unknown:
        save_json(OUT_DIR / "pyq_unknown.json", unknown)
        print(f"  unknown: {len(unknown)}")

    summary = {
        "syllabus_prose_with_pyq": {pid: len(qs) for pid, qs in sorted(by_id.items())},
        "syllabus_total_pyq": sum(len(v) for v in by_id.values()),
        "prose_covered": len(by_id),
        "unresolved_unknown": len(unknown),
    }
    save_json(OUT_DIR / "prose_pyq_summary.json", summary)
    save_json(OUT_DIR / "prose_pyq_all.json", all_q)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
