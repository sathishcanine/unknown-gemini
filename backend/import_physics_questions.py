#!/usr/bin/env python3
"""Synchronize the local Physics PYQ JSON bank to PostgreSQL."""

import json
import os
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "Physics" / "physics_questions_db.json"

SUBJECT_ID = "Physics"
SUBJECT_NAME = "Physics"
SUBJECT_NAME_TA = "இயற்பியல்"
SUBJECT_ICON = "⚛️"


def main():
    db_url = os.getenv(
        "DATABASE_URL",
        "dbname=tnpsc_prep user=sathishkumar host=localhost port=5432",
    )
    questions = json.loads(DB_PATH.read_text(encoding="utf-8"))

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM subjects WHERE id=%s;", (SUBJECT_ID,))
        if cur.fetchone():
            cur.execute(
                "UPDATE subjects SET name=%s, name_ta=%s, icon=%s WHERE id=%s;",
                (SUBJECT_NAME, SUBJECT_NAME_TA, SUBJECT_ICON, SUBJECT_ID),
            )
        else:
            cur.execute(
                "INSERT INTO subjects (id, name, name_ta, icon) VALUES (%s,%s,%s,%s);",
                (SUBJECT_ID, SUBJECT_NAME, SUBJECT_NAME_TA, SUBJECT_ICON),
            )

        # Exact synchronization: keep server Physics equal to the validated local bank.
        cur.execute(
            "DELETE FROM options WHERE question_id IN "
            "(SELECT id FROM questions WHERE subject_id=%s);",
            (SUBJECT_ID,),
        )
        cur.execute("DELETE FROM questions WHERE subject_id=%s;", (SUBJECT_ID,))

        topic_ids = {}

        def topic_id(name):
            if name in topic_ids:
                return topic_ids[name]
            cur.execute(
                "SELECT id FROM topics WHERE subject_id=%s AND name=%s;",
                (SUBJECT_ID, name),
            )
            row = cur.fetchone()
            if row:
                topic_ids[name] = row[0]
            else:
                cur.execute(
                    "INSERT INTO topics (subject_id, name) VALUES (%s,%s) RETURNING id;",
                    (SUBJECT_ID, name),
                )
                topic_ids[name] = cur.fetchone()[0]
            return topic_ids[name]

        added = 0
        for q in questions:
            q_en = (q.get("question_en") or "").strip()
            if not q_en:
                continue
            tid = topic_id((q.get("topic") or "General Physics").strip())
            cur.execute(
                """
                INSERT INTO questions (
                    subject_id, topic_id, question_en, question_ta, correct_option,
                    explanation, explanation_ta, difficulty, type, batch,
                    source_exam, source_fact
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id;
                """,
                (
                    SUBJECT_ID,
                    tid,
                    q_en,
                    (q.get("question_ta") or q_en).strip(),
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
            qid = cur.fetchone()[0]
            for index, option in enumerate(q.get("options") or []):
                key = str(option.get("key") or "ABCDE"[index]).strip().upper()[:1]
                text_en = option.get("text_en") or option.get("text_ta") or ""
                text_ta = option.get("text_ta") or text_en
                cur.execute(
                    "INSERT INTO options (question_id, key, text_en, text_ta) "
                    "VALUES (%s,%s,%s,%s);",
                    (qid, key, text_en, text_ta),
                )
            added += 1

        conn.commit()

        cur.execute(
            """
            SELECT t.name, COUNT(*)
            FROM questions q JOIN topics t ON t.id=q.topic_id
            WHERE q.subject_id=%s
            GROUP BY t.name ORDER BY t.name;
            """,
            (SUBJECT_ID,),
        )
        counts = cur.fetchall()
        server_total = sum(count for _, count in counts)
        print(f"Local Physics JSON: {len(questions)}")
        print(f"Server Physics questions: {server_total}")
        for name, count in counts:
            print(f"  {name}: {count}")
        print(f"Imported: {added}")
        if server_total != len(questions):
            raise RuntimeError(
                f"Server verification failed: expected {len(questions)}, got {server_total}"
            )
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
