import os
import sys
import json
import urllib.request
import urllib.error
import time
import re
import random
import argparse

api_key = os.environ.get("GEMINI_API_KEY")
output_json = "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/Central-Gov-Schemes/cgs_questions_db.json"
facts_json = "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/Central-Gov-Schemes/cgs_facts.json"

SUBJECT = "Central Government Schemes"

if not api_key:
    print("GEMINI_API_KEY not found.")
    sys.exit(1)

model = "gemini-3.1-flash-lite"
url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"


def call_gemini_questions(topic_name, facts_text, difficulty, exclusions, count):
    exclusions_text = "\n".join([f"- {e}" for e in exclusions[:80]])

    prompt = f"""
You are an expert TNPSC Group exam question setter specializing in Central / Union Government Schemes
(subject: {SUBJECT} / மத்திய அரசுத் திட்டங்கள்).

Generate exactly {count} multiple-choice questions under the topic "{topic_name}".
Difficulty Level: {difficulty}

SOURCE FACTS DATABASE (use the full pool; cover multiple schemes when possible):
{facts_text}

STRICT EXCLUSION LIST (Do not generate questions similar to these):
{exclusions_text}

INSTRUCTIONS:
1. Generate exactly {count} unique, high-quality conceptual MCQs grounded ONLY in the facts above.
2. Mix schemes under this ministry (do not focus on only one scheme).
3. Fully bilingual wording (English and Tamil) for question, options, and explanation.
4. Include Option E on every question: "Answer not known" / "விடை தெரியவில்லை".
5. Distractors must be highly plausible (adjacent years, similar scheme names, realistic benefit amounts).
6. Include a mix of formats across the set:
   - Statement-Evaluation (numbered statements with combination choices)
   - Assertion & Reason
   - Match-the-following using STRICT 4x4 HTML:
     Match the following:<br><div class='match-container'><div class='match-col-left'>a) Item A<br>b) Item B<br>c) Item C<br>d) Item D</div><div class='match-col-right'>1. Match 1<br>2. Match 2<br>3. Match 3<br>4. Match 4</div></div>
   - Paragraph-Based Inference (data-rich premise + logical deduction)
7. Keep Tamil scheme names official-style and include English acronyms in parentheses when useful.

Format the output as a JSON array of objects:
[
  {{
    "subject": "{SUBJECT}",
    "topic": "{topic_name}",
    "source_exam": "Practice - Batch",
    "difficulty": "{difficulty}",
    "question_en": "Question text in English",
    "question_ta": "Question text in Tamil",
    "options": [
      {{"key": "A", "text_en": "Option A in English", "text_ta": "Option A in Tamil"}},
      {{"key": "B", "text_en": "Option B in English", "text_ta": "Option B in Tamil"}},
      {{"key": "C", "text_en": "Option C in English", "text_ta": "Option C in Tamil"}},
      {{"key": "D", "text_en": "Option D in English", "text_ta": "Option D in Tamil"}},
      {{"key": "E", "text_en": "Answer not known", "text_ta": "விடை தெரியவில்லை"}}
    ],
    "correct_option": "A/B/C/D",
    "explanation": "Detailed explanation in English",
    "explanation_ta": "Detailed explanation in Tamil",
    "type": "practice",
    "group": "Practice",
    "source_fact": "The English fact this question is based on"
  }}
]

Return ONLY the raw JSON array. No markdown backticks.
"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    headers = {"Content-Type": "application/json"}

    retries = 4
    delay = 8
    for attempt in range(retries):
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as response:
                res_data = response.read().decode("utf-8")
                res_json = json.loads(res_data)
                raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                start_idx = raw_text.find("[")
                if start_idx != -1:
                    count_br = 0
                    for idx in range(start_idx, len(raw_text)):
                        if raw_text[idx] == "[":
                            count_br += 1
                        elif raw_text[idx] == "]":
                            count_br -= 1
                            if count_br == 0:
                                raw_text = raw_text[start_idx : idx + 1]
                                break
                parsed = json.loads(raw_text)
                return parsed if isinstance(parsed, list) else []
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                print(f"      [Attempt {attempt+1}/{retries}] HTTP {e.code}. Retrying in {delay}s...")
                time.sleep(delay)
                delay = min(delay * 2, 90)
            else:
                body = e.read().decode("utf-8", errors="ignore")
                print(f"      [Attempt {attempt+1}/{retries}] HTTP {e.code}: {body[:250]}")
                time.sleep(4)
        except Exception as e:
            print(f"      [Attempt {attempt+1}/{retries}] Error: {e}")
            time.sleep(4)
    return []


def prune_and_select(questions, target_count=30):
    valid_q = [
        q
        for q in questions
        if q.get("question_en") and isinstance(q.get("options"), list) and len(q["options"]) == 5
    ]

    medium_qs = [q for q in valid_q if str(q.get("difficulty", "")).lower() == "medium"]
    hard_qs = [q for q in valid_q if str(q.get("difficulty", "")).lower() == "hard"]

    score_fn = lambda x: len(x.get("question_en", "")) + len(x.get("explanation", ""))
    medium_qs.sort(key=score_fn, reverse=True)
    hard_qs.sort(key=score_fn, reverse=True)

    if len(hard_qs) < 13:
        selected_hard = hard_qs
        selected_medium = medium_qs[: target_count - len(selected_hard)]
    elif len(medium_qs) < 17:
        selected_medium = medium_qs
        selected_hard = hard_qs[: target_count - len(selected_medium)]
    else:
        selected_medium = medium_qs[:17]
        selected_hard = hard_qs[:13]

    combined = selected_medium + selected_hard
    return combined[:target_count]


def generate_batch_for_topic(topic_name, facts, existing_db, batch_name):
    print(f"  Generating {batch_name} for '{topic_name}'...")

    exclusions = []
    for q in existing_db:
        if q.get("topic") == topic_name:
            exclusions.append(q.get("question_en", ""))

    # Full fact pool (no slicing)
    facts_text = "\n".join(
        [
            f"- [{f.get('scheme', 'General')}] {f.get('fact_en', '')} | {f.get('fact_ta', '')}"
            for f in facts
        ]
    )

    print("    Calling Medium difficulty questions...")
    medium_qs = call_gemini_questions(topic_name, facts_text, "Medium", exclusions, 18)
    print(f"    Extracted {len(medium_qs)} Medium questions.")
    time.sleep(6)

    for q in medium_qs:
        exclusions.append(q.get("question_en", ""))

    print("    Calling Hard difficulty questions...")
    hard_qs = call_gemini_questions(topic_name, facts_text, "Hard", exclusions, 14)
    print(f"    Extracted {len(hard_qs)} Hard questions.")

    all_qs = []
    for q in medium_qs + hard_qs:
        q["subject"] = SUBJECT
        q["topic"] = topic_name
        q["type"] = "practice"
        q["group"] = "Practice"
        q["source_exam"] = f"Practice - {batch_name}"
        q["batch"] = batch_name
        # Normalize difficulty casing
        diff = str(q.get("difficulty", "Medium")).strip().capitalize()
        if diff.lower() == "hard":
            q["difficulty"] = "Hard"
        else:
            q["difficulty"] = "Medium"
        all_qs.append(q)

    final_batch = prune_and_select(all_qs, 30)
    random.shuffle(final_batch)
    print(f"    Successfully generated {len(final_batch)} pruned questions for {batch_name}.")
    return final_batch


def main():
    parser = argparse.ArgumentParser(description="Generate CGS practice batches")
    parser.add_argument("--topic", required=True, help="Exact topic name in cgs_facts.json")
    parser.add_argument(
        "--batches",
        nargs="+",
        type=int,
        default=[1, 2],
        help="Batch numbers to generate (default: 1 2)",
    )
    parser.add_argument("--force", action="store_true", help="Regenerate even if batch already complete")
    args = parser.parse_args()

    with open(facts_json, "r", encoding="utf-8") as f:
        facts_db = json.load(f)

    if args.topic not in facts_db or not facts_db[args.topic]:
        print(f"No facts found for topic: {args.topic}")
        sys.exit(1)

    facts = facts_db[args.topic]
    print(f"Topic: {args.topic}")
    print(f"Facts available: {len(facts)}")

    questions_db = []
    if os.path.exists(output_json):
        try:
            with open(output_json, "r", encoding="utf-8") as f:
                questions_db = json.load(f)
            print(f"Loaded existing questions DB: {len(questions_db)} entries.")
        except Exception:
            print("Starting fresh questions database.")

    for n in args.batches:
        batch_name = f"Batch {n}"
        source_exam = f"Practice - {batch_name}"
        existing = [
            q
            for q in questions_db
            if q.get("topic") == args.topic
            and (q.get("batch") == batch_name or q.get("source_exam") == source_exam)
        ]

        if len(existing) >= 30 and not args.force:
            print(f"Topic already has complete {batch_name} ({len(existing)}). Skipping.")
            continue

        if existing:
            print(f"Removing incomplete/old {batch_name} ({len(existing)} questions)...")
            questions_db = [
                q
                for q in questions_db
                if not (
                    q.get("topic") == args.topic
                    and (q.get("batch") == batch_name or q.get("source_exam") == source_exam)
                )
            ]

        batch = generate_batch_for_topic(args.topic, facts, questions_db, batch_name)
        if len(batch) >= 30:
            questions_db.extend(batch[:30])
            with open(output_json, "w", encoding="utf-8") as f:
                json.dump(questions_db, f, indent=2, ensure_ascii=False)
                f.write("\n")
            print(f"Saved {batch_name}: 30 questions.")
            time.sleep(6)
        else:
            print(f"Warning: {batch_name} incomplete ({len(batch)}/30).")

    # Summary
    print("\n=== Summary ===")
    for n in args.batches:
        batch_name = f"Batch {n}"
        qs = [
            q
            for q in questions_db
            if q.get("topic") == args.topic and q.get("batch") == batch_name
        ]
        diffs = {}
        for q in qs:
            d = q.get("difficulty", "?")
            diffs[d] = diffs.get(d, 0) + 1
        print(f"{batch_name}: {len(qs)} questions | {diffs}")


if __name__ == "__main__":
    main()
