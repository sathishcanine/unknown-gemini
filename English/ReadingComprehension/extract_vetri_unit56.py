#!/usr/bin/env python3
"""
Extract Vetrii Unit V (Reading Comprehension) + Unit VI (Translation) from image PDF.

Output:
  English/ReadingComprehension/vetri_extract/<topic_id>.json
  English/Translation/vetri_extract/<topic_id>.json
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
PDF = BASE / "Data" / "General-English" / "Unit-5,6" / "vetrii english unit 5 and 6.pdf"
RC = BASE / "English" / "ReadingComprehension" / "vetri_extract"
TR = BASE / "English" / "Translation" / "vetri_extract"
CACHE = BASE / "English" / "ReadingComprehension" / "_tmp_vetri_u56_page_cache"
MODELS = ["gemini-3.1-flash-lite", "gemini-2.5-flash", "gemini-3.5-flash-lite"]

TOPICS = [
    {
        "id": "unseen_passages",
        "unit": 5,
        "title": "Unseen Passages",
        "pages": (1, 14),
        "batches": 3,
        "out": RC,
    },
    {
        "id": "strong_weak_questions",
        "unit": 5,
        "title": "Strong & Weak Questions",
        "pages": (15, 32),
        "batches": 3,
        "out": RC,
    },
    {
        "id": "match_the_following",
        "unit": 5,
        "title": "Match the Following",
        "pages": (33, 38),
        "batches": 2,
        "out": RC,
    },
    {
        "id": "sentence_completion",
        "unit": 5,
        "title": "Sentence Completion",
        "pages": (39, 50),
        "batches": 3,
        "out": RC,
    },
    {
        "id": "ascertainment_of_facts",
        "unit": 5,
        "title": "Ascertainment of Facts",
        "pages": (51, 55),
        "batches": 2,
        "out": RC,
    },
    {
        "id": "word_translation",
        "unit": 6,
        "title": "Word Translation",
        "pages": (56, 69),
        "batches": 3,
        "out": TR,
    },
    {
        "id": "sentence_translation",
        "unit": 6,
        "title": "Sentence Translation",
        "pages": (70, 85),
        "batches": 3,
        "out": TR,
    },
    {
        "id": "tense_related_translation",
        "unit": 6,
        "title": "Tense-related Translation",
        "pages": (86, 109),
        "batches": 3,
        "out": TR,
    },
    {
        "id": "tense_voice_related",
        "unit": 6,
        "title": "Tense / Voice-related Tasks",
        "pages": (110, 113),
        "batches": 1,
        "out": TR,
    },
]

SCHEMA = """
Return ONLY JSON:
{
  "rules": [{"rule_en":"fact useful for TNPSC MCQ","tag":"strategy|definition|tense|voice|other"}],
  "glossary": [{"term_en":"...","meaning_en":"...","meaning_ta":"..."}],
  "examples": [{"note_en":"...","tag":"..."}],
  "passages": [{"title":"...","text_en":"2-4 sentence ORIGINAL paraphrase of the passage (do not copy verbatim)"}],
  "translations": [{"en":"...","ta":"...","tag":"word|sentence|tense|voice"}],
  "pyq": [
    {
      "question_en":"stem",
      "options_en":["A","B","C","D"],
      "answer_en":"exact option text or letter",
      "answer_letter":"A|B|C|D|null",
      "has_marked_answer":true/false,
      "passage_ref":"optional short passage id/title"
    }
  ],
  "notes_en":"short paragraph summary of this page"
}
Extract ALL visible MCQs, passages, glossary/translation pairs, and useful notes.
For bilingual tables, put each row into translations (and glossary if single words).
Do NOT invent content not visible on the page.
"""


def load_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default if default is not None else {}
    return json.loads(p.read_text(encoding="utf-8"))


def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def call_gemini(parts, api_key, label="", models=None):
    last = None
    for model in models or MODELS:
        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
            f":generateContent?key={api_key}"
        )
        delay = 8
        for attempt in range(3):
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=180) as resp:
                    body = json.loads(resp.read().decode())
                cands = body.get("candidates") or []
                if not cands:
                    raise RuntimeError(f"no candidates: {body.get('promptFeedback') or list(body)[:5]}")
                finish = cands[0].get("finishReason")
                content = cands[0].get("content") or {}
                parts_out = content.get("parts") or []
                if not parts_out or "text" not in parts_out[0]:
                    raise RuntimeError(f"no text parts finish={finish}")
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
                    print(f"    {label} {model} HTTP {e.code}; retry {delay}s")
                    time.sleep(delay)
                    delay = min(delay * 2, 90)
                    continue
                print(f"    {label} {model} HTTP {e.code}")
                break
            except Exception as e:
                last = e
                msg = str(e)
                print(f"    {label} {model} attempt {attempt+1}: {e}")
                if "RECITATION" in msg or "no text parts" in msg:
                    break  # try next model / paraphrased prompt
                time.sleep(delay)
                delay = min(delay * 2, 60)
    print(f"    {label} FAILED: {last}")
    return {}


def extract_page(doc, page_num: int, api_key: str, topic: str) -> dict:
    cache = CACHE / f"p{page_num:03d}.json"
    if cache.exists():
        return load_json(cache)
    pix = doc[page_num - 1].get_pixmap(matrix=fitz.Matrix(0.95, 0.95))
    b64 = base64.b64encode(pix.tobytes("jpg")).decode()
    prompt = f"""
