#!/usr/bin/env python3
"""
Generate TNPSC Ezhuthum Thiran / Marabu Tamil (Unit 3) practice batches from ezhuthum_thiran_notes.json.

Usage:
  python3 Tamil/generate_sollagarathi_questions.py --topic sorkalai_ozhungu_sotrodar --batch 1
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
NOTES_PATH = os.path.join(BASE_DIR, "Tamil", "ezhuthum_thiran_notes.json")
TOPICS_PATH = os.path.join(BASE_DIR, "Tamil", "ezhuthum_thiran_topics.json")
DB_PATH = os.path.join(BASE_DIR, "Tamil", "ezhuthum_thiran_questions_db.json")

MODELS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite"]
EXAMPLE_SAMPLE = 100


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

    lines.append("\nEXAMPLES (input → output):")
    for i, e in enumerate(examples, 1):
        inp = (e.get("input") or "").strip()
        out = (e.get("output") or "").strip()
        kind = e.get("kind") or "other"
        note = (e.get("note_ta") or "").strip()
        page = e.get("source_page")
        note_bit = f" [{note}]" if note else ""
        page_bit = f" (SM p.{page})" if page is not None else ""
        lines.append(f"E{i}.{page_bit} [{kind}] {inp} → {out}{note_bit}")
    return "\n".join(lines)


def preferred_shapes(topic_id: str, topic_ta: str, topic_en: str) -> str:
    if topic_id == "sorkalai_ozhungu_sotrodar" or "ஒழுங்குபடுத்தி" in topic_ta or "சொற்றொடர் அமைத்தல்" in topic_ta:
        return """5. Preferred shapes for this topic (mix across the 17):
   - Jumbled words → choose the correctly ordered Tamil sentence (எழுவாய் + செயப்படுபொருள் + பயனிலை)
   - Identify எழுவாய் / பயனிலை / செயப்படுபொருள் in a short sentence
   - Spot the WRONG word order among close distractors
   - Short definition MCQ: சொல் / சொற்றொடர் / எழுவாய் / பயனிலை / செயப்படுபொருள் (from notes)
   - Optional: 1 match-the-following (term ↔ definition) HTML match-container
