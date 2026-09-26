#!/usr/bin/env python3
"""Extract bilingual TNPSC Physics facts from the Bamini Tamil study-material PDF."""

from __future__ import annotations

import argparse
import base64
import difflib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

import fitz

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from gemini_keys import gemini_keys  # noqa: E402

PDF_PATH = os.path.join(
    BASE_DIR, "Data", "Physics", "STUDY MATERIAL - PHYSICS ( TAMIL).pdf"
)
OUTPUT_JSON = os.path.join(BASE_DIR, "Physics", "physics_facts.json")
QC_PATH = os.path.join(BASE_DIR, "Physics", "physics_facts_qc_report.json")
CACHE_DIR = os.path.join(BASE_DIR, "Physics", "_tmp_fact_extract_cache")
MODEL = "gemini-3.1-flash-lite"
BOOK_NAME = "Physics Tamil Study Material"

# Physical PDF pages, 1-based and inclusive.
TOPICS = {
    "Universe": {
        "topic_ta": "பேரண்டம்",
        "pages": list(range(3, 12)),
    },
    "Laws of Physics": {
        "topic_ta": "பொது அறிவியல் விதிகள்",
        "pages": list(range(12, 26)),
    },
    "Scientific Instruments": {
        "topic_ta": "அறிவியல் கருவிகள்",
        "pages": list(range(26, 31)),
    },
    "Discoveries and National Scientific Laboratories": {
        "topic_ta": "கண்டுபிடிப்புகள் மற்றும் தேசிய அறிவியல் ஆய்வகங்கள்",
        "pages": list(range(30, 40)),
    },
    "Mechanics and Properties of Matter": {
        "topic_ta": "இயந்திரவியல் மற்றும் பருப்பொருளின் பண்புகள்",
        "pages": list(range(40, 45)),
    },
    "Physical Quantities, Standards and Units": {
        "topic_ta": "இயற்பியல் அளவைகள், படிநிலைகள் மற்றும் அலகுகள்",
        "pages": list(range(44, 62)),
    },
    "Force, Motion and Energy": {
        "topic_ta": "விசை, இயக்கம் மற்றும் ஆற்றல்",
        "pages": list(range(61, 79)),
    },
}

KEY_POOL = gemini_keys()
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
        print(f"    ⚠ Disabling key …{key[-6:]}: {reason}")


