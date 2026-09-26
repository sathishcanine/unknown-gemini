#!/usr/bin/env python3
"""
Generate 25 PYQ-style practice MCQs per poem (Unit VII).

Quality rules (v2 — post Dream-of-Spices audit):
- No UI giveaways (don't ask poem TITLE; student is already in that poem quiz)
- At most ONE author/poet meta question
- Balanced correct letters A–D via option shuffle
- No "A. …" letter prefixes inside option text
- Diversified shapes: lines / FoS / vocab / theme / characters — not one fact repeated
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
POEMS_DIR = BASE_DIR / "English" / "Poems"
NOTES_DIR = POEMS_DIR / "notes"
PYQ_DIR = POEMS_DIR / "pyq"
Q_DIR = POEMS_DIR / "questions"
INDEX_PATH = POEMS_DIR / "poems_index.json"
COMBINED_PATH = POEMS_DIR / "poems_questions_db.json"

MODEL = "gemini-3.5-flash-lite"
TARGET = 25
GENERATE_PER_CALL = 32

LETTER_PREFIX_RE = re.compile(r"^[A-Ea-e][\).\:\-]\s*")
TITLE_GIVEAWAY_RE = re.compile(
    r"(title of the poem|poem('?s)? title|what is the (name|title) of (this|the) poem|"
    r"the poem (is )?(called|named)|name of the poem)",
    re.I,
)
AUTHOR_META_RE = re.compile(
    r"(who (is|was) the (author|poet)|poet of the poem|written by|author of the poem|"
    r"the poem .+ is written by)",
    re.I,
)

SHAPES = """Target mix across the 25 questions (approximate):
- 6–8 line meaning / implication / complete-the-line / who-said / character action
- 3–5 figures of speech / alliteration / rhyme (ONLY if supported by notes)
- 4–6 glossary / vocabulary in context
- 3–4 theme / message / tone
- 2–4 detail recall (lists, places, objects) — do NOT repeat the same grocery/item fact
- AT MOST 1 author/poet question (optional). Prefer: "Who wrote the poem that begins with …" using a UNIQUE opening line — NEVER "title of the poem" and NEVER "title written by X".
FORBIDDEN:
- Asking for the poem TITLE (quiz header already shows it)
- "What is the title of the poem written by …"
- Option text starting with "A." / "B." / "C." / "D."
- Meta stems like "Based on textbook worked exercises"
- Invented facts not in the notes/text
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
    # strip repeated letter prefixes: "A. A. Three" → "Three"
    for _ in range(3):
        newt = LETTER_PREFIX_RE.sub("", t).strip()
        if newt == t:
            break
        t = newt
    return t


def ground_text(notes: dict, pyq: dict) -> str:
    lines = [
        f"POEM: {notes.get('poem_title')} — {notes.get('author')}",
        f"SUMMARY: {notes.get('summary_en') or ''}",
        "\nPOEM TEXT:",
        (notes.get("poem_text_en") or "")[:2500],
        "\nRULES/FACTS:",
    ]
    for i, r in enumerate((notes.get("rules") or [])[:25], 1):
        lines.append(f"R{i}: {r.get('rule_en')} [{r.get('tag')}]")
    lines.append("\nFIGURES OF SPEECH:")
    for i, f in enumerate((notes.get("figures_of_speech") or [])[:20], 1):
        lines.append(
            f"F{i}: {f.get('device_en')} — {f.get('example_en')} ({f.get('note_en') or ''})"
        )
    lines.append("\nGLOSSARY:")
    for i, g in enumerate((notes.get("glossary") or [])[:30], 1):
        lines.append(f"G{i}: {g.get('word_en')} = {g.get('meaning_en')}")
    lines.append("\nTEXTBOOK WORKED:")
    for i, w in enumerate((notes.get("worked_exercises") or [])[:20], 1):
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


def is_forbidden_stem(stem: str, poem_title: str) -> bool:
    if TITLE_GIVEAWAY_RE.search(stem):
        return True
    # "What is the title..." variants
    if re.search(r"\btitle\b", stem, re.I) and re.search(r"\bpoem\b", stem, re.I):
        return True
    # asking title when options would be poem names and stem mentions author only
    if re.search(r"title of the poem written by", stem, re.I):
        return True
    if re.search(r"based on textbook|worked exercises", stem, re.I):
        return True
    return False


def normalize_item(raw, poem: dict):
    if not isinstance(raw, dict):
        return None
    q_raw = raw.get("question_en")
    if isinstance(q_raw, list):
        q_raw = " ".join(str(x) for x in q_raw if x)
    q_en = (str(q_raw) if q_raw is not None else "").strip()
    if not q_en:
        return None
    if is_forbidden_stem(q_en, poem["title"]):
        return None
    opts_raw = raw.get("options_en") or []
    if not isinstance(opts_raw, list):
        return None
    opts = [clean_option_text(str(x)) for x in opts_raw if str(x).strip()][:4]
    opts = [o for o in opts if o]
    if len(opts) < 4:
        return None
    if len(set(o.lower() for o in opts)) < 4:
        return None
    # reject if any option still looks like "A. something" after clean failed oddly
    if any(LETTER_PREFIX_RE.match(o) for o in opts):
        opts = [clean_option_text(o) for o in opts]
    ans = raw.get("answer_en")
    if isinstance(ans, list):
        ans = " ".join(str(x) for x in ans if x)
    letter = letter_for_answer(opts, ans)
    if not letter:
        return None
    expl = raw.get("explanation_en")
    if isinstance(expl, list):
        expl = " ".join(str(x) for x in expl if x)
    explanation = (str(expl) if expl is not None else "").strip()
    options = [{"key": chr(65 + i), "text_en": o, "text_ta": o} for i, o in enumerate(opts)]
    options.append({"key": "E", "text_en": "Answer not known", "text_ta": "Answer not known"})
    return {
        "subject": "English",
        "unit": "Poems",
        "menu": poem["title"],
        "topic": poem["title"],
        "topic_id": poem["id"],
        "topic_ta": poem["title"],
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
        "group": poem["id"],
        "source_note": str(raw.get("source_note") or "").strip()
        if not isinstance(raw.get("source_note"), list)
        else " ".join(str(x) for x in raw.get("source_note") if x).strip(),
        "_is_author_meta": bool(AUTHOR_META_RE.search(q_en)),
    }


