#!/usr/bin/env python3
"""
Extract SM fact notes for Unit 7 — தமிழின் தொன்மை, சிறப்பு, திராவிட மொழிகள்.

SM pages: 423-495 (printed) → PDF pages 429-501 (offset +6)

Sub-topics:
  3.1 தமிழின் தொன்மை  (p423-456)
  3.2 தமிழின் சிறப்பு  (p457-487)
  3.3 திராவிட மொழிகள்  (p488-495)

Usage:
  python3 Tamil/extract_thonmai_sm_notes.py
  python3 Tamil/extract_thonmai_sm_notes.py --rounds 3
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
from io import BytesIO

import fitz
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_PATH = os.path.join(BASE_DIR, "Data", "Tamil", "ilakanam", "SM TAMIL FULL BOOK 570 PAGES.pdf")
OUT_PATH = os.path.join(BASE_DIR, "Tamil", "unit7_thonmai_notes_temp.json")
PDF_OFFSET = 6

SUBTOPICS = [
    {"id": "thonmai", "name_ta": "தமிழின் தொன்மை", "print_start": 423, "print_end": 456},
    {"id": "sirappu", "name_ta": "தமிழின் சிறப்பு", "print_start": 457, "print_end": 487},
    {"id": "dravidian", "name_ta": "திராவிட மொழிகள்", "print_start": 488, "print_end": 495},
]

MODELS = ["gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-3.5-flash"]


def load_json(path, default=None):
    if not os.path.exists(path):
        return default if default is not None else {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def get_api_key() -> str:
    k = os.environ.get("GEMINI_API_KEY") or ""
    if k:
        return k
    zshrc = os.path.expanduser("~/.zshrc")
    if os.path.exists(zshrc):
        text = open(zshrc, encoding="utf-8", errors="replace").read()
        for line in text.splitlines():
            if "GEMINI_API_KEY" in line and not line.strip().startswith("#"):
                m = re.search(r'GEMINI_API_KEY[= ]+["\']?([A-Za-z0-9_\-]+)', line)
                if m:
                    return m.group(1)
    raise SystemExit("GEMINI_API_KEY missing")


def call_gemini(api_key: str, prompt: str, img_b64: str | None = None) -> str:
    last = None
    for m in MODELS:
        delay = 6
        for _ in range(4):
            try:
                parts = [{"text": prompt}]
                if img_b64:
                    parts.append({"inlineData": {"mimeType": "image/jpeg", "data": img_b64}})
                payload = {
                    "contents": [{"parts": parts}],
                    "generationConfig": {"responseMimeType": "application/json", "temperature": 0.15},
                }
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
                req = urllib.request.Request(
                    url, data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}, method="POST",
                )
                with urllib.request.urlopen(req, timeout=180) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except urllib.error.HTTPError as e:
                last = e
                if e.code in (429, 503):
                    print(f"    {m} HTTP {e.code}; sleep {delay}s", flush=True)
                    time.sleep(delay)
                    delay = min(delay * 2, 60)
                    continue
                break
            except Exception as e:
                last = e
                time.sleep(delay)
                delay = min(delay * 2, 60)
    raise RuntimeError(str(last))


def parse_json(raw: str):
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("\n", 1)[0]
    try:
        return json.loads(text)
    except Exception:
        pass
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        if start < 0:
            continue
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except Exception:
                        break
    raise ValueError("parse fail")


def render_page(doc, pdf_page: int) -> str:
    page = doc[pdf_page]
    pix = page.get_pixmap(dpi=200)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    if img.width > 1400:
        ratio = 1400 / img.width
        img = img.resize((1400, int(img.height * ratio)), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def extract_page(api_key: str, img_b64: str, printed_page: int, subtopic_name: str, round_no: int) -> dict:
    round_hint = ""
    if round_no > 1:
        round_hint = f"\nThis is extraction round {round_no}. Find NEW facts you may have missed in earlier rounds. Be more thorough."

    prompt = f"""You are a Tamil TNPSC study-material fact extractor. This is printed page {printed_page} from SM Tamil book.
Sub-topic: {subtopic_name}
{round_hint}

Extract ALL factual information from this page as structured data. Focus on:
- Historical facts (dates, periods, events)
- Names of scholars, poets, their works, their contributions
- Language facts (origins, classifications, families)
- Geographic/trade facts
- Quotes from scholars about Tamil
- Statistics (number of countries, speakers, etc.)
- Any comparison between languages

Return JSON:
{{
  "page": {printed_page},
  "facts": [
    {{"fact_ta": "Tamil fact text", "category": "history|scholar|language|trade|geography|quote|statistic"}}
  ],
  "quotes": [
    {{"text_ta": "exact quote in Tamil", "speaker": "who said it"}}
  ]
}}

Extract EVERY detail — even small ones. TNPSC asks very specific factual questions."""
    raw = call_gemini(api_key, prompt, img_b64)
    return parse_json(raw)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=2)
    args = parser.parse_args()

    api_key = get_api_key()
    doc = fitz.open(PDF_PATH)
    notes = load_json(OUT_PATH, {"subtopics": {}})

    for st in SUBTOPICS:
        sid = st["id"]
        name = st["name_ta"]
        p_start, p_end = st["print_start"], st["print_end"]

        if sid not in notes["subtopics"]:
            notes["subtopics"][sid] = {
                "name_ta": name,
                "print_range": f"{p_start}-{p_end}",
                "facts": [],
                "quotes": [],
            }

        existing_facts = {f.get("fact_ta", "") for f in notes["subtopics"][sid]["facts"]}
        existing_quotes = {q.get("text_ta", "") for q in notes["subtopics"][sid]["quotes"]}

        for rnd in range(1, args.rounds + 1):
            print(f"\n=== {name} | Round {rnd}/{args.rounds} (pages {p_start}-{p_end}) ===", flush=True)
            new_facts = 0
            new_quotes = 0

            for printed in range(p_start, p_end + 1):
                pdf_page = printed + PDF_OFFSET
                if pdf_page >= len(doc):
                    print(f"  p{printed} (pdf{pdf_page}) — out of range, skip", flush=True)
                    continue

                print(f"  p{printed} (pdf{pdf_page})...", end=" ", flush=True)
                try:
                    img_b64 = render_page(doc, pdf_page)
                    result = extract_page(api_key, img_b64, printed, name, rnd)

                    for f in result.get("facts", []):
                        ft = (f.get("fact_ta") or "").strip()
                        if ft and ft not in existing_facts:
                            notes["subtopics"][sid]["facts"].append(f)
                            existing_facts.add(ft)
                            new_facts += 1

                    for q in result.get("quotes", []):
                        qt = (q.get("text_ta") or "").strip()
                        if qt and qt not in existing_quotes:
                            notes["subtopics"][sid]["quotes"].append(q)
                            existing_quotes.add(qt)
                            new_quotes += 1

                    print(f"+{new_facts}f +{new_quotes}q", flush=True)
                except Exception as e:
                    print(f"FAIL: {e}", flush=True)

                time.sleep(1)

            save_json(OUT_PATH, notes)
            total_f = len(notes["subtopics"][sid]["facts"])
            total_q = len(notes["subtopics"][sid]["quotes"])
            print(f"  Round {rnd} done: +{new_facts}f +{new_quotes}q | Total: {total_f}f {total_q}q", flush=True)

    doc.close()

    print(f"\n{'='*50}")
    print("EXTRACTION COMPLETE")
    for sid, data in notes["subtopics"].items():
        print(f"  {data['name_ta']}: {len(data['facts'])} facts, {len(data['quotes'])} quotes")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
