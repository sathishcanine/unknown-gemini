import os
import json
import subprocess
import time

db_path = "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/INM/inm_questions_db.json"
topics = [
    "Advent of Europeans",
    "Early Uprising - Tribal Rebellions",
    "Early Uprising - Vellore Revolt",
    "Early Uprising - 1857 Great Revolt",
    "Early Uprising - Effects of British Rule",
    "National Renaissance",
    "INC, Growth of Satyagraha & Militants",
    "Communism & Partition",
    "Role of TN in Freedom Struggle",
    "Leaders - Dr. B.R. Ambedkar",
    "Leaders - Gandhi",
    "Leaders - Nehru",
    "Leaders - Bhagat Singh",
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

def main():
    print("Starting practice question generation runner for INM syllabus topics...")
    
    for topic in topics:
        print(f"\n==========================================")
        print(f"Topic: '{topic}'")
        print(f"==========================================")
        
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
            
            # Execute and stream output in real-time
            try:
                subprocess.run(cmd, check=True)
            except subprocess.CalledProcessError as e:
                print(f"  ERROR generating Batch {batch_num} for '{topic}'")
                # We stop execution on first error to let user debug
                return
                
            time.sleep(2) # brief delay between API queries

    print("\nAll batch generation tasks completed successfully!")

if __name__ == "__main__":
    main()
