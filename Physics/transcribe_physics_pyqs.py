#!/usr/bin/env python3
"""
Transcribe Physics PYQs from Nayakan Academy multi-PDF series (page-by-page).

Sources (Data/physics/):
  PHYSICS 02 — Units and Measurements (Topic 79)
  PHYSICS 03 — Force, Motion and Energy (Topic 80)
  PHYSICS 04 — Electricity (Topic 81)
  PHYSICS 05 — Magnetism / Light / Sound / Heat / Nuclear (Topic 82)

Note: PHYSICS 01 was not present in Data/physics/ at extraction time.

Usage:
  python3 Physics/transcribe_physics_pyqs.py
  python3 Physics/transcribe_physics_pyqs.py --pdf phys02 --start 2 --end 5
  python3 Physics/transcribe_physics_pyqs.py --force
  python3 Physics/transcribe_physics_pyqs.py --qc-only
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

import fitz  # PyMuPDF

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from gemini_keys import DEFAULT_KEY, FALLBACK_KEYS  # noqa: E402

PDF_DIR = os.path.join(BASE_DIR, "Data", "physics")
DB_PATH = os.path.join(BASE_DIR, "Physics", "physics_questions_db.json")
CACHE_DIR = os.path.join(BASE_DIR, "Physics", "_tmp_pyq_extract_cache")
QC_PATH = os.path.join(BASE_DIR, "Physics", "physics_pyq_qc_report.json")
MODEL = "gemini-3.1-flash-lite"

KEY_POOL = [DEFAULT_KEY] + [k for k in FALLBACK_KEYS if k.startswith("AQ.")]

# Finer topics for PDF 05 classification; PDFs 02–04 use their default topic.
PHYSICS_TOPICS = [
    "Units and Measurements",
    "Force, Motion and Energy",
    "Electricity",
    "Magnetism",
    "Light and Optics",
    "Sound",
    "Heat and Thermodynamics",
    "Nuclear Physics",
]

PHYSICS_PDFS = [
    {
        "id": "phys02",
        "file": "(QUN)- (PHYSICS 2 PYQ).pdf",
        "series": "PHYSICS 02",
        "series_topic": 79,
        "default_topic": "Units and Measurements",
        "skip_pages": {1},  # cover
    },
    {
        "id": "phys03",
        "file": "(QUN)- (PHYSICS 3 PYQ) (1).pdf",
        "series": "PHYSICS 03",
        "series_topic": 80,
        "default_topic": "Force, Motion and Energy",
        "skip_pages": {1},
    },
    {
        "id": "phys04",
        "file": "(QUN)- (PHYSICS 4 PYQ).pdf",
        "series": "PHYSICS 04",
        "series_topic": 81,
        "default_topic": "Electricity",
        "skip_pages": {1},
    },
    {
        "id": "phys05",
        "file": "(QUN)- (PHYSICS 5 PYQ).pdf",
        "series": "PHYSICS 05",
        "series_topic": 82,
        "default_topic": "Magnetism",  # cover spans Mag/Light/Sound/Heat/Nuclear — classify per Q
        "skip_pages": {1},
        "classify_subtopics": True,
    },
]

# A question split across two PDF pages is sometimes transcribed twice: once with
# its printed number and once from the continuation page without a number.
# Map genuine unnumbered questions to their printed sequence number; omit known
# continuation duplicates. This preserves every source question exactly once.
UNNUMBERED_PAGE_MAP = {
    "phys02": {5: 6, 9: None, 10: 14, 11: 16, 13: None},
    "phys03": {
        4: None,
        7: None,
        9: None,
        10: 13,
        12: 16,
        14: 19,
        17: None,
        19: 27,
        21: None,
        23: None,
        24: None,
        27: None,
        30: None,
    },
    "phys04": {3: None, 4: 4, 8: None, 10: None, 13: None, 14: None},
    "phys05": {
        5: None,
        6: None,
        7: None,
        9: 14,
        11: None,
        16: None,
        23: None,
        24: 39,
        26: 42,
        29: None,
    },
}

_key_idx = 0
_rate_limit_hits = 0
_disabled_keys: set[str] = set()


def next_api_key() -> str:
    global _key_idx
    if not KEY_POOL:
        raise SystemExit("KEY_POOL empty")
    for _ in range(len(KEY_POOL) * 2):
        key = KEY_POOL[_key_idx % len(KEY_POOL)]
        _key_idx += 1
        if key not in _disabled_keys:
            return key
    raise SystemExit(f"All {len(KEY_POOL)} keys disabled for model {MODEL}")


def disable_key(api_key: str, reason: str):
    if api_key in _disabled_keys:
        return
    _disabled_keys.add(api_key)
    tag = "DEFAULT" if api_key == DEFAULT_KEY else ("AQ" if api_key.startswith("AQ.") else "key")
    print(f"    ⚠ Disabling {tag}…{api_key[-6:]} for {MODEL}: {reason}")


def note_rate_limit(page_num: int, code: int, delay: int):
    global _rate_limit_hits
    _rate_limit_hits += 1
    print(
        f"    ⚠ RATE LIMIT HTTP {code} on P{page_num} "
        f"(hit #{_rate_limit_hits}); rotate key, sleep {delay}s..."
    )


def cache_path(pdf_id: str, page_num: int) -> str:
    return os.path.join(CACHE_DIR, f"{pdf_id}_page_{page_num:03d}.json")


def load_cache(pdf_id: str, page_num: int):
    path = cache_path(pdf_id, page_num)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return None


def save_cache(pdf_id: str, page_num: int, questions: list):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(cache_path(pdf_id, page_num), "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)


def clean_page_text(raw: str) -> str:
    lines = []
    for ln in (raw or "").splitlines():
        s = ln.strip()
        if not s:
            continue
        low = s.lower()
        if "telegram" in low or "9626568454" in s or "nayakan" in low:
            continue
        if s.upper() in ("JOIN", "TELEGRAM"):
            continue
        lines.append(s)
    return "\n".join(lines)


def render_page_b64(doc, page_num: int, dpi: int = 200) -> str:
    page = doc[page_num - 1]
    pix = page.get_pixmap(dpi=dpi)
    return base64.b64encode(pix.tobytes("png")).decode("utf-8")


def build_prompt(meta: dict, page_num: int, page_text: str) -> str:
    topics_bullet = "\n".join(f"  - {t}" for t in PHYSICS_TOPICS)
    default_topic = meta["default_topic"]
    classify = meta.get("classify_subtopics", False)
    topic_rule = (
        f"Pick the SINGLE best topic from the list below (page may mix sections):\n{topics_bullet}"
        if classify
        else f'Use topic "{default_topic}" for every question on this page (override only if clearly wrong).'
    )
    return f"""
