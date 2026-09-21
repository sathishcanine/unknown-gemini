#!/usr/bin/env python3
"""
Extract SM fact notes for Unit 7 — தமிழ்ப்பணி தொடர்பான செய்திகள்.
SM pages: 497-508 (printed) → PDF pages 503-514 (offset +6)

Sub-topics:
  4.1 உ.வே.சாமிநாத ஐயர்  (p497-502)
  4.2 தெ.பொ. மீனாட்சி சுந்தரம்  (p503-503)
  4.3 சி. இலக்குவனார்  (p504-508)

Usage:
  python3 Tamil/extract_tamilpani_sm_notes.py --rounds 2
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
OUT_PATH = os.path.join(BASE_DIR, "Tamil", "unit7_tamilpani_notes_temp.json")
PDF_OFFSET = 6

SUBTOPICS = [
    {"id": "uvesa", "name_ta": "உ.வே.சாமிநாத ஐயர்", "print_start": 497, "print_end": 502},
    {"id": "meenakshi", "name_ta": "தெ.பொ. மீனாட்சி சுந்தரம்", "print_start": 503, "print_end": 503},
    {"id": "ilakkuvanar", "name_ta": "சி. இலக்குவனார்", "print_start": 504, "print_end": 508},
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


def call_gemini(api_key, prompt, img_b64=None):
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
                req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=180) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except urllib.error.HTTPError as e:
                last = e
                if e.code in (429, 503):
                    time.sleep(delay); delay = min(delay * 2, 60); continue
                break
            except Exception as e:
                last = e; time.sleep(delay); delay = min(delay * 2, 60)
    raise RuntimeError(str(last))


def parse_json(raw):
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("\n", 1)[0]
    try:
        return json.loads(text)
    except Exception:
        pass
    for o, c in (("{", "}"), ("[", "]")):
        s = text.find(o)
        if s < 0: continue
        d = 0
        for i, ch in enumerate(text[s:], s):
            if ch == o: d += 1
            elif ch == c:
                d -= 1
                if d == 0:
                    try: return json.loads(text[s:i+1])
                    except: break
    raise ValueError("parse fail")


def render_page(doc, pdf_page):
    page = doc[pdf_page]
    pix = page.get_pixmap(dpi=200)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    if img.width > 1400:
        r = 1400 / img.width
        img = img.resize((1400, int(img.height * r)), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def extract_page(api_key, img_b64, printed, subtopic_name, round_no):
    rh = f"\nRound {round_no}: find NEW facts missed earlier." if round_no > 1 else ""
    prompt = f"""Tamil TNPSC fact extractor. Page {printed}, sub-topic: {subtopic_name}.{rh}

Extract ALL facts about this Tamil scholar:
- Birth/death dates, birthplace, parents, education
- Books authored/edited/published
- Titles/honors received
- Key contributions to Tamil literature
- Institutions founded/associated
- Famous quotes by/about them
- Any dates, statistics, comparisons

Return JSON:
{{"page":{printed},"facts":[{{"fact_ta":"...","category":"biography|works|title|contribution|institution|quote"}}],
"quotes":[{{"text_ta":"exact quote","speaker":"who"}}]}}

Extract EVERY detail — TNPSC asks very specific questions."""
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
        sid, name = st["id"], st["name_ta"]
        p_start, p_end = st["print_start"], st["print_end"]

        if sid not in notes["subtopics"]:
            notes["subtopics"][sid] = {"name_ta": name, "print_range": f"{p_start}-{p_end}", "facts": [], "quotes": []}

        existing_f = {f.get("fact_ta", "") for f in notes["subtopics"][sid]["facts"]}
        existing_q = {q.get("text_ta", "") for q in notes["subtopics"][sid]["quotes"]}

        for rnd in range(1, args.rounds + 1):
            print(f"\n=== {name} | Round {rnd}/{args.rounds} (pages {p_start}-{p_end}) ===", flush=True)
            nf = nq = 0
            for printed in range(p_start, p_end + 1):
                pdf_page = printed + PDF_OFFSET
                if pdf_page >= len(doc):
                    print(f"  p{printed} — out of range", flush=True); continue
                print(f"  p{printed} (pdf{pdf_page})...", end=" ", flush=True)
                try:
                    img = render_page(doc, pdf_page)
                    result = extract_page(api_key, img, printed, name, rnd)
                    for f in result.get("facts", []):
                        ft = (f.get("fact_ta") or "").strip()
                        if ft and ft not in existing_f:
                            notes["subtopics"][sid]["facts"].append(f)
                            existing_f.add(ft); nf += 1
                    for q in result.get("quotes", []):
                        qt = (q.get("text_ta") or "").strip()
                        if qt and qt not in existing_q:
                            notes["subtopics"][sid]["quotes"].append(q)
                            existing_q.add(qt); nq += 1
                    print(f"+{nf}f +{nq}q", flush=True)
                except Exception as e:
                    print(f"FAIL: {e}", flush=True)
                time.sleep(1)
            save_json(OUT_PATH, notes)
            print(f"  Round {rnd}: +{nf}f +{nq}q | Total: {len(notes['subtopics'][sid]['facts'])}f {len(notes['subtopics'][sid]['quotes'])}q", flush=True)

    doc.close()
    print(f"\n{'='*50}\nEXTRACTION COMPLETE")
    for sid, d in notes["subtopics"].items():
        print(f"  {d['name_ta']}: {len(d['facts'])} facts, {len(d['quotes'])} quotes")


if __name__ == "__main__":
    main()
