#!/usr/bin/env python3
"""
Generate TNPSC Tamil Unit 5 வாசித்தல் (Reading Comprehension) practice batches from vasiththal_notes.json.

Usage:
  python3 Tamil/generate_vasiththal_questions.py --topic pathiyil_vinaigal --batch 1
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
NOTES_PATH = os.path.join(BASE_DIR, "Tamil", "vasiththal_notes.json")
TOPICS_PATH = os.path.join(BASE_DIR, "Tamil", "vasiththal_topics.json")
DB_PATH = os.path.join(BASE_DIR, "Tamil", "vasiththal_questions_db.json")

MODELS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite"]
EXAMPLE_SAMPLE = 120


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
        kind = (e.get("kind") or "other").strip()
        note = (e.get("note_ta") or "").strip()
        page = e.get("source_page")
        note_bit = f" [{note}]" if note else ""
        page_bit = f" (SM p.{page})" if page is not None else ""
        lines.append(f"E{i}.{page_bit} [{kind}] {inp} → {out}{note_bit}")
    return "\n".join(lines)


def preferred_shapes(topic_id: str, topic_ta: str, topic_en: str) -> str:
    if topic_id == "pathiyil_vinaigal":
        return """5. Preferred shapes:
  - Given short paragraph (Tamil) + TNPSC style inference/detail question
  - Ask: main idea / specific detail / meaning of a sentence in context
  - Distractors must be close but contradicted by the paragraph.
6. Use ONLY ground truth rules/examples. Pure Tamil options/stems. No academy branding."""
    if topic_id == "seithithaal_vasiththal":
        return """5. Preferred shapes:
  - Short “news/editorial/government news/article” style passage + comprehension MCQ
  - Ask: purpose / tone / what the text is about / correct inference
  - Distractors should differ subtly in implication (not random facts).
6. Use ONLY ground truth. Pure Tamil. No branding."""
    if topic_id == "uvamai_thodar":
        return """5. Preferred shapes:
  - Simile phrase (உவமைத் தொடர்) → choose correct meaning
  - Distractors are close alternative meanings (nearby options only), not invented.
6. Use ONLY ground truth. Pure Tamil. No branding."""
    if topic_id == "marabu_thodar":
        return """5. Preferred shapes:
  - Idiom/traditional phrase (மரபுத் தொடர்) → choose correct meaning
  - Distractors are similar meanings; answer must match ground truth.
6. Use ONLY ground truth. Pure Tamil. No branding."""
    if topic_id == "pazhamozhigal":
        return """5. Preferred shapes:
  - Proverbs (பழமொழிகள்) → choose correct meaning
  - Provide 4 Tamil meanings, 1 correct.
6. Use ONLY ground truth. Pure Tamil. No branding."""
    if topic_id == "aavanam_puriththal":
        return """5. Preferred shapes:
  - Document snippet (notice/document/passage) → comprehension question
  - Ask for correct inference/detail from the document text
  - Distractors must be wrong based on the snippet.
6. Use ONLY ground truth. Pure Tamil. No branding."""
    return "Use ground truth only. Pure Tamil. No branding."


def call_gemini(topic_id, topic_ta, topic_en, batch_num, rules, examples, exclusion_texts, api_key):
    sampled_examples = examples
    if len(examples) > EXAMPLE_SAMPLE:
        sampled_examples = random.sample(examples, EXAMPLE_SAMPLE)

    ground = format_ground_truth(rules, sampled_examples)
    exclusions = ""
    if exclusion_texts:
        exclusions = (
            "\nEXCLUDED STEMS (do not repeat/paraphrase closely):\n"
            + "\n".join(f"- {t}" for t in exclusion_texts[:80])
        )

    shapes = preferred_shapes(topic_id, topic_ta, topic_en)

    prompt = f"""
You are a senior TNPSC General Tamil (பொதுத் தமிழ்) exam compiler for Unit 5 வாசித்தல்.
Topic: "{topic_ta}" ({topic_en})
Generate exactly 17 practice MCQs for Practice Batch {batch_num}.

GROUND TRUTH (SM Academy notes — rules + examples). Use ONLY this material:
{ground}
{exclusions}

Generation rules:
1) Base answers strictly on the ground truth. Prefer authentic meanings/passage points.
2) Do NOT copy previous-year question stems verbatim.
3) Tamil-first: question_ta must be exam-natural Tamil. question_en is a clear English gloss.
4) options_en/options_ta: exactly 4 strings each (A-D), answer must match one option exactly.
5) Tamil options for question_ta; keep them meaningful and close.
6) Provide explanation_ta/explanation_en pointing to the rule/example used (no branding).
7) Return ONLY JSON array.

