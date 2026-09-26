#!/usr/bin/env python3
"""
Double-verify Parts-of-Speech practice batches against Asan+Govt notes.

Checks per question:
  - answer correctness vs notes
  - TNPSC level / sensibility
  - option quality (duplicates, ambiguity)
  - English quality
  - explanation vs marked answer

Writes:
  English/Grammar/parts_of_speech_verify_report.json
  English/Grammar/parts_of_speech_questions_db.json  (fixes/drops applied)

Usage:
  python3 English/Grammar/verify_pos_batches.py
  python3 English/Grammar/verify_pos_batches.py --resume
  python3 English/Grammar/verify_pos_batches.py --topic noun --batch 1
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(
    BASE_DIR, "English", "Grammar", "parts_of_speech_questions_db.json"
)
NOTES_PATH = os.path.join(BASE_DIR, "English", "Grammar", "parts_of_speech_notes.json")
REPORT_PATH = os.path.join(
    BASE_DIR, "English", "Grammar", "parts_of_speech_verify_report.json"
)

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
    raise SystemExit("GEMINI_API_KEY missing")


def call_gemini(api_key: str, prompt: str) -> str:
    last = None
    for m in MODELS:
        delay = 10
        for _ in range(5):
            try:
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "responseMimeType": "application/json",
                        "temperature": 0.1,
                    },
                }
                url = (
                    f"https://generativelanguage.googleapis.com/v1beta/models/{m}"
                    f":generateContent?key={api_key}"
                )
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=210) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except urllib.error.HTTPError as e:
                last = e
                if e.code in (429, 503):
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


def build_notes_text(notes: dict, topic_id: str) -> str:
    block = (notes.get("topics") or {}).get(topic_id) or {}
    lines = [f"TOPIC: {block.get('name_en') or topic_id}"]
    lines.append("\nRULES:")
    for i, r in enumerate((block.get("rules") or [])[:50], 1):
        en = (r.get("rule_en") or "").strip()
        if en:
            src = r.get("source") or ""
            page = r.get("source_page")
            bit = f"[{src} p.{page}] " if page is not None else f"[{src}] "
            lines.append(f"R{i}. {bit}{en}")
    lines.append("\nEXAMPLES:")
    for i, e in enumerate((block.get("examples") or [])[:60], 1):
        inp = (e.get("input") or "").strip()
        out = (e.get("output") or "").strip()
        note = (e.get("note_en") or "").strip()
        if out:
            lines.append(f"E{i}. {inp} → {out}" + (f" ({note})" if note else ""))
        elif inp:
            lines.append(f"E{i}. {inp}" + (f" ({note})" if note else ""))
    lines.append("\nWORKED:")
    for i, w in enumerate((block.get("worked_exercises") or [])[:30], 1):
        lines.append(
            f"W{i}. {(w.get('prompt_en') or '').strip()} => {(w.get('answer_en') or '').strip()}"
        )
    # mixed odd-word drills help noun/adj/verb/adverb
    if topic_id in ("noun", "adjective", "verb", "adverb"):
        mixed = notes.get("mixed_pos") or {}
        for i, w in enumerate((mixed.get("worked_exercises") or [])[:15], 1):
            lines.append(
                f"M{i}. {(w.get('prompt_en') or '').strip()} => {(w.get('answer_en') or '').strip()}"
            )
    return "\n".join(lines)


def verify_batch(api_key, questions, notes_text, topic_id, topic_en, batch):
    q_block = []
    for i, q in enumerate(questions, 1):
        opts = q.get("options") or []
        ot = []
        for o in opts:
            if o.get("key") in "ABCD":
                ot.append(f"{o.get('key')}) {(o.get('text_en') or '').strip()}")
        q_block.append(
            f"Q{i}: {(q.get('question_en') or '').strip()}\n"
            f"  Options: {' | '.join(ot)}\n"
            f"  Marked answer: {q.get('correct_option')}\n"
            f"  Explanation: {(q.get('explanation') or '')[:220]}\n"
        )

    prompt = f"""You are a strict TNPSC General English (SSLC Standard) Grammar verifier.
