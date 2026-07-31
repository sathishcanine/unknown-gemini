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

data_dir = "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/Data/TVK-Government-Data"

pdf_files = {
    "leaders": {
        "pdf": os.path.join(data_dir, "TVK_Govt_LEADERS_Policy_Notes_1_usable.pdf"),
        "cache": "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/TVK/cache_leaders.json"
    },
    "schemes2": {
        "pdf": os.path.join(data_dir, "TVK_govt_Policy_Scheme_part_2_usable.pdf"),
        "cache": "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/TVK/cache_schemes2.json"
    },
    "schemes3": {
        "pdf": os.path.join(data_dir, "Tvk_govt_policy_Scheme_part_3_usable.pdf"),
        "cache": "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/TVK/cache_schemes3.json"
    }
}

model = "gemini-3.5-flash-lite"
url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

cache_lock = threading.Lock()

def call_gemini_transcription(img_base64, page_num, name):
    prompt = """
You are an expert document transcriber.
Your task is to transcribe all the text from the provided page image of a Government policy / scheme document.
The document contains content in Tamil and English (or is bilingual).

INSTRUCTIONS:
1. Transcribe the text exactly as it appears in the image, keeping the exact bilingual structure (Tamil and English).
2. Format the output in clean Markdown:
   - Use `#`, `##`, `###` for headings.
   - Use `*` or `-` for bullet points.
   - Use bold (`**`) for emphasized text.
   - Format tables using standard Markdown table syntax (`| Column 1 | Column 2 |`).
3. Maintain the order of paragraphs, sections, and columns. If the page is in two-column format, read top-to-bottom, left-column first, then right-column.
4. Do not summarize, edit, or paraphrase. Maintain absolute word-for-word accuracy.
5. Return ONLY the transcribed Markdown content. Do not include markdown code block syntax (like ```markdown) or any conversational introduction or notes.
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
        ]
    }
    headers = {"Content-Type": "application/json"}
    
    retries = 5
    delay = 10
    attempt = 0
    while attempt < retries:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                res_data = response.read().decode("utf-8")
                res_json = json.loads(res_data)
                raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                if raw_text.startswith("```"):
                    raw_text = raw_text.split("\n", 1)[1]
                    if raw_text.endswith("```"):
                        raw_text = raw_text.rsplit("\n", 1)[0]
                return raw_text.strip()
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"    [{name}] Page {page_num} Rate limited (429). Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2
            else:
                attempt += 1
                print(f"    [{name}] Page {page_num} [Attempt {attempt}/{retries}] HTTP Error {e.code}")
                time.sleep(5)
        except Exception as e:
            attempt += 1
            print(f"    [{name}] Page {page_num} [Attempt {attempt}/{retries}] Error: {e}")
            time.sleep(5)
    return ""

def process_page(name, pdf_path, cache_data, cache_file, page_idx):
    page_num = page_idx + 1
    page_key = f"page_{page_num}"
    
    with cache_lock:
        if page_key in cache_data and cache_data[page_key].strip():
            return page_num, cache_data[page_key]
            
    doc = fitz.open(pdf_path)
    page = doc[page_idx]
    pix = page.get_pixmap(dpi=150)
    image_bytes = pix.tobytes("jpg")
    img_base64 = base64.b64encode(image_bytes).decode("utf-8")
    doc.close()
    
    print(f"  [{name}] Page {page_num}: Querying Gemini OCR...")
    transcription = call_gemini_transcription(img_base64, page_num, name)
    
    if transcription:
        with cache_lock:
            cache_data[page_key] = transcription
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
        print(f"  [{name}] Page {page_num}: Transcribed successfully.")
        return page_num, transcription
    else:
        print(f"  [{name}] Page {page_num}: Transcription failed.")
        return page_num, ""

def process_pdf(name, info):
    pdf_path = info["pdf"]
    cache_file = info["cache"]
    
    if not os.path.exists(pdf_path):
        print(f"Error: {pdf_path} not found.")
        return
        
    cache_data = {}
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            print(f"\nLoaded cache for {name}: {len(cache_data)} pages already processed.")
        except Exception as e:
            print(f"Error loading cache for {name}: {e}")
            
    doc = fitz.open(pdf_path)
    num_pages = len(doc)
    doc.close()
    
    print(f"Processing '{name}' ({num_pages} pages)...")
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(process_page, name, pdf_path, cache_data, cache_file, idx): idx for idx in range(num_pages)}
        for future in as_completed(futures):
            idx = futures[future]
            try:
                page_num, text = future.result()
            except Exception as e:
                print(f"  [{name}] Error on page {idx+1}: {e}")
            time.sleep(0.5)

def main():
    print("Starting TVK PDFs transcription task...")
    for name, info in pdf_files.items():
        process_pdf(name, info)
    print("\nAll TVK PDF transcriptions completed successfully!")

if __name__ == "__main__":
    main()
