#!/usr/bin/env python3
"""Import Phrases & Clauses questions into Postgres (subject English)."""

import json
import os

import psycopg2

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BACKEND_DIR)
DB_PATH = os.path.join(ROOT_DIR, "English", "Grammar", "phrases_clauses_questions_db.json")

SUBJECT_ID = "English"
SUBJECT_NAME = "General English"
SUBJECT_NAME_TA = "பொது ஆங்கிலம்"
SUBJECT_ICON = "EN"
TOPIC_NAME = "Phrases & Clauses"


def main():
    db_url = os.getenv(
        "DATABASE_URL", "dbname=tnpsc_prep user=sathishkumar host=localhost port=5432"
    )
    print(f"Connecting: {db_url}")
    if not os.path.exists(DB_PATH):
        print(f"Missing {DB_PATH}")
        return

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM subjects WHERE id = %s;", (SUBJECT_ID,))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO subjects (id, name, name_ta, icon) VALUES (%s, %s, %s, %s);",
            (SUBJECT_ID, SUBJECT_NAME, SUBJECT_NAME_TA, SUBJECT_ICON),
        )

    def get_or_create_topic(topic_name):
        key = topic_name.strip()
        cursor.execute(
            "SELECT id FROM topics WHERE subject_id = %s AND name = %s;",
            (SUBJECT_ID, key),
        )
        row = cursor.fetchone()
        if row:
            return row[0]
        cursor.execute(
            "INSERT INTO topics (subject_id, name) VALUES (%s, %s) RETURNING id;",
            (SUBJECT_ID, key),
        )
        print(f"Created topic: {key}")
        return cursor.fetchone()[0]

    with open(DB_PATH, "r", encoding="utf-8") as f:
        questions = json.load(f)

    added = 0
    skipped = 0
    for q in questions:
        topic_name = (q.get("topic") or TOPIC_NAME).strip()
        topic_id = get_or_create_topic(topic_name)
        q_en = (q.get("question_en") or "").strip()
        q_ta = (q.get("question_ta") or q_en).strip()
        if not q_en:
            continue
        cursor.execute(
            """
            SELECT id FROM questions
            WHERE subject_id = %s AND topic_id = %s
              AND (LOWER(TRIM(question_en)) = LOWER(%s) OR LOWER(TRIM(question_ta)) = LOWER(%s));
            """,
            (SUBJECT_ID, topic_id, q_en, q_ta),
        )
        if cursor.fetchone():
            skipped += 1
            continue

        cursor.execute(
            """
            INSERT INTO questions (
                subject_id, topic_id, question_en, question_ta, correct_option,
                explanation, explanation_ta, difficulty, type, batch, source_exam, source_fact
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id;
            """,
            (
                SUBJECT_ID,
                topic_id,
                q_en,
                q_ta,
                q.get("correct_option") or "",
                q.get("explanation") or "",
                q.get("explanation_ta") or "",
                q.get("difficulty") or "Medium",
                q.get("type") or "practice",
                q.get("batch") or "",
                q.get("source_exam") or "",
                q.get("source_note") or q.get("source_fact") or "",
            ),
        )
        qid = cursor.fetchone()[0]
        added += 1
        letters = ["A", "B", "C", "D", "E"]
        for idx, opt in enumerate(q.get("options") or []):
            if isinstance(opt, dict):
                key = str(opt.get("key") or letters[idx]).strip().upper()[:1]
                te = opt.get("text_en") or ""
                tt = opt.get("text_ta") or te
            else:
                key = letters[idx] if idx < 5 else "E"
                te = str(opt)
                tt = te
            cursor.execute(
                "INSERT INTO options (question_id, key, text_en, text_ta) VALUES (%s,%s,%s,%s);",
                (qid, key, te, tt),
            )

    conn.commit()
    cursor.execute(
        """
        SELECT t.name, q.batch, COUNT(*)
        FROM questions q JOIN topics t ON t.id=q.topic_id
        WHERE q.subject_id=%s AND t.name=%s
        GROUP BY t.name, q.batch ORDER BY q.batch;
        """,
        (SUBJECT_ID, TOPIC_NAME),
    )
    rows = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) FROM questions WHERE subject_id=%s;", (SUBJECT_ID,))
    total = cursor.fetchone()[0]
    conn.close()
    print(f"Imported {added} new; skipped {skipped} dups. English total Q={total}")
    for r in rows:
        print(f"  {r[0]} | {r[1]}: {r[2]}")


if __name__ == "__main__":
    main()
