import os
import re
import json
import random
import time
import argparse
import urllib.request
import urllib.error

# Setup paths relative to script location
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "Economic", "economics_questions_db.json")
FACTS_PATH = os.path.join(BASE_DIR, "Economic", "economics_facts.json")
APP_JS_PATH = os.path.join(BASE_DIR, "app.js")

def parse_syllabus_focus(topic):
    """Dynamically parses the syllabus focus description for a topic from app.js."""
    if not os.path.exists(APP_JS_PATH):
        return ""
    try:
        with open(APP_JS_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        pattern = rf'\"{re.escape(topic)}\"\s*:\s*\{{(.*?)\}}'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            block = match.group(1)
            focus_match = re.search(r'focus\s*:\s*\"(.*?)\"', block, re.DOTALL)
            if focus_match:
                # Clean escape slashes
                return focus_match.group(1).replace('\\"', '"').replace('\\n', '\n')
    except Exception as e:
        print(f"Warning: Could not parse syllabus focus from app.js: {e}")
    return ""

def call_gemini_api(prompt, api_key, retries=3):
    """Calls Gemini API with exponential backoff on 503 service unavailable errors."""
    model = "gemini-3.1-flash-lite"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }
    
    headers = {"Content-Type": "application/json"}
    data = json.dumps(payload).encode("utf-8")
    
    delay = 5
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req) as response:
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

