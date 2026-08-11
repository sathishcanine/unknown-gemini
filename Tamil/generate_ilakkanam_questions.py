#!/usr/bin/env python3
"""
Generate TNPSC Ilakkanam practice batches from topic packs in ilakkanam_notes.json.

Usage:
  python3 Tamil/generate_ilakkanam_questions.py --topic pirithu_sertthu --batch 1
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

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTES_PATH = os.path.join(BASE_DIR, "Tamil", "ilakkanam_notes.json")
TOPICS_PATH = os.path.join(BASE_DIR, "Tamil", "ilakkanam_topics.json")
DB_PATH = os.path.join(BASE_DIR, "Tamil", "ilakkanam_questions_db.json")

MODEL = "gemini-3.5-flash-lite"
EXAMPLE_SAMPLE = 100  # per API call (full pool still considered across attempts)


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def topic_meta(topic_id: str) -> dict:
    topics = load_json(TOPICS_PATH, {})
    for t in topics.get("topics", []):
        if t.get("id") == topic_id:
            return t
    return {"id": topic_id, "name_ta": topic_id, "name_en": topic_id}


def normalize_q(text: str) -> str:
    return re.sub(r"\s+", "", (text or "")).lower()


def format_ground_truth(rules, examples):
    lines = ["RULES:"]
    for i, r in enumerate(rules, 1):
        ta = (r.get("rule_ta") or "").strip()
        en = (r.get("rule_en") or "").strip()
        page = r.get("source_page")
        extra = f" (SM p.{page})" if page is not None else ""
        if en:
            lines.append(f"R{i}.{extra} {ta} | EN: {en}")
        else:
            lines.append(f"R{i}.{extra} {ta}")

    lines.append("\nEXAMPLES (input → output):")
    for i, e in enumerate(examples, 1):
        inp = (e.get("input") or "").strip()
        out = (e.get("output") or "").strip()
        kind = e.get("kind") or "other"
        note = (e.get("note_ta") or "").strip()
        page = e.get("source_page")
        note_bit = f" [{note}]" if note else ""
        page_bit = f" (SM p.{page})" if page is not None else ""
        lines.append(f"E{i}.{page_bit} [{kind}] {inp} → {out}{note_bit}")
    return "\n".join(lines)


def call_gemini(topic_ta, topic_en, batch_num, rules, examples, exclusion_texts, api_key):
    # Full rules always; sample examples for context size
    sampled_examples = examples
    if len(examples) > EXAMPLE_SAMPLE:
        sampled_examples = random.sample(examples, EXAMPLE_SAMPLE)

    ground = format_ground_truth(rules, sampled_examples)
    exclusions = ""
    if exclusion_texts:
        exclusions = (
            "\nEXCLUDED STEMS (do not repeat / paraphrase closely):\n"
            + "\n".join(f"- {t}" for t in exclusion_texts[:80])
        )

    # Topic-specific preferred question shapes
    if "sandhi" in topic_en.lower() or "சந்தி" in topic_ta or "ஒற்று" in topic_ta:
        shapes = """5. Preferred shapes for this topic (mix across the 17):
   - Identify சந்திப்பிழை in a word/sentence (choose the erroneous form)
   - Identify ஒற்றுப்பிழை (missing/extra consonant doubling)
   - Choose the CORRECT sandhi/join form among close distractors
   - Spot which option has NO error
   - Short rule MCQ on சந்தி / ஒற்று (1–2 statements)
   - Optional: 1 match-the-following (4x4) using HTML:
     Match the following:<br><div class='match-container'><div class='match-col-left'>a) ...<br>b) ...<br>c) ...<br>d) ...</div><div class='match-col-right'>1. ...<br>2. ...<br>3. ...<br>4. ...</div></div>
6. Distractors must be plausible wrong sandhi/otru forms (wrong உடம்படுமெய், wrong doubling, wrong deletion)."""
    elif "kuril" in topic_en.lower() or "குறில்" in topic_ta or "நெடில்" in topic_ta:
        shapes = """5. Preferred shapes for this topic (mix across the 17):
   - Identify whether a vowel/letter is குறில் or நெடில்
   - Choose the word with குறில் / நெடில் as asked
   - Spot the odd one (குறில் vs நெடில் mix-up)
   - Meaning change when குறில்↔நெடில் changes (if in notes)
   - Short rule MCQ on குறில்–நெடில் distinction
