#!/usr/bin/env python3
"""
Transcribe Biology PYQs page-by-page from scanned PDF via Gemini vision.

Source: Data/Biology/BIOLOGY PYQ PDF 2020 -2025.pdf (117 pages, exam-chronological)
Output: Biology/biology_questions_db.json  (type=pyq)
Cache:  Biology/_tmp_pyq_extract_cache/page_XXX.json

Usage:
  python3 Biology/transcribe_biology_pyqs.py                  # all pages
  python3 Biology/transcribe_biology_pyqs.py --start 1 --end 10
  python3 Biology/transcribe_biology_pyqs.py --start 4 --end 4 --force
  python3 Biology/transcribe_biology_pyqs.py --qc-only
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

PDF_PATH = os.path.join(BASE_DIR, "Data", "Biology", "BIOLOGY PYQ PDF 2020 -2025.pdf")
DB_PATH = os.path.join(BASE_DIR, "Biology", "biology_questions_db.json")
CACHE_DIR = os.path.join(BASE_DIR, "Biology", "_tmp_pyq_extract_cache")
QC_PATH = os.path.join(BASE_DIR, "Biology", "biology_pyq_qc_report.json")
MODEL = "gemini-3.1-flash-lite"

KEY_POOL = [DEFAULT_KEY] + [k for k in FALLBACK_KEYS if k.startswith("AQ.")]

BIOLOGY_TOPICS = [
    "The Cell — Basic Unit of Life",
    "Classification of Living Organisms",
    "Nutrition and Food Habits",
    "Respiration",
    "Blood and Circulation",
    "Endocrine System",
    "Reproductive System",
    "Genetics — Mendelism",
    "Environment and Organism Life",
    "Biodiversity and Conservation",
    "Human Diseases — Prevention and Control",
    "Alcoholism and Drug Addiction",
]

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


def cache_path(page_num: int) -> str:
    return os.path.join(CACHE_DIR, f"page_{page_num:03d}.json")


def load_cache(page_num: int):
    path = cache_path(page_num)
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


def save_cache(page_num: int, questions: list):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(cache_path(page_num), "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)


def page_header_hint(doc, page_num: int) -> str:
    """Extract printable header lines (exam name) from PDF text layer."""
    raw = (doc[page_num - 1].get_text() or "").strip()
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    # Drop lone page numbers / subject title noise for hint
    useful = [
        ln
        for ln in lines
        if not ln.isdigit()
        and ln.upper() not in ("SCIENCE - BIOLOGY", "SCIENCE-BIOLOGY")
    ]
    return " | ".join(useful[:4]) if useful else ""


def is_real_exam_header(hint: str) -> bool:
    h = (hint or "").strip()
    if not h:
        return False
    if h.upper() in ("SCIENCE - BIOLOGY", "SCIENCE-BIOLOGY"):
        return False
    # Prefer strings that look like exam titles
    return bool(re.search(r"(?i)exam|g\s*[12]|group|args|gsaso|cegs|iti|recruit", h))


def apply_exam_inheritance(questions: list, exam_name: str) -> list:
    """Force source_exam onto questions when page continues a prior exam section."""
    if not exam_name:
        return questions
    out = []
    for q in questions:
        qq = dict(q)
        se = (qq.get("source_exam") or "").strip()
        if (not se) or se.upper() in ("SCIENCE - BIOLOGY", "SCIENCE-BIOLOGY") or se.startswith("Page "):
            qq["source_exam"] = exam_name
        out.append(qq)
    return out


def render_page_b64(doc, page_num: int, dpi: int = 200) -> str:
    page = doc[page_num - 1]
    pix = page.get_pixmap(dpi=dpi)
    return base64.b64encode(pix.tobytes("png")).decode("utf-8")


def build_prompt(page_num: int, header_hint: str) -> str:
    topics_bullet = "\n".join(f"  - {t}" for t in BIOLOGY_TOPICS)
    return f"""
You are an expert TNPSC Biology PYQ transcriber.
Transcribe EVERY MCQ visible on this scanned page image (page {page_num}).

