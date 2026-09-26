#!/usr/bin/env python3
"""
Strict double-verify for Unit VII poem questions.

Pass A: rule-based format / options / English-only / uniqueness
Pass B: Gemini content check vs poem notes (wrong answer, off-topic, bad FoS, weak distractors)
Applies FIX_ANSWER / DROP; tops up to 25 if drops occur.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
POEMS_DIR = BASE_DIR / "English" / "Poems"
NOTES_DIR = POEMS_DIR / "notes"
PYQ_DIR = POEMS_DIR / "pyq"
Q_DIR = POEMS_DIR / "questions"
RULE_REPORT = POEMS_DIR / "poems_double_rule_audit.json"
GEMINI_REPORT = POEMS_DIR / "poems_double_verify_report.json"
COMBINED = POEMS_DIR / "poems_questions_db.json"
MODELS = ["gemini-2.5-flash", "gemini-3.5-flash-lite"]
TAMIL_RE = re.compile(r"[\u0B80-\u0BFF]")
TARGET = 25


def load_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default if default is not None else {}
    return json.loads(p.read_text(encoding="utf-8"))


def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rebuild_combined():
    combined = []
    for f in sorted(Q_DIR.glob("*_questions_db.json")):
        combined.extend(load_json(f, []))
    save_json(COMBINED, combined)
    return len(combined)


def rule_audit_poem(pid: str, qs: list) -> list:
    issues = []
    if len(qs) != TARGET:
        issues.append({"q": 0, "type": "count_not_25", "detail": f"count={len(qs)}"})
    stems = []
    for i, q in enumerate(qs, 1):
        qen = (q.get("question_en") or "").strip()
        qta = (q.get("question_ta") or "").strip()
        opts = q.get("options") or []
        abcd = [o for o in opts if str(o.get("key") or "") in "ABCD"]
        letter = (q.get("correct_option") or "").strip().upper()[:1]
        texts = [(o.get("text_en") or "").strip() for o in abcd]
        texts_l = [t.lower() for t in texts]

        def add(t, **kw):
            issues.append({"q": i, "type": t, **kw})

        if not qen:
            add("empty_stem")
        if TAMIL_RE.search(qen) or TAMIL_RE.search(qta or ""):
            add("tamil_in_english")
        if len(abcd) != 4:
            add("not_4_options", detail=len(abcd))
        if any(not t for t in texts):
            add("empty_option")
        if len(texts) == 4 and len(set(texts_l)) < 4:
            add("duplicate_options", options=texts)
        if letter not in ("A", "B", "C", "D"):
            add("bad_correct_letter", letter=letter or "")
        else:
            idx = ord(letter) - 65
            if idx >= len(texts) or not texts[idx]:
                add("correct_points_empty")
            for ti, t in enumerate(texts):
                if t.lower() == "answer not known" and letter == chr(65 + ti):
                    add("correct_is_answer_not_known")
        if len(qen) < 12:
            add("stem_too_short", stem=qen)
        if "<u>" in qen.lower() or "</u>" in qen.lower():
            add("underline_markup", stem=qen[:100])
        if any(len(t) <= 1 for t in texts):
            add("tiny_option", options=texts)
        # TNPSC: options should be distinct meaningful strings
        if any(t.lower() in ("n/a", "null", "none", "undefined", "test") for t in texts_l):
            add("placeholder_option", options=texts)
        stems.append(re.sub(r"\s+", " ", qen.lower()))
    for s, n in Counter(stems).items():
        if n > 1 and s:
            issues.append({"q": 0, "type": "duplicate_stem", "n": n, "stem": s[:120]})
    return issues


def apply_rule_fixes(qs: list, issues: list) -> tuple[list, int, int]:
    """Drop unsalvageable format issues; keep count for reporting."""
    drop = set()
    fixes = 0
    for iss in issues:
        q = int(iss.get("q") or 0)
        if q < 1 or q > len(qs):
            continue
        idx = q - 1
        t = iss.get("type")
        if t in (
            "empty_stem",
            "not_4_options",
            "empty_option",
            "duplicate_options",
            "bad_correct_letter",
            "correct_points_empty",
            "correct_is_answer_not_known",
            "tamil_in_english",
            "placeholder_option",
            "tiny_option",
        ):
            drop.add(idx)
        elif t == "underline_markup":
            # strip simple u tags
            qen = qs[idx].get("question_en") or ""
            cleaned = re.sub(r"</?u>", "", qen, flags=re.I)
            if cleaned != qen:
                qs[idx]["question_en"] = cleaned
                qs[idx]["question_ta"] = cleaned
                fixes += 1
    # duplicate stems: keep first
    seen = set()
    for i, q in enumerate(qs):
        stem = re.sub(r"\s+", " ", (q.get("question_en") or "").lower())
        if stem in seen:
            drop.add(i)
        else:
            seen.add(stem)
    kept = [q for i, q in enumerate(qs) if i not in drop]
    return kept, fixes, len(drop)


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
                        "temperature": 0.05,
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
                with urllib.request.urlopen(req, timeout=240) as resp:
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


def apply_gemini_flags(questions, flagged):
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
        elif sug == "DROP" or (
            issue
            in (
                "off_topic",
                "nonsensical",
                "not_poem",
                "ambiguous",
                "bad_options",
                "duplicate_options",
                "not_tnpsc_format",
            )
            and sev in ("high", "medium")
        ):
            if sev == "high" or sug == "DROP":
                drop.add(idx)
            elif issue in ("bad_options", "ambiguous", "not_tnpsc_format") and sev == "medium":
                drop.add(idx)
    return [q for i, q in enumerate(questions) if i not in drop], fixes, len(drop)


def gemini_verify(pid: str, qs: list, api_key: str) -> dict:
    notes = load_json(NOTES_DIR / f"{pid}.json")
    pyq = load_json(PYQ_DIR / f"{pid}.json", {"questions": []})
    pyq_sample = []
    for i, q in enumerate((pyq.get("questions") or [])[:8], 1):
        pyq_sample.append(f"PYQ{i}: {q.get('question_en')}")
    ref = (
        f"POEM: {notes.get('poem_title')} — {notes.get('author')}\n"
        f"SUMMARY: {notes.get('summary_en')}\n"
        f"TEXT:\n{(notes.get('poem_text_en') or '')[:2200]}\n"
        f"FoS: {json.dumps((notes.get('figures_of_speech') or [])[:15], ensure_ascii=False)}\n"
        f"GLOSS: {json.dumps((notes.get('glossary') or [])[:20], ensure_ascii=False)}\n"
        f"RULES: {json.dumps((notes.get('rules') or [])[:15], ensure_ascii=False)}\n"
        f"WORKED: {json.dumps((notes.get('worked_exercises') or [])[:10], ensure_ascii=False)}\n"
        f"REAL PYQ STEM SAMPLES (format reference):\n" + "\n".join(pyq_sample)
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
    prompt = f"""You are a STRICT TNPSC Group exams (General English — Unit VII Poems) question auditor.