You are an expert TNPSC Physics PYQ transcriber.
Transcribe EVERY MCQ on this page image (PDF page {page_num}).
Series: {meta["series"]} | PYQ SERIES TOPIC {meta["series_topic"]} | Default topic: {default_topic}

PDF text layer (may have garbled Tamil — prefer the IMAGE for Tamil; use text for English/formulas):
---
{page_text[:6000]}
---

RULES:
1. Bilingual English + Tamil. Fix garbled Tamil from the image when possible; keep accurate Unicode.
2. These PDFs usually have NO answer ticks. Deduce the scientifically correct option (A–D). If truly ambiguous, still pick the best option and say so in explanation.
3. Always include option E as "Answer not known" / "விடை தெரியவில்லை".
4. source_exam: "{meta["series"]} Topic {meta["series_topic"]} (Nayakan Academy PYQ)"
5. topic: {topic_rule}
6. group: "Other Exams" (academy PYQ compilation) unless a specific TNPSC group exam is printed on the question.
7. difficulty: "Medium" or "Hard".
8. pyq_number: printed question number (int) when visible.
9. Skip cover/ad/telegram fluff. If no MCQs, return [].
10. Preserve formulas/symbols carefully (μ₀, ε₀, ∝, √, °C, etc.).

Return ONLY a raw JSON array:
- "subject": "Physics"
- "topic": one of the fixed Physics topics
- "source_exam": string
- "difficulty": "Medium"|"Hard"
- "question_en": string
- "question_ta": string
- "options": [{{"key":"A","text_en":"...","text_ta":"..."}}, ... through E]
- "correct_option": "A"|"B"|"C"|"D"
- "explanation": brief English
- "explanation_ta": brief Tamil
- "type": "pyq"
- "group": "Group 1"|"Group 2"|"Other Exams"
- "pyq_number": int|null
- "source_page": {page_num}
- "source_pdf": "{meta["id"]}"