Page header hint from PDF text layer (may be incomplete): "{header_hint}"

RULES:
1. Transcribe bilingual English + Tamil exactly as printed (fix obvious OCR garble only).
2. Correct answer = the option with a tick / checkmark / highlighted / bold answer key. Do NOT guess from knowledge if mark is visible.
3. Always include option E as "Answer not known" / "விடை தெரியவில்லை".
4. source_exam: use the exam title on this page header (e.g. "ARGS EXAM-2020", "G1 EXAM-2021", "G 2 & 2A EXAM – 2025"). Prefer header_hint when clear.
5. topic: pick the SINGLE best match from this fixed list (do not invent new topics):
{topics_bullet}
   If unclear, use "Classification of Living Organisms" only as last resort when truly general taxonomy; otherwise nearest fit.
6. group: "Group 1" if Group I / G1 / G-1; "Group 2" if Group II / G2 / 2A; else "Other Exams".
7. difficulty: "Medium" or "Hard".
8. Include original printed question number as "pyq_number" (integer) when visible.
9. Skip watermarks ("ASPIRE - TNPSC"), page numbers, blank space. If no MCQs, return [].

Return ONLY a raw JSON array of objects with fields:
- "subject": "Biology"
- "topic": one of the fixed topics above
- "source_exam": string
- "difficulty": "Medium" or "Hard"
- "question_en": string
- "question_ta": string
- "options": [{{"key":"A","text_en":"...","text_ta":"..."}}, ... E]
- "correct_option": "A"|"B"|"C"|"D"
- "explanation": brief English why the marked answer is correct
- "explanation_ta": brief Tamil
- "type": "pyq"
- "group": "Group 1"|"Group 2"|"Other Exams"
- "pyq_number": int or null
- "source_page": {page_num}

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


def call_gemini_ocr(img_b64: str, page_num: int, header_hint: str, api_key: str):
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": build_prompt(page_num, header_hint)},
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
                    print(f"    P{page_num}: {se}")
                    return []
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
                continue
            else:
                print(f"    P{page_num} [Attempt {attempt}/{retries}] HTTP {e.code}: {body[:200]}")
                time.sleep(4)
                api_key = next_api_key()
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
        except Exception as e:
            print(f"    P{page_num} [Attempt {attempt}/{retries}] Error: {e}")
            time.sleep(4)
            try:
                api_key = next_api_key()
            except SystemExit as se:
                print(f"    P{page_num}: {se}")
                return []
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
    return []


def has_tamil(s: str) -> bool:
    return bool(re.search(r"[\u0B80-\u0BFF]", s or ""))


def option_tamil_ok(text_en: str, text_ta: str) -> bool:
    """Tamil required unless option is code-only (match keys / numbers) identical in both langs."""
    en = (text_en or "").strip()
    ta = (text_ta or "").strip()
    if has_tamil(ta):
        return True
    if not en:
        return False
    # Code-only answers (e.g. "(a) 1, (b) 2" or "3 1 4 2") — Tamil often identical
    if en == ta and not re.search(r"[A-Za-z\u0B80-\u0BFF]{3,}", en):
        return True
    if en == ta and re.fullmatch(r"[\d\s,;:\-\(\)a-dA-DivxIVX]+", en):
        return True
    return False


