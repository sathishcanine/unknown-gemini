import os
import json
import subprocess
import time

db_path = "INM/inm_questions_db.json"
remaining_topics = [
    "Leaders - Bose",
    "Leaders - Maulana Abul Kalam Azad",
    "Leaders - Gokhale",
    "Leaders - Bharathiyar",
    "Leaders - V.O.C",
    "Leaders - Kamarajar",
    "Leaders - Periyar",
    "Leaders - Rajaji",
    "Leaders - Other Leaders",
    "Newspaper, Magazine, Books"
]

def check_batch_exists(topic, batch_num):
    if not os.path.exists(db_path):
        return False
    try:
        with open(db_path, "r", encoding="utf-8") as f:
            questions = json.load(f)
        matching = [
            q for q in questions 
            if q.get("topic") == topic 
            and q.get("batch") == f"Batch {batch_num}"
            and q.get("type") == "practice"
        ]
        return len(matching) >= 30
    except Exception as e:
        print(f"Error checking database: {e}")
        return False

def validate_topic(topic):
    if not os.path.exists(db_path):
        print(f"Error: Database file does not exist.")
        return False
        
    with open(db_path, "r", encoding="utf-8") as f:
        db = json.load(f)
        
    topic_q = [q for q in db if q.get("topic") == topic and q.get("type") == "practice"]
    
    print(f"\n==========================================")
    print(f"Validation Report for Topic: '{topic}'")
    print(f"Total practice questions found: {len(topic_q)}")
    print(f"==========================================")
    
    batch1 = [q for q in topic_q if q.get("batch") == "Batch 1"]
    batch2 = [q for q in topic_q if q.get("batch") == "Batch 2"]
    print(f"Batch 1: {len(batch1)} questions")
    print(f"Batch 2: {len(batch2)} questions")
    print("------------------------------------------")
    
    errors = []
    warnings = []
    match_q_count = 0
    
    for i, q in enumerate(topic_q):
        label = f"[{q.get('batch')} Q{i+1}]"
        
        # 1. Check all required fields are present and non-empty
        required = ["question_en", "question_ta", "options", "correct_option", "explanation", "explanation_ta", "difficulty"]
        for field in required:
            if field not in q:
                errors.append(f"{label} Missing field '{field}'")
            elif not q[field] and field != "options":
                errors.append(f"{label} Empty field '{field}'")
                
        # 2. Check options structure
        options = q.get("options", [])
        if not isinstance(options, list) or len(options) != 5:
            errors.append(f"{label} Options must be a list of exactly 5 elements.")
        else:
            for idx, opt in enumerate(options):
                for field in ["key", "text_en", "text_ta"]:
                    if field not in opt:
                        errors.append(f"{label} Option {idx+1} missing field '{field}'")
                    elif not opt[field]:
                        errors.append(f"{label} Option {idx+1} has empty field '{field}'")
            
            keys = [opt.get("key") for opt in options]
            if keys != ["A", "B", "C", "D", "E"]:
                errors.append(f"{label} Options keys must be ['A', 'B', 'C', 'D', 'E'], got {keys}")
                
            opt_e = options[4]
            if opt_e.get("text_en") != "Answer not known" or opt_e.get("text_ta") != "விடை தெரியவில்லை":
                errors.append(f"{label} Option E text is incorrect")
                
            correct = q.get("correct_option")
            if correct not in ["A", "B", "C", "D"]:
                errors.append(f"{label} Correct option must be A, B, C, or D, got '{correct}'")
                
        # 3. Check combined length constraint (minimum 180 characters total)
        q_len = len(q.get("question_en", ""))
        exp_len = len(q.get("explanation", ""))
        total_len = q_len + exp_len
        if total_len < 180:
            warnings.append(f"{label} Combined Question + Explanation length is only {total_len} chars")
            
        # 4. Check Match layout structure
        is_match = False
        if "match" in q.get("question_en", "").lower() or "பொருத்து" in q.get("question_ta", "").lower():
            is_match = True
            match_q_count += 1
            
        if is_match:
            q_en = q.get("question_en", "")
            q_ta = q.get("question_ta", "")
            
            has_left_en = (all(x in q_en for x in ["I.", "II.", "III.", "IV."]) or 
                           all(x in q_en for x in ["I -", "II -", "III -", "IV -"]) or
                           all(x in q_en for x in ["a)", "b)", "c)", "d)"]) or
                           all(x in q_en for x in ["a.", "b.", "c.", "d."]) or
                           all(x in q_en for x in ["a -", "b -", "c -", "d -"]))
            has_right_en = (all(x in q_en for x in ["1.", "2.", "3.", "4."]) or 
                            all(x in q_en for x in ["1 -", "2 -", "3 -", "4 -"]))
            
            has_left_ta = (all(x in q_ta for x in ["I.", "II.", "III.", "IV."]) or 
                           all(x in q_ta for x in ["I -", "II -", "III -", "IV -"]) or
                           all(x in q_ta for x in ["a)", "b)", "c)", "d)"]) or
                           all(x in q_ta for x in ["a.", "b.", "c.", "d."]) or
                           all(x in q_ta for x in ["a -", "b -", "c -", "d -"]) or
                           all(x in q_ta for x in ["அ)", "ஆ)", "இ)", "ஈ)"]) or
                           all(x in q_ta for x in ["அ.", "ஆ.", "இ.", "ஈ."]) or
                           all(x in q_ta for x in ["அ -", "ஆ -", "இ -", "ஈ -"]))
            has_right_ta = (all(x in q_ta for x in ["1.", "2.", "3.", "4."]) or 
                            all(x in q_ta for x in ["1 -", "2 -", "3 -", "4 -"]))
            
            if not (has_left_en and has_right_en):
                errors.append(f"{label} Match question (EN) does not follow strict 4x4 format.")
            if not (has_left_ta and has_right_ta):
                errors.append(f"{label} Match question (TA) does not follow strict 4x4 format.")

    print(f"Total Match Questions audited: {match_q_count}")
    print(f"Validation Errors: {len(errors)}")
    for err in errors:
        print(f" - ERROR: {err}")
    print(f"Validation Warnings: {len(warnings)}")
    for warn in warnings:
        print(f" - WARNING: {warn}")
        
    if len(errors) == 0:
        print("SUCCESS: All questions are 100% compliant with standard layout, keys, and TNPSC match guidelines!")
        return True
    else:
        print("FAILURE: Compliance issues found.")
        return False

