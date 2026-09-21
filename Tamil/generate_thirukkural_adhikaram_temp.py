#!/usr/bin/env python3
"""
Temp pipeline: extract SM Thirukkural adhikarams (printed 365-385),
generate 20 PYQ-style MCQs per adhikaram, Gemini-verify, save temp JSON.

Outputs:
  Tamil/unit7_thirukkural_adhikaram_notes_temp.json
  Tamil/unit7_thirukkural_adhikaram_questions_temp.json

Usage:
  python3 Tamil/generate_thirukkural_adhikaram_temp.py --extract
  python3 Tamil/generate_thirukkural_adhikaram_temp.py --generate
  python3 Tamil/generate_thirukkural_adhikaram_temp.py --all
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

import fitz

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_PATH = os.path.join(BASE_DIR, "Data", "Tamil", "ilakanam", "SM TAMIL FULL BOOK 570 PAGES.pdf")
PYQ_PATH = os.path.join(BASE_DIR, "Tamil", "unit7_thirukkural_pyq_page388_group4.json")
NOTES_PATH = os.path.join(BASE_DIR, "Tamil", "unit7_thirukkural_adhikaram_notes_temp.json")
OUT_PATH = os.path.join(BASE_DIR, "Tamil", "unit7_thirukkural_adhikaram_questions_temp.json")
PDF_OFFSET = 6  # printed + 6 = pdf
PRINT_START, PRINT_END = 365, 385
Q_PER_ADHIKARAM = 20

MODELS = ["gemini-2.5-flash-lite", "gemini-3.5-flash-lite", "gemini-3.5-flash"]


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


def call_gemini(api_key: str, prompt: str, img_b64: str | None = None, model: str | None = None) -> str:
    # Prefer requested model first, then fall back to lighter models on 429/503.
    preferred = [model] if model else []
    models = []
    for m in preferred + MODELS:
        if m and m not in models:
            models.append(m)
    last = None
    for m in models:
        delay = 6
        # On 429, don't burn too long on one model — fall through sooner.
        for attempt in range(3):
            try:
                parts = [{"text": prompt}]
                if img_b64:
                    parts.append({"inlineData": {"mimeType": "image/jpeg", "data": img_b64}})
                payload = {
                    "contents": [{"parts": parts}],
                    "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2},
                }
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
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
                print(f"    {m} HTTP {e.code}", flush=True)
                break
            except Exception as e:
                last = e
                print(f"    {m} err: {e}; sleep {delay}s", flush=True)
                time.sleep(delay)
                delay = min(delay * 2, 60)
    # Final slow pass on lite models only
    for m in [x for x in MODELS if "lite" in x]:
        delay = 15
        for attempt in range(5):
            try:
                parts = [{"text": prompt}]
                if img_b64:
                    parts.append({"inlineData": {"mimeType": "image/jpeg", "data": img_b64}})
                payload = {
                    "contents": [{"parts": parts}],
                    "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2},
                }
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=180) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                last = e
                print(f"    final {m}: {e}; sleep {delay}s", flush=True)
                time.sleep(delay)
                delay = min(delay * 2, 90)
    raise RuntimeError(f"Gemini failed: {last}")


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
    # first object or array
    for opener, closer in (("[", "]"), ("{", "}")):
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
    raise ValueError("Could not parse JSON from model output")


def render_page(doc, printed: int, dpi: int = 140) -> str:
    pdf_p = printed + PDF_OFFSET
    pix = doc[pdf_p - 1].get_pixmap(dpi=dpi)
    return base64.b64encode(pix.tobytes("jpg")).decode("utf-8")


def extract_notes(api_key: str):
    doc = fitz.open(PDF_PATH)
    notes = load_json(
        NOTES_PATH,
        {
            "source_pdf": "Data/Tamil/ilakanam/SM TAMIL FULL BOOK 570 PAGES.pdf",
            "printed_range": [PRINT_START, PRINT_END],
            "pdf_offset": PDF_OFFSET,
            "pages": {},
            "adhikarams": [],
        },
    )
    pages = notes.setdefault("pages", {})

    for printed in range(PRINT_START, PRINT_END + 1):
        key = str(printed)
        if pages.get(key, {}).get("status") == "ok" and pages[key].get("kurals"):
            print(f"P{printed}: skip extract", flush=True)
            continue
        print(f"P{printed}: extract...", flush=True)
        img = render_page(doc, printed)
        prompt = f"""Extract Thirukkural content from SM Tamil notes page (footer ~{printed}).

Return JSON:
{{
  "footer": {printed},
  "adhikaram_headings": [{{"serial_no": 1, "title_ta": "ஒழுக்கமுடைமை"}}],
  "kurals": [
    {{
      "adhikaram_title_ta": "ஒழுக்கமுடைமை",
      "adhikaram_serial_no": 1,
      "kural_ta": "two-line kural text",
      "meaning_ta": "meaning as printed"
    }}
  ]
}}

