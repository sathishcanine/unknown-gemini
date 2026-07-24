import os
import sys
import json
import argparse
import random
import urllib.request
import urllib.error

def load_facts(facts_path, topic):
    if not os.path.exists(facts_path):
        print(f"Error: Facts file not found at {facts_path}")
        return []
    with open(facts_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get(topic, [])

def load_existing_questions(db_path, topic):
    if not os.path.exists(db_path):
        return []
    with open(db_path, "r", encoding="utf-8") as f:
        try:
            questions = json.load(f)
            return [q for q in questions if q.get("topic") == topic]
        except Exception:
            return []

def call_gemini_generation(topic, batch_num, facts, exclusion_texts, api_key):
    """Calls Gemini to generate 34 practice questions (17 Medium, 17 Hard) based on facts."""
    facts_formatted = "\n".join([f"- {idx+1}. {f['fact_en']}" for idx, f in enumerate(facts)])
    
    exclusions_formatted = ""
    if exclusion_texts:
        exclusions_formatted = "\nEXCLUDED QUESTION TEXTS (DO NOT GENERATE QUESTIONS SIMILAR TO THESE):\n" + "\n".join([f"- {t}" for t in exclusion_texts[:100]])

    prompt = f"""
You are a senior exam compiler for the TNPSC Group I/II Civil Services.
Your task is to generate exactly 32 practice questions (18 Medium, 14 Hard) for the topic "{topic}" under "Practice Batch {batch_num}".

Ground Truth Facts:
{facts_formatted}
{exclusions_formatted}

Rules for Question Generation:
1. Base every question strictly on the Ground Truth Facts provided. Mention the source fact in the "source_fact" key.
2. Generate exactly 18 "medium" and 14 "hard" difficulty questions.
3. Every question must be fully bilingual (English and Tamil).
4. Target formats:
   - Match the following questions: Must always be a 4x4 matching layout (exactly 4 items in Column A and exactly 4 items in Column B). You MUST format the question text using this exact two-column HTML layout:
     Match the following:<br><div class='match-container'><div class='match-col-left'>a) [Item A]<br>b) [Item B]<br>c) [Item C]<br>d) [Item D]</div><div class='match-col-right'>1. [Match 1]<br>2. [Match 2]<br>3. [Match 3]<br>4. [Match 4]</div></div>
     The Tamil question_ta must use the exact same HTML structure with Tamil translations. Options_en/options_ta must be combinations like: a-2, b-1, c-4, d-3.
   - Statement-based questions: Present 2 or 3 statements, followed by "Which of the statements given above is/are correct?".
   - Standard multiple-choice questions with plausible distractors. Distractors must be highly plausible, using adjacent articles, similar legal cases, or realistic dates/statistics to make them challenging.
5. Advanced Formats (Rule 5):
   - Paragraph-Based Inference Questions (Min 6 per batch): Must feature a 2-3 sentence data-rich premise. Options must test logical deduction rather than rote memory (e.g., using logical qualifiers like 'only', 'more than', 'less than').
   - Contextual Connect Questions (Min 5 per batch): Hook core constitutional principles/facts to modern contexts (such as recent Supreme Court judgments, recent amendments, or executive actions).
6. JSON Output Format:
   Output a raw JSON array of objects. Do not wrap in markdown or include introductions. Each object must have these exact keys:
   - "question_en": Question text in English
   - "question_ta": Question text in Tamil
   - "options_en": Array of 4 options in English
   - "options_ta": Array of 4 options in Tamil
   - "answer_en": Correct option in English (must match one of options_en exactly)
   - "answer_ta": Correct option in Tamil (must match one of options_ta exactly)
   - "explanation_en": Detailed explanation in English
   - "explanation_ta": Detailed explanation in Tamil
   - "difficulty": Either "medium" or "hard"
   - "source_fact": The English ground-truth fact used to generate this question

Ensure the combined length of question + explanation is substantial (minimum 180 characters total).
"""

    model = "gemini-3.1-flash-lite"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            res_data = response.read().decode("utf-8")
            res_json = json.loads(res_data)
            raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
            
            # Clean and parse JSON array
            start_idx = raw_text.find('[')
            if start_idx != -1:
                count = 0
                for idx in range(start_idx, len(raw_text)):
                    if raw_text[idx] == '[':
                        count += 1
                    elif raw_text[idx] == ']':
                        count -= 1
                        if count == 0:
                            raw_text = raw_text[start_idx:idx+1]
                            break
            return json.loads(raw_text)
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.read().decode('utf-8', errors='ignore')}")
    except Exception as e:
        print(f"Error calling Gemini: {e}")
    return []

