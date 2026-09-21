#!/usr/bin/env python3
"""
Batch-by-batch Gemini verification of Aranoolgal questions.

For each batch, sends all Qs to Gemini and asks it to flag:
  - Invalid / factually wrong answer
  - Tamil grammar / spelling errors
  - Not TNPSC level / not sensible
  - Repetitive / near-duplicate options
  - Option text issues (too similar, missing, ambiguous)
  - Correct answer letter mismatch

Writes:
  Tamil/aranoolgal_verify_report.json  (per-batch verdict + flagged Qs)
  Tamil/aranoolgal_questions_db.json   (cleaned — drops/fixes flagged Qs)

Usage:
  python3 Tamil/verify_aranoolgal_batches.py
  python3 Tamil/verify_aranoolgal_batches.py --resume
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "Tamil", "aranoolgal_questions_db.json")
NOTES_PATH = os.path.join(BASE_DIR, "Tamil", "unit7_aranoolgal_notes_temp.json")
REPORT_PATH = os.path.join(BASE_DIR, "Tamil", "aranoolgal_verify_report.json")

MODELS = ["gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-3.5-flash"]


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
                    "generationConfig": {
                        "responseMimeType": "application/json",
                        "temperature": 0.1,
                    },
                }
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=180) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except urllib.error.HTTPError as e:
                last = e
                if e.code in (429, 503):
                    print(f"    {m} HTTP {e.code}; sleep {delay}s", flush=True)
                    time.sleep(delay)
                    delay = min(delay * 2, 90)
                    continue
                break
            except Exception as e:
                last = e
                time.sleep(delay)
                delay = min(delay * 2, 90)
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
            if ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except Exception:
                        break
    raise ValueError("parse fail")


def build_facts_summary(notes: dict, book_ids: list[str]) -> str:
    parts = []
    for bid in book_ids:
        b = notes.get("books", {}).get(bid, {})
        name = b.get("name_ta", bid)
        facts = b.get("facts") or []
        lines = [f"## {name}"]
        for f in facts:
            ft = f.get("fact_ta") if isinstance(f, dict) else str(f)
            if ft:
                lines.append(f"- {ft}")
        parts.append("\n".join(lines))
    return "\n".join(parts)


TOPIC_BOOKS = {
    "நாலடியார் — நான்மணிக்கடிகை": ["naladiyar", "nanmanikadikai"],
    "பழமொழி நானூறு — இன்னா நாற்பது": ["pazhamozhi_nanuru", "inna_narpathu"],
    "திரிகடுகம் — ஏலாதி": ["thirikadugam", "elathi"],
    "சிறுபஞ்சமூலம் — முதுமொழிக் காஞ்சி": ["sirupanchamoolam", "mudhumozhikkanchi"],
    "ஔவையார்": ["avvaiyar"],
    "ஆசாரக்கோவை — அறநெறிச்சாரம் — நீதிநெறி விளக்கம்": ["asarakkovai", "araneri_saram", "neethineri_vilakkam"],
}


def verify_batch(api_key: str, questions: list[dict], facts_text: str, topic: str, batch: str) -> dict:
    q_block = []
    for i, q in enumerate(questions, 1):
        opts = q.get("options") or []
        opt_texts = []
        for o in opts[:4]:
            t = o.get("text_ta") or o.get("text_en") or ""
            t = re.sub(r"^[A-D]\)\s*", "", t)
            opt_texts.append(t)
        q_block.append(
            f"Q{i}: {q.get('question_ta')}\n"
            f"  A) {opt_texts[0] if len(opt_texts)>0 else ''}\n"
            f"  B) {opt_texts[1] if len(opt_texts)>1 else ''}\n"
            f"  C) {opt_texts[2] if len(opt_texts)>2 else ''}\n"
            f"  D) {opt_texts[3] if len(opt_texts)>3 else ''}\n"
            f"  Marked answer: {q.get('correct_option')}\n"
            f"  Explanation: {q.get('explanation_ta')}\n"
        )

    prompt = f"""You are a TNPSC Tamil exam expert verifier. Verify these {len(questions)} MCQs for topic "{topic}" — {batch}.

REFERENCE FACTS (SM Notes):
{facts_text[:12000]}

QUESTIONS TO VERIFY:
{"".join(q_block)}

For EACH question Q1..Q{len(questions)}, check ALL of these:
1. FACTUAL ACCURACY — Is the marked answer correct per the SM facts above? If not, what is the correct answer?
2. TAMIL QUALITY — Any spelling mistakes, grammar errors, or awkward phrasing?
3. TNPSC LEVEL — Is this a valid TNPSC-style question? (Not too trivial, not too obscure)
4. OPTIONS QUALITY — Are all 4 options distinct and sensible? Any repetitive, too-similar, or absurd options?
5. ANSWER LETTER — Does the correct_option letter match the actual correct text among options?
6. SENSIBLE — Is the question meaningful and testable?