Rules:
- Keep Tamil exact.
- serial_no is the book's local numbering 1-20 in this section if shown.
- Include EVERY kural+meaning pair on the page.
- If page continues previous adhikaram with no new heading, still set adhikaram_title_ta from context if visible; else use "".
"""
        raw = call_gemini(api_key, prompt, img)
        obj = parse_json(raw)
        pages[key] = {
            "status": "ok",
            "footer": obj.get("footer"),
            "adhikaram_headings": obj.get("adhikaram_headings") or [],
            "kurals": obj.get("kurals") or [],
        }
        notes["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        save_json(NOTES_PATH, notes)
        print(f"P{printed}: {len(pages[key]['kurals'])} kurals", flush=True)
        time.sleep(1.0)

    doc.close()
    notes["adhikarams"] = rebuild_adhikarams(notes)
    save_json(NOTES_PATH, notes)
    print(f"Extracted {len(notes['adhikarams'])} adhikarams → {NOTES_PATH}", flush=True)
    for a in notes["adhikarams"]:
        print(f"  #{a.get('serial_no')}: {a.get('name_ta')} ({len(a.get('kurals') or [])} kurals)", flush=True)
    return notes


def rebuild_adhikarams(notes: dict) -> list:
    """Linear heading walk; ignore flaky OCR serials; merge known aliases."""
    merge_into = {
        "ஒல்காமை (தொடர்ச்சி)": "ஊக்கமுடைமை",
        "ஒல்காமை": "ஊக்கமுடைமை",
        "செயல்வகை": "வினை செயல்வகை",
        "வினைசெயல்வகை": "வினை செயல்வகை",
        "அவைச்சங்கம்": "அவை அஞ்சாமை",
        "நன்புடைமை": "பண்புடைமை",
    }

    def norm_title(t: str) -> str:
        t = re.sub(r"\s+", " ", (t or "").strip())
        if not t or "தொடர்ச்சி" in t:
            return ""
        return merge_into.get(t, t)

    buckets: list[dict] = []
    current = None

    def start_adh(title: str):
        nonlocal current
        if current and current["name_ta"] == title:
            return
        for a in buckets:
            if a["name_ta"] == title:
                current = a
                return
        a = {"serial_no": len(buckets) + 1, "name_ta": title, "kurals": []}
        buckets.append(a)
        current = a

    for printed in range(PRINT_START, PRINT_END + 1):
        page = (notes.get("pages") or {}).get(str(printed)) or {}
        clean_heads = []
        for h in page.get("adhikaram_headings") or []:
            t = norm_title(h.get("title_ta"))
            if t:
                clean_heads.append(t)
        kurals = page.get("kurals") or []

        if not clean_heads:
            targets = [(current, kurals)] if current else []
        elif len(clean_heads) == 1:
            start_adh(clean_heads[0])
            targets = [(current, kurals)]
        else:
            started = []
            for t in clean_heads:
                start_adh(t)
                started.append(current)
            n = len(started)
            k = len(kurals)
            size = max(1, k // n) if k else 0
            targets = []
            idx = 0
            for i, a in enumerate(started):
                part = kurals[idx:] if i == n - 1 else kurals[idx : idx + size]
                if i < n - 1:
                    idx += size
                targets.append((a, part))

        for adh, part in targets:
            if adh is None:
                continue
            for k in part:
                kt = (k.get("kural_ta") or "").strip()
                if not kt:
                    continue
                kt_title = norm_title(k.get("adhikaram_title_ta"))
                if kt_title and kt_title != adh["name_ta"]:
                    start_adh(kt_title)
                    adh = current
                key = re.sub(r"\s+", "", kt)
                if any(re.sub(r"\s+", "", x["kural_ta"]) == key for x in adh["kurals"]):
                    continue
                adh["kurals"].append(
                    {
                        "kural_ta": kt,
                        "meaning_ta": (k.get("meaning_ta") or "").strip(),
                        "source_page": printed,
                    }
                )

    for i, b in enumerate(buckets, 1):
        if len(b["kurals"]) > 12:
            b["kurals"] = b["kurals"][:10]
        b["serial_no"] = i
        b["kural_count"] = len(b["kurals"])
    return buckets


def pyq_style_samples(limit: int = 8) -> list:
    pyq = load_json(PYQ_PATH, [])
    # prefer meaning-style from later questions
    preferred = [q for q in pyq if q.get("q_no", 0) >= 17][:limit]
    if len(preferred) < limit:
        preferred = pyq[:limit]
    out = []
    for q in preferred:
        out.append(
            {
                "question_ta": q.get("question_ta"),
                "options_ta": q.get("options_ta"),
                "correct_option_letter": q.get("correct_option_letter"),
            }
        )
    return out


def generate_for_adhikaram(api_key: str, adh: dict, samples: list) -> list:
    serial = adh.get("serial_no")
    name = adh.get("name_ta")
    kurals = adh.get("kurals") or []
    prompt = f"""You are writing TNPSC Group-4 style Thirukkural MCQs in Tamil.

