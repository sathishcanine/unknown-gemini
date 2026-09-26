#!/usr/bin/env python3
"""Generate 25-question TNPSC-oriented Physics practice batches."""

from __future__ import annotations

import argparse
import difflib
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from gemini_keys import gemini_keys  # noqa: E402

FACTS_PATH = os.path.join(BASE_DIR, "Physics", "physics_facts.json")
DB_PATH = os.path.join(BASE_DIR, "Physics", "physics_questions_db.json")
GUIDE_PATH = os.path.join(
    BASE_DIR, "Physics", "PHYSICS_BATCH_GENERATION_GUIDE.md"
)
QC_PATH = os.path.join(
    BASE_DIR, "Physics", "physics_questions_qc_report.json"
)
MODEL = "gemini-3.1-flash-lite"
KEY_POOL = gemini_keys()

BATCH_SIZE = 25
GEN_TOTAL = 30
PYQ_STYLE_SAMPLE = 20
SINGLE_PASS_BUFFER_PER_BATCH = 5
API_TIMEOUT_SECONDS = 180
MATCH_HTML_EXAMPLE = (
    "Match the following:<br><div class='match-container'>"
    "<div class='match-col-left'>a) Item A<br>b) Item B<br>c) Item C<br>d) Item D</div>"
    "<div class='match-col-right'>1. Match 1<br>2. Match 2<br>3. Match 3<br>4. Match 4</div>"
    "</div>"
)
FORMAT_TARGETS = {
    "direct": 8,
    "statement": 7,
    "assertion_reason": 3,
    "match": 3,
    "paragraph": 4,
}
EXPECTED_BATCHES = tuple(f"Batch {number}" for number in range(1, 4))
MIN_FACTS_TWO_BATCHES = 45
MIN_FACTS_THREE_BATCHES = 70


def topic_batch_plan(fact_count: int) -> tuple[str, ...]:
    if fact_count >= MIN_FACTS_THREE_BATCHES:
        return EXPECTED_BATCHES
    if fact_count >= MIN_FACTS_TWO_BATCHES:
        return ("Batch 1", "Batch 2")
    raise SystemExit(
        f"Need at least {MIN_FACTS_TWO_BATCHES} facts for 2 batches; "
        f"found {fact_count}"
    )


def expected_batches_for_topic(topic: str, facts_db: dict) -> tuple[str, ...]:
    facts = facts_db.get(topic) or []
    return topic_batch_plan(len(facts))

_key_index = 0
_disabled_keys: set[str] = set()
_rate_limit_hits = 0


def next_api_key() -> str:
    global _key_index
    for _ in range(len(KEY_POOL) * 2):
        key = KEY_POOL[_key_index % len(KEY_POOL)]
        _key_index += 1
        if key not in _disabled_keys:
            return key
    raise SystemExit(f"All {len(KEY_POOL)} Gemini keys are disabled")


def disable_key(key: str, reason: str):
    if key not in _disabled_keys:
        _disabled_keys.add(key)
        print(f"  ⚠ Disabling key …{key[-6:]}: {reason}")


def parse_array(raw: str) -> list:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("\n", 1)[0]
    start = text.find("[")
    if start < 0:
        return []
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "[":
            depth += 1
        elif text[index] == "]":
            depth -= 1
            if depth == 0:
                text = text[start : index + 1]
                break
    data = json.loads(text)
    return data if isinstance(data, list) else []


