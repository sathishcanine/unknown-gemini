#!/usr/bin/env python3
"""
Generate TNPSC Eliya Mozhi Peyarppu / Simple Translation (Unit 6) practice batches.

Usage:
  python3 Tamil/generate_eliya_peyarppu_questions.py --topic angilam_tamil_sorkal --batch 1
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTES_PATH = os.path.join(BASE_DIR, "Tamil", "eliya_peyarppu_notes.json")
TOPICS_PATH = os.path.join(BASE_DIR, "Tamil", "eliya_peyarppu_topics.json")
DB_PATH = os.path.join(BASE_DIR, "Tamil", "eliya_peyarppu_questions_db.json")
PYQ_BY_TOPIC = {
    "angilam_tamil_sorkal": os.path.join(BASE_DIR, "Tamil", "unit6_topic1_pyq_page330.json"),
    "piramozhi_tamil_sorkal": os.path.join(BASE_DIR, "Tamil", "unit6_topic2_pyq_page343.json"),
}
PYQ_PATH = PYQ_BY_TOPIC["angilam_tamil_sorkal"]

MODELS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite"]
EXAMPLE_SAMPLE = 120
BATCH_TARGET = 30

PYQ_PAIR_HINTS = {
    "angilam_tamil_sorkal": {
        1: ("Robot", "இயந்திர மனிதன்"),
        2: ("Calling Bell", "அழைப்பு மணி"),
        3: ("Check", "காசோலை"),
        4: ("Digital Revolution", "மின்னணுப் புரட்சி"),
        5: ("E-commerce", "மின்னணு வணிகம்"),
        6: ("Demand Draft", "வரைவோலை"),
        7: ("Bank", "வங்கி"),
        8: ("Debit Card", "பற்று அட்டை"),
        9: ("Crop (scissors/tool sense)", "செதுக்கி"),
    },
    "piramozhi_tamil_sorkal": {
        1: ("பொக்கிஷம்", "செல்வம்"),
        2: ("ஜனப் பிரளயம்", "மக்கள் வெள்ளம்"),
        3: ("நிபுணர்", "வல்லுநர்"),
        4: ("ஆச்சரியம்", "வியப்பு"),
        5: ("சந்தோஷம்", "மகிழ்ச்சி"),
        6: ("காரியதரிசி ≠ தலைவர்", "தவறான இணை = II"),
    },
}


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def topic_meta(topic_id: str) -> dict:
    topics = load_json(TOPICS_PATH, {})
    for t in topics.get("topics", []):
        if t.get("id") == topic_id:
            return t
    return {"id": topic_id, "name_ta": topic_id, "name_en": topic_id}


def normalize_q(text: str) -> str:
    return re.sub(r"\s+", "", (text or "")).lower()


def format_ground_truth(rules, examples):
    lines = ["RULES:"]
    for i, r in enumerate(rules, 1):
        ta = (r.get("rule_ta") or "").strip()
        en = (r.get("rule_en") or "").strip()
        page = r.get("source_page")
        extra = f" (SM p.{page})" if page is not None else ""
        if en:
            lines.append(f"R{i}.{extra} {ta} | EN: {en}")
        else:
            lines.append(f"R{i}.{extra} {ta}")

    lines.append("\nEXAMPLES (loanword/foreign → pure Tamil):")
    for i, e in enumerate(examples, 1):
        inp = (e.get("input") or "").strip()
        out = (e.get("output") or "").strip()
        kind = e.get("kind") or "other"
        note = (e.get("note_ta") or "").strip()
        page = e.get("source_page")
        note_bit = f" [{note}]" if note else ""
        page_bit = f" (p.{page})" if page is not None else ""
        lines.append(f"E{i}.{page_bit} [{kind}] {inp} → {out}{note_bit}")
    return "\n".join(lines)


def format_pyq_samples(pyq_samples):
    if not pyq_samples:
        return ""
    lines = ["PREVIOUS YEAR QUESTION SHAPES (style reference only — do NOT copy verbatim):"]
    for item in pyq_samples:
        qno = item.get("q_no", "?")
        stem = (item.get("question_ta") or "").strip()
        opts = item.get("options_ta") or []
        ans = item.get("correct_option_letter") or "?"
        opt_txt = " | ".join(f"{k}:{v}" for k, v in zip("ABCD", opts[:4]))
        lines.append(f"PYQ{qno}. {stem}  [{opt_txt}] → {ans}")
    return "\n".join(lines)


def preferred_shapes(topic_id: str = "") -> str:
    if topic_id == "piramozhi_tamil_sorkal":
        return """5. Preferred shapes (mix across the batch — mirror Topic-2 PYQ style):
   A) Correct loanword↔Tamil PAIR among 4 pairs (பொக்கிஷம்-செல்வம் style)
   B) Given loanword (ஜனப் பிரளயம் / நிபுணர்) → choose correct pure Tamil
   C) Sentence with a பிறமொழி word (ஆச்சரியம் / சந்தோஷமாய்) → choose pure Tamil replacement
   D) Spot the WRONG pair among I–IV style statements (or 4 pair options)
