#!/usr/bin/env python3
"""
Double-verify all Thirukkural practice batches (10 topics × Batch 1/2).

Checks: valid/sensible/TNPSC-level, Tamil quality, A-D options unique,
answer letter correct vs SM notes when possible.

Writes:
  Tamil/thirukkural_verify_report.json
  Tamil/thirukkural_questions_db.json  (cleaned)

Usage:
  python3 Tamil/verify_thirukkural_batches.py
  python3 Tamil/verify_thirukkural_batches.py --resume
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

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "Tamil", "thirukkural_questions_db.json")
NOTES_PATH = os.path.join(BASE_DIR, "Tamil", "unit7_thirukkural_adhikaram_notes_temp.json")
REPORT_PATH = os.path.join(BASE_DIR, "Tamil", "thirukkural_verify_report.json")
MODELS = ["gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-3.5-flash"]
CHUNK = 8


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
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=180) as resp:
                    return json.loads(resp.read().decode("utf-8"))["candidates"][0]["content"]["parts"][0]["text"]
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
    for opener, closer in (("[", "]"), ("{", "}")):
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


def opt_texts(q):
    out = []
    for o in q.get("options") or []:
        if isinstance(o, dict):
            out.append((o.get("text_ta") or o.get("text_en") or "").strip())
        else:
            out.append(str(o).strip())
    return out


def verify_chunk(api_key, topic, batch, notes_slice, questions, start_idx):
    payload_qs = []
    for i, q in enumerate(questions):
        payload_qs.append(
            {
                "i": start_idx + i,
                "stem": q.get("question_ta"),
                "options": opt_texts(q),
                "correct": q.get("correct_option"),
                "explanation": q.get("explanation_ta") or "",
                "adhikaram": q.get("adhikaram_name_ta"),
            }
        )
    prompt = f"""You are a strict TNPSC Group Tamil (திருக்குறள்) question auditor.

Topic/batch: {topic} / {batch}
Relevant SM notes (kurals+meanings) for this topic's adhikarams:
{json.dumps(notes_slice, ensure_ascii=False)[:12000]}

Audit EACH MCQ below. Fail if ANY of:
- Not sensible / nonsense / vague
- Not TNPSC-oriented or below/above typical Group exam level for Thirukkural facts/meaning
- Tamil spelling/grammar broken in stem or options
- Options not exactly 4 usable choices
- Duplicate/near-duplicate options
- correct letter wrong vs notes/explanation
- Answer not among options
- Stem repeats almost same as another in this chunk (mark later ones)

