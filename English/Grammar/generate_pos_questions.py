#!/usr/bin/env python3
"""
Generate TNPSC General English Parts-of-Speech practice batches.

Sources: English/Grammar/parts_of_speech_notes.json (+ PYQ style samples)
Output:  English/Grammar/parts_of_speech_questions_db.json

Usage:
  python3 English/Grammar/generate_pos_questions.py --topic noun --batch 1
  python3 English/Grammar/generate_pos_questions.py --all-phase1
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NOTES_PATH = os.path.join(BASE_DIR, "English", "Grammar", "parts_of_speech_notes.json")
TOPICS_PATH = os.path.join(
    BASE_DIR, "English", "Grammar", "parts_of_speech_topics.json"
)
PYQ_PATH = os.path.join(BASE_DIR, "English", "Grammar", "parts_of_speech_pyq.json")
DB_PATH = os.path.join(
    BASE_DIR, "English", "Grammar", "parts_of_speech_questions_db.json"
)

MODEL = "gemini-3.5-flash-lite"
TARGET_PER_BATCH = 25
GENERATE_PER_CALL = 28
RULE_SAMPLE = 40
EXAMPLE_SAMPLE = 55
WORKED_SAMPLE = 25
PYQ_STYLE_SAMPLE = 8

# Phase 1: 15 batches × 25 Q
PHASE1 = [
    ("noun", 1),
    ("noun", 2),
    ("pronoun", 1),
    ("pronoun", 2),
    ("adjective", 1),
    ("adjective", 2),
    ("verb", 1),
    ("adverb", 1),
    ("adverb", 2),
    ("preposition", 1),
    ("preposition", 2),
    ("preposition", 3),
    ("conjunction", 1),
    ("conjunction", 2),
    ("interjection", 1),
]

BATCH_FOCUS = {
    ("noun", 1): "Types of nouns (Proper/Common/Collective/Abstract/Material), countable vs uncountable, identify type in a sentence, classify words.",
    ("noun", 2): "Singular–plural forms (incl. compounds), collective nouns, nominalisation (verb/adj → noun), fill suitable noun, odd noun out.",
    ("pronoun", 1): "Personal pronouns (subject/object), possessive pronouns vs possessive adjectives, fill correct pronoun.",
    ("pronoun", 2): "Relative / reflexive / demonstrative / indefinite / interrogative pronouns; join sentences with relatives.",
    ("adjective", 1): "Kinds of adjectives (quality/quantity/number/demonstrative/possessive/interrogative), identify adjective in sentence.",
    ("adjective", 2): "Order of adjectives, choose correct adjective phrase, odd-one-out (not an adjective), fill suitable adjective.",
    ("verb", 1): "Identify the verb; transitive vs intransitive; action/state verbs. WORD-CLASS only (not full tense conjugation).",
    ("adverb", 1): "Kinds of adverbs (time/place/manner/frequency/degree/reason), identify adverb in sentence.",
    ("adverb", 2): "Adverb vs adjective distinction, fill suitable adverb, odd-one-out, word-order with adverbs.",
    ("preposition", 1): "Prepositions of time and place (at/in/on, since/for, during/in); fill blanks.",
    ("preposition", 2): "Movement & contrast pairs (into/onto, between/among, above/over, below/under, along/through, before/after).",
    ("preposition", 3): "Mixed fill-in blanks, identify preposition in sentence, common error pairs (beside/besides), prepositional phrases.",
    ("conjunction", 1): "Coordinating and subordinating conjunctions; choose suitable linker; combine two sentences.",
    ("conjunction", 2): "Correlative conjunctions (either…or, not only…but also…); identify conjunction; rearrange/combine.",
    ("interjection", 1): "Identify interjections; match emotion (joy/pain/surprise/sorrow); punctuation with ! ; odd-one-out.",
}

SHAPES = {
    "noun": """Preferred TNPSC shapes (mix across the batch):
