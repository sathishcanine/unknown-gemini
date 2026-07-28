import fitz
import os
import json
import base64
import urllib.request
import urllib.error
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

api_key = os.environ.get("GEMINI_API_KEY")
output_json = "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/Indian-History/history_facts.json"

books = {
    "Gurunath": "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/Data/Indian-History-Data/HISTORY_ENGLISH_Gurunath.pdf",
    "Suresh": "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/Data/Indian-History-Data/Indian_history_suresh_usable.pdf"
}

# Mapping for the remaining topics (Topics 16 to 21)
topics_mapping = {
    "Change & Continuity in Socio-Cultural History of TN": {
        "Gurunath": [77, 78, 79, 80],
        "Suresh": [11, 12, 13, 14, 53, 54, 55, 56, 57, 58]
    },
    "Characteristics of Indian Culture, Unity in Diversity": {
        "Suresh": [22, 23, 24, 25, 26, 27, 64, 65, 66, 67, 68, 69]
    },
    "India as a Secular State & Social Harmony": {
        "Suresh": [28, 29, 30, 70, 71]
    },
    "Places in News": {
        # Dynamic current affairs topic - no static textbook pages
    },
    "Sports": {
        "Suresh": [72]
    },
    "Others": {
        "Gurunath": [32, 33, 34, 35, 93, 94],
        "Suresh": [30]
    }
}

if not api_key:
    print("GEMINI_API_KEY not found.")
    exit(1)

model = "gemini-3.1-flash-lite"
url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
file_lock = threading.Lock()

def call_gemini_extraction(topic_name, book_name, page_num, page_text):
    prompt = f"""
    You are an expert TNPSC Group exam question setter and historian.
    I have extracted a single page of text from the book "{book_name}" (Page {page_num}) for the topic: "{topic_name}".
    Your task is to perform an exhaustive, line-by-line fact extraction of this page. Do not summarize or skip anything.
    
    EXTRACT EVERY SINGLE:
    1. Ruler name, king, dynasty, founder, titles, and dates.
    2. Archaeological towns, excavators, excavation years, and artifacts found.
    3. Battles, years, participants, outcomes, and treaties.
    4. Administrative structures, village structures, revenue terms, and taxes.
    5. Temple/monument names, builders, locations, and styles.
    6. Book titles, authors, poets, languages, travelogues, and rock/pillar edicts.
    
    INSTRUCTIONS:
    - Pull out at least 8-15 distinct factual points if present in the text.
    - Keep each fact extremely concise, factual, and clear.
    - Provide accurate bilingual translations (English & Tamil).
    - Provide historical context.
    
    Format the output as a JSON array of objects:
    [
      {{
        "fact_en": "Verifiable fact statement in English",
        "fact_ta": "Verifiable fact statement in Tamil",
        "source": "{book_name}",
        "context_en": "Historical context details in English",
        "context_ta": "Historical context details in Tamil"
      }}
    ]
    
    Return ONLY the raw JSON string as output. Do not add markdown backticks.
    
    ---
    PAGE TEXT:
    {page_text}
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
                print(f"    {book_name} P{page_num} [Attempt {attempt+1}/{retries}] Rate limited. Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2
            else:
                print(f"    {book_name} P{page_num} [Attempt {attempt+1}/{retries}] HTTP Error {e.code}")
                time.sleep(3)
        except Exception as e:
            print(f"    {book_name} P{page_num} [Attempt {attempt+1}/{retries}] Error: {e}")
            time.sleep(3)
    return []

def normalize_text(text):
    return re.sub(r'[^a-zA-Z0-9\u0b80-\u0bff]', '', text).lower()

def deduplicate_facts(facts_list):
    seen = set()
    deduped = []
    for f in facts_list:
        norm = normalize_text(f.get("fact_en", ""))
        if not norm:
            continue
        if norm not in seen:
            seen.add(norm)
            deduped.append(f)
    return deduped

def process_page_task(topic_name, book_name, page_idx):
    book_path = books[book_name]
    doc = fitz.open(book_path)
    page_text = doc[page_idx].get_text()
    doc.close()
    
    if not page_text.strip():
        return []
        
    facts = call_gemini_extraction(topic_name, book_name, page_idx + 1, page_text)
    return facts

def main():
    print("Starting exhaustive page-by-page fact extraction for Topics 16 to 21...")
    
    db = {}
    if os.path.exists(output_json):
        try:
            with open(output_json, "r", encoding="utf-8") as f:
                db = json.load(f)
            print(f"Loaded existing database with {len(db)} topics.")
        except Exception as e:
            print("Starting fresh database.")
            
    for topic_name, sources in topics_mapping.items():
        if topic_name in db and len(db[topic_name]) > 0:
            print(f"Topic '{topic_name}' already has {len(db[topic_name])} facts. Skipping.")
            continue
            
        print(f"\n>>> Processing topic: '{topic_name}'...")
        
        # Build tasks list for this topic
        tasks = []
        for book_name, page_indices in sources.items():
            for idx in page_indices:
                tasks.append((book_name, idx))
                
        if not tasks:
            print(f"  No pages mapped for '{topic_name}'. Storing empty facts list.")
            db[topic_name] = []
            continue
            
        print(f"  Spawning {len(tasks)} parallel page extraction tasks for '{topic_name}'...")
        topic_facts = []
        
        # Thread pool of size 3 to extract pages in parallel
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(process_page_task, topic_name, book, idx): (book, idx) for book, idx in tasks}
            for future in as_completed(futures):
                book, idx = futures[future]
                try:
                    facts = future.result()
                    print(f"    Page {idx+1} of {book}: Extracted {len(facts)} facts.")
                    topic_facts.extend(facts)
                except Exception as e:
                    print(f"    Error processing Page {idx+1} of {book}: {e}")
                time.sleep(1) # slight spacing
                
        initial_count = len(topic_facts)
        deduped = deduplicate_facts(topic_facts)
        print(f"  Deduplicated for '{topic_name}': {initial_count} -> {len(deduped)} unique facts.")
        
        db[topic_name] = deduped
        
        # Save progress after every topic
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2, ensure_ascii=False)
            
    print("\nExhaustive page-by-page fact extraction for Topics 16 to 21 finished successfully!")

if __name__ == "__main__":
    main()
