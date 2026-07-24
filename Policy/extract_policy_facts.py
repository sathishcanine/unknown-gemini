import os
import sys
import json
import time
import urllib.request
import urllib.error
import fitz  # PyMuPDF

# API KEY from environment
API_KEY = os.environ.get("GEMINI_API_KEY")

# Mapping of PDF files to canonical Topic names
PDF_TOPICS = {
    "Gist_ADIDRAVIDAR_TRIBAL_Welfare_PolicyNote2025_Tnpsc_Developer_Academy.pdf": "Adi Dravidar and Tribal Welfare",
    "Gist_AGRICULTURE_PolicyNote2025_Tnpsc_Developer_Academy.pdf": "Agriculture",
    "Gist_DifferentlyAbledPersons_PolicyNote2025_Tnpsc_Developer_Academy.pdf": "Differently Abled Persons",
    "Gist_ENERGY_PolicyNote2025_Tnpsc_Developer_Academy.pdf": "Energy",
    "Gist_Environment_PolicyNote2025_Tnpsc_Developer_Academy.pdf": "Environment",
    "Gist_FOREST_PolicyNote2025_Tnpsc_Developer_Academy_protected.pdf": "Forest",
    "Gist_HEALTH_PolicyNote2025_Tnpsc_Developer_Academy_protected.pdf": "Health",
    "Gist_HIGHER_EDUCATION_PolicyNote2025_Tnpsc_Developer_Academy_protected.pdf": "Higher Education",
    "Gist_INDUSTRY_PolicyNote2025_Tnpsc_Developer_Academy.pdf": "Industry",
    "Gist_IT_PolicyNote2025_Tnpsc_Developer_Academy_protected.pdf": "IT",
    "Gist_LABOUR_Welfare_PolicyNote2025_Tnpsc_Developer_Academy.pdf": "Labour Welfare",
    "Gist_MSME_PolicyNote2025_Tnpsc_Developer_Academy_protected.pdf": "MSME",
    "Gist_NATURAL_RESOURCES_PolicyNote2025_Tnpsc_Developer_Academy.pdf": "Natural Resources",
    "Gist_REVENUE_DISASTER_PolicyNote2025_Tnpsc_Developer_Academy.pdf": "Revenue & Disaster",
    "Gist_RURAL_PolicyNote2025_Tnpsc_Developer_Academy_protected.pdf": "Rural",
    "Gist_SCHOOL_EDUCATION_PolicyNote2025_Tnpsc_Developer_Academy_protected.pdf": "School Education",
    "Gist_SOCIALWELFARE_PolicyNote2025_Tnpsc_Developer_Academy_protected.pdf": "Social Welfare",
    "Gist_SPECIAL_PROG_Implementation_PolicyNote2025_Tnpsc_Developer_Academy_protected.pdf": "Special Program Implementation",
    "Gist_TAMIL_DEVELOPMENT_PolicyNote2025_Tnpsc_Developer_Academy_protected.pdf": "Tamil Development"
}

def call_gemini_extraction(text_segment, topic, round_num, api_key):
    """Sends a policy note text segment to Gemini to extract all factual statements."""
    prompt = f"""
You are an expert TNPSC fact extractor specialized in Tamil Nadu Government Policy Notes.
Extract every single factual statement, budget allocation, scheme name, target metric, statistical data, launch date, and department action about the topic "{topic}" from the text below.
This is Round {round_num} of extraction.

Specifically search for and extract details regarding:
- Budgets allocated for the department, specific projects, or welfare schemes in Tamil Nadu.
- Scheme names, target beneficiaries, eligibility criteria, and financial assistance details.
- State Directorates, Boards, Corporations, and their administrative roles/responsibilities.
- Acts, Rules, Legislative measures, and departmental policies.
- Departmental statistics, targets, and implementation timelines.

For each fact, output a JSON object with:
- "fact_en": The factual statement in English (clear, concise, self-contained, and complete)
- "fact_ta": The exact translation of the fact in Tamil
- "source": A short note of the source (e.g. "Social Welfare Policy Note 2025 Page 12")

Rules:
1. Only extract direct facts present in the text.
2. Ensure facts are atomic (each testing one specific piece of information).
3. Do not include opinions or soft concepts.
4. Output a raw JSON array of objects. Do not wrap in markdown or include introductions.
"""

    model = "gemini-3.1-flash-lite"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {"text": f"--- POLICY NOTE TEXT ---\n{text_segment}"}
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    headers = {"Content-Type": "application/json"}
    
    # Retry loop
    for attempt in range(4):
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                res_data = response.read().decode("utf-8")
                res_json = json.loads(res_data)
                raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                
                # Clean and parse JSON array
                start_idx = raw_text.find('[')
                if start_idx != -1:
                    count = 0
                    for idx in range(start_idx, len(raw_text)):
                        if raw_text[idx] == '[':
                            count += 1
                        elif raw_text[idx] == ']':
                            count -= 1
                            if count == 0:
                                raw_text = raw_text[start_idx:idx+1]
                                break
                return json.loads(raw_text)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait_time = 75 + (attempt * 10)
                print(f"  Rate limited (429) on attempt {attempt+1}/4. Waiting {wait_time}s...", flush=True)
                time.sleep(wait_time)
            elif e.code == 503:
                wait_time = 35 + (attempt * 10)
                print(f"  Service unavailable (503) on attempt {attempt+1}/4. Waiting {wait_time}s...", flush=True)
                time.sleep(wait_time)
            else:
                print(f"  HTTP Error in Round {round_num}: {e.code} - {e.read().decode('utf-8', errors='ignore')}", flush=True)
                break
        except (urllib.error.URLError, Exception) as e:
            wait_time = 15 + (attempt * 10)
            print(f"  Network error ({e}) on attempt {attempt+1}/4. Waiting {wait_time}s...", flush=True)
            time.sleep(wait_time)
            
    return []

