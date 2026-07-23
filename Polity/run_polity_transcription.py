import os
import sys
import json
import time
import subprocess

# Complete list of 32 topics with page ranges matching the PDF index
POLITY_TOPICS = [
    {"num": 1, "topic": "Constitution of India", "start": 3, "end": 22},
    {"num": 2, "topic": "Preamble", "start": 23, "end": 37},
    {"num": 3, "topic": "Salient Features of Constitution", "start": 38, "end": 45},
    {"num": 4, "topic": "Union, States & its Union Territories", "start": 46, "end": 57},
    {"num": 5, "topic": "Citizenship", "start": 58, "end": 69},
    {"num": 6, "topic": "Fundamental Rights", "start": 70, "end": 107},
    {"num": 7, "topic": "DPSP", "start": 108, "end": 131},
    {"num": 8, "topic": "Fundamental Duties", "start": 132, "end": 145},
    {"num": 9, "topic": "Union Executive", "start": 146, "end": 174},
    {"num": 10, "topic": "Union Parliament", "start": 175, "end": 201},
    {"num": 11, "topic": "Attorney General of India", "start": 202, "end": 203},
    {"num": 12, "topic": "CAG of India", "start": 204, "end": 204},
    {"num": 13, "topic": "State Executive", "start": 205, "end": 216},
    {"num": 14, "topic": "State Legislature", "start": 217, "end": 223},
    {"num": 15, "topic": "State Advocate General", "start": 224, "end": 224},
    {"num": 16, "topic": "Local Self Government", "start": 225, "end": 247},
    {"num": 17, "topic": "Centre & State Spirit of Federalism", "start": 248, "end": 268},
    {"num": 18, "topic": "Election", "start": 269, "end": 280},
    {"num": 19, "topic": "Judiciary", "start": 281, "end": 304},
    {"num": 20, "topic": "Rule of Law", "start": 305, "end": 306},
    {"num": 21, "topic": "Official Languages", "start": 307, "end": 308},
    {"num": 22, "topic": "Emergency Provisions", "start": 309, "end": 312},
    {"num": 23, "topic": "Anticorruption Measures", "start": 313, "end": 327},
    {"num": 24, "topic": "Right to Information (RTI)", "start": 328, "end": 338},
    {"num": 25, "topic": "Human Rights Charter", "start": 339, "end": 348},
    {"num": 26, "topic": "Pressure Groups", "start": 349, "end": 349},
    {"num": 27, "topic": "Consumer Protection Forum", "start": 350, "end": 352},
    {"num": 28, "topic": "Women Empowerment", "start": 353, "end": 358},
    {"num": 29, "topic": "Political Parties", "start": 359, "end": 373},
    {"num": 30, "topic": "Important Acts & Articles", "start": 374, "end": 390},
    {"num": 31, "topic": "Important SC Judgements", "start": 391, "end": 398},
    {"num": 32, "topic": "Committees & Commissions", "start": 399, "end": 408}
]

status_file = "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/Polity/transcription_status.json"

def load_status():
    if os.path.exists(status_file):
        try:
            with open(status_file, "r") as f:
                return json.load(f)
        except Exception:
            pass
    
    # Initialize default pending status for all topics
    default_status = {str(item["num"]): {"topic": item["topic"], "status": "pending"} for item in POLITY_TOPICS}
    save_status(default_status)
    return default_status

def save_status(status):
    with open(status_file, "w") as f:
        json.dump(status, f, indent=2)

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        sys.exit(1)
        
    status = load_status()
    
    # Count stats
    total = len(POLITY_TOPICS)
    completed_count = sum(1 for v in status.values() if v["status"] == "completed")
    print(f"=== Indian Polity PYQ Transcription Queue Runner ===")
    print(f"Total Topics: {total} | Completed: {completed_count} | Remaining: {total - completed_count}\n")
    
    for item in POLITY_TOPICS:
        num_str = str(item["num"])
        topic_name = item["topic"]
        start_page = item["start"]
        end_page = item["end"]
        
        topic_status = status.get(num_str, {}).get("status", "pending")
        if topic_status == "completed":
            print(f"Topic {item['num']}/{total}: '{topic_name}' - ALREADY COMPLETED. Skipping.")
            continue
            
        print(f"\n>>> Topic {item['num']}/{total}: Processing '{topic_name}' (Physical Pages {start_page} to {end_page})...")
        status[num_str]["status"] = "in_progress"
        save_status(status)
        
        # Invoke the transcribe script as a subprocess
        cmd = [
            sys.executable,
            "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/Polity/transcribe_polity_pyqs.py",
            "--start", str(start_page),
            "--end", str(end_page),
            "--topic", topic_name
        ]
        
        try:
            # Run transcription synchronously
            res = subprocess.run(cmd, check=True)
            if res.returncode == 0:
                print(f"✔ Topic {item['num']}: '{topic_name}' - TRANSCRIPTION SUCCESSFUL!")
                status[num_str]["status"] = "completed"
                save_status(status)
            else:
                print(f"✖ Topic {item['num']}: '{topic_name}' - Transcription failed with exit code {res.returncode}")
                status[num_str]["status"] = "failed"
                save_status(status)
                
        except subprocess.CalledProcessError as e:
            print(f"✖ Topic {item['num']}: '{topic_name}' - Subprocess raised error: {e}")
            status[num_str]["status"] = "failed"
            save_status(status)
        except Exception as e:
            print(f"✖ Topic {item['num']}: '{topic_name}' - Unexpected error: {e}")
            status[num_str]["status"] = "failed"
            save_status(status)
            
        # Cooldown delay between topics to respect rate limits
        cooldown = 15
        print(f"Sleeping for {cooldown} seconds before the next topic...")
        time.sleep(cooldown)

    print("\n=== QUEUE COMPLETED ===")

if __name__ == "__main__":
    main()