Adhikaram serial: {serial}
Adhikaram name: {name}
Kurals+meanings from SM notes (ground truth — do not invent kurals):
{json.dumps(kurals, ensure_ascii=False)}

PYQ style samples (match tone/shape, do not copy):
{json.dumps(samples, ensure_ascii=False)}

Create EXACTLY {Q_PER_ADHIKARAM} unique MCQs for THIS adhikaram only.
Mix types: meaning, complete the line, concept from kural, which idea Valluvar stresses.
Use ONLY facts supported by the provided kurals/meanings.
Options A-D. One correct answer.

Return JSON array of {Q_PER_ADHIKARAM} objects:
[
  {{
    "question_ta": "...",
    "options_ta": ["A text","B text","C text","D text"],
    "correct_option_letter": "A",
    "explanation_ta": "short",
    "based_on_kural": "optional snippet"
  }}
]
No adhikaram fields here — caller will add them.
"""
    raw = call_gemini(api_key, prompt, None, model="gemini-2.5-flash-lite")
    data = parse_json(raw)
    if isinstance(data, dict):
        data = data.get("questions") or data.get("items") or []
    if not isinstance(data, list):
        return []
    cleaned = []
    for q in data:
        if not isinstance(q, dict):
            continue
        opts = q.get("options_ta") or []
        if isinstance(opts, list) and opts and isinstance(opts[0], dict):
            opts = [(o.get("text_ta") or o.get("text") or "").strip() for o in opts]
        opts = [str(o).strip() for o in opts if str(o).strip()]
        letter = str(
            q.get("correct_option_letter")
            or q.get("correct_option")
            or q.get("answer")
            or q.get("answer_letter")
            or ""
        ).strip().upper()[:1]
        stem = (q.get("question_ta") or "").strip()
        if not stem or len(opts) < 4:
            continue
        # Infer letter from answer text if needed
        if letter not in "ABCD":
            ans_text = str(q.get("answer_text") or q.get("correct_answer") or "").strip()
            if ans_text:
                for i, o in enumerate(opts[:4]):
                    if re.sub(r"\s+", "", o) == re.sub(r"\s+", "", ans_text):
                        letter = chr(65 + i)
                        break
        if letter not in "ABCD":
            continue
        cleaned.append(
            {
                "question_ta": stem,
                "options_ta": opts[:4],
                "correct_option_letter": letter,
                "explanation_ta": (q.get("explanation_ta") or "").strip(),
                "based_on_kural": (q.get("based_on_kural") or "").strip(),
            }
        )
    return cleaned[:Q_PER_ADHIKARAM]


def verify_questions(api_key: str, adh: dict, questions: list) -> list:
    prompt = f"""Verify these TNPSC Thirukkural MCQs against the adhikaram ground truth.

Adhikaram: {adh.get('serial_no')}. {adh.get('name_ta')}
Kurals+meanings:
{json.dumps(adh.get('kurals') or [], ensure_ascii=False)}

Questions:
{json.dumps(questions, ensure_ascii=False)}

For each question index (0-based), check:
- answer letter matches a real supported meaning from the kurals
- stem is clear Tamil MCQ
- distractors plausible but wrong

