#!/usr/bin/env python3
"""
Extract TNPSC Aptitude & Reasoning PYQs from Data/Aptitude-reasoning/*.pdf

- Extract ONLY (no generation)
- Bilingual EN+TA
- type=pyq, tags=["pyq"]
- Reasoning figures cropped → Aptitude/media/reasoning/
- Menus/topics: Aptitude | Reasoning With Picture
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import fitz

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from gemini_keys import gemini_keys, primary_key  # noqa: E402
DATA = BASE / "Data" / "Aptitude-reasoning"
OUT = BASE / "Aptitude"
MEDIA = OUT / "media" / "reasoning"
CACHE = OUT / "_tmp_extract_cache"
MODELS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-2.5-flash"]

SOURCES = [
    {
        "id": "part1",
        "pdf": DATA / "Aptitude & Mental Ability Part-1 Final.pdf",
        "label": "Part-1 Topic-wise PYQ (2020-2024)",
    },
    {
        "id": "part2",
        "pdf": DATA / "Aptitude & Mental Ability Part-2 Final.pdf",
        "label": "Part-2 Topic-wise PYQ (2020-2024)",
    },
    {
        "id": "y2020",
        "pdf": DATA / "2020 TNPSC EXAMS - APTITUDE SUMS (1).pdf",
        "label": "2020 TNPSC Aptitude Sums",
    },
    {
        "id": "y2021",
        "pdf": DATA / "2021 TNPSC EXAMS - APTITUDE SUMS (1).pdf",
        "label": "2021 TNPSC Aptitude Sums",
    },
    {
        "id": "y2022",
        "pdf": DATA / "2022 TNPSC EXAMS - APTITUDE SUMS (1).pdf",
        "label": "2022 TNPSC Aptitude Sums",
    },
    {
        "id": "y2023",
        "pdf": DATA / "2023 EXAM - APTITUDE SUMS (1).pdf",
        "label": "2023 Exam Aptitude Sums",
    },
    {
        "id": "y2024",
        "pdf": DATA / "2024 EXAM - APTITUDE SUMS (1).pdf",
        "label": "2024 Exam Aptitude Sums",
    },
    {
        "id": "y2025",
        "pdf": DATA / "2025 EXAM - APTITUDE SUMS (1).pdf",
        "label": "2025 Exam Aptitude Sums",
    },
]

SCHEMA = """
Return ONLY JSON:
{
  "page_kind": "aptitude|reasoning_picture|toc|answer_key|other",
  "topic_hint": "short topic if visible",
  "questions": [
    {
      "q_num": 1,
      "question_en": "English stem (translate if page is Tamil-only)",
      "question_ta": "Tamil stem (translate if page is English-only)",
      "options": [
        {"key":"A","text_en":"...","text_ta":"..."},
        {"key":"B","text_en":"...","text_ta":"..."},
        {"key":"C","text_en":"...","text_ta":"..."},
        {"key":"D","text_en":"...","text_ta":"..."}
      ],
      "correct_option": "A|B|C|D|null",
      "has_marked_answer": true/false,
      "needs_figure": true/false,
      "figure_bbox": [x0,y0,x1,y1] or null,
      "source_exam": "exam name/year if visible else null",
      "explanation_en": "short if given else empty",
      "explanation_ta": "short if given else empty"
    }
  ]
}
Rules:
- Extract ALL MCQs on the page. Do NOT invent questions.
- Always fill BOTH question_en and question_ta (translate faithfully if one language missing).
- Options: exactly A-D when present; include E only if printed.
- needs_figure=true when solving requires a diagram/dice/figure on the page.
- figure_bbox: normalized 0-1000 coords of the main figure for THAT question (page space). Null if no figure or shared page figure unknown.
- page_kind=reasoning_picture when figures are essential (dice, series, mirror, folding, embedded diagram MCQs).
- page_kind=aptitude for number/ratio/interest/time-work etc. without required picture.
"""


def load_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default if default is not None else {}
    return json.loads(p.read_text(encoding="utf-8"))


def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def call_gemini(parts, api_key=None, label=""):
    """Try models × keys. Default key first; on 429/503 rotate to next key."""
    keys = []
    if api_key:
        keys.append(api_key)
    for k in gemini_keys():
        if k not in keys:
            keys.append(k)
    last = None
    for ki, key in enumerate(keys):
        key_tag = f"k{ki+1}/{len(keys)}"
        for model in MODELS:
            delay = 6
            for attempt in range(3):
                try:
                    payload = {
                        "contents": [{"parts": parts}],
                        "generationConfig": {
                            "responseMimeType": "application/json",
                            "temperature": 0,
                        },
                    }
                    url = (
                        f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
                        f":generateContent?key={key}"
                    )
                    req = urllib.request.Request(
                        url,
                        data=json.dumps(payload).encode(),
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    with urllib.request.urlopen(req, timeout=200) as resp:
                        body = json.loads(resp.read().decode())
                    cands = body.get("candidates") or []
                    if not cands:
                        raise RuntimeError(f"no candidates {body.get('promptFeedback')}")
                    finish = cands[0].get("finishReason")
                    parts_out = (cands[0].get("content") or {}).get("parts") or []
                    if not parts_out or "text" not in parts_out[0]:
                        raise RuntimeError(f"no text finish={finish}")
                    raw = parts_out[0]["text"].strip()
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
                    last = e
                    if e.code in (429, 503):
                        print(
                            f"    {label} {model} {key_tag} HTTP {e.code}; "
                            f"{'next key' if attempt >= 2 else f'sleep {delay}s'}"
                        )
                        if attempt >= 2:
                            break  # next model / key
                        time.sleep(delay)
                        delay = min(delay * 2, 90)
                        continue
                    print(f"    {label} {model} {key_tag} HTTP {e.code}")
                    break  # non-retryable for this model; try next model/key
                except Exception as e:
                    last = e
                    msg = str(e)
                    print(f"    {label} {model} {key_tag} attempt {attempt+1}: {e}")
                    if "RECITATION" in msg or "no text" in msg:
                        break
                    time.sleep(delay)
                    delay = min(delay * 2, 60)
            else:
                continue
            # if 429 exhausted attempts on this model, try next key sooner
            if isinstance(last, urllib.error.HTTPError) and last.code in (429, 503):
                break
    print(f"    {label} FAILED: {last}")
    return {}


def crop_figure(page, bbox, out_path: Path) -> str | None:
    """bbox normalized 0-1000 → clip and save PNG. Returns relative URL path or None."""
    if not bbox or len(bbox) != 4:
        return None
    try:
        x0, y0, x1, y1 = [float(v) for v in bbox]
    except Exception:
        return None
    if x1 <= x0 or y1 <= y0:
        return None
    r = page.rect
    clip = fitz.Rect(
        r.x0 + (x0 / 1000.0) * r.width,
        r.y0 + (y0 / 1000.0) * r.height,
        r.x0 + (x1 / 1000.0) * r.width,
        r.y0 + (y1 / 1000.0) * r.height,
    )
    # pad slightly
    clip = fitz.Rect(clip.x0 - 4, clip.y0 - 4, clip.x1 + 4, clip.y1 + 4) & r
    if clip.width < 20 or clip.height < 20:
        return None
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=clip)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(out_path))
    # URL served via /media/aptitude/...
    rel = out_path.relative_to(OUT / "media")
    return f"/media/aptitude/{rel.as_posix()}"


def full_page_figure(page, out_path: Path) -> str | None:
    """Fallback: save upper 55% of page as figure region."""
    r = page.rect
    clip = fitz.Rect(r.x0, r.y0, r.x1, r.y0 + r.height * 0.55)
    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), clip=clip)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(out_path))
    rel = out_path.relative_to(OUT / "media")
    return f"/media/aptitude/{rel.as_posix()}"


def normalize_question(raw, meta, page_kind: str, image_url: str | None):
    q_en = (raw.get("question_en") or "").strip()
    q_ta = (raw.get("question_ta") or "").strip()
    if not q_en and not q_ta:
        return None
    if not q_en:
        q_en = q_ta
    if not q_ta:
        q_ta = q_en
    opts_in = raw.get("options") or []
    options = []
    for o in opts_in:
        if not isinstance(o, dict):
            continue
        key = str(o.get("key") or "").strip().upper()[:1]
        te = (o.get("text_en") or "").strip()
        tt = (o.get("text_ta") or te).strip()
        if key in "ABCDE" and (te or tt):
            options.append({"key": key, "text_en": te or tt, "text_ta": tt or te})
    # ensure A-D
    abcd = [o for o in options if o["key"] in "ABCD"]
    if len(abcd) < 2:
        return None
    letter = (raw.get("correct_option") or "").strip().upper()[:1]
    if letter not in "ABCD":
        # PYQ extract: skip unmarked (avoid false keys)
        if not raw.get("has_marked_answer"):
            return None
        return None
    needs_fig = bool(raw.get("needs_figure")) or page_kind == "reasoning_picture"
    topic = "Reasoning With Picture" if needs_fig else "Aptitude"
    images = [image_url] if image_url and needs_fig else []
    source_exam = (raw.get("source_exam") or meta["label"] or "").strip()
    expl = (raw.get("explanation_en") or "").strip()
    expl_ta = (raw.get("explanation_ta") or expl).strip()
    return {
        "subject": "Aptitude",
        "topic": topic,
        "menu": topic,
        "question_en": q_en,
        "question_ta": q_ta,
        "options": options,
        "correct_option": letter,
        "explanation": expl,
        "explanation_ta": expl_ta,
        "difficulty": "Medium",
        "type": "pyq",
        "tags": ["pyq"],
        "batch": meta["id"],
        "group": meta["label"],
        "source_exam": source_exam,
        "source_fact": f"{meta['id']}",
        "image_urls": images,
        "has_marked_answer": bool(raw.get("has_marked_answer") and letter in "ABCD"),
        "source_pdf": meta["id"],
        "page": raw.get("_page"),
    }


def extract_page(doc, page_num: int, meta: dict, api_key: str) -> dict:
    cache = CACHE / meta["id"] / f"p{page_num:03d}.json"
    if cache.exists():
        return load_json(cache)
    page = doc[page_num - 1]
    pix = page.get_pixmap(matrix=fitz.Matrix(1.05, 1.05))
    b64 = base64.b64encode(pix.tobytes("jpg")).decode()
    prompt = f"""
