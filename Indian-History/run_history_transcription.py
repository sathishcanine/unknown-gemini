import os
import sys
import json
import time
import subprocess

# Complete list of 21 topics with page ranges matching the PDF index (+2 offset)
HISTORY_TOPICS = [
    {"num": 1, "topic": "Prehistoric Period", "start": 3, "end": 9},
    {"num": 2, "topic": "Indus Valley Civilization", "start": 10, "end": 39},
    {"num": 3, "topic": "Vedic Period", "start": 40, "end": 43},
    {"num": 4, "topic": "Buddhism & Jainism", "start": 44, "end": 50},
    {"num": 5, "topic": "Mauryan Empire", "start": 51, "end": 54},
    {"num": 6, "topic": "Guptas", "start": 55, "end": 75},
    {"num": 7, "topic": "Delhi Sultanate", "start": 76, "end": 98},
    {"num": 8, "topic": "Mughal Empire", "start": 99, "end": 128},
    {"num": 9, "topic": "Marathas", "start": 129, "end": 139},
    {"num": 10, "topic": "Vijayanagar & Bahmani Kingdoms", "start": 140, "end": 161},
    {"num": 11, "topic": "Pallavas", "start": 162, "end": 167},
    {"num": 12, "topic": "Cheras", "start": 168, "end": 170},
    {"num": 13, "topic": "Cholas", "start": 171, "end": 180},
    {"num": 14, "topic": "Pandiyas", "start": 181, "end": 183},
    {"num": 15, "topic": "Chalukyas & Rashtrakutas", "start": 184, "end": 187},
    {"num": 16, "topic": "Change & Continuity in Socio-Cultural History of TN", "start": 188, "end": 194},
    {"num": 17, "topic": "Characteristics of Indian Culture, Unity in Diversity", "start": 195, "end": 207},
    {"num": 18, "topic": "India as a Secular State & Social Harmony", "start": 208, "end": 214},
    {"num": 19, "topic": "Places in News", "start": 215, "end": 216},
    {"num": 20, "topic": "Sports", "start": 217, "end": 218},
    {"num": 21, "topic": "Others", "start": 219, "end": 230}
]

status_file = "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/Indian-History/transcription_status.json"

def load_status():
    if os.path.exists(status_file):
        try:
            with open(status_file, "r") as f:
                return json.load(f)
        except Exception:
            pass
    
    # Initialize default pending status for all topics
    default_status = {str(item["num"]): {"topic": item["topic"], "status": "pending"} for item in HISTORY_TOPICS}
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
    total = len(HISTORY_TOPICS)
    completed_count = sum(1 for v in status.values() if v["status"] == "completed")
    print(f"=== Indian History PYQ Transcription Queue Runner ===")
    print(f"Total Topics: {total} | Completed: {completed_count} | Remaining: {total - completed_count}\n")
    
    for item in HISTORY_TOPICS:
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
            "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/Indian-History/transcribe_history_pyqs.py",
            "--start", str(start_page),
            "--end", str(end_page),
            "--topic", topic_name
        ]
        
        try:
            result = subprocess.run(cmd, check=True)
            if result.returncode == 0:
                status[num_str]["status"] = "completed"
                print(f"Topic {item['num']}/{total}: '{topic_name}' - SUCCESS!")
            else:
                status[num_str]["status"] = "failed"
                print(f"Topic {item['num']}/{total}: '{topic_name}' - FAILED with return code {result.returncode}")
        except subprocess.CalledProcessError as e:
            status[num_str]["status"] = "failed"
            print(f"Topic {item['num']}/{total}: '{topic_name}' - EXCEPTION: {e}")
        
        save_status(status)
        time.sleep(2)
        
    print("\n=== All History Topics Processed! ===")

if __name__ == "__main__":
    main()