Return JSON:
{{
  "batch_summary": {{
    "total": {len(questions)},
    "passed": <count>,
    "flagged": <count>,
    "verdict": "PASS" or "NEEDS_FIX"
  }},
  "flagged_questions": [
    {{
      "q_index": 1,
      "issue_type": "wrong_answer|tamil_error|bad_options|not_tnpsc|duplicate_options|nonsensical",
      "description": "What's wrong (in English)",
      "suggestion": "How to fix OR 'DROP' if unfixable",
      "correct_answer_letter": "A|B|C|D or null if answer is fine"
    }}
  ]
}}

If a question is perfectly fine, do NOT include it in flagged_questions.
Be strict — flag anything that a TNPSC aspirant would find confusing or wrong.
"""
    raw = call_gemini(api_key, prompt)
    return parse_json(raw)


def apply_fixes(questions: list[dict], flagged: list[dict]) -> tuple[list[dict], int, int]:
    drop_indices = set()
    fix_count = 0

    for f in flagged:
        idx = f.get("q_index", 0) - 1
        if idx < 0 or idx >= len(questions):
            continue
        suggestion = (f.get("suggestion") or "").strip().upper()
        if suggestion == "DROP" or f.get("issue_type") in ("nonsensical", "not_tnpsc"):
            drop_indices.add(idx)
            continue
        new_letter = f.get("correct_answer_letter")
        if new_letter and new_letter in "ABCD" and f.get("issue_type") == "wrong_answer":
            questions[idx]["correct_option"] = new_letter
            fix_count += 1

    result = [q for i, q in enumerate(questions) if i not in drop_indices]
    return result, len(drop_indices), fix_count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    api_key = get_api_key()
    db = load_json(DB_PATH, [])
    notes = load_json(NOTES_PATH)
    report = load_json(REPORT_PATH, {"batches": {}}) if args.resume else {"batches": {}}

    by_batch = defaultdict(list)
    for q in db:
        key = f"{q['topic']}|{q['batch']}"
        by_batch[key].append(q)

    sorted_keys = sorted(by_batch.keys())
    total_flagged = 0
    total_dropped = 0
    total_fixed = 0

    for bkey in sorted_keys:
        if args.resume and bkey in report["batches"] and report["batches"][bkey].get("done"):
            s = report["batches"][bkey]["summary"]
            print(f"SKIP {bkey} (prev: {s.get('passed','?')} pass, {s.get('flagged','?')} flagged)", flush=True)
            continue

        topic, batch = bkey.split("|", 1)
        questions = by_batch[bkey]
        book_ids = TOPIC_BOOKS.get(topic, [])
        facts_text = build_facts_summary(notes, book_ids)

        print(f"\n=== Verifying: {topic} | {batch} ({len(questions)} Q) ===", flush=True)

        try:
            result = verify_batch(api_key, questions, facts_text, topic, batch)
        except Exception as e:
            print(f"  VERIFY FAILED: {e}", flush=True)
            report["batches"][bkey] = {"done": False, "error": str(e)}
            save_json(REPORT_PATH, report)
            time.sleep(5)
            continue

        summary = result.get("batch_summary", {})
        flagged = result.get("flagged_questions", [])
        print(f"  Result: {summary.get('passed', '?')} passed, {summary.get('flagged', '?')} flagged, verdict={summary.get('verdict', '?')}", flush=True)

        if flagged:
            for f in flagged:
                print(f"    Q{f.get('q_index')}: [{f.get('issue_type')}] {f.get('description', '')[:100]}", flush=True)

        cleaned, dropped, fixed = apply_fixes(questions, flagged)
        total_flagged += len(flagged)
        total_dropped += dropped
        total_fixed += fixed

        by_batch[bkey] = cleaned

        report["batches"][bkey] = {
            "done": True,
            "summary": summary,
            "flagged": flagged,
            "dropped": dropped,
            "fixed": fixed,
            "final_count": len(cleaned),
        }
        save_json(REPORT_PATH, report)
        print(f"  After cleanup: {len(cleaned)} Q (dropped={dropped}, fixed={fixed})", flush=True)
        time.sleep(3)

    # Rebuild cleaned DB
    clean_db = []
    for bkey in sorted_keys:
        for q in by_batch[bkey]:
            opts = q.get("options") or []
            cleaned_opts = []
            for o in opts[:4]:
                t = o.get("text_ta") or o.get("text_en") or ""
                t = re.sub(r"^[A-D]\)\s*", "", t)
                cleaned_opts.append({
                    "key": o["key"],
                    "text_en": t,
                    "text_ta": t,
                })
            q["options"] = cleaned_opts
            clean_db.append(q)

    save_json(DB_PATH, clean_db)

    print(f"\n{'='*60}")
    print(f"VERIFICATION COMPLETE")
    print(f"Total questions verified: {sum(len(v) for v in by_batch.values())}")
    print(f"Total flagged: {total_flagged}")
    print(f"Total dropped: {total_dropped}")
    print(f"Total answer-fixed: {total_fixed}")
    print(f"Final DB: {len(clean_db)} questions")
    print(f"{'='*60}")

    from collections import Counter
    c = Counter((q["topic"], q["batch"]) for q in clean_db)
    for (t, b), n in sorted(c.items()):
        print(f"  {b} | {t[:50]}: {n}")


if __name__ == "__main__":
    main()
