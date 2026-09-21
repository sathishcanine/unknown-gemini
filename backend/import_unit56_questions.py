#!/usr/bin/env python3
"""Import Unit V Reading Comprehension + Unit VI Translation question DBs into English."""

import json
import os
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parents[1]
SUBJECT_ID = "English"
SUBJECT_NAME = "General English"
SUBJECT_NAME_TA = "பொது ஆங்கிலம்"
SUBJECT_ICON = "EN"

DBS = [
    ROOT / "English" / "ReadingComprehension" / "unseen_passages_questions_db.json",
    ROOT / "English" / "ReadingComprehension" / "strong_weak_questions_questions_db.json",
    ROOT / "English" / "ReadingComprehension" / "match_the_following_questions_db.json",
    ROOT / "English" / "ReadingComprehension" / "sentence_completion_questions_db.json",
    ROOT / "English" / "ReadingComprehension" / "ascertainment_of_facts_questions_db.json",
    ROOT / "English" / "Translation" / "word_translation_questions_db.json",
    ROOT / "English" / "Translation" / "sentence_translation_questions_db.json",
    ROOT / "English" / "Translation" / "tense_related_translation_questions_db.json",
    ROOT / "English" / "Translation" / "tense_voice_related_questions_db.json",
]


def main():
    db_url = os.getenv(
        "DATABASE_URL",
        "dbname=tnpsc_prep user=sathishkumar password=JYxxR14!lY4@-k_3 host=localhost port=5432",
    )
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

    questions = []
    for path in DBS:
        if path.exists():
            questions.extend(json.loads(path.read_text(encoding="utf-8")))
        else:
            print(f"skip missing {path.name}")

    topics = sorted({(q.get("topic") or "").strip() for q in questions if q.get("topic")})
    if topics:
        cur.execute(
            """
            DELETE FROM options WHERE question_id IN (
              SELECT q.id FROM questions q JOIN topics t ON t.id=q.topic_id
              WHERE q.subject_id=%s AND t.name = ANY(%s));
            """,
            (SUBJECT_ID, topics),
        )
        cur.execute(
            """
            DELETE FROM questions WHERE id IN (
              SELECT q.id FROM questions q JOIN topics t ON t.id=q.topic_id
              WHERE q.subject_id=%s AND t.name = ANY(%s));
            """,
            (SUBJECT_ID, topics),
        )
        print(f"Cleared topics: {topics}")

    added = 0
    for q in questions:
        topic_name = (q.get("topic") or "").strip()
        if not topic_name:
            continue
        tid = get_or_create_topic(topic_name)
        q_en = (q.get("question_en") or "").strip()
        if not q_en:
            continue
        q_ta = (q.get("question_ta") or q_en).strip()
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
        SELECT t.name, COUNT(*) FROM questions q JOIN topics t ON t.id=q.topic_id
        WHERE q.subject_id=%s AND t.name = ANY(%s) GROUP BY t.name ORDER BY 1;
        """,
        (SUBJECT_ID, topics),
    )
    for name, n in cur.fetchall():
        print(f"  {name}: {n}")
    cur.execute("SELECT COUNT(*) FROM questions WHERE subject_id=%s;", (SUBJECT_ID,))
    print(f"Imported {added}. English total={cur.fetchone()[0]}")
    conn.close()


if __name__ == "__main__":
    main()
