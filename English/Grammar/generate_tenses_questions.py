#!/usr/bin/env python3
"""Generate Tenses practice batches from tenses_notes.json (25 Q each).

All 12 forms get Batch 1. A second batch is generated where notes are strong enough.

Usage:
  python3 English/Grammar/generate_tenses_questions.py
  python3 English/Grammar/generate_tenses_questions.py --topic simple_present --batch 1
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
NOTES_PATH = os.path.join(BASE_DIR, "English", "Grammar", "tenses_notes.json")
DB_PATH = os.path.join(BASE_DIR, "English", "Grammar", "tenses_questions_db.json")

MODEL = "gemini-3.5-flash-lite"
TARGET_PER_BATCH = 25
GENERATE_PER_CALL = 28
RULE_SAMPLE = 40
EXAMPLE_SAMPLE = 40
WORKED_SAMPLE = 30

TOPICS = [
    {
        "id": "simple_present",
        "name_en": "Simple Present",
        "name_ta": "எளிய நிகழ்காலம்",
        "batches": 2,
        "nearby": "Present Continuous / Present Perfect",
    },
    {
        "id": "present_continuous",
        "name_en": "Present Continuous",
        "name_ta": "நிகழ்கால தொடர்ச்சி",
        "batches": 2,
        "nearby": "Simple Present / Present Perfect Continuous",
    },
    {
        "id": "present_perfect",
        "name_en": "Present Perfect",
        "name_ta": "நிகழ்கால நிறைவு",
        "batches": 2,
        "nearby": "Simple Past / Present Perfect Continuous",
    },
    {
        "id": "present_perfect_continuous",
        "name_en": "Present Perfect Continuous",
        "name_ta": "நிகழ்கால நிறைவுத் தொடர்ச்சி",
        "batches": 2,
        "nearby": "Present Perfect / Present Continuous",
    },
    {
        "id": "simple_past",
        "name_en": "Simple Past",
        "name_ta": "எளிய இறந்தகாலம்",
        "batches": 2,
        "nearby": "Present Perfect / Past Continuous",
    },
    {
        "id": "past_continuous",
        "name_en": "Past Continuous",
        "name_ta": "இறந்தகால தொடர்ச்சி",
        "batches": 2,
        "nearby": "Simple Past / Past Perfect",
    },
    {
        "id": "past_perfect",
        "name_en": "Past Perfect",
        "name_ta": "இறந்தகால நிறைவு",
        "batches": 2,
        "nearby": "Simple Past / Past Perfect Continuous",
    },
    {
        "id": "past_perfect_continuous",
        "name_en": "Past Perfect Continuous",
        "name_ta": "இறந்தகால நிறைவுத் தொடர்ச்சி",
        "batches": 2,
        "nearby": "Past Perfect / Past Continuous",
    },
    {
        "id": "simple_future",
        "name_en": "Simple Future",
        "name_ta": "எளிய எதிர்காலம்",
        "batches": 2,
        "nearby": "Future Continuous / going to / present for future",
    },
    {
        "id": "future_continuous",
        "name_en": "Future Continuous",
        "name_ta": "எதிர்கால தொடர்ச்சி",
        "batches": 1,
        "nearby": "Simple Future / Future Perfect",
    },
    {
        "id": "future_perfect",
        "name_en": "Future Perfect",
        "name_ta": "எதிர்கால நிறைவு",
        "batches": 2,
        "nearby": "Simple Future / Future Perfect Continuous",
    },
    {
        "id": "future_perfect_continuous",
        "name_en": "Future Perfect Continuous",
        "name_ta": "எதிர்கால நிறைவுத் தொடர்ச்சி",
        "batches": 1,
        "nearby": "Future Perfect / Future Continuous",
    },
]

SHAPES = """Preferred TNPSC shapes (mix):
- Identify the tense of the underlined/given verb
- Fill the blank with the correct tense form of the verb in brackets
- Choose the grammatically correct sentence
- Spot the error in tense usage
- Signal-word items (since/for/already/yet/ago/yesterday/by the time/now…)
- Contrast with a nearby tense (wrong nearby form as distractor)
Do NOT copy notes/exercises verbatim. Option E added later."""


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def filter_notes(items, form_id):
    primary = [x for x in items if (x.get("tense_form") or "") == form_id]
    extra = [
        x
        for x in items
        if (x.get("tense_form") or "") in ("overview", "mixed") and x not in primary
    ]
    return primary, extra


def format_ground(rules, examples, worked):
    lines = ["RULES:"]
    for i, r in enumerate(rules, 1):
        src = f" ({r.get('source')} p.{r.get('source_page')})" if r.get("source_page") else ""
        lines.append(f"R{i}{src}: {r.get('rule_en')}")
    lines.append("\nEXAMPLES:")
    for i, e in enumerate(examples, 1):
        lines.append(f"E{i}: {e.get('input')} → {e.get('output')} | {e.get('note_en') or ''}")
    lines.append("\nWORKED:")
    for i, w in enumerate(worked, 1):
        lines.append(f"W{i}: {w.get('prompt_en')} ⇒ {w.get('answer_en')}")
    return "\n".join(lines)


def call_gemini(topic, batch_num, focus, rules, examples, worked, exclusion_texts, api_key):
    rules_s = rules if len(rules) <= RULE_SAMPLE else random.sample(rules, RULE_SAMPLE)
    examples_s = examples if len(examples) <= EXAMPLE_SAMPLE else random.sample(examples, EXAMPLE_SAMPLE)
    worked_s = worked if len(worked) <= WORKED_SAMPLE else random.sample(worked, WORKED_SAMPLE)
    ground = format_ground(rules_s, examples_s, worked_s)
    exclusions = ""
    if exclusion_texts:
        exclusions = (
            "\nEXCLUDED STEMS (do not repeat / paraphrase closely):\n"
            + "\n".join(f"- {t}" for t in exclusion_texts[:100])
        )
    name = topic["name_en"]
    prompt = f"""
