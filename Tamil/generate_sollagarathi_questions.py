#!/usr/bin/env python3
"""
Generate TNPSC Sollagarathi (Unit 2) practice batches from sollagarathi_notes.json.

Usage:
  python3 Tamil/generate_sollagarathi_questions.py --topic ethirchol_eduthelzhuthal --batch 1
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
NOTES_PATH = os.path.join(BASE_DIR, "Tamil", "sollagarathi_notes.json")
TOPICS_PATH = os.path.join(BASE_DIR, "Tamil", "sollagarathi_topics.json")
DB_PATH = os.path.join(BASE_DIR, "Tamil", "sollagarathi_questions_db.json")

MODELS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite"]
EXAMPLE_SAMPLE = 100


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


def preferred_shapes(topic_id: str, topic_ta: str, topic_en: str) -> str:
    if (
        topic_id == "ethirchol_eduthelzhuthal"
        or "எதிர்ச்சொல்" in topic_ta
        or "antonym" in topic_en.lower()
    ):
        return """5. Preferred shapes for this topic (mix across the 17):
   - Direct: given word → choose correct எதிர்ச்சொல் (antonym)
   - Context sentence: pick antonym of the underlined / quoted word
   - Reverse: given antonym, which word pairs with it
   - Spot which option is NOT the antonym / odd among pairs
   - Optional: 1 match-the-following (4x4) using HTML:
     Match the following:<br><div class='match-container'><div class='match-col-left'>a) ...<br>b) ...<br>c) ...<br>d) ...</div><div class='match-col-right'>1. ...<br>2. ...<br>3. ...<br>4. ...</div></div>
