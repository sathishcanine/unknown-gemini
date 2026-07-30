import fitz
import os
import json
import base64
import urllib.request
import urllib.error
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise SystemExit("Error: GEMINI_API_KEY environment variable is not set.")

pdf_path = "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/Data/Chemistry-Data/11th & 12th chemistry_book_back_questions.pdf"
cache_path = "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/Chemistry/book_back_raw_cache.json"
db_path = "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/Chemistry/chemistry_questions_db.json"

model = "gemini-3.5-flash-lite"
url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

cache_lock = threading.Lock()
raw_data_cache = {}

if os.path.exists(cache_path):
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            raw_data_cache = json.load(f)
        print(f"Loaded cache: {len(raw_data_cache)} pages already processed.")
    except Exception as e:
        print(f"Error loading cache: {e}")

# Build Page Mapping (physical 0-indexed page numbers)
page_mapping = {}

# 11th Standard mapping (pages 2 to 61 -> indices 1 to 60)
for p in range(1, 4): page_mapping[p] = ("11th Chemistry - Book back Questions", "Unit 1")
for p in range(4, 8): page_mapping[p] = ("11th Chemistry - Book back Questions", "Unit 2")
for p in range(8, 11): page_mapping[p] = ("11th Chemistry - Book back Questions", "Unit 3")
for p in range(11, 14): page_mapping[p] = ("11th Chemistry - Book back Questions", "Unit 4")
for p in range(14, 18): page_mapping[p] = ("11th Chemistry - Book back Questions", "Unit 5")
for p in range(18, 22): page_mapping[p] = ("11th Chemistry - Book back Questions", "Unit 6")
for p in range(22, 25): page_mapping[p] = ("11th Chemistry - Book back Questions", "Unit 7")
for p in range(25, 30): page_mapping[p] = ("11th Chemistry - Book back Questions", "Unit 8")
for p in range(30, 34): page_mapping[p] = ("11th Chemistry - Book back Questions", "Unit 9")
for p in range(34, 38): page_mapping[p] = ("11th Chemistry - Book back Questions", "Unit 10")
for p in range(38, 44): page_mapping[p] = ("11th Chemistry - Book back Questions", "Unit 11")
for p in range(44, 46): page_mapping[p] = ("11th Chemistry - Book back Questions", "Unit 12")
for p in range(46, 53): page_mapping[p] = ("11th Chemistry - Book back Questions", "Unit 13")
for p in range(53, 58): page_mapping[p] = ("11th Chemistry - Book back Questions", "Unit 14")
for p in range(58, 61): page_mapping[p] = ("11th Chemistry - Book back Questions", "Unit 15")

# 12th Standard mapping (pages 62 to 118 -> indices 61 to 117)
for p in range(61, 66): page_mapping[p] = ("12th Chemistry - Book back Questions", "Unit 1")
for p in range(66, 68): page_mapping[p] = ("12th Chemistry - Book back Questions", "Unit 2")
for p in range(68, 70): page_mapping[p] = ("12th Chemistry - Book back Questions", "Unit 3")
for p in range(70, 73): page_mapping[p] = ("12th Chemistry - Book back Questions", "Unit 4")
for p in range(73, 76): page_mapping[p] = ("12th Chemistry - Book back Questions", "Unit 5")
for p in range(76, 79): page_mapping[p] = ("12th Chemistry - Book back Questions", "Unit 6")
for p in range(79, 84): page_mapping[p] = ("12th Chemistry - Book back Questions", "Unit 7")
page_mapping[84] = ("12th Chemistry - Book back Questions", "Unit 8")
for p in range(85, 88): page_mapping[p] = ("12th Chemistry - Book back Questions", "Unit 8")
for p in range(88, 93): page_mapping[p] = ("12th Chemistry - Book back Questions", "Unit 9")
for p in range(93, 96): page_mapping[p] = ("12th Chemistry - Book back Questions", "Unit 10")
for p in range(96, 100): page_mapping[p] = ("12th Chemistry - Book back Questions", "Unit 11")
for p in range(100, 106): page_mapping[p] = ("12th Chemistry - Book back Questions", "Unit 12")
for p in range(106, 111): page_mapping[p] = ("12th Chemistry - Book back Questions", "Unit 13")
for p in range(111, 114): page_mapping[p] = ("12th Chemistry - Book back Questions", "Unit 14")
for p in range(114, 118): page_mapping[p] = ("12th Chemistry - Book back Questions", "Unit 15")


