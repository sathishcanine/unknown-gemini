import fitz
import os
import json
import base64
import urllib.request
import urllib.error
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise SystemExit("Error: GEMINI_API_KEY environment variable is not set.")

output_json = "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/Chemistry/chemistry_facts.json"

books = {
    "Gurunath": "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/Data/Chemistry-Data/Gurunath_STUDY_MATERIAL_CHEMISTRY_TAMIL.pdf",
    "Iyachamy": "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/Data/Chemistry-Data/GR1_CHEMISTRY_REVISION_NOTES_TAMIL_iyachamy.pdf"
}

# 0-indexed physical page numbers mapped to syllabus topics
topics_mapping = {
    "Elements and Compounds, Periodic Classification of Elements": {
        "Gurunath": list(range(1, 16)),  # Pages 2 to 16
        "Iyachamy": list(range(0, 9)) + list(range(11, 22))  # Pages 1-9, 12-22
    },
    "Acids, Bases, and Salts": {
        "Gurunath": list(range(16, 30)), # Pages 17 to 30
        "Iyachamy": [9, 10] + list(range(22, 29))  # Pages 10-11, 23-29
    },
    "Petroleum Products, Fertilizers, Pesticides": {
        "Gurunath": list(range(71, 77)), # Pages 72 to 77
        "Iyachamy": list(range(29, 39))  # Pages 30 to 39
    }
}

if not api_key:
    print("GEMINI_API_KEY not found.")
    exit(1)

model = "gemini-3.5-flash-lite"
url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

def call_gemini_extraction_text(topic_name, book_name, page_num, page_text):
    prompt = f"""
    You are an expert TNPSC Group exam question setter and chemist.
    I have extracted a single page of text from the book "{book_name}" (Page {page_num}) for the topic: "{topic_name}".
    Your task is to perform an exhaustive, line-by-line fact extraction of this page. Do not summarize or skip anything.
    
    EXTRACT EVERY SINGLE:
    1. Chemical substance, element, compound, alloy, acid, base, salt, ore, metal, non-metal, metalloid, fertilizer, pesticide, or fuel.
    2. Names of chemists, discoverers, and Nobel laureates, along with their discoveries and achievements.
    3. Chemical formulas, equations, compositions, percentages, physical states, colors, odors, and molecular structures.
    4. Industrial processes, manufacturing methods, reactions, laboratory preparation details, and uses/applications in daily life and industries.
    5. Properties, pH values, indicators, periodic trends, group/period characteristics, and classifications.
    
    INSTRUCTIONS:
    - Pull out at least 8-15 distinct factual points if present in the text.
    - Keep each fact extremely concise, factual, and clear.
    - Exclude verbose explanations, conversational descriptions, and generic commentary.
    - Each fact MUST contain a specific entity (name, formula, reaction, process, property, or value).
    - Provide accurate bilingual translations: both English and Tamil.
    - Provide chemical context in both English and Tamil.
    
    Format the output as a JSON array of objects:
    [
      {{
        "fact_en": "Verifiable fact statement in English",
        "fact_ta": "Verifiable fact statement in Tamil",
        "source": "{book_name}",
        "context_en": "Chemical context details in English",
        "context_ta": "Chemical context details in Tamil"
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
    
    return post_request(payload, headers, book_name, page_num)

def call_gemini_extraction_image(topic_name, book_name, page_num, img_base64):
    prompt = f"""
    You are an expert TNPSC Group exam question setter and chemist.
    This is an image of a page from the chemistry study material "{book_name}" (Page {page_num}) for the topic: "{topic_name}".
    Your task is to perform an exhaustive, line-by-line fact extraction of this page. Do not summarize or skip anything.
    
    EXTRACT EVERY SINGLE:
    1. Chemical substance, element, compound, alloy, acid, base, salt, ore, metal, non-metal, metalloid, fertilizer, pesticide, or fuel.
    2. Names of chemists, discoverers, and Nobel laureates, along with their discoveries and achievements.
    3. Chemical formulas, equations, compositions, percentages, physical states, colors, odors, and molecular structures.
    4. Industrial processes, manufacturing methods, reactions, laboratory preparation details, and uses/applications in daily life and industries.
    5. Properties, pH values, indicators, periodic trends, group/period characteristics, and classifications.
    
    INSTRUCTIONS:
    - Pull out at least 8-15 distinct factual points if present in the image.
    - Keep each fact extremely concise, factual, and clear.
    - Exclude verbose explanations, conversational descriptions, and generic commentary.
    - Each fact MUST contain a specific entity (name, formula, reaction, process, property, or value).
    - Provide accurate bilingual translations: both English and Tamil.
    - Provide chemical context in both English and Tamil.
    
    Format the output as a JSON array of objects:
    [
      {{
        "fact_en": "Verifiable fact statement in English",
        "fact_ta": "Verifiable fact statement in Tamil",
        "source": "{book_name}",
        "context_en": "Chemical context details in English",
        "context_ta": "Chemical context details in Tamil"
      }}
    ]
    
    Return ONLY the raw JSON string as output. Do not add markdown backticks.
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
    
    return post_request(payload, headers, book_name, page_num)

