#!/usr/bin/env python3
"""
Generate / top-up MCQs for Unit 7 — தமிழ்ச் சான்றோர் பற்றிய செய்திகள்.
Target: 4 batches × 30 = 120 practice Q.

Usage:
  python3 Tamil/generate_tamilsaandror_questions.py --resume
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from difflib import SequenceMatcher

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTES_PATH = os.path.join(BASE_DIR, "Tamil", "unit7_tamilsaandror_notes_temp.json")
PYQ_PATH = os.path.join(BASE_DIR, "Tamil", "unit7_tamilsaandror_pyq.json")
TEMP_PATH = os.path.join(BASE_DIR, "Tamil", "tamilsaandror_questions_temp.json")
DB_PATH = os.path.join(BASE_DIR, "Tamil", "tamilsaandror_questions_db.json")

MODELS = ["gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-3.5-flash"]
TARGET = 30
NUM_BATCHES = 4
TOPIC_NAME = "தமிழ்ச் சான்றோர் பற்றிய செய்திகள்"
SCHOLARS = (
    "பாவேந்தர் பாரதிதாசன், டி.கே.சிதம்பரனார், குன்றக்குடி அடிகளார், கண்ணதாசன், "
    "காயிதே மில்லத், தாராபாரதி, வேலுநாச்சியார், பட்டுக்கோட்டைக் கல்யாணசுந்தரம், "
    "முடியரசன், தமிழ் ஒளி, உருத்திரங்கண்ணனார், கி.வா.ஜகந்நாதர், நாமக்கல் கவிஞர்"
)


def load_json(p, d=None):
    if not os.path.exists(p):
        return d if d is not None else {}
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(p, d):
    t = p + ".tmp"
    with open(t, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(t, p)


def get_api_key():
    k = os.environ.get("GEMINI_API_KEY") or ""
    if k:
        return k
    zshrc = os.path.expanduser("~/.zshrc")
    if os.path.exists(zshrc):
        for line in open(zshrc, encoding="utf-8", errors="replace"):
            if "GEMINI_API_KEY" in line and not line.strip().startswith("#"):
                m = re.search(r'GEMINI_API_KEY[= ]+["\']?([A-Za-z0-9_\-]+)', line)
                if m:
                    return m.group(1)
    raise SystemExit("GEMINI_API_KEY missing")


def call_gemini(api_key, prompt):
    last = None
    for m in MODELS:
        delay = 6
        for _ in range(4):
            try:
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "responseMimeType": "application/json",
                        "temperature": 0.35,
                    },
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
                    time.sleep(delay)
                    delay = min(delay * 2, 60)
                    continue
                break
            except Exception as e:
                last = e
                time.sleep(delay)
                delay = min(delay * 2, 60)
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
    for o, c in (("[", "]"), ("{", "}")):
        s = text.find(o)
        if s < 0:
            continue
        d = 0
        for i, ch in enumerate(text[s:], s):
            if ch == o:
                d += 1
            elif ch == c:
                d -= 1
                if d == 0:
                    try:
                        return json.loads(text[s : i + 1])
                    except Exception:
                        break
    raise ValueError("parse fail")


def norm(s):
    return re.sub(r"\s+", "", str(s or "").lower())


def build_facts(notes, quote_limit=40):
    lines = []
    for sid, st in notes.get("subtopics", {}).items():
        lines.append(f"\n## {st.get('name_ta', sid)}")
        for f in st.get("facts", []):
            ft = f.get("fact_ta") if isinstance(f, dict) else str(f)
            if ft:
                lines.append(f"- {ft}")
        for q in st.get("quotes", [])[:quote_limit]:
            qt = q.get("text_ta") if isinstance(q, dict) else str(q)
            if qt:
                lines.append(f'- Quote: "{qt}"')
    return "\n".join(lines)


def build_pyq_examples(pyqs):
    lines = []
    for q in pyqs[:12]:
        opts = q.get("options_ta") or []
        lines.append(
            f"Q: {q.get('question_ta')}\n"
            f"A) {opts[0] if opts else ''} B) {opts[1] if len(opts)>1 else ''} "
            f"C) {opts[2] if len(opts)>2 else ''} D) {opts[3] if len(opts)>3 else ''}\n"
            f"Answer: {q.get('correct_option_letter')}\n"
        )
    return "\n".join(lines)


def db_to_temp(db):
    """Rebuild temp batches from final DB (keeps options_ta shape for generator)."""
    batches = {}
    for q in db:
        bkey = q.get("batch") or "Batch 1"
        opts = []
        if q.get("options"):
            opts = [o.get("text_ta") or o.get("text_en") or "" for o in q["options"]]
        elif q.get("options_ta"):
            opts = list(q["options_ta"])
        batches.setdefault(bkey, []).append(
            {
                "question_ta": q.get("question_ta") or "",
                "options_ta": opts,
                "correct_option_letter": q.get("correct_option") or q.get("correct_option_letter") or "A",
                "explanation_ta": q.get("explanation_ta") or q.get("explanation") or "",
                "difficulty": q.get("difficulty") or "Medium",
            }
        )
    return {"batches": batches}


def accept_new(all_qs, existing_stems, need):
    accepted = []
    seen = {norm(s) for s in existing_stems if s}
    for q in all_qs:
        if len(accepted) >= need:
            break
        stem = (q.get("question_ta") or "").strip()
        opts = [str(o) for o in (q.get("options_ta") or [])]
        letter = str(q.get("correct_option_letter") or "").strip().upper()[:1]
        if not stem or len(opts) < 4 or letter not in "ABCD":
            continue
        q["options_ta"] = opts[:4]
        q["correct_option_letter"] = letter
        sn = norm(stem)
        if sn in seen:
            continue
        if any(SequenceMatcher(None, sn, norm(ex)).ratio() >= 0.90 for ex in existing_stems):
            continue
        if any(SequenceMatcher(None, sn, s).ratio() >= 0.90 for s in seen):
            continue
        if len(set(norm(o) for o in opts[:4])) < 4:
            continue
        seen.add(sn)
        accepted.append(q)
    return accepted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true", help="Top-up from existing DB/temp")
    args = parser.parse_args()

    api_key = get_api_key()
    notes = load_json(NOTES_PATH)
    pyqs = load_json(PYQ_PATH, [])

    if args.resume:
        db = load_json(DB_PATH, [])
        if isinstance(db, list) and db:
            temp = db_to_temp(db)
            print(f"Loaded DB -> temp: { {k: len(v) for k,v in temp['batches'].items()} }", flush=True)
        else:
            temp = load_json(TEMP_PATH, {"batches": {}})
    else:
        temp = {"batches": {}}

    facts_all = build_facts(notes, quote_limit=40)
    pyq_examples = build_pyq_examples(pyqs)
    print(f"Facts text length: {len(facts_all)} chars", flush=True)

    for batch_no in range(1, NUM_BATCHES + 1):
        bkey = f"Batch {batch_no}"
        current = list(temp.get("batches", {}).get(bkey, []))
        need = TARGET - len(current)
        if need <= 0:
            print(f"SKIP {bkey} (already {len(current)} Q)", flush=True)
            continue

        # Rotate fact window so later batches see different scholars/quotes
        chunk = 22000
        start = ((batch_no - 1) * 11000) % max(1, len(facts_all) - 200)
        facts_text = facts_all[start : start + chunk]
        if len(facts_text) < 10000:
            facts_text = facts_all[:chunk]

        print(f"\n=== {TOPIC_NAME} | {bkey} (have {len(current)}, need +{need}) ===", flush=True)

        existing = []
        for bk, bqs in temp.get("batches", {}).items():
            for q in bqs:
                existing.append(q.get("question_ta", ""))

        rounds = 5 if need >= 20 else 4
        all_qs = []
        for rnd in range(1, rounds + 1):
            req_n = max(need + 10, 35)
            print(f"  round {rnd}/{rounds} requesting ~{req_n}...", flush=True)
            avoid = ""
            if existing:
                sample = existing[-50:] if len(existing) > 50 else existing
                avoid = (
                    "\n\nIMPORTANT: Create COMPLETELY DIFFERENT questions. "
                    "Use DIFFERENT facts / different scholars / different quote lines. "
                    "Do NOT rephrase these existing stems:\n"
                    + "\n".join(f"- {s[:120]}" for s in sample)
                )
            focus = ""
            if batch_no >= 3:
                focus = (
                    "\nFocus EXTRA on under-used scholars & quotes: "
                    "டி.கே.சிதம்பரனார், குன்றக்குடி அடிகளார், காயிதே மில்லத், தாராபாரதி, "
                    "தமிழ் ஒளி, கி.வா.ஜகந்நாதர், உருத்திரங்கண்ணனார், நாமக்கல் கவிஞர், "
                    "and quote-attribution questions from பாவேந்தர் / வேலுநாச்சியார் / முடியரசன்."
                )
            prompt = f"""TNPSC General Tamil MCQ generator.
