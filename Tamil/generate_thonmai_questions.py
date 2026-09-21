#!/usr/bin/env python3
"""
Generate PYQ-style MCQs for Unit 7 — தமிழின் தொன்மை, சிறப்பு, திராவிட மொழிகள்.

Topics:
  தமிழின் தொன்மை         — 3 batches × 30
  தமிழின் சிறப்பு         — 3 batches × 30
  திராவிட மொழிகள்        — 2 batches × 30

Usage:
  python3 Tamil/generate_thonmai_questions.py
  python3 Tamil/generate_thonmai_questions.py --resume
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from collections import defaultdict
from difflib import SequenceMatcher

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTES_PATH = os.path.join(BASE_DIR, "Tamil", "unit7_thonmai_notes_temp.json")
PYQ_PATH = os.path.join(BASE_DIR, "Tamil", "unit7_tamilin_thonmai_pyq.json")
TEMP_PATH = os.path.join(BASE_DIR, "Tamil", "thonmai_questions_temp.json")
DB_PATH = os.path.join(BASE_DIR, "Tamil", "thonmai_questions_db.json")

MODELS = ["gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-3.5-flash"]
TARGET_PER_BATCH = 30

TOPIC_DEFS = [
    {"id": "thonmai", "name_ta": "தமிழின் தொன்மை", "batches": 3},
    {"id": "sirappu", "name_ta": "தமிழின் சிறப்பு", "batches": 3},
    {"id": "dravidian", "name_ta": "திராவிட மொழிகள்", "batches": 2},
]


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


def call_gemini(api_key: str, prompt: str) -> str:
    last = None
    for m in MODELS:
        delay = 6
        for _ in range(4):
            try:
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"responseMimeType": "application/json", "temperature": 0.25},
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
    raise ValueError("parse fail")


def norm(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").lower())


def build_facts_text(notes: dict, subtopic_id: str) -> str:
    st = notes.get("subtopics", {}).get(subtopic_id, {})
    lines = [f"## {st.get('name_ta', subtopic_id)}"]
    for f in (st.get("facts") or [])[:500]:
        ft = f.get("fact_ta") if isinstance(f, dict) else str(f)
        if ft:
            lines.append(f"- {ft}")
    quotes = st.get("quotes") or []
    if quotes:
        lines.append("### Quotes:")
        for q in quotes[:30]:
            qt = q.get("text_ta") if isinstance(q, dict) else str(q)
            speaker = q.get("speaker", "") if isinstance(q, dict) else ""
            if qt:
                lines.append(f'- "{qt}" — {speaker}')
    return "\n".join(lines)


def build_pyq_examples(pyqs: list, max_n: int = 6) -> str:
    examples = pyqs[:max_n]
    lines = []
    for q in examples:
        opts = q.get("options_ta") or []
        lines.append(
            f"Q: {q.get('question_ta')}\n"
            f"A) {opts[0] if len(opts)>0 else ''} B) {opts[1] if len(opts)>1 else ''} "
            f"C) {opts[2] if len(opts)>2 else ''} D) {opts[3] if len(opts)>3 else ''}\n"
            f"Answer: {q.get('correct_option_letter')}\n"
        )
    return "\n".join(lines)


def generate_batch(api_key, topic_name, batch_label, facts_text, pyq_examples, count, existing_stems):
    avoid = ""
    if existing_stems:
        sample = existing_stems[:40]
        avoid = (
            "\n\nIMPORTANT: Create COMPLETELY DIFFERENT questions from these existing ones. "
            "Use DIFFERENT facts entirely:\n"
            + "\n".join(f"- {s[:100]}" for s in sample)
        )

    prompt = f"""You are a TNPSC General Tamil MCQ generator.
Topic: {topic_name} | Batch: {batch_label}

SM FACTS AND QUOTES:
{facts_text[:14000]}

PYQ STYLE EXAMPLES:
{pyq_examples}

Generate EXACTLY {count} UNIQUE, TNPSC-exam-worthy MCQs in Tamil.

Question types to mix:
- Who said / who wrote about Tamil
- Historical dates and periods
- Tamil spoken countries / statistics
- Scholar names and their contributions
- Language classification and families
- Trade goods and ancient ports
- Ancient literature references
- Comparison between Dravidian languages
- Inscriptions and archaeological evidence

Rules:
- All stems + options in Tamil
- Exactly 4 options A–D, one correct
- No two questions with near-identical stems
- Correct answer MUST be verifiable from the facts above
- Include explanation_ta (1-2 lines Tamil reason)
- Tag difficulty: Easy/Medium/Hard
{avoid}

