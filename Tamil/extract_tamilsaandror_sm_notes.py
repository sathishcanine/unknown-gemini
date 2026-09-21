#!/usr/bin/env python3
"""Extract SM notes for தமிழ்ச் சான்றோர் பற்றிய செய்திகள். Pages 526-558."""
from __future__ import annotations
import argparse, base64, json, os, re, time, urllib.error, urllib.request
from io import BytesIO
import fitz
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_PATH = os.path.join(BASE_DIR, "Data", "Tamil", "ilakanam", "SM TAMIL FULL BOOK 570 PAGES.pdf")
OUT_PATH = os.path.join(BASE_DIR, "Tamil", "unit7_tamilsaandror_notes_temp.json")
PDF_OFFSET = 6
SUBTOPICS = [
    {"id": "pavendhar", "name_ta": "பாவேந்தர்", "print_start": 526, "print_end": 536},
    {"id": "tk_chidambaranar", "name_ta": "டி.கே.சிதம்பரனார்", "print_start": 537, "print_end": 539},
    {"id": "kundrakkudi", "name_ta": "தவத்திரு குன்றக்குடி அடிகளார்", "print_start": 540, "print_end": 540},
    {"id": "kannadasan", "name_ta": "கண்ணதாசன்", "print_start": 541, "print_end": 544},
    {"id": "quaid_millath", "name_ta": "காயிதே மில்லத்", "print_start": 545, "print_end": 546},
    {"id": "thara_bharathi", "name_ta": "தாரா பாரதி", "print_start": 547, "print_end": 547},
    {"id": "velu_nachiyar", "name_ta": "வேலுநாச்சியார்", "print_start": 548, "print_end": 550},
    {"id": "pattukkottai", "name_ta": "பட்டுக்கோட்டைக் கல்யாணசுந்தரம்", "print_start": 551, "print_end": 551},
    {"id": "mudiyarasan", "name_ta": "முடியரசன்", "print_start": 552, "print_end": 554},
    {"id": "tamil_oli", "name_ta": "தமிழ் ஒளி", "print_start": 555, "print_end": 555},
    {"id": "uruthirangannanar", "name_ta": "உருத்திரங்கண்ணனார்", "print_start": 556, "print_end": 556},
    {"id": "ki_va_jagannathan", "name_ta": "கி வா ஜகந்நாதர்", "print_start": 557, "print_end": 557},
    {"id": "namakkal_kavignar", "name_ta": "நாமக்கல் கவிஞர்", "print_start": 558, "print_end": 558},
]
MODELS = ["gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-3.5-flash"]

def load_json(p, d=None):
    if not os.path.exists(p): return d if d is not None else {}
    with open(p, "r", encoding="utf-8") as f: return json.load(f)
def save_json(p, d):
    t = p + ".tmp"
    with open(t, "w", encoding="utf-8") as f: json.dump(d, f, ensure_ascii=False, indent=2); f.write("\n")
    os.replace(t, p)
def get_api_key():
    k = os.environ.get("GEMINI_API_KEY") or ""
    if k: return k
    for line in open(os.path.expanduser("~/.zshrc"), encoding="utf-8", errors="replace"):
        if "GEMINI_API_KEY" in line and not line.strip().startswith("#"):
            m = re.search(r'GEMINI_API_KEY[= ]+["\']?([A-Za-z0-9_\-]+)', line)
            if m: return m.group(1)
    raise SystemExit("GEMINI_API_KEY missing")
def call_gemini(api_key, prompt, img_b64=None):
    last = None
    for m in MODELS:
        delay = 6
        for _ in range(4):
            try:
                parts = [{"text": prompt}]
                if img_b64: parts.append({"inlineData": {"mimeType": "image/jpeg", "data": img_b64}})
                payload = {"contents": [{"parts": parts}], "generationConfig": {"responseMimeType": "application/json", "temperature": 0.15}}
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
                req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=180) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except urllib.error.HTTPError as e:
                last = e
                if e.code in (429, 503): time.sleep(delay); delay = min(delay*2, 60); continue
                break
            except Exception as e: last = e; time.sleep(delay); delay = min(delay*2, 60)
    raise RuntimeError(str(last))
