#!/usr/bin/env python3
"""
Extract Unit 5 வாசித்தல் PYQ for Topic 1 (pathiyil_vinaigal) and output as practice questions for Batch 1.

This is intentionally "PYQ style" (stem + options) as requested.

Source PDF:
  Data/Tamil/ilakanam/Tamil Part A illakanam previous.pdf  (TNPSC previous year questions book)

Output JSON (practice type) suitable for:
  backend/import_vasiththal_questions.py (with env INPUT_DB_PATH)

Usage:
  python3 Tamil/extract_vasiththal_pyq_topic1_batch1.py --start 281 --end 282
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

import fitz

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_PATH = os.path.join(
    BASE_DIR, "Data", "Tamil", "ilakanam", "Tamil Part A illakanam previous.pdf"
)

OUT_PATH_DEFAULT = os.path.join(BASE_DIR, "Tamil", "vasiththal_topic1_pyq_batch1.json")

MODELS = ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-2.5-flash-lite"]


def render_page_png_b64(doc: fitz.Document, page_1_based: int) -> str:
    page = doc[page_1_based - 1]
    pix = page.get_pixmap(dpi=220)
    return base64.b64encode(pix.tobytes("png")).decode("utf-8")


def call_gemini_extract(api_key: str, model: str, page_no: int, img_b64: str) -> list:
    prompt = f"""
Extract ALL TNPSC General Tamil MCQs on this page (page_no={page_no}) for Unit 5 Topic 1:
"கொடுக்கப்பட்ட பத்தியிலிருந்து கேட்கப்பட்ட வினாக்களுக்கு சரியான விடையைத் தேர்ந்தெடுத்தல்".

Rules:
- Return ONLY a JSON array.
- Each MCQ object must be:
  {{
    "question_ta": "<Tamil question stem as in paper>",
    "options_ta": ["<A option>", "<B option>", "<C option>", "<D option>"],
    "correct_option_letter": "A"|"B"|"C"|"D"
  }}
- Do not include extra keys.
- If multiple questions exist on the page, return multiple objects.
"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {"inlineData": {"mimeType": "image/png", "data": img_b64}},
                ]
            }
        ],
        "generationConfig": {"responseMimeType": "application/json"},
    }

    retries = 4
    delay = 6
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=160) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                raw = res["candidates"][0]["content"]["parts"][0]["text"].strip()
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[1]
                    if raw.endswith("```"):
                        raw = raw.rsplit("\n", 1)[0]
                # Sometimes Gemini wraps, but we demanded JSON array.
                start = raw.find("[")
                end = raw.rfind("]")
                if start != -1 and end != -1:
                    raw = raw[start : end + 1]
                data = json.loads(raw)
                if isinstance(data, list):
                    return data
                return []
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            if e.code in (429, 503):
                time.sleep(delay)
                delay = min(delay * 2, 45)
                continue
            # non-retryable
            print(f"Page {page_no} {model} HTTP {e.code}: {body[:120]}")
            return []
        except Exception as e:
            print(f"Page {page_no} {model} err: {e}")
            time.sleep(3)
    return []


def normalize_letter(letter: str) -> str:
    l = (letter or "").strip().upper()
    if l in ("A", "B", "C", "D"):
        return l
    return ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, required=True, help="start page number in PDF (1-based)")
    parser.add_argument("--end", type=int, required=True, help="end page number in PDF (1-based)")
    parser.add_argument("--out", default=OUT_PATH_DEFAULT, help="output json path")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY not found in env.")

    if not os.path.exists(PDF_PATH):
        raise SystemExit(f"PDF not found: {PDF_PATH}")

    doc = fitz.open(PDF_PATH)
    if args.start < 1 or args.end > doc.page_count:
        raise SystemExit(f"Page range out of bounds: pdf has {doc.page_count} pages")

    all_questions = []
    seen_stems = set()

    for page_no in range(args.start, args.end + 1):
        img_b64 = render_page_png_b64(doc, page_no)
        extracted = []
        for model in MODELS:
            extracted = call_gemini_extract(api_key, model, page_no, img_b64)
            if extracted:
                break
        print(f"Extracted from page {page_no}: {len(extracted)} MCQs")

        for mcq in extracted:
            qta = (mcq.get("question_ta") or "").strip()
            opts = mcq.get("options_ta") or []
            letter = normalize_letter(mcq.get("correct_option_letter"))
            if not qta or not isinstance(opts, list) or len(opts) != 4 or not letter:
                continue

            # avoid duplicates
            stem_key = re.sub(r"\s+", "", qta).lower()
            if stem_key in seen_stems:
                continue
            seen_stems.add(stem_key)

            options = [
                {"key": "A", "text_en": opts[0], "text_ta": opts[0]},
                {"key": "B", "text_en": opts[1], "text_ta": opts[1]},
                {"key": "C", "text_en": opts[2], "text_ta": opts[2]},
                {"key": "D", "text_en": opts[3], "text_ta": opts[3]},
                {"key": "E", "text_en": "Answer not known", "text_ta": "விடை தெரியவில்லை"},
            ]

            all_questions.append(
                {
                    "subject": "Tamil",
                    "unit": "Vasiththal",
                    "topic": "கொடுக்கப்பட்ட பத்தியிலிருந்து கேட்கப்பட்ட வினாக்களுக்கு சரியான விடையைத் தேர்ந்தெடுத்தல்",
                    "topic_id": "pathiyil_vinaigal",
                    "source_exam": "PYQ Batch 1",
                    "difficulty": "Medium",
                    "question_en": "",
                    "question_ta": qta,
                    "options": options,
                    "correct_option": letter,
                    "explanation_en": "",
                    "explanation_ta": "",
                    "type": "practice",
                    "batch": "Batch 1",
                    "group": "Practice",
                    "source_note": "PYQ extracted",
                    "source_fact": "",
                }
            )

    doc.close()
    if not all_questions:
        print("No questions extracted. Aborting.")
        sys.exit(1)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(all_questions, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"\nWrote {len(all_questions)} extracted PYQ practice questions → {args.out}")


if __name__ == "__main__":
    main()

