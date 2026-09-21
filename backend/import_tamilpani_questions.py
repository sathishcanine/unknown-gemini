#!/usr/bin/env python3
"""Import Tamilpani practice + PYQ questions into Postgres."""

import json, os, re, psycopg2

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BACKEND_DIR)
SUBJECT_ID = "Tamil"
TOPIC_NAME = "தமிழ்ப்பணி தொடர்பான செய்திகள்"

def main():
    db_url = os.getenv("DATABASE_URL", "dbname=tnpsc_prep user=sathishkumar host=localhost port=5432")
    print(f"Connecting: {db_url}")
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM subjects WHERE id = %s;", (SUBJECT_ID,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO subjects (id, name, name_ta, icon) VALUES (%s, %s, %s, %s);",
            (SUBJECT_ID, "Tamil", "தமிழ்", "த"))

    cursor.execute("SELECT id FROM topics WHERE subject_id = %s AND name = %s;", (SUBJECT_ID, TOPIC_NAME))
    row = cursor.fetchone()
    if row:
        topic_id = row[0]
    else:
        cursor.execute("INSERT INTO topics (subject_id, name) VALUES (%s, %s) RETURNING id;", (SUBJECT_ID, TOPIC_NAME))
        topic_id = cursor.fetchone()[0]
        print(f"  Created topic: '{TOPIC_NAME}'")

    files = [
        (os.path.join(ROOT_DIR, "Tamil", "tamilpani_questions_db.json"), "practice"),
        (os.path.join(ROOT_DIR, "Tamil", "unit7_tamilpani_pyq.json"), "pyq"),
    ]

    total_added = total_skipped = 0
    for fpath, default_type in files:
        if not os.path.exists(fpath):
            print(f"Skip: {fpath} not found"); continue
        questions = json.load(open(fpath, encoding="utf-8"))
        print(f"Processing {os.path.basename(fpath)}: {len(questions)} Q")

        for q in questions:
            q_en = (q.get("question_en") or q.get("question_ta") or "").strip()
            q_ta = (q.get("question_ta") or q_en).strip()
            if not q_en: q_en = q_ta

            cursor.execute(
                "SELECT id FROM questions WHERE subject_id=%s AND topic_id=%s AND (LOWER(TRIM(question_ta))=LOWER(%s) OR LOWER(TRIM(question_en))=LOWER(%s));",
                (SUBJECT_ID, topic_id, q_ta, q_en))
            if cursor.fetchone():
                total_skipped += 1; continue

            q_type = q.get("type") or default_type
            correct = q.get("correct_option") or q.get("correct_option_letter") or ""
            exp = q.get("explanation") or q.get("explanation_ta") or ""
            exp_ta = q.get("explanation_ta") or exp

            cursor.execute(
                """INSERT INTO questions (subject_id, topic_id, question_en, question_ta, correct_option,
                   explanation, explanation_ta, difficulty, type, batch, source_exam, source_fact)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id;""",
                (SUBJECT_ID, topic_id, q_en, q_ta, correct, exp, exp_ta,
                 q.get("difficulty") or "Medium", q_type, q.get("batch") or "",
                 q.get("source_exam") or "", q.get("source_fact") or ""))
            qid = cursor.fetchone()[0]
            total_added += 1

            raw_opts = q.get("options") or q.get("options_ta") or []
            letters = ["A","B","C","D","E"]
            for idx, opt in enumerate(raw_opts):
                if isinstance(opt, dict):
                    ok = (opt.get("key") or letters[idx]).strip()
                    tt = re.sub(r"^[A-D]\)\s*", "", opt.get("text_ta") or opt.get("text_en") or "")
                else:
                    ok = letters[idx]
                    tt = re.sub(r"^[A-D]\)\s*", "", str(opt or "").strip())
                cursor.execute("INSERT INTO options (question_id, key, text_en, text_ta) VALUES (%s,%s,%s,%s);",
                    (qid, ok, tt, tt))

    conn.commit()
    print(f"\nAdded: {total_added}, skipped: {total_skipped}")
    cursor.execute("SELECT q.type, q.batch, COUNT(*) FROM questions q WHERE q.subject_id=%s AND q.topic_id=%s GROUP BY 1,2 ORDER BY 1,2;",
        (SUBJECT_ID, topic_id))
    for t, b, c in cursor.fetchall():
        print(f"  {t} | {b}: {c}")
    cursor.close(); conn.close()

if __name__ == "__main__":
    main()