Topic: {TOPIC_NAME} | {bkey} top-up

SM FACTS (use many different rows — do not keep asking the same birth year / title):
{facts_text}

PYQ STYLE EXAMPLES:
{pyq_examples}

Generate EXACTLY {req_n} UNIQUE TNPSC-style MCQs.
Cover these scholars: {SCHOLARS}
{focus}

Question types to mix: birth/death/place, books, titles, awards, journals/newspapers,
institutions, contributions, quote attribution, "who said", year of event.

Rules:
- Tamil stems + 4 Tamil options A-D
- Exactly one correct_option_letter
- explanation_ta briefly justifying answer
- difficulty Easy|Medium|Hard
- Prefer FACTS not already covered by existing stems
{avoid}

Return JSON: {{"questions":[{{"question_ta":"...","options_ta":["A","B","C","D"],"correct_option_letter":"A|B|C|D","explanation_ta":"...","difficulty":"Easy|Medium|Hard"}}]}}"""
            try:
                raw = call_gemini(api_key, prompt)
                obj = parse_json(raw)
                qs = obj.get("questions") if isinstance(obj, dict) else obj
                if isinstance(qs, list):
                    print(f"  got {len(qs)} raw", flush=True)
                    all_qs.extend(qs)
            except Exception as e:
                print(f"  FAIL: {e}", flush=True)
            time.sleep(2)

        added = accept_new(all_qs, existing, need)
        current.extend(added)
        temp.setdefault("batches", {})[bkey] = current[:TARGET]
        save_json(TEMP_PATH, temp)
        print(
            f"  added {len(added)}/{len(all_qs)} → {bkey} now {len(temp['batches'][bkey])}/{TARGET}",
            flush=True,
        )
        time.sleep(2)

    # Build DB
    db = []
    for bn in range(1, NUM_BATCHES + 1):
        bkey = f"Batch {bn}"
        for q in temp.get("batches", {}).get(bkey, []):
            stem = (q.get("question_ta") or "").strip()
            opts = q.get("options_ta") or []
            db.append(
                {
                    "topic": TOPIC_NAME,
                    "batch": bkey,
                    "question_ta": stem,
                    "question_en": stem,
                    "options": [
                        {"key": chr(65 + j), "text_en": opts[j], "text_ta": opts[j]}
                        for j in range(min(4, len(opts)))
                    ],
                    "correct_option": (q.get("correct_option_letter") or "").strip().upper()[:1],
                    "explanation": q.get("explanation_ta") or "",
                    "explanation_ta": q.get("explanation_ta") or "",
                    "difficulty": q.get("difficulty") or "Medium",
                    "type": "practice",
                    "source_exam": f"TamilSaandror {bkey}",
                    "source_fact": "SM_tamilsaandror",
                }
            )
    save_json(DB_PATH, db)
    print(f"\nDONE total={len(db)}")
    from collections import Counter

    for (t, b), n in sorted(Counter((q["topic"], q["batch"]) for q in db).items()):
        print(f"  {b} | {t}: {n}")


if __name__ == "__main__":
    main()