def cache_path(topic: str, page_num: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", topic.lower()).strip("_")
    return os.path.join(CACHE_DIR, f"{slug}_page_{page_num:03d}.json")


def load_cache(topic: str, page_num: int):
    path = cache_path(topic, page_num)
    if not os.path.exists(path):
        return None
    try:
        data = json.load(open(path, encoding="utf-8"))
        return data if isinstance(data, list) else None
    except Exception:
        return None


def save_cache(topic: str, page_num: int, facts: list):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(cache_path(topic, page_num), "w", encoding="utf-8") as handle:
        json.dump(facts, handle, indent=2, ensure_ascii=False)


def render_page(doc, page_num: int, dpi: int = 200) -> str:
    pix = doc[page_num - 1].get_pixmap(dpi=dpi, alpha=False)
    return base64.b64encode(pix.tobytes("png")).decode("ascii")


def build_prompt(topic: str, topic_ta: str, page_num: int) -> str:
    boundary_note = ""
    if topic == "Scientific Instruments" and page_num == 30:
        boundary_note = (
            "\nBOUNDARY: Extract only the Scientific Instruments entries through "
            "Wavemeter. Stop before the Discoveries and National Scientific "
            "Laboratories heading on the same page.\n"
        )
    if (
        topic == "Discoveries and National Scientific Laboratories"
        and page_num == 30
    ):
        boundary_note = (
            "\nBOUNDARY: Ignore the Scientific Instruments entries at the top. "
            "Start at the Discoveries and National Scientific Laboratories "
            "heading and extract every discoveries-table row below it.\n"
        )
    if topic == "Mechanics and Properties of Matter" and page_num == 44:
        boundary_note = (
            "\nBOUNDARY: Extract only the Mechanics surface-tension application "
            "bullets at the top of the page. Stop before the Physical Quantities, "
            "Standards and Units heading that begins later on this page.\n"
        )
    if topic == "Physical Quantities, Standards and Units" and page_num == 44:
        boundary_note = (
            "\nBOUNDARY: Ignore the Mechanics surface-tension bullets at the top. "
            "Start at the Physical Quantities, Standards and Units heading and "
            "extract only that topic's content below it.\n"
        )
    if topic == "Physical Quantities, Standards and Units" and page_num == 61:
        boundary_note = (
            "\nBOUNDARY: Extract only the Physical Quantities content at the top "
            "of the page (volume/density bullets). Stop before the Force, Motion "
            "and Energy heading that begins later on this page.\n"
        )
    if topic == "Force, Motion and Energy" and page_num == 61:
        boundary_note = (
            "\nBOUNDARY: Ignore the Physical Quantities density bullets at the top. "
            "Start at the Force, Motion and Energy heading (IX. விசை, இயக்கம் "
            "மற்றும் ஆற்றல்) and extract only that topic's content below it.\n"
        )
    if topic == "Force, Motion and Energy" and page_num == 78:
        boundary_note = (
            "\nBOUNDARY: Extract only Force, Motion and Energy content through "
            "Nuclear Energy (அணுக்கரு ஆற்றல்). Stop before the Electricity and "
            "Magnetism chapter heading on the next page.\n"
        )
    return f"""
You are an expert TNPSC Physics fact extractor.

SOURCE: "{BOOK_NAME}", physical PDF page {page_num}
TOPIC: {topic} ({topic_ta})
{boundary_note}
The page is printed in Tamil. Read the PAGE IMAGE directly; its PDF text layer uses
Bamini encoding and must not be copied as Roman gibberish.

Perform exhaustive line-by-line extraction. Read every bullet, list, table row,
caption, number, scientist, year and comparison.

Extract:
1. Definitions and classifications.
2. Physics laws, theories, processes and relationships.
3. Scientists, discoveries and years.
4. Numerical facts: distances, periods, sizes, counts and dates.
5. Table rows as separate testable facts.
6. Cause/effect statements and distinctions suitable for TNPSC MCQs.

Rules:
- Extract only facts visibly supported by this page.
- Do not add outside knowledge or silently update old values in the source.
- Split compound bullets into separate testable facts.
- Prefer 8–20 facts on a content-rich page; do not omit facts merely to meet a limit.
- Translate faithfully into clear English and modern Tamil Unicode.
- Never output Bamini/Romanized Tamil in `fact_ta`.
- Skip academy name, address, contact number, headers, footers and page number.
- Keep each fact independently understandable and specific.

Return ONLY a JSON array:
[
  {{
    "fact_en": "Specific English fact",
    "fact_ta": "குறிப்பிட்ட தமிழ் உண்மை",
    "source": "{BOOK_NAME} Page {page_num}",
    "context_en": "{topic}",
    "context_ta": "{topic_ta}"
  }}
]
""".strip()


def build_audit_prompt(
    topic: str, topic_ta: str, page_num: int, existing_facts: list
) -> str:
    boundary_note = ""
    if topic == "Scientific Instruments" and page_num == 30:
        boundary_note = (
            "\nBOUNDARY: Audit only the Scientific Instruments entries through "
            "Wavemeter. Ignore the next topic beginning later on this page.\n"
        )
    if (
        topic == "Discoveries and National Scientific Laboratories"
        and page_num == 30
    ):
        boundary_note = (
            "\nBOUNDARY: Ignore the Scientific Instruments entries at the top. "
            "Audit only the discoveries table beginning later on this page.\n"
        )
    if topic == "Mechanics and Properties of Matter" and page_num == 44:
        boundary_note = (
            "\nBOUNDARY: Audit only the Mechanics surface-tension application "
            "bullets at the top. Ignore the Physical Quantities topic below.\n"
        )
    if topic == "Physical Quantities, Standards and Units" and page_num == 44:
        boundary_note = (
            "\nBOUNDARY: Ignore the Mechanics bullets at the top. Audit only the "
            "Physical Quantities topic beginning later on this page.\n"
        )
    if topic == "Physical Quantities, Standards and Units" and page_num == 61:
        boundary_note = (
            "\nBOUNDARY: Audit only the Physical Quantities content at the top. "
            "Ignore the Force, Motion and Energy topic below.\n"
        )
    if topic == "Force, Motion and Energy" and page_num == 61:
        boundary_note = (
            "\nBOUNDARY: Ignore the Physical Quantities density bullets at the top. "
            "Audit only the Force, Motion and Energy topic beginning later on this page.\n"
        )
    if topic == "Force, Motion and Energy" and page_num == 78:
        boundary_note = (
            "\nBOUNDARY: Audit only Force, Motion and Energy content through "
            "Nuclear Energy. Ignore the Electricity and Magnetism chapter on the next page.\n"
        )
    existing = "\n".join(
        f"- {fact.get('fact_en', '')}" for fact in existing_facts
    )
    return f"""
You are auditing exhaustive TNPSC Physics fact extraction from a Tamil page image.

SOURCE: "{BOOK_NAME}", physical PDF page {page_num}
TOPIC: {topic} ({topic_ta})
{boundary_note}
The image is authoritative. The PDF uses Bamini Tamil, so read the image directly.

Facts already extracted:
{existing}

Return ONLY facts visibly present on the page that are MISSING from the list above.
Check every bullet, table row, number, year, name, distance, period, classification,
cause/effect statement and qualifier. Do not paraphrase facts already present.
Do not use outside knowledge. Skip academy headers and footers.

Return ONLY a JSON array using:
[
  {{
    "fact_en": "Specific missing English fact",
    "fact_ta": "விடுபட்ட குறிப்பிட்ட தமிழ் உண்மை",
    "source": "{BOOK_NAME} Page {page_num}",
    "context_en": "{topic}",
    "context_ta": "{topic_ta}"
  }}
]
""".strip()


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


def call_gemini(
    image_b64: str,
    topic: str,
    topic_ta: str,
    page_num: int,
    prompt_override: str | None = None,
) -> list:
    global _rate_limit_hits
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt_override
                        or build_prompt(topic, topic_ta, page_num)
                    },
                    {"inlineData": {"mimeType": "image/png", "data": image_b64}},
                ]
            }
        ],
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
            with urllib.request.urlopen(request, timeout=180) as response:
                result = json.loads(response.read().decode("utf-8"))
                return parse_array(result["candidates"][0]["content"]["parts"][0]["text"])
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            if exc.code in (429, 503):
                _rate_limit_hits += 1
                print(
                    f"    ⚠ P{page_num} HTTP {exc.code}; rotate key, sleep {delay}s "
                    f"(hit #{_rate_limit_hits})"
                )
                time.sleep(delay)
                delay = min(delay * 2, 60)
                key = next_api_key()
                continue
            if exc.code == 404 and "no longer available" in body.lower():
                disable_key(key, f"model unavailable for key on P{page_num}")
                key = next_api_key()
                continue
            print(f"    P{page_num} attempt {attempt}/5 HTTP {exc.code}: {body[:180]}")
        except Exception as exc:
            print(f"    P{page_num} attempt {attempt}/5: {exc}")
        time.sleep(4)
        key = next_api_key()
    return []


