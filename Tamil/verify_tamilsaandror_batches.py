#!/usr/bin/env python3
"""Double-verify tamilsaandror questions batch by batch (2 independent passes)."""

from __future__ import annotations
import json, os, re, time, urllib.error, urllib.request
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "Tamil", "tamilsaandror_questions_db.json")
NOTES_PATH = os.path.join(BASE_DIR, "Tamil", "unit7_tamilsaandror_notes_temp.json")
REPORT_PATH = os.path.join(BASE_DIR, "Tamil", "tamilsaandror_verify_report.json")
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
                    "generationConfig": {"responseMimeType": "application/json", "temperature": 0.05}}
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

def build_facts(notes):
    lines = []
    for sid, st in notes.get("subtopics", {}).items():
        lines.append(f"## {st.get('name_ta', sid)}")
        for f in st.get("facts", []):
            ft = f.get("fact_ta") if isinstance(f, dict) else str(f)
            if ft: lines.append(f"- {ft}")
        for q in st.get("quotes", [])[:25]:
            qt = q.get("text_ta") if isinstance(q, dict) else str(q)
            if qt: lines.append(f'- Quote: "{qt}"')
    return "\n".join(lines)

def format_questions(questions):
    q_block = []
    for i, q in enumerate(questions, 1):
        opts = q.get("options") or []
        ot = [re.sub(r"^[A-D]\)\s*", "", str(o.get("text_ta", ""))) for o in opts[:4]]
        while len(ot) < 4: ot.append("")
        q_block.append(
            f"Q{i}: {q.get('question_ta')}\n"
            f"  A) {ot[0]} B) {ot[1]} C) {ot[2]} D) {ot[3]}\n"
            f"  Marked: {q.get('correct_option')}  Expl: {q.get('explanation_ta')}\n"
        )
    return "".join(q_block)

CHECKLIST = """Strict checks for EACH question:
1) Factual accuracy vs SM FACTS (wrong facts = FLAG)
2) Marked answer letter is correct (wrong_answer)
3) Exactly 4 distinct sensible options (no duplicates / near-duplicates / nonsense)
4) Tamil spelling/grammar quality (tamil_mistake)
5) Sensible, clear stem — not ambiguous (ambiguous)
6) TNPSC Group exam oriented & TNPSC difficulty level (not_tnpsc / too_trivial / too_obscure)
7) Options not repetitive across the batch for the same fact
8) Quote-attribution must match speaker correctly

suggestion must be one of: FIX | DROP
If wrong answer: issue_type=wrong_answer and set correct_answer_letter.
If irreparable: suggestion=DROP."""

def verify_batch(api_key, bkey, questions, facts_text, pass_no):
    # Rotate fact window so pass2 sees different supporting facts
    chunk = 20000
    start = 0 if pass_no == 1 else min(12000, max(0, len(facts_text) - chunk))
    facts_slice = facts_text[start:start + chunk]
    if len(facts_slice) < 8000:
        facts_slice = facts_text[:chunk]

    prompt = f"""You are a strict TNPSC General Tamil question auditor.
DOUBLE-VERIFY PASS {pass_no}/2 for batch {bkey} ({len(questions)} MCQs).

SM FACTS:
{facts_slice}

QUESTIONS:
{format_questions(questions)}

{CHECKLIST}

Return ONLY JSON:
{{"batch_summary":{{"total":{len(questions)},"passed":N,"flagged":N,"verdict":"PASS|NEEDS_FIX"}},
 "flagged_questions":[{{"q_index":N,"issue_type":"wrong_answer|factual_error|tamil_mistake|bad_options|duplicate_options|ambiguous|not_tnpsc|other","description":"...","suggestion":"FIX|DROP","correct_answer_letter":"A|B|C|D or null"}}]}}

If everything is good, flagged_questions must be []."""

    result = parse_json(call_gemini(api_key, prompt))
    if isinstance(result, list):
        result = {
            "batch_summary": {
                "total": len(questions),
                "passed": len(questions) - len(result),
                "flagged": len(result),
                "verdict": "NEEDS_FIX" if result else "PASS",
            },
            "flagged_questions": result,
        }
    if not isinstance(result, dict):
        result = {"batch_summary": {"verdict": "PASS"}, "flagged_questions": []}
    if "flagged_questions" not in result or result["flagged_questions"] is None:
        result["flagged_questions"] = []
    return result

