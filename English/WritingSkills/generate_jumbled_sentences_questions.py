#!/usr/bin/env python3
"""Generate Jumbled Sentences practice batches (1 topic × 4 × 25, Option A)."""

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
NOTES_PATH = os.path.join(BASE_DIR, "English", "WritingSkills", "jumbled_sentences_notes.json")
DB_PATH = os.path.join(BASE_DIR, "English", "WritingSkills", "jumbled_sentences_questions_db.json")

MODEL = "gemini-3.5-flash-lite"
TARGET_PER_BATCH = 25
GENERATE_PER_CALL = 28
RULE_SAMPLE = 20
EXAMPLE_SAMPLE = 50
WORKED_SAMPLE = 40

TOPIC = "Jumbled Sentences"

BATCH_FOCUS = {
    1: "Word jumble → correct sentence: rearrange given words/phrases; choose correct sentence order.",
    2: "Sentence jumble → paragraph: choose the correct order of numbered/lettered sentences (coherence).",
    3: "Process / sequence: steps of a process in correct order; opening/closing sentence identification.",
    4: "Exam traps: near-miss orderings, subject-first tips, connector clues (then/finally/however); mixed word+sentence jumbles.",
}

SHAPES = """TNPSC CCSE shapes (mix — rephrase; do NOT copy verbatim from notes):
- Rearrange the jumbled words to form a meaningful sentence (choose correct option)
- Choose the correct order of the following sentences
- The first / last sentence of the paragraph is …
- Arrange the following in the proper sequence (process)
- Which is the coherent order of sentences A–D / 1–5?
STRICT: Jumbled words, jumbled sentences, process sequencing ONLY.
NO letter writing, vocabulary synonym/antonym, acronyms, grammar conjugation.
English only. Options: one clear correct order/sentence + 3 plausible distractors."""

OFF_TOPIC_RE = re.compile(
    r"\b("
    r"acronym|full form|expansion|stands for|abbreviation|"
    r"formal letter|informal letter|salutation|memo|"
    r"synonym|antonym|RAM|ROM|URL|NASA"
    r")\b",
    re.I,
)


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
        lines.append(f"R{i}: {r.get('rule_en')} [{r.get('js_tag')}]")
    lines.append("\nJUMBLE EXAMPLES:")
    for i, e in enumerate(examples, 1):
        lines.append(
            f"E{i}: [{e.get('kind_en') or e.get('js_tag')}] "
            f"{(e.get('prompt_en') or '')[:220]} ⇒ {(e.get('answer_en') or '')[:180]} "
            f"{(e.get('note_en') or '')[:80]}"
        )
    lines.append("\nWORKED:")
    for i, w in enumerate(worked, 1):
        opts = w.get("options_en") or []
        opt_s = " | ".join(str(o)[:60] for o in opts[:4]) if opts else ""
        lines.append(
            f"W{i}: {(w.get('prompt_en') or '')[:200]} ⇒ {w.get('answer_en')}"
            + (f" :: {opt_s}" if opt_s else "")
        )
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
Unit III Writing Skills → Jumbled Sentences — Batch {batch_num}
Batch focus: {focus}
{excl}

Generate exactly {GENERATE_PER_CALL} MCQs supported ONLY by these notes:
{ground}

Rules:
1. Correct answer MUST match a note example/worked answer (or clearly equivalent coherent order).
2. English only — NO Tamil. Set question_ta = question_en, options_ta = options_en, explanation_ta = explanation_en.
3. {SHAPES}
4. Prefer short 4–7 word jumbles or 4–6 sentence orderings (TNPSC style). Options may be full sentences OR order codes like 2-4-1-3 / BDAC.
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


def is_off_topic(q_en):
    return bool(OFF_TOPIC_RE.search(q_en or ""))


def normalize_item(raw, batch_num):
    q_en = (raw.get("question_en") or "").strip()
    if not q_en or is_off_topic(q_en):
        return None
    opts_en = [str(x).strip() for x in (raw.get("options_en") or []) if str(x).strip()][:4]
    if len(opts_en) < 4:
        return None
    if len(set(o.lower() for o in opts_en)) < 4:
        return None
    letter = letter_for_answer(opts_en, raw.get("answer_en"))
    if not letter:
        return None
    explanation = (raw.get("explanation_en") or "").strip()
    options = []
    for i, en in enumerate(opts_en):
        options.append({"key": chr(65 + i), "text_en": en, "text_ta": en})
    options.append({"key": "E", "text_en": "Answer not known", "text_ta": "Answer not known"})
    return {
        "subject": "English",
        "unit": "Writing Skills",
        "menu": "Jumbled Sentences",
        "topic": TOPIC,
        "topic_id": "jumbled_sentences",
        "topic_ta": TOPIC,
        "source_exam": f"Practice Batch {batch_num}",
        "difficulty": raw.get("difficulty") or "Medium",
        "question_en": q_en,
        "question_ta": q_en,
        "options": options,
        "correct_option": letter,
        "explanation": explanation,
        "explanation_ta": explanation,
        "type": "practice",
        "batch": f"Batch {batch_num}",
        "group": "jumbled_sentences",
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
    if not notes.get("examples") and not notes.get("rules") and not notes.get("worked_exercises"):
        raise SystemExit(f"Run extract_jumbled_sentences_notes.py first — missing {NOTES_PATH}")

    rules = notes.get("rules") or []
    examples = notes.get("examples") or []
    worked = notes.get("worked_exercises") or []
    print(f"Notes: rules={len(rules)} examples={len(examples)} worked={len(worked)}")

    batches = [args.batch] if args.batch else [1, 2, 3, 4]
    existing = load_json(DB_PATH, [])
    if not isinstance(existing, list):
        existing = []
    kept = [
        q
        for q in existing
        if not (
            (q.get("topic") or "") == TOPIC
            and int(re.search(r"(\d+)", q.get("batch") or "0").group(1) or 0) in batches
        )
    ]
    exclusion = [q.get("question_en") for q in kept if q.get("question_en")]
    new_rows = []

    for b in batches:
        focus = BATCH_FOCUS[b]
        print(f"\n=== {TOPIC} Batch {b} ===")
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

    c = Counter(q.get("batch") for q in out if q.get("topic") == TOPIC)
    print(f"\nWrote {len(out)} Q → {DB_PATH}")
    for k in sorted(c):
        print(f"  {k}: {c[k]}")


if __name__ == "__main__":
    main()