No markdown fences. No commentary.
""".strip()


def parse_json_array(raw_text: str):
    text = (raw_text or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("\n", 1)[0]
    start_idx = text.find("[")
    if start_idx == -1:
        return []
    count = 0
    for idx in range(start_idx, len(text)):
        if text[idx] == "[":
            count += 1
        elif text[idx] == "]":
            count -= 1
            if count == 0:
                text = text[start_idx : idx + 1]
                break
    data = json.loads(text.strip())
    return data if isinstance(data, list) else []


def call_gemini(img_b64: str, meta: dict, page_num: int, page_text: str, api_key: str):
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": build_prompt(meta, page_num, page_text)},
                    {"inlineData": {"mimeType": "image/png", "data": img_b64}},
                ]
            }
        ],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    retries = 5
    delay = 8
    label = f"{meta['id']}:P{page_num}"
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as response:
                res_json = json.loads(response.read().decode("utf-8"))
                raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                return parse_json_array(raw_text)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            if e.code in (429, 503):
                note_rate_limit(page_num, e.code, delay)
                time.sleep(delay)
                delay = min(delay * 2, 90)
                api_key = next_api_key()
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
            elif e.code == 404 and "no longer available" in body.lower():
                disable_key(api_key, "model not available to this key")
                try:
                    api_key = next_api_key()
                except SystemExit as se:
                    print(f"    {label}: {se}")
                    return []
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
                continue
            else:
                print(f"    {label} [Attempt {attempt}/{retries}] HTTP {e.code}: {body[:200]}")
                time.sleep(4)
                api_key = next_api_key()
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
        except Exception as e:
            print(f"    {label} [Attempt {attempt}/{retries}] Error: {e}")
            time.sleep(4)
            try:
                api_key = next_api_key()
            except SystemExit as se:
                print(f"    {label}: {se}")
                return []
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
    return []


def has_tamil(s: str) -> bool:
    return bool(re.search(r"[\u0B80-\u0BFF]", s or ""))


def option_tamil_ok(text_en: str, text_ta: str) -> bool:
    en = (text_en or "").strip()
    ta = (text_ta or "").strip()
    if has_tamil(ta):
        return True
    if not en:
        return False
    if en == ta and not re.search(r"[A-Za-z\u0B80-\u0BFF]{3,}", en):
        return True
    if en == ta and re.fullmatch(r"[\d\s,;:\-\(\)a-dA-DivxIVX°μ₀ε∝√+\-/=.⁻¹²³⁰]+", en):
        return True
    # Formula / unit / acronym options often identical EN/TA
    if en == ta and re.search(r"[μ₀ε√∝°±≤≥⁻]|Nsm|kgm|UHF|VHF|SHF|THF|Nm", en):
        return True
    if en == ta and len(en) <= 24 and not re.search(r"[a-z]{4,}", en):
        # short symbol/acronym lines (e.g. VHF, UHF)
        return True
    return False


def normalize_question(q: dict, meta: dict, page_num: int) -> dict | None:
    if not isinstance(q, dict):
        return None
    qen = (q.get("question_en") or "").strip()
    if len(qen) < 8:
        return None

    topic = (q.get("topic") or "").strip()
    if topic not in PHYSICS_TOPICS:
        for t in PHYSICS_TOPICS:
            if t.lower() in topic.lower() or topic.lower() in t.lower():
                topic = t
                break
        else:
            topic = meta["default_topic"]
    # Prefer model topic when valid (PDFs can spill across syllabus sections).

    opts = q.get("options") or []
    by_key = {}
    for o in opts:
        if not isinstance(o, dict):
            continue
        k = (o.get("key") or "").strip().upper()
        if k in "ABCDE":
            by_key[k] = {
                "key": k,
                "text_en": (o.get("text_en") or "").strip(),
                "text_ta": (o.get("text_ta") or "").strip(),
            }
    for k in "ABCD":
        if k not in by_key:
            by_key[k] = {"key": k, "text_en": "", "text_ta": ""}
    by_key["E"] = {
        "key": "E",
        "text_en": "Answer not known",
        "text_ta": "விடை தெரியவில்லை",
    }
    options = [by_key[k] for k in "ABCDE"]

    correct = (q.get("correct_option") or "").strip().upper()
    if correct not in "ABCD":
        correct = ""

    source_exam = (q.get("source_exam") or "").strip() or (
        f"{meta['series']} Topic {meta['series_topic']} (Nayakan Academy PYQ)"
    )
    group = (q.get("group") or "Other Exams").strip()
    if group not in ("Group 1", "Group 2", "Other Exams"):
        group = "Other Exams"

    difficulty = (q.get("difficulty") or "Medium").strip()
    if difficulty not in ("Medium", "Hard"):
        difficulty = "Medium"

    pyq_number = q.get("pyq_number")
    try:
        pyq_number = int(pyq_number) if pyq_number is not None else None
    except (TypeError, ValueError):
        pyq_number = None

    return {
        "subject": "Physics",
        "topic": topic,
        "source_exam": source_exam,
        "difficulty": difficulty,
        "question_en": qen,
        "question_ta": (q.get("question_ta") or "").strip(),
        "options": options,
        "correct_option": correct,
        "explanation": (q.get("explanation") or "").strip(),
        "explanation_ta": (q.get("explanation_ta") or "").strip(),
        "type": "pyq",
        "group": group,
        "pyq_number": pyq_number,
        "source_page": page_num,
        "source_pdf": meta["id"],
    }


def curate_page_questions(questions: list, meta: dict, page_num: int) -> list:
    """Normalize a page and resolve known cross-page continuation duplicates."""
    result = []
    unnumbered_target = UNNUMBERED_PAGE_MAP.get(meta["id"], {}).get(page_num, "unmapped")
    for q in questions:
        nq = normalize_question(q, meta, page_num)
        if not nq:
            continue
        if nq.get("pyq_number") is None and unnumbered_target != "unmapped":
            if unnumbered_target is None:
                continue
            nq["pyq_number"] = unnumbered_target
        result.append(nq)
    return result


def qc_questions(questions: list) -> dict:
    hard_issues = []
    soft_issues = []
    for i, q in enumerate(questions):
        tags = []
        soft_tags = []
        qen = q.get("question_en") or ""
        qta = q.get("question_ta") or ""
        if len(qen) < 12:
            tags.append("stem_too_short")
        if not has_tamil(qta):
            tags.append("missing_tamil_stem")
        opts = q.get("options") or []
        if len(opts) != 5:
            tags.append("options_count_ne_5")
        keys = [o.get("key") for o in opts]
        if keys != ["A", "B", "C", "D", "E"]:
            tags.append("options_keys_bad")
        for o in opts:
            if o.get("key") == "E":
                continue
            if not (o.get("text_en") or "").strip():
                tags.append(f"empty_en_opt_{o.get('key')}")
            if not option_tamil_ok(o.get("text_en") or "", o.get("text_ta") or ""):
                tags.append(f"missing_ta_opt_{o.get('key')}")
        e = next((o for o in opts if o.get("key") == "E"), None)
        if not e or (e.get("text_en") or "").lower() not in ("answer not known", "answer not known."):
            tags.append("option_e_bad")
        corr = q.get("correct_option")
        if corr not in ("A", "B", "C", "D"):
            tags.append("correct_option_missing")
        if (q.get("topic") or "") not in PHYSICS_TOPICS:
            tags.append("topic_invalid")
        if (q.get("type") or "") != "pyq":
            tags.append("type_not_pyq")
        if not (q.get("source_exam") or "").strip():
            tags.append("source_exam_missing")
        if not (q.get("explanation") or "").strip():
            soft_tags.append("explanation_missing")
        if re.search(r"[�]|â€|Ã.", qen) or "???" in qen:
            tags.append("garbled_en")
        entry = {
            "index": i,
            "source_pdf": q.get("source_pdf"),
            "source_page": q.get("source_page"),
            "pyq_number": q.get("pyq_number"),
            "question_en": qen[:120],
        }
        if tags:
            hard_issues.append({**entry, "tags": tags})
        elif soft_tags:
            soft_issues.append({**entry, "tags": soft_tags})

    by_topic: dict[str, int] = {}
    by_pdf: dict[str, int] = {}
    for q in questions:
        by_topic[q.get("topic") or "?"] = by_topic.get(q.get("topic") or "?", 0) + 1
        by_pdf[q.get("source_pdf") or "?"] = by_pdf.get(q.get("source_pdf") or "?", 0) + 1

    return {
        "total_pyq": len(questions),
        "issue_count": len(hard_issues),
        "soft_issue_count": len(soft_issues),
        "clean_count": len(questions) - len(hard_issues),
        "by_topic": dict(sorted(by_topic.items(), key=lambda x: -x[1])),
        "by_pdf": by_pdf,
        "issues": hard_issues[:200],
        "soft_issues": soft_issues[:50],
        "issue_tag_counts": {},
    }


def finalize_qc_tag_counts(report: dict):
    counts: dict[str, int] = {}
    for item in report.get("issues") or []:
        for t in item.get("tags") or []:
            counts[t] = counts.get(t, 0) + 1
    report["issue_tag_counts"] = dict(sorted(counts.items(), key=lambda x: -x[1]))
    return report


def load_db() -> list:
    if not os.path.exists(DB_PATH):
        return []
    with open(DB_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception:
            return []


def save_db(questions: list):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)


def merge_pyqs(existing: list, new_qs: list) -> tuple[list, int]:
    """Replace touched pages while preserving every numbered source occurrence."""
    touched = {(q.get("source_pdf"), q.get("source_page")) for q in new_qs}
    kept = [
        q
        for q in existing
        if not (q.get("type") == "pyq" and (q.get("source_pdf"), q.get("source_page")) in touched)
    ]
    by_source: dict[tuple, dict] = {}
    for q in kept:
        if q.get("type") != "pyq":
            continue
        key = (
            q.get("source_pdf"),
            q.get("pyq_number"),
            q.get("source_page") if q.get("pyq_number") is None else None,
        )
        by_source[key] = q
    kept = [q for q in kept if q.get("type") != "pyq"]
    added = 0
    for q in new_qs:
        if not (q.get("question_en") or "").strip():
            continue
        key = (
            q.get("source_pdf"),
            q.get("pyq_number"),
            q.get("source_page") if q.get("pyq_number") is None else None,
        )
        if key not in by_source:
            added += 1
        by_source[key] = q
    kept.extend(by_source.values())
    return kept, added


def run_qc_only():
    db = load_db()
    pyqs = [q for q in db if q.get("type") == "pyq"]
    report = finalize_qc_tag_counts(qc_questions(pyqs))
    with open(QC_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"PYQ total: {report['total_pyq']}")
    print(
        f"Clean: {report['clean_count']} | Hard issues: {report['issue_count']} | "
        f"Soft: {report.get('soft_issue_count', 0)}"
    )
    print(f"By PDF: {report.get('by_pdf')}")
    print(f"Topics: {report['by_topic']}")
    print(f"Issue tags: {report['issue_tag_counts']}")
    print(f"Wrote {QC_PATH}")
    if report["issues"][:5]:
        print("Sample hard issues:")
        for iss in report["issues"][:5]:
            print(
                f"  {iss.get('source_pdf')} P{iss.get('source_page')} "
                f"#{iss.get('pyq_number')}: {iss['tags']} | {iss['question_en'][:80]}"
            )
    if report.get("soft_issues"):
        print("Soft notes:")
        for iss in report["soft_issues"][:5]:
            print(
                f"  {iss.get('source_pdf')} P{iss.get('source_page')} "
                f"#{iss.get('pyq_number')}: {iss['tags']}"
            )
    return report


def process_pdf(meta: dict, start: int | None, end: int | None, force: bool, dpi: int, sleep: float):
    pdf_path = os.path.join(PDF_DIR, meta["file"])
    if not os.path.exists(pdf_path):
        print(f"⚠ Missing PDF: {pdf_path}")
        return []

    doc = fitz.open(pdf_path)
    total = len(doc)
    page_start = start or 1
    page_end = end or total
    page_start = max(1, page_start)
    page_end = min(page_end, total)
    print(f"\n=== {meta['id']} | {meta['series']} | {meta['default_topic']} | pages {page_start}-{page_end}/{total} ===")

    transcribed = []
    for page_num in range(page_start, page_end + 1):
        if page_num in meta.get("skip_pages", set()):
            print(f"{meta['id']} P{page_num}: skip (cover/ad)")
            save_cache(meta["id"], page_num, [])
            continue

        if not force:
            cached = load_cache(meta["id"], page_num)
            if cached is not None:
                normalized = curate_page_questions(cached, meta, page_num)
                print(f"{meta['id']} P{page_num}: cache hit ({len(normalized)} Q)")
                transcribed.extend(normalized)
                continue

        page_text = clean_page_text(doc[page_num - 1].get_text() or "")
        print(f"{meta['id']} P{page_num}: OCR…")
        img_b64 = render_page_b64(doc, page_num, dpi=dpi)
        api_key = next_api_key()
        raw_qs = call_gemini(img_b64, meta, page_num, page_text, api_key)
        normalized = curate_page_questions(raw_qs, meta, page_num)
        # Keep raw normalized rows in cache; curation remains reproducible when read.
        save_cache(
            meta["id"],
            page_num,
            [q for q in (normalize_question(q, meta, page_num) for q in raw_qs) if q],
        )
        print(f"  → {len(normalized)} questions")
        transcribed.extend(normalized)
        if sleep > 0:
            time.sleep(sleep)

    doc.close()
    return transcribed


def main():
    parser = argparse.ArgumentParser(description="Physics PYQ multi-PDF transcriber")
    parser.add_argument("--pdf", choices=[p["id"] for p in PHYSICS_PDFS], help="Single PDF id")
    parser.add_argument("--start", type=int, default=None)
    parser.add_argument("--end", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--qc-only", action="store_true")
    parser.add_argument("--dpi", type=int, default=200)
    parser.add_argument("--sleep", type=float, default=1.0)
    args = parser.parse_args()

    if args.qc_only:
        run_qc_only()
        return

    print(f"Physics PYQ transcription | Model: {MODEL} | keys: {len(KEY_POOL)}")
    print(f"PDF dir: {PDF_DIR}")
    print("Note: PHYSICS 01 not found in Data/physics/ — extracting PHYSICS 02–05 only.")

    metas = [p for p in PHYSICS_PDFS if (not args.pdf or p["id"] == args.pdf)]
    all_new = []
    for meta in metas:
        all_new.extend(
            process_pdf(meta, args.start, args.end, args.force, args.dpi, args.sleep)
        )

    existing = load_db()
    pyq_before = sum(1 for q in existing if q.get("type") == "pyq")
    if args.start is None and args.end is None:
        # A full selected-PDF rebuild must also remove stale continuation rows
        # from pages whose curated result is now empty.
        selected_ids = {meta["id"] for meta in metas}
        existing = [
            q
            for q in existing
            if not (q.get("type") == "pyq" and q.get("source_pdf") in selected_ids)
        ]
    merged, added = merge_pyqs(existing, all_new)
    save_db(merged)
    pyq_after = sum(1 for q in merged if q.get("type") == "pyq")
    print(f"\nMerge: +{added} new stems | pyq {pyq_before}→{pyq_after} | total DB={len(merged)}")

    report = run_qc_only()
    if report["issue_count"] == 0:
        print("\n✔ QC: all Physics PYQs structurally clean")
    else:
        print(f"\n⚠ QC: {report['issue_count']} hard issues — see {QC_PATH}")


if __name__ == "__main__":
    main()