6. Distractors = nearby SM loanword pairs ONLY — NOT invented translations.
   Pure Tamil for Tamil options. NO academy branding."""
    if topic_id == "payanpaattil_angilam_peyarppu":
        return """5. Preferred shapes (mix — reuse Topic-1/Topic-2 PYQ patterns, NEW stems from THIS topic's SM notes only):
   A) English office/admin/computer term → correct Tamil (Robot / Administration style)
   B) Transliterated English in Tamil script → Tamil meaning
   C) Correct EN-Tamil PAIR among 4 pairs
   D) Spot the WRONG pair among close distractors
6. Answers MUST come from THIS topic ground truth (office management / computer / daily-use English terms).
   Distractors = nearby SM terms from same pages. NO academy branding."""
    return """5. Preferred shapes (mix across the batch — mirror PYQ style):
   A) "X (EnglishWord) என்ற ஆங்கிலச் சொல்லுக்கு நேரான தமிழ்ச்சொல்" — 4 Tamil options
   B) "'transliterated English in Tamil script'" — pick correct Tamil meaning (4 Tamil options)
   C) "ஆங்கிலச் சொல்லுக்கு நேரான தமிழ்ச் சொல்லை அறிக" — options as "English - Tamil" pairs; one correct
   D) Spot the WRONG EN↔TA pair among close banking/IT/daily-life distractors
6. Distractors = nearby SM/PYQ-domain terms — NOT invented translations.
   Tamil options in pure Tamil. NO academy branding."""


def pyq_to_practice(item, topic_ta, topic_id, batch_num):
    keys = ["A", "B", "C", "D"]
    opts_ta = [str(x).strip() for x in (item.get("options_ta") or [])[:4]]
    if len(opts_ta) != 4:
        return None
    correct = (item.get("correct_option_letter") or "A").strip().upper()[:1]
    if correct not in keys:
        correct = "A"

    standard_options = []
    for i, ta in enumerate(opts_ta):
        standard_options.append({"key": keys[i], "text_en": ta, "text_ta": ta})
    standard_options.append(
        {"key": "E", "text_en": "Answer not known", "text_ta": "விடை தெரியவில்லை"}
    )

    qno = item.get("q_no")
    hint = (PYQ_PAIR_HINTS.get(topic_id) or {}).get(qno)
    if hint:
        exp_en = f"{hint[0]} = {hint[1]}"
        exp_ta = f"{hint[0]} = {hint[1]}"
    else:
        ans_idx = keys.index(correct)
        exp_ta = f"சரியான விடை: {opts_ta[ans_idx]}"
        exp_en = exp_ta

    q_ta = (item.get("question_ta") or "").strip()
    return {
        "subject": "Tamil",
        "unit": "EliyaMozhiPeyarppu",
        "topic": topic_ta,
        "topic_id": topic_id,
        "source_exam": f"Practice Batch {batch_num}",
        "difficulty": "Medium",
        "question_en": q_ta,
        "question_ta": q_ta,
        "options": standard_options,
        "correct_option": correct,
        "explanation": exp_en,
        "explanation_ta": exp_ta,
        "type": "pyq_style",
        "batch": f"Batch {batch_num}",
        "group": "Practice",
        "source_note": f"PYQ p.{item.get('source_page', 343 if topic_id == 'piramozhi_tamil_sorkal' else 330)}",
    }


def call_gemini(
    topic_id,
    topic_ta,
    topic_en,
    batch_num,
    rules,
    examples,
    pyq_samples,
    need_count,
    exclusion_texts,
    api_key,
):
    sampled_examples = examples
    if len(examples) > EXAMPLE_SAMPLE:
        sampled_examples = random.sample(examples, EXAMPLE_SAMPLE)

    ground = format_ground_truth(rules, sampled_examples)
    pyq_block = format_pyq_samples(pyq_samples)
    exclusions = ""
    if exclusion_texts:
        exclusions = (
            "\nEXCLUDED STEMS (do not repeat / paraphrase closely):\n"
            + "\n".join(f"- {t}" for t in exclusion_texts[:100])
        )

    shapes = preferred_shapes(topic_id)
    prompt = f"""
