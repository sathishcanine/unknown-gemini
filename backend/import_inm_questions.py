import os
import json
import psycopg2

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BACKEND_DIR)
DB_PATH = os.path.join(ROOT_DIR, "INM", "inm_questions_db.json")

SUBJECT_ID = "INM"
SUBJECT_NAME = "Indian National Movement"
SUBJECT_ICON = "🇮🇳"


def main():
    db_url = os.getenv("DATABASE_URL", "dbname=tnpsc_prep user=sathishkumar host=localhost port=5432")
    print(f"Connecting to PostgreSQL database: {db_url}")

    if not os.path.exists(DB_PATH):
        print(f"Error: INM question database not found at {DB_PATH}")
        return

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM subjects WHERE id = %s;", (SUBJECT_ID,))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO subjects (id, name, icon) VALUES (%s, %s, %s);",
            (SUBJECT_ID, SUBJECT_NAME, SUBJECT_ICON),
        )
        print(f"Created {SUBJECT_ID} subject metadata.")

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

    print(f"Loaded {len(questions)} INM questions from JSON. Importing to DB...")

    added_questions = 0
    duplicate_questions = 0

    for q in questions:
        topic_name = q.get("topic") or "General"
        topic_id = get_or_create_topic(topic_name)

        q_en = (q.get("question_en") or "").strip()
        q_ta = (q.get("question_ta") or q_en).strip()

        cursor.execute(
            "SELECT id FROM questions WHERE subject_id = %s AND topic_id = %s AND LOWER(TRIM(question_en)) = LOWER(%s);",
            (SUBJECT_ID, topic_id, q_en),
        )
        if cursor.fetchone():
            duplicate_questions += 1
            continue

        correct_opt = q.get("correct_option") or ""
        exp = q.get("explanation") or ""
        exp_ta = q.get("explanation_ta") or ""
        diff = q.get("difficulty") or "Medium"
        q_type = q.get("type") or "pyq"
        batch = q.get("batch") or ""
        exam = q.get("source_exam") or ""
        fact = q.get("source_fact") or ""

        cursor.execute(
            """
            INSERT INTO questions (
                subject_id, topic_id, question_en, question_ta, correct_option,
                explanation, explanation_ta, difficulty, type, batch, source_exam, source_fact
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
            """,
            (SUBJECT_ID, topic_id, q_en, q_ta, correct_opt, exp, exp_ta, diff, q_type, batch, exam, fact),
        )

        question_id = cursor.fetchone()[0]
        added_questions += 1

        options = q.get("options") or []
        for opt in options:
            opt_key = opt.get("key", "")
            text_en = opt.get("text_en") or opt.get("text_ta") or ""
            text_ta = opt.get("text_ta") or text_en or ""

            cursor.execute(
                """
                INSERT INTO options (question_id, key, text_en, text_ta)
                VALUES (%s, %s, %s, %s);
                """,
                (question_id, opt_key, text_en, text_ta),
            )

    conn.commit()
    conn.close()

    print(f"\nSUCCESS: Imported {added_questions} new questions. Skipped {duplicate_questions} duplicates.")


if __name__ == "__main__":
    main()