def main():
    print("Starting generation and real-time validation runner for remaining INM syllabus topics...")
    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY environment variable is not set.")
        return

    for topic in remaining_topics:
        print(f"\n**************************************************")
        print(f"PROCESSING TOPIC: '{topic}'")
        print(f"**************************************************")
        
        for batch_num in [1, 2]:
            if check_batch_exists(topic, batch_num):
                print(f"  Batch {batch_num} already exists for '{topic}' (at least 30 questions). Skipping.")
                continue
                
            print(f"  Generating Batch {batch_num} for '{topic}'...")
            cmd = [
                "python3",
                "-u",
                "INM/generate_inm_questions.py",
                "--topic", topic,
                "--batch", str(batch_num)
            ]
            
            try:
                subprocess.run(cmd, check=True)
            except subprocess.CalledProcessError as e:
                print(f"  ERROR generating Batch {batch_num} for '{topic}'")
                return
                
            time.sleep(5) # brief cooldown between batches to protect RPM limits
            
        # Post-topic real-time validation
        success = validate_topic(topic)
        if not success:
            print(f"  Validation failed for topic '{topic}'. Stopping execution to inspect.")
            return
            
        print(f"  Topic '{topic}' completed and validated successfully!")
        time.sleep(5)

    print("\nAll remaining topics completed and validated successfully!")

if __name__ == "__main__":
    main()
