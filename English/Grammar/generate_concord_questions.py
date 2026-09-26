#!/usr/bin/env python3
"""
Generate Concord practice batches (2 × 25) from concord_notes.json.

Output: English/Grammar/concord_questions_db.json

Usage:
  python3 English/Grammar/generate_concord_questions.py
  python3 English/Grammar/generate_concord_questions.py --batch 1
"""

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
NOTES_PATH = os.path.join(BASE_DIR, "English", "Grammar", "concord_notes.json")
DB_PATH = os.path.join(BASE_DIR, "English", "Grammar", "concord_questions_db.json")

MODEL = "gemini-3.5-flash-lite"
TARGET_PER_BATCH = 25
GENERATE_PER_CALL = 28
RULE_SAMPLE = 45
EXAMPLE_SAMPLE = 50
WORKED_SAMPLE = 30

BATCH_FOCUS = {
    1: (
        "Core Concord rules: basic singular/plural; and → plural vs one-idea singular; "
        "as well as / with / along with (verb agrees with FIRST subject); "
        "either…or / neither…nor (+ nearer subject); each / every / everyone / either of / neither of."
    ),
    2: (
        "Advanced / exam traps: collective nouns (unit vs members); plural-form singular meaning "
        "(news, maths, measles); units of money/time/distance; titles same vs different person; "
        "intervening phrases; always-plural set (people, police, cattle, scissors); error spotting."
    ),
}

SHAPES = """Preferred TNPSC shapes (mix across the batch):
- Choose the correct verb form (is/are, has/have, was/were, go/goes…)
- Fill in the blank with the correct verb
- Spot the error / choose the grammatically correct sentence
- Identify why a verb is singular or plural (rule application)
- Either…or / neither…nor nearer-subject items
- Collective noun agreement
Do NOT copy exercise stems verbatim from notes — rephrase. Option E added later."""


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def format_ground(rules, examples, worked):
    lines = ["RULES:"]
    for i, r in enumerate(rules, 1):
        tag = f" [{r.get('tag')}]" if r.get("tag") else ""
        src = f" ({r.get('source')} p.{r.get('source_page')})" if r.get("source_page") else ""
        lines.append(f"R{i}{tag}{src}: {r.get('rule_en')}")
    lines.append("\nEXAMPLES:")
    for i, e in enumerate(examples, 1):
        lines.append(
            f"E{i}: {e.get('input')} → {e.get('output')} | {e.get('note_en') or ''}"
        )
    lines.append("\nWORKED:")
    for i, w in enumerate(worked, 1):
        lines.append(f"W{i}: {w.get('prompt_en')} ⇒ {w.get('answer_en')}")
    return "\n".join(lines)


def call_gemini(batch_num, focus, rules, examples, worked, exclusion_texts, api_key):
    rules_s = rules if len(rules) <= RULE_SAMPLE else random.sample(rules, RULE_SAMPLE)
    examples_s = (
        examples if len(examples) <= EXAMPLE_SAMPLE else random.sample(examples, EXAMPLE_SAMPLE)
    )
    worked_s = (
        worked if len(worked) <= WORKED_SAMPLE else random.sample(worked, WORKED_SAMPLE)
    )
    ground = format_ground(rules_s, examples_s, worked_s)
    exclusions = ""
    if exclusion_texts:
        exclusions = (
            "\nEXCLUDED STEMS (do not repeat / paraphrase closely):\n"
            + "\n".join(f"- {t}" for t in exclusion_texts[:120])
        )

    prompt = f"""
You are a senior TNPSC General English (SSLC Standard) exam compiler.
Unit I Grammar → Menu: Concord (Subject–Verb Agreement)
Practice Batch {batch_num} focus: {focus}

Generate exactly {GENERATE_PER_CALL} practice MCQs.

GROUND TRUTH (Asan + Grammer.pdf + Govt notes). Answers MUST follow this material:
{ground}
{exclusions}

Rules:
1. Correct answer must be supported by ground truth.
2. English-first (TNPSC General English). Also provide question_ta / options_ta / explanation_ta.
3. Stay mostly within batch focus; light overlap OK.
4. {SHAPES}
5. Each object (JSON array only):
   - question_en, question_ta
   - options_en: exactly 4 strings
   - options_ta: exactly 4 strings
   - answer_en: exact match to one options_en
   - answer_ta: exact match to one options_ta
   - explanation_en, explanation_ta (cite rule briefly)
   - source_note: e.g. "asan p.2 / grammer p.329"
Do NOT include Option E. Return ONLY a JSON array.
"""

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}"
        f":generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    headers = {"Content-Type": "application/json"}
    retries = 6
    attempt = 0
    delay = 12
    rate_limit = 0
    while attempt < retries:
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=210) as response:
                res_json = json.loads(response.read().decode("utf-8"))
                raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                if raw_text.startswith("```"):
                    raw_text = raw_text.split("\n", 1)[1]
                    if raw_text.endswith("```"):
                        raw_text = raw_text.rsplit("\n", 1)[0]
                start_idx = raw_text.find("[")
                if start_idx != -1:
                    count = 0
                    for idx in range(start_idx, len(raw_text)):
                        if raw_text[idx] == "[":
                            count += 1
                        elif raw_text[idx] == "]":
                            count -= 1
                            if count == 0:
                                raw_text = raw_text[start_idx : idx + 1]
                                break
                data = json.loads(raw_text)
                return data if isinstance(data, list) else []
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            if e.code in (429, 503):
                rate_limit += 1
                print(f"    HTTP {e.code}; retry in {delay}s...")
                if rate_limit >= 6:
                    break
                time.sleep(delay)
                delay = min(delay * 2, 90)
            else:
                attempt += 1
                print(f"    HTTP {e.code}: {body[:200]}")
                time.sleep(5)
        except Exception as e:
            attempt += 1
            print(f"    Error: {e}")
            time.sleep(5)
    return []