def parse_json(raw):
    text = (raw or "").strip()
    if text.startswith("```"): text = text.split("\n",1)[1]
    if text.endswith("```"): text = text.rsplit("\n",1)[0]
    try: return json.loads(text)
    except: pass
    for o,c in (("{","}"),("[","]")):
        s = text.find(o)
        if s < 0: continue
        d = 0
        for i, ch in enumerate(text[s:], s):
            if ch == o: d += 1
            elif ch == c:
                d -= 1
                if d == 0:
                    try: return json.loads(text[s:i+1])
                    except: break
    raise ValueError("parse fail")
def render_page(doc, pdf_page):
    page = doc[pdf_page]; pix = page.get_pixmap(dpi=200)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    if img.width > 1400: r = 1400/img.width; img = img.resize((1400, int(img.height*r)), Image.LANCZOS)
    buf = BytesIO(); img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("ascii")

def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--rounds", type=int, default=2)
    args = parser.parse_args()
    api_key = get_api_key(); doc = fitz.open(PDF_PATH)
    notes = load_json(OUT_PATH, {"subtopics": {}})
    for st in SUBTOPICS:
        sid, name = st["id"], st["name_ta"]
        if sid not in notes["subtopics"]:
            notes["subtopics"][sid] = {"name_ta": name, "facts": [], "quotes": []}
        ef = {f.get("fact_ta","") for f in notes["subtopics"][sid]["facts"]}
        eq = {q.get("text_ta","") for q in notes["subtopics"][sid]["quotes"]}
        for rnd in range(1, args.rounds+1):
            print(f"\n=== {name} | Round {rnd}/{args.rounds} (p{st['print_start']}-{st['print_end']}) ===", flush=True)
            for p in range(st["print_start"], st["print_end"]+1):
                pdf = p + PDF_OFFSET
                if pdf >= len(doc): continue
                print(f"  p{p} (pdf{pdf})...", end=" ", flush=True)
                try:
                    rh = f"\nRound {rnd}: find NEW facts." if rnd > 1 else ""
                    prompt = f"Tamil TNPSC fact extractor. Page {p}, scholar: {name}.{rh}\nExtract ALL facts: birth/death, works, titles, contributions, quotes.\nReturn JSON: {{\"page\":{p},\"facts\":[{{\"fact_ta\":\"...\",\"category\":\"bio|works|title|contribution|quote\"}}],\"quotes\":[{{\"text_ta\":\"...\",\"speaker\":\"...\"}}]}}"
                    result = parse_json(call_gemini(api_key, prompt, render_page(doc, pdf)))
                    nf=nq=0
                    for f in result.get("facts",[]):
                        ft = (f.get("fact_ta") or "").strip()
                        if ft and ft not in ef: notes["subtopics"][sid]["facts"].append(f); ef.add(ft); nf += 1
                    for q in result.get("quotes",[]):
                        qt = (q.get("text_ta") or "").strip()
                        if qt and qt not in eq: notes["subtopics"][sid]["quotes"].append(q); eq.add(qt); nq += 1
                    print(f"+{nf}f +{nq}q", flush=True)
                except Exception as e: print(f"FAIL: {e}", flush=True)
                time.sleep(1)
            save_json(OUT_PATH, notes)
            print(f"  Round {rnd}: total {len(notes['subtopics'][sid]['facts'])}f {len(notes['subtopics'][sid]['quotes'])}q", flush=True)
    doc.close()
    print(f"\n{'='*50}\nEXTRACTION COMPLETE")
    for sid, d in notes["subtopics"].items(): print(f"  {d['name_ta']}: {len(d['facts'])} facts, {len(d['quotes'])} quotes")

if __name__ == "__main__": main()