def post_gemini(prompt: str, timeout: int = 300) -> list:
    global _rate_limit_hits
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    key = next_api_key()
    delay = 8
    for attempt in range(1, 6):
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{MODEL}:generateContent?key={key}"
        )
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            print(
                f"  Gemini call attempt {attempt}/5 "
                f"(prompt_chars={len(prompt)}, timeout={timeout}s)…",
                flush=True,
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
                return parse_array(
                    result["candidates"][0]["content"]["parts"][0]["text"]
                )
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            if exc.code in (429, 503):
                _rate_limit_hits += 1
                print(
                    f"  ⚠ HTTP {exc.code}; rotate key, sleep {delay}s "
                    f"(hit #{_rate_limit_hits})"
                )
                time.sleep(delay)
                delay = min(delay * 2, 60)
                key = next_api_key()
                continue
            if exc.code == 404 and "no longer available" in body.lower():
                disable_key(key, "model unavailable")
                key = next_api_key()
                continue
            print(f"  HTTP {exc.code} attempt {attempt}/5: {body[:200]}")
        except Exception as exc:
            print(f"  Attempt {attempt}/5 failed: {exc}")
        time.sleep(4)
        key = next_api_key()
    return []


def load_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return default


def normalize_text(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", (text or "").lower()))


def has_tamil(text: str) -> bool:
    return bool(re.search(r"[\u0B80-\u0BFF]", text or ""))


def numbered_items(text: str) -> list[str]:
    """Return visible 1.–4. or 1)–4) statement items."""
    parts = re.split(
        r"(?:^|<br\s*/?>|\n)\s*[1-4][.)]\s*",
        text or "",
        flags=re.I,
    )
    return [normalize_text(part) for part in parts[1:] if normalize_text(part)]


def parse_match_code(text: str) -> dict[str, str] | None:
    """Parse a complete a–d to 1–4 bijection from one option."""
    pairs = re.findall(r"\b([a-d])\s*[-–:]\s*([1-4])\b", text or "", re.I)
    if len(pairs) != 4:
        return None
    mapping = {left.lower(): right for left, right in pairs}
    if set(mapping) != set("abcd") or set(mapping.values()) != set("1234"):
        return None
    residue = re.sub(
        r"\b[a-d]\s*[-–:]\s*[1-4]\b", "", text or "", flags=re.I
    )
    if re.sub(r"[\s,;]+", "", residue):
        return None
    return mapping


def similar_stem(stem: str, exclusions: list[str]) -> bool:
    current = normalize_text(stem)
    if not current:
        return True
    for other in exclusions:
        previous = normalize_text(other)
        if current == previous:
            return True
        if (
            min(len(current), len(previous)) >= 45
            and difflib.SequenceMatcher(None, current, previous).ratio() >= 0.93
        ):
            return True
    return False


def resolve_source_fact(source: str, fact_lookup: dict[str, str]) -> str | None:
    """Map a model paraphrase back to one canonical source fact."""
    normalized = normalize_text(source)
    if normalized in fact_lookup:
        return fact_lookup[normalized]
    if not normalized:
        return None
    for fact_norm, canonical in fact_lookup.items():
        if (
            len(normalized) >= 35
            and (normalized in fact_norm or fact_norm in normalized)
        ):
            return canonical
    best_ratio = 0.0
    best_fact = None
    for fact_norm, canonical in fact_lookup.items():
        ratio = difflib.SequenceMatcher(None, normalized, fact_norm).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_fact = canonical
    return best_fact if best_ratio >= 0.80 else None


def normalize_match_layout(stem: str) -> str | None:
    """Wrap a complete plain 4×4 match stem in the required HTML columns."""
    text = (stem or "").strip()
    lower = text.lower()
    if all(
        token in lower
        for token in ("match-container", "match-col-left", "match-col-right")
    ):
        return text
    for old, new in (
        ("அ)", "a)"),
        ("ஆ)", "b)"),
        ("இ)", "c)"),
        ("ஈ)", "d)"),
        ("a.", "a)"),
        ("b.", "b)"),
        ("c.", "c)"),
        ("d.", "d)"),
    ):
        text = text.replace(old, new)
    lower = text.lower()
    required = ("a)", "b)", "c)", "d)", "1.", "2.", "3.", "4.")
    if not all(token in lower for token in required):
        # Accept numbered items written with closing parentheses.
        if not all(token in lower for token in ("a)", "b)", "c)", "d)")):
            return None
        for number in "1234":
            text = re.sub(rf"(?<!\d){number}\)", f"{number}.", text)
        lower = text.lower()
        if not all(f"{number}." in lower for number in "1234"):
            return None
    left_start = lower.find("a)")
    if left_start < 0:
        for marker in ("அ)", "ஆ)", "இ)", "ஈ)"):
            left_start = lower.find(marker)
            if left_start >= 0:
                break
    right_start = lower.find("1.", left_start if left_start >= 0 else 0)
    if right_start < 0:
        right_start = lower.find("1)", left_start if left_start >= 0 else 0)
    if left_start < 0 or right_start < 0:
        return None
    intro = text[:left_start].strip().rstrip("<br>").strip()
    left = text[left_start:right_start].strip()
    right = text[right_start:].strip()
    for marker in ("a)", "b)", "c)", "d)"):
        if marker not in left.lower():
            return None
    for marker in ("1.", "2.", "3.", "4."):
        if marker not in right.lower():
            return None
    clean = lambda value: re.sub(r"(?:\r?\n|<br\s*/?>)+", "<br>", value).strip()
    return (
        f"{clean(intro)}<br><div class='match-container'>"
        f"<div class='match-col-left'>{clean(left)}</div>"
        f"<div class='match-col-right'>{clean(right)}</div></div>"
    )


def force_match_layout(stem: str) -> str | None:
    """Last-resort parser: extract a–d / 1–4 items and wrap in required HTML."""
    text = re.sub(r"<br\s*/?>", "\n", (stem or "").strip())
    left: dict[str, str] = {}
    right: dict[str, str] = {}
    for label in "abcd":
        match = re.search(
            rf"(?i)(?<![a-z0-9]){label}\)\s*(.+?)(?=\s*(?:[a-d]\)|[1-4][.)]|$))",
            text,
            re.S,
        )
        if match:
            left[label] = " ".join(match.group(1).split())
    for number in "1234":
        match = re.search(
            rf"(?<![0-9]){number}[.)]\s*(.+?)(?=\s*(?:[1-4][.)]|$))",
            text,
            re.S,
        )
        if match:
            right[number] = " ".join(match.group(1).split())
    if len(left) != 4 or len(right) != 4:
        return None
    intro = re.split(r"(?i)(?<![a-z0-9])a\)", text, maxsplit=1)[0].strip()
    if not intro:
        intro = "Match the following:"
    left_html = "<br>".join(f"{label}) {left[label]}" for label in "abcd")
    right_html = "<br>".join(f"{number}. {right[number]}" for number in "1234")
    return (
        f"{intro}<br><div class='match-container'>"
        f"<div class='match-col-left'>{left_html}</div>"
        f"<div class='match-col-right'>{right_html}</div></div>"
    )


def pyq_style_text(pyqs: list, sample_size: int = PYQ_STYLE_SAMPLE) -> str:
    lines = []
    for index, q in enumerate(pyqs[:sample_size], 1):
        options = "; ".join(
            f"{option.get('key')}) {option.get('text_en', '')}"
            for option in (q.get("options") or [])[:4]
        )
        lines.append(
            f"{index}. [{q.get('topic', '')}] {q.get('question_en', '')} "
            f"| {options}"
        )
    return "\n".join(lines)


def compact_generation_rules() -> str:
    return """
1. Facts are the only source of truth; store one verbatim English fact as source_fact.
2. Physics PYQs are orientation/style only — never copy a PYQ stem or import PYQ-only facts.
3. Each batch: exactly 25 Medium questions with mix 8 direct, 7 statement, 3 assertion_reason,
   3 match, 4 paragraph; at least 4 contextual per batch.
4. Use each source_fact at most once across the entire topic output.
5. Match: copy this exact HTML shell and replace item text only:
   {MATCH_HTML_EXAMPLE}
   Every A–D option must be one complete bijection such as a-2, b-1, c-4, d-3.
6. Statement: 2–4 numbered statements plus an explicit which-statements-are-correct instruction.
7. Assertion–Reason: standard four TNPSC logical alternatives.
8. Bilingual English + Tamil Unicode for stem, A–D options, and explanations.
9. Plausible distractors from nearby facts; no outside knowledge or invented values.
10. No duplicate or near-duplicate stems within the topic output.
""".strip()


def single_batch_prompt(
    topic: str,
    batch_num: int,
    facts: list,
    pyqs: list,
    exclusions: list[str],
    excluded_source_facts: set[str],
    buffer: int = SINGLE_PASS_BUFFER_PER_BATCH,
    shortage_note: str = "",
) -> str:
    requested = BATCH_SIZE + buffer
    fact_lines = "\n".join(
        f"FACT {index + 1}: {fact['fact_en']} || TA: {fact['fact_ta']}"
        for index, fact in enumerate(facts)
    )
    exclusion_lines = "\n".join(f"- {stem}" for stem in exclusions[-120:])
    excluded_count = len(excluded_source_facts)
    return f"""
You are a senior TNPSC Group I/II Physics exam compiler.
Generate exactly {requested} NEW Medium practice MCQs for "{topic}", Batch {batch_num}.

TARGET FINAL MIX (keep 25 after reserve):
- direct: 8
- statement: 7
- assertion_reason: 3
- match: 3
- paragraph: 4
- at least 4 contextual questions

MANDATORY DISTINCTION:
- FACTS below are the only source of truth for answers and explanations.
- PYQs below are style/orientation references only. Never import a PYQ fact unless
  that fact also occurs in FACTS. Never copy a PYQ stem.

GROUND-TRUTH FACTS ({len(facts)} facts):
{fact_lines}

PHYSICS PYQ ORIENTATION SAMPLES:
{pyq_style_text(pyqs)}

EXCLUDED PRACTICE STEMS — do not repeat or closely paraphrase:
{exclusion_lines or "- None"}

ALREADY-USED SOURCE FACTS — do not reuse any of the {excluded_count} prior facts.

GENERATION RULES:
{compact_generation_rules().format(MATCH_HTML_EXAMPLE=MATCH_HTML_EXAMPLE)}

{shortage_note}

Return ONLY one JSON array with exactly {requested} objects.
Every object must include `"batch": {batch_num}`.
Use each source_fact at most once in this response.

Object schema:
{{
  "batch": {batch_num},
  "question_format": "direct|statement|assertion_reason|match|paragraph",
  "contextual": true,
  "question_en": "...",
  "question_ta": "...",
  "options": [
    {{"key":"A","text_en":"...","text_ta":"..."}},
    {{"key":"B","text_en":"...","text_ta":"..."}},
    {{"key":"C","text_en":"...","text_ta":"..."}},
    {{"key":"D","text_en":"...","text_ta":"..."}}
  ],
  "correct_option": "A|B|C|D",
  "explanation": "...",
  "explanation_ta": "...",
  "difficulty": "Medium",
  "source_fact": "exact English FACT text"
}}
""".strip()


def generation_prompt(
    topic: str,
    batch_num: int,
    facts: list,
    pyqs: list,
    exclusions: list[str],
    excluded_source_facts: set[str],
    requested_total: int = GEN_TOTAL,
    shortage_note: str = "",
) -> str:
    fact_lines = "\n".join(
        f"FACT {index + 1}: {fact['fact_en']} || TA: {fact['fact_ta']}"
        for index, fact in enumerate(facts)
    )
    exclusion_lines = "\n".join(f"- {stem}" for stem in exclusions[-180:])
    excluded_fact_lines = "\n".join(
        f"- {fact}" for fact in sorted(excluded_source_facts)
    )
    guide = open(GUIDE_PATH, encoding="utf-8").read()
    mix_instructions = (
        f"""TOP-UP REQUEST: {shortage_note}.
Generate all {requested_total} candidates ONLY in the shortage formats, weighted
by the listed shortages. If `match` is short, use this exact structure in both
languages (with translated item text but literal a–d and 1–4 labels):
Match the following:<br><div class='match-container'><div class='match-col-left'>a) Item A<br>b) Item B<br>c) Item C<br>d) Item D</div><div class='match-col-right'>1. Match 1<br>2. Match 2<br>3. Match 3<br>4. Match 4</div></div>
Each match option must contain only a complete bijection such as
`a-2, b-1, c-4, d-3`. If `statement` is short, place `<br>` before every
numbered statement and end with an explicit Which/Identify/Select instruction."""
        if shortage_note
        else """
TARGET CANDIDATE MIX:
- direct: 9
- statement: 8
- assertion_reason: 4
- match: 4
- paragraph: 5
""".strip()
    )
    return f"""
You are a senior TNPSC Group I/II Physics exam compiler.
Generate exactly {requested_total} NEW Medium practice MCQs for "{topic}",
Practice Batch {batch_num}.

MANDATORY DISTINCTION:
- FACTS below are the only source of truth for answers and explanations.
- PYQs below are style/orientation references only. Never import a PYQ fact unless
  that fact also occurs in FACTS. Never copy a PYQ stem.

GROUND-TRUTH FACTS:
{fact_lines}

PHYSICS PYQ ORIENTATION BANK:
{pyq_style_text(pyqs)}

EXCLUDED PRACTICE STEMS — do not repeat or closely paraphrase:
{exclusion_lines or "- None"}

ALREADY-USED SOURCE FACTS — do not use these facts for any new candidate:
{excluded_fact_lines or "- None"}

{mix_instructions}

GENERATION RULES:
{guide}

Additional hard requirements:
1. Every object must use one supporting FACT verbatim as `source_fact`.
2. Every answer must be derivable from that fact or an explicitly combined set of
   supplied facts; no outside Physics knowledge.
3. Provide exactly four content options A–D. Do not include option E; the saver adds it.
4. Statement questions: show 2–4 numbered statements and use combination options.
5. Match questions: strict 4×4 HTML with match-container, match-col-left and
   match-col-right; options must be complete matching codes.
6. Assertion–Reason: use standard A/R alternatives.
7. Paragraph questions: 2–3 sentence fact-grounded premise requiring selection or
   inference, not an unsupported current-affairs story.
8. `contextual` is true for an applied observational/numerical TNPSC context; at
   least 4 candidates should be contextual.
9. Tamil must be natural Unicode and fully equivalent to English.
10. Explanations must state why the correct option follows from the source fact.
11. difficulty must be exactly "Medium".

Return ONLY a JSON array. Object schema:
{{
  "question_format": "direct|statement|assertion_reason|match|paragraph",
  "contextual": true,
  "question_en": "...",
  "question_ta": "...",
  "options": [
    {{"key":"A","text_en":"...","text_ta":"..."}},
    {{"key":"B","text_en":"...","text_ta":"..."}},
    {{"key":"C","text_en":"...","text_ta":"..."}},
    {{"key":"D","text_en":"...","text_ta":"..."}}
  ],
  "correct_option": "A|B|C|D",
  "explanation": "...",
  "explanation_ta": "...",
  "difficulty": "Medium",
  "source_fact": "exact English FACT text"
}}
""".strip()


def normalize_candidate(
    raw: dict,
    topic: str,
    batch_num: int,
    fact_lookup: dict[str, str],
    exclusions: list[str],
    excluded_source_facts: set[str],
    candidate_source_facts: set[str],
    existing_source_formats: dict[str, set[str]],
):
    if not isinstance(raw, dict):
        return None, "not_object"
    required = (
        "question_en",
        "question_ta",
        "options",
        "correct_option",
        "explanation",
        "explanation_ta",
        "source_fact",
        "question_format",
    )
    if any(not raw.get(field) for field in required):
        return None, "missing_field"

    stem_en = str(raw["question_en"]).strip()
    stem_ta = str(raw["question_ta"]).strip()
    if len(stem_en) < 15 or not has_tamil(stem_ta):
        return None, "bad_stem"
    if similar_stem(stem_en, exclusions):
        return None, "duplicate_stem"

    question_format = str(raw["question_format"]).strip().lower()
    if question_format not in FORMAT_TARGETS:
        return None, "bad_format"
    if question_format == "match":
        normalized_en = normalize_match_layout(stem_en) or force_match_layout(stem_en)
        normalized_ta = normalize_match_layout(stem_ta) or force_match_layout(stem_ta)
        if not normalized_en:
            return None, "match_not_4x4"
        stem_en = normalized_en
        stem_ta = normalized_ta or normalized_en

    options = raw.get("options")
    if not isinstance(options, list) or len(options) != 4:
        return None, "bad_options"
    by_key = {}
    for option in options:
        if not isinstance(option, dict):
            return None, "bad_options"
        key = str(option.get("key") or "").strip().upper()
        text_en = str(option.get("text_en") or "").strip()
        text_ta = str(option.get("text_ta") or "").strip()
        if key not in "ABCD" or not text_en or not text_ta:
            return None, "bad_options"
        if not has_tamil(text_ta) and re.search(r"[A-Za-z]{4,}", text_ta):
            return None, "missing_tamil_option"
        by_key[key] = {
            "key": key,
            "text_en": text_en,
            "text_ta": text_ta,
        }
    if set(by_key) != set("ABCD"):
        return None, "bad_option_keys"
    normalized_options = [normalize_text(by_key[key]["text_en"]) for key in "ABCD"]
    if len(set(normalized_options)) != 4:
        return None, "duplicate_options"

    correct = str(raw["correct_option"]).strip().upper()
    if correct not in "ABCD":
        return None, "bad_correct"

    source_fact_raw = str(raw["source_fact"]).strip()
    source_fact = resolve_source_fact(source_fact_raw, fact_lookup)
    if not source_fact:
        return None, "ungrounded_source_fact"
    if source_fact in excluded_source_facts:
        return None, "duplicate_source_fact"
    if source_fact in candidate_source_facts:
        return None, "duplicate_source_fact"
    if question_format in existing_source_formats.get(source_fact, set()):
        return None, "duplicate_source_fact"

    lower_stem = stem_en.lower()
    if question_format == "match":
        if not all(
            token in lower_stem
            for token in (
                "match-container",
                "match-col-left",
                "match-col-right",
            )
        ):
            return None, "match_not_4x4"
        if not (
            all(marker in lower_stem for marker in ("a)", "b)", "c)", "d)"))
            or all(marker in stem_ta for marker in ("அ)", "ஆ)", "இ)", "ஈ)"))
        ):
            return None, "match_not_4x4"
        if not all(
            re.search(rf"{number}[.)]", stem_en, re.I)
            for number in "1234"
        ):
            return None, "match_not_4x4"
        parsed_codes = [
            parse_match_code(by_key[key]["text_en"]) for key in "ABCD"
        ]
        if any(code is None for code in parsed_codes):
            return None, "match_bad_options"
        if parsed_codes["ABCD".index(correct)] is None:
            return None, "match_bad_correct"
    if question_format == "statement":
        visible_statements = len(
            re.findall(r"(?:^|<br>|\n)\s*[1-4][.)]", stem_en, re.I)
        )
        if visible_statements < 2:
            return None, "statements_missing"

    explanation = str(raw["explanation"]).strip()
    explanation_ta = str(raw["explanation_ta"]).strip()
    if len(explanation) < 35 or not has_tamil(explanation_ta):
        return None, "bad_explanation"

    standard_options = [by_key[key] for key in "ABCD"]
    standard_options.append(
        {
            "key": "E",
            "text_en": "Answer not known",
            "text_ta": "விடை தெரியவில்லை",
        }
    )
    return (
        {
            "subject": "Physics",
            "topic": topic,
            "source_exam": f"Practice Batch {batch_num}",
            "difficulty": "Medium",
            "question_en": stem_en,
            "question_ta": stem_ta,
            "options": standard_options,
            "correct_option": correct,
            "explanation": explanation,
            "explanation_ta": explanation_ta,
            "type": "practice",
            "batch": f"Batch {batch_num}",
            "group": "Practice",
            "source_fact": source_fact,
            "question_format": question_format,
            "contextual": bool(raw.get("contextual")),
            "orientation": "Physics PYQ",
        },
        None,
    )


def select_batch(candidates: list) -> tuple[list, dict]:
    buckets = {name: [] for name in FORMAT_TARGETS}
    for question in candidates:
        buckets[question["question_format"]].append(question)
    selected = []
    shortages = {}
    for name, target in FORMAT_TARGETS.items():
        bucket = sorted(
            buckets[name],
            key=lambda q: (
                bool(q.get("contextual")),
                len(q["explanation"]) + len(q["explanation_ta"]),
            ),
            reverse=True,
        )
        selected.extend(bucket[:target])
        if len(bucket) < target:
            shortages[name] = target - len(bucket)
    return selected, shortages


def balance_correct_positions(questions: list) -> None:
    """Reorder A–D options to a deterministic 7/6/6/6 answer distribution."""
    target_positions = list("ABCD") * 6 + ["A"]
    for question, target in zip(questions, target_positions):
        current = question["correct_option"]
        if current == target:
            continue
        options = question["options"]
        current_index = "ABCD".index(current)
        target_index = "ABCD".index(target)
        options[current_index], options[target_index] = (
            options[target_index],
            options[current_index],
        )
        for index, option in enumerate(options[:4]):
            option["key"] = "ABCD"[index]
        question["correct_option"] = target


def save_batch(topic: str, batch_num: int, questions: list):
    database = load_json(DB_PATH, [])
    batch_name = f"Batch {batch_num}"
    database = [
        q
        for q in database
        if not (
            q.get("type") == "practice"
            and q.get("topic") == topic
            and q.get("batch") == batch_name
        )
    ]
    random.Random(f"{topic}-{batch_num}").shuffle(questions)
    database.extend(questions)
    with open(DB_PATH, "w", encoding="utf-8") as handle:
        json.dump(database, handle, indent=2, ensure_ascii=False)


def reset_topic_practice(topic: str) -> None:
    """Remove only one topic's practice records before a full regeneration."""
    database = load_json(DB_PATH, [])
    retained = [
        question
        for question in database
        if not (
            question.get("type") == "practice"
            and question.get("topic") == topic
        )
    ]
    with open(DB_PATH, "w", encoding="utf-8") as handle:
        json.dump(retained, handle, indent=2, ensure_ascii=False)
    print(f"Removed {len(database) - len(retained)} existing {topic} practice records")


def run_qc(
    in_progress_topic: str | None = None,
    facts_db: dict | None = None,
) -> dict:
    if facts_db is None:
        facts_db = load_json(FACTS_PATH, {})
    database = load_json(DB_PATH, [])
    pyq_stems = {
        normalize_text(q.get("question_en") or "")
        for q in database
        if q.get("type") == "pyq"
    }
    valid_facts_by_topic = {
        topic: {
            fact.get("fact_en")
            for fact in facts
            if fact.get("fact_en")
        }
        for topic, facts in facts_db.items()
    }
    practice = [q for q in database if q.get("type") == "practice"]
    issues = []
    seen_stems = set()
    seen_match_concepts = {}
    seen_statement_sets = {}
    counts = Counter()
    formats = Counter()
    contextual = Counter()
    answer_positions = Counter()
    for index, question in enumerate(practice):
        tags = []
        key = (question.get("topic"), question.get("batch"))
        counts[key] += 1
        formats[(key, question.get("question_format"))] += 1
        contextual[key] += int(bool(question.get("contextual")))
        answer_positions[(key, question.get("correct_option"))] += 1
        stem = normalize_text(question.get("question_en") or "")
        if not stem or stem in seen_stems:
            tags.append("duplicate_or_empty_stem")
        seen_stems.add(stem)
        if stem in pyq_stems:
            tags.append("copied_pyq_stem")
        if question.get("difficulty") != "Medium":
            tags.append("difficulty_not_medium")
        options = question.get("options") or []
        if [option.get("key") for option in options] != list("ABCDE"):
            tags.append("bad_options")
        elif any(
            not str(option.get(field) or "").strip()
            for option in options
            for field in ("text_en", "text_ta")
        ):
            tags.append("incomplete_bilingual_options")
        elif (
            options[4].get("text_en") != "Answer not known"
            or options[4].get("text_ta") != "விடை தெரியவில்லை"
        ):
            tags.append("bad_option_e")
        if question.get("correct_option") not in "ABCD":
            tags.append("bad_correct")
        if (
            not str(question.get("question_en") or "").strip()
            or not has_tamil(question.get("question_ta") or "")
        ):
            tags.append("incomplete_bilingual_stem")
        if (
            not str(question.get("explanation") or "").strip()
            or not has_tamil(question.get("explanation_ta") or "")
        ):
            tags.append("incomplete_bilingual_explanation")
        if question.get("source_fact") not in valid_facts_by_topic.get(
            question.get("topic"), set()
        ):
            tags.append("ungrounded_source_fact")
        if question.get("orientation") != "Physics PYQ":
            tags.append("missing_pyq_orientation")
        question_format = question.get("question_format")
        if question_format == "statement" and not re.search(
            r"\b(which|identify|select)\b", question.get("question_en") or "", re.I
        ):
            tags.append("incomplete_statement_prompt")
        if question_format == "statement":
            statement_items = numbered_items(question.get("question_en") or "")
            if not 2 <= len(statement_items) <= 4:
                tags.append("statements_missing")
            statement_concept = tuple(statement_items)
            if statement_concept and statement_concept in seen_statement_sets:
                tags.append("duplicate_statement_concept")
            elif statement_concept:
                seen_statement_sets[statement_concept] = index
        if question_format == "match":
            left_match = re.search(
                r"match-col-left'>(.*?)</div>",
                question.get("question_en") or "",
                re.I | re.S,
            )
            right_match = re.search(
                r"match-col-right'>(.*?)</div>",
                question.get("question_en") or "",
                re.I | re.S,
            )
            if not left_match or not right_match:
                tags.append("invalid_match_layout")
            else:
                left_items = [
                    normalize_text(re.sub(r"^[a-d]\)\s*", "", item))
                    for item in left_match.group(1).split("<br>")
                ]
                right_items = [
                    normalize_text(re.sub(r"^[1-4]\.\s*", "", item))
                    for item in right_match.group(1).split("<br>")
                ]
                if (
                    len(left_items) != 4
                    or len(right_items) != 4
                    or len(set(left_items)) != 4
                    or len(set(right_items)) != 4
                ):
                    tags.append("non_unique_4x4_match")
                match_concept = (
                    tuple(sorted(left_items)),
                    tuple(sorted(right_items)),
                )
                if match_concept in seen_match_concepts:
                    tags.append("duplicate_match_concept")
                else:
                    seen_match_concepts[match_concept] = index
                content_options = options[:4]
                parsed_codes = [
                    parse_match_code(option.get("text_en") or "")
                    for option in content_options
                ]
                if any(code is None for code in parsed_codes):
                    tags.append("invalid_match_option_code")
                elif len(
                    {
                        tuple(sorted(code.items()))
                        for code in parsed_codes
                        if code is not None
                    }
                ) != 4:
                    tags.append("duplicate_match_option_code")
                correct_index = "ABCD".find(question.get("correct_option") or "")
                if (
                    correct_index < 0
                    or correct_index >= len(parsed_codes)
                    or parsed_codes[correct_index] is None
                ):
                    tags.append("invalid_correct_match_code")
        if tags:
            issues.append(
                {
                    "index": index,
                    "topic": question.get("topic"),
                    "batch": question.get("batch"),
                    "question_en": (question.get("question_en") or "")[:120],
                    "tags": tags,
                }
            )

    batch_issues = []
    expected_topics = sorted(
        {
            question.get("topic")
            for question in practice
            if question.get("topic")
        }
    )
    actual_keys = set(counts)
    expected_keys = set()
    for topic in expected_topics:
        planned = expected_batches_for_topic(topic, facts_db)
        if topic == in_progress_topic:
            expected_keys.update(
                key for key in actual_keys if key[0] == in_progress_topic
            )
        else:
            expected_keys.update((topic, batch_name) for batch_name in planned)
    expected_practice_total = BATCH_SIZE * len(expected_keys)
    if not expected_topics:
        batch_issues.append({"issue": "no_practice_topics"})
    if len(practice) != expected_practice_total:
        batch_issues.append(
            {
                "practice_total": len(practice),
                "expected": expected_practice_total,
                "issue": "unexpected_practice_total",
            }
        )
    for missing_key in sorted(expected_keys - actual_keys):
        batch_issues.append(
            {
                "topic": missing_key[0],
                "batch": missing_key[1],
                "issue": "missing_expected_batch",
            }
        )
    for unexpected_key in sorted(actual_keys - expected_keys):
        batch_issues.append(
            {
                "topic": unexpected_key[0],
                "batch": unexpected_key[1],
                "issue": "unexpected_practice_batch",
            }
        )
    for key in sorted(expected_keys | actual_keys):
        count = counts[key]
        expected_formats = {
            name: formats[(key, name)] for name in FORMAT_TARGETS
        }
        if count != BATCH_SIZE or expected_formats != FORMAT_TARGETS:
            batch_issues.append(
                {
                    "topic": key[0],
                    "batch": key[1],
                    "count": count,
                    "formats": expected_formats,
                }
            )
        if formats[(key, "paragraph")] < 4:
            batch_issues.append(
                {
                    "topic": key[0],
                    "batch": key[1],
                    "paragraph_count": formats[(key, "paragraph")],
                    "issue": "fewer_than_4_paragraph",
                }
            )
        if contextual[key] < 4:
            batch_issues.append(
                {
                    "topic": key[0],
                    "batch": key[1],
                    "contextual_count": contextual[key],
                    "issue": "fewer_than_4_contextual",
                }
            )
        distribution = {
            answer: answer_positions[(key, answer)] for answer in "ABCD"
        }
        if min(distribution.values()) < 4 or max(distribution.values()) > 8:
            batch_issues.append(
                {
                    "topic": key[0],
                    "batch": key[1],
                    "answer_distribution": distribution,
                    "issue": "imbalanced_answer_positions",
                }
            )

    report = {
        "practice_total": len(practice),
        "hard_issue_count": len(issues) + len(batch_issues),
        "question_issues": issues,
        "batch_issues": batch_issues,
        "batch_counts": {
            f"{topic} / {batch}": count
            for (topic, batch), count in sorted(counts.items())
        },
        "format_counts": {
            f"{topic} / {batch}": {
                name: formats[((topic, batch), name)] for name in FORMAT_TARGETS
            }
            for topic, batch in sorted(counts)
        },
        "contextual_counts": {
            f"{topic} / {batch}": contextual[(topic, batch)]
            for topic, batch in sorted(counts)
        },
        "answer_distributions": {
            f"{topic} / {batch}": {
                answer: answer_positions[((topic, batch), answer)]
                for answer in "ABCD"
            }
            for topic, batch in sorted(counts)
        },
    }
    with open(QC_PATH, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
    print(
        f"QC: practice={len(practice)} | hard issues={report['hard_issue_count']}"
    )
    print(f"Batch counts: {report['batch_counts']}")
    print(f"Format counts: {report['format_counts']}")
    print(f"Contextual: {report['contextual_counts']}")
    print(f"Report: {QC_PATH}")
    return report


def ingest_candidates(
    raw: list,
    topic: str,
    by_batch: dict[int, list],
    fact_lookup: dict[str, str],
    exclusions: list[str],
    excluded_source_facts: set[str],
    existing_source_formats: dict[str, set[str]],
    rejection_counts: Counter,
    session_grounded: set[str] | None = None,
) -> None:
    active_excluded = (
        excluded_source_facts | session_grounded
        if session_grounded is not None
        else excluded_source_facts
    )
    for item in sorted(raw, key=lambda value: int(value.get("batch") or 0)):
        try:
            batch_num = int(item.get("batch") or 0)
        except (TypeError, ValueError):
            rejection_counts["bad_batch"] += 1
            continue
        if batch_num not in by_batch:
            rejection_counts["bad_batch"] += 1
            continue
        candidate_exclusions = exclusions + [
            q["question_en"] for batch in by_batch.values() for q in batch
        ]
        question, reason = normalize_candidate(
            item,
            topic,
            batch_num,
            fact_lookup,
            candidate_exclusions,
            active_excluded,
            {q["source_fact"] for q in by_batch[batch_num]},
            existing_source_formats,
        )
        if question:
            by_batch[batch_num].append(question)
            active_excluded.add(question["source_fact"])
            if session_grounded is not None:
                session_grounded.add(question["source_fact"])
            else:
                excluded_source_facts.add(question["source_fact"])
            existing_source_formats.setdefault(
                question["source_fact"], set()
            ).add(question["question_format"])
        else:
            rejection_counts[reason or "rejected"] += 1


def facts_for_batch(facts: list, batch_num: int, batch_count: int) -> list:
    chunk = (len(facts) + batch_count - 1) // batch_count
    start = (batch_num - 1) * chunk
    return facts[start : start + chunk]


def generate_batch_once(
    topic: str,
    batch_num: int,
    batch_count: int,
    facts: list,
    pyqs: list,
    exclusions: list[str],
    excluded_source_facts: set[str],
    existing_source_formats: dict[str, set[str]],
    fact_lookup: dict[str, str],
    rejection_counts: Counter,
) -> list:
    """Exactly one Gemini call per batch — no top-up loop."""
    by_batch: dict[int, list] = {batch_num: []}
    batch_facts = [
        fact
        for fact in facts_for_batch(facts, batch_num, batch_count)
        if fact["fact_en"] not in excluded_source_facts
    ]
    prompt = single_batch_prompt(
        topic,
        batch_num,
        batch_facts,
        pyqs,
        exclusions[-40:],
        excluded_source_facts,
        buffer=SINGLE_PASS_BUFFER_PER_BATCH,
    )
    requested = BATCH_SIZE + SINGLE_PASS_BUFFER_PER_BATCH
    print(
        f"Batch {batch_num}: 1 API call | facts={len(batch_facts)} | "
        f"request={requested} | prompt={len(prompt)} chars",
        flush=True,
    )
    started = time.time()
    raw = post_gemini(prompt, timeout=API_TIMEOUT_SECONDS)
    elapsed = time.time() - started
    print(
        f"Batch {batch_num}: {len(raw)} candidates in {elapsed:.1f}s",
        flush=True,
    )
    ingest_candidates(
        raw,
        topic,
        by_batch,
        fact_lookup,
        exclusions,
        excluded_source_facts,
        existing_source_formats,
        rejection_counts,
    )
    selected, shortages = select_batch(by_batch[batch_num])
    if shortages or len(selected) != BATCH_SIZE:
        raise SystemExit(
            f"Batch {batch_num} failed after 1 call ({elapsed:.1f}s): "
            f"valid={len(by_batch[batch_num])}, selected={len(selected)}, "
            f"shortages={shortages}, rejected={dict(rejection_counts)}"
        )
    if sum(bool(q.get("contextual")) for q in selected) < 4:
        raise SystemExit(f"Batch {batch_num}: fewer than 4 contextual questions")
    balance_correct_positions(selected)
    return selected


def generate_all_batches(topic: str):
    facts_db = load_json(FACTS_PATH, {})
    facts = facts_db.get(topic) or []
    planned_batches = topic_batch_plan(len(facts))
    database = load_json(DB_PATH, [])
    pyqs = [q for q in database if q.get("type") == "pyq"]
    if not pyqs:
        raise SystemExit("Physics PYQ orientation bank is empty")

    existing_practice = [
        q
        for q in database
        if q.get("type") == "practice" and q.get("topic") != topic
    ]
    exclusions = [q.get("question_en") or "" for q in existing_practice]
    fact_lookup = {
        normalize_text(fact["fact_en"]): fact["fact_en"] for fact in facts
    }
    excluded_source_facts: set[str] = set()
    existing_source_formats: dict[str, set[str]] = {}
    rejection_counts = Counter()
    pending_saves: dict[int, list] = {}

    batch_count = len(planned_batches)
    print(
        f"All-batches: {topic} | {len(facts)} facts | "
        f"{batch_count} batches | exactly {batch_count} API calls",
        flush=True,
    )
    run_started = time.time()

    for batch_name in planned_batches:
        batch_num = int(batch_name.split()[-1])
        pending_saves[batch_num] = generate_batch_once(
            topic,
            batch_num,
            batch_count,
            facts,
            pyqs,
            exclusions,
            excluded_source_facts,
            existing_source_formats,
            fact_lookup,
            rejection_counts,
        )
        for question in pending_saves[batch_num]:
            excluded_source_facts.add(question["source_fact"])
        exclusions.extend(q["question_en"] for q in pending_saves[batch_num])

    for batch_num, selected in pending_saves.items():
        save_batch(topic, batch_num, selected)
        print(
            f"Saved {len(selected)} questions for {topic} Batch {batch_num}. "
            f"Formats={dict(Counter(q['question_format'] for q in selected))}; "
            f"contextual={sum(bool(q.get('contextual')) for q in selected)}",
            flush=True,
        )

    print(
        f"Done in {time.time() - run_started:.1f}s | "
        f"rejected={dict(rejection_counts)}",
        flush=True,
    )
    report = run_qc(in_progress_topic=topic)
    if report["hard_issue_count"]:
        raise SystemExit("Post-save QC failed")


def generate(topic: str, batch_num: int):
    facts_db = load_json(FACTS_PATH, {})
    facts = facts_db.get(topic) or []
    planned_batches = topic_batch_plan(len(facts))
    database = load_json(DB_PATH, [])
    pyqs = [q for q in database if q.get("type") == "pyq"]
    batch_name = f"Batch {batch_num}"
    if batch_name not in planned_batches:
        raise SystemExit(
            f"{topic} supports {len(planned_batches)} batch(es) from "
            f"{len(facts)} facts; requested {batch_name}"
        )
    if not pyqs:
        raise SystemExit("Physics PYQ orientation bank is empty")

    existing_practice = [
        q
        for q in database
        if q.get("type") == "practice"
        and not (
            q.get("topic") == topic
            and q.get("batch") == f"Batch {batch_num}"
        )
    ]
    exclusions = [q.get("question_en") or "" for q in existing_practice]
    # Use each grounding fact only once across this topic's practice bank.
    # This is stricter than the guide's allowance for distinct reasoning and
    # prevents semantic paraphrase duplicates deterministically.
    excluded_source_facts = {
        q.get("source_fact")
        for q in existing_practice
        if q.get("topic") == topic and q.get("source_fact")
    }
    existing_source_formats: dict[str, set[str]] = {}
    for question in existing_practice:
        if question.get("topic") != topic or not question.get("source_fact"):
            continue
        existing_source_formats.setdefault(question["source_fact"], set()).add(
            question.get("question_format") or ""
        )
    fact_lookup = {
        normalize_text(fact["fact_en"]): fact["fact_en"] for fact in facts
    }
    candidates = []
    rejection_counts = Counter()

    for attempt in range(1, 26):
        selected, shortages = select_batch(candidates)
        if not shortages and len(selected) == BATCH_SIZE:
            break
        active_excluded = excluded_source_facts | {
            q["source_fact"] for q in candidates
        }
        available_facts = [
            fact for fact in facts if fact["fact_en"] not in active_excluded
        ]
        if not available_facts:
            break
        shortage_note = ""
        requested = GEN_TOTAL if attempt == 1 else max(12, sum(shortages.values()) + 8)
        if shortages:
            shortage_note = (
                "PRIORITIZE THESE CURRENT SHORTAGES: "
                + ", ".join(f"{name}={count}" for name, count in shortages.items())
            )
        print(
            f"Generation attempt {attempt}: request {requested}; "
            f"current valid={len(candidates)}; shortages={shortages}; "
            f"available_facts={len(available_facts)}"
        )
        raw = post_gemini(
            generation_prompt(
                topic,
                batch_num,
                available_facts,
                pyqs,
                exclusions + [q["question_en"] for q in candidates],
                active_excluded,
                requested,
                shortage_note,
            )
        )
        print(f"  Received {len(raw)} candidates")
        candidate_exclusions = exclusions + [q["question_en"] for q in candidates]
        for item in raw:
            question, reason = normalize_candidate(
                item,
                topic,
                batch_num,
                fact_lookup,
                candidate_exclusions,
                active_excluded,
                {q["source_fact"] for q in candidates},
                existing_source_formats,
            )
            if question:
                candidates.append(question)
                candidate_exclusions.append(question["question_en"])
            else:
                rejection_counts[reason] += 1

    selected, shortages = select_batch(candidates)
    if shortages or len(selected) != BATCH_SIZE:
        raise SystemExit(
            f"Could not build complete batch; valid={len(candidates)}, "
            f"shortages={shortages}, rejected={dict(rejection_counts)}"
        )
    if sum(bool(q.get("contextual")) for q in selected) < 4:
        raise SystemExit("Selected batch has fewer than 4 contextual questions")

    balance_correct_positions(selected)
    save_batch(topic, batch_num, selected)
    print(
        f"Saved {len(selected)} questions for {topic} Batch {batch_num}. "
        f"Formats={dict(Counter(q['question_format'] for q in selected))}; "
        f"contextual={sum(bool(q.get('contextual')) for q in selected)}"
    )
    print(f"Rejected candidates: {dict(rejection_counts)}")
    report = run_qc(in_progress_topic=topic)
    if report["hard_issue_count"]:
        raise SystemExit("Post-save QC failed")


def main():
    parser = argparse.ArgumentParser(description="Generate Physics practice batches")
    parser.add_argument("--topic")
    parser.add_argument("--batch", type=int)
    parser.add_argument(
        "--all-batches",
        action="store_true",
        help="Generate every planned batch for the topic in one LLM call",
    )
    parser.add_argument("--qc-only", action="store_true")
    parser.add_argument("--reset-topic-practice", action="store_true")
    args = parser.parse_args()

    if args.qc_only:
        report = run_qc()
        if report["hard_issue_count"]:
            sys.exit(1)
        return
    if not args.topic:
        raise SystemExit("--topic is required")
    if args.all_batches and args.batch:
        raise SystemExit("Use either --all-batches or --batch, not both")
    if not args.all_batches and args.batch not in (1, 2, 3):
        raise SystemExit("Use --all-batches or --batch 1|2|3")

    facts_db = load_json(FACTS_PATH, {})
    planned = expected_batches_for_topic(args.topic, facts_db)
    if args.reset_topic_practice:
        reset_topic_practice(args.topic)
    print(f"Model: {MODEL} | key pool: {len(KEY_POOL)} (gemini_keys())")

    if args.all_batches:
        generate_all_batches(args.topic)
    else:
        if f"Batch {args.batch}" not in planned:
            raise SystemExit(
                f"{args.topic} supports {len(planned)} batch(es) from "
                f"{len(facts_db.get(args.topic) or [])} facts; "
                f"planned: {', '.join(planned)}"
            )
        if args.reset_topic_practice and args.batch != 1:
            raise SystemExit(
                "--reset-topic-practice with --batch requires --batch 1; "
                "prefer --all-batches --reset-topic-practice instead"
            )
        generate(args.topic, args.batch)

    if _rate_limit_hits:
        print(f"Rate-limit/service retry count: {_rate_limit_hits}")


if __name__ == "__main__":
    main()
