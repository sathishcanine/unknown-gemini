#!/usr/bin/env python3
"""
Strict double-verify for Unit III Writing Skills + Unit IV Technical Terms.

Pass A: rule-based format / options / English-only / uniqueness
Pass B: Gemini content check vs Vetri extract (+ Asan notes where present)
Applies FIX_ANSWER / DROP; tops up per-batch to 25 if drops occur.
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
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
WS = BASE / "English" / "WritingSkills"
TT = BASE / "English" / "TechnicalTerms"
REPORT = WS / "unit34_double_verify_report.json"
RULE_REPORT = WS / "unit34_double_rule_audit.json"
MODELS = ["gemini-2.5-flash", "gemini-3.5-flash-lite"]
TAMIL_RE = re.compile(r"[\u0B80-\u0BFF]")
LETTER_PREFIX_RE = re.compile(r"^[A-Ea-e][\).\:\-]\s*")
TARGET_PER_BATCH = 25

TOPIC_META = {
    "letter_writing": {
        "extract": WS / "vetri_extract" / "letter_writing.json",
        "asan_notes": WS / "letter_writing_notes.json",
        "db": WS / "letter_writing_questions_db.json",
        "topic": "Types of Letters (Formal & Informal)",
        "unit": "WritingSkills",
        "shapes": "Letter parts, formal vs informal, salutation/subscription, enquiry/complaint/order/apology.",
    },
    "jumbled_sentences": {
        "extract": WS / "vetri_extract" / "jumbled_sentences.json",
        "asan_notes": WS / "jumbled_sentences_notes.json",
        "db": WS / "jumbled_sentences_questions_db.json",
        "topic": "Jumbled Sentences",
        "unit": "WritingSkills",
        "shapes": "Rearrange words/sentences; identify first/last; choose correct sequence.",
    },
    "making_queries": {
        "extract": WS / "vetri_extract" / "making_queries.json",
        "asan_notes": None,
        "db": WS / "making_queries_questions_db.json",
        "topic": "Making Queries",
        "unit": "WritingSkills",
        "shapes": "Polite queries, interrogative forms for seeking information.",
    },
    "inferences_blanks_substitutions": {
        "extract": WS / "vetri_extract" / "inferences_blanks_substitutions.json",
        "asan_notes": None,
        "db": WS / "inferences_blanks_substitutions_questions_db.json",
        "topic": "Inferences, Blanks & Substitutions",
        "unit": "WritingSkills",
        "shapes": "Fill blanks, substitutions, inferences from short passages.",
    },
    "administrative_terms": {
        "extract": TT / "vetri_extract" / "administrative_terms.json",
        "asan_notes": None,
        "db": TT / "administrative_terms_questions_db.json",
        "topic": "Administrative Terms",
        "unit": "TechnicalTerms",
        "shapes": "Meaning/definition of administrative terms.",
    },
    "department_related_terms": {
        "extract": TT / "vetri_extract" / "department_related_terms.json",
        "asan_notes": None,
        "db": TT / "department_related_terms_questions_db.json",
        "topic": "Department-related Terms",
        "unit": "TechnicalTerms",
        "shapes": "Departmental terminology meanings and usage.",
    },
    "general_official_terms": {
        "extract": TT / "vetri_extract" / "general_official_terms.json",
        "asan_notes": None,
        "db": TT / "general_official_terms_questions_db.json",
        "topic": "General & Official Terms",
        "unit": "TechnicalTerms",
        "shapes": "General/official term definitions in government English.",
    },
    "official_correspondence": {
        "extract": TT / "vetri_extract" / "official_correspondence.json",
        "asan_notes": None,
        "db": TT / "official_correspondence_questions_db.json",
        "topic": "Basics of Official Correspondence",
        "unit": "TechnicalTerms",
        "shapes": "GO, circular, notification, office note, D.O. letter, memorandum.",
    },
}


def load_json(path, default=None):
    p = Path(path) if path else None
    if not p or not p.exists():
        return default if default is not None else {}
    return json.loads(p.read_text(encoding="utf-8"))


def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clean_option(t: str) -> str:
    t = (t or "").strip()
    for _ in range(3):
        n = LETTER_PREFIX_RE.sub("", t).strip()
        if n == t:
            break
        t = n
    return t


def ground(topic_id: str) -> str:
    meta = TOPIC_META[topic_id]
    extract = load_json(meta["extract"], {})
    asan = load_json(meta["asan_notes"], {}) if meta.get("asan_notes") else {}
    lines = [
        f"TOPIC: {extract.get('topic_title') or meta['topic']}",
        f"SUMMARY:\n{(extract.get('notes_en') or '')[:2500]}",
        "\nRULES:",
    ]
    for i, r in enumerate((extract.get("rules") or [])[:40], 1):
        lines.append(f"R{i}: {r.get('rule_en')} [{r.get('tag')}]")
    lines.append("\nGLOSSARY:")
    for i, g in enumerate((extract.get("glossary") or [])[:80], 1):
        lines.append(f"G{i}: {g.get('term_en')} = {g.get('meaning_en')}")
    lines.append("\nEXAMPLES:")
    for i, e in enumerate((extract.get("examples") or [])[:30], 1):
        lines.append(f"E{i}: {e.get('note_en')}")
    lines.append("\nVETRI PYQ (style reference — answers must match facts):")
    for i, q in enumerate((extract.get("pyq") or [])[:40], 1):
        opts = " | ".join((q.get("options_en") or [])[:4])
        lines.append(
            f"P{i}: {q.get('question_en')} => {q.get('answer_letter') or q.get('answer_en')} :: {opts}"
        )
    if asan and isinstance(asan, dict):
        for i, r in enumerate((asan.get("rules") or [])[:25], 1):
            lines.append(f"AR{i}: {r.get('rule_en')}")
    return "\n".join(lines)


def expected_count(topic_id: str, qs: list) -> int:
    extract = load_json(TOPIC_META[topic_id]["extract"], {})
    n = int(extract.get("batches_target") or 2)
    n = max(1, min(3, n))
    # Prefer current batch count if already multi-batch
    batches = {q.get("batch") or "Batch 1" for q in qs}
    if len(batches) >= 1 and len(qs) in (25, 50, 75):
        return len(qs)
    return n * TARGET_PER_BATCH


def rule_audit(tid: str, qs: list, target: int) -> list:
    issues = []
    if len(qs) != target:
        issues.append({"q": 0, "type": "count_mismatch", "detail": f"count={len(qs)} target={target}"})
    stems = []
    for i, q in enumerate(qs, 1):
        qen = (q.get("question_en") or "").strip()
        qta = (q.get("question_ta") or "").strip()
        opts = q.get("options") or []
        abcd = [o for o in opts if str(o.get("key") or "") in "ABCD"]
        letter = (q.get("correct_option") or "").strip().upper()[:1]
        texts = [clean_option(o.get("text_en") or "") for o in abcd]
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
        if any(t.lower() in ("n/a", "null", "none", "undefined", "test") for t in texts_l):
            add("placeholder_option", options=texts)
        stems.append(re.sub(r"\s+", " ", qen.lower()))
    for s, n in Counter(stems).items():
        if n > 1 and s:
            issues.append({"q": 0, "type": "duplicate_stem", "n": n, "stem": s[:120]})
    return issues


def apply_rule_fixes(qs: list, issues: list) -> tuple[list, int, int]:
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
            qen = qs[idx].get("question_en") or ""
            cleaned = re.sub(r"</?u>", "", qen, flags=re.I)
            if cleaned != qen:
                qs[idx]["question_en"] = cleaned
                qs[idx]["question_ta"] = cleaned
                fixes += 1
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


def gemini_verify_chunk(topic_id: str, qs: list, api_key: str, offset: int = 0) -> dict:
    meta = TOPIC_META[topic_id]
    ref = ground(topic_id)
    q_block = []
    for i, q in enumerate(qs, 1):
        opts = [
            f"{o.get('key')}) {clean_option(o.get('text_en') or '')}"
            for o in (q.get("options") or [])
            if o.get("key") in "ABCD"
        ]
        q_block.append(
            f"Q{i}: {q.get('question_en')}\n  Options: {' | '.join(opts)}\n"
            f"  Marked: {q.get('correct_option')}\n"
        )
    prompt = f"""You are a STRICT TNPSC Group exams (General English — {meta['unit']}: {meta['topic']}) question auditor.

