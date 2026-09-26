#!/usr/bin/env python3
"""
Extract Poem PYQs from tall topicwise scan PDFs and store per poem.

Sources:
  Data/General-English/Unit-7/Poem PYQ Topicwise (1-10) (1).pdf
  Data/General-English/Unit-7/Poem PYQ Topicwise (11-25) (1).pdf

Output:
  English/Poems/pyq/<poem_id>.json
  English/Poems/poem_pyq_all.json
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
from pathlib import Path

import fitz

BASE_DIR = Path(__file__).resolve().parents[2]
UNIT7 = BASE_DIR / "Data" / "General-English" / "Unit-7"
OUT_DIR = BASE_DIR / "English" / "Poems"
PYQ_DIR = OUT_DIR / "pyq"
CACHE_DIR = OUT_DIR / "_tmp_pyq_extract_cache"
INDEX_PATH = OUT_DIR / "poems_index.json"

MODEL = "gemini-3.1-flash-lite"
BAND_H = 1800
OVERLAP = 200

PYQ_FILES = [
    UNIT7 / "Poem PYQ Topicwise (1-10) (1).pdf",
    UNIT7 / "Poem PYQ Topicwise (11-25) (1).pdf",
]

SCHEMA = """
Return ONLY JSON:
{
  "bands_poem_titles": ["title if a poem section header is visible"],
  "questions": [
    {
      "poem_title": "exact poem title this Q belongs to",
      "question_en": "full stem including any quoted lines",
      "options_en": ["A text","B text","C text","D text"],
      "answer_en": "exact correct option text OR letter A/B/C/D if only letter marked",
      "answer_letter": "A|B|C|D|null",
      "has_marked_answer": true/false,
      "figure_of_speech": true/false,
      "source_note": "short"
    }
  ]
}
Extract ALL visible MCQs. If answer is ticked/circled, set answer_letter and answer_en.
If poem title unclear, use nearest section header above the question.
Do NOT invent questions not visible on the image.
"""


def load_json(path, default=None):
    if not Path(path).exists():
        return default if default is not None else {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


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
    return {"bands_poem_titles": [], "questions": []}


def slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (title or "").lower()).strip("_")


def normalize_title(title: str, poem_titles: list[str]) -> str:
    t = re.sub(r"\s+", " ", (title or "").strip())
    if not t:
        return ""
    tl = t.lower().replace("*", "").strip()
    # direct / fuzzy match against index titles
    for pt in poem_titles:
        pl = pt.lower()
        if tl == pl or tl in pl or pl in tl:
            return pt
        # ignore leading The
        if tl.replace("the ", "") == pl.replace("the ", ""):
            return pt
    # common aliases
    aliases = {
        "team work": "Teamwork",
        "stick-together families": "The Stick-Together Families",
        "the stick-together families": "The Stick-Together Families",
        "stick together families": "The Stick-Together Families",
        "making life worth while": "Making Life Worth While",  # may be outside 29
        "from a railway carriage": "From a Railway Carriage",
        "stopping by woods on a snowy evening": "Stopping by Woods on a Snowy Evening",
        "the spider and the fly": "The Spider and The Fly",
        "secret of the machines": "The Secret of the Machines",
        "the secret of the machines": "The Secret of the Machines",
        "on killing a tree": "On Killing a Tree",
        "a poison tree": "A Poison Tree",
        "nature, the gentlest mother": "Nature the Gentlest Mother",
        "nature the gentlest mother": "Nature the Gentlest Mother",
    }
    if tl in aliases:
        mapped = aliases[tl]
        for pt in poem_titles:
            if pt.lower() == mapped.lower():
                return pt
        return mapped
    return t


def extract_band(img_b64: str, api_key: str, label: str) -> dict:
    cache = CACHE_DIR / f"{label}.json"
    if cache.exists():
        return load_json(cache)
    prompt = f"""