Return JSON only:
{{
  "questions": [
    {{
      "question_ta": "...",
      "options_ta": ["A text","B text","C text","D text"],
      "correct_option_letter": "A|B|C|D",
      "explanation_ta": "short Tamil reason",
      "difficulty": "Easy|Medium|Hard"
    }}
  ]
}}
"""
    raw = call_gemini(api_key, prompt)
    obj = parse_json(raw)
    qs = obj.get("questions") if isinstance(obj, dict) else obj
    return qs if isinstance(qs, list) else []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    api_key = get_api_key()
    notes = load_json(NOTES_PATH)
    pyqs = load_json(PYQ_PATH, [])
    temp = load_json(TEMP_PATH, {"topics": {}}) if args.resume else {"topics": {}}
    pyq_examples = build_pyq_examples(pyqs)

    for tdef in TOPIC_DEFS:
        tid = tdef["id"]
        topic_name = tdef["name_ta"]
        num_batches = tdef["batches"]

        facts_text = build_facts_text(notes, tid)

        if tid not in temp["topics"]:
            temp["topics"][tid] = {"name_ta": topic_name, "batches": {}}
        topic_data = temp["topics"][tid]

        for batch_no in range(1, num_batches + 1):
            bkey = f"Batch {batch_no}"

            if args.resume and bkey in topic_data.get("batches", {}) and len(topic_data["batches"][bkey]) >= TARGET_PER_BATCH - 5:
                print(f"SKIP {topic_name} | {bkey} ({len(topic_data['batches'][bkey])} Q)", flush=True)
                continue

            print(f"\n=== {topic_name} | {bkey} (target {TARGET_PER_BATCH}) ===", flush=True)

            existing_stems = []
            for bk, bqs in topic_data.get("batches", {}).items():
                for q in bqs:
                    existing_stems.append(q.get("question_ta", ""))

            all_qs = []
            for rnd in range(1, 4):
                print(f"  round {rnd}/3 requesting ~{TARGET_PER_BATCH + 5}...", flush=True)
                try:
                    batch_qs = generate_batch(
                        api_key, topic_name, bkey, facts_text, pyq_examples,
                        TARGET_PER_BATCH + 5,
                        existing_stems + [q.get("question_ta", "") for q in all_qs],
                    )
                    print(f"  got {len(batch_qs)} raw", flush=True)
                    all_qs.extend(batch_qs)
                except Exception as e:
                    print(f"  FAIL round {rnd}: {e}", flush=True)
                time.sleep(2)

            accepted = []
            seen_norms = set()
            for q in all_qs:
                stem = (q.get("question_ta") or "").strip()
                opts = q.get("options_ta") or []
                letter = (q.get("correct_option_letter") or "").strip().upper()[:1]
                if not stem or len(opts) < 4 or letter not in "ABCD":
                    continue
                sn = norm(stem)
                if sn in seen_norms:
                    continue
                if any(SequenceMatcher(None, sn, norm(ex)).ratio() >= 0.92 for ex in existing_stems):
                    continue
                if any(SequenceMatcher(None, sn, s).ratio() >= 0.92 for s in seen_norms):
                    continue
                opt_norms = [norm(o) for o in opts[:4]]
                if len(set(opt_norms)) < 4:
                    continue
                seen_norms.add(sn)
                accepted.append(q)

            accepted = accepted[:TARGET_PER_BATCH]
            topic_data.setdefault("batches", {})[bkey] = accepted
            save_json(TEMP_PATH, temp)
            print(f"  accepted {len(accepted)}/{len(all_qs)} for {bkey}", flush=True)
            time.sleep(3)

    # Build final DB
    print("\n=== Building final DB ===", flush=True)
    db = []
    for tdef in TOPIC_DEFS:
        tid = tdef["id"]
        topic_name = tdef["name_ta"]
        topic_data = temp["topics"].get(tid, {})

        for batch_no in range(1, tdef["batches"] + 1):
            bkey = f"Batch {batch_no}"
            for q in topic_data.get("batches", {}).get(bkey, []):
                stem = (q.get("question_ta") or "").strip()
                opts = q.get("options_ta") or []
                letter = (q.get("correct_option_letter") or "").strip().upper()[:1]
                explanation = (q.get("explanation_ta") or "").strip()
                options = [
                    {"key": chr(65 + j), "text_en": opts[j], "text_ta": opts[j]}
                    for j in range(min(4, len(opts)))
                ]
                db.append({
                    "topic": topic_name,
                    "batch": bkey,
                    "question_ta": stem,
                    "question_en": stem,
                    "options": options,
                    "correct_option": letter,
                    "explanation": explanation,
                    "explanation_ta": explanation,
                    "difficulty": q.get("difficulty") or "Medium",
                    "type": "practice",
                    "source_exam": f"Thonmai {tid} {bkey}",
                    "source_fact": f"SM_thonmai_{tid}",
                })

    save_json(DB_PATH, db)
    print(f"\nDONE total={len(db)}")
    from collections import Counter
    c = Counter((q["topic"], q["batch"]) for q in db)
    for (t, b), n in sorted(c.items()):
        print(f"  {b} | {t}: {n}")


if __name__ == "__main__":
    main()
