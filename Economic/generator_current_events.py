import os
import json
import random
import time
import argparse
import urllib.request
import urllib.error

# Setup paths relative to script location
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "Economic", "current_affairs_questions_db.json")
FACTS_PATH = os.path.join(BASE_DIR, "Economic", "economics_facts.json")
GUIDE_PATH = os.path.join(BASE_DIR, "Economic", "CURRENT_EVENTS_GENERATION_GUIDE.md")

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
    parser = argparse.ArgumentParser(description="TNPSC Current Affairs Batch Generator")
    parser.add_argument("--topic", required=True, help="Exact syllabus topic name (e.g. 'Current Affairs : January 2026')")
    parser.add_argument("--batch", required=True, help="Batch label (e.g. 'Batch 1')")
    
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
        print(f"Error: No facts found in economics_facts.json for topic '{args.topic}'")
        exit(1)
        
    print(f"Loaded {len(topic_facts)} ground-truth facts for Current Affairs.")
    
    # 2. Load database & build exclusion list
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        exit(1)
        
    with open(DB_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)
        
    existing_topic_qs = [q for q in db if q.get("topic") == args.topic]
    existing_texts = [q["question_en"] for q in existing_topic_qs]
    exclude_str = "\n".join([f"- {t[:100]}..." for t in existing_texts])
    print(f"Collected {len(existing_texts)} existing questions to use as exclusions.")
    
    # 3. Load Current Affairs Guide rules
    guide_rules = ""
    if os.path.exists(GUIDE_PATH):
        with open(GUIDE_PATH, "r", encoding="utf-8") as f:
            guide_rules = f.read()
            
    # 4. Formulate the Current Affairs prompt
    prompt = f"""
You are a expert TNPSC (Tamil Nadu Public Service Commission) Group exam question setter.
Your task is to generate exactly **34 unique, high-quality, syllabus-aligned bilingual (English and Tamil) questions** based ONLY on the provided facts.
This is for **{args.batch}** of the topic "{args.topic}".

---
CORE FACTS FOR THIS MONTH:
{json.dumps(topic_facts, indent=2, ensure_ascii=False)}

---
EXISTING QUESTIONS TO EXCLUDE (DO NOT duplicate, copy, or paraphrase these):
{exclude_str}

---
CURRENT AFFAIRS GENERATION RULES & PATTERNS:
{guide_rules}

---
CRITICAL FORMAT RULES:
- Include the `"difficulty"` field in the JSON object with the value "Medium" or "Hard" (exactly 17 Medium and 17 Hard candidates).
- Medium questions should test direct facts, awards, or appointments.
- Hard questions should test statement-evaluations, numerical GDP projections, space launching parameters, and assertion-reason relationships.
- Return a JSON array of exactly 34 objects:
   [
     {{
       "subject": "Current Affairs",
       "topic": "{args.topic}",
       "source_exam": "Practice {args.batch}",
       "difficulty": "Medium/Hard",
       "question_en": "Question text in English",
       "question_ta": "தமிழ் வினா உரை",
       "options": [
         {{ "key": "A", "text_en": "Option A EN", "text_ta": "விருப்பம் A TA" }},
         {{ "key": "B", ... }},
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
        q["subject"] = "Current Affairs"  # Guarantee subject matches
        
    # Shuffle once
    print("Shuffling final batch...")
    random.shuffle(final_batch)
    
    # 9. Merge and save back to database
    db.extend(final_batch)
    
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
        
    print(f"\nSUCCESS: Saved 30 optimized Current Affairs questions to {DB_PATH}!")
    print(f"Total questions in database: {len(db)}")

if __name__ == "__main__":
    main()
