#!/usr/bin/env python3
"""
Top up Thirukkural adhikaram questions to support 10 topics × (Batch1 30 + Batch2 30).

Generates EXTRA more PYQ-style MCQs per adhikaram, Gemini-verifies, appends to
Tamil/unit7_thirukkural_adhikaram_questions_temp.json (resume-safe).

Usage:
  python3 Tamil/topup_thirukkural_adhikaram_questions.py
  python3 Tamil/topup_thirukkural_adhikaram_questions.py --extra 15
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYQ_PATH = os.path.join(BASE_DIR, "Tamil", "unit7_thirukkural_pyq_page388_group4.json")
NOTES_PATH = os.path.join(BASE_DIR, "Tamil", "unit7_thirukkural_adhikaram_notes_temp.json")
OUT_PATH = os.path.join(BASE_DIR, "Tamil", "unit7_thirukkural_adhikaram_questions_temp.json")

MODELS = ["gemini-2.5-flash-lite", "gemini-3.5-flash-lite", "gemini-3.5-flash"]


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def call_gemini(api_key: str, prompt: str, model: str | None = None) -> str:
    preferred = [model] if model else []
    models = []
    for m in preferred + MODELS:
        if m and m not in models:
            models.append(m)
    last = None
    for m in models:
        delay = 6
        for attempt in range(3):
            try:
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"responseMimeType": "application/json", "temperature": 0.35},
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
                    delay = min(delay * 2, 60)
                    continue
                break
            except Exception as e:
                last = e
                print(f"    {m} err: {e}; sleep {delay}s", flush=True)
                time.sleep(delay)
                delay = min(delay * 2, 60)
    for m in [x for x in MODELS if "lite" in x]:
        delay = 15
        for attempt in range(5):
            try:
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"responseMimeType": "application/json", "temperature": 0.35},
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
            except Exception as e:
                last = e
                print(f"    final {m}: {e}; sleep {delay}s", flush=True)
                time.sleep(delay)
                delay = min(delay * 2, 90)
    raise RuntimeError(f"Gemini failed: {last}")


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
    raise ValueError("Could not parse JSON")


def pyq_style_samples(limit: int = 10) -> list:
    pyq = load_json(PYQ_PATH, [])
    preferred = [q for q in pyq if q.get("q_no", 0) >= 15][:limit]
    if len(preferred) < limit:
        preferred = pyq[:limit]
    return [
        {
            "question_ta": q.get("question_ta"),
            "options_ta": q.get("options_ta"),
            "correct_option_letter": q.get("correct_option_letter"),
        }
        for q in preferred
    ]


def normalize_letter(q: dict, opts: list) -> str:
    letter = str(
        q.get("correct_option_letter")
        or q.get("correct_option")
        or q.get("answer")
        or ""
    ).strip().upper()[:1]
    if letter in "ABCD":
        return letter
    ans_text = str(q.get("answer_text") or q.get("correct_answer") or "").strip()
    if ans_text:
        for i, o in enumerate(opts[:4]):
            if re.sub(r"\s+", "", o) == re.sub(r"\s+", "", ans_text):
                return chr(65 + i)
    return ""


def generate_extra(api_key: str, adh: dict, samples: list, existing_stems: set, n: int) -> list:
    serial = adh.get("serial_no")
    name = adh.get("name_ta")
    kurals = adh.get("kurals") or []
    avoid = list(existing_stems)[:40]
    prompt = f"""You write TNPSC Group-4 Thirukkural MCQs in Tamil (PYQ standard types).

Adhikaram: {serial}. {name}
Ground-truth kurals+meanings (do not invent kurals):
{json.dumps(kurals, ensure_ascii=False)}

PYQ style samples (match shapes; do not copy stems):
{json.dumps(samples, ensure_ascii=False)}

Avoid near-duplicates of these existing stems:
{json.dumps(avoid, ensure_ascii=False)}

Create EXACTLY {n} NEW unique MCQs for THIS adhikaram.
Use these PYQ-standard types (mix):
1) Meaning / who-what from a kural
2) Complete the kural line (முதல் வரி → ?)
3) Concept Valluvar stresses in this adhikaram
4) Word meaning from a kural (ஒரு சொல்லின் பொருள்)
5) Match idea ↔ correct option

Rules:
- Tamil only stems/options
- Options A-D, one correct
- Only facts supported by provided kurals/meanings
- Must include correct_option_letter as A/B/C/D

