#!/usr/bin/env python3
"""
Gemini vision audit for Reasoning With Picture questions.

DROP when figure is unusable / answer leaked / multi-question crop /
not picture-reasoning / stem-options-figure mismatch.
KEEP only clean figure-based MCQs suitable for the app.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

import psycopg2
from psycopg2.extras import Json

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from gemini_keys import gemini_keys  # noqa: E402

OUT = BASE / "Aptitude"
DB_PATH = OUT / "reasoning_picture_questions_db.json"
MEDIA = OUT / "media" / "reasoning"
REPORT = OUT / "reasoning_picture_verify_report.json"
MODELS = ["gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-3.1-flash-lite"]
BATCH_SIZE = 25
TOPIC = "Reasoning With Picture"

PROMPT = """You are QA for a TNPSC mobile quiz app ("Reasoning With Picture").

You receive:
1) The question stem + options + claimed correct answer (JSON)
2) The figure image currently shown to the student

Decide KEEP or DROP. Be STRICT — the user already found many garbage items.

DROP if ANY of these are true:
- answer_leaked: hand-drawn tick/cross/circle/highlight marks the correct option in the image
- bad_crop: image shows multiple questions, cut-off options, page header/footer, or bilingual duplicate of same Q
- unusable_figure: blurry, tiny, empty, wrong crop, watermark dominates readability, figure incomplete
- not_picture_reasoning: solving does NOT need this figure (pure coding-decoding / verbal / series text) OR figure is just a photocopied option list
- mismatch: figure does not match the stem, or options printed in figure contradict app options
- wrong_topic: statistics table / pure aptitude chart misfiled as visual reasoning WITHOUT a usable diagram for a genuine figure Q (tables that ARE the data for the Q may KEEP if clean and no answer mark)
- options_broken: app options empty/garbage relative to figure

KEEP only if:
- figure is a clear, self-contained diagram/dice/mirror/folding/series-figure needed to solve
- no answer mark visible
- stem + options + figure align
- student can solve without seeing the answer in the image