You are a senior TNPSC General English (SSLC Standard) exam compiler.
Unit I Grammar → Tenses → "{name}"
Practice Batch {batch_num} focus: {focus}

Generate exactly {GENERATE_PER_CALL} practice MCQs strictly about {name}.
Wrong options may use nearby tenses ({topic['nearby']}) but the KEY must be {name}.

GROUND TRUTH (Asan + Grammer.pdf + Govt notes). Answers MUST follow this material:
{ground}
{exclusions}

Rules:
1. Correct answer must be supported by ground truth.
2. English-first (TNPSC General English). Also provide question_ta / options_ta / explanation_ta.
3. {SHAPES}
4. Each object (JSON array only):
   - question_en, question_ta
   - options_en: exactly 4 strings
   - options_ta: exactly 4 strings
   - answer_en: exact match to one options_en
   - answer_ta: exact match to one options_ta
   - explanation_en, explanation_ta (cite rule briefly)
   - source_note: e.g. "asan p.12 / grammer p.18"
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
                if rate_limit >= 8:
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
    ae = (answer_en or "").strip().lower()
    for i, opt in enumerate(options_en):
        if (opt or "").strip().lower() == ae:
            return chr(65 + i)
    return None


def normalize_item(raw, topic, batch_num):
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
    letter = letter_for_answer(opts_en, ans_en)
    if not letter:
        return None
    options = []
    for i, (en, ta) in enumerate(zip(opts_en, opts_ta)):
        options.append({"key": chr(65 + i), "text_en": en, "text_ta": ta or en})
    options.append(
        {"key": "E", "text_en": "Answer not known", "text_ta": "விடை தெரியவில்லை"}
    )
    return {
        "subject": "English",
        "unit": "Grammar",
        "menu": "Tenses",
        "topic": topic["name_en"],
        "topic_id": topic["id"],
        "topic_ta": topic["name_ta"],
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
        "group": "tenses",
        "source_note": (raw.get("source_note") or "").strip(),
    }


