#!/usr/bin/env python3
"""
Generate TNPSC practice batches for Unit V Reading Comprehension / Unit VI Translation.

Batches: 1–3 × 25 from extract batches_target (or --batches override).
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
RC = BASE / "English" / "ReadingComprehension"
TR = BASE / "English" / "Translation"
MODEL = "gemini-3.5-flash-lite"
TARGET = 25
GENERATE_PER_CALL = 30
LETTER_PREFIX_RE = re.compile(r"^[A-Ea-e][\).\:\-]\s*")

TOPIC_META = {
    "unseen_passages": {
        "extract": RC / "vetri_extract" / "unseen_passages.json",
        "db": RC / "unseen_passages_questions_db.json",
        "topic": "Unseen Passages",
        "unit": "ReadingComprehension",
        "shapes": "Passage-based MCQs: main idea, detail, vocab-in-context, inference. Prefer short passage+Q style. English only.",
    },
    "strong_weak_questions": {
        "extract": RC / "vetri_extract" / "strong_weak_questions.json",
        "db": RC / "strong_weak_questions_questions_db.json",
        "topic": "Strong & Weak Questions",
        "unit": "ReadingComprehension",
        "shapes": "Identify strong vs weak questions; answer inference/tone (strong) vs fact-locate (weak) from short passages.",
    },
    "match_the_following": {
        "extract": RC / "vetri_extract" / "match_the_following.json",
        "db": RC / "match_the_following_questions_db.json",
        "topic": "Match the Following",
        "unit": "ReadingComprehension",
        "shapes": "Match column A–B items from passage/news; choose correct pairing code (e.g. 1-a 2-b).",
    },
    "sentence_completion": {
        "extract": RC / "vetri_extract" / "sentence_completion.json",
        "db": RC / "sentence_completion_questions_db.json",
        "topic": "Sentence Completion",
        "unit": "ReadingComprehension",
        "shapes": "Fill blanks using words/phrases from a short passage; contextually correct completion.",
    },
    "ascertainment_of_facts": {
        "extract": RC / "vetri_extract" / "ascertainment_of_facts.json",
        "db": RC / "ascertainment_of_facts_questions_db.json",
        "topic": "Ascertainment of Facts",
        "unit": "ReadingComprehension",
        "shapes": "Choose the statement that is factually accurate / best response based ONLY on the passage.",
    },
    "word_translation": {
        "extract": TR / "vetri_extract" / "word_translation.json",
        "db": TR / "word_translation_questions_db.json",
        "topic": "Word Translation",
        "unit": "Translation",
        "shapes": "Choose correct Tamil meaning for English word, or English for Tamil. Options may include Tamil script.",
    },
    "sentence_translation": {
        "extract": TR / "vetri_extract" / "sentence_translation.json",
        "db": TR / "sentence_translation_questions_db.json",
        "topic": "Sentence Translation",
        "unit": "Translation",
        "shapes": "Choose correct Tamil translation of English sentence (or reverse). Options may include Tamil.",
    },
    "tense_related_translation": {
        "extract": TR / "vetri_extract" / "tense_related_translation.json",
        "db": TR / "tense_related_translation_questions_db.json",
        "topic": "Tense-related Translation",
        "unit": "Translation",
        "shapes": "Identify tense / choose correct Tamil verb form for English tense sentences; EN↔TA tense pairs.",
    },
    "tense_voice_related": {
        "extract": TR / "vetri_extract" / "tense_voice_related.json",
        "db": TR / "tense_voice_related_questions_db.json",
        "topic": "Tense / Voice-related Tasks",
        "unit": "Translation",
        "shapes": "Active↔Passive with Tamil equivalents; choose correct voice/tense translation.",
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


def ground(extract: dict, topic_id: str) -> str:
    lines = [
        f"TOPIC: {extract.get('topic_title')}",
        f"SUMMARY:\n{(extract.get('notes_en') or '')[:2500]}",
        "\nRULES:",
    ]
    for i, r in enumerate((extract.get("rules") or [])[:40], 1):
        lines.append(f"R{i}: {r.get('rule_en')} [{r.get('tag')}]")
    lines.append("\nGLOSSARY:")
    for i, g in enumerate((extract.get("glossary") or [])[:120], 1):
        ta = g.get("meaning_ta") or ""
        lines.append(f"G{i}: {g.get('term_en')} = {g.get('meaning_en')} | TA:{ta}")
    lines.append("\nPASSAGES:")
    for i, p in enumerate((extract.get("passages") or [])[:12], 1):
        lines.append(f"PASS{i} [{p.get('title')}]: {(p.get('text_en') or '')[:900]}")
    lines.append("\nTRANSLATION PAIRS:")
    for i, t in enumerate((extract.get("translations") or [])[:120], 1):
        lines.append(f"T{i}: EN={(t.get('en') or '')[:160]} || TA={(t.get('ta') or '')[:160]}")
    lines.append("\nEXAMPLES:")
    for i, e in enumerate((extract.get("examples") or [])[:30], 1):
        lines.append(f"E{i}: {e.get('note_en')}")
    lines.append("\nVETRI PYQ (style — REPHRASE, do not copy verbatim):")
    for i, q in enumerate((extract.get("pyq") or [])[:40], 1):
        opts = " | ".join((q.get("options_en") or [])[:4])
        lines.append(
            f"P{i}: {q.get('question_en')} => {q.get('answer_letter') or q.get('answer_en')} :: {opts}"
        )
    return "\n".join(lines)


def call_gemini(prompt: str, api_key: str) -> list:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}"
        f":generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.35},
    }
    delay = 12
    for _ in range(6):
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=210) as resp:
                raw = json.loads(resp.read().decode())["candidates"][0]["content"]["parts"][0][
                    "text"
                ].strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1]
                if raw.endswith("```"):
                    raw = raw.rsplit("\n", 1)[0]
            start = raw.find("[")
            if start >= 0:
                depth = 0
                for i, ch in enumerate(raw[start:], start):
                    if ch == "[":
                        depth += 1
                    elif ch == "]":
                        depth -= 1
                        if depth == 0:
                            raw = raw[start : i + 1]
                            break
            data = json.loads(raw)
            return data if isinstance(data, list) else []
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                time.sleep(delay)
                delay = min(delay * 2, 90)
            else:
                time.sleep(5)
        except Exception:
            time.sleep(5)
    return []


def letter_for(opts, ans):
    ae = clean_option(ans or "")
    for i, o in enumerate(opts):
        if clean_option(o) == ae or clean_option(o).lower() == ae.lower():
            return chr(65 + i)
    if ae.upper()[:1] in "ABCD" and len(ae) <= 2:
        return ae.upper()[:1]
    return None


def normalize(raw, meta, batch_num: int):
    if not isinstance(raw, dict):
        return None
    q_en = raw.get("question_en")
    if isinstance(q_en, list):
        q_en = " ".join(str(x) for x in q_en)
    q_en = (str(q_en) if q_en else "").strip()
    if len(q_en) < 12:
        return None
    opts_raw = raw.get("options_en") or []
    if not isinstance(opts_raw, list):
        return None
    opts = [clean_option(str(x)) for x in opts_raw if str(x).strip()][:4]
    if len(opts) < 4 or len(set(o.lower() for o in opts)) < 4:
        return None
    ans = raw.get("answer_en")
    if isinstance(ans, list):
        ans = " ".join(str(x) for x in ans)
    letter = letter_for(opts, ans)
    if not letter:
        return None
    expl = raw.get("explanation_en")
    if isinstance(expl, list):
        expl = " ".join(str(x) for x in expl)
    expl = (str(expl) if expl else "").strip()
    options = [{"key": chr(65 + i), "text_en": o, "text_ta": o} for i, o in enumerate(opts)]
    options.append({"key": "E", "text_en": "Answer not known", "text_ta": "Answer not known"})
    return {
        "subject": "English",
        "unit": meta["unit"],
        "menu": meta["topic"],
        "topic": meta["topic"],
        "topic_id": meta["topic"].lower().replace(" ", "_").replace("&", "and").replace("/", "_").replace(",", ""),
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
        "batch": f"Batch {batch_num}",
        "group": meta["topic"],
        "source_note": str(raw.get("source_note") or "Vetri Unit V/VI").strip(),
    }


def shuffle_balance(rows, seed: str):
    rng = random.Random(seed)
    cycle = list("ABCD") * ((len(rows) // 4) + 2)
    rng.shuffle(cycle)
    out = []
    for i, q in enumerate(rows):
        abcd = [o for o in q["options"] if o["key"] in "ABCD"]
        e = [o for o in q["options"] if o["key"] == "E"]
        if len(abcd) != 4:
            out.append(q)
            continue
        ci = ord(q["correct_option"]) - 65
        correct = abcd[ci]["text_en"]
        others = [abcd[j]["text_en"] for j in range(4) if j != ci]
        rng.shuffle(others)
        desired = cycle[i % len(cycle)]
        di = ord(desired) - 65
        texts = [None] * 4
        texts[di] = correct
        oi = 0
        for j in range(4):
            if texts[j] is None:
                texts[j] = others[oi]
                oi += 1
        nq = dict(q)
        nq["options"] = [
            {"key": chr(65 + j), "text_en": texts[j], "text_ta": texts[j]} for j in range(4)
        ] + (
            e or [{"key": "E", "text_en": "Answer not known", "text_ta": "Answer not known"}]
        )
        nq["correct_option"] = desired
        out.append(nq)
    return out


def generate_batch(topic_id: str, batch_num: int, n_batches: int, api_key: str, exclusion: list) -> list:
    meta = TOPIC_META[topic_id]
    extract = load_json(meta["extract"])
    g = ground(extract, topic_id)
    focus = f"Batch {batch_num}/{n_batches} — diversify; avoid repeating earlier batch facts."
    excl = "\n".join(f"- {t}" for t in exclusion[-100:]) if exclusion else ""
    allow_ta = "Translation" in meta["unit"]
    lang_rule = (
        "Tamil script ALLOWED in options (and short stems when asking EN→TA)."
        if allow_ta
        else "English ONLY in stems and options (no Tamil)."
    )
    prompt = f"""
