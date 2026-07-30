import os
import json
import subprocess
import time

db_path = "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/Chemistry/chemistry_questions_db.json"
chemistry_topics = [
    "Elements and Compounds, Periodic Classification of Elements",
    "Acids, Bases, and Salts",
    "Petroleum Products, Fertilizers, Pesticides"
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
    print("Starting Chemistry practice question generation runner...")
    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY environment variable is not set.")
        return

    for topic in chemistry_topics:
        print(f"\n**************************************************")
        print(f"PROCESSING TOPIC: '{topic}'")
        print(f"**************************************************")
        
        for batch_num in [1, 2]:
            if check_batch_exists(topic, batch_num):
                print(f"  Batch {batch_num} already exists for '{topic}' (at least 30 questions). Skipping.")
                continue
                
            print(f"  Generating Batch {batch_num} for '{topic}'...")
            cmd = [
                "/Users/sathishkumar/.asdf/installs/python/3.10.16/bin/python3",
                "-u",
                "Chemistry/generate_chemistry_questions.py",
                "--topic", topic,
                "--batch", str(batch_num)
            ]
            
            try:
                subprocess.run(cmd, check=True)
            except subprocess.CalledProcessError as e:
                print(f"  ERROR generating Batch {batch_num} for '{topic}'")
                return
                
            time.sleep(5) # Brief cooldown between batches
            
        print(f"  Topic '{topic}' completed successfully!")
        time.sleep(5)

    print("\nAll Chemistry topics completed successfully!")

if __name__ == "__main__":
    main()