- Identify the type of noun used in the sentence (Proper/Common/Collective/Abstract/Material)
- Fill in the blank with the suitable noun / plural form
- Classify words as Proper / Common / Collective / Abstract
- Identify the noun(s) in the given sentence
- Transformation: verb/adjective → noun (nominalisation) OR singular ↔ plural
- Find the odd word (POS / noun subclass)
- Collective noun fill (a ___ of cows)
PYQ-style stems OK (odd word, plural of X, collective noun) — do NOT copy PYQ verbatim.
CRITICAL: Never say "underlined word/noun" unless you wrap that word in <u>…</u>.
Prefer naming the word: Identify the type of noun for the word 'Akbar' in: 'Akbar was a great emperor.'""",
    "pronoun": """Preferred TNPSC shapes (mix):
- Fill blank with correct personal / relative / reflexive pronoun
- Choose subject vs object pronoun
- Possessive pronoun vs possessive adjective
- Join two sentences using a relative pronoun
- Identify the pronoun / type of pronoun
- Odd-one-out among pronoun types
If referring to a word in a sentence, name it in quotes OR wrap it in <u>…</u>.""",
    "adjective": """Preferred TNPSC shapes (mix):
- Identify the adjective / kind of adjective
- Choose correct order of adjectives
- Fill blank with suitable adjective
- Find odd one out (which is NOT an adjective)
- Change form as directed (noun/verb → adjective) if in notes
- Sentence-based identification
If referring to a word in a sentence, name it in quotes OR wrap it in <u>…</u>.""",
    "verb": """Preferred TNPSC shapes (mix) — WORD CLASS only:
- Identify the verb in the sentence
- Transitive vs Intransitive
- Find odd one out (which is NOT a verb / odd verb sense)
- Choose the verb that expresses action vs state
Do NOT ask full tense conjugations or voice transforms (later menus).
If referring to a word in a sentence, name it in quotes OR wrap it in <u>…</u>.""",
    "adverb": """Preferred TNPSC shapes (mix):
- Identify the adverb / kind of adverb
- Fill blank with suitable adverb
- Adverb vs adjective (choose correct form)
- Odd-one-out
- Put words in correct order (adverb placement) if natural
If referring to a word in a sentence, name it in quotes OR wrap it in <u>…</u>.""",
    "preposition": """Preferred TNPSC shapes (mix):
- Fill in the blank with suitable preposition
- Choose most appropriate preposition
- Identify the preposition in the sentence
- Contrast pairs (since/for, between/among, beside/besides…)
- Complete short passage with prepositions
- Match preposition to meaning (sparingly)""",
    "conjunction": """Preferred TNPSC shapes (mix):
- Fill blank with suitable conjunction / linker
- Choose coordinating / subordinating / correlative conjunction
- Combine two sentences using given linker
- Identify the conjunction
- Correlative pairs (either…or, neither…nor, not only…but also)""",
    "interjection": """Preferred TNPSC shapes (mix):