Return JSON only:
{{
  "results": [
    {{
      "i": 0,
      "ok": true,
      "action": "keep|fix|drop",
      "issues": ["tamil","wrong_answer","dup_opts","weak","nonsense","not_tnpsc"],
      "fix_stem": "",
      "fix_options": [],
      "fix_correct": "",
      "fix_explanation": "",
      "note_ta": "short"
    }}
  ]
}}
If action=fix, provide fixed fields. If drop, leave fixes empty.
Be strict but keep good PYQ-style meaning/complete-line questions.
"""
    raw = call_gemini(api_key, prompt + "\nQUESTIONS:\n" + json.dumps(payload_qs, ensure_ascii=False))
    obj = parse_json(raw)
    results = obj.get("results") if isinstance(obj, dict) else obj
    return results if isinstance(results, list) else []


def notes_for_topic(notes, topic_name):
    # topic like "A — B"
    parts = [p.strip() for p in topic_name.split("—")]
    adhs = notes.get("adhikarams") or []
    out = []
    for a in adhs:
        if a.get("name_ta") in parts:
            out.append(
                {
                    "name_ta": a.get("name_ta"),
                    "kurals": a.get("kurals") or [],
                }
            )
    return out


def apply_fix(q, r):
    action = (r.get("action") or ("keep" if r.get("ok") else "drop")).lower()
    if action == "drop":
        return None
    qq = dict(q)
    if action == "fix":
        if (r.get("fix_stem") or "").strip():
            qq["question_ta"] = r["fix_stem"].strip()
            qq["question_en"] = qq["question_ta"]
        fo = r.get("fix_options") or []
        if isinstance(fo, list) and len(fo) >= 4:
            texts = []
            for o in fo[:4]:
                if isinstance(o, dict):
                    texts.append((o.get("text_ta") or o.get("text") or "").strip())
                else:
                    texts.append(str(o).strip())
            if all(texts):
                qq["options"] = [
                    {"key": chr(65 + i), "text_en": texts[i], "text_ta": texts[i]} for i in range(4)
                ]
        fc = str(r.get("fix_correct") or "").strip().upper()[:1]
        if fc in "ABCD":
            qq["correct_option"] = fc
        if (r.get("fix_explanation") or "").strip():
            qq["explanation_ta"] = r["fix_explanation"].strip()
            qq["explanation"] = qq["explanation_ta"]
    # structural sanitize
    texts = opt_texts(qq)
    letter = (qq.get("correct_option") or "").upper()[:1]
    if letter not in "ABCD" or len(texts) < 4 or len(set(re.sub(r"\s+", "", t.lower()) for t in texts[:4])) < 4:
        return None
    qq["double_verified"] = True
    qq["verify_issues"] = r.get("issues") or []
    return qq


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY missing")

    db = load_json(DB_PATH, [])
    notes = load_json(NOTES_PATH, {})
    report = load_json(REPORT_PATH, {"batches": {}, "summary": {}}) if args.resume else {"batches": {}, "summary": {}}

    # group
    groups = defaultdict(list)
    for i, q in enumerate(db):
        groups[(q.get("topic"), q.get("batch"))].append((i, q))

    batch_keys = sorted(groups.keys(), key=lambda x: (x[0] or "", x[1] or ""))
    print(f"Verifying {len(batch_keys)} batches, {len(db)} questions", flush=True)

    cleaned_by_index = {}
    dropped = []
    fixed = []

    for topic, batch in batch_keys:
        bkey = f"{topic}||{batch}"
        items = groups[(topic, batch)]
        if args.resume and report.get("batches", {}).get(bkey, {}).get("status") == "done":
            print(f"SKIP {batch} | {topic[:40]}...", flush=True)
            for rec in report["batches"][bkey].get("actions") or []:
                cleaned_by_index[rec["index"]] = rec["question"]
            for d in report["batches"][bkey].get("dropped_indices") or []:
                dropped.append(d)
            continue

        print(f"\n=== {batch} | {topic} ({len(items)} Q) ===", flush=True)
        notes_slice = notes_for_topic(notes, topic)
        batch_kept = []
        batch_dropped = []
        batch_fixed = 0

        for cstart in range(0, len(items), CHUNK):
            chunk = items[cstart : cstart + CHUNK]
            qs = [q for _, q in chunk]
            idxs = [i for i, _ in chunk]
            try:
                results = verify_chunk(api_key, topic, batch, notes_slice, qs, 0)
            except Exception as e:
                print(f"  chunk fail {e}; keep originals marked unchecked", flush=True)
                for i, q in chunk:
                    qq = dict(q)
                    qq["double_verified"] = False
                    qq["verify_issues"] = ["verify_failed"]
                    cleaned_by_index[i] = qq
                    batch_kept.append({"index": i, "question": qq})
                time.sleep(5)
                continue

            by_local = {}
            for r in results:
                if isinstance(r, dict) and r.get("i") is not None:
                    by_local[int(r["i"])] = r

            for local_i, (global_i, q) in enumerate(chunk):
                r = by_local.get(local_i) or {"ok": True, "action": "keep", "issues": []}
                new_q = apply_fix(q, r)
                if new_q is None:
                    batch_dropped.append(global_i)
                    dropped.append(global_i)
                    print(f"  DROP i={global_i}: {r.get('issues')} {r.get('note_ta','')[:60]}", flush=True)
                else:
                    if (r.get("action") or "").lower() == "fix":
                        batch_fixed += 1
                        fixed.append(global_i)
                    cleaned_by_index[global_i] = new_q
                    batch_kept.append({"index": global_i, "question": new_q})
            time.sleep(6)

        report.setdefault("batches", {})[bkey] = {
            "status": "done",
            "topic": topic,
            "batch": batch,
            "input": len(items),
            "kept_indices": [x["index"] for x in batch_kept],
            "dropped_indices": batch_dropped,
            "fixed": batch_fixed,
            "actions": [
                {
                    "index": x["index"],
                    "issues": x["question"].get("verify_issues") or [],
                    "double_verified": x["question"].get("double_verified"),
                    "question": x["question"],
                }
                for x in batch_kept
            ],
        }
        report["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        save_json(REPORT_PATH, report)
        print(f"  kept={len(batch_kept)} dropped={len(batch_dropped)} fixed={batch_fixed}", flush=True)
        time.sleep(4)

    # Rebuild final DB from cleaned; fill short batches later if needed
    final = []
    for i, q in enumerate(db):
        if i in cleaned_by_index:
            final.append(cleaned_by_index[i])
        elif i not in dropped:
            # shouldn't happen
            final.append(q)

    # Re-number nothing; keep topic/batch. Remove near-dups within topic+batch after verify
    def norm(s):
        return re.sub(r"\s+", "", (s or "").lower())

    from difflib import SequenceMatcher

    by_tb = defaultdict(list)
    for q in final:
        by_tb[(q.get("topic"), q.get("batch"))].append(q)
    deduped = []
    for key, items in by_tb.items():
        acc = []
        for q in items:
            sn = norm(q.get("question_ta"))
            if any(SequenceMatcher(None, sn, norm(a.get("question_ta"))).ratio() >= 0.92 for a in acc):
                dropped.append(-1)
                continue
            acc.append(q)
        deduped.extend(acc)

    save_json(DB_PATH, deduped)
    report["summary"] = {
        "input": len(db),
        "output": len(deduped),
        "dropped": len(db) - len(deduped),
        "fixed_count": len(set(fixed)),
        "per_batch": {f"{t} | {b}": c for (t, b), c in sorted(Counter((q.get("topic"), q.get("batch")) for q in deduped).items())},
    }
    save_json(REPORT_PATH, report)
    print(f"\nDONE output={len(deduped)} dropped≈{len(db)-len(deduped)} report={REPORT_PATH}", flush=True)
    for (t, b), c in sorted(Counter((q.get("topic"), q.get("batch")) for q in deduped).items()):
        print(f"  {b} | {t[:50]}: {c}", flush=True)


if __name__ == "__main__":
    main()
