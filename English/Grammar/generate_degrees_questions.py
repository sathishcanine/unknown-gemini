#!/usr/bin/env python3
"""Generate Degrees of Comparison practice batches (6 topics × 2 × 25)."""

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
NOTES_PATH = os.path.join(BASE_DIR, "English", "Grammar", "degrees_notes.json")
TOPICS_PATH = os.path.join(BASE_DIR, "English", "Grammar", "degrees_topics.json")
DB_PATH = os.path.join(BASE_DIR, "English", "Grammar", "degrees_questions_db.json")

MODEL = "gemini-3.5-flash-lite"
TARGET_PER_BATCH = 25
GENERATE_PER_CALL = 28
RULE_SAMPLE = 35
EXAMPLE_SAMPLE = 40
WORKED_SAMPLE = 30

BATCH_FOCUS = {
    1: "Straightforward identify/fill/choose correct degree form; clear rules from notes.",
    2: "Exam traps: irregular forms, article the, elder/older, Type II B very few, error spotting (more better).",
}

SHAPES = """TNPSC shapes (mix):
- Choose the correct degree of comparison
- Fill in the blank with comparative/superlative form
- Select the correctly transformed sentence (positive/comparative/superlative)
- Rewrite without changing meaning (choose best option)
- Spot/correct the error in degree usage
Rephrase stems; do not copy verbatim from notes."""


def load_json(path, default=None):
    if not os.path.exists(path):
        return default if default is not None else {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def notes_for_topic(notes: dict, topic_id: str):
    rules = [
        r
        for r in notes.get("rules") or []
        if (r.get("degree_topic") or "") in (topic_id, "overview")
    ]
    examples = [
        e
        for e in notes.get("examples") or []
        if (e.get("degree_topic") or "") in (topic_id, "overview")
    ]
    worked = [
        w
        for w in notes.get("worked_exercises") or []
        if (w.get("degree_topic") or "") in (topic_id, "overview")
    ]
    if not rules and not examples:
        rules = notes.get("rules") or []
        examples = notes.get("examples") or []
        worked = notes.get("worked_exercises") or []
    return rules, examples, worked


def format_ground(rules, examples, worked):
    lines = ["RULES:"]
    for i, r in enumerate(rules, 1):
        src = f" ({r.get('source')} p.{r.get('source_page')})" if r.get("source_page") else ""
        lines.append(f"R{i}{src}: {r.get('rule_en')}")
    lines.append("\nEXAMPLES:")
    for i, e in enumerate(examples, 1):
        lines.append(
            f"E{i}: {e.get('input_en') or ''} → {e.get('output_en') or ''} | {e.get('note_en') or ''}"
        )
    lines.append("\nWORKED:")
    for i, w in enumerate(worked, 1):
        lines.append(f"W{i}: {w.get('prompt_en')} ⇒ {w.get('answer_en')}")
    return "\n".join(lines)


def call_gemini(topic, batch_num, focus, topic_focus, rules, examples, worked, exclusions, api_key):
    rules_s = rules if len(rules) <= RULE_SAMPLE else random.sample(rules, RULE_SAMPLE)
    examples_s = examples if len(examples) <= EXAMPLE_SAMPLE else random.sample(examples, EXAMPLE_SAMPLE)
    worked_s = worked if len(worked) <= WORKED_SAMPLE else random.sample(worked, WORKED_SAMPLE)
    ground = format_ground(rules_s, examples_s, worked_s)
    excl = ""
    if exclusions:
        excl = "\nEXCLUDED STEMS:\n" + "\n".join(f"- {t}" for t in exclusions[:100])

    prompt = f"""
Senior TNPSC General English compiler.
Unit I Grammar → Degrees of Comparison → {topic['name_en']} ({topic['id']})
Batch {batch_num}: {focus}
Topic focus: {topic_focus}
{excl}

Generate exactly {GENERATE_PER_CALL} MCQs supported ONLY by:
{ground}

Rules:
1. Answers must match notes / standard SSLC degree-of-comparison rules.
2. English-first + question_ta, options_ta, explanation_ta.
3. {SHAPES}
4. For this topic batch, most questions must test "{topic['name_en']}" rules.
5. JSON array objects with: question_en, question_ta, options_en[4], options_ta[4], answer_en, answer_ta, explanation_en, explanation_ta, source_note
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


def normalize_item(raw, topic, batch_num):
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
        "menu": "Degrees of Comparison",
        "topic": topic["name_en"],
        "topic_id": topic["id"],
        "topic_ta": topic.get("name_ta") or topic["name_en"],
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
        "group": topic["id"],
        "source_note": (raw.get("source_note") or "").strip(),
    }


def generate_batch(topic, batch_num, notes, exclusion, api_key):
    rules, examples, worked = notes_for_topic(notes, topic["id"])
    focus = BATCH_FOCUS[batch_num]
    topic_focus = topic.get("focus") or topic["name_en"]
    print(
        f"\n=== {topic['name_en']} Batch {batch_num} "
        f"(notes r/e/w={len(rules)}/{len(examples)}/{len(worked)}) ==="
    )
    rows = []
    seen = {re.sub(r"\s+", " ", t.strip().lower()) for t in exclusion if t}
    for round_i in range(3):
        if len(rows) >= TARGET_PER_BATCH:
            break
        raw_list = call_gemini(
            topic, batch_num, focus, topic_focus, rules, examples, worked, exclusion, api_key
        )
        print(f"  round {round_i+1}: raw={len(raw_list)} kept={len(rows)}")
        for raw in raw_list:
            item = normalize_item(raw, topic, batch_num)
            if not item:
                continue
            stem = re.sub(r"\s+", " ", item["question_en"].strip().lower())
            if stem in seen:
                continue
            seen.add(stem)
            rows.append(item)
            exclusion.append(item["question_en"])
            if len(rows) >= TARGET_PER_BATCH:
                break
        time.sleep(2)
    print(f"  final: {len(rows)}")
    return rows[:TARGET_PER_BATCH]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic")
    parser.add_argument("--batch", type=int, choices=[1, 2])
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY not set")

    notes = load_json(NOTES_PATH)
    if not notes.get("rules") and not notes.get("examples"):
        raise SystemExit(f"Run extract_degrees_notes.py first — missing {NOTES_PATH}")

    topics_cfg = load_json(TOPICS_PATH, {})
    topics = topics_cfg.get("topics") or []
    if args.topic:
        topics = [t for t in topics if t.get("id") == args.topic]
    if not topics:
        raise SystemExit("No topics configured")

    existing = load_json(DB_PATH, [])
    if not args.topic and not args.batch:
        existing = [q for q in existing if q.get("menu") != "Degrees of Comparison"]
    out: list = list(existing)
    exclusion = [q.get("question_en") for q in out if q.get("question_en")]

    for topic in topics:
        batches = [args.batch] if args.batch else [1, 2]
        for b in batches:
            out = [
                q
                for q in out
                if not (
                    q.get("topic_id") == topic["id"]
                    and (q.get("batch") or "") == f"Batch {b}"
                )
            ]
            exclusion = [q.get("question_en") for q in out if q.get("question_en")]
            rows = generate_batch(topic, b, notes, exclusion, api_key)
            out.extend(rows)
            exclusion.extend(q.get("question_en") for q in rows if q.get("question_en"))

    save_json(DB_PATH, out)
    from collections import Counter

    c = Counter((q.get("topic_id"), q.get("batch")) for q in out)
    print(f"\nWrote {len(out)} Q → {DB_PATH}")
    for k in sorted(c):
        print(f"  {k[0]:28} {k[1]}: {c[k]}")


if __name__ == "__main__":
    main()
