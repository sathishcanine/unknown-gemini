#!/usr/bin/env python3
"""Batch-by-batch Gemini verification of Thonmai/Sirappu/Dravidian questions."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "Tamil", "thonmai_questions_db.json")
NOTES_PATH = os.path.join(BASE_DIR, "Tamil", "unit7_thonmai_notes_temp.json")
REPORT_PATH = os.path.join(BASE_DIR, "Tamil", "thonmai_verify_report.json")

MODELS = ["gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-3.5-flash"]

TOPIC_SUBTOPIC = {
    "தமிழின் தொன்மை": "thonmai",
    "தமிழின் சிறப்பு": "sirappu",
    "திராவிட மொழிகள்": "dravidian",
}


def load_json(path, default=None):
    if not os.path.exists(path):
        return default if default is not None else {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def get_api_key() -> str:
    k = os.environ.get("GEMINI_API_KEY") or ""
    if k:
        return k
    zshrc = os.path.expanduser("~/.zshrc")
    if os.path.exists(zshrc):
        text = open(zshrc, encoding="utf-8", errors="replace").read()
        for line in text.splitlines():
            if "GEMINI_API_KEY" in line and not line.strip().startswith("#"):
                m = re.search(r'GEMINI_API_KEY[= ]+["\']?([A-Za-z0-9_\-]+)', line)
                if m:
                    return m.group(1)
    raise SystemExit("GEMINI_API_KEY missing")


def call_gemini(api_key: str, prompt: str) -> str:
    last = None
    for m in MODELS:
        delay = 8
        for _ in range(4):
            try:
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1},
                }
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
                req = urllib.request.Request(
                    url, data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}, method="POST",
                )
                with urllib.request.urlopen(req, timeout=180) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except urllib.error.HTTPError as e:
                last = e
                if e.code in (429, 503):
                    time.sleep(delay); delay = min(delay * 2, 90); continue
                break
            except Exception as e:
                last = e; time.sleep(delay); delay = min(delay * 2, 90)
    raise RuntimeError(str(last))


def parse_json(raw: str):
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("\n", 1)[0]
    try:
        return json.loads(text)
    except Exception:
        pass
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        if start < 0:
            continue
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == opener: depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    try: return json.loads(text[start:i+1])
                    except: break
    raise ValueError("parse fail")


def build_facts(notes, subtopic_id):
    st = notes.get("subtopics", {}).get(subtopic_id, {})
    lines = []
    for f in (st.get("facts") or [])[:400]:
        ft = f.get("fact_ta") if isinstance(f, dict) else str(f)
        if ft: lines.append(f"- {ft}")
    return "\n".join(lines)


def verify_batch(api_key, questions, facts_text, topic, batch):
    q_block = []
    for i, q in enumerate(questions, 1):
        opts = q.get("options") or []
        ot = [re.sub(r"^[A-D]\)\s*", "", o.get("text_ta", "")) for o in opts[:4]]
        q_block.append(
            f"Q{i}: {q.get('question_ta')}\n"
            f"  A) {ot[0] if len(ot)>0 else ''} B) {ot[1] if len(ot)>1 else ''} "
            f"C) {ot[2] if len(ot)>2 else ''} D) {ot[3] if len(ot)>3 else ''}\n"
            f"  Marked: {q.get('correct_option')}  Expl: {q.get('explanation_ta')}\n"
        )
    prompt = f"""TNPSC Tamil verifier. Verify {len(questions)} MCQs for "{topic}" — {batch}.

REFERENCE FACTS:
{facts_text[:12000]}

QUESTIONS:
{"".join(q_block)}

Check each Q: factual accuracy, Tamil quality, TNPSC level, option quality, answer letter correctness.