def normalize_question(q: dict, page_num: int, header_hint: str) -> dict | None:
    if not isinstance(q, dict):
        return None
    qen = (q.get("question_en") or "").strip()
    if len(qen) < 8:
        return None

    topic = (q.get("topic") or "").strip()
    if topic not in BIOLOGY_TOPICS:
        # fuzzy contain
        for t in BIOLOGY_TOPICS:
            if t.lower() in topic.lower() or topic.lower() in t.lower():
                topic = t
                break
        else:
            topic = "Classification of Living Organisms"

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
    # Ensure A–D present; always force E
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

    source_exam = (q.get("source_exam") or "").strip() or header_hint or f"Page {page_num}"
    group = (q.get("group") or "Other Exams").strip()
    if group not in ("Group 1", "Group 2", "Other Exams"):
        gl = group.lower()
        if "group 1" in gl or "g1" in gl or "g-1" in gl:
            group = "Group 1"
        elif "group 2" in gl or "g2" in gl or "2a" in gl:
            group = "Group 2"
        else:
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
        "subject": "Biology",
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
    }


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
            expl = ((q.get("explanation") or "") + " " + (q.get("explanation_ta") or "")).lower()
            if any(
                x in expl
                for x in (
                    "under review",
                    "expert committee",
                    "answer withheld",
                    "விடை நிலுவை",
                    "பரிசீலனை",
                )
            ):
                soft_tags.append("answer_under_review")
            else:
                tags.append("correct_option_missing")
        if (q.get("topic") or "") not in BIOLOGY_TOPICS:
            tags.append("topic_invalid")
        if (q.get("type") or "") != "pyq":
            tags.append("type_not_pyq")
        if not (q.get("source_exam") or "").strip():
            tags.append("source_exam_missing")
        if not (q.get("explanation") or "").strip():
            tags.append("explanation_missing")
        if re.search(r"[�]|â€|Ã.", qen) or "???" in qen:
            tags.append("garbled_en")
        entry = {
            "index": i,
            "source_page": q.get("source_page"),
            "pyq_number": q.get("pyq_number"),
            "question_en": qen[:120],
        }
        if tags:
            hard_issues.append({**entry, "tags": tags})
        elif soft_tags:
            soft_issues.append({**entry, "tags": soft_tags})

    by_topic: dict[str, int] = {}
    by_exam: dict[str, int] = {}
    by_page: dict[int, int] = {}
    for q in questions:
        by_topic[q.get("topic") or "?"] = by_topic.get(q.get("topic") or "?", 0) + 1
        by_exam[q.get("source_exam") or "?"] = by_exam.get(q.get("source_exam") or "?", 0) + 1
        p = q.get("source_page")
        if isinstance(p, int):
            by_page[p] = by_page.get(p, 0) + 1

    empty_pages = [p for p in range(1, 118) if by_page.get(p, 0) == 0]
    return {
        "total_pyq": len(questions),
        "issue_count": len(hard_issues),
        "soft_issue_count": len(soft_issues),
        "clean_count": len(questions) - len(hard_issues),
        "by_topic": dict(sorted(by_topic.items(), key=lambda x: -x[1])),
        "by_exam_count": len(by_exam),
        "pages_with_questions": len(by_page),
        "empty_pages_1_117": empty_pages,
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
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)


def merge_pyqs(existing: list, new_qs: list) -> tuple[list, int]:
    """Replace PYQs from overlapping source_pages; keep practice intact."""
    pages_touched = {q.get("source_page") for q in new_qs if q.get("source_page")}
    kept = [
        q
        for q in existing
        if not (q.get("type") == "pyq" and q.get("source_page") in pages_touched)
    ]
    # Also dedupe against remaining PYQs by English stem
    existing_stems = {
        (q.get("question_en") or "").strip().lower()
        for q in kept
        if q.get("type") == "pyq"
    }
    added = 0
    for q in new_qs:
        stem = (q.get("question_en") or "").strip().lower()
        if not stem or stem in existing_stems:
            continue
        kept.append(q)
        existing_stems.add(stem)
        added += 1
    return kept, added


def collect_from_cache(start: int, end: int) -> list:
    all_qs = []
    for p in range(start, end + 1):
        cached = load_cache(p)
        if cached is None:
            continue
        for q in cached:
            nq = normalize_question(q, p, "")
            if nq:
                all_qs.append(nq)
    return all_qs