def letter_for_answer(options_en, answer_en):
    for i, opt in enumerate(options_en):
        if (opt or "").strip() == (answer_en or "").strip():
            return chr(65 + i)
    # fuzzy
    ae = (answer_en or "").strip().lower()
    for i, opt in enumerate(options_en):
        if (opt or "").strip().lower() == ae:
            return chr(65 + i)
    return None


def normalize_item(raw, batch_num):
    q_en = (raw.get("question_en") or "").strip()
    if not q_en:
        return None
    opts_en = [str(x).strip() for x in (raw.get("options_en") or []) if str(x).strip()]
    opts_ta = [str(x).strip() for x in (raw.get("options_ta") or [])]
    if len(opts_en) < 4:
        return None
    opts_en = opts_en[:4]
    while len(opts_ta) < 4:
        opts_ta.append(opts_en[len(opts_ta)])
    opts_ta = opts_ta[:4]
    ans_en = (raw.get("answer_en") or "").strip()
    ans_ta = (raw.get("answer_ta") or "").strip()
    letter = letter_for_answer(opts_en, ans_en)
    if not letter:
        return None
    # Option E
    options = []
    for i, (en, ta) in enumerate(zip(opts_en, opts_ta)):
        options.append({"key": chr(65 + i), "text_en": en, "text_ta": ta or en})
    options.append(
        {
            "key": "E",
            "text_en": "Answer not known",
            "text_ta": "விடை தெரியவில்லை",
        }
    )
    return {
        "subject": "English",
        "unit": "Grammar",
        "menu": "Concord",
        "topic": "Concord",
        "topic_id": "concord",
        "topic_ta": "பொருத்தம்",
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
        "group": "concord",
        "source_note": (raw.get("source_note") or "").strip(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, choices=[1, 2], default=None)
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY not set")

    notes = load_json(NOTES_PATH, None)
    if not notes:
        raise SystemExit(f"Missing notes at {NOTES_PATH} — run extract_concord_notes.py first")

    rules = notes.get("rules") or []
    examples = notes.get("examples") or []
    worked = notes.get("worked_exercises") or []
    print(f"Notes: rules={len(rules)} examples={len(examples)} worked={len(worked)}")

    existing = load_json(DB_PATH, [])
    # keep non-Concord rows if any, drop old Concord for regeneration of selected batches
    batches = [args.batch] if args.batch else [1, 2]
    kept = [
        q
        for q in existing
        if not (
            (q.get("topic") or "") == "Concord"
            and int(re.search(r"(\d+)", q.get("batch") or "0").group(1) or 0) in batches
        )
    ]

    exclusion = [q.get("question_en") for q in kept if q.get("question_en")]
    new_rows = []

    for b in batches:
        focus = BATCH_FOCUS[b]
        print(f"\n=== Generating Concord Batch {b} ===")
        print(f"Focus: {focus[:90]}...")
        raw_list = call_gemini(b, focus, rules, examples, worked, exclusion, api_key)
        print(f"  raw items: {len(raw_list)}")
        batch_rows = []
        seen_stems = {re.sub(r"\s+", " ", t.strip().lower()) for t in exclusion if t}
        for raw in raw_list:
            item = normalize_item(raw, b)
            if not item:
                continue
            stem = re.sub(r"\s+", " ", item["question_en"].strip().lower())
            if stem in seen_stems:
                continue
            seen_stems.add(stem)
            batch_rows.append(item)
            exclusion.append(item["question_en"])
            if len(batch_rows) >= TARGET_PER_BATCH:
                break
        # top-up if short
        tries = 0
        while len(batch_rows) < TARGET_PER_BATCH and tries < 2:
            tries += 1
            print(f"  top-up round {tries} (have {len(batch_rows)})...")
            more = call_gemini(b, focus, rules, examples, worked, exclusion, api_key)
            for raw in more:
                item = normalize_item(raw, b)
                if not item:
                    continue
                stem = re.sub(r"\s+", " ", item["question_en"].strip().lower())
                if stem in seen_stems:
                    continue
                seen_stems.add(stem)
                batch_rows.append(item)
                exclusion.append(item["question_en"])
                if len(batch_rows) >= TARGET_PER_BATCH:
                    break
            time.sleep(2)

        batch_rows = batch_rows[:TARGET_PER_BATCH]
        print(f"  kept: {len(batch_rows)}")
        new_rows.extend(batch_rows)
        time.sleep(2)

    out = kept + new_rows
    save_json(DB_PATH, out)
    print(f"\nWrote {DB_PATH}: total={len(out)} new_concord={len(new_rows)}")


if __name__ == "__main__":
    main()
