#!/usr/bin/env python3
"""
Extract TNPSC General English Parts-of-Speech PYQs from the tall
Grammar PYQ Topicwise (11-21).pdf via Gemini OCR.

PDF is a single ultra-tall image page — extract by Y clip ranges.

Writes:
  English/Grammar/parts_of_speech_pyq.json

Usage:
  python3 English/Grammar/extract_parts_of_speech_pyqs.py
  python3 English/Grammar/extract_parts_of_speech_pyqs.py --section topic15
  python3 English/Grammar/extract_parts_of_speech_pyqs.py --section topic16_noun
  python3 English/Grammar/extract_parts_of_speech_pyqs.py --section all
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
    BASE_DIR, "Data", "General-English", "Grammar PYQ Topicwise (11-21).pdf"
)
OUT_PATH = os.path.join(BASE_DIR, "English", "Grammar", "parts_of_speech_pyq.json")
SLICE_DIR = os.path.join(BASE_DIR, "English", "_tmp_pyq_scan", "pos_slices")

MODEL = "gemini-3.1-flash-lite"
MAX_WORKERS = 2

# Y ranges on the single tall page (PDF user space units)
SECTIONS = {
    "topic15": {
        "label": "15. Find out the odd words (Verb, Noun, Adjective, Adverb)",
        "y0": 12821,
        "y1": 14530,
        "default_pos_hint": None,
        "pyq_topic_num": 15,
    },
    # Noun-heavy plurals — feed Noun submenu style samples
    "topic16_noun": {
        "label": "16. Select the correct Plural forms / Singular–Plural (Noun)",
        "y0": 14530,
        "y1": 19659,
        "default_pos_hint": "noun",
        "pyq_topic_num": 16,
    },
}

SLICE_HEIGHT = 850
SLICE_OVERLAP = 180


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def normalize_q(text: str) -> str:
    return re.sub(r"\s+", "", (text or "")).lower()


def make_slices(y0: float, y1: float) -> list[tuple[float, float]]:
    slices = []
    y = y0
    while y < y1:
        end = min(y1, y + SLICE_HEIGHT)
        slices.append((y, end))
        if end >= y1:
            break
        y = end - SLICE_OVERLAP
    return slices


def render_clip_jpg_b64(page, y0: float, y1: float, scale: float = 1.4) -> str:
    clip = fitz.Rect(0, y0, page.rect.width, y1)
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=clip)
    return base64.b64encode(pix.tobytes("jpg")).decode("utf-8")


def call_gemini_slice(section_label, slice_id, y0, y1, img_b64, api_key, default_pos_hint):
    hint_line = (
        f'- If unclear, set pos_subtopic to "{default_pos_hint}".'
        if default_pos_hint
        else "- If unclear which POS, set pos_subtopic to \"\".\n"
             "- Prefer noun|pronoun|adjective|verb|adverb|preposition|conjunction|interjection|mixed."
    )
    prompt = f"""
You are extracting TNPSC General English PREVIOUS YEAR MCQs from a scanned strip.
Section: "{section_label}"
Strip: {slice_id} (Y {int(y0)}–{int(y1)} on tall PYQ PDF page)

Extract EVERY multiple-choice question on this strip. Aim for high recall —
if a question has a stem and at least options A–D, include it.

Rules:
- Keep English text accurate (fix OCR typos only if obvious).
- Include the printed question number inside question_en when visible (e.g. "92. The correct...").
- Options are usually A–E. Option E is often "Answer not known" / "Answer Not known".
- If a handwritten checkmark / tick marks the correct option, set correct_option to that key.
- If correct answer is unclear, set correct_option to "".
- Ignore headers, ads, watermarks, date stamps, and red section titles (not questions).
- Only skip a question if the stem OR most options are cut off / unreadable.
- Do NOT invent questions not visible on the strip.
- Typical density: 2–4 MCQs per strip — do not stop after the first question.
- Tag pos_subtopic when the question targets a part of speech
  (odd-word-by-POS, identify noun/verb/adjective/adverb, plural noun, etc.).
{hint_line}

