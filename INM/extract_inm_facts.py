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
output_json = "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/INM/inm_facts.json"

books = {
    "Suresh": "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/Data/INM-Data/INM_suresh_A3_usable.pdf",
    "TAF": "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/Data/INM-Data/INM_taf_usable.pdf"
}

# Complete mapping for all 23 syllabus topics to physical PDF page indices (0-indexed)
topics_mapping = {
    "Advent of Europeans": {
        "Suresh": [20, 21, 22, 23, 24, 25]
    },
    "Early Uprising - Tribal Rebellions": {
        "Suresh": [20, 32, 33, 34]
    },
    "Early Uprising - Vellore Revolt": {
        "Suresh": [23, 24, 25]
    },
    "Early Uprising - 1857 Great Revolt": {
        "Suresh": [34, 35, 36]
    },
    "Early Uprising - Effects of British Rule": {
        "Suresh": [3, 4, 5, 6, 7, 8]
    },
    "National Renaissance": {
        "Suresh": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
    },
    "INC, Growth of Satyagraha & Militants": {
        "Suresh": [37, 38, 39, 40, 41, 42, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77]
    },
    "Communism & Partition": {
        "Suresh": [78, 79, 80, 81, 82, 83, 84]
    },
    "Role of TN in Freedom Struggle": {
        "Suresh": [25, 26, 27, 28, 29, 30, 31]
    },
    "Leaders - Dr. B.R. Ambedkar": {
        "Suresh": [44]
    },
    "Leaders - Gandhi": {
        "Suresh": [43],
        "TAF": [2, 3, 4]
    },
    "Leaders - Nehru": {
        "Suresh": [44]
    },
    "Leaders - Bhagat Singh": {
        "Suresh": [45],
        "TAF": [7, 8]
    },
    "Leaders - Bose": {
        "Suresh": [44],
        "TAF": [9, 10]
    },
    "Leaders - Maulana Abul Kalam Azad": {
        "Suresh": [45],
        "TAF": [5, 6]
    },
    "Leaders - Gokhale": {
        "Suresh": [11, 12]
    },
    "Leaders - Bharathiyar": {
        "Suresh": [46],
        "TAF": [21, 22]
    },
    "Leaders - V.O.C": {
        "Suresh": [46],
        "TAF": [23, 24]
    },
    "Leaders - Kamarajar": {
        "Suresh": [48]
    },
    "Leaders - Periyar": {
        "Suresh": [48, 49, 50],
        "TAF": [25, 26, 27, 28, 29]
    },
    "Leaders - Rajaji": {
        "Suresh": [47]
    },
    "Leaders - Other Leaders": {
        "Suresh": [49, 50, 51, 52],
        "TAF": [11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 30, 31]
    },
    "Newspaper, Magazine, Books": {
        "Suresh": [85, 86, 87, 88, 89, 90, 91, 92]
    }
}

if not api_key:
    print("GEMINI_API_KEY not found.")
    exit(1)

model = "gemini-3.5-flash-lite"
url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
file_lock = threading.Lock()

def call_gemini_extraction(topic_name, book_name, page_num, page_text):
    prompt = f"""
    You are an expert TNPSC Group exam question setter and historian.
    I have extracted a single page of text from the book "{book_name}" (Page {page_num}) for the topic: "{topic_name}".
    Your task is to perform an exhaustive, line-by-line fact extraction of this page. Do not summarize or skip anything.
    
    EXTRACT EVERY SINGLE:
    1. Historical event, movement, organization, political party, and year/date of occurrence.
    2. Names of freedom fighters, reformist leaders, British officials, governors, and kings, along with their roles and achievements.
    3. Newspapers, magazines, books, pamphlets, and patriotic songs published by organizations or leaders.
    4. Legislative acts, commissions, declarations, treaties, pacts, and conferences (e.g., Rowlatt Act, Simon Commission, Wavell Plan).
    5. Details of protests, satyagrahas, uprisings, and rebellion details specific to Tamil Nadu.
    
    INSTRUCTIONS:
    - Pull out at least 8-15 distinct factual points if present in the text.
    - Keep each fact extremely concise, factual, and clear.
    - Exclude verbose explanations, conversational descriptions, and generic commentary.
    - Each fact MUST contain a specific entity (name, date, location, treaty, organization, or coin).
    - Provide accurate bilingual translations: both English and Tamil.
    - Provide historical context in both English and Tamil.
    
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
    
    retries = 5
    delay = 6
    attempt = 0
    while attempt < retries:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                res_data = response.read().decode("utf-8")
                res_json = json.loads(res_data)
                raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                return json.loads(raw_text)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"    {book_name} P{page_num} Rate limited (429). Retrying in {delay}s (does not count as attempt)...")
                time.sleep(delay)
                delay *= 2
            else:
                attempt += 1
                print(f"    {book_name} P{page_num} [Attempt {attempt}/{retries}] HTTP Error {e.code}")
                time.sleep(3)
        except Exception as e:
            attempt += 1
            print(f"    {book_name} P{page_num} [Attempt {attempt}/{retries}] Error: {e}")
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
        
    print(f"    {book_name} P{page_idx + 1}: Querying Gemini API...")
    facts = call_gemini_extraction(topic_name, book_name, page_idx + 1, page_text)
    return facts

def main():
    print("Starting INM page-by-page fact extraction for all remaining topics...")
    
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
            print(f"  No pages mapped for '{topic_name}'.")
            continue
            
        print(f"  Spawning {len(tasks)} parallel page extraction tasks for '{topic_name}'...")
        topic_facts = []
        
        # Thread pool of size 2 to extract pages in parallel
        with ThreadPoolExecutor(max_workers=2) as executor:
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
            
    print("\nExhaustive page-by-page fact extraction finished successfully!")

if __name__ == "__main__":
    main()