def main():
    api_key = API_KEY
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        sys.exit(1)
    facts_file = "Policy/policy_facts.json"
    facts_data = {}
    if os.path.exists(facts_file):
        with open(facts_file, "r", encoding="utf-8") as f:
            try:
                facts_data = json.load(f)
            except Exception:
                facts_data = {}

    def normalize(text):
        return "".join(c for c in text.lower() if c.isalnum())

    for filename, topic_name in PDF_TOPICS.items():
        pdf_path = f"Data/Policy/{filename}"
        if not os.path.exists(pdf_path):
            print(f"Skipping {filename} (not found)", flush=True)
            continue
            
        print(f"\n==========================================", flush=True)
        print(f"STARTING POLICY FACT EXTRACTION FOR: '{topic_name}'", flush=True)
        print(f"File: {filename}", flush=True)
        print(f"==========================================", flush=True)
        
        # Read text of the PDF
        doc = fitz.open(pdf_path)
        if doc.is_encrypted:
            doc.authenticate("tnpscdeveloper1")
        combined_text = ""
        for p_idx in range(len(doc)):
            combined_text += f"\n--- Page {p_idx+1} ---\n"
            combined_text += doc[p_idx].get_text()
            
        total_chars = len(combined_text)
        print(f"Compiled raw text: {total_chars} characters across {len(doc)} pages.", flush=True)
        
        if total_chars < 500:
            print(f"  Skipping '{topic_name}' due to insufficient text.", flush=True)
            continue
            
        # Partition combined text into 5 segments
        chunk_size = total_chars // 5
        segments = [
            combined_text[:chunk_size],
            combined_text[chunk_size:chunk_size*2],
            combined_text[chunk_size*2:chunk_size*3],
            combined_text[chunk_size*3:chunk_size*4],
            combined_text[chunk_size*4:]
        ]
        
        all_extracted_facts = []
        for r in range(5):
            print(f"  Round {r+1}/5 Extraction...", flush=True)
            facts = call_gemini_extraction(segments[r], topic_name, r+1, api_key)
            print(f"    Extracted {len(facts)} facts.", flush=True)
            all_extracted_facts.extend(facts)
            
            # Preemptive safety sleep
            if r < 4:
                print("  Sleeping 3s to respect API rate limits...", flush=True)
                time.sleep(3)
            
        # Deduplicate
        unique_facts = []
        seen = set()
        for f in all_extracted_facts:
            f_en = f.get("fact_en", "").strip()
            if "provided text does not contain" in f_en.lower() or "no factual information" in f_en.lower():
                continue
            norm_en = normalize(f_en)
            if norm_en and norm_en not in seen:
                unique_facts.append(f)
                seen.add(norm_en)
                
        print(f"Deduplication complete. Total unique facts: {len(unique_facts)}", flush=True)
        
        # Save to facts database
        facts_data[topic_name] = unique_facts
        
        with open(facts_file, "w", encoding="utf-8") as f:
            json.dump(facts_data, f, indent=2, ensure_ascii=False)
        print(f"SUCCESS: Saved facts for '{topic_name}' to {facts_file}", flush=True)

        # Sleep between topics
        print("Sleeping 3s between topics...", flush=True)
        time.sleep(3)

    print("\n==========================================")
    print("ALL POLICY FACT EXTRACTION COMPLETE!")
    print("==========================================")

if __name__ == "__main__":
    main()
