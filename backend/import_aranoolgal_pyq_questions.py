#!/usr/bin/env python3
"""Import Tamil Unit 7 Aranoolgal PYQs into Postgres (type=pyq)."""

import json
import os

import psycopg2

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BACKEND_DIR)
DB_PATH = os.getenv(
    "INPUT_DB_PATH",
    os.path.join(ROOT_DIR, "Tamil", "aranoolgal_pyq_questions_db.json"),
)

SUBJECT_ID = "Tamil"
SUBJECT_NAME = "Tamil"
SUBJECT_NAME_TA = "தமிழ்"
SUBJECT_ICON = "த"
TOPIC_NAME = "அறநூல்கள் தொடர்பான செய்திகள்"


def main():
    db_url = os.getenv(
        "DATABASE_URL", "dbname=tnpsc_prep user=sathishkumar host=localhost port=5432"
    )
    print(f"Connecting to PostgreSQL database: {db_url}")

    if not os.path.exists(DB_PATH):
        print(f"Error: Aranoolgal PYQ database not found at {DB_PATH}")
        return

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM subjects WHERE id = %s;", (SUBJECT_ID,))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO subjects (id, name, name_ta, icon) VALUES (%s, %s, %s, %s);",
            (SUBJECT_ID, SUBJECT_NAME, SUBJECT_NAME_TA, SUBJECT_ICON),
        )
        print(f"Created {SUBJECT_ID} subject metadata.")
    else:
        cursor.execute(
            "UPDATE subjects SET name = %s, name_ta = %s, icon = %s WHERE id = %s;",
            (SUBJECT_NAME, SUBJECT_NAME_TA, SUBJECT_ICON, SUBJECT_ID),
        )

    cursor.execute(
        "SELECT id FROM topics WHERE subject_id = %s AND name = %s;",
        (SUBJECT_ID, TOPIC_NAME),
    )
    row = cursor.fetchone()
    if row:
        topic_id = row[0]
    else:
        cursor.execute(
            "INSERT INTO topics (subject_id, name) VALUES (%s, %s) RETURNING id;",
            (SUBJECT_ID, TOPIC_NAME),
        )
        topic_id = cursor.fetchone()[0]
        print(f"Created topic: '{TOPIC_NAME}'")

    with open(DB_PATH, "r", encoding="utf-8") as f:
        questions = json.load(f)

    print(f"Loaded {len(questions)} Aranoolgal PYQs. Importing...")

    added = 0
    skipped = 0

    for q in questions:
        q_en = (q.get("question_en") or "").strip()
        q_ta = (q.get("question_ta") or q_en).strip()
        if not q_en and q_ta:
            q_en = q_ta

        cursor.execute(
            """
            SELECT id FROM questions
            WHERE subject_id = %s AND topic_id = %s
              AND LOWER(COALESCE(type,'')) = 'pyq'
              AND (
                LOWER(TRIM(question_ta)) = LOWER(%s)
                OR LOWER(TRIM(question_en)) = LOWER(%s)
              );
            """,
            (SUBJECT_ID, topic_id, q_ta, q_en),
        )
        if cursor.fetchone():
            skipped += 1
            continue

        cursor.execute(
            """
            INSERT INTO questions (
                subject_id, topic_id, question_en, question_ta, correct_option,
                explanation, explanation_ta, difficulty, type, batch, source_exam, source_fact
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
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
                q.get("type") or "pyq",
                q.get("batch") or "",
                q.get("source_exam") or "",
                q.get("source_fact") or "",
            ),
        )
        question_id = cursor.fetchone()[0]
        added += 1

        raw_options = q.get("options") or []
        letters = ["A", "B", "C", "D", "E"]
        for idx, opt in enumerate(raw_options):
            if isinstance(opt, dict):
                opt_key = (opt.get("key") or letters[idx]).strip()
                text_en = opt.get("text_en") or opt.get("text_ta") or ""
                text_ta = opt.get("text_ta") or text_en or ""
            else:
                opt_key = letters[idx]
                text_en = str(opt or "").strip()
                text_ta = text_en
            cursor.execute(
                """
                INSERT INTO options (question_id, key, text_en, text_ta)
                VALUES (%s, %s, %s, %s);
                """,
                (question_id, opt_key, text_en, text_ta),
            )

    conn.commit()

    cursor.execute(
        """
        SELECT COUNT(*) FROM questions
        WHERE subject_id = %s AND topic_id = %s AND LOWER(COALESCE(type,'')) = 'pyq';
        """,
        (SUBJECT_ID, topic_id),
    )
    total_pyq = cursor.fetchone()[0]
    print(f"Added: {added}, duplicates skipped: {skipped}, topic PYQ total: {total_pyq}")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
