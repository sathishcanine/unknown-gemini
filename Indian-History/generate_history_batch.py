import os
import json
import base64
import urllib.request
import urllib.error
import time
import re
import random

api_key = os.environ.get("GEMINI_API_KEY")
output_json = "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/Indian-History/history_questions_db.json"
facts_json = "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/Indian-History/history_facts.json"

if not api_key:
    print("GEMINI_API_KEY not found.")
    exit(1)

model = "gemini-3.5-flash-lite"
url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

def call_gemini_questions(topic_name, facts_text, difficulty, exclusions, count):
    exclusions_text = "\n".join([f"- {e}" for e in exclusions[:50]])
    
    prompt = f"""
    You are an expert TNPSC Group exam question setter and historian.
    I want you to generate exactly {count} multiple-choice questions under the topic "{topic_name}".
    Difficulty Level: {difficulty}
    
    SOURCE FACTS DATABASE:
    {facts_text}
    
    STRICT EXCLUSION LIST (Do not generate questions similar to these):
    {exclusions_text}
    
    INSTRUCTIONS:
    1. Generate exactly {count} unique, high-quality, conceptual multiple-choice questions.
    2. Wording and options must be fully bilingual (English and Tamil).
    3. Include Option E: `"key": "E", "text_en": "Answer not known", "text_ta": "விடை தெரியவில்லை"` for every question.
    4. Distractors (wrong options) must be highly plausible and closely related to the facts.
    5. Follow these advanced formats:
       - Statement-Evaluation (numbered statements 1, 2, 3, 4 with combination choices).
       - Assertion & Reason.
       - Match-the-following (must use the 2-column HTML match-container with exactly 4x4 layout).
       - Paragraph-Based Inference Questions (data-rich premise testing logical deduction).
       
    Format the output as a JSON array of objects:
    [
      {{
        "subject": "History",
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
        "explanation": "Detailed explanation of the correct answer in English",
        "explanation_ta": "Detailed explanation of the correct answer in Tamil",
        "type": "practice",
        "group": "Practice"
      }}
    ]
    
    Return ONLY the raw JSON string. Do not add markdown backticks.
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }
    headers = {"Content-Type": "application/json"}
    
    retries = 3
    delay = 6
    for attempt in range(retries):
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req) as response:
                res_data = response.read().decode("utf-8")
                res_json = json.loads(res_data)
                raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                return json.loads(raw_text)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"      [Attempt {attempt+1}/{retries}] Rate limited. Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2
            else:
                print(f"      [Attempt {attempt+1}/{retries}] HTTP Error {e.code}")
                time.sleep(3)
        except Exception as e:
            print(f"      [Attempt {attempt+1}/{retries}] Error: {e}")
            time.sleep(3)
    return []

def prune_and_select(questions, target_count=30):
    valid_q = [q for q in questions if "question_en" in q and "options" in q and len(q["options"]) == 5]
    
    # Split by difficulty
    medium_qs = [q for q in valid_q if q.get("difficulty") == "Medium"]
    hard_qs = [q for q in valid_q if q.get("difficulty") == "Hard"]
    
    # Sort both lists by quality score
    score_fn = lambda x: len(x.get("question_en", "")) + len(x.get("explanation", ""))
    medium_qs.sort(key=score_fn, reverse=True)
    hard_qs.sort(key=score_fn, reverse=True)
    
    # Dynamic selection logic
    if len(hard_qs) < 13:
        selected_hard = hard_qs
        needed_medium = target_count - len(selected_hard)
        selected_medium = medium_qs[:needed_medium]
    elif len(medium_qs) < 17:
        selected_medium = medium_qs
        needed_hard = target_count - len(selected_medium)
        selected_hard = hard_qs[:needed_hard]
    else:
        selected_medium = medium_qs[:17]
        selected_hard = hard_qs[:13]
        
    combined = selected_medium + selected_hard
    return combined[:target_count]

def generate_batch_for_topic(topic_name, facts, existing_db, batch_name):
    print(f"  Generating {batch_name} for '{topic_name}'...")
    
    # 1. Gather exclusions
    exclusions = []
    for q in existing_db:
        if q.get("topic") == topic_name:
            exclusions.append(q.get("question_en", ""))
            
    # 2. Format facts text
    facts_text = "\n".join([f"- {f['fact_en']} | {f['fact_ta']}" for f in facts[:40]])
    
    # 3. Call Medium questions
    print("    Calling Medium difficulty questions...")
    medium_qs = call_gemini_questions(topic_name, facts_text, "Medium", exclusions, 18)
    print(f"    Extracted {len(medium_qs)} Medium questions.")
    time.sleep(6)
    
    # Update exclusions
    for q in medium_qs:
        exclusions.append(q.get("question_en", ""))
        
    # 4. Call Hard questions
    print("    Calling Hard difficulty questions...")
    hard_qs = call_gemini_questions(topic_name, facts_text, "Hard", exclusions, 14)
    print(f"    Extracted {len(hard_qs)} Hard questions.")
    
    # 5. Merge, sort, and prune
    all_qs = []
    for q in (medium_qs + hard_qs):
        q["source_exam"] = f"Practice - {batch_name}"
        q["batch"] = batch_name  # e.g. "Batch 1" — required for app grouping (30 Qs/batch)
        all_qs.append(q)
        
    final_batch = prune_and_select(all_qs, 30)
    
    # Shuffle batch once
    random.shuffle(final_batch)
    
    print(f"    Successfully generated {len(final_batch)} pruned questions for {batch_name}.")
    return final_batch

def main():
    print("Cooling down for 30 seconds to clear rate limit window...")
    time.sleep(30)
    
    if not os.path.exists(facts_json):
        print("Facts file not found.")
        return
        
    with open(facts_json, "r", encoding="utf-8") as f:
        facts_db = json.load(f)
        
    # Load existing questions database
    questions_db = []
    if os.path.exists(output_json):
        try:
            with open(output_json, "r", encoding="utf-8") as f:
                questions_db = json.load(f)
            print(f"Loaded existing questions database with {len(questions_db)} entries.")
        except Exception as e:
            print("Starting fresh database.")
            
    # Filter topics with actual facts
    active_topics = [t for t, facts in facts_db.items() if len(facts) > 0]
    print(f"Found {len(active_topics)} active topics for generation.")
    
    for topic in active_topics:
        # Check if Batch 1 already generated and complete
        b1_qs = [q for q in questions_db if q.get("topic") == topic and q.get("source_exam") == "Practice - Batch 1"]
        if len(b1_qs) < 30:
            if len(b1_qs) > 0:
                print(f"Topic '{topic}' has incomplete Batch 1 ({len(b1_qs)}/30 questions). Re-generating...")
                questions_db = [q for q in questions_db if not (q.get("topic") == topic and q.get("source_exam") == "Practice - Batch 1")]
            batch = generate_batch_for_topic(topic, facts_db[topic], questions_db, "Batch 1")
            if len(batch) >= 30:
                questions_db.extend(batch)
                with open(output_json, "w", encoding="utf-8") as f:
                    json.dump(questions_db, f, indent=2, ensure_ascii=False)
                time.sleep(6)
            else:
                print(f"Warning: Failed to generate complete Batch 1 for '{topic}'. Will retry on next run.")
        else:
            print(f"Topic '{topic}' already has complete Batch 1. Skipping.")
            
        # Check if Batch 2 already generated and complete
        b2_qs = [q for q in questions_db if q.get("topic") == topic and q.get("source_exam") == "Practice - Batch 2"]
        if len(b2_qs) < 30:
            if len(b2_qs) > 0:
                print(f"Topic '{topic}' has incomplete Batch 2 ({len(b2_qs)}/30 questions). Re-generating...")
                questions_db = [q for q in questions_db if not (q.get("topic") == topic and q.get("source_exam") == "Practice - Batch 2")]
            batch = generate_batch_for_topic(topic, facts_db[topic], questions_db, "Batch 2")
            if len(batch) >= 30:
                questions_db.extend(batch)
                with open(output_json, "w", encoding="utf-8") as f:
                    json.dump(questions_db, f, indent=2, ensure_ascii=False)
                time.sleep(6)
            else:
                print(f"Warning: Failed to generate complete Batch 2 for '{topic}'. Will retry on next run.")
        else:
            print(f"Topic '{topic}' already has complete Batch 2. Skipping.")
            
    print("\nAll batches generated successfully!")

if __name__ == "__main__":
    main()