6. Distractors = plausible wrong orders from the SAME jumbled bag — NOT invented sentences.
   Use ONLY notes. Pure Tamil only. NO SM branding / Latin / rule codes (R#/E#)."""
    if topic_id == "thodar_vagaigal" or "தொடர் வகை" in topic_ta:
        return """5. Preferred shapes: classify தொடர் type; pick example of a type; spot wrong classification — from notes only. Pure Tamil. NO branding."""
    if topic_id == "seyvinai_seyappattu" or "செய்வினை" in topic_ta or "தன்வினை" in topic_ta:
        return """5. Preferred shapes: identify செய்வினை/செயப்பாட்டு வினை/தன்வினை/பிறவினை; transform voice/causative from notes examples. Pure Tamil. NO branding."""
    if topic_id == "orumai_panmai_pizhai_thodar" or "ஒருமைப் பன்மை பிழை" in topic_ta:
        return """5. Preferred shapes: spot number-agreement error; choose corrected தொடர்; from notes only. Pure Tamil. NO branding."""
    if topic_id == "thinai_paal_kaalam" or "திணை மரபு" in topic_ta or "பால் மரபு" in topic_ta:
        return """5. Preferred shapes: திணை/பால்/காலம் marabu MCQs from notes lists/rules only. Pure Tamil. NO branding."""
    if topic_id == "ilamai_oli_vinai_thogai" or "இளமைப் பெயர்" in topic_ta or "ஒலிமரபு" in topic_ta:
        return """5. Preferred shapes: இளமைப்பெயர் / ஒலிமரபு / வினைமரபு / தொகை மரபு from notes lists only. Pure Tamil. NO branding."""
    if topic_id == "niruththal_kuriyidugal" or "நிறுத்தற்" in topic_ta or "நிறுத்தக்" in topic_ta or "punctuation" in topic_en.lower():
        return """5. Preferred shapes: choose correctly punctuated sentence; where does காற்புள்ளி go; identify mark type — from notes only. Pure Tamil. NO branding."""


def call_gemini(topic_id, topic_ta, topic_en, batch_num, rules, examples, exclusion_texts, api_key):
    sampled_examples = examples
    if len(examples) > EXAMPLE_SAMPLE:
        sampled_examples = random.sample(examples, EXAMPLE_SAMPLE)

    ground = format_ground_truth(rules, sampled_examples)
    exclusions = ""
    if exclusion_texts:
        exclusions = (
            "\nEXCLUDED STEMS (do not repeat / paraphrase closely):\n"
            + "\n".join(f"- {t}" for t in exclusion_texts[:80])
        )

    shapes = preferred_shapes(topic_id, topic_ta, topic_en)
    prompt = f"""
You are a senior TNPSC General Tamil (பொதுத் தமிழ்) exam compiler for Unit 3 எழுதும் திறன் / மரபுத் தமிழ்.
Topic: "{topic_ta}" ({topic_en})
Generate exactly 17 practice MCQs for Practice Batch {batch_num}.

GROUND TRUTH (SM Academy notes — rules + examples). Use ONLY this material:
{ground}
{exclusions}

Generation rules:
1. Base every answer on the ground truth. Prefer authentic SM examples; you may lightly rephrase
   stems but answers must match the notes.
2. Do NOT copy previous-year question stems verbatim from memory or common PYQ banks.
3. Tamil-first: question_ta must be exam-natural Tamil. question_en is a clear English gloss.
4. Do NOT force Medium/Hard split. Focus on clean TNPSC-style vocabulary items.
{shapes}
7. Each object keys (JSON array only):
   - question_en, question_ta
   - options_en: exactly 4 strings
   - options_ta: exactly 4 strings (parallel to options_en)
   - answer_en: must equal one of options_en exactly
   - answer_ta: must equal one of options_ta exactly
   - explanation_en, explanation_ta (cite the pair/rule briefly — no SM branding)
   - difficulty: optional; if present use "medium"
   - source_note: short pointer like "notes pair" (no academy name)

Option E (Answer not known) will be added by post-processing — do NOT include it in options_en/options_ta.
Escape internal double quotes properly. Return ONLY a JSON array.
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


def main():
    parser = argparse.ArgumentParser(description="Sollagarathi practice question generator")
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
    if not rules and not examples:
        print("Error: no SM rules/examples for this topic yet.")
        sys.exit(1)

    meta = topic_meta(args.topic)
    topic_ta = block.get("name_ta") or meta.get("name_ta") or args.topic
    topic_en = meta.get("name_en") or args.topic

    print(f"Topic: {topic_ta} ({args.topic})")
    print(f"Ground truth: {len(rules)} rules, {len(examples)} examples")

    all_db = load_json(DB_PATH, [])
    if not isinstance(all_db, list):
        all_db = []

    existing_topic = [
        q
        for q in all_db
        if q.get("topic") == topic_ta or q.get("topic_id") == args.topic
    ]
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

    print(f"Existing for topic: {len(existing_topic)}; exclusion stems: {len(exclusion_texts)}")

    valid = []
    attempts = 10

    for attempt in range(attempts):
        print(f"Calling Gemini (attempt {attempt + 1}/{attempts})...")
        raw = call_gemini(
            args.topic,
            topic_ta,
            topic_en,
            args.batch,
            rules,
            examples,
            exclusion_texts,
            api_key,
        )
        print(f"  Received {len(raw)} raw questions")

        for q in raw:
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
                continue
            if not isinstance(q["options_en"], list) or not isinstance(q["options_ta"], list):
                continue
            if len(q["options_en"]) != 4 or len(q["options_ta"]) != 4:
                print("  Discard: options not length 4")
                continue

            ans_en = str(q["answer_en"]).strip()
            ans_ta = str(q["answer_ta"]).strip()
            opts_en = [str(x).strip() for x in q["options_en"]]
            opts_ta = [str(x).strip() for x in q["options_ta"]]
            if ans_en not in opts_en or ans_ta not in opts_ta:
                print(f"  Discard: answer mismatch — {ans_en[:60]}")
                continue

            q_en = str(q["question_en"]).strip()
            q_ta = str(q["question_ta"]).strip()
            if "match" in q_en.lower() or "பொருத்து" in q_ta:
                low = q_en.lower()
                has_abcd = all(p in low for p in ["a)", "b)", "c)", "d)"]) or all(
                    p in low for p in ["a.", "b.", "c.", "d."]
                )
                has_1234 = all(p in low for p in ["1.", "2.", "3.", "4."]) or all(
                    p in low for p in ["1)", "2)", "3)", "4)"]
                )
                if not (has_abcd and has_1234):
                    print("  Discard: weak match layout")
                    continue

            combined = len(q_en) + len(q_ta) + len(str(q["explanation_en"])) + len(
                str(q["explanation_ta"])
            )
            if combined < 120:
                print(f"  Discard: too short ({combined})")
                continue

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
                standard_options.append(
                    {"key": keys_map[i], "text_en": en, "text_ta": ta}
                )
                if (en, ta) == correct_pair:
                    correct_key = keys_map[i]
            standard_options.append(
                {
                    "key": "E",
                    "text_en": "Answer not known",
                    "text_ta": "விடை தெரியவில்லை",
                }
            )

            raw_diff = str(q.get("difficulty") or "medium").strip().capitalize()
            if raw_diff not in ("Medium", "Hard"):
                raw_diff = "Medium"

            # Scrub branding from source_note / explanations lightly
            def scrub(s):
                s = re.sub(r"\bSM\b\.?", "", s or "", flags=re.I)
                s = re.sub(r"எஸ்\.?\s*எம்\.?", "", s)
                s = re.sub(r"விதி\s*R\d+", "", s)
                s = re.sub(r"\s{2,}", " ", s).strip(" ,.")
                return s

            standard_q = {
                "subject": "Tamil",
                "unit": "EzhuthumThiran",
                "topic": topic_ta,
                "topic_id": args.topic,
                "source_exam": f"Practice Batch {args.batch}",
                "difficulty": raw_diff,
                "question_en": q_en,
                "question_ta": q_ta,
                "options": standard_options,
                "correct_option": correct_key,
                "explanation": scrub(str(q["explanation_en"])),
                "explanation_ta": scrub(str(q["explanation_ta"])),
                "type": "practice",
                "batch": f"Batch {args.batch}",
                "group": "Practice",
                "source_note": scrub(str(q.get("source_note") or "notes")) or "notes",
            }

            key_ta = normalize_q(standard_q["question_ta"])
            key_en = normalize_q(standard_q["question_en"])
            if key_ta in existing_keys or key_en in existing_keys:
                continue
            if any(
                normalize_q(x["question_ta"]) == key_ta
                or normalize_q(x["question_en"]) == key_en
                for x in valid
            ):
                continue

            valid.append(standard_q)
            existing_keys.add(key_ta)
            existing_keys.add(key_en)
            exclusion_texts.append(q_ta[:220])

        print(f"  Accumulated valid={len(valid)}")
        if len(valid) >= 30:
            break
        print("  Sleeping 8s...")
        time.sleep(8)

    if len(valid) < 30:
        print(f"ERROR: need 30 valid; got {len(valid)}")
        sys.exit(1)

    valid.sort(
        key=lambda q: len(q["explanation"]) + len(q["explanation_ta"]), reverse=True
    )
    final_batch = valid[:30]
    random.shuffle(final_batch)
    print("Selecting 30 questions")

    all_db.extend(final_batch)
    save_json(DB_PATH, all_db)
    print(
        f"\nSUCCESS: Added {len(final_batch)} Q → {DB_PATH} "
        f"(topic={topic_ta}, Batch {args.batch}); DB total={len(all_db)}"
    )


if __name__ == "__main__":
    main()