6. Distractors must be close lookalike vowels/words (அ/ஆ, இ/ஈ, உ/ஊ, எ/ஏ, ஒ/ஓ)."""
    elif (
        "la_na_ra" in topic_en.lower()
        or "லகர" in topic_ta
        or "ளகர" in topic_ta
        or "னகர" in topic_ta
        or "ரகர" in topic_ta
    ):
        shapes = """5. Preferred shapes for this topic (mix across the 17):
   - Meaning difference for lookalike pairs (ல/ள/ழ, ன/ண, ர/ற) from SM examples
   - Choose the correct spelling for a given meaning (e.g. நெருப்பு → அனல் not அணல்)
   - Identify which letter pair / rule applies (டக்கு முன் ண; றக்கு முன் ன)
   - Spot the odd / wrong letter in a word among close distractors
   - Short rule MCQ on மயங்கொலி எழுத்துக்கள் (ண ன ந ல ள ழ ர ற)
   - Optional: 1 match-the-following (4x4) using HTML match-container
6. Distractors must be close lookalike spellings that swap ல↔ள↔ழ, ன↔ண, ர↔ற.
   Do NOT invent pairs not in SM notes. Pure Tamil in question_ta/options_ta (no Latin)."""
    elif "இனவெழுத்து" in topic_ta or "இன எழுத்து" in topic_ta or "cognate" in topic_en.lower():
        shapes = """5. Preferred shapes for this topic (mix across the 17):
   - Identify இன எழுத்து pairs: வல்லினம்↔மெல்லினம் (க்-ங், ச்-ஞ், ட்-ண், த்-ந், ப்-ம், ற்-ன்)
   - Choose correct cognate letter for a given letter (e.g. ட் → ண்)
   - Fix wrong இன letter in a word (கன்தம் → கண்டம்)
   - உயிர் இனம்: குறில்↔நெடில்; ஐ→இ; ஔ→உ; ஆய்தத்துக்கு இனம் இல்லை
   - Spot words where மெல்லினம் is followed by its வல்லின இனம் (திங்கள், மஞ்சள், அம்பு…)
   - Short rule MCQ on definition of இனவெழுத்து / இடையினம் ஆறும் ஒரே இனம்
6. Distractors = wrong cognate pairs. Pure Tamil only (no Latin/SM branding). Use ONLY notes."""
    elif "சுட்டு" in topic_ta or "demonstrative" in topic_en.lower():
        shapes = """5. Preferred shapes for this topic (mix across the 17):
   - Identify சுட்டு எழுத்துக்கள்: அ, இ, உ (மூன்று)
   - சேய்மைச்சுட்டு (அ) vs அண்மைச்சுட்டு (இ); உ = இடையில்/பழைய பயன்பாடு
   - அகச்சுட்டு vs புறச்சுட்டு (நீக்கினால் பொருள் தருமா?)
   - சுட்டுத்திரிபு: அ/இ → அந்த/இந்த; இப்பள்ளி → இந்தப்பள்ளி
   - Classify examples: அவன்/இவன், அவ்வீடு/இம்மலை, உம்பர் etc.
   - Optional: வல்லினம் மிகுதல் after அ/இ or அந்த/இந்த (அச்சட்டை, இந்தக்காலம்)
6. Distractors = mix-ups of அண்மை/சேய்மை or அக/புற. Pure Tamil only. Use ONLY notes."""
    elif "வினா எழுத்து" in topic_ta or "வினாஎழுத்து" in topic_ta or "interrogative" in topic_en.lower():
        shapes = """5. Preferred shapes for this topic (mix across the 17):
   - Identify வினா எழுத்துக்கள்: எ, யா, ஆ, ஓ, ஏ (ஐந்து) and position rules (முதல்/இறுதி)
   - அகவினா vs புறவினா (நீக்கினால் பொருள் தருமா?) — எது/யார் vs அவனா?/வருவானோ?
   - ஏ = வினா + தேற்றம்/அழுத்தம் (அவனே செய்தான்)
   - வினா வகைகள் (6): அறியா, ஐய, கொளல், கொடை, ஏவல் (+ அறிவு if in notes)
   - விடை வகைகள் (8): சுட்டு/மறை/நேர்/ஏவல்/வினாஎதிர்வினா/உற்றது உரைத்தல்/உறுவது கூறல்/இனமொழி; வெளிப்படை vs குறிப்பு
   - Match example dialogue → correct வினா/விடை type