You are a senior TNPSC General Tamil (பொதுத் தமிழ்) exam compiler for Unit 6 எளிய மொழி பெயர்ப்பு.
Topic: "{topic_ta}" ({topic_en})
Generate exactly {need_count} practice MCQs for Practice Batch {batch_num}.

GROUND TRUTH (SM notes — loanword/foreign → pure Tamil pairs). Use ONLY this material for answers:
{ground}

{pyq_block}
{exclusions}

Generation rules:
1. Base every answer on the ground truth pairs. Lightly rephrase stems; answers must match notes.
2. Match the PYQ shapes above but write NEW stems — do NOT copy PYQ stems verbatim.
3. Tamil-first: question_ta must be exam-natural Tamil. question_en mirrors question_ta.
4. For pair-match shapes, options_en and options_ta may both be the "loanword - Tamil" pair string.
{shapes}
7. Each object keys (JSON array only):
   - question_en, question_ta
   - options_en: exactly 4 strings
   - options_ta: exactly 4 strings (parallel; often identical for Tamil-only options)
   - answer_en: must equal one of options_en exactly
   - answer_ta: must equal one of options_ta exactly
   - explanation_en, explanation_ta (brief — cite the loanword→Tamil pair)
   - difficulty: optional; use "medium"
   - source_note: short pointer like "notes pair"

Option E will be added in post-processing — do NOT include it.
Return ONLY a JSON array of {need_count} objects.
"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    headers = {"Content-Type": "application/json"}

    for model in MODELS:
        retries = 4
        attempt = 0
        delay = 10
        while attempt < retries:
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
                f":generateContent?key={api_key}"
            )
            req = urllib.request.Request(
                url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=180) as response:
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
                    if isinstance(data, list):
                        print(f"    model={model}")
                        return data
                    return []
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="ignore")
                if e.code == 429:
                    print(f"    {model} rate limited; sleep {delay}s...")
                    time.sleep(delay)
                    delay = min(delay * 2, 45)
                    attempt += 1
                    continue
                print(f"    {model} HTTP {e.code}: {body[:160]}")
                break
            except Exception as e:
                attempt += 1
                print(f"    {model} Error: {e}")
                time.sleep(5)
    return []


def scrub(s):
    s = re.sub(r"\bSM\b\.?", "", s or "", flags=re.I)
    s = re.sub(r"எஸ்\.?\s*எம்\.?", "", s)
    s = re.sub(r"\s{2,}", " ", s).strip(" ,.")
    return s


