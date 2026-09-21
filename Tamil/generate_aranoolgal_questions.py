#!/usr/bin/env python3
"""
Generate PYQ-style MCQs for Unit 7 அறநூல்கள் (6 topics × 30×N batches).

Reads:
  Tamil/unit7_aranoolgal_notes_temp.json  (facts+quotes from 3-round OCR)
  Tamil/unit7_aranoolgal_pyq.json         (style samples)

Writes:
  Tamil/aranoolgal_questions_temp.json    (raw generated)
  Tamil/aranoolgal_questions_db.json      (final deduped, batched)
  Tamil/aranoolgal_topics.json            (topic metadata)

Usage:
  python3 Tamil/generate_aranoolgal_questions.py
  python3 Tamil/generate_aranoolgal_questions.py --resume
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
NOTES_PATH = os.path.join(BASE_DIR, "Tamil", "unit7_aranoolgal_notes_temp.json")
PYQ_PATH = os.path.join(BASE_DIR, "Tamil", "unit7_aranoolgal_pyq.json")
TEMP_PATH = os.path.join(BASE_DIR, "Tamil", "aranoolgal_questions_temp.json")
DB_PATH = os.path.join(BASE_DIR, "Tamil", "aranoolgal_questions_db.json")
TOPICS_PATH = os.path.join(BASE_DIR, "Tamil", "aranoolgal_topics.json")

MODELS = ["gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-3.5-flash"]
TARGET_PER_BATCH = 30

TOPIC_DEFS = [
    {
        "id": "aranoolgal_1",
        "name_ta": "நாலடியார் — நான்மணிக்கடிகை",
        "books": ["naladiyar", "nanmanikadikai"],
        "batches": 3,
    },
    {
        "id": "aranoolgal_2",
        "name_ta": "பழமொழி நானூறு — இன்னா நாற்பது",
        "books": ["pazhamozhi_nanuru", "inna_narpathu"],
        "batches": 3,
    },
    {
        "id": "aranoolgal_3",
        "name_ta": "திரிகடுகம் — ஏலாதி",
        "books": ["thirikadugam", "elathi"],
        "batches": 2,
    },
    {
        "id": "aranoolgal_4",
        "name_ta": "சிறுபஞ்சமூலம் — முதுமொழிக் காஞ்சி",
        "books": ["sirupanchamoolam", "mudhumozhikkanchi"],
        "batches": 3,
    },
    {
        "id": "aranoolgal_5",
        "name_ta": "ஔவையார்",
        "books": ["avvaiyar"],
        "batches": 3,
    },
    {
        "id": "aranoolgal_6",
        "name_ta": "ஆசாரக்கோவை — அறநெறிச்சாரம் — நீதிநெறி விளக்கம்",
        "books": ["asarakkovai", "araneri_saram", "neethineri_vilakkam"],
        "batches": 3,
    },
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
                m = re.search(r'GEMINI_API_KEY[= ]+["\']?([A-Za-z0-9_\-]+)["\']?', line)
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
                    "generationConfig": {
                        "responseMimeType": "application/json",
                        "temperature": 0.25,
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


def build_facts_text(notes: dict, book_ids: list[str]) -> str:
    parts = []
    for bid in book_ids:
        b = notes.get("books", {}).get(bid, {})
        name = b.get("name_ta", bid)
        facts = b.get("facts") or []
        quotes = b.get("quotes") or []
        lines = [f"\n## {name}"]
        for f in facts:
            ft = f.get("fact_ta") if isinstance(f, dict) else str(f)
            if ft:
                lines.append(f"- {ft}")
        if quotes:
            lines.append("### Quotes:")
            for q in quotes[:10]:
                qt = q.get("text_ta") if isinstance(q, dict) else str(q)
                if qt:
                    lines.append(f'- "{qt}"')
        parts.append("\n".join(lines))
    return "\n".join(parts)


def build_pyq_examples(pyqs: list, book_ids: list[str], max_n: int = 6) -> str:
    relevant = []
    for q in pyqs:
        section = norm(q.get("section_ta", ""))
        for bid in book_ids:
            if bid.replace("_", "") in section or section in norm(
                next(
                    (
                        td["name_ta"]
                        for td in TOPIC_DEFS
                        if bid in td["books"]
                    ),
                    "",
                )
            ):
                relevant.append(q)
                break
    if not relevant:
        relevant = pyqs[:4]
    examples = relevant[:max_n]
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


def generate_batch(
    api_key: str,
    topic_name: str,
    batch_label: str,
    facts_text: str,
    pyq_examples: str,
    count: int,
    existing_stems: list[str],
) -> list[dict]:
    avoid = ""
    if existing_stems:
        sample = existing_stems[:40]
        avoid = (
            "\n\nIMPORTANT: You MUST create COMPLETELY DIFFERENT questions from these existing ones. "
            "Do NOT rephrase or reword them. Use DIFFERENT facts entirely:\n"
            + "\n".join(f"- {s[:100]}" for s in sample)
        )

    prompt = f"""You are a TNPSC General Tamil MCQ generator for Unit 7 அறநூல்கள்.
Topic: {topic_name} | Batch: {batch_label}

SM FACTS AND QUOTES:
{facts_text[:14000]}

PYQ STYLE EXAMPLES:
{pyq_examples}

