#!/usr/bin/env python3
"""Verify poem practice batches (25 Q each) against notes + stored PYQ."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
POEMS_DIR = BASE_DIR / "English" / "Poems"
NOTES_DIR = POEMS_DIR / "notes"
PYQ_DIR = POEMS_DIR / "pyq"
Q_DIR = POEMS_DIR / "questions"
REPORT_PATH = POEMS_DIR / "poems_verify_report.json"
MODELS = ["gemini-3.5-flash-lite", "gemini-2.5-flash"]


def load_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default if default is not None else {}
    return json.loads(p.read_text(encoding="utf-8"))


def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def call_gemini(api_key: str, prompt: str) -> str:
    last = None
    for m in MODELS:
        delay = 10
        for _ in range(5):
            try:
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1},
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


def apply_flags(questions, flagged):
    drop = set()
    fixes = 0
    for f in flagged:
        idx = int(f.get("q_index") or 0) - 1
        if idx < 0 or idx >= len(questions):
            continue
        issue = f.get("issue_type") or ""
        sug = (f.get("suggestion") or "").upper()
        letter = (f.get("correct_answer_letter") or "").strip().upper()[:1]
        sev = (f.get("severity") or "medium").lower()
        if sug == "FIX_ANSWER" or (issue == "wrong_answer" and letter in "ABCD"):
            if letter in "ABCD":
                questions[idx]["correct_option"] = letter
                fixes += 1
            elif sev == "high":
                drop.add(idx)
        elif sug == "DROP" or (issue in ("off_topic", "nonsensical", "not_poem") and sev == "high"):
            drop.add(idx)
    return [q for i, q in enumerate(questions) if i not in drop], fixes, len(drop)


def verify_poem(pid: str, api_key: str) -> dict:
    notes = load_json(NOTES_DIR / f"{pid}.json")
    qs = load_json(Q_DIR / f"{pid}_questions_db.json", [])
    if not qs:
        return {"kept": 0, "fixed": 0, "dropped": 0, "verdict": "EMPTY"}
    ref = (
        f"POEM: {notes.get('poem_title')} — {notes.get('author')}\n"
        f"SUMMARY: {notes.get('summary_en')}\n"
        f"TEXT:\n{(notes.get('poem_text_en') or '')[:2000]}\n"
        f"FoS: {json.dumps((notes.get('figures_of_speech') or [])[:15])}\n"
        f"GLOSS: {json.dumps((notes.get('glossary') or [])[:20])}\n"
    )
    q_block = []
    for i, q in enumerate(qs, 1):
        opts = [
            f"{o.get('key')}) {(o.get('text_en') or '').strip()}"
            for o in (q.get("options") or [])
            if o.get("key") in "ABCD"
        ]
        q_block.append(
            f"Q{i}: {q.get('question_en')}\n  Options: {' | '.join(opts)}\n"
            f"  Marked: {q.get('correct_option')}\n"
        )
    prompt = f"""Strict TNPSC Unit VII Poem verifier for "{notes.get('poem_title')}".
Flag wrong answers, off-topic (other poems / grammar unrelated), duplicate options.

REFERENCE:
{ref[:12000]}

QUESTIONS:
{''.join(q_block)}

Return ONLY JSON:
{{
  "batch_summary": {{"total": {len(qs)}, "flagged": N, "verdict": "PASS|NEEDS_FIX"}},
  "flagged_questions": [
    {{"q_index": 1, "issue_type": "wrong_answer|off_topic|bad_options|nonsensical|not_poem",
      "severity": "medium|high", "description": "...",
      "suggestion": "FIX_ANSWER|DROP", "correct_answer_letter": "A|B|C|D or null"}}
  ]
}}
"""
    result = parse_json(call_gemini(api_key, prompt))
    flagged = result.get("flagged_questions") or []
    summary = result.get("batch_summary") or {}
    cleaned, fixes, drops = apply_flags(list(qs), flagged)
    save_json(Q_DIR / f"{pid}_questions_db.json", cleaned)
    print(
        f"  {pid}: verdict={summary.get('verdict')} flagged={len(flagged)} "
        f"fixed={fixes} dropped={drops} kept={len(cleaned)}"
    )
    return {
        "summary": summary,
        "fixed": fixes,
        "dropped": drops,
        "kept": len(cleaned),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--poem", type=str)
    args = parser.parse_args()
    api_key = os.environ.get("GEMINI_API_KEY") or ""
    if not api_key:
        raise SystemExit("GEMINI_API_KEY missing")

    files = sorted(Q_DIR.glob("*_questions_db.json"))
    if args.poem:
        files = [Q_DIR / f"{args.poem}_questions_db.json"]
    report = {"poems": {}}
    for f in files:
        pid = f.name.replace("_questions_db.json", "")
        print(f"Verifying {pid}...")
        report["poems"][pid] = verify_poem(pid, api_key)
        time.sleep(1.5)
    # rebuild combined
    combined = []
    for f in sorted(Q_DIR.glob("*_questions_db.json")):
        combined.extend(load_json(f, []))
    save_json(POEMS_DIR / "poems_questions_db.json", combined)
    save_json(REPORT_PATH, report)
    print(f"Combined {len(combined)} Q; report → {REPORT_PATH}")


if __name__ == "__main__":
    main()