def main():
    parser = argparse.ArgumentParser(description="Unified TNPSC Indian Economy Batch Generator")
    parser.add_argument("--topic", required=True, help="Exact syllabus topic name (e.g. 'Social Problem : Poverty')")
    parser.add_argument("--batch", required=True, help="Batch label (e.g. 'Batch 2')")
    
    args = parser.parse_args()
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        exit(1)
        
    print(f"Topic: {args.topic}")
    print(f"Batch: {args.batch}")
    
    # 1. Load ground truth facts
    if not os.path.exists(FACTS_PATH):
        print(f"Error: Facts database not found at {FACTS_PATH}")
        exit(1)
        
    with open(FACTS_PATH, "r", encoding="utf-8") as f:
        all_facts = json.load(f)
        
    topic_facts = all_facts.get(args.topic, [])
    if not topic_facts:
        print(f"Warning: No facts found in economics_facts.json for topic '{args.topic}'")
        # Let's check if the topic name is slightly different
        close_matches = [k for k in all_facts.keys() if args.topic.lower() in k.lower()]
        if close_matches:
            print(f"Did you mean: {close_matches}?")
        exit(1)
        
    print(f"Loaded {len(topic_facts)} ground-truth facts.")
    
    # 2. Parse focus details from app.js
    focus_details = parse_syllabus_focus(args.topic)
    if focus_details:
        print("Syllabus Focus parsed successfully from app.js.")
    else:
        print("Warning: Syllabus focus details not found in app.js. Sticking to default facts.")
        
    # 3. Load database & build exclusion list
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        exit(1)
        
    with open(DB_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)
        
    existing_topic_qs = [q for q in db if q.get("topic") == args.topic]
    existing_texts = [q["question_en"] for q in existing_topic_qs]
    exclude_str = "\n".join([f"- {t[:100]}..." for t in existing_texts])
    print(f"Collected {len(existing_texts)} existing questions to use as exclusions.")
    
    # 4. Formulate the prompt
    prompt = f"""
You are a expert TNPSC (Tamil Nadu Public Service Commission) Group exam question setter.
Your task is to generate exactly **34 unique, high-quality, syllabus-aligned bilingual (English and Tamil) questions** based ONLY on the provided facts.
This is for **{args.batch}** of the topic "{args.topic}".

---
CORE FACTS FOR THE TOPIC "{args.topic}":
{json.dumps(topic_facts, indent=2, ensure_ascii=False)}

---
SYLLABUS FOCUS AND DETAIL TO TEST:
{focus_details}

---
EXISTING QUESTIONS TO EXCLUDE (DO NOT duplicate, copy, or paraphrase these):
{exclude_str}

---
CRITICAL RULES FOR QUESTION GENERATION:

1. DIFFICULTY SPLIT (COMPULSORY COUNT):
   - Generate exactly **17 Medium difficulty** questions.
   - Generate exactly **17 Hard difficulty** questions.
   - You must include the `"difficulty"` field in the JSON object with the value "Medium" or "Hard".
   - Medium questions should test general concepts: Basic years, broad definitions, and primary statistics from the facts sheet.
   - Hard questions should test deep stats, specific percentages, complex committee pairings, structural details, and comparative figures.

2. UNIVERSAL ADVANCED QUESTION FORMATS (COMPULSORY INCLUSION COUNTS):
   - **At least 5 questions must be Paragraph-Based Inference Questions (Logical Deduction)**:
     - These must present a data-rich paragraph (2-3 sentences) detailing comparative statistics from the facts sheet.
     - Ask the candidate to identify the correct logical deduction or inference.
     - Use logical qualifiers like *only*, *more than*, *less than*, *primarily* in distractors to test reading precision.
   - **At least 4 questions must be Contextual Connect / Real-World Application Questions**:
     - Connect a core concept from the facts sheet to a modern hook (e.g. recent NITI Aayog report, Union/State Budget allocations, WHO reports, or global indexes).
     - Test the deep-level origin, definition, or details of that concept in the light of the modern hook.

3. TYPES OF QUESTIONS (Generate a mixed set containing):
   - Direct MCQs
   - Statement Questions
   - Assertion & Reason Questions
   - Match the Following Questions (using the specific HTML column layout below!)

4. PLAUSIBLE DISTRACTORS (WRONG OPTIONS) RULE:
   - All incorrect options (distractors) MUST be highly plausible and closely related to the correct answer.
   - If the correct answer is a specific rate, year, or percentage, the distractors must be adjacent numbers or years.

5. MATCH THE FOLLOWING LAYOUT:
   - For matching questions, format the question_en and question_ta body using our exact 2-column HTML layout:
     "question_en": "Match the following:<br><div class='match-container'><div class='match-col-left'>a) Item A<br>b) Item B<br>c) Item C<br>d) Item D</div><div class='match-col-right'>1. Match 1<br>2. Match 2<br>3. Match 3<br>4. Match 4</div></div>"
   - Format the options text to just show the simple row of matching numbers aligned with spaces (e.g. "4   1   2   3"). Only return the number sequence.

6. STRUCTURE OF OUTPUT JSON (Return a JSON array of exactly 34 objects):
   [
     {{
       "subject": "Economy",
       "topic": "{args.topic}",
       "source_exam": "Practice {args.batch}",
       "difficulty": "Medium/Hard",
       "question_en": "Question text in English",
       "question_ta": "தமிழ் வினா உரை",
       "options": [
         {{ "key": "A", "text_en": "Option A EN", "text_ta": "விருப்பம் A TA" }},
         {{ "key": "B", "text_en": "Option B EN", "text_ta": "விருப்பம் B TA" }},
         {{ "key": "C", ... }},
         {{ "key": "D", ... }},
         {{ "key": "E", "text_en": "Answer not known", "text_ta": "விடை தெரியவில்லை" }}
       ],
       "correct_option": "A/B/C/D",
       "explanation": "Brief explanation in English",
       "explanation_ta": "சுருக்கமான விளக்கம் தமிழில்"
     }}
   ]

Return ONLY the raw JSON string as output. Do not include markdown codeblocks or introductions.
"""

    # 5. Call API
    print("Calling Gemini API...")
    raw_text = call_gemini_api(prompt, api_key)
    
    # 6. Parse JSON output
    text_to_parse = raw_text.strip()
    start_idx = text_to_parse.find('[')
    if start_idx == -1:
        print("Error: Output does not contain a JSON array.")
        exit(1)
        
    count = 0
    for idx in range(start_idx, len(text_to_parse)):
        if text_to_parse[idx] == '[':
            count += 1
        elif text_to_parse[idx] == ']':
            count -= 1
            if count == 0:
                text_to_parse = text_to_parse[start_idx:idx+1]
                break
                
    generated_qs = json.loads(text_to_parse)
    print(f"Parsed {len(generated_qs)} questions successfully.")
    
    # 7. Balance difficulty split (15 Medium / 15 Hard)
    medium_qs = [q for q in generated_qs if q.get("difficulty") == "Medium"]
    hard_qs = [q for q in generated_qs if q.get("difficulty") == "Hard"]
    other_qs = [q for q in generated_qs if q.get("difficulty") not in ["Medium", "Hard"]]
    
    # Force distribute unassigned difficulties
    for q in other_qs:
        if len(medium_qs) < len(hard_qs):
            q["difficulty"] = "Medium"
            medium_qs.append(q)
        else:
            q["difficulty"] = "Hard"
            hard_qs.append(q)
            
    # Balancer loops
    while len(hard_qs) < 15 and len(medium_qs) > 15:
        q = medium_qs.pop()
        q["difficulty"] = "Hard"
        hard_qs.append(q)
        
    while len(medium_qs) < 15 and len(hard_qs) > 15:
        q = hard_qs.pop()
        q["difficulty"] = "Medium"
        medium_qs.append(q)
        
    print(f"Balanced counts: Medium={len(medium_qs)}, Hard={len(hard_qs)}")
    
    if len(medium_qs) < 15 or len(hard_qs) < 15:
        print("Error: Under-generated questions. Balancer could not reach 15/15 split.")
        exit(1)
        
    # 8. Pruning by quality score (length of explanation)
    def get_quality_score(q):
        options = q.get("options", [])
        if len(options) < 4:
            return -9999
        if not q.get("question_ta") or not q.get("question_en"):
            return -9999
        return len(q.get("question_en", "")) + len(q.get("explanation", ""))
        
    medium_qs.sort(key=get_quality_score, reverse=True)
    hard_qs.sort(key=get_quality_score, reverse=True)
    
    final_medium = medium_qs[:15]
    final_hard = hard_qs[:15]
    
    print(f"Pruned Medium: Kept 15, discarded {len(medium_qs) - 15}")
    print(f"Pruned Hard: Kept 15, discarded {len(hard_qs) - 15}")
    
    final_batch = final_medium + final_hard
    
    # Standardize attributes
    for q in final_batch:
        q["topic"] = args.topic
        q["type"] = "practice"
        q["batch"] = args.batch
        q["group"] = "Practice"
        
    # Shuffle once
    print("Shuffling final batch...")
    random.shuffle(final_batch)
    
    # 9. Merge and save back to database
    db.extend(final_batch)
    
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
        
    print(f"\nSUCCESS: Saved 30 optimized questions to {DB_PATH}!")
    print(f"Total questions in database: {len(db)}")

if __name__ == "__main__":
    main()