Extract TNPSC General English study content from Vetrii IAS book page {page_num}.
Topic focus: {topic}
{SCHEMA}
IMPORTANT: Paraphrase passage text in your own words (short summary). Do NOT copy long verbatim newspaper/book passages.
For MCQs, keep stems/options as close as needed for exam practice but shorten long quoted stems.
"""
    data = call_gemini(
        [{"text": prompt}, {"inlineData": {"mimeType": "image/jpeg", "data": b64}}],
        api_key,
        label=f"p{page_num}",
    )
    if not data or (
        not data.get("pyq")
        and not data.get("glossary")
        and not data.get("translations")
        and not data.get("rules")
        and not data.get("notes_en")
    ):
        # Fallback: paraphrased / structure-only extract
        alt = f"""
This page is from a TNPSC exam guide ({topic}). Return ONLY paraphrased study notes + MCQ answer keys.
Do NOT reproduce copyrighted passage text verbatim — summarize each passage in 2-3 original sentences.
Extract MCQ questions with options and answers (paraphrase stems if long).
{SCHEMA}
"""
        data = call_gemini(
            [{"text": alt}, {"inlineData": {"mimeType": "image/jpeg", "data": b64}}],
            api_key,
            label=f"p{page_num}alt",
            models=["gemini-2.5-flash", "gemini-3.5-flash-lite"],
        ) or {}
    data["page"] = page_num
    save_json(cache, data)
    return data


def merge_topic(pages_data: list, meta: dict) -> dict:
    rules, gloss, examples, pyq, notes = [], [], [], [], []
    passages, translations = [], []
    seen_stem = set()
    seen_pass = set()
    seen_tr = set()
    for d in pages_data:
        rules.extend(d.get("rules") or [])
        gloss.extend(d.get("glossary") or [])
        examples.extend(d.get("examples") or [])
        if d.get("notes_en"):
            notes.append(f"p{d.get('page')}: {d['notes_en']}")
        for p in d.get("passages") or []:
            key = ((p.get("text_en") or "")[:120]).strip().lower()
            if key and key not in seen_pass:
                seen_pass.add(key)
                passages.append(p)
        for t in d.get("translations") or []:
            key = f"{(t.get('en') or '').strip().lower()}|{(t.get('ta') or '').strip()}"
            if key != "|" and key not in seen_tr:
                seen_tr.add(key)
                translations.append(t)
        for q in d.get("pyq") or []:
            stem = (q.get("question_en") or "").strip().lower()
            if not stem or stem in seen_stem:
                continue
            seen_stem.add(stem)
            pyq.append(q)
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
        "rules": rules[:100],
        "glossary": gloss_u[:400],
        "examples": examples[:80],
        "passages": passages[:40],
        "translations": translations[:500],
        "pyq": pyq,
        "notes_en": "\n".join(notes)[:10000],
        "source": str(PDF.relative_to(BASE)),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", type=str)
    parser.add_argument("--unit", type=int, choices=[5, 6])
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
    RC.mkdir(parents=True, exist_ok=True)
    TR.mkdir(parents=True, exist_ok=True)
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
                f"pyq={len(d.get('pyq') or [])} pass={len(d.get('passages') or [])} "
                f"tr={len(d.get('translations') or [])}"
            )
            time.sleep(0.4)
        merged = merge_topic(pages_data, meta)
        out_path = Path(meta["out"]) / f"{meta['id']}.json"
        save_json(out_path, merged)
        print(
            f"  → {out_path.name}: rules={len(merged['rules'])} gloss={len(merged['glossary'])} "
            f"pyq={len(merged['pyq'])} passages={len(merged['passages'])} "
            f"tr={len(merged['translations'])}"
        )
    doc.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