def post_request(payload, headers, book_name, page_num):
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
                # Clean up backticks if any
                if raw_text.startswith("```"):
                    raw_text = raw_text.split("\n", 1)[1]
                    if raw_text.endswith("```"):
                        raw_text = raw_text.rsplit("\n", 1)[0]
                return json.loads(raw_text.strip())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"    {book_name} P{page_num} Rate limited (429). Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2
            else:
                attempt += 1
                print(f"    {book_name} P{page_num} [Attempt {attempt}/{retries}] HTTP Error {e.code}")
                time.sleep(5)
        except Exception as e:
            attempt += 1
            print(f"    {book_name} P{page_num} [Attempt {attempt}/{retries}] Error: {e}")
            time.sleep(5)
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
    page_num = page_idx + 1
    
    if book_name == "Gurunath":
        # Gurunath has legacy Tab encoding. Render as image for visual OCR.
        print(f"    {book_name} P{page_num}: Rendering page as image...")
        page = doc[page_idx]
        pix = page.get_pixmap(dpi=150)
        image_bytes = pix.tobytes("jpg")
        img_base64 = base64.b64encode(image_bytes).decode("utf-8")
        doc.close()
        
        print(f"    {book_name} P{page_num}: Querying Gemini API (Image)...")
        facts = call_gemini_extraction_image(topic_name, book_name, page_num, img_base64)
    else:
        # Iyachamy is Unicode. Read text directly.
        page_text = doc[page_idx].get_text()
        doc.close()
        
        if not page_text.strip():
            return []
            
        print(f"    {book_name} P{page_num}: Querying Gemini API (Text)...")
        facts = call_gemini_extraction_text(topic_name, book_name, page_num, page_text)
        
    return facts

def main():
    print("Starting Chemistry page-by-page fact extraction...")
    
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
        
        tasks = []
        for book_name, page_indices in sources.items():
            for idx in page_indices:
                tasks.append((book_name, idx))
                
        if not tasks:
            print(f"  No pages mapped for '{topic_name}'.")
            continue
            
        print(f"  Spawning {len(tasks)} parallel page extraction tasks for '{topic_name}'...")
        topic_facts = []
        
        # Thread pool of size 2 to protect API rate limits (RPM/TPM)
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
                time.sleep(1)
                
        initial_count = len(topic_facts)
        deduped = deduplicate_facts(topic_facts)
        print(f"  Deduplicated for '{topic_name}': {initial_count} -> {len(deduped)} unique facts.")
        
        db[topic_name] = deduped
        
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2, ensure_ascii=False)
            
    print("\nExhaustive page-by-page Chemistry fact extraction finished successfully!")

if __name__ == "__main__":
    main()