- Identify the interjection
- Match interjection to emotion (joy, pain, surprise, sorrow…)
- Choose sentence with correct interjection / punctuation
- Odd-one-out (which is NOT an interjection)
- Fill blank with suitable interjection""",
}


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def normalize_q(text: str) -> str:
    return re.sub(r"\s+", "", (text or "")).lower()


def topic_meta(topic_id: str) -> dict:
    topics = load_json(TOPICS_PATH, {})
    for t in topics.get("topics", []):
        if t.get("id") == topic_id:
            return t
    return {"id": topic_id, "name_en": topic_id.title(), "name_ta": topic_id}


def format_ground_truth(rules, examples, worked):
    lines = ["RULES:"]
    for i, r in enumerate(rules, 1):
        en = (r.get("rule_en") or "").strip()
        src = r.get("source") or ""
        page = r.get("source_page")
        bit = f" ({src} p.{page})" if page is not None else f" ({src})" if src else ""
        lines.append(f"R{i}.{bit} {en}")

    lines.append("\nEXAMPLES:")
    for i, e in enumerate(examples, 1):
        inp = (e.get("input") or "").strip()
        out = (e.get("output") or "").strip()
        note = (e.get("note_en") or "").strip()
        kind = e.get("kind") or "example"
        page = e.get("source_page")
        src = e.get("source") or ""
        page_bit = f" ({src} p.{page})" if page is not None else ""
        note_bit = f" [{note}]" if note else ""
        if out:
            lines.append(f"E{i}.{page_bit} [{kind}] {inp} → {out}{note_bit}")
        else:
            lines.append(f"E{i}.{page_bit} [{kind}] {inp}{note_bit}")

    if worked:
        lines.append("\nWORKED EXERCISES (with answers):")
        for i, w in enumerate(worked, 1):
            prompt = (w.get("prompt_en") or "").strip()
            ans = (w.get("answer_en") or "").strip()
            page = w.get("source_page")
            src = w.get("source") or ""
            page_bit = f" ({src} p.{page})" if page is not None else ""
            lines.append(f"W{i}.{page_bit} {prompt} => {ans}")
    return "\n".join(lines)


def format_pyq_style(samples: list) -> str:
    if not samples:
        return ""
    lines = [
        "\nPYQ STYLE SAMPLES (pattern only — DO NOT copy stems/options verbatim):"
    ]
    for i, s in enumerate(samples[:PYQ_STYLE_SAMPLE], 1):
        q = (s.get("question_en") or "").strip()
        opts = ", ".join(
            f"{o.get('key')}:{o.get('text_en')}" for o in (s.get("options") or [])[:4]
        )
        lines.append(f"S{i}. {q} | {opts}")
    return "\n".join(lines)


def call_gemini(
    topic_id,
    topic_en,
    topic_ta,
    batch_num,
    focus,
    rules,
    examples,
    worked,
    pyq_samples,
    exclusion_texts,
    api_key,
):
    rules_s = rules if len(rules) <= RULE_SAMPLE else random.sample(rules, RULE_SAMPLE)
    examples_s = (
        examples
        if len(examples) <= EXAMPLE_SAMPLE
        else random.sample(examples, EXAMPLE_SAMPLE)
    )
    worked_s = (
        worked
        if len(worked) <= WORKED_SAMPLE
        else random.sample(worked, WORKED_SAMPLE)
    )
    pyq_s = (
        pyq_samples
        if len(pyq_samples) <= PYQ_STYLE_SAMPLE
        else random.sample(pyq_samples, PYQ_STYLE_SAMPLE)
    )

    ground = format_ground_truth(rules_s, examples_s, worked_s)
    pyq_block = format_pyq_style(pyq_s)
    exclusions = ""
    if exclusion_texts:
        exclusions = (
            "\nEXCLUDED STEMS (do not repeat / paraphrase closely):\n"
            + "\n".join(f"- {t}" for t in exclusion_texts[:100])
        )

    shapes = SHAPES.get(topic_id, SHAPES["noun"])

    prompt = f"""
You are a senior TNPSC General English (SSLC Standard) exam compiler for Unit I Grammar.
Menu: Parts of Speech → Topic: "{topic_en}" ({topic_ta})
Practice Batch {batch_num} focus: {focus}

Generate exactly {GENERATE_PER_CALL} practice MCQs for this batch.

GROUND TRUTH (Asan Academy + TN Govt notes). Use ONLY this material for answers:
{ground}
{pyq_block}
{exclusions}

Generation rules:
1. Every correct answer MUST be supported by the ground truth. Prefer authentic examples from notes;
   you may rephrase stems but answers must match the notes.
2. Do NOT copy PYQ stems/options verbatim. Imitate TNPSC STYLE only (odd word, fill blank,
   identify type, plural forms, choose correct option, Option-E habit).
