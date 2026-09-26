#!/usr/bin/env python3
"""
Double-verify Direct & Indirect Speech practice batches against direct_indirect_notes.json.

Verifies the 10 topic batches (250 Q).

Usage:
  python3 English/Grammar/verify_direct_indirect_batches.py
  python3 English/Grammar/verify_direct_indirect_batches.py --resume
  python3 English/Grammar/verify_direct_indirect_batches.py --topic statements_dti --batch 1
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "English", "Grammar", "direct_indirect_questions_db.json")
NOTES_PATH = os.path.join(BASE_DIR, "English", "Grammar", "direct_indirect_notes.json")
REPORT_PATH = os.path.join(BASE_DIR, "English", "Grammar", "direct_indirect_verify_report.json")

MODELS = ["gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-3.5-flash"]

TOPIC_LABELS = {
    "statements_dti": "Statements (Direct → Indirect)",
    "questions": "Questions (WH & Yes/No)",
    "commands_imperatives": "Commands, Requests & Imperatives",
    "indirect_to_direct": "Indirect → Direct",
    "time_pronoun_reporting": "Time, Place, Pronoun & Reporting Verbs",
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


def notes_text(notes: dict, topic_id: str) -> str:
    lines = [f"SPEECH TOPIC: {TOPIC_LABELS.get(topic_id, topic_id)}"]
    allowed = {topic_id, "overview", "other"}

    lines.append("\nRULES:")
    n = 0
    for r in notes.get("rules") or []:
        pt = r.get("speech_topic") or ""
        if pt not in allowed:
            continue
        n += 1
        if n > 45:
            break
        lines.append(
            f"R{n}. [{r.get('source')} p.{r.get('source_page')}] {(r.get('rule_en') or '').strip()}"
        )

    lines.append("\nEXAMPLES:")
    n = 0
    for e in notes.get("examples") or []:
        pt = e.get("speech_topic") or ""
        if pt not in allowed:
            continue
        n += 1
        if n > 35:
            break
        lines.append(
            f"E{n}. Direct: {(e.get('direct_en') or '')} | Indirect: {(e.get('indirect_en') or '')}"
        )

    lines.append("\nWORKED:")
    n = 0
    for w in notes.get("worked_exercises") or []:
        pt = w.get("speech_topic") or ""
        if pt not in allowed:
            continue
        n += 1
        if n > 25:
            break
        lines.append(f"W{n}. {(w.get('prompt_en') or '')} => {(w.get('answer_en') or '')}")
    return "\n".join(lines)


def structural_check(questions: list) -> list:
    issues = []
    for i, q in enumerate(questions, 1):
        stem = (q.get("question_en") or "").strip()
        if len(stem) < 12:
            issues.append(
                {
                    "q_index": i,
                    "issue_type": "nonsensical",
                    "severity": "high",
                    "description": "Stem too short or empty",
                    "suggestion": "DROP",
                    "correct_answer_letter": None,
                }
            )
            continue
        opts = q.get("options") or []
        keys = []
        texts = []
        for o in opts:
            if o.get("key") in "ABCD":
                keys.append(o.get("key"))
                texts.append((o.get("text_en") or "").strip().lower())
        if len(keys) < 4:
            issues.append(
                {
                    "q_index": i,
                    "issue_type": "bad_options",
                    "severity": "high",
                    "description": f"Only {len(keys)} options",
                    "suggestion": "DROP",
                    "correct_answer_letter": None,
                }
            )
        marked = (q.get("correct_option") or "").strip().upper()[:1]
        if marked not in keys:
            issues.append(
                {
                    "q_index": i,
                    "issue_type": "wrong_answer",
                    "severity": "high",
                    "description": f"Marked {marked} not in options {keys}",
                    "suggestion": "DROP",
                    "correct_answer_letter": None,
                }
            )
        if len(set(texts)) < len(texts):
            issues.append(
                {
                    "q_index": i,
                    "issue_type": "bad_options",
                    "severity": "high",
                    "description": "Duplicate option text",
                    "suggestion": "DROP",
                    "correct_answer_letter": None,
                }
            )
    return issues


def verify_batch(api_key, questions, notes_block, topic_id, topic_en, batch):
    q_block = []
    for i, q in enumerate(questions, 1):
        src = (q.get("source_note") or "").strip()
        src_line = f"  Source: {src}\n" if src else ""
        opts = [
            f"{o.get('key')}) {(o.get('text_en') or '').strip()}"
            for o in (q.get("options") or [])
            if o.get("key") in "ABCD"
        ]
        q_block.append(
            f"Q{i}: {(q.get('question_en') or '').strip()}\n"
            f"{src_line}"
            f"  Options: {' | '.join(opts)}\n"
            f"  Marked answer: {q.get('correct_option')}\n"
            f"  Explanation: {(q.get('explanation') or '')[:220]}\n"
        )

    prompt = f"""You are a strict TNPSC General English (SSLC Standard) Direct & Indirect Speech verifier.
