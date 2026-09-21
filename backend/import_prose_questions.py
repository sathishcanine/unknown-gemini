#!/usr/bin/env python3
"""Import Unit VII Prose questions into Postgres (subject English)."""

import json
import os
from pathlib import Path

import psycopg2

BACKEND_DIR = Path(__file__).resolve().parent
ROOT = BACKEND_DIR.parent
DB_PATH = ROOT / "English" / "Prose" / "prose_questions_db.json"

SUBJECT_ID = "English"
SUBJECT_NAME = "General English"
SUBJECT_NAME_TA = "பொது ஆங்கிலம்"
SUBJECT_ICON = "EN"


def main():
    db_url = os.getenv(
        "DATABASE_URL",
        "dbname=tnpsc_prep user=sathishkumar password=JYxxR14!lY4@-k_3 host=localhost port=5432",
    )
    print(f"Connecting: {db_url}")
    if not DB_PATH.exists():
        print(f"Missing {DB_PATH}")
        return

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("SELECT id FROM subjects WHERE id=%s;", (SUBJECT_ID,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO subjects (id, name, name_ta, icon) VALUES (%s,%s,%s,%s);",
            (SUBJECT_ID, SUBJECT_NAME, SUBJECT_NAME_TA, SUBJECT_ICON),
        )

    def get_or_create_topic(name):
        cur.execute(
            "SELECT id FROM topics WHERE subject_id=%s AND name=%s;",
            (SUBJECT_ID, name),
        )
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute(
            "INSERT INTO topics (subject_id, name) VALUES (%s,%s) RETURNING id;",
            (SUBJECT_ID, name),
        )
        print(f"Created topic: {name}")
        return cur.fetchone()[0]

    questions = json.loads(DB_PATH.read_text(encoding="utf-8"))
    added = skipped = 0
    for q in questions:
        topic_name = (q.get("topic") or "").strip()
        if not topic_name:
            continue
        tid = get_or_create_topic(topic_name)
        q_en = (q.get("question_en") or "").strip()
        q_ta = (q.get("question_ta") or q_en).strip()
        if not q_en:
            continue
        cur.execute(
            """
            SELECT id FROM questions
            WHERE subject_id=%s AND topic_id=%s
              AND (LOWER(TRIM(question_en))=LOWER(%s) OR LOWER(TRIM(question_ta))=LOWER(%s));
            """,
            (SUBJECT_ID, tid, q_en, q_ta),
        )
        if cur.fetchone():
            skipped += 1
            continue
        cur.execute(
            """
            INSERT INTO questions (
                subject_id, topic_id, question_en, question_ta, correct_option,
                explanation, explanation_ta, difficulty, type, batch, source_exam, source_fact
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id;
            """,
            (
                SUBJECT_ID,
                tid,
                q_en,
                q_ta,
                q.get("correct_option") or "",
                q.get("explanation") or "",
                q.get("explanation_ta") or "",
                q.get("difficulty") or "Medium",
                q.get("type") or "practice",
                q.get("batch") or "Batch 1",
                q.get("source_exam") or "",
                q.get("source_note") or "",
            ),
        )
        qid = cur.fetchone()[0]
        added += 1
        for idx, opt in enumerate(q.get("options") or []):
            if isinstance(opt, dict):
                key = str(opt.get("key") or "ABCDE"[idx]).strip().upper()[:1]
                te = opt.get("text_en") or ""
                tt = opt.get("text_ta") or te
            else:
                key = "ABCDE"[idx] if idx < 5 else "E"
                te = tt = str(opt)
            cur.execute(
                "INSERT INTO options (question_id, key, text_en, text_ta) VALUES (%s,%s,%s,%s);",
                (qid, key, te, tt),
            )

    conn.commit()
    cur.execute(
        """
        SELECT t.name, COUNT(*)
        FROM questions q JOIN topics t ON t.id=q.topic_id
        WHERE q.subject_id=%s AND t.name = ANY(%s)
        GROUP BY t.name ORDER BY t.name;
        """,
        (SUBJECT_ID, sorted({(q.get("topic") or "") for q in questions})),
    )
    for name, n in cur.fetchall():
        print(f"  {name}: {n}")
    cur.execute("SELECT COUNT(*) FROM questions WHERE subject_id=%s;", (SUBJECT_ID,))
    print(f"Imported {added} new; skipped {skipped}. English total={cur.fetchone()[0]}")
    conn.close()


if __name__ == "__main__":
    main()
