import os
import sys
import json
import base64
import argparse
import urllib.request
import urllib.error
import fitz  # PyMuPDF

def call_gemini_ocr(img_data, topic, page_num, api_key):
    """Sends a page image to the Gemini API for transcription."""
    prompt = f"""
You are an expert TNPSC question transcriber.
Transcribe all the questions from the provided page image.
This page is part of the topic "{topic}".

For each question on the page, generate a JSON object with the following fields:
- "subject": "INM"
- "topic": "{topic}"
- "source_exam": The exam code written above the question (e.g. "EOG4-2022" or "CEGS-2022"). Look carefully at the header of each question block.
- "difficulty": "Medium" or "Hard"
- "question_en": Question text in English
- "question_ta": Question text in Tamil
- "options": A list of 5 options, each having "key" (A, B, C, D, E), "text_en", and "text_ta". Option E is always "Answer not known" in English and "விடை தெரியவில்லை" in Tamil.
- "correct_option": The correct option key (e.g. "A", "B", "C", "D" - deduce it from the highlighted key, ticks, bold option text, or standard answers)
- "explanation": Brief explanation in English
- "explanation_ta": Brief explanation in Tamil
- "type": "pyq"
- "group": Deduce from exam code (if Group I exam, set to "Group 1", if Group II, set to "Group 2", otherwise "Other Exams")

Return ONLY a raw JSON array of objects.
If the page contains only header titles, blank sections, or no exam questions, return an empty JSON array [].
Do not wrap your output in markdown code blocks or add conversational introduction.
"""

    model = "gemini-3.5-flash-lite"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inlineData": {
                            "mimeType": "image/png",
                            "data": img_data
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req) as response:
            res_data = response.read().decode("utf-8")
            res_json = json.loads(res_data)
            raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
            
            # Parse JSON safely
            text_to_parse = raw_text.strip()
            start_idx = text_to_parse.find('[')
            if start_idx != -1:
                count = 0
                for idx in range(start_idx, len(text_to_parse)):
                    if text_to_parse[idx] == '[':
                        count += 1
                    elif text_to_parse[idx] == ']':
                        count -= 1
                        if count == 0:
                            text_to_parse = text_to_parse[start_idx:idx+1]
                            break
            parsed_questions = json.loads(text_to_parse)
            return parsed_questions
            
    except urllib.error.HTTPError as e:
        print(f"  HTTP Error on Page {page_num}: {e.code} - {e.read().decode('utf-8', errors='ignore')}")
    except Exception as e:
        print(f"  Error parsing Page {page_num}: {e}")
    return []

def main():
    parser = argparse.ArgumentParser(description="TNPSC INM PYQ Transcriber")
    parser.add_argument("--start", type=int, required=True, help="Start page number (1-based physical page)")
    parser.add_argument("--end", type=int, required=True, help="End page number (1-based physical page)")
    parser.add_argument("--topic", type=str, required=True, help="Topic name (e.g., 'Advent of Europeans')")
    
    args = parser.parse_args()
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        sys.exit(1)
        
    pdf_path = "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/Data/INM-Data/INM PYQ PDF 2020 -2025.pdf"
    db_path = "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/INM/inm_questions_db.json"
    
    if not os.path.exists(pdf_path):
        print(f"Error: PDF not found at {pdf_path}")
        sys.exit(1)
        
    # Open PDF
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    
    if args.start < 1 or args.end > total_pages or args.start > args.end:
        print(f"Error: Invalid page range {args.start}-{args.end}. Total pages: {total_pages}")
        sys.exit(1)
        
    print(f"Starting INM PYQ transcription for topic '{args.topic}' across physical pages {args.start} to {args.end}...")
    
    new_questions = []
    
    for page_num in range(args.start, args.end + 1):
        print(f"Processing Page {page_num}...")
        
        # Render page to PNG pixmap
        page = doc[page_num - 1]  # 0-indexed in fitz
        pix = page.get_pixmap(dpi=200)
        
        # Temporary path inside workspace
        temp_img_path = f"/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/INM/temp_page_{page_num}.png"
        pix.save(temp_img_path)
        
        # Base64 encode
        with open(temp_img_path, "rb") as img_file:
            img_data = base64.b64encode(img_file.read()).decode("utf-8")
            
        # Clean up temp image
        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)
            
        # Call Gemini OCR
        questions = call_gemini_ocr(img_data, args.topic, page_num, api_key)
        if questions:
            print(f"  Transcribed {len(questions)} questions from Page {page_num}.")
            new_questions.extend(questions)
        else:
            print(f"  No questions found on Page {page_num}.")
            
    if not new_questions:
        print("No new questions transcribed.")
        sys.exit(0)
        
    # Load existing questions database
    existing_qs = []
    if os.path.exists(db_path):
        with open(db_path, "r", encoding="utf-8") as f:
            try:
                existing_qs = json.load(f)
            except Exception:
                existing_qs = []
                
    # Deduplicate based on English question text
    existing_texts = set(q["question_en"].strip().lower() for q in existing_qs)
    
    added_count = 0
    for q in new_questions:
        q_text = q.get("question_en", "").strip().lower()
        if q_text and q_text not in existing_texts:
            existing_qs.append(q)
            existing_texts.add(q_text)
            added_count += 1
            
    # Save back to database
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(existing_qs, f, indent=2, ensure_ascii=False)
        
    print(f"\nSUCCESS: Added {added_count} unique questions to {db_path}!")
    print(f"Total questions in INM database: {len(existing_qs)}")

if __name__ == "__main__":
    main()
