"""
Generate TNPSC Biology practice batches from biology_facts.json (25 Q / batch).

Usage:
  python3 Biology/generate_biology_questions.py --topic "The Cell — Basic Unit of Life" --batch 1
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
sys.path.insert(0, BASE_DIR)
from gemini_keys import DEFAULT_KEY, FALLBACK_KEYS  # noqa: E402

FACTS_PATH = os.path.join(BASE_DIR, "Biology", "biology_facts.json")
DB_PATH = os.path.join(BASE_DIR, "Biology", "biology_questions_db.json")
GUIDE_PATH = os.path.join(BASE_DIR, "Biology", "BIOLOGY_BATCH_GENERATION_GUIDE.md")
MODEL = "gemini-3.1-flash-lite"

# User-approved pool: DEFAULT_KEY + 4× AQ keys only
KEY_POOL = [DEFAULT_KEY] + [k for k in FALLBACK_KEYS if k.startswith("AQ.")]

BATCH_SIZE = 25
GEN_TOTAL = 28  # all Medium candidates; prune to 25

_STRONG_FACT = [
    r"\b(16\d{2}|17\d{2}|18\d{2}|19\d{2}|20\d{2})\b",
    r"(?i)\b(Hooke|Leeuwenhoek|Leewenhoek|Robert Brown|Purkinje|Schleiden|Schwann|Virchow|Mendel|Linnaeus|Aristotle|Hippocrates|Pasteur|Darwin|Watson|Crick|Harvey|Landsteiner|Banting|Best|Salk|Jenner)\b",
    r"(?i)\b(mitochondria|ribosome|lysosome|chloroplast|nucleolus|endoplasmic|golgi|vacuole|centrosome|chromosome|chromatid|centriole|plasmodesmata|tonoplast)\b",
    r"(?i)\b(hormone|insulin|thyroxine|adrenaline|estrogen|testosterone|progesterone|oxytocin|vasopressin|GH|FSH|LH|TSH|ACTH)\b",
    r"(?i)\b(DNA|RNA|ATP|NADP|NADH|mitosis|meiosis|allele|genotype|phenotype|homozygous|heterozygous|linkage)\b",
    r"(?i)\b(bacteria|virus|fungi|protista|monera|plantae|animalia|pathogen|vaccine|antibody|antigen|hemoglobin|plasma|platelet|erythrocyte|leukocyte)\b",
    r"(?i)\b(photosynthesis|respiration|glycolysis|Krebs|electron transport|circulation|systole|diastole|synapse|neuron)\b",
    r"(?i)\b(called|named|discovered|composed of|consists of|caused by|deficiency|syndrome|secretes|transmits)\b",
    r"(?i)\b(WHO|UNESCO|IUCN|Red Data|hotspot|ozone|greenhouse|pollution|Biodiversity|Wildlife|Project Tiger|Silent Valley)\b",
    r"(?i)\b(BCG|DPT|MMR|polio|measles|malaria|tuberculosis|cholera|typhoid|AIDS|HIV|diabetes|goitre)\b",
]

_key_idx = 0
_rate_limit_hits = 0


def next_api_key() -> str:
    global _key_idx
    if not KEY_POOL:
        raise SystemExit("KEY_POOL empty")
    key = KEY_POOL[_key_idx % len(KEY_POOL)]
    _key_idx += 1
    return key


def is_tnpsc_fact(fact_en: str) -> bool:
    """Keep exam-worthy facts; drop vague hierarchy / fluff."""
    en = (fact_en or "").strip()
    if len(en) < 30 or len(en) > 450:
        return False
    low = en.lower()
    if low.startswith(("various ", "many types", "several types", "see ", "this page", "the text")):
        return False
    if re.search(r"(?i)^(organs?|tissues?) (are|is) (made|composed)", en):
        return False
    if re.search(r"(?i)\b(important|essential|necessary)\.?$", en) and not any(
        re.search(p, en) for p in _STRONG_FACT
    ):
        return False
    if any(re.search(p, en) for p in _STRONG_FACT):
        return True
    structure = bool(
        re.search(
            r"\b(is|are|was|were|has|have|contains|produces|stores|found in|known as|secretes|causes|defined as)\b",
            en,
            re.I,
        )
    )
    words = re.findall(r"[A-Za-z]{4,}", en)
    return structure and len(en) >= 45 and len(words) >= 6


def filter_tnpsc_facts(facts: list) -> list:
    return [f for f in facts if is_tnpsc_fact(f.get("fact_en") or "")]


def recommended_batches(valid_count: int) -> int:
    if valid_count >= 70:
        return 3
    if valid_count >= 40:
        return 2
    if valid_count >= 25:
        return 2  # still try 2 for thin topics
    return 0


def load_facts(topic: str):
    if not os.path.exists(FACTS_PATH):
        print(f"Error: Facts file not found at {FACTS_PATH}")
        return []
    with open(FACTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get(topic, [])


def load_existing_questions(topic: str):
    if not os.path.exists(DB_PATH):
        return []
    with open(DB_PATH, "r", encoding="utf-8") as f:
        try:
            questions = json.load(f)
            return [q for q in questions if q.get("topic") == topic]
        except Exception:
            return []


def call_gemini_generation(topic, batch_num, facts, exclusion_texts, api_key, guide_rules):
    facts_formatted = "\n".join([f"- {idx+1}. {f['fact_en']}" for idx, f in enumerate(facts)])
    exclusions_formatted = ""
    if exclusion_texts:
        exclusions_formatted = (
            "\nEXCLUDED QUESTION TEXTS (DO NOT GENERATE SIMILAR):\n"
            + "\n".join([f"- {t}" for t in exclusion_texts[:150]])
        )

    prompt = f"""