Return ONLY JSON:
{
  "verdict": "KEEP" | "DROP",
  "reasons": ["answer_leaked", ...],
  "detail": "one short sentence",
  "correct_looks_ok": true/false
}
"""


def load_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default if default is not None else {}
    return json.loads(p.read_text(encoding="utf-8"))


def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_image(url: str) -> Path | None:
    if not url:
        return None
    # "/media/aptitude/reasoning/foo.png" → MEDIA/foo.png
    name = Path(url).name
    p = MEDIA / name
    return p if p.exists() else None


def call_gemini(parts, label=""):
    keys = gemini_keys()
    last = None
    for ki, key in enumerate(keys):
        key_tag = f"k{ki+1}/{len(keys)}"
        for model in MODELS:
            delay = 6
            for attempt in range(3):
                try:
                    payload = {
                        "contents": [{"parts": parts}],
                        "generationConfig": {
                            "responseMimeType": "application/json",
                            "temperature": 0,
                        },
                    }
                    url = (
                        f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
                        f":generateContent?key={key}"
                    )
                    req = urllib.request.Request(
                        url,
                        data=json.dumps(payload).encode(),
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    with urllib.request.urlopen(req, timeout=180) as resp:
                        body = json.loads(resp.read().decode())
                    cands = body.get("candidates") or []
                    if not cands:
                        raise RuntimeError(f"no candidates {body.get('promptFeedback')}")
                    parts_out = (cands[0].get("content") or {}).get("parts") or []
                    if not parts_out or "text" not in parts_out[0]:
                        raise RuntimeError("no text")
                    raw = parts_out[0]["text"].strip()
                    if raw.startswith("```"):
                        raw = raw.split("\n", 1)[1]
                        if raw.endswith("```"):
                            raw = raw.rsplit("\n", 1)[0]
                    start = raw.find("{")
                    if start >= 0:
                        depth = 0
                        for i, ch in enumerate(raw[start:], start):
                            if ch == "{":
                                depth += 1
                            elif ch == "}":
                                depth -= 1
                                if depth == 0:
                                    raw = raw[start : i + 1]
                                    break
                    data = json.loads(raw)
                    return data if isinstance(data, dict) else {}
                except urllib.error.HTTPError as e:
                    last = e
                    if e.code in (429, 503):
                        print(
                            f"    {label} {model} {key_tag} HTTP {e.code}; "
                            f"{'next key' if attempt >= 2 else f'sleep {delay}s'}"
                        )
                        if attempt >= 2:
                            break
                        time.sleep(delay)
                        delay = min(delay * 2, 90)
                        continue
                    print(f"    {label} {model} {key_tag} HTTP {e.code}")
                    break
                except Exception as e:
                    last = e
                    print(f"    {label} {model} {key_tag} {type(e).__name__}: {e}")
                    time.sleep(2)
                    break
    raise RuntimeError(f"gemini failed {label}: {last}")


def verify_one(idx: int, q: dict) -> dict:
    urls = q.get("image_urls") or []
    img_path = resolve_image(urls[0]) if urls else None
    meta = {
        "index": idx,
        "batch": q.get("batch"),
        "page": q.get("page"),
        "source_pdf": q.get("source_pdf"),
        "question_en": q.get("question_en"),
        "question_ta": (q.get("question_ta") or "")[:300],
        "options": q.get("options"),
        "correct_option": q.get("correct_option"),
        "image_urls": urls,
    }
    parts = [
        {"text": PROMPT},
        {"text": "QUESTION JSON:\n" + json.dumps(meta, ensure_ascii=False)},
    ]
    if img_path:
        b64 = base64.b64encode(img_path.read_bytes()).decode()
        parts.append({"inline_data": {"mime_type": "image/png", "data": b64}})
    else:
        parts.append({"text": "NO IMAGE FILE FOUND on disk — treat as DROP unusable_figure."})

    try:
        result = call_gemini(parts, label=f"q{idx}")
    except Exception as e:
        return {
            "index": idx,
            "verdict": "DROP",
            "reasons": ["verify_failed"],
            "detail": str(e)[:200],
            "correct_looks_ok": False,
            "question_en": q.get("question_en"),
            "image_urls": urls,
            "batch": q.get("batch"),
        }

    verdict = str(result.get("verdict") or "DROP").upper().strip()
    if verdict not in ("KEEP", "DROP"):
        verdict = "DROP"
    if not img_path:
        verdict = "DROP"
        reasons = list(result.get("reasons") or [])
        if "unusable_figure" not in reasons:
            reasons.append("unusable_figure")
        result["reasons"] = reasons
        result["detail"] = (result.get("detail") or "") + " | missing image file"

    return {
        "index": idx,
        "verdict": verdict,
        "reasons": result.get("reasons") or [],
        "detail": result.get("detail") or "",
        "correct_looks_ok": bool(result.get("correct_looks_ok")),
        "question_en": (q.get("question_en") or "")[:160],
        "image_urls": urls,
        "batch": q.get("batch"),
        "page": q.get("page"),
        "source_pdf": q.get("source_pdf"),
    }


def rebatch(qs: list) -> list:
    for i, q in enumerate(qs):
        bi = i // BATCH_SIZE + 1
        q["batch"] = f"Batch {bi}"
        q["type"] = "practice"
        tags = q.get("tags") or []
        if "pyq" not in [str(t).lower() for t in tags]:
            tags = list(tags) + ["pyq"]
        q["tags"] = tags
        q["topic"] = TOPIC
    return qs


def sync_db(qs: list, db_url: str):
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    # wipe topic questions
    cur.execute(
        """
        DELETE FROM options WHERE question_id IN (
          SELECT q.id FROM questions q JOIN topics t ON t.id=q.topic_id
          WHERE q.subject_id='Aptitude' AND t.name=%s);
        """,
        (TOPIC,),
    )
    cur.execute(
        """
        DELETE FROM questions WHERE id IN (
          SELECT q.id FROM questions q JOIN topics t ON t.id=q.topic_id
          WHERE q.subject_id='Aptitude' AND t.name=%s);
        """,
        (TOPIC,),
    )
    cur.execute(
        "SELECT id FROM topics WHERE subject_id='Aptitude' AND name=%s;",
        (TOPIC,),
    )
    row = cur.fetchone()
    if not row:
        cur.execute(
            "INSERT INTO topics (subject_id, name) VALUES ('Aptitude', %s) RETURNING id;",
            (TOPIC,),
        )
        tid = cur.fetchone()[0]
    else:
        tid = row[0]

    added = 0
    for q in qs:
        q_en = (q.get("question_en") or "").strip()
        if not q_en:
            continue
        cur.execute(
            """
            INSERT INTO questions (
                subject_id, topic_id, question_en, question_ta, correct_option,
                explanation, explanation_ta, difficulty, type, batch, source_exam, source_fact,
                image_urls, tags
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id;
            """,
            (
                "Aptitude",
                tid,
                q_en,
                (q.get("question_ta") or q_en).strip(),
                q.get("correct_option") or "",
                q.get("explanation") or "",
                q.get("explanation_ta") or "",
                q.get("difficulty") or "Medium",
                q.get("type") or "practice",
                q.get("batch") or "",
                q.get("source_exam") or "",
                q.get("source_fact") or "",
                Json(q.get("image_urls") or []),
                Json(q.get("tags") or ["pyq"]),
            ),
        )
        qid = cur.fetchone()[0]
        added += 1
        for oi, opt in enumerate(q.get("options") or []):
            if isinstance(opt, dict):
                key = str(opt.get("key") or "ABCDE"[oi]).strip().upper()[:1]
                te = opt.get("text_en") or ""
                tt = opt.get("text_ta") or te
            else:
                key = "ABCDE"[oi] if oi < 5 else "E"
                te = tt = str(opt)
            cur.execute(
                "INSERT INTO options (question_id, key, text_en, text_ta) VALUES (%s,%s,%s,%s);",
                (qid, key, te, tt),
            )
    conn.commit()
    cur.execute(
        """
        SELECT batch, COUNT(*) FROM questions q JOIN topics t ON t.id=q.topic_id
        WHERE q.subject_id='Aptitude' AND t.name=%s
        GROUP BY batch ORDER BY COALESCE(NULLIF(regexp_replace(batch,'\\D','','g'),'')::int,0);
        """,
        (TOPIC,),
    )
    print("DB batches:", cur.fetchall())
    print(f"DB imported {added}")
    conn.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Drop DROP verdicts, rebatch, write JSON")
    ap.add_argument("--sync-db", action="store_true", help="Re-import kept Qs into local Postgres")
    ap.add_argument("--resume", action="store_true", help="Resume from existing report (skip done indices)")
    ap.add_argument(
        "--db-url",
        default="dbname=tnpsc_prep user=sathishkumar password=JYxxR14!lY4@-k_3 host=localhost port=5432",
    )
    args = ap.parse_args()

    qs = load_json(DB_PATH, [])
    print(f"Loaded {len(qs)} questions")

    report = load_json(REPORT, {"results": []}) if args.resume else {"results": []}
    done = {int(r["index"]) for r in report.get("results") or [] if "index" in r}

    results = list(report.get("results") or [])
    for i, q in enumerate(qs, 1):
        if i in done:
            print(f"  skip q{i} (cached)")
            continue
        print(f"  verify q{i}/{len(qs)} batch={q.get('batch')} page={q.get('page')}…")
        r = verify_one(i, q)
        print(f"    → {r['verdict']} {r.get('reasons')} | {r.get('detail','')[:80]}")
        results.append(r)
        report["results"] = results
        save_json(REPORT, report)
        time.sleep(1.2)

    # normalize order
    results.sort(key=lambda r: int(r.get("index") or 0))
    keep_idx = {int(r["index"]) for r in results if r.get("verdict") == "KEEP"}
    drop_idx = {int(r["index"]) for r in results if r.get("verdict") != "KEEP"}
    reason_counts = Counter()
    for r in results:
        if r.get("verdict") != "KEEP":
            for reason in r.get("reasons") or ["unspecified"]:
                reason_counts[reason] += 1

    report["summary"] = {
        "total": len(qs),
        "keep": len(keep_idx),
        "drop": len(drop_idx),
        "drop_reasons": dict(reason_counts),
    }
    save_json(REPORT, report)
    print("\nSUMMARY", report["summary"])

    if not args.apply:
        print("Dry run only. Re-run with --apply to delete DROPs.")
        return

    kept = [q for i, q in enumerate(qs, 1) if i in keep_idx]
    # remove orphaned images that only belonged to dropped Qs
    kept_imgs = set()
    for q in kept:
        for u in q.get("image_urls") or []:
            kept_imgs.add(Path(u).name)
    for r in results:
        if int(r.get("index") or 0) not in keep_idx:
            for u in r.get("image_urls") or []:
                name = Path(u).name
                if name and name not in kept_imgs:
                    p = MEDIA / name
                    if p.exists():
                        p.unlink()
                        print(f"  deleted media {name}")

    kept = rebatch(kept)
    save_json(DB_PATH, kept)
    print(f"Wrote {len(kept)} kept questions → {DB_PATH}")
    print("Batches:", Counter(q["batch"] for q in kept))

    if args.sync_db:
        sync_db(kept, args.db_url)


if __name__ == "__main__":
    main()
