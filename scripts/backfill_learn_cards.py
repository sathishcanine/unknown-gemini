#!/usr/bin/env python3
"""
Backfill Learn Mode cards: explanation + tip + exam trick (EN+TA).

- Round-robins 4 AI Studio Gemini keys to spread rate limits
- Writes into *_questions_db.json (source of truth)
- Optional --sync-db updates Postgres for live app users

Usage:
  python3 scripts/backfill_learn_cards.py                  # empty explanations only
  python3 scripts/backfill_learn_cards.py --enrich-tips     # also fill tip/trick gaps
  python3 scripts/backfill_learn_cards.py --limit 50
  python3 scripts/backfill_learn_cards.py --paths Aptitude/aptitude_questions_db.json
  python3 scripts/backfill_learn_cards.py --sync-db
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gemini_keys import gemini_keys_ai_studio  # noqa: E402

MODELS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.6-flash"]
SAVE_EVERY = 10

PROMPT = """You are a top TNPSC Group exam coach. Write a crisp Learn Mode card for this MCQ.

Return ONLY JSON:
{{
  "explanation": "2-3 short sentences: why the correct option is right (and the common trap if useful). No fluff.",
  "explanation_ta": "Same meaning in clear Tamil (2-3 short sentences).",
  "learning_tip": "One short, actionable tip (max 18 words) a student can reuse on similar questions.",
  "learning_tip_ta": "Same tip in Tamil (max 18 words).",
  "exam_trick": "One exam shortcut / memory hook / elimination trick (max 16 words).",
  "exam_trick_ta": "Same trick in Tamil (max 16 words)."
}}

Rules:
- Be accurate for TNPSC. Prefer formula/rule/concept over waffle.
- Tip and trick must be SHORT and crisp — not paragraphs.
- Do not invent a different correct answer. Correct option is given.
- If reasoning/picture question, focus on the visual rule.
- English for EN fields; Tamil for TA fields. No mixed-language in one field.