Return ONLY a JSON array:
[
  {{
    "question_en": "full question stem",
    "options": [
      {{"key": "A", "text_en": "..."}},
      {{"key": "B", "text_en": "..."}}
    ],
    "correct_option": "A",
    "pos_subtopic": "noun",
    "source_exam": "PYQ",
    "source_slice": "{slice_id}",
    "source_y": [{int(y0)}, {int(y1)}]
  }}
]
"""
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {"inlineData": {"mimeType": "image/jpeg", "data": img_b64}},
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
                start_idx = raw_text.find("[")
                if start_idx != -1:
                    count = 0
                    for idx in range(start_idx, len(raw_text)):
                        if raw_text[idx] == "[":
                            count += 1
                        elif raw_text[idx] == "]":
                            count -= 1
                            if count == 0:
                                raw_text = raw_text[start_idx : idx + 1]
                                break
                data = json.loads(raw_text.strip())
                return data if isinstance(data, list) else []
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            if e.code in (429, 503):
                print(f"    {slice_id} HTTP {e.code}; retry in {delay}s...")
                time.sleep(delay)
                delay = min(delay * 2, 60)
            else:
                attempt += 1
                print(f"    {slice_id} [Attempt {attempt}/{retries}] HTTP {e.code}: {body[:180]}")
                time.sleep(5)
        except Exception as e:
            attempt += 1
            print(f"    {slice_id} [Attempt {attempt}/{retries}] Error: {e}")
            time.sleep(5)
    return []


def dedupe_samples(samples: list) -> list:
    seen = set()
    out = []
    valid_pos = {
        "noun",
        "pronoun",
        "adjective",
        "verb",
        "adverb",
        "preposition",
        "conjunction",
        "interjection",
        "mixed",
        "",
    }
    for s in samples:
        q = (s.get("question_en") or "").strip()
        if not q:
            continue
        key = normalize_q(q)
        if key in seen:
            continue
        seen.add(key)
        opts = []
        for o in s.get("options") or []:
            if not isinstance(o, dict):
                continue
            opts.append(
                {
                    "key": str(o.get("key") or "").strip().upper()[:1],
                    "text_en": (o.get("text_en") or o.get("text") or "").strip(),
                }
            )
        pos = str(s.get("pos_subtopic") or "").strip().lower()
        if pos not in valid_pos:
            pos = ""
        out.append(
            {
                "question_en": q,
                "options": opts,
                "correct_option": str(s.get("correct_option") or "").strip().upper()[:1],
                "pos_subtopic": pos,
                "source_exam": s.get("source_exam") or "PYQ",
                "source_slice": s.get("source_slice"),
                "source_y": s.get("source_y"),
                "pyq_topic_num": s.get("pyq_topic_num"),
                "section_id": s.get("section_id"),
            }
        )
    return out


def extract_section(section_id: str, api_key: str) -> list:
    if section_id not in SECTIONS:
        raise SystemExit(f"Unknown section: {section_id}")
    if not os.path.exists(PDF_PATH):
        raise SystemExit(f"Missing PDF: {PDF_PATH}")

    meta = SECTIONS[section_id]
    y0, y1 = meta["y0"], meta["y1"]
    label = meta["label"]
    print(f"\n=== {section_id}: {label} ===")
    print(f"Y range {y0}–{y1}")

    doc = fitz.open(PDF_PATH)
    page = doc[0]
    slices = make_slices(y0, y1)
    os.makedirs(SLICE_DIR, exist_ok=True)

    rendered = []
    for i, (sy0, sy1) in enumerate(slices):
        slice_id = f"{section_id}_s{i:02d}_y{int(sy0)}-{int(sy1)}"
        print(f"  Render {slice_id}...")
        img_b64 = render_clip_jpg_b64(page, sy0, sy1)
        # keep debug slice
        clip = fitz.Rect(0, sy0, page.rect.width, sy1)
        pix = page.get_pixmap(matrix=fitz.Matrix(0.7, 0.7), clip=clip)
        pix.save(os.path.join(SLICE_DIR, f"{slice_id}.jpg"))
        rendered.append((slice_id, sy0, sy1, img_b64))
    doc.close()

    collected = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = {
            ex.submit(
                call_gemini_slice,
                label,
                slice_id,
                sy0,
                sy1,
                img_b64,
                api_key,
                meta["default_pos_hint"],
            ): slice_id
            for slice_id, sy0, sy1, img_b64 in rendered
        }
        for fut in as_completed(futs):
            slice_id = futs[fut]
            try:
                qs = fut.result() or []
            except Exception as e:
                print(f"  {slice_id} failed: {e}")
                qs = []
            print(f"  {slice_id}: {len(qs)} questions")
            for q in qs:
                q["section_id"] = section_id
                q["pyq_topic_num"] = meta["pyq_topic_num"]
                if meta["default_pos_hint"] and not (q.get("pos_subtopic") or "").strip():
                    q["pos_subtopic"] = meta["default_pos_hint"]
            collected.extend(qs)

    return dedupe_samples(collected)


def merge_into_out(section_id: str, samples: list):
    data = load_json(
        OUT_PATH,
        {
            "menu": "parts_of_speech",
            "role": "pyq_style_samples_only",
            "note": "Do not copy verbatim into practice question bank.",
            "pdf": "Data/General-English/Grammar PYQ Topicwise (11-21).pdf",
            "model": MODEL,
            "sections": {},
            "by_pos_subtopic": {},
            "samples": [],
        },
    )
    data["sections"][section_id] = {
        "meta": SECTIONS[section_id],
        "count": len(samples),
    }

    # Replace samples for this section; keep other sections
    remaining = [s for s in data.get("samples") or [] if s.get("section_id") != section_id]
    remaining.extend(samples)
    data["samples"] = remaining

    by_pos: dict[str, list] = {}
    for s in remaining:
        pos = s.get("pos_subtopic") or "untagged"
        by_pos.setdefault(pos, []).append(s.get("question_en", "")[:80])
    data["by_pos_subtopic"] = {k: len(v) for k, v in sorted(by_pos.items())}
    data["total"] = len(remaining)
    data["model"] = MODEL
    save_json(OUT_PATH, data)
    print(f"Saved section {section_id}: {len(samples)} → total {data['total']} in {OUT_PATH}")
    print("By pos_subtopic:", data["by_pos_subtopic"])


def main():
    parser = argparse.ArgumentParser(description="Extract Parts of Speech PYQs")
    parser.add_argument(
        "--section",
        default="all",
        choices=["topic15", "topic16_noun", "all"],
        help="Which Y-range section to extract",
    )
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY not found.")

    sections = ["topic15", "topic16_noun"] if args.section == "all" else [args.section]
    for sid in sections:
        samples = extract_section(sid, api_key)
        merge_into_out(sid, samples)

    print("\nDone.")


if __name__ == "__main__":
    main()