Check EVERY question for:
1. TNPSC MCQ format (clear stem, exactly 4 plausible options A–D, one unambiguously correct)
2. Marked answer is factually correct vs poem notes/text/glossary/FoS
3. Options are valid (no duplicates, no nonsense, no two correct answers, distractors plausible but wrong)
4. On-topic for THIS poem only (not other poems / unrelated grammar)
5. English only (no Tamil)
6. Style roughly like TNPSC poem PYQs (poet/title/theme/line meaning/FoS/alliteration/vocab)

Be strict but fair. Flag only real problems. Prefer FIX_ANSWER when the right letter is clear; DROP when stem/options are bad.

REFERENCE NOTES:
{ref[:13000]}

QUESTIONS ({len(qs)}):
{''.join(q_block)}

Return ONLY JSON:
{{
  "batch_summary": {{
    "total": {len(qs)},
    "flagged": N,
    "tnpsc_format_ok": true/false,
    "verdict": "PASS|NEEDS_FIX|FAIL"
  }},
  "flagged_questions": [
    {{
      "q_index": 1,
      "issue_type": "wrong_answer|off_topic|bad_options|ambiguous|nonsensical|not_poem|duplicate_options|not_tnpsc_format|tamil",
      "severity": "medium|high",
      "description": "short reason",
      "suggestion": "FIX_ANSWER|DROP",
      "correct_answer_letter": "A|B|C|D or null"
    }}
  ]
}}
"""
    result = parse_json(call_gemini(api_key, prompt))
    flagged = result.get("flagged_questions") or []
    summary = result.get("batch_summary") or {}
    cleaned, fixes, drops = apply_gemini_flags(list(qs), flagged)
    return {
        "summary": summary,
        "flagged": flagged,
        "fixed": fixes,
        "dropped": drops,
        "kept": cleaned,
    }


def topup_poem(pid: str, qs: list, api_key: str) -> list:
    """Generate replacements to reach TARGET."""
    if len(qs) >= TARGET:
        return qs[:TARGET]
    notes = load_json(NOTES_DIR / f"{pid}.json")
    need = TARGET - len(qs)
    seen = {re.sub(r"\s+", " ", (q.get("question_en") or "").lower()) for q in qs}
    excl = "\n".join(f"- {q.get('question_en')}" for q in qs)
    prompt = f"""TNPSC Unit VII poem practice. Poem: "{notes.get('poem_title')}" by {notes.get('author')}.