3. English ONLY for General English — no Tamil. Set question_ta = question_en, options_ta = options_en, explanation_ta = explanation_en.
4. No Medium/Hard force. Clean SSLC-standard Grammar items.
5. Batch focus (stay mostly within this focus, light overlap OK): {focus}
   6. {shapes}
7. NEVER write "the underlined word/noun" unless that exact word is wrapped in <u>word</u>. Prefer: for the word 'X' in: '…'.
8. Each object keys (JSON array only):
   - question_en, question_ta
   - options_en: exactly 4 strings
   - options_ta: exactly 4 strings (parallel; copy English)
   - answer_en: must equal one of options_en exactly
   - answer_ta: must equal one of options_ta exactly
   - explanation_en, explanation_ta (brief rule cite)
   - difficulty: optional "medium"
   - source_note: short pointer like "asan p.3 / govt p.83 / R2"

Option E (Answer not known) will be added by post-processing — do NOT include it in options.
Escape internal quotes. Return ONLY a JSON array.
"""

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}"
        f":generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    headers = {"Content-Type": "application/json"}

    retries = 6
    attempt = 0
    rate_limit_attempt = 0
    delay = 12
    while attempt < retries:
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=210) as response:
                res_json = json.loads(response.read().decode("utf-8"))
                raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                if raw_text.startswith("```"):
                    raw_text = raw_text.split("\n", 1)[1]
                    if raw_text.endswith("```"):
                        raw_text = raw_text.rsplit("\n", 1)[0]
                start_idx = raw_text.find("[")
                if start_idx != -1:
                    count = 0
                    for idx in range(start_idx, len(raw_text)):
                        if raw_text[idx] == "[":
                            count += 1
                        elif raw_text[idx] == "]":
                            count -= 1
                            if count == 0:
                                raw_text = raw_text[start_idx : idx + 1]
                                break
                data = json.loads(raw_text)
                return data if isinstance(data, list) else []
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            if e.code in (429, 503):
                rate_limit_attempt += 1
                print(f"    HTTP {e.code}; retry in {delay}s... ({body[:120]})")
                if rate_limit_attempt >= 6:
                    break
                time.sleep(delay)
                delay = min(delay * 2, 90)
            else:
                attempt += 1
                print(f"    HTTP {e.code}: {body[:200]}")
                time.sleep(5)
        except Exception as e:
            attempt += 1
            print(f"    Error: {e}")
            time.sleep(5)
    return []


def normalize_raw_question(q: dict, topic_id: str, topic_en: str, topic_ta: str, batch_num: int):
    q_en = str(q.get("question_en") or "").strip()
    q_ta = str(q.get("question_ta") or "").strip()
    if not q_en:
        return None

    opts_en = q.get("options_en") or []
    opts_ta = q.get("options_ta") or []
    if not isinstance(opts_en, list) or len(opts_en) < 4:
        # tolerate options: [{key,text_en}]
        raw_opts = q.get("options") or []
        if isinstance(raw_opts, list) and len(raw_opts) >= 4:
            opts_en = [
                (o.get("text_en") or o.get("text") or "").strip()
                if isinstance(o, dict)
                else str(o)
                for o in raw_opts[:4]
            ]
            opts_ta = [
                (o.get("text_ta") or o.get("text_en") or "").strip()
                if isinstance(o, dict)
                else str(o)
                for o in raw_opts[:4]
            ]
        else:
            return None
    opts_en = [str(x).strip() for x in opts_en[:4]]
    if len(opts_ta) < 4:
        opts_ta = list(opts_en)
    opts_ta = [str(x).strip() for x in opts_ta[:4]]
    if any(not x for x in opts_en):
        return None

    ans_en = str(q.get("answer_en") or q.get("correct_en") or "").strip()
    ans_ta = str(q.get("answer_ta") or "").strip()
    if ans_en not in opts_en:
        # try correct_option letter
        letter = str(q.get("correct_option") or "").strip().upper()[:1]
        if letter in "ABCD":
            ans_en = opts_en[ord(letter) - ord("A")]
        else:
            return None
    correct_index = opts_en.index(ans_en)
    if not ans_ta or ans_ta not in opts_ta:
        ans_ta = opts_ta[correct_index]

    pairs = list(zip(opts_en, opts_ta))
    correct_pair = pairs[correct_index]
    random.shuffle(pairs)
    keys_map = ["A", "B", "C", "D"]
    standard_options = []
    correct_key = "A"
    for i, (en, ta) in enumerate(pairs):
        standard_options.append({"key": keys_map[i], "text_en": en, "text_ta": ta})
        if (en, ta) == correct_pair:
            correct_key = keys_map[i]
    standard_options.append(
        {
            "key": "E",
            "text_en": "Answer not known",
            "text_ta": "விடை தெரியவில்லை",
        }
    )

    expl_en = str(q.get("explanation_en") or q.get("explanation") or "").strip()
    expl_ta = str(q.get("explanation_ta") or "").strip()
    if not expl_en:
        return None

    return {
        "subject": "English",
        "unit": "Grammar",
        "menu": "Parts of Speech",
        "topic": topic_en,
        "topic_id": topic_id,
        "topic_ta": topic_ta,
        "source_exam": f"Practice Batch {batch_num}",
        "difficulty": "Medium",
        "question_en": q_en,
        "question_ta": q_ta or q_en,
        "options": standard_options,
        "correct_option": correct_key,
        "explanation": expl_en,
        "explanation_ta": expl_ta or expl_en,
        "type": "practice",
        "batch": f"Batch {batch_num}",
        "group": "Practice",
        "source_note": str(q.get("source_note") or "").strip(),
    }


def generate_batch(topic_id: str, batch_num: int, api_key: str) -> int:
    meta = topic_meta(topic_id)
    topic_en = meta.get("name_en") or topic_id.title()
    topic_ta = meta.get("name_ta") or topic_id

    notes = load_json(NOTES_PATH, {})
    block = (notes.get("topics") or {}).get(topic_id) or {}
    rules = block.get("rules") or []
    examples = block.get("examples") or []
    worked = block.get("worked_exercises") or []
    pyq_samples = block.get("pyq_samples") or []

    # Also pull mixed_pos worked drills lightly for odd-word style on adj/verb/noun
    if topic_id in ("noun", "adjective", "verb", "adverb") and not pyq_samples:
        mixed = notes.get("mixed_pos") or {}
        pyq_samples = mixed.get("pyq_samples") or []

    if not rules and not examples and not worked:
        print(f"ERROR: no notes for {topic_id}")
        return 0

    focus = BATCH_FOCUS.get((topic_id, batch_num), f"General {topic_en} MCQs")
    print(f"\n=== {topic_id} Batch {batch_num}: {topic_en} ===")
    print(f"Focus: {focus}")
    print(f"Notes: R={len(rules)} E={len(examples)} W={len(worked)} PYQ={len(pyq_samples)}")

    db = load_json(DB_PATH, [])
    if not isinstance(db, list):
        db = []

    existing_keys = set()
    exclusion_texts = []
    for q in db:
        if not isinstance(q, dict):
            continue
        existing_keys.add(normalize_q(q.get("question_en")))
        existing_keys.add(normalize_q(q.get("question_ta")))
        if q.get("topic_id") == topic_id:
            exclusion_texts.append((q.get("question_en") or "")[:160])

    valid = []
    for attempt in range(1, 5):
        need = TARGET_PER_BATCH - len(valid)
        if need <= 0:
            break
        print(f"  API call {attempt} (have {len(valid)}/{TARGET_PER_BATCH})...")
        raw = call_gemini(
            topic_id,
            topic_en,
            topic_ta,
            batch_num,
            focus,
            rules,
            examples,
            worked,
            pyq_samples,
            exclusion_texts + [v["question_en"][:160] for v in valid],
            api_key,
        )
        print(f"  Got {len(raw)} raw questions")
        for q in raw:
            if not isinstance(q, dict):
                continue
            std = normalize_raw_question(q, topic_id, topic_en, topic_ta, batch_num)
            if not std:
                continue
            key_en = normalize_q(std["question_en"])
            key_ta = normalize_q(std["question_ta"])
            if key_en in existing_keys or key_ta in existing_keys:
                continue
            if any(
                normalize_q(v["question_en"]) == key_en
                or normalize_q(v["question_ta"]) == key_ta
                for v in valid
            ):
                continue
            valid.append(std)
            existing_keys.add(key_en)
            existing_keys.add(key_ta)
        print(f"  Accumulated valid={len(valid)}")
        if len(valid) >= TARGET_PER_BATCH:
            break
        time.sleep(8)

    if len(valid) < TARGET_PER_BATCH:
        print(f"WARNING: need {TARGET_PER_BATCH}; got {len(valid)} — saving what we have")
        if len(valid) < 15:
            print("ERROR: too few questions; abort this batch")
            return 0

    valid.sort(key=lambda q: len(q["explanation"]) + len(q.get("explanation_ta") or ""), reverse=True)
    final_batch = valid[:TARGET_PER_BATCH]
    random.shuffle(final_batch)

    db.extend(final_batch)
    save_json(DB_PATH, db)
    print(
        f"SUCCESS: +{len(final_batch)} Q → {DB_PATH} "
        f"({topic_en} Batch {batch_num}); DB total={len(db)}"
    )
    return len(final_batch)


def main():
    parser = argparse.ArgumentParser(description="Generate POS practice batches")
    parser.add_argument("--topic", help="topic id, e.g. noun")
    parser.add_argument("--batch", type=int, help="batch number")
    parser.add_argument(
        "--all-phase1",
        action="store_true",
        help="Generate all 15 Phase-1 batches (375 Q)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List Phase-1 plan",
    )
    args = parser.parse_args()

    if args.list:
        for tid, b in PHASE1:
            print(f"{tid:14} Batch {b}: {BATCH_FOCUS.get((tid,b),'')[:70]}")
        print(f"Total: {len(PHASE1)} batches × {TARGET_PER_BATCH} = {len(PHASE1)*TARGET_PER_BATCH} Q")
        return

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY not found.")

    if args.all_phase1:
        jobs = PHASE1
    elif args.topic and args.batch:
        jobs = [(args.topic, args.batch)]
    else:
        raise SystemExit("Pass --topic X --batch N  OR  --all-phase1")

    # Fresh DB only if starting phase1 from scratch and file missing
    if args.all_phase1 and not os.path.exists(DB_PATH):
        save_json(DB_PATH, [])

    total = 0
    failed = []
    for tid, bnum in jobs:
        # skip if this topic+batch already has TARGET questions
        db = load_json(DB_PATH, [])
        already = sum(
            1
            for q in db
            if isinstance(q, dict)
            and q.get("topic_id") == tid
            and q.get("batch") == f"Batch {bnum}"
        )
        if already >= TARGET_PER_BATCH:
            print(f"\nSKIP {tid} Batch {bnum}: already {already} Q")
            continue
        n = generate_batch(tid, bnum, api_key)
        if n <= 0:
            failed.append((tid, bnum))
        else:
            total += n
        time.sleep(5)

    print(f"\n==== DONE: added {total} questions ====")
    if failed:
        print("Failed batches:", failed)
        sys.exit(1)

    # summary
    db = load_json(DB_PATH, [])
    from collections import Counter

    c = Counter()
    for q in db:
        if isinstance(q, dict):
            c[f"{q.get('topic_id')}|{q.get('batch')}"] += 1
    print("DB by topic/batch:")
    for k in sorted(c):
        print(f"  {k}: {c[k]}")
    print(f"DB total: {len(db)}")


if __name__ == "__main__":
    main()