def main():
    parser = argparse.ArgumentParser(description="Polity Practice Question Generator")
    parser.add_argument("--topic", required=True, help="Exact topic name in syllabus")
    parser.add_argument("--batch", type=int, required=True, help="Practice Batch number")
    parser.add_argument("--start", type=int, default=None, help="1-based start index of facts (optional/deprecated)")
    parser.add_argument("--end", type=int, default=None, help="1-based end index of facts (optional/deprecated)")
    
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        sys.exit(1)

    facts_path = "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/Polity/polity_facts.json"
    db_path = "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/Polity/polity_questions_db.json"

    # 1. Load all facts for the topic
    all_topic_facts = load_facts(facts_path, args.topic)
    if not all_topic_facts:
        print(f"Error: No facts found for topic '{args.topic}' in {facts_path}.")
        sys.exit(1)

    # Use all facts for the topic to allow complete pool analysis
    sliced_facts = all_topic_facts
    print(f"Loaded all {len(sliced_facts)} facts for topic '{args.topic}' for generation.")

    # 2. Load existing questions to build exclusion list
    existing_qs = load_existing_questions(db_path, args.topic)
    exclusion_texts = [q.get("question_en", "").strip().lower() for q in existing_qs if q.get("question_en")]
    print(f"Found {len(existing_qs)} existing questions for exclusions.")

    # 3. Call Gemini to generate batch
    print(f"Calling Gemini to generate practice questions for Batch {args.batch}...")
    raw_questions = call_gemini_generation(args.topic, args.batch, sliced_facts, exclusion_texts, api_key)
    print(f"Received {len(raw_questions)} questions from Gemini.")

    # 4. Python-side validation, mapping and pruning
    valid_medium = []
    valid_hard = []

    for q in raw_questions:
        # Check keys
        required_keys = ["question_en", "question_ta", "options_en", "options_ta", "answer_en", "answer_ta", "explanation_en", "explanation_ta", "difficulty"]
        if not all(k in q for k in required_keys):
            continue
            
        # Verify answer exists in options
        ans_en = q["answer_en"].strip()
        ans_ta = q["answer_ta"].strip()
        
        if ans_en not in q["options_en"] or ans_ta not in q["options_ta"]:
            print(f"  Discarding question due to mismatched option/answer: {ans_en}")
            continue

        # Strict Match-the-following 4x4 layout validation
        is_match = False
        if "match" in q["question_en"].lower() or "பொருத்து" in q["question_ta"].lower():
            is_match = True
            
        if is_match:
            q_text_lower = q["question_en"].lower()
            has_abcd = (all(p in q_text_lower for p in ["a)", "b)", "c)", "d)"]) or 
                       all(p in q_text_lower for p in ["a.", "b.", "c.", "d."]) or
                       all(p in q_text_lower for p in ["a -", "b -", "c -", "d -"]))
            has_1234 = (all(p in q_text_lower for p in ["1.", "2.", "3.", "4."]) or 
                       all(p in q_text_lower for p in ["1)", "2)", "3)", "4)"]) or
                       all(p in q_text_lower for p in ["1 -", "2 -", "3 -", "4 -"]))
            if not (has_abcd and has_1234):
                print(f"  Discarding match question due to sub-standard match layout (not 4x4): {q['question_en'][:100]}...")
                continue

        # Length validation: combined length of question + explanation
        combined_len = len(q["question_en"]) + len(q["question_ta"]) + len(q["explanation_en"]) + len(q["explanation_ta"])
        if combined_len < 180:
            print(f"  Discarding question due to short explanation length: {combined_len} chars")
            continue

        # Transform to standard frontend schema format
        correct_index = q["options_en"].index(ans_en)
        keys_map = ["A", "B", "C", "D"]
        correct_key = keys_map[correct_index]

        standard_options = []
        for i in range(4):
            standard_options.append({
                "key": keys_map[i],
                "text_en": q["options_en"][i].strip(),
                "text_ta": q["options_ta"][i].strip()
            })
        
        # Add Option E (Answer Not Known)
        standard_options.append({
            "key": "E",
            "text_en": "Answer not known",
            "text_ta": "விடை தெரியவில்லை"
        })

        standard_q = {
            "subject": "Polity",
            "topic": args.topic,
            "source_exam": f"Practice Batch {args.batch}",
            "difficulty": q["difficulty"].strip().capitalize(),
            "question_en": q["question_en"].strip(),
            "question_ta": q["question_ta"].strip(),
            "options": standard_options,
            "correct_option": correct_key,
            "explanation": q["explanation_en"].strip(),
            "explanation_ta": q["explanation_ta"].strip(),
            "type": "practice",
            "batch": f"Batch {args.batch}",
            "group": "Practice",
            "source_fact": q.get("source_fact", "").strip()
        }

        # Sort by difficulty
        diff = q["difficulty"].lower()
        if diff == "medium":
            valid_medium.append(standard_q)
        elif diff == "hard":
            valid_hard.append(standard_q)

    print(f"Valid questions - Medium: {len(valid_medium)}, Hard: {len(valid_hard)}")

    # We need at least 30 valid questions in total to select a full batch
    if len(valid_medium) + len(valid_hard) < 30:
        print(f"ERROR: Not enough valid questions to make 30. Got Medium: {len(valid_medium)}, Hard: {len(valid_hard)}")
        sys.exit(1)

    # Sort each list by length (descending) to get the most detailed explanations
    valid_medium.sort(key=lambda q: len(q["explanation"]) + len(q["explanation_ta"]), reverse=True)
    valid_hard.sort(key=lambda q: len(q["explanation"]) + len(q["explanation_ta"]), reverse=True)

    # Dynamically select questions to get as close to 17/13 as possible
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
    random.shuffle(final_batch) # Shuffle to mix difficulties

    # 5. Append to database
    all_db_qs = []
    if os.path.exists(db_path):
        with open(db_path, "r", encoding="utf-8") as f:
            try:
                all_db_qs = json.load(f)
            except Exception:
                all_db_qs = []

    # Check for duplicates one last time before saving
    existing_all_texts = set(q.get("question_en", "").strip().lower() for q in all_db_qs if q.get("question_en"))
    
    added_count = 0
    for q in final_batch:
        q_en_text = q["question_en"].strip().lower()
        if q_en_text not in existing_all_texts:
            all_db_qs.append(q)
            existing_all_texts.add(q_en_text)
            added_count += 1

    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(all_db_qs, f, indent=2, ensure_ascii=False)

    print(f"\nSUCCESS: Added {added_count} unique questions for topic '{args.topic}' (Batch {args.batch}) to database!")
    print(f"Total questions in Polity database: {len(all_db_qs)}")

if __name__ == "__main__":
    main()