Generate exactly {need + 4} SAFE MCQs grounded ONLY in this poem.
English only. Exactly 4 options. One clear correct answer.
Avoid contested FoS if unsure. Prefer poet/title/theme/line/glossary items.
Do NOT duplicate:
{excl}

POEM TEXT:
{(notes.get('poem_text_en') or '')[:2000]}
SUMMARY: {notes.get('summary_en')}
GLOSS: {json.dumps((notes.get('glossary') or [])[:15], ensure_ascii=False)}
FoS: {json.dumps((notes.get('figures_of_speech') or [])[:10], ensure_ascii=False)}

Return ONLY JSON array:
[{{"question_en":"...","options_en":["A","B","C","D"],"answer_en":"...","explanation_en":"...","source_note":"..."}}]
"""
    try:
        text = call_gemini(api_key, prompt)
        t = text.strip()
        if t.startswith("```"):
            t = t.split("\n", 1)[1]
            if t.endswith("```"):
                t = t.rsplit("\n", 1)[0]
        raw_list = []
        start = t.find("[")
        if start >= 0:
            depth = 0
            for i, ch in enumerate(t[start:], start):
                if ch == "[":
                    depth += 1
                elif ch == "]":
                    depth -= 1
                    if depth == 0:
                        raw_list = json.loads(t[start : i + 1])
                        break
    except Exception as e:
        print(f"  topup fail: {e}")
        return qs

    poem_meta = {
        "title": notes.get("poem_title"),
        "id": pid,
        "author": notes.get("author"),
    }
    for r in raw_list:
        q_en = (r.get("question_en") or "").strip()
        opts = [str(x).strip() for x in (r.get("options_en") or []) if str(x).strip()][:4]
        if not q_en or len(opts) < 4 or len(set(o.lower() for o in opts)) < 4:
            continue
        stem = re.sub(r"\s+", " ", q_en.lower())
        if stem in seen:
            continue
        ans = (r.get("answer_en") or "").strip()
        letter = None
        for i, o in enumerate(opts):
            if o == ans or o.lower() == ans.lower():
                letter = chr(65 + i)
                break
        if not letter and ans.upper()[:1] in "ABCD" and len(ans) <= 2:
            letter = ans.upper()[:1]
        if not letter:
            continue
        options = [{"key": chr(65 + i), "text_en": o, "text_ta": o} for i, o in enumerate(opts)]
        options.append({"key": "E", "text_en": "Answer not known", "text_ta": "Answer not known"})
        expl = (r.get("explanation_en") or "").strip()
        qs.append(
            {
                "subject": "English",
                "unit": "Poems",
                "menu": poem_meta["title"],
                "topic": poem_meta["title"],
                "topic_id": pid,
                "topic_ta": poem_meta["title"],
                "source_exam": "Practice Batch 1",
                "difficulty": "Medium",
                "question_en": q_en,
                "question_ta": q_en,
                "options": options,
                "correct_option": letter,
                "explanation": expl,
                "explanation_ta": expl,
                "type": "practice",
                "batch": "Batch 1",
                "group": pid,
                "source_note": (r.get("source_note") or "double-verify topup").strip(),
            }
        )
        seen.add(stem)
        if len(qs) >= TARGET:
            break
    return qs[:TARGET]


def process_poem(pid: str, api_key: str, skip_gemini: bool = False) -> dict:
    path = Q_DIR / f"{pid}_questions_db.json"
    qs = load_json(path, [])
    out = {"pid": pid, "start": len(qs)}

    # Pass A
    rule_issues = rule_audit_poem(pid, qs)
    qs, rfix, rdrop = apply_rule_fixes(list(qs), rule_issues)
    out["rule_issues"] = len(rule_issues)
    out["rule_fixed"] = rfix
    out["rule_dropped"] = rdrop

    # Pass B
    if skip_gemini:
        out["gemini"] = {"skipped": True}
    else:
        g = gemini_verify(pid, qs, api_key)
        qs = g["kept"]
        out["gemini"] = {
            "verdict": (g.get("summary") or {}).get("verdict"),
            "tnpsc_format_ok": (g.get("summary") or {}).get("tnpsc_format_ok"),
            "flagged": len(g.get("flagged") or []),
            "fixed": g.get("fixed"),
            "dropped": g.get("dropped"),
            "flagged_questions": g.get("flagged") or [],
            "summary": g.get("summary") or {},
        }

    # Top up
    if len(qs) < TARGET:
        print(f"  topping up {pid}: {len(qs)} → {TARGET}")
        qs = topup_poem(pid, qs, api_key)
        # light re-check new ones with rules only
        rule2 = rule_audit_poem(pid, qs)
        qs, _, _ = apply_rule_fixes(list(qs), rule2)

    # final rule snapshot
    final_issues = rule_audit_poem(pid, qs)
    out["final_count"] = len(qs)
    out["final_rule_issues"] = len(final_issues)
    out["final_rule_detail"] = final_issues
    save_json(path, qs)
    print(
        f"  {pid}: start={out['start']} rule_iss={out['rule_issues']} "
        f"g_flag={out.get('gemini', {}).get('flagged')} "
        f"g_fix={out.get('gemini', {}).get('fixed')} "
        f"g_drop={out.get('gemini', {}).get('dropped')} "
        f"final={out['final_count']} remain_rule={out['final_rule_issues']} "
        f"verdict={out.get('gemini', {}).get('verdict')}"
    )
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--poem", type=str)
    parser.add_argument("--rules-only", action="store_true")
    args = parser.parse_args()
    api_key = os.environ.get("GEMINI_API_KEY") or ""
    if not args.rules_only and not api_key:
        raise SystemExit("GEMINI_API_KEY missing")

    files = sorted(Q_DIR.glob("*_questions_db.json"))
    if args.poem:
        files = [Q_DIR / f"{args.poem}_questions_db.json"]

    report = {"poems": {}, "totals": {}}
    for f in files:
        pid = f.name.replace("_questions_db.json", "")
        print(f"\n=== Double-verify {pid} ===")
        report["poems"][pid] = process_poem(pid, api_key, skip_gemini=args.rules_only)
        if not args.rules_only:
            time.sleep(1.2)

    total = rebuild_combined()
    report["totals"] = {
        "combined": total,
        "poems": len(report["poems"]),
        "need_attention": [
            pid
            for pid, r in report["poems"].items()
            if r.get("final_count") != TARGET
            or r.get("final_rule_issues", 0) > 0
            or (r.get("gemini") or {}).get("verdict") == "FAIL"
        ],
    }
    save_json(GEMINI_REPORT, report)
    # also save rule-focused rollup
    save_json(
        RULE_REPORT,
        {
            pid: {
                "rule_issues": r.get("rule_issues"),
                "final_rule_issues": r.get("final_rule_issues"),
                "final_rule_detail": r.get("final_rule_detail"),
                "final_count": r.get("final_count"),
            }
            for pid, r in report["poems"].items()
        },
    )
    print(f"\nCombined={total} report → {GEMINI_REPORT}")
    if report["totals"]["need_attention"]:
        print("NEED ATTENTION:", ", ".join(report["totals"]["need_attention"]))
    else:
        print("All poems clean at 25 Q with no remaining rule issues.")


if __name__ == "__main__":
    main()
