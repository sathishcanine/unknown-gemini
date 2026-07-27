import os
import json
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAPPING_PATH = os.path.join(ROOT_DIR, "backend", "textbook_mapping.json")

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
                    SELECT s.id, s.name, s.icon, COUNT(q.id) as questions_count
                    FROM subjects s
                    LEFT JOIN questions q ON s.id = q.subject_id
                    GROUP BY s.id, s.name, s.icon;
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
            with conn.cursor() as cur:
                # Normalise input subject name matching DB ID
                sub_norm = subject
                if subject in ["Economy", "Economics"]:
                    sub_norm = "Economy"
                
                cur.execute("""
                    SELECT DISTINCT name 
                    FROM topics 
                    WHERE subject_id = %s 
                    ORDER BY name;
                """, (sub_norm,))
                rows = cur.fetchall()
                return [row[0] for row in rows]
        except Exception as e:
            print(f"Error in get_topics_for_subject: {e}")
            return []
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

    def save_test_session(self, user_id, topic_name, correct_count, total_count, time_taken, answers):
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

                cur.execute("SELECT id FROM topics WHERE name = %s;", (topic_name,))
                topic_row = cur.fetchone()
                if topic_row:
                    topic_id = topic_row[0]
                else:
                    cur.execute("INSERT INTO topics (subject_id, name) VALUES (%s, %s) RETURNING id;", 
                                (subject_id, topic_name))
                    topic_id = cur.fetchone()[0]

                # 2. Ensure user exists (auto-register/upsert user for testing/auth convenience)
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
                            user_uuid = user_row[0]
                    except Exception:
                        pass

                if not user_uuid:
                    cur.execute("""
                        INSERT INTO users (display_name, email) 
                        VALUES (%s, %s) 
                        ON CONFLICT (email) DO UPDATE SET display_name = EXCLUDED.display_name
                        RETURNING id;
                    """, ("Test User", f"user_{user_id}@example.com" if "@" not in user_id else user_id))
                    user_uuid = cur.fetchone()[0]

                # 3. Save Test Session
                cur.execute("""
                    INSERT INTO test_sessions (user_id, topic_id, correct_count, total_count, time_taken)
                    VALUES (%s, %s, %s, %s, %s) RETURNING id;
                """, (user_uuid, topic_id, correct_count, total_count, time_taken))
                session_id = cur.fetchone()[0]

                # 4. Save individual user responses
                for ans in answers:
                    q_id = ans.get("question_id")
                    selected = ans.get("selected_option", "")
                    is_correct = ans.get("is_correct", False)

                    cur.execute("""
                        INSERT INTO user_answers (session_id, question_id, selected_option, is_correct)
                        VALUES (%s, %s, %s, %s);
                    """, (session_id, q_id, selected, is_correct))

                # 5. Log Activity
                cur.execute("""
                    INSERT INTO activity_logs (user_id, event_type, meta_data)
                    VALUES (%s, %s, %s);
                """, (user_uuid, "quiz_completed", json.dumps({
                    "session_id": session_id,
                    "topic": topic_name,
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
                    SELECT ts.id, t.name as topic_name, ts.correct_count, ts.total_count, ts.time_taken, ts.timestamp
                    FROM test_sessions ts
                    JOIN topics t ON ts.topic_id = t.id
                    WHERE ts.user_id = %s
                    ORDER BY ts.timestamp DESC;
                """, (user_uuid,))

                rows = cur.fetchall()
                res = []
                for r in rows:
                    rd = dict(r)
                    rd["timestamp"] = rd["timestamp"].isoformat()
                    res.append(rd)
                return res
        except Exception as e:
            print(f"Error in get_user_history: {e}")
            return []
        finally:
            self.release_conn(conn)

# Singleton instance
db = QuestionDatabase()
