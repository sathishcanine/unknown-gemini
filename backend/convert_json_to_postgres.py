import os
import json
import psycopg2
from psycopg2.extras import Json

# Resolve project directories
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BACKEND_DIR)

MAPPING_PATH = os.path.join(BACKEND_DIR, "textbook_mapping.json")

JSON_PATHS = {
    "Economy": os.path.join(ROOT_DIR, "Economic", "economics_questions_db.json"),
    "Polity": os.path.join(ROOT_DIR, "Polity", "polity_questions_db.json"),
    "Policy": os.path.join(ROOT_DIR, "Policy", "policy_questions_db.json"),
    "Current Affairs": os.path.join(ROOT_DIR, "Current-affairs", "current_affairs_questions_db.json"),
}

SUBJECTS_METADATA = [
    {"id": "Economy", "name": "Indian Economy", "icon": "📈"},
    {"id": "Polity", "name": "Indian Polity", "icon": "⚖️"},
    {"id": "Current Affairs", "name": "Current Affairs", "icon": "📰"},
    {"id": "Policy", "name": "Policy Notes", "icon": "📋"},
]

def main():
    db_url = os.getenv("DATABASE_URL", "dbname=tnpsc_prep user=sathishkumar host=localhost port=5432")
    print(f"Connecting to PostgreSQL database: {db_url}")
    
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    # 1. Drop existing tables if they exist to start clean
    print("Dropping old tables...")
    cursor.execute("DROP TABLE IF EXISTS leaderboard CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS activity_logs CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS user_answers CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS test_sessions CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS options CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS questions CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS topics CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS subjects CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS users CASCADE;")
    
    # 2. Create Tables
    print("Creating tables...")
    
    cursor.execute("""
    CREATE TABLE users (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        email VARCHAR(100) UNIQUE,
        google_id VARCHAR(100) UNIQUE,
        display_name VARCHAR(100),
        phone_number VARCHAR(20),
        whatsapp_enabled BOOLEAN DEFAULT FALSE,
        total_points INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    cursor.execute("""
    CREATE TABLE subjects (
        id VARCHAR(50) PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        icon VARCHAR(10) NOT NULL
    );
    """)
    
    cursor.execute("""
    CREATE TABLE topics (
        id SERIAL PRIMARY KEY,
        subject_id VARCHAR(50) NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
        name VARCHAR(255) NOT NULL,
        textbook_mapping JSONB
    );
    """)
    
    cursor.execute("""
    CREATE TABLE questions (
        id SERIAL PRIMARY KEY,
        subject_id VARCHAR(50) NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
        topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
        question_en TEXT NOT NULL,
        question_ta TEXT NOT NULL,
        correct_option VARCHAR(5) NOT NULL,
        explanation TEXT,
        explanation_ta TEXT,
        difficulty VARCHAR(20) NOT NULL,
        type VARCHAR(20) NOT NULL,
        batch VARCHAR(100),
        source_exam TEXT,
        source_fact TEXT
    );
    """)
    
    cursor.execute("""
    CREATE TABLE options (
        id SERIAL PRIMARY KEY,
        question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
        key VARCHAR(5) NOT NULL,
        text_en TEXT NOT NULL,
        text_ta TEXT NOT NULL
    );
    """)
    
    cursor.execute("""
    CREATE TABLE test_sessions (
        id SERIAL PRIMARY KEY,
        user_id UUID REFERENCES users(id) ON DELETE SET NULL,
        topic_id INTEGER REFERENCES topics(id) ON DELETE SET NULL,
        correct_count INTEGER NOT NULL,
        total_count INTEGER NOT NULL,
        time_taken INTEGER NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    cursor.execute("""
    CREATE TABLE user_answers (
        id SERIAL PRIMARY KEY,
        session_id INTEGER NOT NULL REFERENCES test_sessions(id) ON DELETE CASCADE,
        question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
        selected_option VARCHAR(5) NOT NULL,
        is_correct BOOLEAN NOT NULL
    );
    """)
    
    cursor.execute("""
    CREATE TABLE activity_logs (
        id SERIAL PRIMARY KEY,
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        event_type VARCHAR(100) NOT NULL,
        meta_data JSONB,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    cursor.execute("""
    CREATE TABLE leaderboard (
        user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        weekly_points INTEGER DEFAULT 0,
        monthly_points INTEGER DEFAULT 0,
        rank INTEGER,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # 3. Insert Subjects Metadata
    print("Inserting subjects...")
    for sub in SUBJECTS_METADATA:
        cursor.execute("INSERT INTO subjects (id, name, icon) VALUES (%s, %s, %s);", 
                       (sub["id"], sub["name"], sub["icon"]))
        
    # 4. Load Textbook Mappings to seed Topics table
    textbook_mappings = {}
    if os.path.exists(MAPPING_PATH):
        with open(MAPPING_PATH, "r", encoding="utf-8") as f:
            textbook_mappings = json.load(f)
            
    # Helper to resolve/insert topic ID dynamically
    topic_cache = {}
    
    def get_or_create_topic(subject_id, topic_name):
        topic_name = topic_name or "General"
        key = (subject_id, topic_name)
        if key in topic_cache:
            return topic_cache[key]
            
        cursor.execute("SELECT id FROM topics WHERE subject_id = %s AND name = %s;", (subject_id, topic_name))
        row = cursor.fetchone()
        if row:
            topic_cache[key] = row[0]
            return row[0]
            
        mapping = textbook_mappings.get(topic_name)
        mapping_json = Json(mapping) if mapping else None
        
        cursor.execute("INSERT INTO topics (subject_id, name, textbook_mapping) VALUES (%s, %s, %s) RETURNING id;",
                       (subject_id, topic_name, mapping_json))
        topic_id = cursor.fetchone()[0]
        topic_cache[key] = topic_id
        return topic_id

    # 5. Load JSON Questions and Insert
    for subject_key, db_path in JSON_PATHS.items():
        if not os.path.exists(db_path):
            print(f"Warning: Question bank not found for {subject_key} at {db_path}")
            continue
            
        print(f"Importing {subject_key} questions...")
        with open(db_path, "r", encoding="utf-8") as f:
            questions = json.load(f)
            
        for q in questions:
            sub = q.get("subject") or subject_key
            if sub in ["Economy", "Economics"]:
                sub = "Economy"
            elif sub == "Polity":
                sub = "Polity"
            elif sub == "Policy":
                sub = "Policy"
            elif sub == "Current Affairs":
                sub = "Current Affairs"
            else:
                sub = subject_key
                
            topic_name = q.get("topic") or "General"
            topic_id = get_or_create_topic(sub, topic_name)
            
            q_en = q.get("question_en") or ""
            q_ta = q.get("question_ta") or q_en
            correct_opt = q.get("correct_option") or q.get("answer_en") or q.get("answer") or ""
            exp = q.get("explanation") or ""
            exp_ta = q.get("explanation_ta") or ""
            diff = q.get("difficulty") or "Medium"
            q_type = q.get("type") or "practice"
            batch = q.get("batch") or ""
            exam = q.get("source_exam") or ""
            fact = q.get("source_fact") or ""
            
            cursor.execute("""
                INSERT INTO questions (
                    subject_id, topic_id, question_en, question_ta, correct_option, 
                    explanation, explanation_ta, difficulty, type, batch, source_exam, source_fact
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
            """, (sub, topic_id, q_en, q_ta, correct_opt, exp, exp_ta, diff, q_type, batch, exam, fact))
            
            question_id = cursor.fetchone()[0]
            
            options = q.get("options") or []
            for opt in options:
                opt_key = opt.get("key", "")
                text_en = opt.get("text_en") or opt.get("text_ta") or ""
                if not text_en:
                    for k, v in opt.items():
                        if "text" in k and k != "text_ta":
                            text_en = v
                            break
                text_ta = opt.get("text_ta") or text_en or ""
                
                cursor.execute("""
                    INSERT INTO options (question_id, key, text_en, text_ta) 
                    VALUES (%s, %s, %s, %s);
                """, (question_id, opt_key, text_en, text_ta))
                
    # 6. Create Indices for performance
    print("Creating indices...")
    cursor.execute("CREATE INDEX idx_questions_lookup ON questions(subject_id, topic_id, type, batch);")
    cursor.execute("CREATE INDEX idx_options_question ON options(question_id);")
    cursor.execute("CREATE INDEX idx_topics_subject ON topics(subject_id);")
    
    conn.commit()
    
    # Print counts
    cursor.execute("SELECT COUNT(*) FROM questions;")
    total_q = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM topics;")
    total_t = cursor.fetchone()[0]
    
    print(f"Success! Imported {total_q} questions and seed-mapped {total_t} topics to PostgreSQL.")
    conn.close()

if __name__ == "__main__":
    main()