6. Distractors = mix-ups of வினா/விடை types. Pure Tamil only. Use ONLY notes."""
    elif (
        "ஒருமை" in topic_ta
        or "பன்மை" in topic_ta
        or "singular" in topic_en.lower()
        or "plural" in topic_en.lower()
    ):
        shapes = """5. Preferred shapes for this topic (mix across the 17):
   - Fix ஒருமை–பன்மை agreement error in a sentence (choose corrected form)
   - Choose the பிழையற்ற தொடர் among close distractors
   - Identify ஒருமை vs பன்மை for nouns (கள்) and verb agreement (விரிந்தது/விரிந்தன)
   - அன்று (ஒருமை) vs அல்ல (பன்மை) usage
   - தான்/தன்னை/தனக்கு/தனது (ஒருமை) vs தாம்/தம்மை/தமக்கு/தமது (பன்மை); மரியாதை பன்மை
   - Convert ஒருமை↔பன்மை for SM pairs (கல்–கற்கள், மரம்–மரங்கள், நான்–நாங்கள்…)
   - Short rule MCQ + optional 1 match-the-following (4x4) HTML match-container
6. Distractors = wrong number agreement / wrong pronoun form. Pure Tamil only. Use ONLY notes."""
    elif (
        "வேர்ச்சொல் அறிதல்" in topic_ta
        or topic_en.lower().strip() in ("root words", "root word", "roots")
    ):
        shapes = """5. Preferred shapes for this topic (mix across the 17):
   - Identify the வேர்ச்சொல் (root) of a given conjugated/derived word
   - Choose the correct root among close distractors (wrong truncation / wrong stem)
   - Spot which option is NOT a வேர்ச்சொல் / which IS the root
   - Short rule MCQ: வேர்ச்சொல் = அடிப்பகுதி; பெரும்பாலும் ஏவல் வினை
   - Optional: 1 match-the-following (word → root) using HTML match-container
6. Distractors = nearby wrong roots (extra/missing letters, tense/person endings kept).
   Use ONLY notes examples. Pure Tamil only. NO SM branding / Latin in question_ta."""
    elif (
        "வினைமுற்று" in topic_ta
        or "வினையெச்சம்" in topic_ta
        or "பெயரெச்சம்" in topic_ta
        or "வினையாலணையும்" in topic_ta
        or "தொழிற்பெயர்" in topic_ta
        or "participle" in topic_en.lower()
        or "finite verb" in topic_en.lower()
    ):
        shapes = """5. Preferred shapes for this topic (mix across the 17):
   - Classify a given form: வினைமுற்று / வினையெச்சம் / பெயரெச்சம் / வினையாலணையும் பெயர் / தொழிற்பெயர்
   - தெரிநிலை vs குறிப்பு (வினைமுற்று / வினையெச்சம் / பெயரெச்சம்)
   - ஏவல் வினைமுற்று (ஒருமை/பன்மை) and வியங்கோள் வினைமுற்று (க, இய, இயர், அல்)
   - Convert: வேர்ச்சொல் → correct derived form; பெயரெச்சம் ↔ வினைமுற்று (from SM examples)
   - முற்றெச்சம் / வினைமுற்றுத் தொடர் identification
   - தொழிற்பெயர் vs வினையாலணையும் பெயர் distinction
   - Short rule MCQ + optional 1 match-the-following (form → type) HTML match-container
6. Distractors = nearby wrong verb/participle types. Pure Tamil only. Use ONLY notes. NO SM branding."""
    elif (
        "அயற்சொல்" in topic_ta
        or "தமிழ்ச்சொல்" in topic_ta
        or "loan" in topic_en.lower()
        or "பிறமொழி" in topic_ta
    ):
        shapes = """5. Preferred shapes for this topic (mix across the 17):
   - ஆங்கிலச் / பிறமொழிச் சொல்லுக்கு நேரான தமிழ்ச்சொல் (loan → Tamil)
   - தூய தமிழ்ச்சொல்லைக் கண்டறிக among options that include loan/Sanskritised forms
   - பிறமொழிக் கலப்பற்ற தொடர் / வாக்கியம் (choose pure-Tamil sentence)
   - பிறமொழிச் சொற்களை நீக்கிச் சரியான தமிழ் வடிவம்
   - Short rule MCQ: அயற்சொல் / திசைச்சொல் / வடசொல் / தற்சமம் / தற்பவம் (from notes only)
   - Optional: 1 match-the-following (loan → Tamil) using HTML match-container