Return JSON:
{{"batch_summary":{{"total":{len(questions)},"passed":N,"flagged":N,"verdict":"PASS|NEEDS_FIX"}},
"flagged_questions":[{{"q_index":N,"issue_type":"wrong_answer|tamil_error|bad_options|not_tnpsc|duplicate_options|nonsensical",
"description":"...","suggestion":"fix or DROP","correct_answer_letter":"A|B|C|D or null"}}]}}
Only include genuinely problematic Qs in flagged_questions."""
    raw = call_gemini(api_key, prompt)
    return parse_json(raw)


def main():
    api_key = get_api_key()
    db = load_json(DB_PATH, [])
    notes = load_json(NOTES_PATH)
    report = {"batches": {}}

    by_batch = defaultdict(list)
    for q in db:
        by_batch[f"{q['topic']}|{q['batch']}"].append(q)

    total_flagged = total_dropped = total_fixed = 0

    for bkey in sorted(by_batch):
        topic, batch = bkey.split("|", 1)
        questions = by_batch[bkey]
        sid = TOPIC_SUBTOPIC.get(topic, "thonmai")
        facts_text = build_facts(notes, sid)

        print(f"\n=== Verifying: {topic} | {batch} ({len(questions)} Q) ===", flush=True)
        try:
            result = verify_batch(api_key, questions, facts_text, topic, batch)
        except Exception as e:
            print(f"  VERIFY FAILED: {e}", flush=True)
            report["batches"][bkey] = {"done": False, "error": str(e)}
            save_json(REPORT_PATH, report)
            time.sleep(5)
            continue

        if isinstance(result, list):
            result = {"batch_summary": {"total": len(questions), "passed": len(questions), "flagged": 0, "verdict": "PASS"}, "flagged_questions": []}
        summary = result.get("batch_summary", {})
        flagged = result.get("flagged_questions", [])
        print(f"  Result: {summary.get('passed','?')} passed, {summary.get('flagged','?')} flagged, verdict={summary.get('verdict','?')}", flush=True)

        drop_idx = set()
        fixes = 0
        for f in flagged:
            idx = f.get("q_index", 0) - 1
            if idx < 0 or idx >= len(questions): continue
            print(f"    Q{f.get('q_index')}: [{f.get('issue_type')}] {f.get('description','')[:100]}", flush=True)
            sug = (f.get("suggestion") or "").strip().upper()
            if sug == "DROP" or f.get("issue_type") in ("nonsensical", "not_tnpsc"):
                drop_idx.add(idx)
            elif f.get("correct_answer_letter") and f.get("issue_type") == "wrong_answer":
                questions[idx]["correct_option"] = f["correct_answer_letter"]
                fixes += 1

        cleaned = [q for i, q in enumerate(questions) if i not in drop_idx]
        # Strip A)/B) prefixes from options
        for q in cleaned:
            for o in q.get("options", []):
                o["text_ta"] = re.sub(r"^[A-D]\)\s*", "", o.get("text_ta", ""))
                o["text_en"] = o["text_ta"]

        total_flagged += len(flagged)
        total_dropped += len(drop_idx)
        total_fixed += fixes
        by_batch[bkey] = cleaned

        report["batches"][bkey] = {
            "done": True, "summary": summary, "flagged": flagged,
            "dropped": len(drop_idx), "fixed": fixes, "final_count": len(cleaned),
        }
        save_json(REPORT_PATH, report)
        print(f"  After cleanup: {len(cleaned)} Q (dropped={len(drop_idx)}, fixed={fixes})", flush=True)
        time.sleep(3)

    clean_db = []
    for bkey in sorted(by_batch):
        clean_db.extend(by_batch[bkey])
    save_json(DB_PATH, clean_db)

    print(f"\n{'='*60}\nVERIFICATION COMPLETE")
    print(f"Flagged: {total_flagged}, Dropped: {total_dropped}, Fixed: {total_fixed}")
    print(f"Final DB: {len(clean_db)} questions")
    from collections import Counter
    for (t, b), n in sorted(Counter((q["topic"], q["batch"]) for q in clean_db).items()):
        print(f"  {b} | {t}: {n}")


if __name__ == "__main__":
    main()