Verify these {len(questions)} MCQs for "{topic_en}" ({topic_id}) — {batch}.

REFERENCE NOTES (Grammer primary + Govt). Ground truth for answers:
{notes_block[:14000]}

QUESTIONS:
{''.join(q_block)}

Check EACH question for:
1) wrong_answer — marked letter wrong per notes / standard SSLC reported-speech rules
2) bad_options — duplicate, ambiguous, two correct, weak distractors
3) not_tnpsc — too trivial/obscure/college-level; not exam-style speech MCQ
4) nonsensical — broken stem, unclear task, bad English
5) explanation_mismatch — explanation contradicts marked answer
6) off_topic — not testing the intended speech rule for this batch

Be strict but fair. TNPSC Group exams expect SSLC-level direct/indirect speech MCQs.
Only flag genuinely problematic items.

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
    return parse_json(call_gemini(api_key, prompt))


def apply_flags(questions, flagged):
    drop_idx = set()
    fixes = 0
    details = []
    for f in flagged:
        idx = int(f.get("q_index") or 0) - 1
        if idx < 0 or idx >= len(questions):
            continue
        issue = f.get("issue_type") or ""
        sug = (f.get("suggestion") or "").strip().upper()
        sev = (f.get("severity") or "medium").lower()
        desc = (f.get("description") or "")[:200]
        letter = (f.get("correct_answer_letter") or "").strip().upper()[:1]
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
            if sug == "DROP" or sev == "high" or issue == "nonsensical":
                drop_idx.add(idx)
        elif issue == "bad_options" and sev == "high":
            drop_idx.add(idx)
        elif issue == "explanation_mismatch" and letter in "ABCD":
            questions[idx]["correct_option"] = letter
            questions[idx]["verify_fixed"] = True
            fixes += 1
            details[-1]["new_answer"] = letter

    cleaned = [q for i, q in enumerate(questions) if i not in drop_idx]
    return cleaned, fixes, len(drop_idx), details


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--topic")
    parser.add_argument("--batch", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    api_key = get_api_key()
    db = load_json(DB_PATH, [])
    notes = load_json(NOTES_PATH, {})
    report = load_json(REPORT_PATH, {"batches": {}}) if args.resume else {"batches": {}}

    if not args.resume and not args.dry_run:
        backup = DB_PATH.replace(".json", ".pre_verify_backup.json")
        if os.path.exists(DB_PATH):
            shutil.copy2(DB_PATH, backup)
            print(f"Backup → {backup}")

    by_batch = defaultdict(list)
    order = []
    for q in db:
        if (q.get("topic") or "").strip() == "Mixed Direct & Indirect Speech":
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

        questions = list(by_batch.get(bkey) or [])
        if not questions:
            print(f"MISSING batch {bkey}")
            continue

        topic_id = questions[0].get("topic_id") or "?"
        topic_en = questions[0].get("topic") or TOPIC_LABELS.get(topic_id, topic_id)
        batch = questions[0].get("batch") or "?"
        notes_block = notes_text(notes, topic_id)

        print(f"\n=== Verifying: {topic_en} | {batch} ({len(questions)} Q) ===", flush=True)

        local_flags = structural_check(questions)
        if local_flags:
            print(f"  Structural issues: {len(local_flags)}", flush=True)

        try:
            result = verify_batch(
                api_key, questions, notes_block, topic_id, topic_en, batch
            )
        except Exception as e:
            print(f"  VERIFY FAILED: {e}", flush=True)
            report.setdefault("batches", {})[bkey] = {"done": False, "error": str(e)}
            save_json(REPORT_PATH, report)
            updated[bkey] = questions
            time.sleep(5)
            continue

        flagged = (result.get("flagged_questions") or []) + local_flags
        summary = result.get("batch_summary") or {}
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
        if len(cleaned) < 20 and dropped:
            cleaned, fixes, dropped, details = apply_flags(
                questions,
                [
                    f
                    for f in flagged
                    if (f.get("suggestion") or "").upper() == "FIX_ANSWER"
                    or f.get("issue_type") == "wrong_answer"
                    or (
                        f.get("issue_type") == "explanation_mismatch"
                        and (f.get("correct_answer_letter") or "").strip().upper()[:1]
                        in "ABCD"
                    )
                ],
            )

        total_flagged += len(flagged)
        total_dropped += dropped
        total_fixed += fixes
        updated[bkey] = cleaned

        verdict = summary.get("verdict") or ("NEEDS_FIX" if flagged else "PASS")
        if flagged and not dropped and not fixes:
            verdict = "PASS_WITH_WARNINGS" if len(cleaned) == len(questions) else verdict

        report.setdefault("batches", {})[bkey] = {
            "done": True,
            "topic_en": topic_en,
            "summary": summary,
            "structural_flags": len(local_flags),
            "flagged_count": len(flagged),
            "flagged": details,
            "dropped": dropped,
            "fixed": fixes,
            "final_count": len(cleaned),
            "verdict": verdict,
        }
        save_json(REPORT_PATH, report)
        print(
            f"  After cleanup: {len(cleaned)} Q (dropped={dropped}, fixed={fixes})",
            flush=True,
        )

        if args.dry_run:
            updated[bkey] = questions
        time.sleep(2.5)

    if args.dry_run:
        print("\nDRY RUN — DB not modified")
        return

    mixed = [q for q in db if (q.get("topic") or "").strip() == "Mixed Direct & Indirect Speech"]
    clean_db = []
    for bkey in order:
        clean_db.extend(updated.get(bkey) or by_batch.get(bkey) or [])
    clean_db.extend(mixed)

    save_json(DB_PATH, clean_db)

    print(f"\n{'='*60}")
    print("VERIFICATION COMPLETE (250 speech Q)")
    print(f"Flagged: {total_flagged}, Dropped: {total_dropped}, Fixed: {total_fixed}")
    print(f"Final DB: {len(clean_db)} questions")
    c = Counter(
        (q.get("topic_id"), q.get("batch"))
        for q in clean_db
        if q.get("topic_id") != "mixed_direct_indirect"
    )
    short = []
    for k in sorted(c):
        n = c[k]
        mark = " OK" if n >= 25 else " SHORT"
        print(f"  {k[0]:28} {k[1]}: {n}{mark}")
        if n < 25:
            short.append((k[0], k[1], n))
    report["totals"] = {
        "flagged": total_flagged,
        "dropped": total_dropped,
        "fixed": total_fixed,
        "final_db": len(clean_db),
        "topic_q_verified": sum(n for _, n in c.items()),
        "short_batches": short,
        "pass_batches": sum(
            1
            for b in report.get("batches", {}).values()
            if b.get("verdict") in ("PASS", "PASS_WITH_WARNINGS")
        ),
        "needs_fix_batches": sum(
            1
            for b in report.get("batches", {}).values()
            if b.get("verdict") == "NEEDS_FIX"
        ),
    }
    save_json(REPORT_PATH, report)
    if short:
        print("\nSHORT batches needing top-up:", short)


if __name__ == "__main__":
    main()