You are a senior TNPSC Group I/II Biology exam compiler (Botany + Zoology).
Generate exactly {GEN_TOTAL} practice questions — **all Medium difficulty** — for topic "{topic}", Practice Batch {batch_num}.
These will be pruned to a final batch of {BATCH_SIZE} questions.

Ground Truth Facts:
{facts_formatted}
{exclusions_formatted}

GENERATION GUIDE:
{guide_rules}

Rules:
1. Base every question strictly on the Ground Truth Facts. Put the English fact in "source_fact".
2. All {GEN_TOTAL} questions must have difficulty exactly "medium". Fully bilingual (English + Tamil Unicode).
3. Match-the-following: strict 4x4 HTML layout with match-container / match-col-left / match-col-right.
4. Statement questions: 2–4 numbered statements with combination options.
5. Assertion-Reason allowed with standard A/R option wording including Option E later.
6. Advanced formats within the {GEN_TOTAL}: Min 5 paragraph-inference + Min 4 contextual-connect style items.
7. Output raw JSON array only. Each object keys:
   question_en, question_ta, options_en (4), options_ta (4),
   answer_en, answer_ta, explanation_en, explanation_ta, difficulty, source_fact
8. Combined question+explanation should be substantial (>=180 chars total across EN+TA fields).
9. ONLY write questions that a TNPSC aspirant would see: concrete definitions, scientists/years, organelles, hormones, pathogens, processes, schemes — NOT vague “organs→tissues→cells” fluff.
10. Do NOT generate Hard or Easy questions. difficulty must be "medium".
11. Every question must be answerable from the Ground Truth Facts list alone.
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    headers = {"Content-Type": "application/json"}
    retries = 5
    delay = 8
    global _rate_limit_hits
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=240) as response:
                res_json = json.loads(response.read().decode("utf-8"))
                raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
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
                return json.loads(raw_text)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            if e.code in (429, 503):
                _rate_limit_hits += 1
                print(f"  ⚠ RATE LIMIT HTTP {e.code} (hit #{_rate_limit_hits}); sleep {delay}s, rotate key...")
                time.sleep(delay)
                delay = min(delay * 2, 60)
                api_key = next_api_key()
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
            else:
                print(f"  HTTP {e.code} attempt {attempt}/{retries}: {body[:200]}")
                time.sleep(4)
                api_key = next_api_key()
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
        except Exception as e:
            print(f"  Error attempt {attempt}/{retries}: {e}")
            time.sleep(4)
            api_key = next_api_key()
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
    return []


