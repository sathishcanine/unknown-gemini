#!/usr/bin/env python3
"""
Extract SM fact notes for Unit 7 அறநூல்கள் (12 books) via Gemini OCR.

Writes Tamil/unit7_aranoolgal_notes_temp.json

Usage:
  python3 Tamil/extract_aranoolgal_sm_notes.py --books nanmanikadikai,pazhamozhi_nanuru
  python3 Tamil/extract_aranoolgal_sm_notes.py --all --rounds 3
  python3 Tamil/extract_aranoolgal_sm_notes.py --list
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import re
import time
import urllib.error
import urllib.request

import fitz
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_PATH = os.path.join(
    BASE_DIR, "Data", "Tamil", "ilakanam", "SM TAMIL FULL BOOK 570 PAGES.pdf"
)
NOTES_PATH = os.path.join(BASE_DIR, "Tamil", "unit7_aranoolgal_notes_temp.json")
MODELS = ["gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-3.5-flash"]
PDF_OFFSET = 6  # printed N -> pdf N+6

# TOC 2.1–2.12 (printed pages). id -> meta
BOOKS = [
    {
        "id": "naladiyar",
        "name_ta": "நாலடியார்",
        "toc_no": "2.1",
        "printed": [398, 399],
    },
    {
        "id": "nanmanikadikai",
        "name_ta": "நான்மணிக்கடிகை",
        "toc_no": "2.2",
        "printed": [400, 401],  # leftover facts spill to top of 401
    },
    {
        "id": "pazhamozhi_nanuru",
        "name_ta": "பழமொழி நானூறு",
        "toc_no": "2.3",
        "printed": [401, 402],
    },
    {
        "id": "inna_narpathu",
        "name_ta": "இன்னா நாற்பது",
        "toc_no": "2.4",
        "printed": [403, 404],  # shares page with இனியவை
    },
    {
        "id": "thirikadugam",
        "name_ta": "திரிகடுகம்",
        "toc_no": "2.5",
        "printed": [404, 405],
    },
    {
        "id": "elathi",
        "name_ta": "ஏலாதி",
        "toc_no": "2.6",
        "printed": [406, 406],
    },
    {
        "id": "sirupanchamoolam",
        "name_ta": "சிறுபஞ்சமூலம்",
        "toc_no": "2.7",
        "printed": [407, 407],
    },
    {
        "id": "mudhumozhikkanchi",
        "name_ta": "முதுமொழிக் காஞ்சி",
        "toc_no": "2.8",
        "printed": [408, 409],
    },
    {
        "id": "avvaiyar",
        "name_ta": "ஔவையார்",
        "toc_no": "2.9",
        "printed": [410, 413],
    },
    {
        "id": "asarakkovai",
        "name_ta": "ஆசாரக்கோவை",
        "toc_no": "2.10",
        "printed": [414, 414],
    },
    {
        "id": "araneri_saram",
        "name_ta": "அறநெறிச்சாரம்",
        "toc_no": "2.11",
        "printed": [415, 415],
    },
    {
        "id": "neethineri_vilakkam",
        "name_ta": "நீதிநெறி விளக்கம்",
        "toc_no": "2.12",
        "printed": [416, 416],
    },
]


def load_json(path, default):
    if not os.path.exists(path):
        return default
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
                m = re.search(r'GEMINI_API_KEY[= ]+["\']?([A-Za-z0-9_\-]+)["\']?', line)
                if m:
                    return m.group(1)
    raise SystemExit("GEMINI_API_KEY missing")


def empty_notes():
    return {
        "subject": "Tamil",
        "unit": "Aranoolgal",
        "unit_order": 7,
        "version": 1,
        "pdf": "SM TAMIL FULL BOOK 570 PAGES.pdf",
        "pdf_offset": PDF_OFFSET,
        "overview": {
            "name_ta": "பதினெண்கீழ்க்கணக்கு / அறநூல்கள் அறிமுகம்",
            "printed_pages": [397],
            "facts": [],
        },
        "books": {
            b["id"]: {
                "id": b["id"],
                "toc_no": b["toc_no"],
                "name_ta": b["name_ta"],
                "printed_pages": b["printed"],
                "status": "pending",
                "facts": [],
                "quotes": [],
                "sample_poems": [],
                "vocab": [],
                "source_pages": [],
            }
            for b in BOOKS
        },
    }


def render_jpeg(doc, pdf_1based: int, max_w=1500) -> bytes:
    pix = doc[pdf_1based - 1].get_pixmap(matrix=fitz.Matrix(1.7, 1.7))
    png_bytes = pix.tobytes("png")
    im = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    if im.width > max_w:
        h = int(im.height * max_w / im.width)
        im = im.resize((max_w, h), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=80)
    return buf.getvalue()


def call_gemini(api_key: str, prompt: str, img_jpeg: bytes) -> dict:
    last = None
    for model in MODELS:
        delay = 6
        for _ in range(5):
            try:
                url = (
                    "https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{model}:generateContent?key={api_key}"
                )
                body = {
                    "contents": [
                        {
                            "parts": [
                                {"text": prompt},
                                {
                                    "inline_data": {
                                        "mime_type": "image/jpeg",
                                        "data": base64.b64encode(img_jpeg).decode(),
                                    }
                                },
                            ]
                        }
                    ],
                    "generationConfig": {
                        "responseMimeType": "application/json",
                        "temperature": 0.1,
                    },
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(body).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=180) as resp:
                    raw = json.loads(resp.read().decode("utf-8"))
                    text = raw["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(text)
            except urllib.error.HTTPError as e:
                last = e
                code = e.code
                if code in (429, 503):
                    print(f"    {model} HTTP {code}; sleep {delay}s", flush=True)
                    time.sleep(delay)
                    delay = min(delay * 2, 60)
                    continue
                print(f"    {model} HTTP {code}; try next", flush=True)
                break
            except Exception as e:
                last = e
                print(f"    {model} err {e}; sleep {delay}s", flush=True)
                time.sleep(delay)
                delay = min(delay * 2, 60)
    raise RuntimeError(str(last))


def extract_page(api_key, book_name, printed, pdf_p, jpg, round_no: int = 1) -> dict:
    prompt = f"""You OCR Santhosh Mani Academy TNPSC Tamil SM notes for அறநூல்கள்.

