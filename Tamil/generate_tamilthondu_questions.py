#!/usr/bin/env python3
"""
Generate MCQs for Unit 7 — தமிழ்த் தொண்டு தொடர்பான செய்திகள்.
Single topic, 3 batches × 30 = 90 Q.

Usage:
  python3 Tamil/generate_tamilthondu_questions.py
  python3 Tamil/generate_tamilthondu_questions.py --resume
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
NOTES_PATH = os.path.join(BASE_DIR, "Tamil", "unit7_tamilthondu_notes_temp.json")
PYQ_PATH = os.path.join(BASE_DIR, "Tamil", "unit7_tamilthondu_pyq.json")
TEMP_PATH = os.path.join(BASE_DIR, "Tamil", "tamilthondu_questions_temp.json")
DB_PATH = os.path.join(BASE_DIR, "Tamil", "tamilthondu_questions_db.json")

MODELS = ["gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-3.5-flash"]
TARGET = 30
NUM_BATCHES = 2
TOPIC_NAME = "தமிழ்த் தொண்டு தொடர்பான செய்திகள்"


def load_json(p, d=None):
    if not os.path.exists(p): return d if d is not None else {}
    with open(p, "r", encoding="utf-8") as f: return json.load(f)

def save_json(p, d):
    t = p + ".tmp"
    with open(t, "w", encoding="utf-8") as f: json.dump(d, f, ensure_ascii=False, indent=2); f.write("\n")
    os.replace(t, p)

def get_api_key():
    k = os.environ.get("GEMINI_API_KEY") or ""
    if k: return k
    zshrc = os.path.expanduser("~/.zshrc")
    if os.path.exists(zshrc):
        for line in open(zshrc, encoding="utf-8", errors="replace"):
            if "GEMINI_API_KEY" in line and not line.strip().startswith("#"):
                m = re.search(r'GEMINI_API_KEY[= ]+["\']?([A-Za-z0-9_\-]+)', line)
                if m: return m.group(1)
    raise SystemExit("GEMINI_API_KEY missing")

def call_gemini(api_key, prompt):
    last = None
    for m in MODELS:
        delay = 6
        for _ in range(4):
            try:
                payload = {"contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"responseMimeType": "application/json", "temperature": 0.25}}
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
                req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=180) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except urllib.error.HTTPError as e:
                last = e
                if e.code in (429, 503): time.sleep(delay); delay = min(delay*2, 60); continue
                break
            except Exception as e: last = e; time.sleep(delay); delay = min(delay*2, 60)
    raise RuntimeError(str(last))

def parse_json(raw):
    text = (raw or "").strip()
    if text.startswith("```"): text = text.split("\n",1)[1]
    if text.endswith("```"): text = text.rsplit("\n",1)[0]
    try: return json.loads(text)
    except: pass
    for o,c in (("[","]"),("{","}")):
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

def norm(s): return re.sub(r"\s+", "", (s or "").lower())

def build_facts(notes):
    lines = []
    for sid, st in notes.get("subtopics", {}).items():
        lines.append(f"\n## {st.get('name_ta', sid)}")
        for f in st.get("facts", []):
            ft = f.get("fact_ta") if isinstance(f, dict) else str(f)
            if ft: lines.append(f"- {ft}")
        for q in st.get("quotes", [])[:10]:
            qt = q.get("text_ta") if isinstance(q, dict) else str(q)
            if qt: lines.append(f'- Quote: "{qt}"')
    return "\n".join(lines)

def build_pyq_examples(pyqs):
    lines = []
    for q in pyqs[:6]:
        opts = q.get("options_ta") or []
        lines.append(f"Q: {q.get('question_ta')}\nA) {opts[0] if opts else ''} B) {opts[1] if len(opts)>1 else ''} C) {opts[2] if len(opts)>2 else ''} D) {opts[3] if len(opts)>3 else ''}\nAnswer: {q.get('correct_option_letter')}\n")
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    api_key = get_api_key()
    notes = load_json(NOTES_PATH)
    pyqs = load_json(PYQ_PATH, [])
    temp = load_json(TEMP_PATH, {"batches": {}}) if args.resume else {"batches": {}}

    facts_text = build_facts(notes)
    pyq_examples = build_pyq_examples(pyqs)

    for batch_no in range(1, NUM_BATCHES + 1):
        bkey = f"Batch {batch_no}"
        if args.resume and bkey in temp.get("batches", {}) and len(temp["batches"][bkey]) >= TARGET - 5:
            print(f"SKIP {bkey} ({len(temp['batches'][bkey])} Q)", flush=True)
            continue

        print(f"\n=== {TOPIC_NAME} | {bkey} (target {TARGET}) ===", flush=True)
        existing = []
        for bk, bqs in temp.get("batches", {}).items():
            for q in bqs: existing.append(q.get("question_ta", ""))

        avoid = ""
        if existing:
            avoid = "\n\nIMPORTANT: Create COMPLETELY DIFFERENT questions. Use DIFFERENT facts:\n" + "\n".join(f"- {s[:100]}" for s in existing[:40])

        all_qs = []
        for rnd in range(1, 4):
            print(f"  round {rnd}/3 requesting ~{TARGET+5}...", flush=True)
            prompt = f"""TNPSC General Tamil MCQ generator.