def apply_flags(questions, flagged):
    drop_idx = set()
    fixes = 0
    for f in flagged:
        idx = int(f.get("q_index", 0)) - 1
        if idx < 0 or idx >= len(questions):
            continue
        print(f"    Q{f.get('q_index')}: [{f.get('issue_type')}] {str(f.get('description',''))[:120]}", flush=True)
        sug = (f.get("suggestion") or "").strip().upper()
        if sug == "DROP":
            drop_idx.add(idx)
        elif f.get("correct_answer_letter") and (f.get("issue_type") or "") in (
            "wrong_answer", "factual_error"
        ):
            letter = str(f["correct_answer_letter"]).strip().upper()[:1]
            if letter in "ABCD":
                questions[idx]["correct_option"] = letter
                fixes += 1
        elif sug == "FIX" and f.get("correct_answer_letter"):
            letter = str(f["correct_answer_letter"]).strip().upper()[:1]
            if letter in "ABCD":
                questions[idx]["correct_option"] = letter
                fixes += 1
    cleaned = [q for i, q in enumerate(questions) if i not in drop_idx]
    for q in cleaned:
        for o in q.get("options", []):
            o["text_ta"] = re.sub(r"^[A-D]\)\s*", "", str(o.get("text_ta", "")))
            o["text_en"] = o["text_ta"]
    return cleaned, len(drop_idx), fixes

def main():
    api_key = get_api_key()
    db = load_json(DB_PATH, [])
    notes = load_json(NOTES_PATH)
    facts_text = build_facts(notes)
    report = {"passes": 2, "batches": {}}

    by_batch = defaultdict(list)
    for q in db:
        by_batch[q["batch"]].append(q)

    total_flagged = total_dropped = total_fixed = 0

    for pass_no in (1, 2):
        print(f"\n{'#'*60}\n# DOUBLE VERIFY PASS {pass_no}/2\n{'#'*60}", flush=True)
        for bkey in sorted(by_batch):
            questions = by_batch[bkey]
            print(f"\n=== Pass {pass_no} | {bkey} ({len(questions)} Q) ===", flush=True)
            try:
                result = verify_batch(api_key, bkey, questions, facts_text, pass_no)
            except Exception as e:
                print(f"  FAIL: {e}", flush=True)
                report["batches"].setdefault(bkey, {})[f"pass{pass_no}"] = {"done": False, "error": str(e)}
                save_json(REPORT_PATH, report)
                continue

            summary = result.get("batch_summary", {})
            flagged = result.get("flagged_questions", []) or []
            print(
                f"  Result: {summary.get('passed','?')} passed, "
                f"{summary.get('flagged', len(flagged))} flagged, "
                f"verdict={summary.get('verdict','?')}",
                flush=True,
            )

            cleaned, dropped, fixes = apply_flags(questions, flagged)
            total_flagged += len(flagged)
            total_dropped += dropped
            total_fixed += fixes
            by_batch[bkey] = cleaned
            report["batches"].setdefault(bkey, {})[f"pass{pass_no}"] = {
                "done": True,
                "summary": summary,
                "flagged": flagged,
                "dropped": dropped,
                "fixed": fixes,
                "final": len(cleaned),
            }
            save_json(REPORT_PATH, report)
            print(f"  After cleanup: {len(cleaned)} Q (dropped={dropped}, fixed={fixes})", flush=True)
            time.sleep(3)

    clean_db = []
    for bkey in sorted(by_batch):
        clean_db.extend(by_batch[bkey])
    save_json(DB_PATH, clean_db)

    print(f"\n{'='*60}")
    print("DOUBLE VERIFICATION COMPLETE")
    print(f"Flagged: {total_flagged}, Dropped: {total_dropped}, Fixed: {total_fixed}")
    print(f"Final: {len(clean_db)} Q")
    from collections import Counter
    print(dict(Counter(q["batch"] for q in clean_db)))

if __name__ == "__main__":
    main()