Generate EXACTLY {count} UNIQUE, TNPSC-exam-worthy MCQs in Tamil.

Question types to mix:
- Author / compiler of a book
- Verse count / chapter count
- Alias / alternate name of a book
- Religion of author
- Meaning of book title (e.g. கடிகை = அணிகலன்)
- Famous line attribution ("who said X" or "from which book")
- Structure (முப்பால் / இயல் count)
- English translator
- Match-the-following (occasionally)

Rules:
- All stems + options in Tamil
- Exactly 4 options A–D, one correct
- No two questions with near-identical stems
- Correct answer MUST be verifiable from the facts above
- Include explanation_ta (1-2 lines Tamil reason)
- Tag each Q with book_name_ta (which specific book it tests)
{avoid}

Return JSON only:
{{
  "questions": [
    {{
      "question_ta": "...",
      "options_ta": ["A text","B text","C text","D text"],
      "correct_option_letter": "A|B|C|D",
      "explanation_ta": "short Tamil reason",
      "book_name_ta": "நாலடியார்",
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

    total_gen = 0
    for tdef in TOPIC_DEFS:
        tid = tdef["id"]
        topic_name = tdef["name_ta"]
        num_batches = tdef["batches"]
        book_ids = tdef["books"]

        facts_text = build_facts_text(notes, book_ids)
        pyq_examples = build_pyq_examples(pyqs, book_ids)

        if tid not in temp["topics"]:
            temp["topics"][tid] = {
                "name_ta": topic_name,
                "books": book_ids,
                "batches_target": num_batches,
                "batches": {},
            }
        topic_data = temp["topics"][tid]

        for batch_no in range(1, num_batches + 1):
            batch_label = f"Batch {batch_no}"
            bkey = batch_label

            if args.resume and bkey in topic_data.get("batches", {}) and len(topic_data["batches"][bkey]) >= TARGET_PER_BATCH - 5:
                print(f"SKIP {topic_name} | {batch_label} ({len(topic_data['batches'][bkey])} Q)", flush=True)
                total_gen += len(topic_data["batches"][bkey])
                continue

            print(f"\n=== {topic_name} | {batch_label} (target {TARGET_PER_BATCH}) ===", flush=True)

            existing_stems = []
            for bk, bqs in topic_data.get("batches", {}).items():
                for q in bqs:
                    existing_stems.append(q.get("question_ta", ""))

            all_qs = []
            rounds = 3
            per_round = TARGET_PER_BATCH + 5

            for rnd in range(1, rounds + 1):
                print(f"  round {rnd}/{rounds} requesting ~{per_round}...", flush=True)
                try:
                    batch_qs = generate_batch(
                        api_key, topic_name, batch_label, facts_text,
                        pyq_examples, per_round,
                        existing_stems + [q.get("question_ta", "") for q in all_qs],
                    )
                    print(f"  got {len(batch_qs)} raw", flush=True)
                    all_qs.extend(batch_qs)
                except Exception as e:
                    print(f"  FAIL round {rnd}: {e}", flush=True)
                time.sleep(2)

            # Dedupe + filter
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
            total_gen += len(accepted)
            save_json(TEMP_PATH, temp)
            print(f"  accepted {len(accepted)}/{len(all_qs)} for {batch_label}", flush=True)
            time.sleep(3)

    # Build final DB
    print("\n=== Building final DB ===", flush=True)
    db = []
    topics_meta = []
    for tdef in TOPIC_DEFS:
        tid = tdef["id"]
        topic_name = tdef["name_ta"]
        topic_data = temp["topics"].get(tid, {})
        topics_meta.append({
            "id": tid,
            "name_ta": topic_name,
            "books": tdef["books"],
            "batches": tdef["batches"],
        })

        for batch_no in range(1, tdef["batches"] + 1):
            batch_label = f"Batch {batch_no}"
            batch_qs = topic_data.get("batches", {}).get(batch_label, [])
            for i, q in enumerate(batch_qs):
                stem = (q.get("question_ta") or "").strip()
                opts = q.get("options_ta") or []
                letter = (q.get("correct_option_letter") or "").strip().upper()[:1]
                explanation = (q.get("explanation_ta") or "").strip()
                book_name = (q.get("book_name_ta") or "").strip()
                options = [
                    {"key": chr(65 + j), "text_en": opts[j], "text_ta": opts[j]}
                    for j in range(min(4, len(opts)))
                ]
                db.append({
                    "topic": topic_name,
                    "batch": batch_label,
                    "question_ta": stem,
                    "question_en": stem,
                    "options": options,
                    "correct_option": letter,
                    "explanation": explanation,
                    "explanation_ta": explanation,
                    "difficulty": q.get("difficulty") or "Medium",
                    "type": "practice",
                    "source_exam": f"Aranoolgal {tid} {batch_label}",
                    "source_fact": f"SM_aranoolgal_{book_name}",
                    "book_name_ta": book_name,
                })

    save_json(DB_PATH, db)
    save_json(TOPICS_PATH, {"unit": "Aranoolgal", "topics": topics_meta})
    print(f"\nDONE total={len(db)} topics={len(topics_meta)}")
    from collections import Counter
    c = Counter((q["topic"], q["batch"]) for q in db)
    for (t, b), n in sorted(c.items()):
        print(f"  {b} | {t[:50]}: {n}")


if __name__ == "__main__":
    main()
