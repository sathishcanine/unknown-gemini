import os
import json
import datetime
from zoneinfo import ZoneInfo
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAPPING_PATH = os.path.join(ROOT_DIR, "backend", "textbook_mapping.json")
IST = ZoneInfo("Asia/Kolkata")


def to_ist_iso(dt):
    """Serialize a DB timestamp (stored as UTC, often naive) as an IST ISO string."""
    if dt is None:
        return None
    if isinstance(dt, datetime.datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone(IST).isoformat()
    return str(dt)


def ist_today_iso():
    return datetime.datetime.now(IST).date().isoformat()


class QuestionDatabase:
    def __init__(self):
        db_url = os.getenv("DATABASE_URL", "dbname=tnpsc_prep user=sathishkumar host=localhost port=5432")
        # Minimum 1 connection, maximum 10 connections in pool for multi-threading
        self.pool = ThreadedConnectionPool(1, 10, dsn=db_url)
        self.textbook_mappings = {}
        self.load_mappings()
        print("Database initialized: PostgreSQL connection pool active.")

    def load_mappings(self):
        if os.path.exists(MAPPING_PATH):
            try:
                with open(MAPPING_PATH, "r", encoding="utf-8") as f:
                    self.textbook_mappings = json.load(f)
            except Exception as e:
                print(f"Error loading textbook mapping: {e}")

    def get_conn(self):
        return self.pool.getconn()

    def release_conn(self, conn):
        self.pool.putconn(conn)

    def get_subjects(self, group_name="Group 1"):
        conn = self.get_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT s.id, s.name, s.name_ta, s.icon, COUNT(q.id) as questions_count
                    FROM subjects s
                    LEFT JOIN questions q ON s.id = q.subject_id
                    GROUP BY s.id, s.name, s.name_ta, s.icon;
                """)
                rows = cur.fetchall()
                # Return standard subjects metadata formatted correctly
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error in get_subjects: {e}")
            return []
        finally:
            self.release_conn(conn)

    def get_topics_for_subject(self, subject):
        conn = self.get_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Normalise input subject name matching DB ID
                sub_norm = subject
                if subject in ["Economy", "Economics"]:
                    sub_norm = "Economy"

                cur.execute("""
                    SELECT name, textbook_mapping
                    FROM topics
                    WHERE subject_id = %s
                    ORDER BY name;
                """, (sub_norm,))
                rows = cur.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error in get_topics_for_subject: {e}")
            return []
        finally:
            self.release_conn(conn)

    def get_tamil_topic_question_counts(self):
        """topic name → question count for subject Tamil."""
        conn = self.get_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT t.name, COUNT(q.id)::int AS questions_count
                    FROM topics t
                    LEFT JOIN questions q ON q.topic_id = t.id
                    WHERE t.subject_id = 'Tamil'
                    GROUP BY t.name;
                    """
                )
                return {row["name"]: int(row["questions_count"] or 0) for row in cur.fetchall()}
        except Exception as e:
            print(f"Error in get_tamil_topic_question_counts: {e}")
            return {}
        finally:
            self.release_conn(conn)

    def get_questions(self, subject, topic=None, batch=None):
        conn = self.get_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                sub_norm = subject
                if subject in ["Economy", "Economics"]:
                    sub_norm = "Economy"

                query = """
                    SELECT q.id, q.subject_id as subject, t.name as topic, q.question_en, q.question_ta, 
                           q.correct_option, q.explanation, q.explanation_ta, q.difficulty, q.type, 
                           q.batch, q.source_exam, q.source_fact
                    FROM questions q
                    JOIN topics t ON q.topic_id = t.id
                    WHERE q.subject_id = %s
                """
                params = [sub_norm]

                if topic:
                    query += " AND LOWER(t.name) = LOWER(%s)"
                    params.append(topic)

                if batch:
                    if batch.lower() in ["pyq", "pyqs"]:
                        query += " AND LOWER(q.type) = 'pyq'"
                    else:
                        query += " AND LOWER(q.type) != 'pyq' AND LOWER(q.batch) = LOWER(%s)"
                    params.append(batch)

                cur.execute(query, tuple(params))
                questions = [dict(row) for row in cur.fetchall()]

                # Optimized: Fetch all options for these question IDs in a single query
                if questions:
                    q_ids = [q["id"] for q in questions]
                    cur.execute("""
                        SELECT question_id, key, text_en, text_ta
                        FROM options
                        WHERE question_id = ANY(%s)
                        ORDER BY question_id, key;
                    """, (q_ids,))
                    
                    options_rows = cur.fetchall()
                    
                    # Group options by question_id
                    options_by_q = {}
                    for opt in options_rows:
                        q_id = opt["question_id"]
                        if q_id not in options_by_q:
                            options_by_q[q_id] = []
                        options_by_q[q_id].append({
                            "key": opt["key"],
                            "text_en": opt["text_en"],
                            "text_ta": opt["text_ta"]
                        })

                    # Assign options back to questions
                    for q in questions:
                        q["options"] = options_by_q.get(q["id"], [])
                        
                return questions
        except Exception as e:
            print(f"Error in get_questions: {e}")
            return []
        finally:
            self.release_conn(conn)

    def _resolve_user_uuid(self, cur, user_id):
        """Resolve or create a users.id for an email / uuid-like user_id."""
        user_uuid = None
        is_uuid = False
        try:
            import uuid
            uuid.UUID(str(user_id))
            is_uuid = True
        except ValueError:
            pass

        if is_uuid:
            try:
                cur.execute("SELECT id FROM users WHERE id = %s;", (user_id,))
                user_row = cur.fetchone()
                if user_row:
                    return user_row[0]
            except Exception:
                pass

        cur.execute("""
            INSERT INTO users (display_name, email)
            VALUES (%s, %s)
            ON CONFLICT (email) DO UPDATE SET display_name = EXCLUDED.display_name
            RETURNING id;
        """, ("Test User", f"user_{user_id}@example.com" if "@" not in str(user_id) else user_id))
        return cur.fetchone()[0]

    def save_test_session(self, user_id, topic_name, correct_count, total_count, time_taken, answers, batch=None):
        """
        Saves a user test session and individual question responses into the PostgreSQL database.
        """
        conn = self.get_conn()
        try:
            conn.autocommit = False
            with conn.cursor() as cur:
                # 1. Resolve topic_id (find or create)
                # Parse subject from topic_name prefix or fallback
                subject_id = "Economy"
                if "Polity" in topic_name:
                    subject_id = "Polity"
                elif "Policy" in topic_name:
                    subject_id = "Policy"
                elif "Current" in topic_name:
                    subject_id = "Current Affairs"
                elif "History" in topic_name:
                    subject_id = "History"
                elif "Chemistry" in topic_name:
                    subject_id = "Chemistry"
                elif "Movement" in topic_name or topic_name.startswith("INM"):
                    subject_id = "INM"
                elif "TVK" in topic_name or topic_name.startswith("TVK"):
                    subject_id = "TVK"
                elif "Ministry of" in topic_name or topic_name in (
                    "NITI Aayog",
                    "Culture & Communications",
                    "Civil Aviation & Heavy Industries",
                    "Chemicals, Fertilisers & Mines",
                    "Corporate Affairs & Electronics / IT",
                    "Home Affairs & North Eastern Region Development",
                    "Consumer Affairs & Environment",
                ):
                    subject_id = "CGS"
                elif (
                    "பிரித்து" in topic_name
                    or "சந்தி" in topic_name
                    or "இலக்கண" in topic_name
                    or topic_name.startswith("Tamil")
                ):
                    subject_id = "Tamil"

                cur.execute("SELECT id FROM topics WHERE name = %s;", (topic_name,))
                topic_row = cur.fetchone()
                if topic_row:
                    topic_id = topic_row[0]
                else:
                    cur.execute("INSERT INTO topics (subject_id, name) VALUES (%s, %s) RETURNING id;", 
                                (subject_id, topic_name))
                    topic_id = cur.fetchone()[0]

                # 2. Ensure user exists (auto-register/upsert user for testing/auth convenience)
                user_uuid = self._resolve_user_uuid(cur, user_id)

                # Infer batch from answers when client did not send one.
                session_batch = (batch or "").strip() or None
                if not session_batch and answers:
                    q_ids = [a.get("question_id") for a in answers if a.get("question_id")]
                    if q_ids:
                        cur.execute("""
                            SELECT q.batch
                            FROM questions q
                            WHERE q.id = ANY(%s)
                              AND LOWER(COALESCE(q.type, '')) <> 'pyq'
                              AND NULLIF(TRIM(q.batch), '') IS NOT NULL
                            GROUP BY q.batch
                            ORDER BY COUNT(*) DESC
                            LIMIT 1;
                        """, (q_ids,))
                        row = cur.fetchone()
                        if row and row[0]:
                            session_batch = row[0]

                # 3. Save Test Session
                cur.execute("""
                    INSERT INTO test_sessions (user_id, topic_id, correct_count, total_count, time_taken, batch)
                    VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;
                """, (user_uuid, topic_id, correct_count, total_count, time_taken, session_batch))
                session_id = cur.fetchone()[0]

                # 4. Save individual user responses
                for ans in answers:
                    q_id = ans.get("question_id")
                    selected = ans.get("selected_option", "")
                    is_correct = ans.get("is_correct", False)
                    response_time_ms = ans.get("response_time_ms")

                    cur.execute("""
                        INSERT INTO user_answers (session_id, question_id, selected_option, is_correct, response_time_ms)
                        VALUES (%s, %s, %s, %s, %s);
                    """, (session_id, q_id, selected, is_correct, response_time_ms))

                # 5. Log Activity
                cur.execute("""
                    INSERT INTO activity_logs (user_id, event_type, meta_data)
                    VALUES (%s, %s, %s);
                """, (user_uuid, "quiz_completed", json.dumps({
                    "session_id": session_id,
                    "topic": topic_name,
                    "batch": session_batch,
                    "accuracy": (correct_count / total_count * 100) if total_count > 0 else 0
                })))

                conn.commit()
                return session_id
        except Exception as e:
            conn.rollback()
            print(f"Error saving test session: {e}")
            raise e
        finally:
            conn.autocommit = True
            self.release_conn(conn)

    def get_completed_batches(self, user_id, topic_name):
        """
        Return practice batches the user has completed for a topic.
        Uses test_sessions.batch, with a fallback join through answered questions.
        """
        conn = self.get_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                email = f"user_{user_id}@example.com" if "@" not in str(user_id) else user_id
                is_uuid = False
                try:
                    import uuid
                    uuid.UUID(str(user_id))
                    is_uuid = True
                except ValueError:
                    pass

                if is_uuid:
                    cur.execute("SELECT id FROM users WHERE id = %s;", (user_id,))
                else:
                    cur.execute("SELECT id FROM users WHERE email = %s;", (email,))
                row = cur.fetchone()
                if not row:
                    return []
                user_uuid = row["id"]

                cur.execute("""
                    SELECT
                        ts.id,
                        ts.batch,
                        ts.correct_count,
                        ts.total_count,
                        ts.timestamp
                    FROM test_sessions ts
                    JOIN topics t ON t.id = ts.topic_id
                    WHERE ts.user_id = %s
                      AND t.name = %s
                    ORDER BY ts.timestamp DESC;
                """, (user_uuid, topic_name))
                sessions = cur.fetchall()

                completed = {}
                for s in sessions:
                    batch = (s.get("batch") or "").strip()
                    if not batch:
                        cur.execute("""
                            SELECT q.batch
                            FROM user_answers ua
                            JOIN questions q ON q.id = ua.question_id
                            WHERE ua.session_id = %s
                              AND LOWER(COALESCE(q.type, '')) <> 'pyq'
                              AND NULLIF(TRIM(q.batch), '') IS NOT NULL
                            GROUP BY q.batch
                            ORDER BY COUNT(*) DESC
                            LIMIT 1;
                        """, (s["id"],))
                        inferred = cur.fetchone()
                        batch = (inferred["batch"] if inferred else "") or ""
                    if not batch:
                        continue
                    # Keep latest session stats per batch key.
                    if batch not in completed:
                        completed[batch] = {
                            "batch": batch,
                            "correct_count": s["correct_count"],
                            "total_count": s["total_count"],
                            "timestamp": to_ist_iso(s["timestamp"]),
                        }
                return list(completed.values())
        except Exception as e:
            print(f"Error in get_completed_batches: {e}")
            return []
        finally:
            self.release_conn(conn)

    def get_user_history(self, user_id):
        conn = self.get_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                user_uuid = None
                is_uuid = False
                try:
                    import uuid
                    uuid.UUID(str(user_id))
                    is_uuid = True
                except ValueError:
                    pass

                if is_uuid:
                    cur.execute("SELECT id FROM users WHERE id = %s;", (user_id,))
                else:
                    cur.execute("SELECT id FROM users WHERE email = %s;", (f"user_{user_id}@example.com" if "@" not in user_id else user_id,))

                row = cur.fetchone()
                if row:
                    user_uuid = row["id"]
                else:
                    return []

                cur.execute("""
                    SELECT ts.id, t.name as topic_name, ts.correct_count, ts.total_count,
                           ts.time_taken, ts.timestamp, ts.batch
                    FROM test_sessions ts
                    JOIN topics t ON ts.topic_id = t.id
                    WHERE ts.user_id = %s
                    ORDER BY ts.timestamp DESC;
                """, (user_uuid,))

                rows = cur.fetchall()
                res = []
                for r in rows:
                    rd = dict(r)
                    rd["timestamp"] = to_ist_iso(rd["timestamp"])
                    res.append(rd)
                return res
        except Exception as e:
            print(f"Error in get_user_history: {e}")
            return []
        finally:
            self.release_conn(conn)

    def get_session_detail(self, user_id, session_id):
        """
        Full session payload for re-opening Test Results:
        questions (+ options) in answer order, selected answers, score, time.
        """
        conn = self.get_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                email = f"user_{user_id}@example.com" if "@" not in str(user_id) else user_id
                is_uuid = False
                try:
                    import uuid
                    uuid.UUID(str(user_id))
                    is_uuid = True
                except ValueError:
                    pass

                if is_uuid:
                    cur.execute("SELECT id FROM users WHERE id = %s;", (user_id,))
                else:
                    cur.execute("SELECT id FROM users WHERE email = %s;", (email,))
                user_row = cur.fetchone()
                if not user_row:
                    return None
                user_uuid = user_row["id"]

                cur.execute("""
                    SELECT ts.id, t.name AS topic_name, ts.correct_count, ts.total_count,
                           ts.time_taken, ts.timestamp, ts.batch, ts.user_id
                    FROM test_sessions ts
                    JOIN topics t ON t.id = ts.topic_id
                    WHERE ts.id = %s AND ts.user_id = %s;
                """, (session_id, user_uuid))
                session = cur.fetchone()
                if not session:
                    return None

                cur.execute("""
                    SELECT
                        ua.id AS answer_row_id,
                        ua.selected_option,
                        ua.is_correct,
                        q.id, q.subject_id AS subject, t.name AS topic,
                        q.question_en, q.question_ta, q.correct_option,
                        q.explanation, q.explanation_ta, q.difficulty, q.type,
                        q.batch, q.source_exam, q.source_fact
                    FROM user_answers ua
                    JOIN questions q ON q.id = ua.question_id
                    JOIN topics t ON t.id = q.topic_id
                    WHERE ua.session_id = %s
                    ORDER BY ua.id ASC;
                """, (session_id,))
                answer_rows = cur.fetchall()

                questions = []
                answers = {}
                q_ids = []
                for idx, row in enumerate(answer_rows):
                    q_ids.append(row["id"])
                    answers[str(idx)] = row["selected_option"] or "E"
                    questions.append({
                        "id": row["id"],
                        "subject": row["subject"],
                        "topic": row["topic"],
                        "question_en": row["question_en"],
                        "question_ta": row["question_ta"],
                        "correct_option": row["correct_option"],
                        "explanation": row["explanation"] or "",
                        "explanation_ta": row["explanation_ta"] or "",
                        "difficulty": row["difficulty"] or "Medium",
                        "type": row["type"] or "practice",
                        "batch": row["batch"] or "",
                        "source_exam": row["source_exam"] or "",
                        "source_fact": row["source_fact"] or "",
                        "group": "Practice",
                        "options": [],
                    })

                if q_ids:
                    cur.execute("""
                        SELECT question_id, key, text_en, text_ta
                        FROM options
                        WHERE question_id = ANY(%s)
                        ORDER BY question_id, key;
                    """, (q_ids,))
                    options_by_q = {}
                    for opt in cur.fetchall():
                        qid = opt["question_id"]
                        options_by_q.setdefault(qid, []).append({
                            "key": opt["key"],
                            "text_en": opt["text_en"],
                            "text_ta": opt["text_ta"],
                        })
                    for q in questions:
                        q["options"] = options_by_q.get(q["id"], [])

                ts = session["timestamp"]
                timestamp_ms = None
                if ts is not None:
                    try:
                        timestamp_ms = ts.timestamp() * 1000.0
                    except Exception:
                        timestamp_ms = None

                return {
                    "id": session["id"],
                    "topic_name": session["topic_name"],
                    "batch": session.get("batch") or "",
                    "correct_count": session["correct_count"],
                    "total_count": session["total_count"],
                    "time_taken": session["time_taken"],
                    "timestamp": to_ist_iso(session["timestamp"]),
                    "timestamp_ms": timestamp_ms,
                    "answers": answers,
                    "questions": questions,
                }
        except Exception as e:
            print(f"Error in get_session_detail: {e}")
            return None
        finally:
            self.release_conn(conn)

    def delete_user_account(self, user_id):
        conn = self.get_conn()
        try:
            with conn.cursor() as cur:
                user_uuid = None
                is_uuid = False
                try:
                    import uuid
                    uuid.UUID(str(user_id))
                    is_uuid = True
                except ValueError:
                    pass

                if is_uuid:
                    cur.execute("SELECT id FROM users WHERE id = %s;", (user_id,))
                else:
                    cur.execute("SELECT id FROM users WHERE email = %s;", (f"user_{user_id}@example.com" if "@" not in user_id else user_id,))

                row = cur.fetchone()
                if not row:
                    return False
                user_uuid = row[0]

                # 1. Delete user answers
                cur.execute("DELETE FROM user_answers WHERE session_id IN (SELECT id FROM test_sessions WHERE user_id = %s);", (user_uuid,))
                # 2. Delete test sessions
                cur.execute("DELETE FROM test_sessions WHERE user_id = %s;", (user_uuid,))
                # 3. Delete activity logs
                cur.execute("DELETE FROM activity_logs WHERE user_id = %s;", (user_uuid,))
                # 4. Delete user record
                cur.execute("DELETE FROM users WHERE id = %s;", (user_uuid,))

                conn.commit()
                return True
        except Exception as e:
            conn.rollback()
            print(f"Error deleting user account: {e}")
            raise e
        finally:
            self.release_conn(conn)

    # =====================================================================
    # ADMIN ANALYTICS
    # =====================================================================

    def get_admin_by_username(self, username):
        conn = self.get_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM admin_users WHERE username = %s;", (username,))
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            self.release_conn(conn)

    def create_admin_user(self, username, password_hash):
        conn = self.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO admin_users (username, password_hash) VALUES (%s, %s) "
                    "ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash;",
                    (username, password_hash),
                )
                conn.commit()
        finally:
            self.release_conn(conn)

    def touch_admin_login(self, username):
        conn = self.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE admin_users SET last_login_at = CURRENT_TIMESTAMP WHERE username = %s;", (username,))
                conn.commit()
        finally:
            self.release_conn(conn)

    @staticmethod
    def _period_bounds(start_date, end_date):
        """
        Convert inclusive YYYY-MM-DD calendar days in IST into UTC-naive
        timestamps, matching how CURRENT_TIMESTAMP is stored on this server (UTC).
        """
        start_ist = datetime.datetime.strptime(start_date, "%Y-%m-%d").replace(
            hour=0, minute=0, second=0, microsecond=0, tzinfo=IST
        )
        end_ist = datetime.datetime.strptime(end_date, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59, microsecond=999999, tzinfo=IST
        )
        start_utc = start_ist.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        end_utc = end_ist.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return start_utc, end_utc

    def _period_metrics(self, cur, start_date, end_date):
        start_dt, end_dt = self._period_bounds(start_date, end_date)

        cur.execute("SELECT COUNT(*) AS c FROM users WHERE created_at BETWEEN %s AND %s;", (start_dt, end_dt))
        new_users = cur.fetchone()["c"]

        cur.execute(
            "SELECT COUNT(DISTINCT user_id) AS c FROM activity_logs WHERE timestamp BETWEEN %s AND %s AND user_id IS NOT NULL;",
            (start_dt, end_dt),
        )
        active_users = cur.fetchone()["c"]

        cur.execute("SELECT COUNT(*) AS c FROM test_sessions WHERE timestamp BETWEEN %s AND %s;", (start_dt, end_dt))
        total_tests = cur.fetchone()["c"]

        cur.execute(
            """
            SELECT COUNT(ua.id) AS solved,
                   COALESCE(AVG(CASE WHEN ua.is_correct THEN 1.0 ELSE 0 END) * 100, 0) AS accuracy
            FROM user_answers ua
            JOIN test_sessions ts ON ua.session_id = ts.id
            WHERE ts.timestamp BETWEEN %s AND %s;
            """,
            (start_dt, end_dt),
        )
        row = cur.fetchone()
        questions_solved = row["solved"] or 0
        accuracy = round(float(row["accuracy"] or 0), 1)

        cur.execute(
            "SELECT COALESCE(AVG(time_taken), 0) AS avg_time FROM test_sessions WHERE timestamp BETWEEN %s AND %s;",
            (start_dt, end_dt),
        )
        avg_session_seconds = round(float(cur.fetchone()["avg_time"] or 0), 1)

        return {
            "new_users": new_users,
            "active_users": active_users,
            "total_tests": total_tests,
            "questions_solved": questions_solved,
            "accuracy": accuracy,
            "avg_session_seconds": avg_session_seconds,
        }

    def get_dashboard_summary(self, start_date, end_date, compare_start=None, compare_end=None):
        conn = self.get_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Real-time engagement gauges (independent of the selected period)
                cur.execute("SELECT COUNT(DISTINCT user_id) AS c FROM activity_logs WHERE timestamp >= NOW() - INTERVAL '1 day' AND user_id IS NOT NULL;")
                dau = cur.fetchone()["c"]
                cur.execute("SELECT COUNT(DISTINCT user_id) AS c FROM activity_logs WHERE timestamp >= NOW() - INTERVAL '7 days' AND user_id IS NOT NULL;")
                wau = cur.fetchone()["c"]
                cur.execute("SELECT COUNT(DISTINCT user_id) AS c FROM activity_logs WHERE timestamp >= NOW() - INTERVAL '30 days' AND user_id IS NOT NULL;")
                mau = cur.fetchone()["c"]
                cur.execute("SELECT COUNT(*) AS c FROM users;")
                total_users = cur.fetchone()["c"]

                # Retention cohorts (D1 / D7 / D30)
                retention = {}
                for label, days in (("d1", 1), ("d7", 7), ("d30", 30)):
                    cur.execute(
                        """
                        WITH cohort AS (
                            SELECT id, created_at::date AS signup_date
                            FROM users
                            WHERE created_at::date <= CURRENT_DATE - INTERVAL '%s day'
                        ),
                        activity AS (
                            SELECT DISTINCT user_id, timestamp::date AS activity_date FROM activity_logs
                        )
                        SELECT COUNT(DISTINCT c.id) AS cohort_size,
                               COUNT(DISTINCT a.user_id) AS retained
                        FROM cohort c
                        LEFT JOIN activity a ON a.user_id = c.id AND a.activity_date = c.signup_date + INTERVAL '%s day'
                        """ % (days, days)
                    )
                    r = cur.fetchone()
                    cohort_size = r["cohort_size"] or 0
                    retained = r["retained"] or 0
                    retention[label] = round((retained / cohort_size * 100), 1) if cohort_size > 0 else 0

                current = self._period_metrics(cur, start_date, end_date)

                comparison = None
                if compare_start and compare_end:
                    comparison = self._period_metrics(cur, compare_start, compare_end)

                return {
                    "engagement": {"dau": dau, "wau": wau, "mau": mau, "total_users": total_users},
                    "retention": retention,
                    "period": current,
                    "comparison": comparison,
                    "not_tracked": {
                        "ad_revenue": None,
                        "subscriptions": None,
                        "premium_users": None,
                        "crash_rate": None,
                    },
                }
        finally:
            self.release_conn(conn)

    def get_users_list(self, start_date, end_date, search=None, sort_by="last_active_at", page=1, page_size=20):
        conn = self.get_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                start_dt, end_dt = self._period_bounds(start_date, end_date)
                sort_columns = {
                    "last_active_at": "last_active_at DESC NULLS LAST",
                    "created_at": "created_at DESC",
                    "total_tests": "total_tests DESC",
                    "avg_accuracy": "avg_accuracy DESC",
                    "total_points": "u.total_points DESC",
                }
                order_clause = sort_columns.get(sort_by, sort_columns["last_active_at"])

                search_clause = ""
                params = [start_dt, end_dt]
                if search:
                    search_clause = "WHERE (u.email ILIKE %s OR u.display_name ILIKE %s)"
                    params += [f"%{search}%", f"%{search}%"]

                count_query = f"SELECT COUNT(*) AS c FROM users u {search_clause};"
                cur.execute(count_query, params[2:] if search else [])
                total = cur.fetchone()["c"]

                query = f"""
                    SELECT u.id, u.email, u.display_name, u.created_at, u.last_active_at,
                           u.platform, u.country, u.total_points,
                           COUNT(DISTINCT ts.id) FILTER (WHERE ts.timestamp BETWEEN %s AND %s) AS total_tests,
                           COALESCE(AVG(CASE WHEN ua.is_correct THEN 1.0 ELSE 0 END) * 100, 0) AS avg_accuracy
                    FROM users u
                    LEFT JOIN test_sessions ts ON ts.user_id = u.id
                    LEFT JOIN user_answers ua ON ua.session_id = ts.id
                    {search_clause}
                    GROUP BY u.id
                    ORDER BY {order_clause}
                    LIMIT %s OFFSET %s;
                """
                params.append(page_size)
                params.append((page - 1) * page_size)
                cur.execute(query, params)
                rows = [dict(r) for r in cur.fetchall()]
                for r in rows:
                    r["created_at"] = to_ist_iso(r["created_at"]) if r["created_at"] else None
                    r["last_active_at"] = to_ist_iso(r["last_active_at"]) if r["last_active_at"] else None
                    r["avg_accuracy"] = round(float(r["avg_accuracy"] or 0), 1)

                return {"users": rows, "total": total, "page": page, "page_size": page_size}
        finally:
            self.release_conn(conn)

    def get_user_detail(self, user_id):
        conn = self.get_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM users WHERE id = %s;", (user_id,))
                user = cur.fetchone()
                if not user:
                    return None
                user = dict(user)
                user["created_at"] = to_ist_iso(user["created_at"]) if user["created_at"] else None
                user["last_active_at"] = to_ist_iso(user["last_active_at"]) if user["last_active_at"] else None

                cur.execute(
                    """
                    SELECT COUNT(ua.id) AS attempted,
                           SUM(CASE WHEN ua.is_correct THEN 1 ELSE 0 END) AS correct,
                           SUM(CASE WHEN ua.selected_option = 'E' THEN 1 ELSE 0 END) AS skipped
                    FROM user_answers ua
                    JOIN test_sessions ts ON ua.session_id = ts.id
                    WHERE ts.user_id = %s;
                    """,
                    (user_id,),
                )
                stats_row = cur.fetchone()
                attempted = stats_row["attempted"] or 0
                correct = stats_row["correct"] or 0
                skipped = stats_row["skipped"] or 0
                wrong = attempted - correct - skipped
                accuracy = round((correct / attempted * 100), 1) if attempted > 0 else 0

                cur.execute(
                    "SELECT COALESCE(AVG(response_time_ms), 0) AS avg_ms FROM user_answers ua "
                    "JOIN test_sessions ts ON ua.session_id = ts.id WHERE ts.user_id = %s AND ua.response_time_ms IS NOT NULL;",
                    (user_id,),
                )
                avg_time_seconds = round(float(cur.fetchone()["avg_ms"] or 0) / 1000.0, 1)

                cur.execute(
                    "SELECT MAX(total_count) AS longest FROM test_sessions WHERE user_id = %s;",
                    (user_id,),
                )
                longest_session = cur.fetchone()["longest"] or 0

                # Favorite / weakest subject by attempts & accuracy
                cur.execute(
                    """
                    SELECT s.name AS subject_name,
                           COUNT(ua.id) AS attempts,
                           COALESCE(AVG(CASE WHEN ua.is_correct THEN 1.0 ELSE 0 END) * 100, 0) AS accuracy
                    FROM user_answers ua
                    JOIN test_sessions ts ON ua.session_id = ts.id
                    JOIN questions q ON ua.question_id = q.id
                    JOIN subjects s ON q.subject_id = s.id
                    WHERE ts.user_id = %s
                    GROUP BY s.name
                    ORDER BY attempts DESC;
                    """,
                    (user_id,),
                )
                subject_rows = [dict(r) for r in cur.fetchall()]
                favorite_subject = subject_rows[0]["subject_name"] if subject_rows else None
                weakest_subject = None
                if subject_rows:
                    eligible = [r for r in subject_rows if r["attempts"] >= 5] or subject_rows
                    weakest_subject = min(eligible, key=lambda r: r["accuracy"])["subject_name"]

                # Streak computation from distinct active days
                cur.execute(
                    "SELECT DISTINCT timestamp::date AS d FROM activity_logs WHERE user_id = %s ORDER BY d;",
                    (user_id,),
                )
                active_days = [r["d"] for r in cur.fetchall()]
                current_streak, highest_streak = self._compute_streaks(active_days)

                return {
                    "profile": user,
                    "stats": {
                        "attempted": attempted,
                        "correct": correct,
                        "wrong": wrong,
                        "skipped": skipped,
                        "accuracy": accuracy,
                        "avg_time_seconds": avg_time_seconds,
                        "longest_session": longest_session,
                        "current_streak": current_streak,
                        "highest_streak": highest_streak,
                        "favorite_subject": favorite_subject,
                        "weakest_subject": weakest_subject,
                    },
                }
        finally:
            self.release_conn(conn)

    @staticmethod
    def _compute_streaks(active_days):
        if not active_days:
            return 0, 0
        highest = 1
        run = 1
        for i in range(1, len(active_days)):
            if (active_days[i] - active_days[i - 1]).days == 1:
                run += 1
            else:
                run = 1
            highest = max(highest, run)

        today = datetime.datetime.now(IST).date()
        current = 0
        if active_days[-1] in (today, today - datetime.timedelta(days=1)):
            current = 1
            for i in range(len(active_days) - 1, 0, -1):
                if (active_days[i] - active_days[i - 1]).days == 1:
                    current += 1
                else:
                    break
        return current, highest

    def get_leaderboard(self, start_date, end_date, limit=20):
        """
        V1 leaderboard from existing data only:
        - most tests / questions / accuracy in the selected IST period
        - longest current + highest streak from activity_logs (all-time)
        """
        start_dt, end_dt = self._period_bounds(start_date, end_date)
        conn = self.get_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Period performance leaders
                cur.execute(
                    """
                    SELECT u.id, u.email, u.display_name,
                           COUNT(DISTINCT ts.id) AS total_tests,
                           COUNT(ua.id) AS questions_solved,
                           COALESCE(AVG(CASE WHEN ua.is_correct THEN 1.0 ELSE 0 END) * 100, 0) AS avg_accuracy
                    FROM users u
                    JOIN test_sessions ts ON ts.user_id = u.id
                        AND ts.timestamp BETWEEN %s AND %s
                    LEFT JOIN user_answers ua ON ua.session_id = ts.id
                    GROUP BY u.id
                    HAVING COUNT(DISTINCT ts.id) > 0
                    ORDER BY total_tests DESC, questions_solved DESC
                    LIMIT %s;
                    """,
                    (start_dt, end_dt, limit),
                )
                by_tests = [dict(r) for r in cur.fetchall()]

                cur.execute(
                    """
                    SELECT u.id, u.email, u.display_name,
                           COUNT(DISTINCT ts.id) AS total_tests,
                           COUNT(ua.id) AS questions_solved,
                           COALESCE(AVG(CASE WHEN ua.is_correct THEN 1.0 ELSE 0 END) * 100, 0) AS avg_accuracy
                    FROM users u
                    JOIN test_sessions ts ON ts.user_id = u.id
                        AND ts.timestamp BETWEEN %s AND %s
                    JOIN user_answers ua ON ua.session_id = ts.id
                    GROUP BY u.id
                    HAVING COUNT(ua.id) >= 5
                    ORDER BY avg_accuracy DESC, questions_solved DESC
                    LIMIT %s;
                    """,
                    (start_dt, end_dt, limit),
                )
                by_accuracy = [dict(r) for r in cur.fetchall()]

                cur.execute(
                    """
                    SELECT u.id, u.email, u.display_name,
                           COUNT(DISTINCT ts.id) AS total_tests,
                           COUNT(ua.id) AS questions_solved,
                           COALESCE(AVG(CASE WHEN ua.is_correct THEN 1.0 ELSE 0 END) * 100, 0) AS avg_accuracy
                    FROM users u
                    JOIN test_sessions ts ON ts.user_id = u.id
                        AND ts.timestamp BETWEEN %s AND %s
                    JOIN user_answers ua ON ua.session_id = ts.id
                    GROUP BY u.id
                    HAVING COUNT(ua.id) > 0
                    ORDER BY questions_solved DESC, avg_accuracy DESC
                    LIMIT %s;
                    """,
                    (start_dt, end_dt, limit),
                )
                by_questions = [dict(r) for r in cur.fetchall()]

                # Streaks (all-time activity days). Cap to users with any activity.
                cur.execute(
                    """
                    SELECT u.id, u.email, u.display_name,
                           array_agg(d.day ORDER BY d.day) AS active_days
                    FROM users u
                    JOIN (
                        SELECT DISTINCT user_id,
                               ((timestamp AT TIME ZONE 'UTC') AT TIME ZONE 'Asia/Kolkata')::date AS day
                        FROM activity_logs
                        WHERE user_id IS NOT NULL
                    ) d ON d.user_id = u.id
                    GROUP BY u.id, u.email, u.display_name;
                    """
                )
                streak_rows = []
                for row in cur.fetchall():
                    days = [d for d in (row["active_days"] or []) if d is not None]
                    current_streak, highest_streak = self._compute_streaks(days)
                    streak_rows.append({
                        "id": row["id"],
                        "email": row["email"],
                        "display_name": row["display_name"],
                        "current_streak": current_streak,
                        "highest_streak": highest_streak,
                        "active_days": len(days),
                    })

                by_current_streak = sorted(
                    streak_rows, key=lambda r: (r["current_streak"], r["highest_streak"], r["active_days"]), reverse=True
                )[:limit]
                by_highest_streak = sorted(
                    streak_rows, key=lambda r: (r["highest_streak"], r["current_streak"], r["active_days"]), reverse=True
                )[:limit]

                def _rank(rows, value_key, extras=None):
                    out = []
                    for i, r in enumerate(rows, start=1):
                        entry = {
                            "rank": i,
                            "id": str(r["id"]),
                            "email": r["email"],
                            "display_name": r.get("display_name") or "Student",
                            "value": r[value_key],
                        }
                        if extras:
                            for k in extras:
                                v = r.get(k)
                                if isinstance(v, float):
                                    v = round(v, 1)
                                entry[k] = v
                        if value_key == "avg_accuracy":
                            entry["value"] = round(float(entry["value"] or 0), 1)
                        out.append(entry)
                    return out

                return {
                    "period": {"start": start_date, "end": end_date},
                    "most_tests": _rank(by_tests, "total_tests", ["questions_solved", "avg_accuracy"]),
                    "highest_accuracy": _rank(by_accuracy, "avg_accuracy", ["questions_solved", "total_tests"]),
                    "most_questions": _rank(by_questions, "questions_solved", ["total_tests", "avg_accuracy"]),
                    "longest_current_streak": _rank(by_current_streak, "current_streak", ["highest_streak", "active_days"]),
                    "longest_highest_streak": _rank(by_highest_streak, "highest_streak", ["current_streak", "active_days"]),
                }
        finally:
            self.release_conn(conn)

    def get_user_timeline(self, user_id, page=1, page_size=30):
        conn = self.get_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT COUNT(*) AS c FROM activity_logs WHERE user_id = %s;", (user_id,))
                total = cur.fetchone()["c"]
                cur.execute(
                    """
                    SELECT event_type, meta_data, timestamp
                    FROM activity_logs
                    WHERE user_id = %s
                    ORDER BY timestamp DESC
                    LIMIT %s OFFSET %s;
                    """,
                    (user_id, page_size, (page - 1) * page_size),
                )
                rows = [dict(r) for r in cur.fetchall()]
                for r in rows:
                    r["timestamp"] = to_ist_iso(r["timestamp"])
                return {"events": rows, "total": total, "page": page, "page_size": page_size}
        finally:
            self.release_conn(conn)

    def get_topic_analytics(self, start_date, end_date):
        conn = self.get_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                start_dt, end_dt = self._period_bounds(start_date, end_date)
                cur.execute(
                    """
                    SELECT t.id, t.name, s.name AS subject_name,
                           COUNT(ua.id) AS attempts,
                           COALESCE(AVG(CASE WHEN ua.is_correct THEN 1.0 ELSE 0 END) * 100, 0) AS accuracy,
                           COALESCE(AVG(ua.response_time_ms) / 1000.0, NULL) AS avg_time_seconds,
                           MODE() WITHIN GROUP (ORDER BY q.difficulty) AS difficulty
                    FROM topics t
                    JOIN subjects s ON s.id = t.subject_id
                    LEFT JOIN questions q ON q.topic_id = t.id
                    LEFT JOIN user_answers ua ON ua.question_id = q.id
                    LEFT JOIN test_sessions ts ON ua.session_id = ts.id AND ts.timestamp BETWEEN %s AND %s
                    GROUP BY t.id, t.name, s.name
                    ORDER BY attempts DESC;
                    """,
                    (start_dt, end_dt),
                )
                topics = [dict(r) for r in cur.fetchall()]

                # Completion / drop rate from quiz_started vs quiz_completed activity events (topic in meta_data)
                cur.execute(
                    """
                    SELECT meta_data->>'topic' AS topic_name, event_type, COUNT(*) AS c
                    FROM activity_logs
                    WHERE event_type IN ('quiz_started', 'quiz_completed')
                      AND timestamp BETWEEN %s AND %s
                    GROUP BY meta_data->>'topic', event_type;
                    """,
                    (start_dt, end_dt),
                )
                funnel = {}
                for r in cur.fetchall():
                    funnel.setdefault(r["topic_name"], {})[r["event_type"]] = r["c"]

                for t in topics:
                    t["accuracy"] = round(float(t["accuracy"] or 0), 1)
                    t["avg_time_seconds"] = round(float(t["avg_time_seconds"]), 1) if t["avg_time_seconds"] is not None else None
                    f = funnel.get(t["name"])
                    if f and f.get("quiz_started"):
                        started = f.get("quiz_started", 0)
                        completed = f.get("quiz_completed", 0)
                        t["completion_rate"] = round(completed / started * 100, 1) if started else None
                        t["drop_rate"] = round((started - completed) / started * 100, 1) if started else None
                    else:
                        t["completion_rate"] = None
                        t["drop_rate"] = None
                return topics
        finally:
            self.release_conn(conn)

    def get_question_analytics(self, start_date, end_date, topic_id=None, sort_by="attempts", page=1, page_size=25):
        conn = self.get_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                start_dt, end_dt = self._period_bounds(start_date, end_date)
                topic_clause = "AND q.topic_id = %s" if topic_id else ""
                params = [start_dt, end_dt]
                if topic_id:
                    params.append(topic_id)

                sort_columns = {
                    "attempts": "attempts DESC",
                    "correct_pct": "correct_pct ASC",
                    "wrong_count": "wrong_count DESC",
                    "skipped_count": "skipped_count DESC",
                    "avg_time_seconds": "avg_time_seconds DESC NULLS LAST",
                }
                order_clause = sort_columns.get(sort_by, sort_columns["attempts"])

                cur.execute(
                    f"""
                    SELECT q.id, q.question_en, q.difficulty, t.name AS topic_name,
                           COUNT(ua.id) AS attempts,
                           SUM(CASE WHEN ua.is_correct THEN 1 ELSE 0 END) AS correct_count,
                           SUM(CASE WHEN ua.selected_option = 'E' THEN 1 ELSE 0 END) AS skipped_count,
                           AVG(ua.response_time_ms) / 1000.0 AS avg_time_seconds
                    FROM questions q
                    JOIN topics t ON q.topic_id = t.id
                    LEFT JOIN user_answers ua ON ua.question_id = q.id
                    LEFT JOIN test_sessions ts ON ua.session_id = ts.id AND ts.timestamp BETWEEN %s AND %s
                    WHERE 1=1 {topic_clause}
                    GROUP BY q.id, q.question_en, q.difficulty, t.name
                    HAVING COUNT(ua.id) > 0
                    ORDER BY {order_clause}
                    LIMIT %s OFFSET %s;
                    """,
                    params + [page_size, (page - 1) * page_size],
                )
                rows = [dict(r) for r in cur.fetchall()]
                for r in rows:
                    attempts = r["attempts"] or 0
                    correct = r["correct_count"] or 0
                    skipped = r["skipped_count"] or 0
                    wrong = attempts - correct - skipped
                    r["correct_pct"] = round(correct / attempts * 100, 1) if attempts else 0
                    r["wrong_pct"] = round(wrong / attempts * 100, 1) if attempts else 0
                    r["skipped_pct"] = round(skipped / attempts * 100, 1) if attempts else 0
                    r["wrong_count"] = wrong
                    r["avg_time_seconds"] = round(float(r["avg_time_seconds"]), 1) if r["avg_time_seconds"] is not None else None
                    r["question_en"] = (r["question_en"] or "")[:160]
                    # Not tracked yet - future app update features
                    r["bookmark_pct"] = None
                    r["report_pct"] = None
                    r["liked_pct"] = None
                    r["disliked_pct"] = None
                return rows
        finally:
            self.release_conn(conn)

    def log_event(self, user_id, event_type, meta_data=None):
        conn = self.get_conn()
        try:
            with conn.cursor() as cur:
                user_uuid = self._resolve_user_uuid(cur, user_id, create_if_missing=True)
                cur.execute(
                    "INSERT INTO activity_logs (user_id, event_type, meta_data) VALUES (%s, %s, %s);",
                    (user_uuid, event_type, json.dumps(meta_data or {})),
                )
                cur.execute("UPDATE users SET last_active_at = CURRENT_TIMESTAMP WHERE id = %s;", (user_uuid,))
                conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Error logging event: {e}")
        finally:
            self.release_conn(conn)

    def update_user_device_info(self, user_id, platform=None, os_version=None, app_version=None, country=None, display_name=None):
        conn = self.get_conn()
        try:
            with conn.cursor() as cur:
                user_uuid = self._resolve_user_uuid(cur, user_id, create_if_missing=True)
                cur.execute(
                    """
                    UPDATE users SET
                        platform = COALESCE(%s, platform),
                        os_version = COALESCE(%s, os_version),
                        app_version = COALESCE(%s, app_version),
                        country = COALESCE(%s, country),
                        display_name = COALESCE(%s, display_name),
                        last_active_at = CURRENT_TIMESTAMP
                    WHERE id = %s;
                    """,
                    (platform, os_version, app_version, country, display_name, user_uuid),
                )
                conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Error updating user device info: {e}")
        finally:
            self.release_conn(conn)

    def _resolve_user_uuid(self, cur, user_id, create_if_missing=False):
        import uuid
        is_uuid = False
        try:
            uuid.UUID(str(user_id))
            is_uuid = True
        except ValueError:
            pass

        if is_uuid:
            cur.execute("SELECT id FROM users WHERE id = %s;", (user_id,))
        else:
            email = f"user_{user_id}@example.com" if "@" not in str(user_id) else user_id
            cur.execute("SELECT id FROM users WHERE email = %s;", (email,))

        row = cur.fetchone()
        if row:
            return row[0]

        if not create_if_missing:
            return None

        email = f"user_{user_id}@example.com" if "@" not in str(user_id) else user_id
        cur.execute(
            "INSERT INTO users (display_name, email) VALUES (%s, %s) "
            "ON CONFLICT (email) DO UPDATE SET email = EXCLUDED.email RETURNING id;",
            ("Test User", email),
        )
        return cur.fetchone()[0]


# Singleton instance
db = QuestionDatabase()
