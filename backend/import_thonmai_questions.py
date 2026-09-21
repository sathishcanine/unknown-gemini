#!/usr/bin/env python3
"""Import Thonmai/Sirappu/Dravidian practice + PYQ questions into Postgres."""

import json
import os
import re

import psycopg2

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BACKEND_DIR)

SUBJECT_ID = "Tamil"
SUBJECT_NAME = "Tamil"
SUBJECT_NAME_TA = "தமிழ்"
SUBJECT_ICON = "த"


def main():
    db_url = os.getenv(
        "DATABASE_URL", "dbname=tnpsc_prep user=sathishkumar host=localhost port=5432"
    )
    print(f"Connecting: {db_url}")

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
        cursor.execute("SELECT id FROM topics WHERE subject_id = %s AND name = %s;", (SUBJECT_ID, key))
        row = cursor.fetchone()
        if row:
            topic_cache[key] = row[0]
            return row[0]
        cursor.execute("INSERT INTO topics (subject_id, name) VALUES (%s, %s) RETURNING id;", (SUBJECT_ID, key))
        topic_id = cursor.fetchone()[0]
        topic_cache[key] = topic_id
        print(f"  Created topic: '{key}'")
        return topic_id

    files = [
        (os.path.join(ROOT_DIR, "Tamil", "thonmai_questions_db.json"), "practice"),
        (os.path.join(ROOT_DIR, "Tamil", "unit7_tamilin_thonmai_pyq.json"), "pyq"),
    ]

    total_added = 0
    total_skipped = 0

    for fpath, default_type in files:
        if not os.path.exists(fpath):
            print(f"Skip: {fpath} not found")
            continue

        questions = json.load(open(fpath, encoding="utf-8"))
        print(f"Processing {os.path.basename(fpath)}: {len(questions)} questions")

        for q in questions:
            topic_name = q.get("topic") or q.get("section_ta") or "தமிழின் தொன்மை"
            # PYQ doesn't have per-subtopic split, put under single topic
            if default_type == "pyq":
                topic_name = "தமிழின் தொன்மை"
            topic_id = get_or_create_topic(topic_name)

            q_en = (q.get("question_en") or q.get("question_ta") or "").strip()
            q_ta = (q.get("question_ta") or q_en).strip()
            if not q_en:
                q_en = q_ta

            cursor.execute(
                """SELECT id FROM questions WHERE subject_id = %s AND topic_id = %s
                   AND (LOWER(TRIM(question_ta)) = LOWER(%s) OR LOWER(TRIM(question_en)) = LOWER(%s));""",
                (SUBJECT_ID, topic_id, q_ta, q_en),
            )
            if cursor.fetchone():
                total_skipped += 1
                continue

            q_type = q.get("type") or default_type
            correct = q.get("correct_option") or q.get("correct_option_letter") or ""
            explanation = q.get("explanation") or q.get("explanation_ta") or ""
            exp_ta = q.get("explanation_ta") or explanation

            cursor.execute(
                """INSERT INTO questions (subject_id, topic_id, question_en, question_ta, correct_option,
                   explanation, explanation_ta, difficulty, type, batch, source_exam, source_fact)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id;""",
                (SUBJECT_ID, topic_id, q_en, q_ta, correct, explanation, exp_ta,
                 q.get("difficulty") or "Medium", q_type,
                 q.get("batch") or "", q.get("source_exam") or "", q.get("source_fact") or ""),
            )
            question_id = cursor.fetchone()[0]
            total_added += 1

            raw_options = q.get("options") or q.get("options_ta") or []
            letters = ["A", "B", "C", "D", "E"]
            for idx, opt in enumerate(raw_options):
                if isinstance(opt, dict):
                    opt_key = (opt.get("key") or letters[idx]).strip()
                    text_ta = re.sub(r"^[A-D]\)\s*", "", opt.get("text_ta") or opt.get("text_en") or "")
                    text_en = text_ta
                else:
                    opt_key = letters[idx]
                    text_ta = re.sub(r"^[A-D]\)\s*", "", str(opt or "").strip())
                    text_en = text_ta
                cursor.execute(
                    "INSERT INTO options (question_id, key, text_en, text_ta) VALUES (%s,%s,%s,%s);",
                    (question_id, opt_key, text_en, text_ta),
                )

    conn.commit()

    cursor.execute(
        """SELECT t.name, q.type, q.batch, COUNT(*)
           FROM topics t JOIN questions q ON q.topic_id = t.id
           WHERE t.subject_id = %s AND t.name IN ('தமிழின் தொன்மை','தமிழின் சிறப்பு','திராவிட மொழிகள்')
           GROUP BY 1,2,3 ORDER BY 1,2,3;""",
        (SUBJECT_ID,),
    )
    rows = cursor.fetchall()
    print(f"\nAdded: {total_added}, skipped: {total_skipped}")
    for name, qtype, batch, cnt in rows:
        print(f"  {name[:30]} | {qtype} | {batch}: {cnt}")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
