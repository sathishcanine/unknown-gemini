#!/usr/bin/env python3
"""Import Tamil Unit 4 Kalaichorkal / Technical Terms practice questions into Postgres."""

import json
import os

import psycopg2

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BACKEND_DIR)
DB_PATH = os.path.join(ROOT_DIR, "Tamil", "kalaichorkal_questions_db.json")

SUBJECT_ID = "Tamil"
SUBJECT_NAME = "Tamil"
SUBJECT_NAME_TA = "தமிழ்"
SUBJECT_ICON = "த"


def main():
    db_url = os.getenv(
        "DATABASE_URL", "dbname=tnpsc_prep user=sathishkumar host=localhost port=5432"
    )
    print(f"Connecting to PostgreSQL database: {db_url}")

    if not os.path.exists(DB_PATH):
        print(f"Error: Unit 4 question database not found at {DB_PATH}")
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
        print(f"Updated {SUBJECT_ID} subject metadata.")

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
        print(f"Created topic: '{key}'")
        return topic_id

    with open(DB_PATH, "r", encoding="utf-8") as f:
        questions = json.load(f)

    print(f"Loaded {len(questions)} Unit 4 questions from JSON. Importing to DB...")

    added_questions = 0
    duplicate_questions = 0

    for q in questions:
        topic_name = q.get("topic") or "General"
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
            duplicate_questions += 1
            continue

        correct_opt = q.get("correct_option") or ""
        exp = q.get("explanation") or ""
        exp_ta = q.get("explanation_ta") or ""
        diff = q.get("difficulty") or "Medium"
        q_type = q.get("type") or "practice"
        batch = q.get("batch") or ""
        exam = q.get("source_exam") or ""
        fact = q.get("source_fact") or q.get("source_note") or ""

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
                correct_opt,
                exp,
                exp_ta,
                diff,
                q_type,
                batch,
                exam,
                fact,
            ),
        )

        question_id = cursor.fetchone()[0]
        added_questions += 1

        normalized = []
        raw_options = q.get("options")
        if isinstance(raw_options, dict):
            for key, text in raw_options.items():
                text_en = (text or "").strip() if isinstance(text, str) else str(text or "")
                normalized.append((str(key).strip().upper()[:1] or "A", text_en, text_en))
        elif isinstance(raw_options, list):
            letters = ["A", "B", "C", "D", "E"]
            for idx, opt in enumerate(raw_options):
                if isinstance(opt, dict):
                    opt_key = (
                        opt.get("key") or letters[idx] if idx < len(letters) else chr(65 + idx)
                    ).strip()
                    text_en = opt.get("text_en") or opt.get("text_ta") or ""
                    text_ta = opt.get("text_ta") or text_en or ""
                    normalized.append((opt_key, text_en, text_ta))
                else:
                    text_en = str(opt or "").strip()
                    key = letters[idx] if idx < len(letters) else chr(65 + idx)
                    normalized.append((key, text_en, text_en))

        for opt_key, text_en, text_ta in normalized:
            cursor.execute(
                """
                INSERT INTO options (question_id, key, text_en, text_ta)
                VALUES (%s, %s, %s, %s);
                """,
                (question_id, opt_key, text_en, text_ta),
            )

    conn.commit()

    topic_ta = "சொற்களை ஒழுங்குபடுத்திச் சொற்றொடர் அமைத்தல்"
    cursor.execute(
        """
        SELECT q.batch, COUNT(*) FROM questions q
        JOIN topics t ON t.id = q.topic_id
        WHERE t.subject_id = %s AND t.name = %s
        GROUP BY 1 ORDER BY 1;
        """,
        (SUBJECT_ID, topic_ta),
    )
    topic_batches = cursor.fetchall()
    cursor.execute(
        "SELECT COUNT(*), COUNT(DISTINCT topic_id) FROM questions WHERE subject_id = %s;",
        (SUBJECT_ID,),
    )
    total_q, total_topics = cursor.fetchone()
    conn.close()

    print(
        f"\nSUCCESS: Imported {added_questions} new questions. "
        f"Skipped {duplicate_questions} duplicates."
    )
    print(f"Tamil totals: {total_q} questions across {total_topics} topics")
    print(f"Topic '{topic_ta}' batches: {topic_batches}")


if __name__ == "__main__":
    main()