def validate_generated(q, existing_keys, valid):
    required = [
        "question_en",
        "question_ta",
        "options_en",
        "options_ta",
        "answer_en",
        "answer_ta",
        "explanation_en",
        "explanation_ta",
    ]
    if not all(k in q for k in required):
        return None
    if not isinstance(q["options_en"], list) or not isinstance(q["options_ta"], list):
        return None
    if len(q["options_en"]) != 4 or len(q["options_ta"]) != 4:
        return None

    ans_en = str(q["answer_en"]).strip()
    ans_ta = str(q["answer_ta"]).strip()
    opts_en = [str(x).strip() for x in q["options_en"]]
    opts_ta = [str(x).strip() for x in q["options_ta"]]
    if ans_en not in opts_en or ans_ta not in opts_ta:
        return None

    q_en = str(q["question_en"]).strip()
    q_ta = str(q["question_ta"]).strip()
    if not q_ta:
        return None

    idx_en = opts_en.index(ans_en)
    idx_ta = opts_ta.index(ans_ta)
    correct_index = idx_ta if idx_en != idx_ta else idx_en
    if idx_en != idx_ta:
        ans_en = opts_en[correct_index]

    pairs = list(zip(opts_en, opts_ta))
    correct_pair = pairs[correct_index]
    random.shuffle(pairs)
    keys_map = ["A", "B", "C", "D"]
    standard_options = []
    correct_key = "A"
    for i, (en, ta) in enumerate(pairs):
        standard_options.append({"key": keys_map[i], "text_en": en, "text_ta": ta})
        if (en, ta) == correct_pair:
            correct_key = keys_map[i]
    standard_options.append(
        {"key": "E", "text_en": "Answer not known", "text_ta": "விடை தெரியவில்லை"}
    )

    raw_diff = str(q.get("difficulty") or "medium").strip().capitalize()
    if raw_diff not in ("Medium", "Hard"):
        raw_diff = "Medium"

    standard_q = {
        "question_en": q_en,
        "question_ta": q_ta,
        "options": standard_options,
        "correct_option": correct_key,
        "explanation": scrub(str(q["explanation_en"])),
        "explanation_ta": scrub(str(q["explanation_ta"])),
        "difficulty": raw_diff,
        "source_note": scrub(str(q.get("source_note") or "notes")) or "notes",
    }

    key_ta = normalize_q(standard_q["question_ta"])
    key_en = normalize_q(standard_q["question_en"])
    if key_ta in existing_keys or key_en in existing_keys:
        return None
    if any(
        normalize_q(x["question_ta"]) == key_ta or normalize_q(x["question_en"]) == key_en
        for x in valid
    ):
        return None
    return standard_q