def has_tamil(text: str) -> bool:
    return bool(re.search(r"[\u0B80-\u0BFF]", text or ""))


def normalize_fact(fact: dict, topic: str, topic_ta: str, page_num: int):
    if not isinstance(fact, dict):
        return None
    fact_en = (fact.get("fact_en") or "").strip()
    fact_ta = (fact.get("fact_ta") or "").strip()
    if len(fact_en) < 15:
        return None
    return {
        "fact_en": fact_en,
        "fact_ta": fact_ta,
        "source": f"{BOOK_NAME} Page {page_num}",
        "context_en": topic,
        "context_ta": topic_ta,
    }


def normalized_english(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", (text or "").lower()))


def numeric_values(text: str, tamil: bool = False) -> set[str]:
    values = {
        token.replace(",", "")
        for token in re.findall(r"\d[\d,]*(?:\.\d+)?", text or "")
    }
    crore_pattern = (
        r"(\d+(?:\.\d+)?)\s*(?:கோடி|crore)"
        if tamil
        else r"(\d+(?:\.\d+)?)\s*crore"
    )
    for match in re.finditer(crore_pattern, text or "", re.I):
        original = match.group(1)
        values.discard(original)
        values.add(f"{float(original) * 10:g}")
    return values


def deduplicate(facts: list) -> list:
    kept = []
    normalized = []
    for fact in facts:
        current = normalized_english(fact["fact_en"])
        if not current:
            continue
        duplicate = False
        for previous in normalized:
            if current == previous:
                duplicate = True
                break
            if (
                min(len(current), len(previous)) >= 45
                and difflib.SequenceMatcher(None, current, previous).ratio() >= 0.96
            ):
                duplicate = True
                break
        if not duplicate:
            kept.append(fact)
            normalized.append(current)
    return kept


def qc_facts(topic: str, facts: list, expected_pages: list) -> dict:
    issues = []
    page_counts = {page: 0 for page in expected_pages}
    seen = set()
    for index, fact in enumerate(facts):
        tags = []
        fact_en = (fact.get("fact_en") or "").strip()
        fact_ta = (fact.get("fact_ta") or "").strip()
        source = fact.get("source") or ""
        if len(fact_en) < 15:
            tags.append("english_too_short")
        if not has_tamil(fact_ta):
            tags.append("missing_tamil")
        if re.search(r"\b(?:ngh|tpz|kw;|vd;|fs;|j;j)\w*", fact_ta, re.I):
            tags.append("bamini_gibberish")
        numbers_en = numeric_values(fact_en)
        numbers_ta = numeric_values(fact_ta, tamil=True)
        if numbers_en != numbers_ta:
            tags.append("numeric_translation_mismatch")
        if "billion" in fact_en.lower() and "மில்லியன்" in fact_ta:
            tags.append("magnitude_translation_mismatch")
        if "million" in fact_en.lower() and "பில்லியன்" in fact_ta:
            tags.append("magnitude_translation_mismatch")
        if topic != fact.get("context_en"):
            tags.append("wrong_context")
        match = re.search(r"Page\s+(\d+)", source)
        if not match:
            tags.append("missing_source_page")
        else:
            page = int(match.group(1))
            if page in page_counts:
                page_counts[page] += 1
            else:
                tags.append("source_page_outside_topic")
        norm = normalized_english(fact_en)
        if norm in seen:
            tags.append("exact_duplicate")
        seen.add(norm)
        if tags:
            issues.append(
                {
                    "index": index,
                    "source": source,
                    "fact_en": fact_en[:140],
                    "tags": tags,
                }
            )
    empty_pages = [page for page, count in page_counts.items() if count == 0]
    return {
        "topic": topic,
        "total_facts": len(facts),
        "issue_count": len(issues),
        "page_counts": page_counts,
        "empty_pages": empty_pages,
        "issues": issues,
    }


def load_db() -> dict:
    if not os.path.exists(OUTPUT_JSON):
        return {}
    try:
        data = json.load(open(OUTPUT_JSON, encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_db(data: dict):
    with open(OUTPUT_JSON, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)


def write_qc(db: dict) -> dict:
    reports = {}
    for topic, config in TOPICS.items():
        reports[topic] = qc_facts(topic, db.get(topic) or [], config["pages"])
    with open(QC_PATH, "w", encoding="utf-8") as handle:
        json.dump(reports, handle, indent=2, ensure_ascii=False)
    return reports


def main():
    parser = argparse.ArgumentParser(description="Extract Physics facts from Tamil PDF")
    parser.add_argument("--topic", choices=TOPICS.keys())
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--audit-missing",
        action="store_true",
        help="Second vision pass: add only facts omitted by the first extraction",
    )
    parser.add_argument("--qc-only", action="store_true")
    parser.add_argument("--dpi", type=int, default=200)
    parser.add_argument("--sleep", type=float, default=1.0)
    args = parser.parse_args()

    db = load_db()
    for topic in TOPICS:
        db.setdefault(topic, [])

    if args.qc_only:
        reports = write_qc(db)
        for topic, report in reports.items():
            print(
                f"{topic}: {report['total_facts']} facts | "
                f"issues={report['issue_count']} | empty_pages={report['empty_pages']}"
            )
        return

    if not args.topic:
        print("Choose one topic:")
        for topic in TOPICS:
            print(f"  - {topic}")
        return
    if db.get(args.topic) and not args.force and not args.audit_missing:
        print(
            f"{args.topic} already has {len(db[args.topic])} facts. "
            "Use --force to replace."
        )
        return
    if not os.path.exists(PDF_PATH):
        raise SystemExit(f"PDF missing: {PDF_PATH}")

    config = TOPICS[args.topic]
    topic_ta = config["topic_ta"]
    pages = config["pages"]
    print(f"PDF: {PDF_PATH}")
    print(f"Topic: {args.topic} ({topic_ta}) | physical pages {pages[0]}–{pages[-1]}")
    print(f"Model: {MODEL} | key pool: {len(KEY_POOL)} (gemini_keys())")

    all_facts = []
    document = fitz.open(PDF_PATH)
    try:
        for page_num in pages:
            if args.audit_missing:
                existing_page = load_cache(args.topic, page_num) or []
                print(
                    f"P{page_num}: missing-fact audit "
                    f"({len(existing_page)} existing facts)…"
                )
                raw = call_gemini(
                    render_page(document, page_num, dpi=args.dpi),
                    args.topic,
                    topic_ta,
                    page_num,
                    build_audit_prompt(
                        args.topic, topic_ta, page_num, existing_page
                    ),
                )
                missing = [
                    fact
                    for fact in (
                        normalize_fact(item, args.topic, topic_ta, page_num)
                        for item in raw
                    )
                    if fact
                ]
                combined = deduplicate(existing_page + missing)
                save_cache(args.topic, page_num, combined)
                print(f"  → {len(missing)} candidates; page total {len(combined)}")
                all_facts.extend(combined)
                if args.sleep:
                    time.sleep(args.sleep)
                continue
            cached = None if args.force else load_cache(args.topic, page_num)
            if cached is not None:
                print(f"P{page_num}: cache hit ({len(cached)} facts)")
                all_facts.extend(cached)
                continue
            print(f"P{page_num}: vision extraction…")
            raw = call_gemini(
                render_page(document, page_num, dpi=args.dpi),
                args.topic,
                topic_ta,
                page_num,
            )
            normalized = [
                fact
                for fact in (
                    normalize_fact(item, args.topic, topic_ta, page_num) for item in raw
                )
                if fact
            ]
            save_cache(args.topic, page_num, normalized)
            print(f"  → {len(normalized)} facts")
            all_facts.extend(normalized)
            if args.sleep:
                time.sleep(args.sleep)
    finally:
        document.close()

    deduped = deduplicate(all_facts)
    if not deduped:
        raise SystemExit("Extraction produced zero facts; existing data was not replaced")
    db[args.topic] = deduped
    save_db(db)
    reports = write_qc(db)
    report = reports[args.topic]
    print(f"\nExtracted: {len(all_facts)} | after dedupe: {len(deduped)}")
    print(
        f"QC: issues={report['issue_count']} | empty_pages={report['empty_pages']} | "
        f"page_counts={report['page_counts']}"
    )
    print(f"Saved: {OUTPUT_JSON}")
    print(f"QC report: {QC_PATH}")


if __name__ == "__main__":
    main()
