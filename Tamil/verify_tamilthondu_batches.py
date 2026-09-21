#!/usr/bin/env python3
"""Verify tamilthondu questions batch by batch."""

from __future__ import annotations
import json, os, re, time, urllib.error, urllib.request
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "Tamil", "tamilthondu_questions_db.json")
NOTES_PATH = os.path.join(BASE_DIR, "Tamil", "unit7_tamilthondu_notes_temp.json")
REPORT_PATH = os.path.join(BASE_DIR, "Tamil", "tamilthondu_verify_report.json")
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

def call_gemini(api_key, prompt):
    last = None
    for m in MODELS:
        delay = 8
        for _ in range(4):
            try:
                payload = {"contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1}}
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
                req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=180) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except urllib.error.HTTPError as e:
                last = e
                if e.code in (429, 503): time.sleep(delay); delay = min(delay*2, 90); continue
                break
            except Exception as e: last = e; time.sleep(delay); delay = min(delay*2, 90)
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

def main():
    api_key = get_api_key()
    db = load_json(DB_PATH, [])
    notes = load_json(NOTES_PATH)
    report = {"batches": {}}

    facts_lines = []
    for sid, st in notes.get("subtopics", {}).items():
        facts_lines.append(f"## {st.get('name_ta', sid)}")
        for f in st.get("facts", []):
            ft = f.get("fact_ta") if isinstance(f, dict) else str(f)
            if ft: facts_lines.append(f"- {ft}")
    facts_text = "\n".join(facts_lines)

    by_batch = defaultdict(list)
    for q in db: by_batch[q["batch"]].append(q)

    total_flagged = total_dropped = total_fixed = 0

    for bkey in sorted(by_batch):
        questions = by_batch[bkey]
        print(f"\n=== Verifying: {bkey} ({len(questions)} Q) ===", flush=True)

        q_block = []
        for i, q in enumerate(questions, 1):
            opts = q.get("options") or []
            ot = [re.sub(r"^[A-D]\)\s*", "", o.get("text_ta", "")) for o in opts[:4]]
            q_block.append(f"Q{i}: {q.get('question_ta')}\n  A) {ot[0] if ot else ''} B) {ot[1] if len(ot)>1 else ''} C) {ot[2] if len(ot)>2 else ''} D) {ot[3] if len(ot)>3 else ''}\n  Marked: {q.get('correct_option')}  Expl: {q.get('explanation_ta')}\n")

        prompt = f"""TNPSC Tamil verifier. Verify {len(questions)} MCQs — {bkey}.

FACTS:\n{facts_text[:12000]}

QUESTIONS:\n{"".join(q_block)}

Check: factual accuracy, Tamil quality, TNPSC level, options, answer letter.
Return JSON: {{"batch_summary":{{"total":{len(questions)},"passed":N,"flagged":N,"verdict":"PASS|NEEDS_FIX"}},"flagged_questions":[{{"q_index":N,"issue_type":"...","description":"...","suggestion":"fix or DROP","correct_answer_letter":"A|B|C|D or null"}}]}}"""

        try:
            result = parse_json(call_gemini(api_key, prompt))
            if isinstance(result, list):
                result = {"batch_summary": {"total": len(questions), "passed": len(questions), "flagged": 0, "verdict": "PASS"}, "flagged_questions": []}
        except Exception as e:
            print(f"  FAIL: {e}", flush=True)
            report["batches"][bkey] = {"done": False, "error": str(e)}
            save_json(REPORT_PATH, report); continue

        summary = result.get("batch_summary", {})
        flagged = result.get("flagged_questions", [])
        print(f"  Result: {summary.get('passed','?')} passed, {summary.get('flagged','?')} flagged", flush=True)

        drop_idx = set(); fixes = 0
        for f in flagged:
            idx = f.get("q_index", 0) - 1
            if idx < 0 or idx >= len(questions): continue
            print(f"    Q{f.get('q_index')}: [{f.get('issue_type')}] {f.get('description','')[:100]}", flush=True)
            if (f.get("suggestion") or "").strip().upper() == "DROP": drop_idx.add(idx)
            elif f.get("correct_answer_letter") and f.get("issue_type") == "wrong_answer":
                questions[idx]["correct_option"] = f["correct_answer_letter"]; fixes += 1

        cleaned = [q for i, q in enumerate(questions) if i not in drop_idx]
        for q in cleaned:
            for o in q.get("options", []):
                o["text_ta"] = re.sub(r"^[A-D]\)\s*", "", o.get("text_ta", ""))
                o["text_en"] = o["text_ta"]

        total_flagged += len(flagged); total_dropped += len(drop_idx); total_fixed += fixes
        by_batch[bkey] = cleaned
        report["batches"][bkey] = {"done": True, "summary": summary, "flagged": flagged, "dropped": len(drop_idx), "fixed": fixes, "final": len(cleaned)}
        save_json(REPORT_PATH, report)
        print(f"  After cleanup: {len(cleaned)} Q (dropped={len(drop_idx)}, fixed={fixes})", flush=True)
        time.sleep(3)

    clean_db = []
    for bkey in sorted(by_batch): clean_db.extend(by_batch[bkey])
    save_json(DB_PATH, clean_db)

    print(f"\n{'='*60}\nVERIFICATION COMPLETE\nFlagged: {total_flagged}, Dropped: {total_dropped}, Fixed: {total_fixed}\nFinal: {len(clean_db)} Q")

if __name__ == "__main__":
    main()