Extract ALL TNPSC Aptitude / Mental Ability MCQs from this page.
Source: {meta['label']} page {page_num}.
{SCHEMA}
"""
    data = call_gemini(
        [{"text": prompt}, {"inlineData": {"mimeType": "image/jpeg", "data": b64}}],
        api_key,
        label=f"{meta['id']}:p{page_num}",
    )
    if not data:
        data = {"page_kind": "other", "questions": []}
    data["page"] = page_num
    data["source_id"] = meta["id"]
    save_json(cache, data)
    return data


def process_source(meta: dict, api_key: str, start: int = 1, end: int = 0):
    pdf = meta["pdf"]
    if not pdf.exists():
        print(f"MISSING {pdf}")
        return [], []
    doc = fitz.open(pdf)
    last = end or doc.page_count
    last = min(last, doc.page_count)
    print(f"\n=== {meta['id']} {pdf.name} pages {start}-{last} / {doc.page_count} ===")
    aptitude, reasoning = [], []
    seen = set()
    for p in range(start, last + 1):
        print(f"  page {p}...")
        raw = extract_page(doc, p, meta, api_key)
        kind = (raw.get("page_kind") or "other").lower()
        if kind in ("toc", "answer_key"):
            print(f"    skip kind={kind}")
            time.sleep(0.2)
            continue
        qs = raw.get("questions") or []
        print(f"    kind={kind} qs={len(qs)}")
        for qi, q in enumerate(qs, 1):
            q["_page"] = p
            needs = bool(q.get("needs_figure")) or kind == "reasoning_picture"
            image_url = None
            if needs:
                fname = f"{meta['id']}_p{p:03d}_q{qi}.png"
                out_img = MEDIA / fname
                image_url = crop_figure(doc[p - 1], q.get("figure_bbox"), out_img)
                if not image_url:
                    image_url = full_page_figure(doc[p - 1], out_img)
            item = normalize_question(q, meta, kind, image_url)
            if not item:
                continue
            # skip unmarked? keep but flag — still useful for practice with caution
            stem = re.sub(r"\s+", " ", item["question_en"].lower())
            if stem in seen:
                continue
            seen.add(stem)
            if item["topic"] == "Reasoning With Picture":
                reasoning.append(item)
            else:
                aptitude.append(item)
        if p % 15 == 0:
            save_json(OUT / f"_tmp_{meta['id']}_aptitude.json", aptitude)
            save_json(OUT / f"_tmp_{meta['id']}_reasoning.json", reasoning)
            print(f"    checkpoint aptitude={len(aptitude)} reasoning={len(reasoning)}")
        time.sleep(1.8)
    doc.close()
    return aptitude, reasoning


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=str, help="part1|part2|y2020|... or all")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=0)
    args = parser.parse_args()
    api = primary_key()
    print(f"Gemini keys available: {len(gemini_keys())} (default first)")

    CACHE.mkdir(parents=True, exist_ok=True)
    MEDIA.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    sources = SOURCES
    if args.source and args.source != "all":
        sources = [s for s in SOURCES if s["id"] == args.source]
        if not sources:
            raise SystemExit(f"unknown source {args.source}")

    all_apt, all_reas = [], []
    # load existing to append across runs
    apt_path = OUT / "aptitude_questions_db.json"
    reas_path = OUT / "reasoning_picture_questions_db.json"
    if apt_path.exists() and args.source and args.source != "all":
        all_apt = load_json(apt_path, [])
    if reas_path.exists() and args.source and args.source != "all":
        all_reas = load_json(reas_path, [])

    for meta in sources:
        a, r = process_source(meta, api, start=args.start, end=args.end)
        all_apt.extend(a)
        all_reas.extend(r)
        # save incrementally
        save_json(apt_path, all_apt)
        save_json(reas_path, all_reas)
        print(f"  running totals aptitude={len(all_apt)} reasoning={len(all_reas)}")

    # dedupe finals
    def dedupe(rows):
        out, seen = [], set()
        for q in rows:
            stem = re.sub(r"\s+", " ", (q.get("question_en") or "").lower())
            if stem in seen:
                continue
            seen.add(stem)
            out.append(q)
        return out

    all_apt = dedupe(all_apt)
    all_reas = dedupe(all_reas)
    save_json(apt_path, all_apt)
    save_json(reas_path, all_reas)
    print(f"\nDONE aptitude={len(all_apt)} reasoning={len(all_reas)}")
    print(f"  → {apt_path}")
    print(f"  → {reas_path}")


if __name__ == "__main__":
    main()
