#!/usr/bin/env python3
"""
Generate 25 PYQ-style practice MCQs per prose lesson (Unit VII).

TNPSC quality rules (same bar as poem v2):
- No UI giveaways (don't ask lesson TITLE; quiz header already shows it)
- At most ONE author meta question
- Balanced correct letters A–D via option shuffle
- No letter prefixes inside option text
- Diversified: plot / character / quote / vocab / theme — not one fact repeated
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

BASE_DIR = Path(__file__).resolve().parents[2]
PROSE_DIR = BASE_DIR / "English" / "Prose"
NOTES_DIR = PROSE_DIR / "notes"
PYQ_DIR = PROSE_DIR / "pyq"
Q_DIR = PROSE_DIR / "questions"
INDEX_PATH = PROSE_DIR / "prose_index.json"
COMBINED_PATH = PROSE_DIR / "prose_questions_db.json"

MODEL = "gemini-3.5-flash-lite"
TARGET = 25
GENERATE_PER_CALL = 32

LETTER_PREFIX_RE = re.compile(r"^[A-Ea-e][\).\:\-]\s*")
TITLE_GIVEAWAY_RE = re.compile(
    r"(title of the (prose|lesson|story|passage)|what is the (name|title) of (this|the) (prose|lesson|story)|"
    r"(prose|lesson|story) is (called|named)|title of the (prose|lesson) written by)",
    re.I,
)
AUTHOR_META_RE = re.compile(
    r"(who (is|was) the (author|writer)|author of the (prose|lesson|story)|written by|"
    r"the (prose|lesson|story) .+ is written by)",
    re.I,
)

SHAPES = """Target mix across the 25 questions (approximate):
- 7–9 plot / incident / who-did-what / sequence
- 4–6 character / relationship / motivation
- 3–5 vocabulary / glossary in context
- 3–4 theme / message / moral / tone
- 2–3 quote / complete-the-line / significant dialogue
- AT MOST 1 author question (optional). Prefer author linked to a UNIQUE plot cue — NEVER ask for the lesson TITLE.
FORBIDDEN:
- Asking for the prose/lesson TITLE (quiz header already shows it)
- "What is the title of the story written by …"
- Option text starting with "A." / "B." / "C." / "D."
- Meta stems like "Based on textbook worked exercises"
- Invented facts not in the notes/text/PYQ bank
"""


def load_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default if default is not None else {}
    return json.loads(p.read_text(encoding="utf-8"))


def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clean_option_text(text: str) -> str:
    t = (text or "").strip()
    for _ in range(3):
        newt = LETTER_PREFIX_RE.sub("", t).strip()
        if newt == t:
            break
        t = newt
    return t


def ground_text(notes: dict, pyq: dict) -> str:
    lines = [
        f"PROSE: {notes.get('prose_title')} — {notes.get('author')}",
        f"SUMMARY: {notes.get('summary_en') or ''}",
        "\nPROSE EXCERPTS:",
        (notes.get("prose_text_en") or "")[:2800],
        "\nCHARACTERS:",
    ]
    for i, c in enumerate((notes.get("characters") or [])[:20], 1):
        lines.append(f"C{i}: {c.get('name_en')} — {c.get('role_en')}")
    lines.append("\nRULES/FACTS:")
    for i, r in enumerate((notes.get("rules") or [])[:25], 1):
        lines.append(f"R{i}: {r.get('rule_en')} [{r.get('tag')}]")
    lines.append("\nGLOSSARY:")
    for i, g in enumerate((notes.get("glossary") or [])[:30], 1):
        lines.append(f"G{i}: {g.get('word_en')} = {g.get('meaning_en')}")
    lines.append("\nTEXTBOOK WORKED:")
    for i, w in enumerate((notes.get("worked_exercises") or [])[:25], 1):
        lines.append(f"W{i}: {w.get('prompt_en')} ⇒ {w.get('answer_en')}")
    lines.append("\nSTORED PYQ (style reference — rephrase, do not copy):")
    for i, q in enumerate((pyq.get("questions") or [])[:40], 1):
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
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=210) as resp:
                raw = json.loads(resp.read().decode("utf-8"))["candidates"][0]["content"]["parts"][0][
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


def letter_for_answer(options_en, answer_en):
    ae = clean_option_text(answer_en or "")
    for i, opt in enumerate(options_en):
        if clean_option_text(opt) == ae:
            return chr(65 + i)
    ae_l = ae.lower()
    for i, opt in enumerate(options_en):
        if clean_option_text(opt).lower() == ae_l:
            return chr(65 + i)
    if ae.upper()[:1] in "ABCD" and len(ae) <= 2:
        return ae.upper()[:1]
    return None


def is_forbidden_stem(stem: str) -> bool:
    if TITLE_GIVEAWAY_RE.search(stem):
        return True
    if re.search(r"\btitle\b", stem, re.I) and re.search(
        r"\b(prose|lesson|story|passage)\b", stem, re.I
    ):
        return True
    if re.search(r"based on textbook|worked exercises", stem, re.I):
        return True
    return False


def as_text(val) -> str:
    if isinstance(val, list):
        return " ".join(str(x) for x in val if x)
    return str(val) if val is not None else ""


def normalize_item(raw, item: dict):
    if not isinstance(raw, dict):
        return None
    q_en = as_text(raw.get("question_en")).strip()
    if not q_en or is_forbidden_stem(q_en):
        return None
    opts_raw = raw.get("options_en") or []
    if not isinstance(opts_raw, list):
        return None
    opts = [clean_option_text(str(x)) for x in opts_raw if str(x).strip()][:4]
    opts = [o for o in opts if o]
    if len(opts) < 4 or len(set(o.lower() for o in opts)) < 4:
        return None
    letter = letter_for_answer(opts, as_text(raw.get("answer_en")))
    if not letter:
        return None
    explanation = as_text(raw.get("explanation_en")).strip()
    options = [{"key": chr(65 + i), "text_en": o, "text_ta": o} for i, o in enumerate(opts)]
    options.append({"key": "E", "text_en": "Answer not known", "text_ta": "Answer not known"})
    return {
        "subject": "English",
        "unit": "Prose",
        "menu": item["title"],
        "topic": item["title"],
        "topic_id": item["id"],
        "topic_ta": item["title"],
        "source_exam": "Practice Batch 1",
        "difficulty": "Medium",
        "question_en": q_en,
        "question_ta": q_en,
        "options": options,
        "correct_option": letter,
        "explanation": explanation,
        "explanation_ta": explanation,
        "type": "practice",
        "batch": "Batch 1",
        "group": item["id"],
        "source_note": as_text(raw.get("source_note")).strip(),
        "_is_author_meta": bool(AUTHOR_META_RE.search(q_en)),
    }


def shuffle_balance(rows: list, seed: str) -> list:
    rng = random.Random(seed)
    target_cycle = list("ABCD") * ((len(rows) // 4) + 2)
    rng.shuffle(target_cycle)
    balanced = []
    for i, q in enumerate(rows):
        abcd = [o for o in (q.get("options") or []) if o.get("key") in "ABCD"]
        e_opts = [o for o in (q.get("options") or []) if o.get("key") == "E"]
        if len(abcd) != 4:
            balanced.append(q)
            continue
        correct_letter = (q.get("correct_option") or "A").strip().upper()[:1]
        correct_idx = ord(correct_letter) - 65 if correct_letter in "ABCD" else 0
        correct_text = abcd[correct_idx].get("text_en")
        texts = [o.get("text_en") for o in abcd]
        desired = target_cycle[i % len(target_cycle)]
        desired_idx = ord(desired) - 65
        others = [t for j, t in enumerate(texts) if j != correct_idx]
        rng.shuffle(others)
        new_texts = [None] * 4
        new_texts[desired_idx] = correct_text
        oi = 0
        for j in range(4):
            if new_texts[j] is None:
                new_texts[j] = others[oi]
                oi += 1
        new_opts = [
            {"key": chr(65 + j), "text_en": new_texts[j], "text_ta": new_texts[j]} for j in range(4)
        ]
        new_opts.extend(
            e_opts
            or [{"key": "E", "text_en": "Answer not known", "text_ta": "Answer not known"}]
        )
        nq = dict(q)
        nq["options"] = new_opts
        nq["correct_option"] = desired
        nq.pop("_is_author_meta", None)
        balanced.append(nq)
    return balanced


def generate_for_item(item: dict, api_key: str) -> list:
    notes = load_json(NOTES_DIR / f"{item['id']}.json")
    pyq = load_json(PYQ_DIR / f"{item['id']}.json", {"questions": []})
    if not notes.get("prose_title") and not notes.get("prose_text_en"):
        print(f"  SKIP no notes for {item['id']}")
        return []
    ground = ground_text(notes, pyq)
    exclusion = []
    rows = []
    seen = set()
    author_count = 0
    for round_i in range(5):
        if len(rows) >= TARGET + 4:
            break
        excl = (
            "\nEXCLUDED (do not repeat):\n" + "\n".join(f"- {t}" for t in exclusion[:90])
            if exclusion
            else ""
        )
        prompt = f"""
