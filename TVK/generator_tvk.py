import os
import sys
import json
import random
import time
import argparse
import urllib.request
import urllib.error

# Setup paths relative to script location
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "TVK", "tvk_questions_db.json")
FACTS_PATH = os.path.join(BASE_DIR, "TVK", "tvk_facts.json")
GUIDE_PATH = os.path.join(BASE_DIR, "TVK", "TVK_GENERATION_GUIDE.md")


def call_gemini_api(prompt, api_key, retries=3):
    """Calls Gemini API with exponential backoff on 503 service unavailable errors."""
    model = "gemini-3.1-flash-lite"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }

    headers = {"Content-Type": "application/json"}
    data = json.dumps(payload).encode("utf-8")

    delay = 5
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=90) as response:
                res_data = response.read().decode("utf-8")
                res_json = json.loads(res_data)
                return res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="ignore")
            if e.code == 503:
                print(f"Attempt {attempt}/{retries} failed with 503 (Service Unavailable). Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2
            else:
                print(f"HTTP Error {e.code}: {error_body}")
                raise e
        except Exception as e:
            print(f"Unexpected error: {e}")
            raise e

    raise Exception("Max retries exceeded for Gemini API call.")


def call_gemini_generation(topic, batch, facts, exclusion_texts, api_key):
    """Builds a structured prompt for practice question generation based on TVK facts."""
    facts_str = "\n".join(
        [f"- Fact: {f['fact_en']} | Source: {f.get('source', '')}" for f in facts]
    )
    exclusions_str = "\n".join([f"- {t}" for t in exclusion_texts[:60]])

    prompt = f"""
You are an expert TNPSC question generator.
Generate practice questions based on TVK-Government Policies notes for the topic "{topic}".
This is Batch {batch}.

Generate exactly 32 practice questions (18 "Medium" and 14 "Hard" difficulty level questions).
For each question, choose one or more facts from the provided ground-truth facts list below as reference. Do not use facts not mentioned.

--- GROUND TRUTH FACTS ---
{facts_str}

--- STRICT EXCLUSION LIST (DO NOT GENERATE QUESTIONS SIMILAR TO THESE) ---
{exclusions_str}

--- QUESTION PATTERNS TO INCLUDE ---
1. Statement-Evaluation Questions (30% - 40%): Numbered statements (1, 2, 3) where options are combinations like "1 and 2 only".
2. Match the Following Questions (15% - 20%): Standard HTML 4x4 layout.
   You MUST format the question using this exact HTML structure:
   "Match the following:<br><div class='match-container'><div class='match-col-left'>a) Left Item 1<br>b) Left Item 2<br>c) Left Item 3<br>d) Left Item 4</div><div class='match-col-right'>1. Right Item 1<br>2. Right Item 2<br>3. Right Item 3<br>4. Right Item 4</div></div>"
   The options MUST be simple matching digits (e.g. "3   4   1   2"). Do not use plain text spaces or lists for columns.
3. Assertion & Reason Questions (15% - 20%): Standard options.
4. Direct MCQ Fact-Checks (20% - 30%): Single choice questions on schemes, budgets, leaders, stats, etc.

--- RULES FOR DISTRACTORS AND EXPLANATIONS ---
- All options (A, B, C, D) must be highly plausible. Use close budget numbers, adjacent years, or related scheme/leader names.
- Bilingual: Every question, option, and explanation must be fully translated into Tamil.
- Explanation: Provide a detailed, deep-dive explanation (minimum 180 characters combined) explaining why the option is correct and why other options are incorrect.

OUTPUT FORMAT:
Output a raw JSON array of objects. Do not wrap in markdown or include introductions.
Each object must have the following keys:
- "question_en": Question text in English
- "question_ta": Question text in Tamil
- "options_en": Array of 4 option strings in English
- "options_ta": Array of 4 option strings in Tamil
- "answer_en": The correct option string in English (must exactly match one of options_en)
- "answer_ta": The correct option string in Tamil (must exactly match one of options_ta)
- "explanation_en": Explanation in English
- "explanation_ta": Explanation in Tamil
- "difficulty": "Medium" or "Hard"
- "source_fact": The English fact(s) this question is based on.
"""

    raw_text = call_gemini_api(prompt, api_key)

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

    try:
        return json.loads(raw_text)
    except Exception as e:
        print(f"Error parsing JSON response: {e}")
        print("Raw output was:")
        print(raw_text[:2000])
        raise e


def load_existing_questions(db_path, topic):
    """Loads existing database questions for a topic to prevent duplication."""
    if not os.path.exists(db_path):
        return []
    try:
        with open(db_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [q for q in data if q.get("topic") == topic]
    except Exception:
        return []


def main():
    parser = argparse.ArgumentParser(description="TNPSC TVK-Government Policies Batch Generator")
    parser.add_argument(
        "--topic",
        required=True,
        help="Canonical topic name (e.g. 'TVK Leaders')",
    )
    parser.add_argument("--batch", required=True, help="Batch label (e.g. '1' or 'Batch 1')")
    parser.add_argument("--start", type=int, default=None, help="Start index of facts (optional/deprecated)")
    parser.add_argument("--end", type=int, default=None, help="End index of facts (optional/deprecated)")

    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        exit(1)

    batch_label = str(args.batch).strip()
    if batch_label.lower().startswith("batch"):
        batch_num = batch_label.split()[-1]
    else:
        batch_num = batch_label

    print(f"Topic: {args.topic}")
    print(f"Batch: {batch_num}")
    print(f"Guide: {GUIDE_PATH}")

    if not os.path.exists(FACTS_PATH):
        print(f"Error: Facts database not found at {FACTS_PATH}")
        exit(1)

    with open(FACTS_PATH, "r", encoding="utf-8") as f:
        all_facts = json.load(f)

    all_topic_facts = all_facts.get(args.topic, [])
    if not all_topic_facts:
        print(f"Error: No facts found for topic '{args.topic}'")
        exit(1)

    sliced_facts = all_topic_facts
    print(f"Loaded all {len(sliced_facts)} facts for topic '{args.topic}' for generation.")

    existing_qs = load_existing_questions(DB_PATH, args.topic)
    exclusion_texts = [
        q.get("question_en", "").strip().lower() for q in existing_qs if q.get("question_en")
    ]
    print(f"Found {len(existing_qs)} existing questions for exclusions.")

    print(f"Calling Gemini to generate practice questions for Batch {batch_num}...")
    raw_questions = call_gemini_generation(
        args.topic, batch_num, sliced_facts, exclusion_texts, api_key
    )
    print(f"Received {len(raw_questions)} questions from Gemini.")

    valid_medium = []
    valid_hard = []

    for q in raw_questions:
        required_keys = [
            "question_en",
            "question_ta",
            "options_en",
            "options_ta",
            "answer_en",
            "answer_ta",
            "explanation_en",
            "explanation_ta",
            "difficulty",
        ]
        if not all(k in q for k in required_keys):
            continue

        if not isinstance(q["options_en"], list) or not isinstance(q["options_ta"], list):
            print("  Discarding question: options_en and options_ta must be JSON lists.")
            continue
        if len(q["options_en"]) != 4 or len(q["options_ta"]) != 4:
            print("  Discarding question: options_en and options_ta must have exactly 4 items.")
            continue

        ans_en = q["answer_en"].strip()
        ans_ta = q["answer_ta"].strip()

        if ans_en not in q["options_en"] or ans_ta not in q["options_ta"]:
            print(f"  Discarding question due to mismatched option/answer: {ans_en}")
            continue

        is_match = False
        if "match" in q["question_en"].lower() or "பொருத்து" in q["question_ta"].lower():
            is_match = True

        if is_match:
            q_text_lower = q["question_en"].lower()
            has_abcd = (
                all(p in q_text_lower for p in ["a)", "b)", "c)", "d)"])
                or all(p in q_text_lower for p in ["a.", "b.", "c.", "d."])
                or all(p in q_text_lower for p in ["a -", "b -", "c -", "d -"])
            )
            has_1234 = (
                all(p in q_text_lower for p in ["1.", "2.", "3.", "4."])
                or all(p in q_text_lower for p in ["1)", "2)", "3)", "4)"])
                or all(p in q_text_lower for p in ["1 -", "2 -", "3 -", "4 -"])
            )
            if not (has_abcd and has_1234):
                print(
                    f"  Discarding match question due to sub-standard match layout (not 4x4): {q['question_en'][:100]}..."
                )
                continue

        combined_len = (
            len(q["question_en"])
            + len(q["question_ta"])
            + len(q["explanation_en"])
            + len(q["explanation_ta"])
        )
        if combined_len < 180:
            print(f"  Discarding question due to short explanation length: {combined_len} chars")
            continue

        correct_index = q["options_en"].index(ans_en)
        keys_map = ["A", "B", "C", "D"]
        correct_key = keys_map[correct_index]

        standard_options = []
        for i in range(4):
            standard_options.append(
                {
                    "key": keys_map[i],
                    "text_en": q["options_en"][i].strip(),
                    "text_ta": q["options_ta"][i].strip(),
                }
            )

        standard_options.append(
            {
                "key": "E",
                "text_en": "Answer not known",
                "text_ta": "விடை தெரியவில்லை",
            }
        )

        standard_q = {
            "subject": "TVK",
            "topic": args.topic,
            "source_exam": f"Practice Batch {batch_num}",
            "difficulty": q["difficulty"].strip().capitalize(),
            "question_en": q["question_en"].strip(),
            "question_ta": q["question_ta"].strip(),
            "options": standard_options,
            "correct_option": correct_key,
            "explanation": q["explanation_en"].strip(),
            "explanation_ta": q["explanation_ta"].strip(),
            "type": "practice",
            "batch": f"Batch {batch_num}",
            "group": "Practice",
            "source_fact": q.get("source_fact", "").strip(),
        }

        diff = q["difficulty"].lower()
        if diff == "medium":
            valid_medium.append(standard_q)
        elif diff == "hard":
            valid_hard.append(standard_q)

    print(f"Valid questions - Medium: {len(valid_medium)}, Hard: {len(valid_hard)}")

    if len(valid_medium) + len(valid_hard) < 30:
        print(
            f"ERROR: Not enough valid questions to make 30. Got Medium: {len(valid_medium)}, Hard: {len(valid_hard)}"
        )
        sys.exit(1)

    valid_medium.sort(key=lambda q: len(q["explanation"]) + len(q["explanation_ta"]), reverse=True)
    valid_hard.sort(key=lambda q: len(q["explanation"]) + len(q["explanation_ta"]), reverse=True)

    if len(valid_hard) < 13:
        take_hard = len(valid_hard)
        take_medium = 30 - take_hard
    elif len(valid_medium) < 17:
        take_medium = len(valid_medium)
        take_hard = 30 - take_medium
    else:
        take_medium = 17
        take_hard = 13

    print(f"Selecting {take_medium} Medium and {take_hard} Hard questions for the final batch of 30.")
    final_medium = valid_medium[:take_medium]
    final_hard = valid_hard[:take_hard]

    final_batch = final_medium + final_hard
    random.shuffle(final_batch)

    all_db_qs = []
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "r", encoding="utf-8") as f:
            try:
                all_db_qs = json.load(f)
            except Exception:
                all_db_qs = []

    all_db_qs.extend(final_batch)

    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(all_db_qs, f, indent=2, ensure_ascii=False)

    print(
        f"\nSUCCESS: Added 30 unique questions for topic '{args.topic}' (Batch {batch_num}) to database!"
    )
    print(f"Total questions in TVK database: {len(all_db_qs)}")


if __name__ == "__main__":
    main()