def main():
    parser = argparse.ArgumentParser(description="Unit 6 Eliya Peyarppu practice generator")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--batch", type=int, required=True)
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not set.")
        sys.exit(1)

    notes = load_json(NOTES_PATH, {})
    block = (notes.get("topics") or {}).get(args.topic)
    if not block:
        print(f"Error: topic '{args.topic}' not in {NOTES_PATH}")
        sys.exit(1)

    rules = block.get("rules") or []
    examples = block.get("examples") or []
    pyq_path = PYQ_BY_TOPIC.get(args.topic) or PYQ_PATH
    pyq_samples = block.get("pyq_samples") or load_json(pyq_path, [])
    # Style-only samples from earlier topics (do not seed as real questions)
    style_samples = block.get("style_pyq_samples") or []
    prompt_pyq = pyq_samples if pyq_samples else style_samples
    seed_pyq = bool(block.get("seed_pyq", True)) and bool(pyq_samples)
    if not rules and not examples:
        print("Error: no SM rules/examples for this topic yet.")
        sys.exit(1)

    meta = topic_meta(args.topic)
    topic_ta = block.get("name_ta") or meta.get("name_ta") or args.topic
    topic_en = meta.get("name_en") or args.topic

    print(f"Topic: {topic_ta} ({args.topic})")
    print(
        f"Ground truth: {len(rules)} rules, {len(examples)} examples, "
        f"{len(pyq_samples)} PYQ samples, {len(style_samples)} style samples"
    )

    all_db = load_json(DB_PATH, [])
    if not isinstance(all_db, list):
        all_db = []

    existing_topic = [
        q
        for q in all_db
        if q.get("topic") == topic_ta or q.get("topic_id") == args.topic
    ]
    existing_batch = [
        q for q in existing_topic if q.get("batch") == f"Batch {args.batch}"
    ]
    if existing_batch:
        print(f"Batch {args.batch} already has {len(existing_batch)} questions — skipping.")
        return

    exclusion_texts = []
    for q in existing_topic:
        for key in ("question_ta", "question_en"):
            t = (q.get(key) or "").strip()
            if t:
                exclusion_texts.append(t[:220])

    existing_keys = set()
    for q in all_db:
        existing_keys.add(normalize_q(q.get("question_ta") or ""))
        existing_keys.add(normalize_q(q.get("question_en") or ""))

    valid = []
    if args.batch == 1 and seed_pyq:
        print("Seeding Batch 1 with PYQ examples...")
        for item in pyq_samples:
            rec = pyq_to_practice(item, topic_ta, args.topic, args.batch)
            if not rec:
                continue
            key_ta = normalize_q(rec["question_ta"])
            if key_ta in existing_keys:
                continue
            valid.append(rec)
            existing_keys.add(key_ta)
            exclusion_texts.append(rec["question_ta"][:220])
        print(f"  PYQ seeded: {len(valid)}")
    elif args.batch == 1 and style_samples:
        print(f"  Using {len(style_samples)} prior-topic PYQs as STYLE only (not seeded)")

    need = BATCH_TARGET - len(valid)
    print(f"Need {need} generated questions to reach {BATCH_TARGET}")

    attempts = 12
    for attempt in range(attempts):
        if need <= 0:
            break
        ask = min(need + 5, 25)
        print(f"Calling Gemini (attempt {attempt + 1}/{attempts}), ask={ask}...")
        raw = call_gemini(
            args.topic,
            topic_ta,
            topic_en,
            args.batch,
            rules,
            examples,
            prompt_pyq,
            ask,
            exclusion_texts,
            api_key,
        )
        print(f"  Received {len(raw)} raw questions")

        for q in raw:
            std = validate_generated(q, existing_keys, valid)
            if not std:
                continue
            std.update(
                {
                    "subject": "Tamil",
                    "unit": "EliyaMozhiPeyarppu",
                    "topic": topic_ta,
                    "topic_id": args.topic,
                    "source_exam": f"Practice Batch {args.batch}",
                    "type": "practice",
                    "batch": f"Batch {args.batch}",
                    "group": "Practice",
                }
            )
            valid.append(std)
            existing_keys.add(normalize_q(std["question_ta"]))
            existing_keys.add(normalize_q(std["question_en"]))
            exclusion_texts.append(std["question_ta"][:220])

        print(f"  Accumulated valid={len(valid)}")
        need = BATCH_TARGET - len(valid)
        if need <= 0:
            break
        print("  Sleeping 8s...")
        time.sleep(8)

    if len(valid) < BATCH_TARGET:
        print(f"ERROR: need {BATCH_TARGET} valid; got {len(valid)}")
        sys.exit(1)

    final_batch = valid[:BATCH_TARGET]
    random.shuffle(final_batch)
    print(f"Selecting {BATCH_TARGET} questions for Batch {args.batch}")

    all_db.extend(final_batch)
    save_json(DB_PATH, all_db)
    pyq_count = sum(1 for q in final_batch if q.get("type") == "pyq_style")
    print(
        f"\nSUCCESS: Added {len(final_batch)} Q → {DB_PATH} "
        f"(topic={topic_ta}, Batch {args.batch}, PYQ={pyq_count}); DB total={len(all_db)}"
    )


if __name__ == "__main__":
    main()