Senior TNPSC General English compiler for "{meta['topic']}".
Generate exactly {GENERATE_PER_CALL} MCQs.
{focus}
Shapes: {meta['shapes']}
Hard rules:
1. Answers grounded in NOTES/PASSAGES/TRANSLATIONS/GLOSSARY/PYQ facts below.
2. Exactly 4 options; NO "A." prefixes inside option text.
3. answer_en must match one option exactly.
4. REPHRASE Vetri PYQ — do not copy stems verbatim.
5. {lang_rule}
6. One clear correct answer; balanced difficulty.
EXCLUDED stems:
{excl}

GROUND:
{g[:15000]}

Return ONLY JSON array:
[{{"question_en":"...","options_en":["..","..","..",".."],"answer_en":"...","explanation_en":"...","source_note":"..."}}]
"""
    raw = call_gemini(prompt, api_key)
    rows, seen = [], set()
    for r in raw:
        item = normalize(r, meta, batch_num)
        if not item:
            continue
        stem = re.sub(r"\s+", " ", item["question_en"].lower())
        if stem in seen or any(stem == re.sub(r"\s+", " ", x.lower()) for x in exclusion):
            continue
        if any(
            stem == re.sub(r"\s+", " ", (pq.get("question_en") or "").lower())
            for pq in (extract.get("pyq") or [])
        ):
            continue
        seen.add(stem)
        rows.append(item)
        if len(rows) >= TARGET:
            break
    return shuffle_balance(rows[:TARGET], seed=f"{topic_id}-{batch_num}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True, choices=list(TOPIC_META.keys()))
    parser.add_argument("--batches", type=int, default=0)
    args = parser.parse_args()

    api = os.environ.get("GEMINI_API_KEY")
    if not api:
        raise SystemExit("GEMINI_API_KEY missing")

    meta = TOPIC_META[args.topic]
    extract = load_json(meta["extract"])
    if not extract:
        raise SystemExit(f"Missing extract: {meta['extract']} — run extract_vetri_unit56.py first")

    n = args.batches or int(extract.get("batches_target") or 2)
    n = max(1, min(3, n))
    print(f"=== {meta['topic']} → {n} batches × {TARGET} ===")

    all_rows = []
    exclusion = []
    for b in range(1, n + 1):
        print(f"  Batch {b}...")
        rows = []
        for attempt in range(4):
            chunk = generate_batch(args.topic, b, n, api, exclusion)
            for r in chunk:
                stem = re.sub(r"\s+", " ", r["question_en"].lower())
                if any(stem == re.sub(r"\s+", " ", x["question_en"].lower()) for x in rows):
                    continue
                rows.append(r)
                exclusion.append(r["question_en"])
                if len(rows) >= TARGET:
                    break
            print(f"    attempt {attempt+1}: got {len(rows)}")
            if len(rows) >= TARGET:
                break
            time.sleep(1.5)
        rows = rows[:TARGET]
        dist = Counter(r["correct_option"] for r in rows)
        print(f"    wrote {len(rows)} dist={dict(sorted(dist.items()))}")
        all_rows.extend(rows)
        time.sleep(1)

    save_json(meta["db"], all_rows)
    print(f"Saved {len(all_rows)} → {meta['db']}")


if __name__ == "__main__":
    main()