Focus book: {book_name}
Printed page: {printed} | PDF page: {pdf_p}
Extraction round: {round_no} of 3 (be thorough; catch facts you might miss on a quick pass).

Extract FACT-BANK content for MCQs. Prefer facts over long poem meanings.

Return JSON only:
{{
  "footer_page": null,
  "book_headings_ta": ["..."],
  "facts": [
    {{"fact_ta":"...", "category":"author|count|alias|religion|meaning_of_title|structure|quote_attribution|other", "confidence":"high|medium"}}
  ],
  "quotes": [{{"text_ta":"...", "note_ta":""}}],
  "sample_poems": [
    {{"lines_ta":["..."], "author_ta":"", "meaning_ta":"", "source_label_ta":""}}
  ],
  "vocab": [{{"word_ta":"...", "meaning_ta":"..."}}],
  "other_books_on_page": ["..."]
}}

Rules:
- Atomic facts (one claim each). Include numbers, names, aliases, religion, verse counts, compilers, English translators, special titles.
- Keep Tamil accurate.
- Also extract short famous lines as quotes.
- If page has leftover facts for another book, put them in facts too and list book in other_books_on_page.
- Skip pure handwriting marks.
- Round {round_no}: look carefully at side notes, "மேலும் அறிந்து கொள்வோம்", small bullets, and table-like lines.
"""
    return call_gemini(api_key, prompt, jpg)


def norm_fact(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").strip().lower())


def merge_book(book: dict, page_obj: dict, printed: int):
    seen_f = {norm_fact(f.get("fact_ta") if isinstance(f, dict) else str(f)) for f in book.get("facts") or []}
    for f in page_obj.get("facts") or []:
        if isinstance(f, dict):
            ft = (f.get("fact_ta") or "").strip()
            if not ft or norm_fact(ft) in seen_f:
                continue
            seen_f.add(norm_fact(ft))
            f["source_page"] = printed
            book.setdefault("facts", []).append(f)
        else:
            ft = str(f).strip()
            if ft and norm_fact(ft) not in seen_f:
                seen_f.add(norm_fact(ft))
                book.setdefault("facts", []).append(
                    {"fact_ta": ft, "category": "other", "confidence": "medium", "source_page": printed}
                )

    for q in page_obj.get("quotes") or []:
        if isinstance(q, dict) and (q.get("text_ta") or "").strip():
            q["source_page"] = printed
            book.setdefault("quotes", []).append(q)

    for p in page_obj.get("sample_poems") or []:
        if isinstance(p, dict):
            p["source_page"] = printed
            book.setdefault("sample_poems", []).append(p)

    for v in page_obj.get("vocab") or []:
        if isinstance(v, dict) and (v.get("word_ta") or "").strip():
            v["source_page"] = printed
            book.setdefault("vocab", []).append(v)

    if printed not in book.get("source_pages", []):
        book.setdefault("source_pages", []).append(printed)


def extract_books(book_ids: list[str], api_key: str, rounds: int = 1):
    if not os.path.exists(PDF_PATH):
        raise SystemExit(f"Missing PDF: {PDF_PATH}")

    notes = load_json(NOTES_PATH, empty_notes())
    if "books" not in notes:
        notes = empty_notes()
    # ensure all book shells exist
    for b in BOOKS:
        notes["books"].setdefault(
            b["id"],
            {
                "id": b["id"],
                "toc_no": b["toc_no"],
                "name_ta": b["name_ta"],
                "printed_pages": b["printed"],
                "status": "pending",
                "facts": [],
                "quotes": [],
                "sample_poems": [],
                "vocab": [],
                "source_pages": [],
            },
        )

    by_id = {b["id"]: b for b in BOOKS}
    doc = fitz.open(PDF_PATH)
    rounds = max(1, int(rounds))

    for bid in book_ids:
        meta = by_id[bid]
        book = notes["books"][bid]
        print(
            f"\n=== {meta['toc_no']} {meta['name_ta']} pages {meta['printed']} | rounds={rounds} ===",
            flush=True,
        )
        book["status"] = "in_progress"
        book["name_ta"] = meta["name_ta"]
        book["toc_no"] = meta["toc_no"]
        book["printed_pages"] = meta["printed"]
        book["extract_rounds_target"] = rounds
        save_json(NOTES_PATH, notes)

        pages = list(range(meta["printed"][0], meta["printed"][-1] + 1))
        for rnd in range(1, rounds + 1):
            print(f"  -- round {rnd}/{rounds} --", flush=True)
            before = len(book.get("facts") or [])
            for printed in pages:
                pdf_p = printed + PDF_OFFSET
                print(f"  OCR r{rnd} printed {printed} (pdf {pdf_p})...", flush=True)
                jpg = render_jpeg(doc, pdf_p)
                try:
                    obj = extract_page(api_key, meta["name_ta"], printed, pdf_p, jpg, round_no=rnd)
                except Exception as e:
                    print(f"  FAIL {e}", flush=True)
                    continue
                merge_book(book, obj or {}, printed)
                print(
                    f"  -> facts={len(book.get('facts') or [])} quotes={len(book.get('quotes') or [])} poems={len(book.get('sample_poems') or [])}",
                    flush=True,
                )
                save_json(NOTES_PATH, notes)
                time.sleep(1.2)
            added = len(book.get("facts") or []) - before
            book["extract_rounds_done"] = rnd
            print(f"  round {rnd} added≈{added} facts (total {len(book.get('facts') or [])})", flush=True)
            save_json(NOTES_PATH, notes)
            if rnd < rounds:
                time.sleep(2)

        book["status"] = "done"
        book["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        notes["updated_at"] = book["updated_at"]
        save_json(NOTES_PATH, notes)
        print(f"  DONE {bid}: {len(book.get('facts') or [])} facts after {rounds} rounds", flush=True)

    doc.close()
    return notes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument(
        "--books",
        type=str,
        default="",
        help="comma-separated book ids",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=1,
        help="OCR merge rounds per book (default 1; use 3 for denser facts)",
    )
    args = parser.parse_args()

    if args.list:
        for b in BOOKS:
            print(f"{b['toc_no']:4} {b['id']:22} {b['name_ta']}  pp {b['printed']}")
        return

    if args.all:
        ids = [b["id"] for b in BOOKS]
    elif args.books.strip():
        ids = [x.strip() for x in args.books.split(",") if x.strip()]
    else:
        raise SystemExit("Pass --books id1,id2 or --all or --list")

    known = {b["id"] for b in BOOKS}
    bad = [i for i in ids if i not in known]
    if bad:
        raise SystemExit(f"Unknown book ids: {bad}")

    api_key = get_api_key()
    notes = extract_books(ids, api_key, rounds=args.rounds)
    print("\nSummary:")
    for bid in ids:
        b = notes["books"][bid]
        print(
            f"  {b.get('toc_no')} {b.get('name_ta')}: status={b.get('status')} "
            f"facts={len(b.get('facts') or [])} rounds={b.get('extract_rounds_done')}"
        )


if __name__ == "__main__":
    main()