6. Distractors = nearby wrong Tamil glosses or mixed foreign words. Use ONLY notes pairs.
   Pure Tamil in question_ta/options_ta except when the stem itself quotes an English loan.
   NO SM branding / academy ads."""
    elif (
        "எதிர்ச்சொல்" in topic_ta
        or "antonym" in topic_en.lower()
    ):
        shapes = """5. Preferred shapes for this topic (mix across the 17):
   - Direct: given word → choose correct எதிர்ச்சொல் (antonym)
   - Reverse: given antonym pair direction (A→? or ?→B) from notes
   - Spot which option is NOT an antonym / odd-one among pairs
   - Short classical/literary word antonym (from notes only: மேதை↔பேதை, மிசை, etc.)
   - Optional: 1 match-the-following (word → antonym) using HTML match-container
6. Distractors = near-synonyms, related words, or reverse-direction traps — NOT random.
   Use ONLY notes pairs. Pure Tamil only. NO SM branding / Latin / rule codes (R#/E#)."""
    elif (
        "வேறுபாடு" in topic_ta
        or "இரண்டு வினை" in topic_ta
        or "difference between two verb" in topic_en.lower()
    ):
        shapes = """5. Preferred shapes for this topic (mix across the 17):
   - Given a verb pair (A–B), choose the correct meaning contrast from SM notes
   - Fill the blank / choose correct verb in a short sentence (விரிந்து vs விரித்து, etc.)
   - Identify which statement correctly explains the difference
   - Spot lookalike pairs that differ by one letter/sound (உரி/உறி, விலை/விளை…)
   - Short rule MCQ: தன்வினை vs பிறவினை / நிகழ்ச்சி vs செயற்படுத்துதல்
   - Optional: 1 match-the-following (pair → meaning) HTML match-container
6. Distractors = swapped meanings, near-synonyms, or wrong member of the pair.
   Use ONLY notes pairs. Pure Tamil only. NO SM branding / Latin / rule codes (R#/E#)."""
    elif (
        "வினைச்சொல்" in topic_ta
        or topic_en.lower().strip() in ("verbs", "verb", "vinaichol")
    ):
        shapes = """5. Preferred shapes for this topic (mix across the 17):
   - Identify/classify: வினைச்சொல் / வினைமுற்று / வினையெச்சம் / பெயரெச்சம் / முற்றெச்சம்
   - தெரிநிலை vs குறிப்பு (வினைமுற்று / பெயரெச்சம் / வினையெச்சம்)
   - ஏவல் வினைமுற்று (ஒருமை/பன்மை) vs வியங்கோள் வினைமுற்று (க, இய, இயர், அல்)
   - Pick correct example for a given type from SM notes
   - Short rule MCQ on definitions / விகுதிகள்
   - Optional: 1 match-the-following (form/example → type) HTML match-container
6. Distractors = nearby wrong verb/participle types. Use ONLY notes.
   Pure Tamil only. NO SM branding / Latin / rule codes (R#/E#).
   Focus on CLASSIFICATION (not root→derivative transforms — that is a different topic)."""
    else:
        shapes = """5. Preferred shapes for this topic (mix across the 17):
   - பிரித்து எழுதுக (split the joined word)
   - சேர்த்து எழுதுக (join with correct உடம்படுமெய் / புணர்ச்சி)
   - Choose the correct split among close distractors
   - Spot the wrong split / wrong join
   - Short statement (1–2) about a புணர்ச்சி rule → which is correct
   - Optional: 1 match-the-following (4x4) using HTML:
     Match the following:<br><div class='match-container'><div class='match-col-left'>a) ...<br>b) ...<br>c) ...<br>d) ...</div><div class='match-col-right'>1. ...<br>2. ...<br>3. ...<br>4. ...</div></div>
6. Distractors must be plausible wrong splits/joins (wrong உடம்படுமெய் ய்/வ், wrong word boundary, nearby lookalikes)."""

    prompt = f"""
You are a senior TNPSC General Tamil (பொதுத் தமிழ்) exam compiler for Unit 1 இலக்கணம்.
Topic: "{topic_ta}" ({topic_en})
Generate exactly 17 practice MCQs for Practice Batch {batch_num}.

GROUND TRUTH (SM Academy notes — rules + examples). Use ONLY this material:
{ground}
{exclusions}

Generation rules:
1. Base every answer on the ground truth. Prefer authentic SM examples; you may lightly rephrase
   stems but answers must match the notes.
2. Do NOT copy previous-year question stems verbatim from memory or common PYQ banks.
3. Tamil-first: question_ta must be exam-natural Tamil. question_en is a clear English gloss.
4. Do NOT force Medium/Hard split. Focus on clean TNPSC-style Ilakkanam items.
   You may omit difficulty, or set "difficulty": "medium" for all.
{shapes}
7. Each object keys (JSON array only):
   - question_en, question_ta
   - options_en: exactly 4 strings
   - options_ta: exactly 4 strings (parallel to options_en)
   - answer_en: must equal one of options_en exactly
   - answer_ta: must equal one of options_ta exactly
   - explanation_en, explanation_ta (cite the rule briefly)
   - difficulty: optional; if present use "medium" (Hard not required)
   - source_note: short pointer like "SM rule R3 / example E12"

Option E (Answer not known) will be added by post-processing — do NOT include it in options_en/options_ta.
Escape internal double quotes properly. Return ONLY a JSON array.
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

    retries = 5
    attempt = 0
    rate_limit_attempt = 0
    delay = 10
    while attempt < retries:
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as response:
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
            if e.code == 429:
                rate_limit_attempt += 1
                print(f"    Rate limited (429): {body[:200]}")
                if rate_limit_attempt >= 4:
                    break
                print(f"    Retrying in {delay}s...")
                time.sleep(delay)
                delay = min(delay * 2, 45)
            else:
                attempt += 1
                print(f"    HTTP {e.code}: {body[:200]}")
                time.sleep(5)
        except Exception as e:
            attempt += 1
            print(f"    Error: {e}")
            time.sleep(5)
    return []


def main():
    parser = argparse.ArgumentParser(description="Ilakkanam practice question generator")
    parser.add_argument("--topic", required=True, help="topic id, e.g. pirithu_sertthu")
    parser.add_argument("--batch", type=int, required=True, help="batch number")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not set.")
        sys.exit(1)

    notes = load_json(NOTES_PATH, {})
    block = (notes.get("topics") or {}).get(args.topic)
    if not block:
        print(f"Error: topic '{args.topic}' not in {NOTES_PATH}")
        sys.exit(1)

    rules = block.get("rules") or []
    examples = block.get("examples") or []
    if not rules and not examples:
        print("Error: no SM rules/examples for this topic yet.")
        sys.exit(1)

    meta = topic_meta(args.topic)
    topic_ta = block.get("name_ta") or meta.get("name_ta") or args.topic
    topic_en = meta.get("name_en") or args.topic

    print(f"Topic: {topic_ta} ({args.topic})")
    print(f"Ground truth: {len(rules)} rules, {len(examples)} examples")

    all_db = load_json(DB_PATH, [])
    if not isinstance(all_db, list):
        all_db = []

    existing_topic = [
        q
        for q in all_db
        if q.get("topic") == topic_ta or q.get("topic_id") == args.topic
    ]
    exclusion_texts = []
    for q in existing_topic:
        for key in ("question_ta", "question_en"):
            t = (q.get(key) or "").strip()
            if t:
                exclusion_texts.append(t[:220])

    existing_keys = set()
    for q in all_db:
        existing_keys.add(normalize_q(q.get("question_ta") or ""))
        existing_keys.add(normalize_q(q.get("question_en") or ""))

    print(f"Existing for topic: {len(existing_topic)}; exclusion stems: {len(exclusion_texts)}")

    valid = []
    attempts = 6

    for attempt in range(attempts):
        print(f"Calling Gemini (attempt {attempt + 1}/{attempts})...")
        raw = call_gemini(
            topic_ta, topic_en, args.batch, rules, examples, exclusion_texts, api_key
        )
        print(f"  Received {len(raw)} raw questions")

        for q in raw:
            required = [
                "question_en",
                "question_ta",
                "options_en",
                "options_ta",
                "answer_en",
                "answer_ta",
                "explanation_en",
                "explanation_ta",
            ]
            if not all(k in q for k in required):
                continue
            if not isinstance(q["options_en"], list) or not isinstance(q["options_ta"], list):
                continue
            if len(q["options_en"]) != 4 or len(q["options_ta"]) != 4:
                print("  Discard: options not length 4")
                continue

            ans_en = str(q["answer_en"]).strip()
            ans_ta = str(q["answer_ta"]).strip()
            opts_en = [str(x).strip() for x in q["options_en"]]
            opts_ta = [str(x).strip() for x in q["options_ta"]]
            if ans_en not in opts_en or ans_ta not in opts_ta:
                print(f"  Discard: answer mismatch — {ans_en[:60]}")
                continue

            # Match layout soft check
            q_en = str(q["question_en"]).strip()
            q_ta = str(q["question_ta"]).strip()
            if "match" in q_en.lower() or "பொருத்து" in q_ta:
                low = q_en.lower()
                has_abcd = all(p in low for p in ["a)", "b)", "c)", "d)"]) or all(
                    p in low for p in ["a.", "b.", "c.", "d."]
                )
                has_1234 = all(p in low for p in ["1.", "2.", "3.", "4."]) or all(
                    p in low for p in ["1)", "2)", "3)", "4)"]
                )
                if not (has_abcd and has_1234):
                    print("  Discard: weak match layout")
                    continue

            combined = len(q_en) + len(q_ta) + len(str(q["explanation_en"])) + len(
                str(q["explanation_ta"])
            )
            if combined < 160:
                print(f"  Discard: too short ({combined})")
                continue

            # Prefer Tamil answer index if both match different indices inconsistently
            idx_en = opts_en.index(ans_en)
            idx_ta = opts_ta.index(ans_ta)
            correct_index = idx_ta if idx_ta == idx_en else idx_ta
            if idx_en != idx_ta:
                # realign: trust Tamil index for Ilakkanam
                correct_index = idx_ta
                ans_en = opts_en[correct_index]

            # Shuffle A–D so models that bias to option A don't cluster keys
            pairs = list(zip(opts_en, opts_ta))
            correct_pair = pairs[correct_index]
            random.shuffle(pairs)
            keys_map = ["A", "B", "C", "D"]
            standard_options = []
            correct_key = "A"
            for i, (en, ta) in enumerate(pairs):
                standard_options.append(
                    {"key": keys_map[i], "text_en": en, "text_ta": ta}
                )
                if (en, ta) == correct_pair:
                    correct_key = keys_map[i]
            standard_options.append(
                {
                    "key": "E",
                    "text_en": "Answer not known",
                    "text_ta": "விடை தெரியவில்லை",
                }
            )

            # Tamil Ilakkanam: no Medium/Hard force — default Medium for schema only
            raw_diff = str(q.get("difficulty") or "medium").strip().capitalize()
            if raw_diff not in ("Medium", "Hard"):
                raw_diff = "Medium"

            standard_q = {
                "subject": "Tamil",
                "unit": "Ilakkanam",
                "topic": topic_ta,
                "topic_id": args.topic,
                "source_exam": f"Practice Batch {args.batch}",
                "difficulty": raw_diff,
                "question_en": q_en,
                "question_ta": q_ta,
                "options": standard_options,
                "correct_option": correct_key,
                "explanation": str(q["explanation_en"]).strip(),
                "explanation_ta": str(q["explanation_ta"]).strip(),
                "type": "practice",
                "batch": f"Batch {args.batch}",
                "group": "Practice",
                "source_note": str(q.get("source_note") or "").strip(),
            }

            key_ta = normalize_q(standard_q["question_ta"])
            key_en = normalize_q(standard_q["question_en"])
            if key_ta in existing_keys or key_en in existing_keys:
                continue
            if any(
                normalize_q(x["question_ta"]) == key_ta
                or normalize_q(x["question_en"]) == key_en
                for x in valid
            ):
                continue

            valid.append(standard_q)

        print(f"  Accumulated valid={len(valid)}")
        if len(valid) >= 30:
            break
        print("  Sleeping 10s...")
        time.sleep(10)

    if len(valid) < 30:
        print(f"ERROR: need 30 valid; got {len(valid)}")
        sys.exit(1)

    # Prefer richer explanations; no Medium/Hard quota
    valid.sort(
        key=lambda q: len(q["explanation"]) + len(q["explanation_ta"]), reverse=True
    )
    final_batch = valid[:30]
    random.shuffle(final_batch)
    print(f"Selecting 30 questions (no Medium/Hard force)")

    all_db.extend(final_batch)
    save_json(DB_PATH, all_db)
    print(
        f"\nSUCCESS: Added {len(final_batch)} Q → {DB_PATH} "
        f"(topic={topic_ta}, Batch {args.batch}); DB total={len(all_db)}"
    )


if __name__ == "__main__":
    main()
