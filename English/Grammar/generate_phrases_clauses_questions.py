#!/usr/bin/env python3
"""Generate Phrases & Clauses practice batches (1 topic × 4 × 25, mixed types)."""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import time
import urllib.error
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NOTES_PATH = os.path.join(BASE_DIR, "English", "Grammar", "phrases_clauses_notes.json")
DB_PATH = os.path.join(BASE_DIR, "English", "Grammar", "phrases_clauses_questions_db.json")

MODEL = "gemini-3.5-flash-lite"
TARGET_PER_BATCH = 25
GENERATE_PER_CALL = 28
RULE_SAMPLE = 45
EXAMPLE_SAMPLE = 50
WORKED_SAMPLE = 35

BATCH_FOCUS = {
    1: (
        "Mixed batch 1: phrase vs clause; finite verb test; identify whether the "
        "underlined group is a phrase or a clause; main vs subordinate clause basics."
    ),
    2: (
        "Mixed batch 2: noun phrase, adjective phrase, adverb phrase; classify "
        "underlined groups by phrase type; function in sentence."
    ),
    3: (
        "Mixed batch 3: noun clause, adjective clause, adverb clause; independent "
        "vs dependent clause; classify clause type."
    ),
    4: (
        "Mixed batch 4: mixed identification & classification; spot phrase/clause "
        "type in full sentences; exam-style traps; all types in each set."
    ),
}

SHAPES = """TNPSC shapes (mix ALL phrase/clause types within each batch):
- Identify phrase or clause in the sentence
- Classify as noun/adjective/adverb phrase
- Classify as noun/adjective/adverb clause
- Main (independent) vs subordinate (dependent) clause
- Which underlined part is a/an ... ?
Rephrase stems; do not copy verbatim from notes.
Do NOT ask to combine or transform sentences (that is Synthesis)."""


def load_json(path, default=None):
    if not os.path.exists(path):
        return default if default is not None else {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def format_ground(rules, examples, worked):
    lines = ["RULES:"]
    for i, r in enumerate(rules, 1):
        tag = f" [{r.get('pc_tag')}]" if r.get("pc_tag") else ""
        src = f" p.{r.get('source_page')}" if r.get("source_page") else ""
        lines.append(f"R{i}{tag}{src}: {r.get('rule_en')}")
    lines.append("\nEXAMPLES:")
    for i, e in enumerate(examples, 1):
        lines.append(
            f"E{i}: {e.get('input_en')} → {e.get('output_en')} | {e.get('note_en') or ''}"
        )
    lines.append("\nWORKED:")
    for i, w in enumerate(worked, 1):
        lines.append(f"W{i}: {w.get('prompt_en')} ⇒ {w.get('answer_en')}")
    return "\n".join(lines)


def call_gemini(batch_num, focus, rules, examples, worked, exclusions, api_key):
    rules_s = rules if len(rules) <= RULE_SAMPLE else random.sample(rules, RULE_SAMPLE)
    examples_s = examples if len(examples) <= EXAMPLE_SAMPLE else random.sample(examples, EXAMPLE_SAMPLE)
    worked_s = worked if len(worked) <= WORKED_SAMPLE else random.sample(worked, WORKED_SAMPLE)
    ground = format_ground(rules_s, examples_s, worked_s)
    excl = ""
    if exclusions:
        excl = "\nEXCLUDED STEMS:\n" + "\n".join(f"- {t}" for t in exclusions[:100])

    prompt = f"""
Senior TNPSC General English compiler.
Unit I Grammar → Phrases & Clauses (mixed identification) — Batch {batch_num}
Batch focus: {focus}
{excl}

Generate exactly {GENERATE_PER_CALL} MCQs supported ONLY by:
{ground}

Rules:
1. Each batch must MIX different phrase/clause types — not all one type.
2. Answers must match Grammer.pdf SSLC phrase/clause rules.
3. English-first + question_ta, options_ta, explanation_ta.
4. {SHAPES}
5. JSON array: question_en, question_ta, options_en[4], options_ta[4], answer_en, answer_ta, explanation_en, explanation_ta, source_note
No Option E. Return ONLY JSON array.
"""
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}"
        f":generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    delay = 12
    for _ in range(6):
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=210) as response:
                raw = json.loads(response.read().decode("utf-8"))["candidates"][0]["content"]["parts"][0]["text"].strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1]
                if raw.endswith("```"):
                    raw = raw.rsplit("\n", 1)[0]
            start = raw.find("[")
            if start >= 0:
                depth = 0
                for i, ch in enumerate(raw[start:], start):
                    if ch == "[":
                        depth += 1
                    elif ch == "]":
                        depth -= 1
                        if depth == 0:
                            raw = raw[start : i + 1]
                            break
            data = json.loads(raw)
            return data if isinstance(data, list) else []
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                time.sleep(delay)
                delay = min(delay * 2, 90)
            else:
                time.sleep(5)
        except Exception:
            time.sleep(5)
    return []