def prune_and_save(topic, batch_num, raw_questions):
    valid = []
    for q in raw_questions:
        required = [
            "question_en", "question_ta", "options_en", "options_ta",
            "answer_en", "answer_ta", "explanation_en", "explanation_ta", "difficulty",
        ]
        if not all(k in q for k in required):
            continue
        if not isinstance(q.get("options_en"), list) or not isinstance(q.get("options_ta"), list):
            continue
        if len(q["options_en"]) < 4 or len(q["options_ta"]) < 4:
            continue
        ans_en = str(q["answer_en"]).strip()
        ans_ta = str(q["answer_ta"]).strip()
        opts_en = [str(x).strip() for x in q["options_en"][:4]]
        opts_ta = [str(x).strip() for x in q["options_ta"][:4]]
        if ans_en not in opts_en:
            matched = next((o for o in opts_en if o.lower() == ans_en.lower()), None)
            if not matched:
                continue
            ans_en = matched
        if ans_ta not in opts_ta:
            matched_ta = next((o for o in opts_ta if o == ans_ta), None)
            if not matched_ta:
                correct_index = opts_en.index(ans_en)
                ans_ta = opts_ta[correct_index]
            else:
                ans_ta = matched_ta

        is_match = "match" in q["question_en"].lower() or "பொருத்து" in q["question_ta"]
        if is_match:
            ql = q["question_en"].lower()
            has_layout = "match-container" in ql or "match-col-left" in ql
            has_abcd = all(p in ql for p in ["a)", "b)", "c)", "d)"]) or all(
                p in ql for p in ["a.", "b.", "c.", "d."]
            )
            has_1234 = all(p in ql for p in ["1.", "2.", "3.", "4."]) or all(
                p in ql for p in ["1)", "2)", "3)", "4)"]
            )
            if not ((has_abcd and has_1234) or has_layout):
                print(f"  Discard match (not 4x4): {q['question_en'][:80]}...")
                continue

        combined_len = (
            len(q["question_en"]) + len(q["question_ta"])
            + len(q["explanation_en"]) + len(q["explanation_ta"])
        )
        if combined_len < 180:
            continue

        correct_index = opts_en.index(ans_en)
        keys_map = ["A", "B", "C", "D"]
        standard_options = [
            {"key": keys_map[i], "text_en": opts_en[i], "text_ta": opts_ta[i]}
            for i in range(4)
        ]
        standard_options.append(
            {"key": "E", "text_en": "Answer not known", "text_ta": "விடை தெரியவில்லை"}
        )

        # Force Medium per rule (even if model labels Hard)
        standard_q = {
            "subject": "Biology",
            "topic": topic,
            "source_exam": f"Practice Batch {batch_num}",
            "difficulty": "Medium",
            "question_en": q["question_en"].strip(),
            "question_ta": q["question_ta"].strip(),
            "options": standard_options,
            "correct_option": keys_map[correct_index],
            "explanation": q["explanation_en"].strip(),
            "explanation_ta": q["explanation_ta"].strip(),
            "type": "practice",
            "batch": f"Batch {batch_num}",
            "group": "Practice",
            "source_fact": str(q.get("source_fact", "")).strip(),
        }
        valid.append(standard_q)

    print(f"Valid Medium candidates: {len(valid)}")
    if len(valid) < 20:
        print(f"ERROR: Need at least 20 valid Qs; got {len(valid)}")
        return 0

    valid.sort(key=lambda q: len(q["explanation"]) + len(q["explanation_ta"]), reverse=True)
    final_batch = valid[:BATCH_SIZE]
    random.shuffle(final_batch)
    if len(final_batch) < BATCH_SIZE:
        print(f"  WARN: only {len(final_batch)}/{BATCH_SIZE} after pruning (match/length filters)")
    print(f"Selecting {len(final_batch)} Medium questions")

    all_db_qs = []
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "r", encoding="utf-8") as f:
            try:
                all_db_qs = json.load(f)
            except Exception:
                all_db_qs = []

    existing_all = {q.get("question_en", "").strip().lower() for q in all_db_qs if q.get("question_en")}
    added = 0
    for q in final_batch:
        key = q["question_en"].strip().lower()
        if key not in existing_all:
            all_db_qs.append(q)
            existing_all.add(key)
            added += 1

    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(all_db_qs, f, indent=2, ensure_ascii=False)

    print(f"SUCCESS: Added {added} Qs for '{topic}' Batch {batch_num}. DB total={len(all_db_qs)}")
    return added


def main():
    parser = argparse.ArgumentParser(description="Biology Practice Question Generator (25/batch)")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--batch", type=int, required=True)
    args = parser.parse_args()

    global _rate_limit_hits
    _rate_limit_hits = 0
    api_key = next_api_key()
    print(f"Model: {MODEL} | API key pool: {len(KEY_POOL)} (DEFAULT + 4× AQ)")

    guide_rules = ""
    if os.path.exists(GUIDE_PATH):
        with open(GUIDE_PATH, "r", encoding="utf-8") as f:
            guide_rules = f.read()

    all_topic_facts = load_facts(args.topic)
    if not all_topic_facts:
        print(f"Error: No facts for '{args.topic}' in {FACTS_PATH}. Extract facts first.")
        sys.exit(1)

    filtered = filter_tnpsc_facts(all_topic_facts)
    print(f"Facts: {len(all_topic_facts)} raw → {len(filtered)} TNPSC-valid")
    if len(filtered) < 25:
        print(f"ERROR: Too few TNPSC-valid facts ({len(filtered)}) for a 25-Q batch.")
        sys.exit(1)

    existing_qs = load_existing_questions(args.topic)
    exclusion_texts = [q.get("question_en", "").strip().lower() for q in existing_qs if q.get("question_en")]
    print(f"Found {len(existing_qs)} existing questions for exclusions.")

    print(f"Calling Gemini for Batch {args.batch} ({GEN_TOTAL} → prune to {BATCH_SIZE})...")
    raw_questions = call_gemini_generation(
        args.topic, args.batch, filtered, exclusion_texts, api_key, guide_rules
    )
    print(f"Received {len(raw_questions)} questions from Gemini.")
    if not raw_questions:
        sys.exit(1)

    added = prune_and_save(args.topic, args.batch, raw_questions)
    if added == 0:
        sys.exit(1)
    if _rate_limit_hits:
        print(f"⚠ RATE LIMIT SUMMARY: {_rate_limit_hits} hits this batch.")


if __name__ == "__main__":
    main()