Extract TNPSC General English Poem PYQ MCQs from this scanned strip ({label}).
Questions are topicwise by poem. Section headers name the poem.
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
        pix = page.get_pixmap(matrix=fitz.Matrix(1.1, 1.1), clip=clip)
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
    # answer may be "A) text"
    m = re.match(r"^([A-Da-d])[).:\-\s]+(.*)$", ae)
    if m:
        return m.group(1).upper()
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--pdf", choices=["1-10", "11-25", "all"], default="all")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY not set")

    if args.fresh and CACHE_DIR.exists():
        for p in CACHE_DIR.glob("*.json"):
            p.unlink()

    index = load_json(INDEX_PATH)
    poems = index.get("poems") or []
    poem_titles = [p["title"] for p in poems]
    title_to_id = {p["title"]: p["id"] for p in poems}
    # also slug map
    for p in poems:
        title_to_id[p["id"]] = p["id"]

    files = []
    if args.pdf in ("1-10", "all"):
        files.append(("pyq_1_10", PYQ_FILES[0]))
    if args.pdf in ("11-25", "all"):
        files.append(("pyq_11_25", PYQ_FILES[1]))

    all_q = []
    for tag, pdf in files:
        print(f"\n=== {pdf.name} ===")
        bands = slice_pdf_bands(pdf)
        print(f"  bands: {len(bands)}")
        last_poem = ""
        for bi, y0, y1, jpg in bands:
            label = f"{tag}_b{bi:03d}"
            print(f"  {label} y={y0:.0f}-{y1:.0f}...")
            b64 = base64.b64encode(jpg).decode("utf-8")
            data = extract_band(b64, api_key, label)
            qs = data.get("questions") or []
            titles = data.get("bands_poem_titles") or []
            if titles:
                last_poem = normalize_title(titles[0], poem_titles) or last_poem
            print(f"    → Q={len(qs)} titles={titles}")
            for raw in qs:
                if not isinstance(raw, dict):
                    continue
                poem = normalize_title(raw.get("poem_title") or last_poem, poem_titles)
                if not poem:
                    poem = last_poem
                if poem:
                    last_poem = poem
                opts = [str(x).strip() for x in (raw.get("options_en") or []) if str(x).strip()]
                # strip leading A) B)
                clean_opts = []
                for o in opts[:4]:
                    clean_opts.append(re.sub(r"^[A-Da-d][).:\-\s]+", "", o).strip() or o)
                while len(clean_opts) < 4:
                    clean_opts.append("")
                letter = letter_from_answer(clean_opts, raw.get("answer_en"), raw.get("answer_letter"))
                stem = (raw.get("question_en") or "").strip()
                if not stem or len([x for x in clean_opts if x]) < 2:
                    continue
                item = {
                    "poem_title": poem,
                    "poem_id": title_to_id.get(poem) or slug(poem),
                    "question_en": stem,
                    "options_en": clean_opts[:4],
                    "answer_en": (raw.get("answer_en") or "").strip(),
                    "answer_letter": letter,
                    "has_marked_answer": bool(raw.get("has_marked_answer") or letter),
                    "figure_of_speech": bool(raw.get("figure_of_speech")),
                    "source_pdf": pdf.name,
                    "source_band": label,
                    "source_note": (raw.get("source_note") or "").strip(),
                }
                all_q.append(item)
            time.sleep(0.8)

    # dedupe by stem
    seen = set()
    deduped = []
    for q in all_q:
        key = re.sub(r"\s+", " ", q["question_en"].lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(q)

    # group by poem
    by_poem: dict[str, list] = {}
    for q in deduped:
        pid = q.get("poem_id") or "unknown"
        by_poem.setdefault(pid, []).append(q)

    PYQ_DIR.mkdir(parents=True, exist_ok=True)
    for pid, items in by_poem.items():
        title = items[0].get("poem_title") or pid
        out = {
            "poem_id": pid,
            "poem_title": title,
            "count": len(items),
            "questions": items,
        }
        save_json(PYQ_DIR / f"{pid}.json", out)
        print(f"  saved {pid}: {len(items)} PYQ")

    summary = {
        "total_raw": len(all_q),
        "total_deduped": len(deduped),
        "by_poem": {k: len(v) for k, v in sorted(by_poem.items(), key=lambda x: -len(x[1]))},
        "questions": deduped,
    }
    save_json(OUT_DIR / "poem_pyq_all.json", summary)
    print(f"\nTOTAL deduped PYQ: {len(deduped)} across {len(by_poem)} poems")
    print("by_poem:", summary["by_poem"])


if __name__ == "__main__":
    main()