def letter_for_answer(options_en, answer_en):
    ae = (answer_en or "").strip()
    for i, opt in enumerate(options_en):
        if (opt or "").strip() == ae:
            return chr(65 + i)
    ae_l = ae.lower()
    for i, opt in enumerate(options_en):
        if (opt or "").strip().lower() == ae_l:
            return chr(65 + i)
    return None


def normalize_item(raw, batch_num):
    q_en = (raw.get("question_en") or "").strip()
    if not q_en:
        return None
    opts_en = [str(x).strip() for x in (raw.get("options_en") or []) if str(x).strip()][:4]
    opts_ta = [str(x).strip() for x in (raw.get("options_ta") or [])]
    if len(opts_en) < 4:
        return None
    while len(opts_ta) < 4:
        opts_ta.append(opts_en[len(opts_ta)])
    opts_ta = opts_ta[:4]
    letter = letter_for_answer(opts_en, raw.get("answer_en"))
    if not letter:
        return None
    options = []
    for i, (en, ta) in enumerate(zip(opts_en, opts_ta)):
        options.append({"key": chr(65 + i), "text_en": en, "text_ta": ta or en})
    options.append({"key": "E", "text_en": "Answer not known", "text_ta": "விடை தெரியவில்லை"})
    return {
        "subject": "English",
        "unit": "Grammar",
        "menu": "Phrases & Clauses",
        "topic": "Phrases & Clauses",
        "topic_id": "phrases_clauses",
        "topic_ta": "சொற்றொடர்கள் & உட்கூறு வாக்கியங்கள்",
        "source_exam": f"Practice Batch {batch_num}",
        "difficulty": raw.get("difficulty") or "Medium",
        "question_en": q_en,
        "question_ta": (raw.get("question_ta") or q_en).strip(),
        "options": options,
        "correct_option": letter,
        "explanation": (raw.get("explanation_en") or "").strip(),
        "explanation_ta": (raw.get("explanation_ta") or "").strip(),
        "type": "practice",
        "batch": f"Batch {batch_num}",
        "group": "phrases_clauses",
        "source_note": (raw.get("source_note") or "").strip(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, choices=[1, 2, 3, 4])
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY not set")

    notes = load_json(NOTES_PATH)
    if not notes.get("rules") and not notes.get("examples"):
        raise SystemExit(f"Run extract_phrases_clauses_notes.py first — missing {NOTES_PATH}")

    rules = notes.get("rules") or []
    examples = notes.get("examples") or []
    worked = notes.get("worked_exercises") or []
    print(f"Notes: rules={len(rules)} examples={len(examples)} worked={len(worked)}")

    batches = [args.batch] if args.batch else [1, 2, 3, 4]
    existing = load_json(DB_PATH, [])
    kept = [
        q
        for q in existing
        if not (
            (q.get("topic") or "") == "Phrases & Clauses"
            and int(re.search(r"(\d+)", q.get("batch") or "0").group(1) or 0) in batches
        )
    ]
    exclusion = [q.get("question_en") for q in kept if q.get("question_en")]
    new_rows = []

    for b in batches:
        focus = BATCH_FOCUS[b]
        print(f"\n=== Phrases & Clauses Batch {b} (mixed) ===")
        batch_rows = []
        seen = {re.sub(r"\s+", " ", t.strip().lower()) for t in exclusion if t}
        for round_i in range(3):
            if len(batch_rows) >= TARGET_PER_BATCH:
                break
            raw_list = call_gemini(b, focus, rules, examples, worked, exclusion, api_key)
            print(f"  round {round_i+1}: raw={len(raw_list)} kept={len(batch_rows)}")
            for raw in raw_list:
                item = normalize_item(raw, b)
                if not item:
                    continue
                stem = re.sub(r"\s+", " ", item["question_en"].strip().lower())
                if stem in seen:
                    continue
                seen.add(stem)
                batch_rows.append(item)
                exclusion.append(item["question_en"])
                if len(batch_rows) >= TARGET_PER_BATCH:
                    break
            time.sleep(2)
        print(f"  final: {len(batch_rows)}")
        new_rows.extend(batch_rows[:TARGET_PER_BATCH])

    out = kept + new_rows
    save_json(DB_PATH, out)
    from collections import Counter

    c = Counter(q.get("batch") for q in out if q.get("topic") == "Phrases & Clauses")
    print(f"\nWrote {len(out)} Q → {DB_PATH}")
    for k in sorted(c):
        print(f"  {k}: {c[k]}")


if __name__ == "__main__":
    main()
