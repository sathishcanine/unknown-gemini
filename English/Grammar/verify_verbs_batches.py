#!/usr/bin/env python3
"""Verify Verbs practice batches (8 topic batches × 25) against verbs_notes.json."""

from __future__ import annotations

import json
import os
import shutil
import time
import urllib.error
import urllib.request
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "English", "Grammar", "verbs_questions_db.json")
NOTES_PATH = os.path.join(BASE_DIR, "English", "Grammar", "verbs_notes.json")
REPORT_PATH = os.path.join(BASE_DIR, "English", "Grammar", "verbs_verify_report.json")
MODELS = ["gemini-3.5-flash-lite", "gemini-2.5-flash"]

TOPIC_LABELS = {
    "main_verbs": "Main Verbs",
    "auxiliary_verbs": "Auxiliary Verbs",
    "regular_verbs": "Regular Verbs",
    "irregular_verbs": "Irregular Verbs",
    "mixed_verbs": "Mixed Verbs",
}


def load_json(path, default=None):
    if not os.path.exists(path):
        return default if default is not None else {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


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
    start = text.find("{")
    if start >= 0:
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return json.loads(text[start : i + 1])
    raise ValueError("parse fail")


def notes_text(notes: dict, topic_id: str = "") -> str:
    label = TOPIC_LABELS.get(topic_id, "Verbs (all types)")
    rules = notes.get("rules") or []
    if topic_id:
        rules = [r for r in rules if (r.get("verb_topic") or "") in (topic_id, "overview")] or rules
    lines = [f"TOPIC: {label}", "\nRULES:"]
    for i, r in enumerate(rules[:45], 1):
        lines.append(
            f"R{i}. [{r.get('verb_topic')}] p.{r.get('source_page')} {(r.get('rule_en') or '').strip()}"
        )
    lines.append("\nEXAMPLES:")
    ex = notes.get("examples") or []
    if topic_id:
        ex = [e for e in ex if (e.get("verb_topic") or "") in (topic_id, "overview")] or ex
    for i, e in enumerate(ex[:40], 1):
        lines.append(f"E{i}. {e.get('input_en')} → {e.get('output_en')}")
    lines.append("\nWORKED:")
    wk = notes.get("worked_exercises") or []
    if topic_id:
        wk = [w for w in wk if (w.get("verb_topic") or "") in (topic_id, "overview")] or wk
    for i, w in enumerate(wk[:35], 1):
        lines.append(f"W{i}. {w.get('prompt_en')} => {w.get('answer_en')}")
    return "\n".join(lines)


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
                "old_answer": questions[idx].get("correct_option"),
                "question_en": (questions[idx].get("question_en") or "")[:140],
            }
        )
        if sug == "FIX_ANSWER" or (issue == "wrong_answer" and letter in "ABCD"):
            if letter in "ABCD":
                questions[idx]["correct_option"] = letter
                questions[idx]["verify_fixed"] = True
                details[-1]["new_answer"] = letter
                fixes += 1
            elif sev == "high":
                drop_idx.add(idx)
        elif sug == "DROP" or (issue in ("nonsensical", "not_tnpsc", "off_topic", "tense_question", "question_tag") and sev == "high"):
            drop_idx.add(idx)
        elif issue == "explanation_mismatch" and letter in "ABCD":
            questions[idx]["correct_option"] = letter
            questions[idx]["verify_fixed"] = True
            fixes += 1
            details[-1]["new_answer"] = letter
    cleaned = [q for i, q in enumerate(questions) if i not in drop_idx]
    return cleaned, fixes, len(drop_idx), details


def main():
    api_key = os.environ.get("GEMINI_API_KEY") or ""
    if not api_key:
        raise SystemExit("GEMINI_API_KEY missing")

    if os.path.exists(DB_PATH):
        shutil.copy2(DB_PATH, DB_PATH.replace(".json", ".pre_verify_backup.json"))

    notes = load_json(NOTES_PATH)
    qs = load_json(DB_PATH, [])
    by_key = defaultdict(list)
    for q in qs:
        tid = q.get("topic_id") or "other"
        by_key[(tid, q.get("batch") or "Batch ?")].append(q)

    report = {"batches": {}, "totals": {"fixed": 0, "dropped": 0}}
    rebuilt = []

    for key in sorted(by_key.keys()):
        topic_id, batch = key
        questions = by_key[key]
        label = TOPIC_LABELS.get(topic_id, topic_id)
        print(f"Verifying {label} / {batch} ({len(questions)} Q)...")
        ntext = notes_text(notes, topic_id if topic_id != "mixed_verbs" else "")
        q_block = []
        for i, q in enumerate(questions, 1):
            opts = [
                f"{o.get('key')}) {(o.get('text_en') or '').strip()}"
                for o in (q.get("options") or [])
                if o.get("key") in "ABCD"
            ]
            q_block.append(
                f"Q{i}: {(q.get('question_en') or '').strip()}\n"
                f"  Options: {' | '.join(opts)}\n"
                f"  Marked answer: {q.get('correct_option')}\n"
                f"  Explanation: {(q.get('explanation') or '')[:220]}\n"
            )
        prompt = f"""Strict TNPSC General English Verbs verifier.
Verify these {len(questions)} MCQs for {label} / {batch}.
Focus: main/auxiliary/regular/irregular verbs ONLY — NOT tense usage, question tags, voice, or reported speech.

REFERENCE NOTES:
{ntext[:14000]}

QUESTIONS:
{''.join(q_block)}

Flag: wrong_answer | bad_options | not_tnpsc | nonsensical | explanation_mismatch | off_topic | tense_question | question_tag
Return ONLY JSON:
{{
  "batch_summary": {{"total": {len(questions)}, "passed": N, "flagged": N, "verdict": "PASS|NEEDS_FIX"}},
  "flagged_questions": [
    {{"q_index": 1, "issue_type": "...", "severity": "medium|high",
      "description": "...", "suggestion": "FIX_ANSWER|DROP|REVISE",
      "correct_answer_letter": "A|B|C|D or null"}}
  ]
}}
"""
        result = parse_json(call_gemini(api_key, prompt))
        flagged = result.get("flagged_questions") or []
        cleaned, fixes, drops, details = apply_flags(list(questions), flagged)
        if len(cleaned) < 20:
            cleaned, fixes, drops, details = apply_flags(
                list(questions),
                [
                    f
                    for f in flagged
                    if (f.get("suggestion") or "").upper() == "FIX_ANSWER"
                    or f.get("issue_type") == "wrong_answer"
                ],
            )
        print(
            f"  verdict={result.get('batch_summary', {}).get('verdict')} "
            f"flagged={len(flagged)} fixed={fixes} dropped={drops} kept={len(cleaned)}"
        )
        report["batches"][f"{label}|{batch}"] = {
            "summary": result.get("batch_summary"),
            "fixed": fixes,
            "dropped": drops,
            "kept": len(cleaned),
            "details": details,
        }
        report["totals"]["fixed"] += fixes
        report["totals"]["dropped"] += drops
        rebuilt.extend(cleaned)
        time.sleep(2)

    save_json(DB_PATH, rebuilt)
    save_json(REPORT_PATH, report)
    print(f"Saved {DB_PATH} ({len(rebuilt)} Q) and {REPORT_PATH}")


if __name__ == "__main__":
    main()
