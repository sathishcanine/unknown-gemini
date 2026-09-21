#!/usr/bin/env python3
"""Import தமிழ்த் தொண்டு practice + PYQ questions into Postgres."""
import json, os, psycopg2

DB = os.environ.get("DATABASE_URL", "postgresql://sathishkumar@localhost:5432/tnpsc_prep")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRACTICE = os.path.join(BASE, "Tamil", "tamilthondu_questions_db.json")
PYQ = os.path.join(BASE, "Tamil", "unit7_tamilthondu_pyq.json")
SUBJECT_ID = "Tamil"
TOPIC = "தமிழ்த் தொண்டு தொடர்பான செய்திகள்"

def run():
    conn = psycopg2.connect(DB); cur = conn.cursor()
    cur.execute("SELECT id FROM topics WHERE subject_id=%s AND name=%s", (SUBJECT_ID, TOPIC))
    row = cur.fetchone()
    if not row:
        cur.execute("INSERT INTO topics(subject_id, name) VALUES(%s,%s) RETURNING id", (SUBJECT_ID, TOPIC))
        row = cur.fetchone()
    tid = row[0]
    cur.execute("DELETE FROM options WHERE question_id IN (SELECT id FROM questions WHERE topic_id=%s)", (tid,))
    cur.execute("DELETE FROM questions WHERE topic_id=%s", (tid,))
    print(f"Topic id={tid}")

    total = 0
    keys = ["A", "B", "C", "D"]
    for path, qtype in ((PRACTICE, "practice"), (PYQ, "pyq")):
        if not os.path.exists(path): continue
        qs = json.load(open(path, encoding="utf-8"))
        for q in qs:
            opts = q.get("options_ta", [])
            cur.execute("""INSERT INTO questions(subject_id, topic_id, question_en, question_ta, correct_option, difficulty, type, batch)
                           VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                        (SUBJECT_ID, tid, q["question_ta"], q["question_ta"], q.get("correct_option_letter","A"),
                         "medium", qtype, q.get("batch","")))
            qid = cur.fetchone()[0]
            for i, opt in enumerate(opts[:4]):
                cur.execute("INSERT INTO options(question_id, key, text_ta, text_en) VALUES(%s,%s,%s,%s)",
                            (qid, keys[i], opt, opt))
            total += 1
    conn.commit(); cur.close(); conn.close()
    print(f"Imported {total} questions for {TOPIC}")

if __name__ == "__main__": run()