Subject: {subject}
Topic: {topic}
Question (EN): {question_en}
Question (TA): {question_ta}
Options:
{options_block}
Correct option: {correct}
Existing explanation (may be empty): {existing_explanation}
"""


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def discover_dbs(paths: Optional[List[str]]) -> List[Path]:
    if paths:
        return [ROOT / p if not Path(p).is_absolute() else Path(p) for p in paths]
    out = []
    for p in ROOT.rglob("*_questions_db.json"):
        s = str(p)
        if "node_modules" in s or "admin-panel" in s or "_tmp" in s:
            continue
        out.append(p)
    return sorted(out)


def needs_full(q: dict) -> bool:
    return not (q.get("explanation") or "").strip()


def needs_tips(q: dict) -> bool:
    return not (q.get("learning_tip") or "").strip() or not (q.get("exam_trick") or "").strip()


def options_block(q: dict) -> str:
    lines = []
    for o in q.get("options") or []:
        if isinstance(o, dict):
            lines.append(
                f"  {o.get('key')}: {(o.get('text_en') or '')} | {(o.get('text_ta') or '')}"
            )
        else:
            lines.append(f"  {o}")
    return "\n".join(lines) if lines else "  (none)"


def parse_json_loose(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("\n", 1)[0]
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("no JSON object")
    return json.loads(text[start : end + 1])


class KeyRotator:
    def __init__(self, keys: List[str]):
        self.keys = keys or gemini_keys_ai_studio(4)
        self.i = 0
        print(f"Using {len(self.keys)} Gemini keys (round-robin)")

    def next(self) -> str:
        k = self.keys[self.i % len(self.keys)]
        self.i += 1
        return k


def call_gemini(prompt: str, rotator: KeyRotator) -> dict:
    last_err: Optional[Exception] = None
    # Try each key once per model tier, then backoff
    for model in MODELS:
        for _ in range(len(rotator.keys)):
            key = rotator.next()
            key_tag = f"k{(rotator.i - 1) % len(rotator.keys) + 1}/{len(rotator.keys)}"
            delay = 4
            for attempt in range(3):
                try:
                    payload = {
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "responseMimeType": "application/json",
                            "temperature": 0.25,
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
                    with urllib.request.urlopen(req, timeout=120) as resp:
                        body = json.loads(resp.read().decode())
                    cands = body.get("candidates") or []
                    if not cands:
                        raise RuntimeError(f"no candidates {body.get('promptFeedback')}")
                    parts = (cands[0].get("content") or {}).get("parts") or []
                    if not parts or "text" not in parts[0]:
                        raise RuntimeError(f"no text finish={cands[0].get('finishReason')}")
                    data = parse_json_loose(parts[0]["text"])
                    if not (data.get("explanation") or "").strip():
                        raise RuntimeError("empty explanation")
                    return data
                except urllib.error.HTTPError as e:
                    last_err = e
                    code = e.code
                    msg = e.read().decode(errors="ignore")[:200]
                    print(f"  {model} {key_tag} HTTP {code}: {msg}")
                    if code in (429, 503):
                        time.sleep(delay)
                        delay = min(delay * 2, 40)
                        break  # next key
                    if code >= 500:
                        time.sleep(delay)
                        delay = min(delay * 2, 40)
                        continue
                    break
                except Exception as e:
                    last_err = e
                    print(f"  {model} {key_tag} err: {e}")
                    time.sleep(delay)
                    delay = min(delay * 2, 40)
    raise RuntimeError(f"all keys/models failed: {last_err}")


def apply_card(q: dict, card: dict, overwrite_explanation: bool) -> None:
    if overwrite_explanation or not (q.get("explanation") or "").strip():
        q["explanation"] = (card.get("explanation") or "").strip()
        q["explanation_ta"] = (card.get("explanation_ta") or q["explanation"]).strip()
    if not (q.get("learning_tip") or "").strip() or overwrite_explanation:
        q["learning_tip"] = (card.get("learning_tip") or "").strip()
        q["learning_tip_ta"] = (card.get("learning_tip_ta") or q["learning_tip"]).strip()
    if not (q.get("exam_trick") or "").strip() or overwrite_explanation:
        q["exam_trick"] = (card.get("exam_trick") or "").strip()
        q["exam_trick_ta"] = (card.get("exam_trick_ta") or q["exam_trick"]).strip()


def process_file(
    path: Path,
    rotator: KeyRotator,
    enrich_tips: bool,
    limit: Optional[int],
    dry_run: bool,
    topic: Optional[str] = None,
    batch: Optional[str] = None,
) -> Tuple[int, int]:
    data = load_json(path)
    if not isinstance(data, list):
        print(f"skip non-list {path}")
        return 0, 0

    def matches_filters(q: dict) -> bool:
        if topic and (q.get("topic") or "").strip().lower() != topic.strip().lower():
            return False
        if batch and (q.get("batch") or "").strip().lower() != batch.strip().lower():
            return False
        return True

    targets: List[int] = []
    for i, q in enumerate(data):
        if not matches_filters(q):
            continue
        if needs_full(q) or (enrich_tips and needs_tips(q)):
            targets.append(i)
    if limit is not None:
        targets = targets[:limit]

    filt = []
    if topic:
        filt.append(f"topic={topic}")
    if batch:
        filt.append(f"batch={batch}")
    filt_s = (" · " + ", ".join(filt)) if filt else ""
    print(f"\n=== {path.relative_to(ROOT)}{filt_s} · {len(targets)} to fill / {len(data)} total ===")
    if dry_run:
        return len(targets), 0

    done = 0
    for n, idx in enumerate(targets, 1):
        q = data[idx]
        overwrite = needs_full(q)
        prompt = PROMPT.format(
            subject=q.get("subject") or "",
            topic=q.get("topic") or "",
            question_en=(q.get("question_en") or "")[:1200],
            question_ta=(q.get("question_ta") or "")[:1200],
            options_block=options_block(q),
            correct=q.get("correct_option") or "",
            existing_explanation=(q.get("explanation") or "")[:500],
        )
        try:
            card = call_gemini(prompt, rotator)
            apply_card(q, card, overwrite_explanation=overwrite)
            done += 1
            print(
                f"  [{n}/{len(targets)}] OK tip={(q.get('learning_tip') or '')[:48]!r}"
            )
        except Exception as e:
            print(f"  [{n}/{len(targets)}] FAIL: {e}")
            time.sleep(2)
            continue

        if done % SAVE_EVERY == 0:
            save_json(path, data)
            print(f"  … checkpoint saved ({done})")

        time.sleep(0.35)  # gentle pacing across 4 keys

    if done:
        save_json(path, data)
        print(f"  saved {done} updates → {path.name}")
    return len(targets), done


def sync_db(paths: List[Path]) -> None:
    try:
        import psycopg2
    except ImportError:
        print("psycopg2 missing — skip --sync-db")
        return

    db_url = os.getenv(
        "DATABASE_URL",
        "dbname=tnpsc_prep user=sathishkumar password=JYxxR14!lY4@-k_3 host=localhost port=5432",
    )
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute(
        """
        ALTER TABLE questions
          ADD COLUMN IF NOT EXISTS learning_tip TEXT DEFAULT '',
          ADD COLUMN IF NOT EXISTS learning_tip_ta TEXT DEFAULT '',
          ADD COLUMN IF NOT EXISTS exam_trick TEXT DEFAULT '',
          ADD COLUMN IF NOT EXISTS exam_trick_ta TEXT DEFAULT '';
        """
    )
    updated = 0
    for path in paths:
        data = load_json(path)
        if not isinstance(data, list):
            continue
        for q in data:
            q_en = (q.get("question_en") or "").strip()
            if not q_en:
                continue
            exp = (q.get("explanation") or "").strip()
            if not exp and not (q.get("learning_tip") or "").strip():
                continue
            subject = (q.get("subject") or "").strip() or None
            cur.execute(
                """
                UPDATE questions
                SET explanation = COALESCE(NULLIF(%s, ''), explanation),
                    explanation_ta = COALESCE(NULLIF(%s, ''), explanation_ta),
                    learning_tip = COALESCE(NULLIF(%s, ''), learning_tip),
                    learning_tip_ta = COALESCE(NULLIF(%s, ''), learning_tip_ta),
                    exam_trick = COALESCE(NULLIF(%s, ''), exam_trick),
                    exam_trick_ta = COALESCE(NULLIF(%s, ''), exam_trick_ta)
                WHERE question_en = %s
                  AND (%s IS NULL OR subject_id = %s);
                """,
                (
                    exp,
                    (q.get("explanation_ta") or "").strip(),
                    (q.get("learning_tip") or "").strip(),
                    (q.get("learning_tip_ta") or "").strip(),
                    (q.get("exam_trick") or "").strip(),
                    (q.get("exam_trick_ta") or "").strip(),
                    q_en,
                    subject,
                    subject,
                ),
            )
            updated += cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    print(f"DB sync: {updated} rows touched")


def main():
    ap = argparse.ArgumentParser(
        description="Pilot learn cards on ONE batch first; expand later to save AI credits."
    )
    ap.add_argument("--paths", nargs="*", help="Specific *_questions_db.json paths")
    ap.add_argument("--topic", default=None, help="Only this topic (e.g. 'Agriculture S&T')")
    ap.add_argument("--batch", default=None, help="Only this batch (e.g. 'Batch 1')")
    ap.add_argument("--enrich-tips", action="store_true", help="Also fill tip/trick when explanation exists")
    ap.add_argument("--limit", type=int, default=None, help="Max questions per file")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sync-db", action="store_true")
    ap.add_argument("--keys", type=int, default=4, help="How many AIza keys to rotate (default 4)")
    args = ap.parse_args()

    paths = discover_dbs(args.paths)
    if not paths:
        raise SystemExit("No question DB files found")

    # Prefer aptitude + economics gaps first when scanning all
    def sort_key(p: Path):
        name = p.name.lower()
        if "aptitude" in name:
            return (0, str(p))
        if "economic" in name:
            return (1, str(p))
        return (2, str(p))

    paths = sorted(paths, key=sort_key)
    rotator = KeyRotator(gemini_keys_ai_studio(args.keys))

    total_t = total_d = 0
    for path in paths:
        # Skip files with nothing to do quickly
        try:
            data = load_json(path)
        except Exception:
            continue
        if not isinstance(data, list):
            continue
        pending = 0
        for q in data:
            if args.topic and (q.get("topic") or "").strip().lower() != args.topic.strip().lower():
                continue
            if args.batch and (q.get("batch") or "").strip().lower() != args.batch.strip().lower():
                continue
            if needs_full(q) or (args.enrich_tips and needs_tips(q)):
                pending += 1
        if pending == 0:
            continue
        t, d = process_file(
            path,
            rotator,
            args.enrich_tips,
            args.limit,
            args.dry_run,
            topic=args.topic,
            batch=args.batch,
        )
        total_t += t
        total_d += d
        if args.sync_db and not args.dry_run and d > 0:
            print(f"  syncing DB for {path.name}…")
            sync_db([path])

    print(f"\nDone. targeted={total_t} filled={total_d}")
    if args.sync_db and not args.dry_run:
        # Final catch-all sync (also synced per file when --sync-db)
        sync_db(paths)


if __name__ == "__main__":
    main()