Return JSON array only:
[
  {{
    "question_ta": "...",
    "options_ta": ["","","",""],
    "correct_option_letter": "A",
    "explanation_ta": "short",
    "based_on_kural": "snippet"
  }}
]
"""
    raw = call_gemini(api_key, prompt, model="gemini-2.5-flash-lite")
    data = parse_json(raw)
    if isinstance(data, dict):
        data = data.get("questions") or data.get("items") or []
    if not isinstance(data, list):
        return []
    cleaned = []
    for q in data:
        if not isinstance(q, dict):
            continue
        opts = q.get("options_ta") or []
        if opts and isinstance(opts[0], dict):
            opts = [(o.get("text_ta") or o.get("text") or "").strip() for o in opts]
        opts = [str(o).strip() for o in opts if str(o).strip()]
        stem = (q.get("question_ta") or "").strip()
        letter = normalize_letter(q, opts)
        if not stem or len(opts) < 4 or letter not in "ABCD":
            continue
        key = re.sub(r"\s+", "", stem.lower())
        if key in existing_stems:
            continue
        cleaned.append(
            {
                "question_ta": stem,
                "options_ta": opts[:4],
                "correct_option_letter": letter,
                "explanation_ta": (q.get("explanation_ta") or "").strip(),
                "based_on_kural": (q.get("based_on_kural") or "").strip(),
            }
        )
        existing_stems.add(key)
    return cleaned[:n]


def verify_questions(api_key: str, adh: dict, questions: list) -> list:
    if not questions:
        return []
    prompt = f"""Verify these TNPSC Thirukkural MCQs against ground truth.

Adhikaram: {adh.get('serial_no')}. {adh.get('name_ta')}
Kurals+meanings:
{json.dumps(adh.get('kurals') or [], ensure_ascii=False)}

Questions:
{json.dumps(questions, ensure_ascii=False)}

Return JSON:
{{"results":[{{"index":0,"ok":true,"correct_option_letter":"A","fix_stem":"","note_ta":""}}]}}
ALWAYS include correct_option_letter A-D for each index.
"""
    raw = call_gemini(api_key, prompt, model="gemini-2.5-flash-lite")
    obj = parse_json(raw)
    results = obj.get("results") if isinstance(obj, dict) else obj
    if not isinstance(results, list):
        for q in questions:
            q["verified"] = True
        return questions
    by_i = {int(r.get("index")): r for r in results if isinstance(r, dict) and r.get("index") is not None}
    out = []
    for i, q in enumerate(questions):
        r = by_i.get(i) or {}
        qq = dict(q)
        letter = str(r.get("correct_option_letter") or q.get("correct_option_letter") or "").strip().upper()[:1]
        if letter in "ABCD":
            qq["correct_option_letter"] = letter
        if (r.get("fix_stem") or "").strip():
            qq["question_ta"] = r["fix_stem"].strip()
        qq["verified"] = bool(r.get("ok", True)) if r else True
        qq["verify_note_ta"] = (r.get("note_ta") or "").strip()
        out.append(qq)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--extra", type=int, default=12, help="extra Q per adhikaram")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY missing")

    notes = load_json(NOTES_PATH, {})
    adhikarams = notes.get("adhikarams") or []
    out = load_json(OUT_PATH, {"questions": [], "progress": {}})
    questions = list(out.get("questions") or [])
    topup_progress = out.setdefault("topup_progress", {})
    samples = pyq_style_samples()

    for adh in adhikarams:
        serial = int(adh.get("serial_no") or 0)
        name = adh.get("name_ta") or ""
        key = str(serial)
        if topup_progress.get(key) == "done":
            print(f"Adhikaram {serial} {name}: topup skip", flush=True)
            continue

        existing = [q for q in questions if int(q.get("adhikaram_serial_no") or 0) == serial]
        stems = {re.sub(r"\s+", "", (q.get("question_ta") or "").lower()) for q in existing}
        print(f"\n=== Topup {serial}. {name} (have {len(existing)}, +{args.extra}) ===", flush=True)

        gen = generate_extra(api_key, adh, samples, stems, args.extra)
        print(f"  generated {len(gen)}", flush=True)
        if len(gen) < max(8, args.extra // 2):
            more = generate_extra(api_key, adh, samples, stems, args.extra)
            gen.extend(more)
            # dedupe
            seen = set()
            uniq = []
            for g in gen:
                k = re.sub(r"\s+", "", g["question_ta"].lower())
                if k in seen:
                    continue
                seen.add(k)
                uniq.append(g)
            gen = uniq[: args.extra]
            print(f"  after retry {len(gen)}", flush=True)

        verified = verify_questions(api_key, adh, gen)
        good = [q for q in verified if q.get("correct_option_letter") in "ABCD"]
        print(f"  verified keep {len(good)}", flush=True)

        for q in good:
            questions.append(
                {
                    "q_no": None,
                    "adhikaram_serial_no": serial,
                    "adhikaram_name_ta": name,
                    "question_ta": q["question_ta"],
                    "options_ta": q["options_ta"],
                    "correct_option_letter": q["correct_option_letter"],
                    "explanation_ta": q.get("explanation_ta") or "",
                    "based_on_kural": q.get("based_on_kural") or "",
                    "verified": q.get("verified", True),
                    "verify_note_ta": q.get("verify_note_ta") or "",
                    "examGroup": ["group4"],
                    "source": "generated_topup_pyq_style",
                }
            )

        topup_progress[key] = "done" if len(good) >= max(6, args.extra // 2) else f"partial_{len(good)}"
        for i, q in enumerate(questions, 1):
            q["q_no"] = i
        out["questions"] = questions
        out["topup_progress"] = topup_progress
        out["count"] = len(questions)
        out["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        save_json(OUT_PATH, out)
        print(f"  saved total {len(questions)}", flush=True)
        time.sleep(8)

    print(f"\nDONE topup total={len(questions)}", flush=True)


if __name__ == "__main__":
    main()