def run_qc_only():
    db = load_db()
    pyqs = [q for q in db if q.get("type") == "pyq"]
    report = finalize_qc_tag_counts(qc_questions(pyqs))
    with open(QC_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"PYQ total: {report['total_pyq']}")
    print(f"Clean: {report['clean_count']} | Hard issues: {report['issue_count']} | Soft: {report.get('soft_issue_count', 0)}")
    print(f"Pages with Qs: {report['pages_with_questions']} | Empty pages: {len(report['empty_pages_1_117'])}")
    print(f"Topics: {report['by_topic']}")
    print(f"Issue tags: {report['issue_tag_counts']}")
    print(f"Wrote {QC_PATH}")
    if report["issues"][:5]:
        print("Sample hard issues:")
        for iss in report["issues"][:5]:
            print(f"  P{iss.get('source_page')} #{iss.get('pyq_number')}: {iss['tags']} | {iss['question_en'][:80]}")
    if report.get("soft_issues"):
        print("Soft notes (not hard-fails):")
        for iss in report["soft_issues"][:5]:
            print(f"  P{iss.get('source_page')} #{iss.get('pyq_number')}: {iss['tags']} | {iss['question_en'][:80]}")
    return report


def main():
    parser = argparse.ArgumentParser(description="Biology PYQ page-by-page transcriber")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=117)
    parser.add_argument("--force", action="store_true", help="Ignore page cache")
    parser.add_argument("--qc-only", action="store_true", help="QC existing PYQs in DB only")
    parser.add_argument("--dpi", type=int, default=200)
    parser.add_argument("--sleep", type=float, default=1.2, help="Pause between pages")
    args = parser.parse_args()

    if args.qc_only:
        run_qc_only()
        return

    if not os.path.exists(PDF_PATH):
        raise SystemExit(f"PDF not found: {PDF_PATH}")

    doc = fitz.open(PDF_PATH)
    total = len(doc)
    start = max(1, args.start)
    end = min(args.end, total)
    print(f"Biology PYQ transcription | pages {start}-{end} of {total}")
    print(f"Model: {MODEL} | keys: {len(KEY_POOL)} (DEFAULT + AQ)")
    print(f"Cache: {CACHE_DIR}")

    transcribed = []
    last_exam = ""
    for page_num in range(start, end + 1):
        header = page_header_hint(doc, page_num)
        if is_real_exam_header(header):
            last_exam = header
        exam_for_page = last_exam or header

        if not args.force:
            cached = load_cache(page_num)
            if cached is not None:
                cached = apply_exam_inheritance(cached, exam_for_page)
                normalized = []
                for q in cached:
                    nq = normalize_question(q, page_num, exam_for_page)
                    if nq:
                        normalized.append(nq)
                save_cache(page_num, normalized)
                print(f"P{page_num}: cache hit ({len(normalized)} Q) exam='{(exam_for_page or '')[:40]}'")
                transcribed.extend(normalized)
                continue

        print(f"P{page_num}: OCR… exam='{(exam_for_page or '')[:60]}'")
        img_b64 = render_page_b64(doc, page_num, dpi=args.dpi)
        api_key = next_api_key()
        raw_qs = call_gemini_ocr(img_b64, page_num, exam_for_page, api_key)
        normalized = []
        for q in raw_qs:
            nq = normalize_question(q, page_num, exam_for_page)
            if nq:
                normalized.append(nq)
        normalized = apply_exam_inheritance(normalized, exam_for_page)
        save_cache(page_num, normalized)
        print(f"  → {len(normalized)} questions")
        transcribed.extend(normalized)
        if args.sleep > 0:
            time.sleep(args.sleep)

    doc.close()

    # Merge into DB
    existing = load_db()
    practice_n = sum(1 for q in existing if q.get("type") == "practice")
    pyq_before = sum(1 for q in existing if q.get("type") == "pyq")
    merged, added = merge_pyqs(existing, transcribed)
    save_db(merged)
    pyq_after = sum(1 for q in merged if q.get("type") == "pyq")
    print(
        f"\nMerge: +{added} new PYQ stems | practice={practice_n} | "
        f"pyq {pyq_before}→{pyq_after} | total DB={len(merged)}"
    )

    # QC on all PYQs in DB
    report = run_qc_only()
    if report["issue_count"] == 0:
        print("\n✔ QC: all PYQs structurally clean")
    else:
        print(f"\n⚠ QC: {report['issue_count']} questions need review (see {QC_PATH})")


if __name__ == "__main__":
    main()