6. Distractors = near-synonyms, related words, or reverse-direction traps — NOT random.
   Use ONLY notes pairs. Pure Tamil only. NO SM branding / Latin / rule codes (R#/E#)."""
    if (
        topic_id == "orezhuthu_orumozhi"
        or "ஓரெழுத்து" in topic_ta
        or "one-letter" in topic_en.lower()
    ):
        return """5. Preferred shapes for this topic (mix across the 17):
   - Meaning → choose the ஓரெழுத்து ஒரு மொழி letter (e.g. சோலை → கா; அரசன் → கோ)
   - Letter → choose a correct meaning from notes (e.g. ஆ → பசு)
   - Rule MCQ: தொல்காப்பியர் நெட்டெழுத்து ஏழு; நன்னூல் 42 (40 + நொ, து); குறில் தனித்து சொல்லாகாது
   - Identify which is / is NOT an ஓரெழுத்து ஒரு மொழி
   - Optional: 1 match-the-following (meaning ↔ letter) HTML match-container
6. Distractors = other one-letter words or wrong meanings from notes — NOT random invention.
   Use ONLY notes. Pure Tamil only. NO SM branding / Latin / rule codes (R#/E#)."""
    if (
        topic_id == "uriya_porul_kandarithal"
        or "உரிய பொருள்" in topic_ta
        or "சொல்லும் பொருளும்" in topic_ta
        or "apt meaning" in topic_en.lower()
    ):
        return """5. Preferred shapes for this topic (mix across the 17):
   - Word → choose the correct பொருள் / meaning from notes
   - Meaning → choose the matching சொல் (reverse)
   - Spot the wrong meaning among close distractors
   - Short literary/classical word meaning (திங்கள், மேதினி, ஆழிப்பெருக்கு…) from notes only
   - Optional: 1 match-the-following (word ↔ meaning) HTML match-container
6. Distractors = nearby wrong meanings from the same notes bank — NOT invented glosses.
   Use ONLY notes pairs. Pure Tamil only. NO SM branding / Latin / rule codes (R#/E#)."""
    if (
        topic_id == "oruporul_pala_sorkal"
        or "ஒருபொருள் தரும் பல" in topic_ta
        or "இணையான வேறு சொல்" in topic_ta
        or "equivalent word" in topic_en.lower()
    ):
        return """5. Preferred shapes for this topic (mix across the 17):
   - Word → choose an இணைச்சொல் / equivalent from the same synonym group (notes only)
   - Given a meaning-group, which word belongs / does NOT belong
   - Pick the correct alternate for classical words (கடல்→ஆழி, உலகம்→ஞாலம், அரசன்→வேந்தன்…)
   - Spot the odd word that is NOT a synonym of the given head word
   - Optional: 1 match-the-following (word ↔ equivalent) HTML match-container
6. Distractors = words from OTHER synonym groups in notes — NOT invented synonyms.
   Use ONLY notes. Pure Tamil only. NO SM branding / Latin / rule codes (R#/E#)."""
    if (
        topic_id == "poruntha_sol_kandarithal"
        or "பொருந்தா சொல்" in topic_ta
        or "odd word" in topic_en.lower()
        or "odd one" in topic_en.lower()
    ):
        return """5. Preferred shapes for this topic (mix across the 17):
   - Classic odd-one-out: 4 words in options A–D; pick the பொருந்தா சொல் (from notes odd_one examples)
   - Set membership: given a known group (அறுசுவை / அகத்திணை / அரசுக்குரிய பத்து…), which does NOT belong
   - Pair mismatch: which இணை / pair is wrong among four pairs
   - Grammar/category odd-one (பெயர்ச்சொல் vs வினை, மாநிலம் vs நாடு, நீர்நிலை vs அல்லாதது)
   - Optional: 1 match-the-following ONLY if it still tests odd-membership (prefer plain MCQ)
6. Distractors = the three words that DO belong together from notes. Answer = the odd one from notes.
   Use ONLY notes. Pure Tamil only. NO SM branding / Latin / rule codes (R#/E#)."""
    if (
        topic_id == "agara_varisai"
        or "அகர வரிசை" in topic_ta
        or "alphabetical" in topic_en.lower()
    ):
        return """5. Preferred shapes for this topic (mix across the 17):
   - Given 4–5 jumbled words → choose the correct அகர வரிசை order (options are full sequences)
   - Which option is the correctly ordered list?
   - Which word should come FIRST / LAST in அகர வரிசை among the given words?
   - Spot the WRONG order among four sequences
   - Mix: உயிர்-first lists (அ ஆ இ…) and உயிர்மெய் series (க கா கி…; க் before க)
6. Use ONLY notes order examples as answer truth. Distractors = plausible near-miss reorderings.
   Pure Tamil only. NO SM branding / Latin / rule codes (R#/E#)."""
    if (
        topic_id == "oruporul_panmozhi"
        or "ஒருபொருள் பன்மொழி" in topic_ta
        or "ஒருபொருட் பன்மொழி" in topic_ta
        or "panmozhi" in topic_en.lower()
    ):
        return """5. Preferred shapes for this topic (mix across the 17):
   - Compound → choose the correct split (நடுமையம் → நடு + மையம்; மீமிசை → மீ + மிசை)
   - Compound / pair → choose the shared meaning (உயர்ந்து+ஓங்கி → உயர்ந்த; நடு+மையம் → நடுப்பகுதி)
   - Identify which option IS / is NOT ஒருபொருட் பன்மொழி (from notes compounds only)
   - Short rule MCQ: definition; இணைப்பெயர் / ஒருபொருட்கிளவி / ஒத்தச்சொல்; நன்னூல் term
   - Optional: 1 match-the-following (compound ↔ split or meaning) HTML match-container
6. Distractors = other notes splits/meanings — NOT invented glosses.
   Use ONLY notes. Pure Tamil only. NO SM branding / Latin / rule codes (R#/E#)."""
    if (
        topic_id == "iruporul_kurikkum_sorkal"
        or "இருபொருள்" in topic_ta
        or "dual" in topic_en.lower()
        or "two meaning" in topic_en.lower()
    ):
        return """5. Preferred shapes for this topic (mix across the 17):
   - Word → choose BOTH meanings / the correct dual-meaning pair from notes (ஆறு→நதி, எண்; மதி→அறிவு, நிலவு)
   - Meaning → which word has these two senses
   - Spot which option is NOT a meaning of the given word
   - Context/pun phrases from notes (தாமரைக்காடு, பலதையொலி) → choose the dual reading
   - Optional: 1 match-the-following (word ↔ dual meanings) HTML match-container
6. Distractors = meanings of OTHER notes words — NOT invented glosses.
   Use ONLY notes. Pure Tamil only. NO SM branding / Latin / rule codes (R#/E#)."""
    if (
        topic_id == "pechu_ezhuthu_vazhakku"
        or "பேச்சு வழக்கு" in topic_ta
        or "எழுத்து வழக்கு" in topic_ta
        or "colloquial" in topic_en.lower()
        or "spoken" in topic_en.lower()
    ):
        return """5. Preferred shapes for this topic (mix across the 17):
   - பேச்சு வழக்கு → choose correct எழுத்து வழக்கு (ஒலகம்→உலகம்; சாப்டான்→சாப்பிட்டான்)
   - எழுத்து வழக்கு → which is the matching spoken form
   - Spot the WRONG / வழுஉ form among options
   - Short sentence: convert colloquial phrase to written Tamil (from notes)
   - Rule MCQ: பேச்சு vs எழுத்து; உலக/செய்யுள் வழக்கு; தொல்காப்பியர்; வழுஉச் சொல்
   - Optional: 1 match-the-following (பேச்சு ↔ எழுத்து) HTML match-container
6. Distractors = other notes pairs — NOT invented spellings.
   Use ONLY notes. Pure Tamil only. NO SM branding / Latin / rule codes (R#/E#)."""
    if (
        topic_id == "koditta_idam_sariya_sol"
        or "கோடிட்ட" in topic_ta
        or "fill" in topic_en.lower()
        or "blank" in topic_en.lower()
    ):
        return """5. Preferred shapes for this topic (mix across the 17):
   - Fill-in-the-blank stem with --- / ___; choose the correct word (from notes output)
   - Given a completed sentence, which word correctly fills the blank
   - Spot the WRONG filler among close distractors
   - Meaning/clue → apt word (கணையாழி, ஞாயிறு, கேணி, மேதினி…) from notes only
   - Optional: 1 match-the-following (clue ↔ word) HTML match-container
6. Distractors = other notes answers — NOT invented fillers.
   Use ONLY notes. Pure Tamil only. NO SM branding / Latin / rule codes (R#/E#)."""
    if (
        topic_id == "poruthamana_porul"
        or "பொருத்தமான பொருள்" in topic_ta
        or "suitable meaning" in topic_en.lower()
    ):
        return """5. Preferred shapes for this topic (mix across the 17):
   - Word / phrase / underlined word → choose the பொருத்தமான பொருள் (apt meaning) from notes
   - Meaning → which word/phrase matches (reverse)
   - Literary/classical line snippet → apt meaning of the keyed word (notes only)
   - Spot the WRONG meaning among close distractors
   - Optional: 1 match-the-following (word ↔ meaning) HTML match-container
6. Distractors = other notes meanings — NOT invented glosses.
   Use ONLY notes. Pure Tamil only. NO SM branding / Latin / rule codes (R#/E#)."""
    if (
        topic_id == "oor_peyar_maruu"
        or "மரூஉ" in topic_ta
        or "ஊர்ப் பெயர்" in topic_ta
        or "maruu" in topic_en.lower()
        or "place name" in topic_en.lower()
    ):
        return """5. Preferred shapes for this topic (mix across the 17):
   - Full place name → choose the correct மரூஉ (colloquial/short form) from notes
   - மரூஉ → choose the matching full ஊர்ப் பெயர் (reverse)
   - Spot the WRONG மரூஉ among close place-name distractors
   - Optional: 1 match-the-following (ஊர் ↔ மரூஉ) HTML match-container
6. Distractors = other notes மரூஉ / place names — NOT invented forms.
   Use ONLY notes. Pure Tamil only. NO SM branding / Latin / rule codes (R#/E#)."""
    if (
        topic_id == "pizhai_thiruthugal"
        or "பிழை" in topic_ta
        or "error" in topic_en.lower()
        or "correction" in topic_en.lower()
    ):
        return """5. Preferred shapes for this topic (mix across the 17):
   - Wrong word/form in a short phrase → choose the corrected form (from notes)
   - Spot the பிழை among four options / which option is already correct
   - Given a common spelling/usage error → pick the சரியான வடிவம்
   - Rule-based: apply notes correction rules (எழுத்து / சொல் பிழை) to choose the right fix
   - Optional: 1 match-the-following (பிழை ↔ திருத்தம்) HTML match-container
6. Distractors = plausible wrong spellings from notes — NOT invented junk.
   Use ONLY notes. Pure Tamil only. NO SM branding / Latin / rule codes (R#/E#)."""
    if (
        topic_id == "sorkalai_inaithu_puthiya_sol"
        or "இணைத்துப் புதிய சொல்" in topic_ta
        or "புதிய சொல்" in topic_ta
        or "compound" in topic_en.lower()
        or "combine" in topic_en.lower()
    ):
        return """5. Preferred shapes for this topic (mix across the 17):
   - Two (or more) words → choose the correct combined புதிய சொல் (from notes)
   - Combined word → choose the correct split / components (reverse)
   - Spot the WRONG compound among close distractors
   - Optional: 1 match-the-following (parts ↔ compound) HTML match-container
6. Distractors = other notes compounds / wrong joins — NOT invented words.
   Use ONLY notes. Pure Tamil only. NO SM branding / Latin / rule codes (R#/E#)."""
    if (
        topic_id == "adaippukkul_sol_serthal"
        or "அடைப்புக்குள்" in topic_ta
        or "தகுந்த இடத்தில் சேர்த்தல்" in topic_ta
        or "bracket" in topic_en.lower()
        or "insert" in topic_en.lower()
    ):
        return """5. Preferred shapes for this topic (mix across the 17):
   - Sentence with blank + word in brackets → choose the correctly completed sentence (notes)
   - Given options of placements, pick where the bracketed word fits
   - Spot the WRONG insertion / wrong position among close distractors
   - Optional: 1 match-the-following (bracket word ↔ apt slot) HTML match-container
6. Distractors = wrong placements or wrong related words from notes — NOT invented.
   Use ONLY notes. Pure Tamil only. NO SM branding / Latin / rule codes (R#/E#)."""
    if (
        topic_id == "pala_porul_oru_sol"
        or "பல பொருள் தரும் ஒரு சொல்" in topic_ta
        or "பல பொருள்" in topic_ta
        or "many meanings" in topic_en.lower()
        or "polysem" in topic_en.lower()
    ):
        return """5. Preferred shapes for this topic (mix across the 17):
   - Word → choose the FULL set / correct multi-meaning list from notes (அகம்→வீடு, மனம், உட்பகுதி…)
   - Given several meanings → which ONE word covers them (reverse)
   - Spot which option is NOT a meaning of the given word
   - Sentence where the SAME word is used in multiple senses (notes book examples: அணி, படி, திங்கள், ஆறு) → identify the word / choose the correct multi-sense sentence
   - Distinguish from ஒருபொருள் பல சொற்கள்: here ONE word → MANY meanings (not many synonyms for one sense)
   - Optional: 1 match-the-following (word ↔ multi-meanings) HTML match-container
6. Distractors = meanings of OTHER notes words — NOT invented glosses.
   Prefer true polysemy pairs from notes. Pure Tamil only. NO SM branding / Latin / rule codes (R#/E#)."""
    return """5. Preferred shapes: TNPSC vocabulary MCQs from notes only.
6. Distractors must be plausible. Pure Tamil. NO SM branding."""

def call_gemini(topic_id, topic_ta, topic_en, batch_num, rules, examples, exclusion_texts, api_key):
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

    shapes = preferred_shapes(topic_id, topic_ta, topic_en)
    prompt = f"""
You are a senior TNPSC General Tamil (பொதுத் தமிழ்) exam compiler for Unit 2 சொல்லகராதி.
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
4. Do NOT force Medium/Hard split. Focus on clean TNPSC-style vocabulary items.
{shapes}
7. Each object keys (JSON array only):
   - question_en, question_ta
   - options_en: exactly 4 strings
   - options_ta: exactly 4 strings (parallel to options_en)
   - answer_en: must equal one of options_en exactly
   - answer_ta: must equal one of options_ta exactly
   - explanation_en, explanation_ta (cite the pair/rule briefly — no SM branding)
   - difficulty: optional; if present use "medium"
   - source_note: short pointer like "notes pair" (no academy name)

Option E (Answer not known) will be added by post-processing — do NOT include it in options_en/options_ta.
Escape internal double quotes properly. Return ONLY a JSON array.
"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    headers = {"Content-Type": "application/json"}

    for model in MODELS:
        retries = 4
        attempt = 0
        delay = 10
        while attempt < retries:
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
                f":generateContent?key={api_key}"
            )
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
                    if isinstance(data, list):
                        print(f"    model={model}")
                        return data
                    return []
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="ignore")
                if e.code == 429:
                    print(f"    {model} rate limited; sleep {delay}s...")
                    time.sleep(delay)
                    delay = min(delay * 2, 45)
                    attempt += 1
                    continue
                print(f"    {model} HTTP {e.code}: {body[:160]}")
                break
            except Exception as e:
                attempt += 1
                print(f"    {model} Error: {e}")
                time.sleep(5)
    return []


def main():
    parser = argparse.ArgumentParser(description="Sollagarathi practice question generator")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--batch", type=int, required=True)
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
            args.topic,
            topic_ta,
            topic_en,
            args.batch,
            rules,
            examples,
            exclusion_texts,
            api_key,
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
            if combined < 120:
                print(f"  Discard: too short ({combined})")
                continue

            idx_en = opts_en.index(ans_en)
            idx_ta = opts_ta.index(ans_ta)
            correct_index = idx_ta if idx_en != idx_ta else idx_en
            if idx_en != idx_ta:
                ans_en = opts_en[correct_index]

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

            raw_diff = str(q.get("difficulty") or "medium").strip().capitalize()
            if raw_diff not in ("Medium", "Hard"):
                raw_diff = "Medium"

            # Scrub branding from source_note / explanations lightly
            def scrub(s):
                s = re.sub(r"\bSM\b\.?", "", s or "", flags=re.I)
                s = re.sub(r"எஸ்\.?\s*எம்\.?", "", s)
                s = re.sub(r"விதி\s*R\d+", "", s)
                s = re.sub(r"\s{2,}", " ", s).strip(" ,.")
                return s

            standard_q = {
                "subject": "Tamil",
                "unit": "Sollagarathi",
                "topic": topic_ta,
                "topic_id": args.topic,
                "source_exam": f"Practice Batch {args.batch}",
                "difficulty": raw_diff,
                "question_en": q_en,
                "question_ta": q_ta,
                "options": standard_options,
                "correct_option": correct_key,
                "explanation": scrub(str(q["explanation_en"])),
                "explanation_ta": scrub(str(q["explanation_ta"])),
                "type": "practice",
                "batch": f"Batch {args.batch}",
                "group": "Practice",
                "source_note": scrub(str(q.get("source_note") or "notes")) or "notes",
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
            existing_keys.add(key_ta)
            existing_keys.add(key_en)
            exclusion_texts.append(q_ta[:220])

        print(f"  Accumulated valid={len(valid)}")
        if len(valid) >= 30:
            break
        print("  Sleeping 8s...")
        time.sleep(8)

    if len(valid) < 30:
        print(f"ERROR: need 30 valid; got {len(valid)}")
        sys.exit(1)

    valid.sort(
        key=lambda q: len(q["explanation"]) + len(q["explanation_ta"]), reverse=True
    )
    final_batch = valid[:30]
    random.shuffle(final_batch)
    print("Selecting 30 questions")

    all_db.extend(final_batch)
    save_json(DB_PATH, all_db)
    print(
        f"\nSUCCESS: Added {len(final_batch)} Q → {DB_PATH} "
        f"(topic={topic_ta}, Batch {args.batch}); DB total={len(all_db)}"
    )


if __name__ == "__main__":
    main()