Return JSON:
{{
  "results": [
    {{
      "index": 0,
      "ok": true,
      "correct_option_letter": "A",
      "fix_stem": "",
      "note_ta": ""
    }}
  ]
}}
ALWAYS return correct_option_letter as A/B/C/D for every index (the right answer after verification).
If stem broken, set fix_stem to repaired stem (else "").
"""
    raw = call_gemini(api_key, prompt, None, model="gemini-2.5-flash-lite")
    obj = parse_json(raw)
    results = obj.get("results") if isinstance(obj, dict) else obj
    if not isinstance(results, list):
        return questions
    by_i = {int(r.get("index")): r for r in results if isinstance(r, dict) and r.get("index") is not None}
    out = []
    for i, q in enumerate(questions):
        r = by_i.get(i) or {}
        qq = dict(q)
        letter = str(
            r.get("correct_option_letter")
            or r.get("fix_letter")
            or q.get("correct_option_letter")
            or ""
        ).strip().upper()[:1]
        if letter in "ABCD":
            qq["correct_option_letter"] = letter
        fix_stem = (r.get("fix_stem") or "").strip()
        if fix_stem:
            qq["question_ta"] = fix_stem
        qq["verified"] = bool(r.get("ok", True)) if r else False
        qq["verify_note_ta"] = (r.get("note_ta") or "").strip()
        out.append(qq)
    return out


def generate_all(api_key: str):
    notes = load_json(NOTES_PATH, {})
    adhikarams = notes.get("adhikarams") or []
    if len(adhikarams) < 15:
        print("Notes incomplete; running extract first...", flush=True)
        notes = extract_notes(api_key)
        adhikarams = notes.get("adhikarams") or []

    out = load_json(
        OUT_PATH,
        {
            "temp": True,
            "topic": "thirukkural",
            "source": "SM pages 365-385 + G4 PYQ style",
            "q_per_adhikaram": Q_PER_ADHIKARAM,
            "questions": [],
            "progress": {},
        },
    )
    progress = out.setdefault("progress", {})
    questions = [q for q in out.get("questions") or [] if q.get("adhikaram_serial_no")]
    # drop incomplete adhikarams from progress if regenerating missing
    samples = pyq_style_samples()

    for adh in adhikarams:
        serial = int(adh.get("serial_no") or 0)
        name = adh.get("name_ta") or ""
        key = str(serial)
        existing = [q for q in questions if q.get("adhikaram_serial_no") == serial]
        if progress.get(key) == "done" and len(existing) >= Q_PER_ADHIKARAM:
            print(f"Adhikaram {serial} {name}: skip ({len(existing)} Q)", flush=True)
            continue

        print(f"\n=== Generate {serial}. {name} ({len(adh.get('kurals') or [])} kurals) ===", flush=True)
        # remove old partial
        questions = [q for q in questions if q.get("adhikaram_serial_no") != serial]

        gen = generate_for_adhikaram(api_key, adh, samples)
        print(f"  generated {len(gen)}", flush=True)
        if len(gen) < Q_PER_ADHIKARAM:
            # one retry
            more = generate_for_adhikaram(api_key, adh, samples)
            seen = {re.sub(r"\s+", "", g["question_ta"]) for g in gen}
            for g in more:
                k = re.sub(r"\s+", "", g["question_ta"])
                if k not in seen:
                    gen.append(g)
                    seen.add(k)
                if len(gen) >= Q_PER_ADHIKARAM:
                    break
            gen = gen[:Q_PER_ADHIKARAM]
            print(f"  after retry {len(gen)}", flush=True)

        print(f"  verifying with Gemini...", flush=True)
        verified = verify_questions(api_key, adh, gen)
        # Drop / flag empty letters
        good = [q for q in verified if q.get("correct_option_letter") in "ABCD"]
        if len(good) < Q_PER_ADHIKARAM:
            print(f"  letter gaps: {len(good)}/{len(verified)}; retry generate once", flush=True)
            more = generate_for_adhikaram(api_key, adh, samples)
            more = verify_questions(api_key, adh, more)
            seen = {re.sub(r"\s+", "", g["question_ta"]) for g in good}
            for g in more:
                if g.get("correct_option_letter") not in "ABCD":
                    continue
                k = re.sub(r"\s+", "", g["question_ta"])
                if k in seen:
                    continue
                good.append(g)
                seen.add(k)
                if len(good) >= Q_PER_ADHIKARAM:
                    break
        verified = good[:Q_PER_ADHIKARAM]

        # if short, keep what we have but mark
        for i, q in enumerate(verified, 1):
            questions.append(
                {
                    "q_no": None,  # filled later
                    "adhikaram_serial_no": serial,
                    "adhikaram_name_ta": name,
                    "question_ta": q["question_ta"],
                    "options_ta": q["options_ta"],
                    "correct_option_letter": q["correct_option_letter"],
                    "explanation_ta": q.get("explanation_ta") or "",
                    "based_on_kural": q.get("based_on_kural") or "",
                    "verified": q.get("verified", False),
                    "verify_note_ta": q.get("verify_note_ta") or "",
                    "examGroup": ["group4"],
                    "source": "generated_from_sm_adhikaram",
                }
            )

        progress[key] = "done" if len(verified) >= Q_PER_ADHIKARAM else f"partial_{len(verified)}"
        # renumber globally
        for i, q in enumerate(questions, 1):
            q["q_no"] = i
        out["questions"] = questions
        out["progress"] = progress
        out["count"] = len(questions)
        out["adhikaram_count"] = len({q["adhikaram_serial_no"] for q in questions})
        out["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        save_json(OUT_PATH, out)
        print(f"  saved total {len(questions)} → {OUT_PATH}", flush=True)
        time.sleep(8.0)

    print(f"\nDONE: {len(questions)} questions, {out.get('adhikaram_count')} adhikarams", flush=True)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--extract", action="store_true")
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    if not (args.extract or args.generate or args.all):
        args.all = True

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY missing")

    if args.extract or args.all:
        extract_notes(api_key)
    if args.generate or args.all:
        generate_all(api_key)


if __name__ == "__main__":
    main()
