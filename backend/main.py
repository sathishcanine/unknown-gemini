from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import json

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from database import db

# Resolve project root directory path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(title="TNPSC Prep API", description="Backend API for TNPSC Practice Questions & Advisor")

# Enable CORS for Flutter app connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["*"],
)

# Serve static frontend files
@app.get("/")
def read_index():
    return FileResponse(os.path.join(ROOT_DIR, "index.html"))

@app.get("/app.js")
def read_js():
    return FileResponse(os.path.join(ROOT_DIR, "app.js"))

@app.get("/styles.css")
def read_css():
    return FileResponse(os.path.join(ROOT_DIR, "styles.css"))

# Mount subdirectories as static files
app.mount("/Polity", StaticFiles(directory=os.path.join(ROOT_DIR, "Polity")), name="Polity")
app.mount("/Economic", StaticFiles(directory=os.path.join(ROOT_DIR, "Economic")), name="Economic")
app.mount("/Policy", StaticFiles(directory=os.path.join(ROOT_DIR, "Policy")), name="Policy")
app.mount("/Current-affairs", StaticFiles(directory=os.path.join(ROOT_DIR, "Current-affairs")), name="Current-affairs")

# Request / Response Schemas
class SubjectResponse(BaseModel):
    id: str
    name: str
    icon: str
    questions_count: int

class TextbookMappingModel(BaseModel):
    title: str
    titleTa: str
    book: str
    chapter: str
    pages: str
    focus: str

class TopicResponse(BaseModel):
    name: str
    textbook: Optional[TextbookMappingModel] = None

class OptionModel(BaseModel):
    key: str
    text_en: str
    text_ta: str

class QuestionModel(BaseModel):
    id: Optional[int] = None
    subject: str
    topic: str
    source_exam: Optional[str] = ""
    difficulty: Optional[str] = "Medium"
    question_en: str
    question_ta: str
    options: List[OptionModel]
    correct_option: str
    explanation: str
    explanation_ta: str
    type: Optional[str] = "practice"
    batch: Optional[str] = ""
    group: Optional[str] = "Practice"
    source_fact: Optional[str] = ""

class AnswerSubmitModel(BaseModel):
    question_id: int
    selected_option: str
    is_correct: bool

class SessionSubmitRequest(BaseModel):
    user_id: str
    topic_name: str
    correct_count: int
    total_count: int
    time_taken: int
    answers: List[AnswerSubmitModel]

class SessionSubmitResponse(BaseModel):
    session_id: int
    status: str = "success"

class HistoryEntry(BaseModel):
    topic: str
    group: str
    correctCount: int
    totalCount: int
    answers: Dict[str, str]  # qIndexStr -> selectedOption
    questions: List[QuestionModel]
    timestamp: Optional[float] = None

class HistorySubmitRequest(BaseModel):
    session: HistoryEntry
    all_history: List[HistoryEntry]

class WeaknessReport(BaseModel):
    topic: str
    accuracy: int
    status: str
    textbook: Optional[TextbookMappingModel] = None

class StatsResponse(BaseModel):
    total_tests: int
    total_correct: int
    total_solved: int
    avg_accuracy: int
    mastery_percent: int
    weakness: Optional[WeaknessReport] = None

@app.get("/api/subjects", response_model=List[SubjectResponse])
def get_subjects():
    return db.get_subjects()

@app.get("/api/syllabus/{subject}", response_model=List[TopicResponse])
def get_syllabus(subject: str):
    topics = db.get_topics_for_subject(subject)
    response = []
    for topic_name in topics:
        # Resolve textbook mapping metadata
        mapping = db.textbook_mappings.get(topic_name)
        response.append(TopicResponse(name=topic_name, textbook=mapping))
    return response

@app.get("/api/questions", response_model=List[QuestionModel])
def get_questions(
    subject: str,
    topic: Optional[str] = None,
    batch: Optional[str] = None
):
    qs = db.get_questions(subject, topic, batch)
    return qs

@app.post("/api/stats", response_model=StatsResponse)
def calculate_stats(history: List[HistoryEntry]):
    total_tests = len(history)
    if total_tests == 0:
        return StatsResponse(
            total_tests=0,
            total_correct=0,
            total_solved=0,
            avg_accuracy=0,
            mastery_percent=0,
            weakness=None
        )

    total_correct = 0
    total_solved = 0
    
    # Track stats by topic to calculate weakness
    topic_stats = {}
    
    for session in history:
        total_correct += session.correctCount
        total_solved += session.totalCount
        
        # Aggregate by topic
        t_name = session.topic
        if t_name not in topic_stats:
            topic_stats[t_name] = {"correct": 0, "total": 0}
        topic_stats[t_name]["correct"] += session.correctCount
        topic_stats[t_name]["total"] += session.totalCount

    avg_accuracy = round((total_correct / total_solved) * 100) if total_solved > 0 else 0
    
    # Calculate weaknesses (accuracy < 70% for topics with at least 5 questions solved)
    weakness_report = None
    critical_weakness = None
    
    for t_name, stats in topic_stats.items():
        if stats["total"] >= 5:
            acc = round((stats["correct"] / stats["total"]) * 100)
            if acc < 70:
                # Find corresponding textbook mapping
                textbook = db.textbook_mappings.get(t_name)
                critical_weakness = WeaknessReport(
                    topic=t_name,
                    accuracy=acc,
                    status="critical",
                    textbook=textbook
                )
                break  # Return the first critical weakness found

    # Mastery percent is linked to average accuracy
    mastery_percent = avg_accuracy

    return StatsResponse(
        total_tests=total_tests,
        total_correct=total_correct,
        total_solved=total_solved,
        avg_accuracy=avg_accuracy,
        mastery_percent=mastery_percent,
        weakness=critical_weakness
    )

class SessionHistoryResponse(BaseModel):
    id: int
    topic_name: str
    correct_count: int
    total_count: int
    time_taken: int
    timestamp: str

@app.post("/api/sessions/submit", response_model=SessionSubmitResponse)
def submit_session(req: SessionSubmitRequest):
    try:
        session_id = db.save_test_session(
            user_id=req.user_id,
            topic_name=req.topic_name,
            correct_count=req.correct_count,
            total_count=req.total_count,
            time_taken=req.time_taken,
            answers=[ans.dict() for ans in req.answers]
        )
        return SessionSubmitResponse(session_id=session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/history", response_model=List[SessionHistoryResponse])
def get_user_history(user_id: str):
    return db.get_user_history(user_id)

@app.delete("/api/users/{user_id}")
def delete_user_account(user_id: str):
    success = db.delete_user_account(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Account deleted successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8085)
