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
pdf_path = "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/Data/Indian-History-Data/Indian_history_suresh.pdf"
output_json = "/Users/sathishkumar/.gemini/antigravity/brain/17695494-8089-45b1-a1dc-9ce7f3eac4ce/scratch/history_transcribed_pages.json"

if not api_key:
    print("GEMINI_API_KEY not found.")
    exit(1)

# Lock for thread-safe writing to the JSON file
file_lock = threading.Lock()

# Load existing progress if available
transcribed_data = {}
if os.path.exists(output_json):
    try:
        with open(output_json, "r", encoding="utf-8") as f:
            transcribed_data = json.load(f)
        print(f"Loaded existing progress: {len(transcribed_data)} pages already transcribed.")
    except Exception as e:
        print(f"Error loading existing JSON, starting fresh: {e}")

doc = fitz.open(pdf_path)
num_pages = len(doc)
print(f"Total Pages: {num_pages}")
doc.close()

model = "gemini-3.1-flash-lite"
url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

def call_ocr_api(img_base64, page_num):
    prompt = """
    This is an image of a page from a Tamil book on Indian History (Suresh IAS Academy).
    Please perform highly accurate OCR and transcribe all text from this page.
    - Output the transcribed text in Unicode Tamil and English as it appears on the page.
    - Replicate the layout structure (headings, bullet points, lists, sections) as closely as possible.
    - If there are tables, represent them as Markdown tables.
    - Output ONLY the raw transcribed text. Do not add any introduction, explanations, or notes.
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
    delay = 6
    
    for attempt in range(retries):
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req) as response:
                res_data = response.read().decode("utf-8")
                res_json = json.loads(res_data)
                text = res_json["candidates"][0]["content"]["parts"][0]["text"]
                return text
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"  Page {page_num} [Attempt {attempt+1}/{retries}] Rate limited (429). Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2
            else:
                print(f"  Page {page_num} [Attempt {attempt+1}/{retries}] HTTP Error {e.code}: {e.read().decode('utf-8', errors='ignore')}")
                time.sleep(3)
        except Exception as e:
            print(f"  Page {page_num} [Attempt {attempt+1}/{retries}] Error: {e}")
            time.sleep(3)
            
    return None

def process_page(page_idx):
    page_num = page_idx + 1
    page_key = f"page_{page_num}"
    
    # Check if already done
    with file_lock:
        if page_key in transcribed_data:
            return page_num, True
            
    print(f"Starting page {page_num}/{num_pages}...")
    
    # We open a separate fitz document per thread to avoid race conditions
    thread_doc = fitz.open(pdf_path)
    page = thread_doc[page_idx]
    
    # Render page to high-res image (150 DPI)
    pix = page.get_pixmap(dpi=150)
    image_bytes = pix.tobytes("jpg")
    img_base64 = base64.b64encode(image_bytes).decode("utf-8")
    thread_doc.close()
    
    transcribed_text = call_ocr_api(img_base64, page_num)
    if transcribed_text:
        with file_lock:
            transcribed_data[page_key] = transcribed_text
            with open(output_json, "w", encoding="utf-8") as f:
                json.dump(transcribed_data, f, indent=2, ensure_ascii=False)
        print(f"  Page {page_num} completed and saved.")
        return page_num, True
    else:
        print(f"  Page {page_num} failed after retries.")
        return page_num, False

# Process pages in parallel
pages_to_process = [i for i in range(num_pages) if f"page_{i+1}" not in transcribed_data]

if pages_to_process:
    print(f"Processing {len(pages_to_process)} remaining pages in parallel with 3 workers...")
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(process_page, idx): idx for idx in pages_to_process}
        for future in as_completed(futures):
            page_num, success = future.result()
            if not success:
                print(f"Warning: Page {page_num} transcription failed.")
            # Small stagger to respect rate limits
            time.sleep(1)
else:
    print("All pages already transcribed!")

print("Transcription queue finished!")