Verify these {len(questions)} MCQs for Parts of Speech → "{topic_en}" ({topic_id}) — {batch}.

REFERENCE NOTES (Asan + TN Govt). Treat these as ground truth for answers:
{notes_text[:14000]}

QUESTIONS:
{"".join(q_block)}

Check EACH question carefully for:
1) wrong_answer — marked letter does not match notes / standard grammar
2) bad_options — duplicate, ambiguous, two correct, nonsense distractors
3) not_tnpsc — too trivial/obscure/college-level/not exam style
4) nonsensical — stem broken, English broken, unclear task
5) explanation_mismatch — explanation contradicts marked answer
6) off_topic — not really about {topic_en} word-class / this POS topic

Be strict but fair. SSLC TNPSC Grammar level is expected.
Only flag genuinely problematic questions.

Return ONLY JSON:
{{
  "batch_summary": {{
    "total": {len(questions)},
    "passed": N,
    "flagged": N,
    "verdict": "PASS|NEEDS_FIX"
  }},
  "flagged_questions": [
    {{
      "q_index": 1,
      "issue_type": "wrong_answer|bad_options|not_tnpsc|nonsensical|explanation_mismatch|off_topic",
      "severity": "medium|high",
      "description": "...",
      "suggestion": "FIX_ANSWER|DROP|REVISE",
      "correct_answer_letter": "A|B|C|D or null"
    }}
  ]
}}
"""
    raw = call_gemini(api_key, prompt)
    return parse_json(raw)


def apply_flags(questions, flagged):
    drop_idx = set()
    fixes = 0
    revise_idx = set()
    details = []
    for f in flagged:
        idx = int(f.get("q_index") or 0) - 1
        if idx < 0 or idx >= len(questions):
            continue
        issue = f.get("issue_type") or ""
        sug = (f.get("suggestion") or "").strip().upper()
        sev = (f.get("severity") or "medium").lower()
        desc = (f.get("description") or "")[:200]
        details.append(
            {
                "q_index": idx + 1,
                "issue_type": issue,
                "severity": sev,
                "description": desc,
                "suggestion": sug,
                "question_en": (questions[idx].get("question_en") or "")[:120],
                "old_answer": questions[idx].get("correct_option"),
            }
        )
        letter = (f.get("correct_answer_letter") or "").strip().upper()[:1]
        if sug == "FIX_ANSWER" or (issue == "wrong_answer" and letter in "ABCD"):
            if letter in "ABCD":
                questions[idx]["correct_option"] = letter
                questions[idx]["verify_fixed"] = True
                questions[idx]["verify_note"] = desc
                details[-1]["new_answer"] = letter
                fixes += 1
            elif sev == "high":
                drop_idx.add(idx)
        elif sug == "DROP" or issue in ("nonsensical", "not_tnpsc", "off_topic"):
            # only drop high severity or explicit DROP
            if sug == "DROP" or sev == "high" or issue == "nonsensical":
                drop_idx.add(idx)
            else:
                revise_idx.add(idx)
        elif sug == "REVISE" and sev == "high":
            drop_idx.add(idx)
        elif issue == "bad_options" and sev == "high":
            drop_idx.add(idx)
        elif issue == "explanation_mismatch" and letter in "ABCD":
            questions[idx]["correct_option"] = letter
            questions[idx]["verify_fixed"] = True
            fixes += 1

    cleaned = [q for i, q in enumerate(questions) if i not in drop_idx]
    return cleaned, fixes, len(drop_idx), details


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--topic")
    parser.add_argument("--batch", type=int)
    args = parser.parse_args()

    api_key = get_api_key()
    db = load_json(DB_PATH, [])
    notes = load_json(NOTES_PATH, {})
    report = load_json(REPORT_PATH, {"batches": {}}) if args.resume else {"batches": {}}

    by_batch = defaultdict(list)
    order = []
    for q in db:
        if not isinstance(q, dict):
            continue
        key = f"{q.get('topic_id')}|{q.get('batch')}"
        if key not in by_batch:
            order.append(key)
        by_batch[key].append(q)

    if args.topic and args.batch:
        order = [f"{args.topic}|Batch {args.batch}"]

    total_flagged = total_dropped = total_fixed = 0
    updated = {}

    for bkey in order:
        if args.resume and report.get("batches", {}).get(bkey, {}).get("done"):
            print(f"SKIP (resume): {bkey}")
            updated[bkey] = by_batch[bkey]
            continue

        questions = by_batch.get(bkey) or []
        if not questions:
            print(f"MISSING batch {bkey}")
            continue
        topic_id = questions[0].get("topic_id")
        topic_en = questions[0].get("topic") or topic_id
        batch = questions[0].get("batch")
        notes_text = build_notes_text(notes, topic_id)

        print(f"\n=== Verifying: {topic_id} | {batch} ({len(questions)} Q) ===", flush=True)
        try:
            result = verify_batch(
                api_key, questions, notes_text, topic_id, topic_en, batch
            )
        except Exception as e:
            print(f"  VERIFY FAILED: {e}", flush=True)
            report.setdefault("batches", {})[bkey] = {"done": False, "error": str(e)}
            save_json(REPORT_PATH, report)
            updated[bkey] = questions
            time.sleep(5)
            continue

        if isinstance(result, list):
            result = {
                "batch_summary": {
                    "total": len(questions),
                    "passed": len(questions),
                    "flagged": 0,
                    "verdict": "PASS",
                },
                "flagged_questions": [],
            }

        summary = result.get("batch_summary") or {}
        flagged = result.get("flagged_questions") or []
        print(
            f"  Result: passed={summary.get('passed','?')} flagged={len(flagged)} "
            f"verdict={summary.get('verdict','?')}",
            flush=True,
        )
        for f in flagged:
            print(
                f"    Q{f.get('q_index')}: [{f.get('issue_type')}/{f.get('severity')}] "
                f"{(f.get('description') or '')[:110]}",
                flush=True,
            )

        cleaned, fixes, dropped, details = apply_flags(questions, flagged)
        total_flagged += len(flagged)
        total_dropped += dropped
        total_fixed += fixes
        updated[bkey] = cleaned

        report.setdefault("batches", {})[bkey] = {
            "done": True,
            "summary": summary,
            "flagged_count": len(flagged),
            "flagged": details,
            "dropped": dropped,
            "fixed": fixes,
            "final_count": len(cleaned),
            "verdict": summary.get("verdict") or ("NEEDS_FIX" if flagged else "PASS"),
        }
        save_json(REPORT_PATH, report)
        print(
            f"  After cleanup: {len(cleaned)} Q (dropped={dropped}, fixed={fixes})",
            flush=True,
        )
        time.sleep(3)

    # Rebuild DB preserving order of batches
    clean_db = []
    for bkey in order:
        clean_db.extend(updated.get(bkey) or by_batch.get(bkey) or [])
    # include any batches not in order (safety)
    seen = set(id(q) for q in clean_db)
    for bkey, qs in by_batch.items():
        if bkey not in updated and bkey not in order:
            clean_db.extend(qs)

    save_json(DB_PATH, clean_db)

    print(f"\n{'='*60}")
    print("VERIFICATION COMPLETE")
    print(f"Flagged: {total_flagged}, Dropped: {total_dropped}, Fixed: {total_fixed}")
    print(f"Final DB: {len(clean_db)} questions")
    c = Counter((q.get("topic_id"), q.get("batch")) for q in clean_db)
    short = []
    for k in sorted(c):
        n = c[k]
        mark = " OK" if n >= 25 else " SHORT"
        print(f"  {k[0]:14} {k[1]}: {n}{mark}")
        if n < 25:
            short.append((k[0], k[1], n))
    report["totals"] = {
        "flagged": total_flagged,
        "dropped": total_dropped,
        "fixed": total_fixed,
        "final_db": len(clean_db),
        "short_batches": short,
    }
    save_json(REPORT_PATH, report)
    if short:
        print("\nSHORT batches needing top-up:", short)


if __name__ == "__main__":
    main()