def call_gemini_extraction(img_base64, page_num):
    prompt = """
This is an image of a page from a Tamil chemistry textbook compilation containing book-back multiple-choice questions.
The page contains questions in Tamil script, along with options and answer keys (marked with "tpil: <option>" or "விடை: <option>", where option is a, b, c, d / அ, ஆ, இ, ஈ).

Please extract all the multiple choice questions from this page.
For each question:
1. Transcribe the Tamil question and translate it to English.
2. Transcribe the 4 Tamil options (அ, ஆ, இ, ஈ) and translate them to English.
3. Identify the correct answer option (marked by "tpil:" or "விடை:") and map it to one of the 4 options:
   - "m" or "அ" maps to Option A
   - "M" or "ஆ" maps to Option B
   - "," or "இ" maps to Option C
   - "<" or "ஈ" maps to Option D
4. Generate a detailed bilingual explanation in English and Tamil for the correct answer.

Output the result STRICTLY as a JSON array of objects (no markdown blocks or backticks) with the exact structure:
[
  {
    "question_en": "Question text in English",
    "question_ta": "Question text in Tamil",
    "options_en": {
      "A": "Option A text in English",
      "B": "Option B text in English",
      "C": "Option C text in English",
      "D": "Option D text in English"
    },
    "options_ta": {
      "A": "Option A text in Tamil",
      "B": "Option B text in Tamil",
      "C": "Option C text in Tamil",
      "D": "Option D text in Tamil"
    },
    "correct_option": "A" | "B" | "C" | "D",
    "explanation_en": "Detailed explanation of correct answer in English",
    "explanation_ta": "Detailed explanation of correct answer in Tamil"
  }
]
"""

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": img_base64
                        }
                    }
                ]
            }
        ],
        "generationConfig": {"responseMimeType": "application/json"}
    }
    headers = {"Content-Type": "application/json"}
    
    retries = 5
    delay = 10
    attempt = 0
    while attempt < retries:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                res_data = response.read().decode("utf-8")
                res_json = json.loads(res_data)
                raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                if raw_text.startswith("```"):
                    raw_text = raw_text.split("\n", 1)[1]
                    if raw_text.endswith("```"):
                        raw_text = raw_text.rsplit("\n", 1)[0]
                return json.loads(raw_text.strip())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"    Page {page_num} Rate limited (429). Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2
            else:
                attempt += 1
                print(f"    Page {page_num} [Attempt {attempt}/{retries}] HTTP Error {e.code}")
                time.sleep(5)
        except Exception as e:
            attempt += 1
            print(f"    Page {page_num} [Attempt {attempt}/{retries}] Error: {e}")
            time.sleep(5)
    return []

def process_page(page_idx):
    page_num = page_idx + 1
    page_key = f"page_{page_num}"
    
    # Check cache
    with cache_lock:
        if page_key in raw_data_cache:
            return page_num, raw_data_cache[page_key]
            
    doc = fitz.open(pdf_path)
    page = doc[page_idx]
    pix = page.get_pixmap(dpi=150)
    image_bytes = pix.tobytes("jpg")
    img_base64 = base64.b64encode(image_bytes).decode("utf-8")
    doc.close()
    
    print(f"  Page {page_num}: Querying Gemini API...")
    questions = call_gemini_extraction(img_base64, page_num)
    
    if questions:
        with cache_lock:
            raw_data_cache[page_key] = questions
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(raw_data_cache, f, indent=2, ensure_ascii=False)
        print(f"  Page {page_num}: Extracted {len(questions)} questions.")
        return page_num, questions
    else:
        print(f"  Page {page_num}: Extraction failed.")
        return page_num, []

def compile_database():
    print("\nCompiling final database and adding Option E...")
    
    new_questions = []
    
    for page_key, questions in raw_data_cache.items():
        if not questions:
            continue
            
        page_num = int(page_key.split("_")[1])
        page_idx = page_num - 1
        
        if page_idx not in page_mapping:
            continue
            
        topic, unit = page_mapping[page_idx]
        
        for q in questions:
            # Verify required keys
            required = ["question_en", "question_ta", "options_en", "options_ta", "correct_option", "explanation_en", "explanation_ta"]
            if not all(k in q for k in required):
                continue
                
            correct_opt = q["correct_option"].strip().upper()
            if correct_opt not in ["A", "B", "C", "D"]:
                continue
                
            standard_options = []
            keys_map = ["A", "B", "C", "D"]
            for k in keys_map:
                txt_en = q["options_en"].get(k, q["options_en"].get(k.lower(), "")).strip()
                txt_ta = q["options_ta"].get(k, q["options_ta"].get(k.lower(), "")).strip()
                standard_options.append({
                    "key": k,
                    "text_en": txt_en,
                    "text_ta": txt_ta
                })
                
            # Add Option E
            standard_options.append({
                "key": "E",
                "text_en": "Answer not known",
                "text_ta": "விடை தெரியவில்லை"
            })
            
            db_q = {
                "subject": "Chemistry",
                "topic": topic,
                "source_exam": topic,
                "difficulty": "Medium",
                "question_en": q["question_en"].strip(),
                "question_ta": q["question_ta"].strip(),
                "options": standard_options,
                "correct_option": correct_opt,
                "explanation": q["explanation_en"].strip(),
                "explanation_ta": q["explanation_ta"].strip(),
                "type": "practice",
                "batch": unit,
                "group": "Practice"
            }
            new_questions.append(db_q)
            
    # Load existing database
    existing_questions = []
    if os.path.exists(db_path):
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                existing_questions = json.load(f)
            print(f"Loaded existing database with {len(existing_questions)} questions.")
        except Exception as e:
            print(f"Error loading existing database: {e}")
            
    # Remove existing book back questions to avoid duplicates on rerun
    cleaned_existing = [
        q for q in existing_questions 
        if q.get("topic") not in ["11th Chemistry - Book back Questions", "12th Chemistry - Book back Questions"]
    ]
    
    total_db_questions = cleaned_existing + new_questions
    
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(total_db_questions, f, indent=2, ensure_ascii=False)
        
    print(f"SUCCESS: Compiled and saved {len(new_questions)} book back questions!")
    print(f"Total database questions now: {len(total_db_questions)}")

def main():
    doc = fitz.open(pdf_path)
    num_pages = len(doc)
    doc.close()
    
    print(f"Total Pages in PDF: {num_pages}")
    
    # Only process pages 2 to 118 (indices 1 to 117)
    pages_to_process = list(range(1, num_pages))
    
    # ThreadPoolExecutor to run tasks in parallel
    print(f"Spawning parallel page extraction tasks for {len(pages_to_process)} pages...")
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(process_page, idx): idx for idx in pages_to_process}
        for future in as_completed(futures):
            idx = futures[future]
            try:
                page_num, qs = future.result()
            except Exception as e:
                print(f"  Error on page {idx+1}: {e}")
            time.sleep(0.5)
            
    compile_database()

if __name__ == "__main__":
    main()