def shuffle_balance(rows: list, seed: str) -> list:
    """Permute option order so correct letters are roughly balanced A–D."""
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
        # pick desired letter for this slot
        desired = target_cycle[i % len(target_cycle)]
        desired_idx = ord(desired) - 65
        # rearrange: put correct at desired_idx, shuffle others into remaining
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
        new_opts.extend(e_opts or [{"key": "E", "text_en": "Answer not known", "text_ta": "Answer not known"}])
        nq = dict(q)
        nq["options"] = new_opts
        nq["correct_option"] = desired
        nq.pop("_is_author_meta", None)
        balanced.append(nq)
    return balanced


def generate_for_poem(poem: dict, api_key: str) -> list:
    notes = load_json(NOTES_DIR / f"{poem['id']}.json")
    pyq = load_json(PYQ_DIR / f"{poem['id']}.json", {"questions": []})
    if not notes.get("poem_title") and not notes.get("poem_text_en"):
        print(f"  SKIP no notes for {poem['id']}")
        return []
    ground = ground_text(notes, pyq)
    exclusion = []
    rows = []
    seen = set()
    author_count = 0
    for round_i in range(5):
        if len(rows) >= TARGET + 4:  # over-generate then trim
            break
        excl = (
            "\nEXCLUDED (do not repeat):\n" + "\n".join(f"- {t}" for t in exclusion[:90])
            if exclusion
            else ""
        )
        prompt = f"""
Senior TNPSC General English (Unit VII — Poems) question compiler.
Poem under test: "{poem['title']}" by {poem['author']}.
Student quiz screen ALREADY shows header "{poem['title']}" — never ask for the poem title.

Generate exactly {GENERATE_PER_CALL} high-quality practice MCQs for THIS poem only.
{excl}

GROUND TRUTH:
{ground[:14000]}

{SHAPES}

Hard rules:
1. Every answer must be supported by poem text / glossary / FoS / worked notes.
2. English ONLY for all fields (question_ta = question_en, etc.).
3. Exactly 4 options in options_en; plain text only (NO "A."/"B." prefixes inside options).
4. answer_en must exactly match one of options_en.
5. Prefer TNPSC PYQ shapes from the style bank — REPHRASE, never copy stems verbatim.
6. Diversify: avoid asking the same grocery/item/list fact more than twice.
7. Include FoS/alliteration/rhyme ONLY when notes support them.

Return ONLY a JSON array of objects:
question_en, question_ta, options_en[4], options_ta[4], answer_en, answer_ta,
explanation_en, explanation_ta, source_note
"""
        raw_list = call_gemini(prompt, api_key)
        print(f"  round {round_i+1}: raw={len(raw_list)} kept={len(rows)}")
        for raw in raw_list:
            item = normalize_item(raw, poem)
            if not item:
                continue
            stem = re.sub(r"\s+", " ", item["question_en"].lower())
            if stem in seen:
                continue
            if any(
                stem == re.sub(r"\s+", " ", (pq.get("question_en") or "").lower())
                for pq in (pyq.get("questions") or [])
            ):
                continue
            if item.pop("_is_author_meta", False):
                if author_count >= 1:
                    continue
                author_count += 1
            seen.add(stem)
            rows.append(item)
            exclusion.append(item["question_en"])
            if len(rows) >= TARGET + 4:
                break
        time.sleep(1.5)

    rows = rows[:TARGET]
    rows = shuffle_balance(rows, seed=poem["id"])
    dist = Counter(q["correct_option"] for q in rows)
    print(f"  answer_dist={dict(sorted(dist.items()))} author_meta={author_count}")
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--poem", type=str)
    parser.add_argument("--with-pyq-only", action="store_true", default=False)
    parser.add_argument("--all-poems", action="store_true", default=True)
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY not set")

    index = load_json(INDEX_PATH)
    poems = index["poems"]
    if args.with_pyq_only and not args.poem:
        have = {p.stem for p in PYQ_DIR.glob("*.json")}
        poems = [p for p in poems if p["id"] in have]
    if args.poem:
        key = args.poem.strip()
        poems = [p for p in poems if p["id"] == key or str(p["num"]) == key]

    Q_DIR.mkdir(parents=True, exist_ok=True)
    for poem in poems:
        print(f"\n=== Generate {poem['num']}. {poem['title']} ===")
        rows = generate_for_poem(poem, api_key)
        save_json(Q_DIR / f"{poem['id']}_questions_db.json", rows)
        print(f"  wrote {len(rows)} Q")

    combined = []
    for f in sorted(Q_DIR.glob("*_questions_db.json")):
        combined.extend(load_json(f, []))
    save_json(COMBINED_PATH, combined)
    print(f"\nCombined total: {len(combined)} → {COMBINED_PATH}")


if __name__ == "__main__":
    main()
