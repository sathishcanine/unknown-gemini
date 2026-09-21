#!/usr/bin/env python3
"""Import Aranoolgal practice questions (462 verified) into Postgres."""

import json
import os

import psycopg2

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BACKEND_DIR)
DB_PATH = os.getenv(
    "INPUT_DB_PATH",
    os.path.join(ROOT_DIR, "Tamil", "aranoolgal_questions_db.json"),
)

SUBJECT_ID = "Tamil"
SUBJECT_NAME = "Tamil"
SUBJECT_NAME_TA = "தமிழ்"
SUBJECT_ICON = "த"


def main():
    db_url = os.getenv(
        "DATABASE_URL", "dbname=tnpsc_prep user=sathishkumar host=localhost port=5432"
    )
    print(f"Connecting: {db_url}")

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM subjects WHERE id = %s;", (SUBJECT_ID,))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO subjects (id, name, name_ta, icon) VALUES (%s, %s, %s, %s);",
            (SUBJECT_ID, SUBJECT_NAME, SUBJECT_NAME_TA, SUBJECT_ICON),
        )

    topic_cache = {}

    def get_or_create_topic(topic_name):
        key = topic_name.strip()
        if key in topic_cache:
            return topic_cache[key]
        cursor.execute(
            "SELECT id FROM topics WHERE subject_id = %s AND name = %s;",
            (SUBJECT_ID, key),
        )
        row = cursor.fetchone()
        if row:
            topic_cache[key] = row[0]
            return row[0]
        cursor.execute(
            "INSERT INTO topics (subject_id, name) VALUES (%s, %s) RETURNING id;",
            (SUBJECT_ID, key),
        )
        topic_id = cursor.fetchone()[0]
        topic_cache[key] = topic_id
        print(f"  Created topic: '{key}'")
        return topic_id

    with open(DB_PATH, "r", encoding="utf-8") as f:
        questions = json.load(f)

    print(f"Loaded {len(questions)} Aranoolgal practice questions. Importing...")

    added = 0
    skipped = 0

    for q in questions:
        topic_name = q.get("topic") or "அறநூல்கள் தொடர்பான செய்திகள்"
        topic_id = get_or_create_topic(topic_name)

        q_en = (q.get("question_en") or "").strip()
        q_ta = (q.get("question_ta") or q_en).strip()
        if not q_en and q_ta:
            q_en = q_ta

        cursor.execute(
            """
            SELECT id FROM questions
            WHERE subject_id = %s AND topic_id = %s
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
                q.get("type") or "practice",
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
                "INSERT INTO options (question_id, key, text_en, text_ta) VALUES (%s, %s, %s, %s);",
                (question_id, opt_key, text_en, text_ta),
            )

    conn.commit()

    cursor.execute(
        """
        SELECT t.name, q.batch, COUNT(*)
        FROM topics t
        JOIN questions q ON q.topic_id = t.id
        WHERE t.subject_id = %s AND q.type = 'practice'
          AND t.name IN (
            'நாலடியார் — நான்மணிக்கடிகை',
            'பழமொழி நானூறு — இன்னா நாற்பது',
            'திரிகடுகம் — ஏலாதி',
            'சிறுபஞ்சமூலம் — முதுமொழிக் காஞ்சி',
            'ஔவையார்',
            'ஆசாரக்கோவை — அறநெறிச்சாரம் — நீதிநெறி விளக்கம்'
          )
        GROUP BY 1, 2
        ORDER BY 1, 2;
        """,
        (SUBJECT_ID,),
    )
    rows = cursor.fetchall()
    print(f"\nAdded: {added}, skipped: {skipped}")
    print("Topic breakdown:")
    for name, batch, cnt in rows:
        print(f"  {name[:50]} | {batch}: {cnt}")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
