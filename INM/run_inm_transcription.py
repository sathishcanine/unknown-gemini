import os
import sys
import json
import time
import subprocess

# Complete list of 23 topics with page ranges matching the INM PDF index (physical offset of +2)
INM_TOPICS = [
    {"num": 1, "topic": "Advent of Europeans", "start": 3, "end": 7},
    {"num": 2, "topic": "Early Uprising - Tribal Rebellions", "start": 8, "end": 14},
    {"num": 3, "topic": "Early Uprising - Vellore Revolt", "start": 15, "end": 18},
    {"num": 4, "topic": "Early Uprising - 1857 Great Revolt", "start": 19, "end": 25},
    {"num": 5, "topic": "Early Uprising - Effects of British Rule", "start": 26, "end": 33},
    {"num": 6, "topic": "National Renaissance", "start": 34, "end": 65},
    {"num": 7, "topic": "INC, Growth of Satyagraha & Militants", "start": 66, "end": 131},
    {"num": 8, "topic": "Communism & Partition", "start": 132, "end": 142},
    {"num": 9, "topic": "Role of TN in Freedom Struggle", "start": 143, "end": 166},
    {"num": 10, "topic": "Leaders - Dr. B.R. Ambedkar", "start": 167, "end": 174},
    {"num": 11, "topic": "Leaders - Gandhi", "start": 175, "end": 184},
    {"num": 12, "topic": "Leaders - Nehru", "start": 185, "end": 192},
    {"num": 13, "topic": "Leaders - Bhagat Singh", "start": 193, "end": 199},
    {"num": 14, "topic": "Leaders - Bose", "start": 200, "end": 206},
    {"num": 15, "topic": "Leaders - Maulana Abul Kalam Azad", "start": 207, "end": 210},
    {"num": 16, "topic": "Leaders - Gokhale", "start": 211, "end": 214},
    {"num": 17, "topic": "Leaders - Bharathiyar", "start": 215, "end": 217},
    {"num": 18, "topic": "Leaders - V.O.C", "start": 218, "end": 227},
    {"num": 19, "topic": "Leaders - Kamarajar", "start": 228, "end": 232},
    {"num": 20, "topic": "Leaders - Periyar", "start": 233, "end": 243},
    {"num": 21, "topic": "Leaders - Rajaji", "start": 244, "end": 248},
    {"num": 22, "topic": "Leaders - Other Leaders", "start": 249, "end": 253},
    {"num": 23, "topic": "Newspaper, Magazine, Books", "start": 254, "end": 265}
]

status_file = "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/INM/transcription_status.json"

def load_status():
    if os.path.exists(status_file):
        try:
            with open(status_file, "r") as f:
                res = json.load(f)
                if res and len(res) == len(INM_TOPICS):
                    return res
        except Exception:
            pass
    
    # Initialize default pending status for all topics
    default_status = {str(item["num"]): {"topic": item["topic"], "status": "pending"} for item in INM_TOPICS}
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
    total = len(INM_TOPICS)
    completed_count = sum(1 for v in status.values() if v["status"] == "completed")
    print(f"=== Indian National Movement (INM) PYQ Transcription Queue Runner ===")
    print(f"Total Topics: {total} | Completed: {completed_count} | Remaining: {total - completed_count}\n")
    
    for item in INM_TOPICS:
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
            "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/INM/transcribe_inm_pyqs.py",
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