Check EVERY question for:
1. TNPSC MCQ format (clear stem, exactly 4 plausible options A–D, one unambiguously correct)
2. Marked answer is factually correct vs NOTES/GLOSSARY/RULES/PYQ facts
3. Options valid (no duplicates, no nonsense, no two correct answers)
4. On-topic for "{meta['topic']}" only — shapes: {meta['shapes']}
5. English only (no Tamil)
6. Style like TNPSC Writing Skills / Technical Terms items

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
      "issue_type": "wrong_answer|off_topic|bad_options|ambiguous|nonsensical|duplicate_options|not_tnpsc_format|tamil",
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
    # Remap q_index stays local to chunk; caller merges
    summary = result.get("batch_summary") or {}
    cleaned, fixes, drops = apply_gemini_flags(list(qs), flagged)
    return {
        "summary": summary,
        "flagged": flagged,
        "fixed": fixes,
        "dropped": drops,
        "kept": cleaned,
        "offset": offset,
    }


def letter_for(opts, ans):
    ae = clean_option(ans or "")
    for i, o in enumerate(opts):
        if clean_option(o) == ae or clean_option(o).lower() == ae.lower():
            return chr(65 + i)
    if ae.upper()[:1] in "ABCD" and len(ae) <= 2:
        return ae.upper()[:1]
    return None