def generate_one(topic, batch_num, notes, exclusion, api_key):
    form = topic["id"]
    rules_p, rules_x = filter_notes(notes.get("rules") or [], form)
    ex_p, ex_x = filter_notes(notes.get("examples") or [], form)
    wk_p, wk_x = filter_notes(notes.get("worked_exercises") or [], form)
    rules = rules_p + rules_x[:8]
    examples = ex_p + ex_x[:8]
    worked = wk_p + wk_x[:8]
    if batch_num == 1:
        focus = (
            f"Core {topic['name_en']}: form, uses, signal words, fill-in, identify the tense."
        )
    else:
        focus = (
            f"Exam traps for {topic['name_en']}: error spotting, contrast with "
            f"{topic['nearby']}, choose the correct sentence, since/for/by/ago traps."
        )
    print(f"\n=== {topic['name_en']} Batch {batch_num} ===")
    print(f"  notes R={len(rules_p)} E={len(ex_p)} W={len(wk_p)}")
    raw_list = call_gemini(topic, batch_num, focus, rules, examples, worked, exclusion, api_key)
    print(f"  raw: {len(raw_list)}")
    batch_rows = []
    seen = {re.sub(r"\s+", " ", t.strip().lower()) for t in exclusion if t}
    def absorb(items):
        for raw in items:
            item = normalize_item(raw, topic, batch_num)
            if not item:
                continue
            stem = re.sub(r"\s+", " ", item["question_en"].strip().lower())
            if stem in seen:
                continue
            seen.add(stem)
            batch_rows.append(item)
            exclusion.append(item["question_en"])
            if len(batch_rows) >= TARGET_PER_BATCH:
                return
    absorb(raw_list)
    tries = 0
    while len(batch_rows) < TARGET_PER_BATCH and tries < 3:
        tries += 1
        print(f"  top-up {tries} (have {len(batch_rows)})...")
        more = call_gemini(topic, batch_num, focus, rules, examples, worked, exclusion, api_key)
        absorb(more)
        time.sleep(2)
    batch_rows = batch_rows[:TARGET_PER_BATCH]
    print(f"  kept: {len(batch_rows)}")
    return batch_rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", default=None)
    parser.add_argument("--batch", type=int, default=None)
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY not set")

    notes = load_json(NOTES_PATH, None)
    if not notes:
        raise SystemExit(f"Missing {NOTES_PATH}")

    topics = TOPICS
    if args.topic:
        topics = [t for t in TOPICS if t["id"] == args.topic]
        if not topics:
            raise SystemExit(f"Unknown topic {args.topic}")

    existing = load_json(DB_PATH, [])
    drop_ids = {t["id"] for t in topics}
    drop_batches = {args.batch} if args.batch else None
    kept = []
    for q in existing:
        tid = q.get("topic_id")
        if tid not in drop_ids:
            kept.append(q)
            continue
        if drop_batches is not None:
            m = re.search(r"(\d+)", q.get("batch") or "0")
            b = int(m.group(1)) if m else 0
            if b not in drop_batches:
                kept.append(q)

    exclusion = [q.get("question_en") for q in kept if q.get("question_en")]
    new_rows = []
    for topic in topics:
        batches = [args.batch] if args.batch else list(range(1, topic["batches"] + 1))
        for b in batches:
            if b < 1 or b > topic["batches"]:
                continue
            rows = generate_one(topic, b, notes, exclusion, api_key)
            new_rows.extend(rows)
            time.sleep(1.5)

    out = kept + new_rows
    save_json(DB_PATH, out)
    print(f"\nWrote {DB_PATH}: total={len(out)} new={len(new_rows)}")
    from collections import Counter
    print(Counter((q.get("topic"), q.get("batch")) for q in out))


if __name__ == "__main__":
    main()
