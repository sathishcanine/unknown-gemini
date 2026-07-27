import os
import json
import sqlite3

# Resolve project directories
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BACKEND_DIR)

DB_FILE = os.path.join(BACKEND_DIR, "tnpsc_prep.db")
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
    print(f"Creating SQLite database at: {DB_FILE}")
    
    # Remove existing database file if present
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 1. Create Tables
    cursor.execute("""
    CREATE TABLE subjects (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        icon TEXT NOT NULL
    );
    """)
    
    cursor.execute("""
    CREATE TABLE topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id TEXT NOT NULL,
        name TEXT NOT NULL,
        textbook_mapping TEXT, -- JSON string representation
        FOREIGN KEY (subject_id) REFERENCES subjects(id)
    );
    """)
    
    cursor.execute("""
    CREATE TABLE questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id TEXT NOT NULL,
        topic_id INTEGER NOT NULL,
        question_en TEXT NOT NULL,
        question_ta TEXT NOT NULL,
        correct_option TEXT NOT NULL,
        explanation TEXT,
        explanation_ta TEXT,
        difficulty TEXT NOT NULL,
        type TEXT NOT NULL,
        batch TEXT,
        source_exam TEXT,
        source_fact TEXT,
        FOREIGN KEY (subject_id) REFERENCES subjects(id),
        FOREIGN KEY (topic_id) REFERENCES topics(id)
    );
    """)
    
    cursor.execute("""
    CREATE TABLE options (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER NOT NULL,
        key TEXT NOT NULL,
        text_en TEXT NOT NULL,
        text_ta TEXT NOT NULL,
        FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
    );
    """)
    
    # 2. Insert Subjects Metadata
    for sub in SUBJECTS_METADATA:
        cursor.execute("INSERT INTO subjects (id, name, icon) VALUES (?, ?, ?);", 
                       (sub["id"], sub["name"], sub["icon"]))
        
    # 3. Load Textbook Mappings to seed Topics table
    textbook_mappings = {}
    if os.path.exists(MAPPING_PATH):
        with open(MAPPING_PATH, "r", encoding="utf-8") as f:
            textbook_mappings = json.load(f)
            
    # Helper to resolve/insert topic ID dynamically
    topic_cache = {} # Key: (subject_id, topic_name) -> topic_id
    
    def get_or_create_topic(subject_id, topic_name):
        topic_name = topic_name or "General"
        key = (subject_id, topic_name)
        if key in topic_cache:
            return topic_cache[key]
            
        # Check database
        cursor.execute("SELECT id FROM topics WHERE subject_id = ? AND name = ?;", (subject_id, topic_name))
        row = cursor.fetchone()
        if row:
            topic_cache[key] = row[0]
            return row[0]
            
        # Insert new topic
        mapping = textbook_mappings.get(topic_name)
        mapping_str = json.dumps(mapping) if mapping else None
        
        cursor.execute("INSERT INTO topics (subject_id, name, textbook_mapping) VALUES (?, ?, ?);",
                       (subject_id, topic_name, mapping_str))
        topic_id = cursor.lastrowid
        topic_cache[key] = topic_id
        return topic_id

    # 4. Load JSON Questions and Insert
    for subject_key, db_path in JSON_PATHS.items():
        if not os.path.exists(db_path):
            print(f"Warning: Question bank not found for {subject_key} at {db_path}")
            continue
            
        print(f"Importing {subject_key} questions...")
        with open(db_path, "r", encoding="utf-8") as f:
            questions = json.load(f)
            
        for q in questions:
            # Normalize subject keys
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
            
            # Extract properties
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
            
            # Insert Question
            cursor.execute("""
                INSERT INTO questions (
                    subject_id, topic_id, question_en, question_ta, correct_option, 
                    explanation, explanation_ta, difficulty, type, batch, source_exam, source_fact
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (sub, topic_id, q_en, q_ta, correct_opt, exp, exp_ta, diff, q_type, batch, exam, fact))
            
            question_id = cursor.lastrowid
            
            # Normalize and Insert Options
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
                    VALUES (?, ?, ?, ?);
                """, (question_id, opt_key, text_en, text_ta))
                
    # 5. Create Indices for rapid lookups on demand
    print("Creating database indices...")
    cursor.execute("CREATE INDEX idx_questions_lookup ON questions(subject_id, topic_id, type, batch);")
    cursor.execute("CREATE INDEX idx_options_question ON options(question_id);")
    cursor.execute("CREATE INDEX idx_topics_subject ON topics(subject_id);")
    
    conn.commit()
    
    # Log counts
    cursor.execute("SELECT COUNT(*) FROM questions;")
    total_q = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM topics;")
    total_t = cursor.fetchone()[0]
    
    print(f"Success! Imported {total_q} questions and seed-mapped {total_t} topics.")
    conn.close()

if __name__ == "__main__":
    main()