Each object keys (JSON array only):
- question_en, question_ta
- options_en: [4 strings]
- options_ta: [4 strings] (parallel to options_en)
- answer_en
- answer_ta
- explanation_en
- explanation_ta
- difficulty: optional (use "medium")

{shapes}
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
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=180) as response:
                    res_json = json.loads(response.read().decode("utf-8"))
                    raw_text = res_json["candidates"][0]["content"]["parts"][0][
                        "text"
                    ].strip()

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
    parser = argparse.ArgumentParser(description="Vasiththal (Reading Comprehension) practice question generator")
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
        print(f"Error: topic '{args.topic}' not in {NOTES_PATH}. Run extract first.")
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
        q for q in all_db if q.get("topic") == topic_ta or q.get("topic_id") == args.topic
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
    attempts = 3
    for attempt in range(attempts):
        print(f"Calling Gemini (attempt {attempt + 1}/{attempts})...")
        raw_qs = call_gemini(
            args.topic,
            topic_ta,
            topic_en,
            args.batch,
            rules,
            examples,
            exclusion_texts,
            api_key,
        )
        if not raw_qs:
            continue

        for q in raw_qs:
            q_en = str(q.get("question_en") or "").strip()
            q_ta = str(q.get("question_ta") or "").strip()
            opts_en = q.get("options_en") or []
            opts_ta = q.get("options_ta") or []

            if len(opts_en) != 4 or len(opts_ta) != 4:
                continue
            ans_en = str(q.get("answer_en") or "").strip()
            ans_ta = str(q.get("answer_ta") or "").strip()

            if ans_en not in [str(x).strip() for x in opts_en]:
                continue
            if ans_ta not in [str(x).strip() for x in opts_ta]:
                continue

            # Scrub branding lightly
            def scrub(s):
                s = re.sub(r"\bSM\b\.?", "", s or "", flags=re.I)
                s = re.sub(r"\s{2,}", " ", s or "").strip()
                return s

            exp_en = scrub(str(q.get("explanation_en") or ""))
            exp_ta = scrub(str(q.get("explanation_ta") or ""))
            if len(q_en) + len(q_ta) + len(exp_en) + len(exp_ta) < 120:
                continue

            # Build standard options with keys A-D and optional E
            pairs = list(zip([str(x).strip() for x in opts_en], [str(x).strip() for x in opts_ta]))
            correct_pair = (ans_en, ans_ta)
            random.shuffle(pairs)

            keys_map = ["A", "B", "C", "D"]
            correct_key = None
            standard_options = []
            for i, (en, ta) in enumerate(pairs):
                key = keys_map[i]
                standard_options.append({"key": key, "text_en": en, "text_ta": ta})
                if (en, ta) == correct_pair:
                    correct_key = key
            if correct_key is None:
                continue

            standard_options.append({"key": "E", "text_en": "Answer not known", "text_ta": "விடை தெரியவில்லை"})

            diff = str(q.get("difficulty") or "medium").strip().lower().capitalize()
            if diff not in ("Medium", "Hard"):
                diff = "Medium"

            standard_q = {
                "subject": "Tamil",
                "unit": "Vasiththal",
                "topic": topic_ta,
                "topic_id": args.topic,
                "source_exam": f"Practice Batch {args.batch}",
                "difficulty": diff,
                "question_en": q_en,
                "question_ta": q_ta,
                "options": standard_options,
                "correct_option": correct_key,
                "explanation": exp_en,
                "explanation_ta": exp_ta,
                "type": "practice",
                "batch": f"Batch {args.batch}",
                "group": "Practice",
                "source_note": "notes",
            }

            key_ta = normalize_q(standard_q["question_ta"])
            key_en = normalize_q(standard_q["question_en"])
            if key_ta in existing_keys or key_en in existing_keys:
                continue

            valid.append(standard_q)
            existing_keys.add(key_ta)
            existing_keys.add(key_en)

        # Stop early if we got enough
        if len(valid) >= 17:
            break

    if not valid:
        print("No valid questions generated; check notes quality / topic range.")
        return

    updated = all_db + valid
    save_json(DB_PATH, updated)
    print(f"\nSUCCESS: Added {len(valid)} new questions for {topic_ta} ({args.topic}) batch {args.batch}")
    print(f"DB now has {len(updated)} total questions.")


if __name__ == "__main__":
    main()