Senior TNPSC General English (Unit VII — Prose) question compiler.
Lesson under test: "{item['title']}" by {item.get('author') or 'the author'}.
Student quiz screen ALREADY shows header "{item['title']}" — never ask for the lesson title.

Generate exactly {GENERATE_PER_CALL} high-quality practice MCQs for THIS prose ONLY.
Think like a TNPSC Group exams setter: clear stem, one unambiguous answer, plausible distractors.
{excl}

GROUND TRUTH + PYQ STYLE BANK:
{ground[:14500]}

{SHAPES}

Hard rules:
1. Every answer must be supported by prose notes / text / glossary / worked / PYQ facts.
2. English ONLY for all fields (question_ta = question_en, etc.).
3. Exactly 4 options in options_en; plain text only (NO "A."/"B." prefixes inside options).
4. answer_en must exactly match one of options_en.
5. Match TNPSC Prose PYQ style from the bank — REPHRASE stems, never copy verbatim.
6. Diversify facts; do not repeat the same incident more than twice.

Return ONLY a JSON array of objects:
question_en, question_ta, options_en[4], options_ta[4], answer_en, answer_ta,
explanation_en, explanation_ta, source_note
"""
        raw_list = call_gemini(prompt, api_key)
        print(f"  round {round_i+1}: raw={len(raw_list)} kept={len(rows)}")
        for raw in raw_list:
            row = normalize_item(raw, item)
            if not row:
                continue
            stem = re.sub(r"\s+", " ", row["question_en"].lower())
            if stem in seen:
                continue
            if any(
                stem == re.sub(r"\s+", " ", (pq.get("question_en") or "").lower())
                for pq in (pyq.get("questions") or [])
            ):
                continue
            if row.pop("_is_author_meta", False):
                if author_count >= 1:
                    continue
                author_count += 1
            seen.add(stem)
            rows.append(row)
            exclusion.append(row["question_en"])
            if len(rows) >= TARGET + 4:
                break
        time.sleep(1.5)

    rows = shuffle_balance(rows[:TARGET], seed=item["id"])
    dist = Counter(q["correct_option"] for q in rows)
    print(f"  answer_dist={dict(sorted(dist.items()))} author_meta={author_count}")
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prose", type=str)
    parser.add_argument("--phase1", action="store_true", default=True)
    parser.add_argument("--with-pyq-only", action="store_true")
    parser.add_argument("--all-prose", action="store_true")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY not set")

    index = load_json(INDEX_PATH)
    items = index["prose"]
    if args.prose:
        key = args.prose.strip()
        items = [p for p in items if p["id"] == key or str(p["num"]) == key]
        if not items:
            raise SystemExit(f"prose not found: {key}")
    elif args.all_prose:
        pass
    elif args.with_pyq_only:
        have = {p.stem for p in PYQ_DIR.glob("*.json")}
        items = [p for p in items if p["id"] in have]
    elif args.phase1:
        items = [p for p in items if p.get("num", 0) <= 14]

    Q_DIR.mkdir(parents=True, exist_ok=True)
    for item in items:
        print(f"\n=== Generate {item['num']}. {item['title']} ===")
        rows = generate_for_item(item, api_key)
        save_json(Q_DIR / f"{item['id']}_questions_db.json", rows)
        print(f"  wrote {len(rows)} Q")

    combined = []
    for f in sorted(Q_DIR.glob("*_questions_db.json")):
        combined.extend(load_json(f, []))
    save_json(COMBINED_PATH, combined)
    print(f"\nCombined total: {len(combined)} → {COMBINED_PATH}")


if __name__ == "__main__":
    main()