Topic: {TOPIC_NAME} | {bkey}

SM FACTS:
{facts_text[:14000]}

PYQ EXAMPLES:
{pyq_examples}

Generate EXACTLY {TARGET+5} UNIQUE MCQs about Tamil scholars (தேவநேயப்பாவாணர், பெருஞ்சித்திரனார், ஜி.யு.போப், வீரமாமுனிவர்).

Question types: birth/death dates, birthplace, books authored/edited, titles received, institutions, key contributions, famous quotes attribution, match-the-following.

Rules: Tamil stems+options, 4 options A-D, one correct, explanation_ta, difficulty tag.
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

        accepted = []
        seen = set()
        for q in all_qs:
            stem = (q.get("question_ta") or "").strip()
            opts = q.get("options_ta") or []
            letter = (q.get("correct_option_letter") or "").strip().upper()[:1]
            if not stem or len(opts) < 4 or letter not in "ABCD": continue
            sn = norm(stem)
            if sn in seen: continue
            if any(SequenceMatcher(None, sn, norm(ex)).ratio() >= 0.92 for ex in existing): continue
            if any(SequenceMatcher(None, sn, s).ratio() >= 0.92 for s in seen): continue
            if len(set(norm(o) for o in opts[:4])) < 4: continue
            seen.add(sn)
            accepted.append(q)

        accepted = accepted[:TARGET]
        temp.setdefault("batches", {})[bkey] = accepted
        save_json(TEMP_PATH, temp)
        print(f"  accepted {len(accepted)}/{len(all_qs)} for {bkey}", flush=True)
        time.sleep(3)

    # Build DB
    db = []
    for bn in range(1, NUM_BATCHES + 1):
        bkey = f"Batch {bn}"
        for q in temp.get("batches", {}).get(bkey, []):
            stem = (q.get("question_ta") or "").strip()
            opts = q.get("options_ta") or []
            db.append({
                "topic": TOPIC_NAME, "batch": bkey,
                "question_ta": stem, "question_en": stem,
                "options": [{"key": chr(65+j), "text_en": opts[j], "text_ta": opts[j]} for j in range(min(4, len(opts)))],
                "correct_option": (q.get("correct_option_letter") or "").strip().upper()[:1],
                "explanation": q.get("explanation_ta") or "", "explanation_ta": q.get("explanation_ta") or "",
                "difficulty": q.get("difficulty") or "Medium", "type": "practice",
                "source_exam": f"Tamilthondu {bkey}", "source_fact": "SM_tamilthondu",
            })
    save_json(DB_PATH, db)
    print(f"\nDONE total={len(db)}")
    from collections import Counter
    for (t, b), n in sorted(Counter((q["topic"], q["batch"]) for q in db).items()):
        print(f"  {b} | {t}: {n}")

if __name__ == "__main__":
    main()