def topup_batch(topic_id: str, qs: list, batch_label: str, need: int, api_key: str) -> list:
    if need <= 0:
        return qs
    meta = TOPIC_META[topic_id]
    extract = load_json(meta["extract"], {})
    ref = ground(topic_id)
    seen = {re.sub(r"\s+", " ", (q.get("question_en") or "").lower()) for q in qs}
    excl = "\n".join(f"- {q.get('question_en')}" for q in qs[-80:])
    batch_num = 1
    m = re.search(r"(\d+)", batch_label or "")
    if m:
        batch_num = int(m.group(1))
    prompt = f"""TNPSC General English practice for "{meta['topic']}".
Generate exactly {need + 4} SAFE MCQs grounded ONLY in the notes below.
English only. Exactly 4 options. One clear correct answer.
Shapes: {meta['shapes']}
Do NOT duplicate:
{excl}

GROUND:
{ref[:12000]}

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

    added = 0
    for r in raw_list:
        if added >= need:
            break
        q_en = (r.get("question_en") or "").strip()
        opts = [clean_option(str(x)) for x in (r.get("options_en") or []) if str(x).strip()][:4]
        if not q_en or len(opts) < 4 or len(set(o.lower() for o in opts)) < 4:
            continue
        stem = re.sub(r"\s+", " ", q_en.lower())
        if stem in seen:
            continue
        if any(
            stem == re.sub(r"\s+", " ", (pq.get("question_en") or "").lower())
            for pq in (extract.get("pyq") or [])
        ):
            continue
        letter = letter_for(opts, r.get("answer_en"))
        if not letter:
            continue
        expl = (r.get("explanation_en") or "").strip()
        options = [{"key": chr(65 + i), "text_en": o, "text_ta": o} for i, o in enumerate(opts)]
        options.append({"key": "E", "text_en": "Answer not known", "text_ta": "Answer not known"})
        qs.append(
            {
                "subject": "English",
                "unit": meta["unit"],
                "menu": meta["topic"],
                "topic": meta["topic"],
                "topic_id": meta["topic"].lower().replace(" ", "_").replace("&", "and").replace(",", ""),
                "topic_ta": meta["topic"],
                "source_exam": f"Practice Batch {batch_num}",
                "difficulty": "Medium",
                "question_en": q_en,
                "question_ta": q_en,
                "options": options,
                "correct_option": letter,
                "explanation": expl,
                "explanation_ta": expl,
                "type": "practice",
                "batch": batch_label or f"Batch {batch_num}",
                "group": meta["topic"],
                "source_note": (r.get("source_note") or "double-verify topup").strip(),
            }
        )
        seen.add(stem)
        added += 1
    return qs


def split_by_batch(qs: list) -> dict[str, list]:
    buckets: dict[str, list] = defaultdict(list)
    for q in qs:
        buckets[q.get("batch") or "Batch 1"].append(q)
    if not buckets:
        buckets["Batch 1"] = []
    return dict(sorted(buckets.items(), key=lambda x: x[0]))


def process_topic(topic_id: str, api_key: str, skip_gemini: bool = False) -> dict:
    meta = TOPIC_META[topic_id]
    path = meta["db"]
    qs = load_json(path, [])
    target = expected_count(topic_id, qs)
    out = {"topic_id": topic_id, "start": len(qs), "target": target}

    rule_issues = rule_audit(topic_id, qs, target)
    qs, rfix, rdrop = apply_rule_fixes(list(qs), rule_issues)
    out["rule_issues"] = len(rule_issues)
    out["rule_fixed"] = rfix
    out["rule_dropped"] = rdrop

    all_flagged = []
    g_fix = g_drop = 0
    verdicts = []
    if skip_gemini:
        out["gemini"] = {"skipped": True}
    else:
        # Verify in chunks of 25 to keep context tight
        kept_all = []
        for i in range(0, max(len(qs), 1), TARGET_PER_BATCH):
            chunk = qs[i : i + TARGET_PER_BATCH]
            if not chunk:
                continue
            print(f"  Gemini chunk {i // TARGET_PER_BATCH + 1} ({len(chunk)} Q)...")
            g = gemini_verify_chunk(topic_id, chunk, api_key, offset=i)
            kept_all.extend(g["kept"])
            g_fix += g.get("fixed") or 0
            g_drop += g.get("dropped") or 0
            for f in g.get("flagged") or []:
                ff = dict(f)
                ff["q_index"] = int(f.get("q_index") or 0) + i
                all_flagged.append(ff)
            verdicts.append((g.get("summary") or {}).get("verdict"))
            time.sleep(1.0)
        qs = kept_all
        # Aggregate verdict
        if "FAIL" in verdicts:
            verdict = "FAIL"
        elif "NEEDS_FIX" in verdicts:
            verdict = "NEEDS_FIX"
        elif verdicts:
            verdict = "PASS"
        else:
            verdict = None
        out["gemini"] = {
            "verdict": verdict,
            "flagged": len(all_flagged),
            "fixed": g_fix,
            "dropped": g_drop,
            "flagged_questions": all_flagged,
            "chunk_verdicts": verdicts,
        }

    # Top up per batch to 25
    by_batch = split_by_batch(qs)
    # If we lost entire batches, recreate empty slots from original target
    n_batches = max(1, target // TARGET_PER_BATCH)
    for b in range(1, n_batches + 1):
        label = f"Batch {b}"
        if label not in by_batch:
            by_batch[label] = []
    rebuilt = []
    for label in sorted(by_batch.keys(), key=lambda x: int(re.search(r"\d+", x).group()) if re.search(r"\d+", x) else 0):
        batch_qs = by_batch[label]
        if len(batch_qs) < TARGET_PER_BATCH:
            print(f"  topping up {topic_id} {label}: {len(batch_qs)} → {TARGET_PER_BATCH}")
            batch_qs = topup_batch(
                topic_id, batch_qs, label, TARGET_PER_BATCH - len(batch_qs), api_key
            )
            rule2 = rule_audit(topic_id, batch_qs, len(batch_qs))
            batch_qs, _, _ = apply_rule_fixes(list(batch_qs), rule2)
        rebuilt.extend(batch_qs[:TARGET_PER_BATCH])
    qs = rebuilt[:target]

    # If still short overall, fill Batch 1
    while len(qs) < target and not skip_gemini:
        label = f"Batch {(len(qs) // TARGET_PER_BATCH) + 1}"
        before = len(qs)
        qs = topup_batch(topic_id, qs, label, min(TARGET_PER_BATCH, target - len(qs)), api_key)
        if len(qs) == before:
            break

    final_issues = rule_audit(topic_id, qs, target)
    # Don't fail solely on count_mismatch if we report it — still save
    out["final_count"] = len(qs)
    out["final_rule_issues"] = len([i for i in final_issues if i.get("type") != "count_mismatch"])
    out["final_rule_detail"] = final_issues
    save_json(path, qs)
    print(
        f"  {topic_id}: start={out['start']} rule_iss={out['rule_issues']} "
        f"g_flag={out.get('gemini', {}).get('flagged')} "
        f"g_fix={out.get('gemini', {}).get('fixed')} "
        f"g_drop={out.get('gemini', {}).get('dropped')} "
        f"final={out['final_count']} remain_rule={out['final_rule_issues']} "
        f"verdict={out.get('gemini', {}).get('verdict')}"
    )
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", type=str, choices=list(TOPIC_META.keys()))
    parser.add_argument("--unit", type=int, choices=[3, 4], help="3=WritingSkills 4=TechnicalTerms")
    parser.add_argument("--rules-only", action="store_true")
    args = parser.parse_args()
    api_key = os.environ.get("GEMINI_API_KEY") or ""
    if not args.rules_only and not api_key:
        raise SystemExit("GEMINI_API_KEY missing")

    topics = list(TOPIC_META.keys())
    if args.topic:
        topics = [args.topic]
    elif args.unit == 3:
        topics = [t for t, m in TOPIC_META.items() if m["unit"] == "WritingSkills"]
    elif args.unit == 4:
        topics = [t for t, m in TOPIC_META.items() if m["unit"] == "TechnicalTerms"]

    report = {"topics": {}, "totals": {}}
    for tid in topics:
        print(f"\n=== Double-verify {tid} ===")
        report["topics"][tid] = process_topic(tid, api_key, skip_gemini=args.rules_only)
        if not args.rules_only:
            time.sleep(1.2)

    need = [
        tid
        for tid, r in report["topics"].items()
        if r.get("final_count") != r.get("target")
        or r.get("final_rule_issues", 0) > 0
        or (r.get("gemini") or {}).get("verdict") == "FAIL"
    ]
    report["totals"] = {
        "topics": len(report["topics"]),
        "questions": sum(r.get("final_count") or 0 for r in report["topics"].values()),
        "need_attention": need,
    }
    save_json(REPORT, report)
    save_json(
        RULE_REPORT,
        {
            tid: {
                "rule_issues": r.get("rule_issues"),
                "final_rule_issues": r.get("final_rule_issues"),
                "final_rule_detail": r.get("final_rule_detail"),
                "final_count": r.get("final_count"),
                "target": r.get("target"),
            }
            for tid, r in report["topics"].items()
        },
    )
    print(f"\nTotal Q={report['totals']['questions']} report → {REPORT}")
    if need:
        print("NEED ATTENTION:", ", ".join(need))
    else:
        print("All Unit III/IV topics clean at target counts.")


if __name__ == "__main__":
    main()
