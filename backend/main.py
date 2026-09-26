from fastapi import FastAPI, Query, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import json
import datetime

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from database import db
from admin_auth import hash_password, verify_password, create_access_token, require_admin
from razorpay_payments import (
    razorpay_configured,
    razorpay_key_id,
    create_order as rz_create_order,
    verify_payment_signature,
    verify_webhook_signature,
)

# Resolve project root directory path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(title="TNPSC Prep API", description="Backend API for TNPSC Practice Questions & Advisor")

@app.on_event("startup")
def _startup_ensure_schema():
    try:
        db.ensure_whatsapp_columns()
        db.ensure_subscription_schema()
        db.ensure_learn_card_columns()
    except Exception as e:
        print(f"Startup schema ensure failed: {e}")

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

@app.get("/privacy")
@app.get("/privacy-policy")
def read_privacy():
    return FileResponse(os.path.join(ROOT_DIR, "privacy.html"))

@app.get("/delete-account")
def read_delete_account():
    return FileResponse(os.path.join(ROOT_DIR, "delete-account.html"))

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
app.mount("/TVK", StaticFiles(directory=os.path.join(ROOT_DIR, "TVK")), name="TVK")
app.mount("/Current-affairs", StaticFiles(directory=os.path.join(ROOT_DIR, "Current-affairs")), name="Current-affairs")
# Aptitude/Reasoning figure media (PNG crops)
_aptitude_media = os.path.join(ROOT_DIR, "Aptitude", "media")
os.makedirs(_aptitude_media, exist_ok=True)
app.mount("/media/aptitude", StaticFiles(directory=_aptitude_media), name="aptitude_media")

# Request / Response Schemas
class SubjectResponse(BaseModel):
    id: str
    name: str
    name_ta: Optional[str] = None
    icon: str
    questions_count: int

class TextbookMappingModel(BaseModel):
    title: str = ""
    titleTa: str = ""
    book: str = ""
    chapter: str = ""
    pages: str = ""
    focus: str = ""

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
    explanation: Optional[str] = ""
    explanation_ta: Optional[str] = ""
    learning_tip: Optional[str] = ""
    learning_tip_ta: Optional[str] = ""
    exam_trick: Optional[str] = ""
    exam_trick_ta: Optional[str] = ""
    type: Optional[str] = "practice"
    batch: Optional[str] = ""
    group: Optional[str] = "Practice"
    source_fact: Optional[str] = ""
    image_urls: Optional[List[str]] = []
    tags: Optional[List[str]] = []

class AnswerSubmitModel(BaseModel):
    question_id: int
    selected_option: str
    is_correct: bool
    response_time_ms: Optional[int] = None

class SessionSubmitRequest(BaseModel):
    user_id: str
    topic_name: str
    correct_count: int
    total_count: int
    time_taken: int
    answers: List[AnswerSubmitModel]
    batch: Optional[str] = None

class CompletedBatchResponse(BaseModel):
    batch: str
    correct_count: int
    total_count: int
    timestamp: Optional[str] = None

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

TAMIL_UNITS_PATH = os.path.join(ROOT_DIR, "backend", "tamil_units.json")
ENGLISH_UNITS_PATH = os.path.join(ROOT_DIR, "backend", "english_units.json")


def _load_tamil_units_config() -> dict:
    if not os.path.exists(TAMIL_UNITS_PATH):
        return {"units": []}
    try:
        with open(TAMIL_UNITS_PATH, "r", encoding="utf-8") as f:
            return json.load(f) or {"units": []}
    except Exception as e:
        print(f"Error loading tamil_units.json: {e}")
        return {"units": []}


def _load_english_units_config() -> dict:
    if not os.path.exists(ENGLISH_UNITS_PATH):
        return {"units": []}
    try:
        with open(ENGLISH_UNITS_PATH, "r", encoding="utf-8") as f:
            return json.load(f) or {"units": []}
    except Exception as e:
        print(f"Error loading english_units.json: {e}")
        return {"units": []}


class TamilUnitResponse(BaseModel):
    id: str
    order: int = 0
    name_ta: str
    name_en: str = ""
    subtitle_ta: str = ""
    subtitle_en: str = ""
    accent: str = "#3B82F6"
    icon: str = "menu_book_outlined"
    topics: List[str] = []
    topic_count: int = 0
    questions_count: int = 0


class EnglishGroupResponse(BaseModel):
    id: str
    order: int = 0
    name_en: str
    name_ta: str = ""
    subtitle_en: str = ""
    subtitle_ta: str = ""
    accent: str = "#0D9488"
    icon: str = "schedule_outlined"
    topics: List[str] = []
    topic_count: int = 0
    questions_count: int = 0


class EnglishMenuResponse(BaseModel):
    id: str
    order: int = 0
    name_en: str
    name_ta: str = ""
    subtitle_en: str = ""
    subtitle_ta: str = ""
    accent: str = "#0891B2"
    icon: str = "category_outlined"
    topics: List[str] = []
    groups: List[EnglishGroupResponse] = []
    topic_count: int = 0
    questions_count: int = 0
    group_count: int = 0


class EnglishUnitResponse(BaseModel):
    id: str
    order: int = 0
    name_en: str
    name_ta: str = ""
    subtitle_en: str = ""
    subtitle_ta: str = ""
    accent: str = "#06B6D4"
    icon: str = "translate_outlined"
    menus: List[EnglishMenuResponse] = []
    menu_count: int = 0
    questions_count: int = 0


@app.get("/api/subjects", response_model=List[SubjectResponse])
def get_subjects():
    return db.get_subjects()


@app.get("/api/tamil/units", response_model=List[TamilUnitResponse])
def get_tamil_units():
    """Podhu Tamil unit menu — driven by backend/tamil_units.json (no app rebuild to add units)."""
    cfg = _load_tamil_units_config()
    units = list(cfg.get("units") or [])
    units.sort(key=lambda u: int(u.get("order") or 0))
    counts = db.get_tamil_topic_question_counts()

    out: List[TamilUnitResponse] = []
    for u in units:
        topics = [str(t).strip() for t in (u.get("topics") or []) if str(t).strip()]
        live_topics = [t for t in topics if t in counts]
        q_total = sum(counts.get(t, 0) for t in live_topics)
        out.append(
            TamilUnitResponse(
                id=str(u.get("id") or ""),
                order=int(u.get("order") or 0),
                name_ta=str(u.get("name_ta") or u.get("id") or ""),
                name_en=str(u.get("name_en") or ""),
                subtitle_ta=str(u.get("subtitle_ta") or ""),
                subtitle_en=str(u.get("subtitle_en") or ""),
                accent=str(u.get("accent") or "#3B82F6"),
                icon=str(u.get("icon") or "menu_book_outlined"),
                topics=topics,
                topic_count=len(live_topics) if counts else len(topics),
                questions_count=q_total,
            )
        )
    return out


@app.get("/api/english/units", response_model=List[EnglishUnitResponse])
def get_english_units():
    """General English unit/menu hub — driven by backend/english_units.json."""
    cfg = _load_english_units_config()
    units = list(cfg.get("units") or [])
    units.sort(key=lambda u: int(u.get("order") or 0))
    counts = db.get_topic_question_counts("English")

    out: List[EnglishUnitResponse] = []
    for u in units:
        menus_cfg = list(u.get("menus") or [])
        menus_cfg.sort(key=lambda m: int(m.get("order") or 0))
        menus: List[EnglishMenuResponse] = []
        unit_q = 0
        for m in menus_cfg:
            groups_cfg = list(m.get("groups") or [])
            groups_cfg.sort(key=lambda g: int(g.get("order") or 0))
            groups: List[EnglishGroupResponse] = []
            group_topics: List[str] = []
            menu_q = 0
            for g in groups_cfg:
                g_topics = [str(t).strip() for t in (g.get("topics") or []) if str(t).strip()]
                group_topics.extend(g_topics)
                live_g = [t for t in g_topics if t in counts]
                g_q = sum(counts.get(t, 0) for t in live_g)
                menu_q += g_q
                groups.append(
                    EnglishGroupResponse(
                        id=str(g.get("id") or ""),
                        order=int(g.get("order") or 0),
                        name_en=str(g.get("name_en") or g.get("id") or ""),
                        name_ta=str(g.get("name_ta") or ""),
                        subtitle_en=str(g.get("subtitle_en") or ""),
                        subtitle_ta=str(g.get("subtitle_ta") or ""),
                        accent=str(g.get("accent") or "#0D9488"),
                        icon=str(g.get("icon") or "schedule_outlined"),
                        topics=g_topics,
                        topic_count=len(live_g) if counts else len(g_topics),
                        questions_count=g_q,
                    )
                )

            topics = [str(t).strip() for t in (m.get("topics") or []) if str(t).strip()]
            # Keep topics empty when nested groups exist — clients must open a group.
            if groups:
                topics = []
            elif not topics and group_topics:
                topics = list(dict.fromkeys(group_topics))  # preserve order, unique
            live_topics = [t for t in topics if t in counts]
            # topic_count for grouped menus = number of groups (menus under Tenses)
            if groups:
                topic_count = len(groups)
            else:
                topic_count = len(live_topics) if counts else len(topics)
            q_total = sum(counts.get(t, 0) for t in live_topics) if not groups else menu_q
            unit_q += q_total
            menus.append(
                EnglishMenuResponse(
                    id=str(m.get("id") or ""),
                    order=int(m.get("order") or 0),
                    name_en=str(m.get("name_en") or m.get("id") or ""),
                    name_ta=str(m.get("name_ta") or ""),
                    subtitle_en=str(m.get("subtitle_en") or ""),
                    subtitle_ta=str(m.get("subtitle_ta") or ""),
                    accent=str(m.get("accent") or "#0891B2"),
                    icon=str(m.get("icon") or "category_outlined"),
                    topics=topics,
                    groups=groups,
                    topic_count=topic_count,
                    questions_count=q_total,
                    group_count=len(groups),
                )
            )
        out.append(
            EnglishUnitResponse(
                id=str(u.get("id") or ""),
                order=int(u.get("order") or 0),
                name_en=str(u.get("name_en") or u.get("id") or ""),
                name_ta=str(u.get("name_ta") or ""),
                subtitle_en=str(u.get("subtitle_en") or ""),
                subtitle_ta=str(u.get("subtitle_ta") or ""),
                accent=str(u.get("accent") or "#06B6D4"),
                icon=str(u.get("icon") or "translate_outlined"),
                menus=menus,
                menu_count=len(menus),
                questions_count=unit_q,
            )
        )
    return out


@app.get("/api/syllabus/{subject}", response_model=List[TopicResponse])
def get_syllabus(
    subject: str,
    unit: Optional[str] = Query(None),
    menu: Optional[str] = Query(None),
    group: Optional[str] = Query(None),
):
    topics = db.get_topics_for_subject(subject)
    allowed = None
    topic_order: List[str] = []
    if subject == "Tamil" and unit:
        cfg = _load_tamil_units_config()
        for u in cfg.get("units") or []:
            if str(u.get("id")) == unit:
                topic_order = [
                    str(t).strip() for t in (u.get("topics") or []) if str(t).strip()
                ]
                allowed = set(topic_order)
                break
    if subject == "English" and (menu or group):
        cfg = _load_english_units_config()
        for u in cfg.get("units") or []:
            for m in u.get("menus") or []:
                if menu and str(m.get("id")) != menu:
                    continue
                if group:
                    for g in m.get("groups") or []:
                        if str(g.get("id")) == group:
                            topic_order = [
                                str(t).strip() for t in (g.get("topics") or []) if str(t).strip()
                            ]
                            allowed = set(topic_order)
                            break
                    if allowed is not None:
                        break
                else:
                    # Nested groups (Tenses): require group= — do not flatten all forms.
                    groups_cfg = list(m.get("groups") or [])
                    if groups_cfg:
                        topic_order = []
                        allowed = set()
                        break
                    # Flat menu topics
                    topic_order = [
                        str(t).strip() for t in (m.get("topics") or []) if str(t).strip()
                    ]
                    allowed = set(topic_order)
                    break
            if allowed is not None:
                break
    response = []
    for topic in topics:
        topic_name = topic["name"] if isinstance(topic, dict) else topic
        if allowed is not None and topic_name not in allowed:
            continue
        mapping = None
        if isinstance(topic, dict):
            mapping = topic.get("textbook_mapping")
        if not mapping:
            mapping = db.textbook_mappings.get(topic_name)
        response.append(TopicResponse(name=topic_name, textbook=mapping))
    if subject == "English" and topic_order:
        rank = {name: i for i, name in enumerate(topic_order)}
        response.sort(key=lambda t: rank.get(t.name, 10_000))
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
    batch: Optional[str] = None

class SessionDetailResponse(BaseModel):
    id: int
    topic_name: str
    batch: Optional[str] = None
    correct_count: int
    total_count: int
    time_taken: int
    timestamp: Optional[str] = None
    timestamp_ms: Optional[float] = None
    answers: Dict[str, str]
    questions: List[QuestionModel]

@app.post("/api/sessions/submit", response_model=SessionSubmitResponse)
def submit_session(req: SessionSubmitRequest):
    try:
        session_id = db.save_test_session(
            user_id=req.user_id,
            topic_name=req.topic_name,
            correct_count=req.correct_count,
            total_count=req.total_count,
            time_taken=req.time_taken,
            answers=[ans.dict() for ans in req.answers],
            batch=req.batch,
        )
        return SessionSubmitResponse(session_id=session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/history", response_model=List[SessionHistoryResponse])
def get_user_history(user_id: str):
    return db.get_user_history(user_id)

@app.get("/api/sessions/completed-batches", response_model=List[CompletedBatchResponse])
def get_completed_batches(user_id: str, topic: str = Query(...)):
    return db.get_completed_batches(user_id, topic)

@app.get("/api/sessions/{session_id}", response_model=SessionDetailResponse)
def get_session_detail(session_id: int, user_id: str = Query(...)):
    detail = db.get_session_detail(user_id, session_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Session not found")
    return detail

@app.delete("/api/users/{user_id}")
def delete_user_account(user_id: str):
    success = db.delete_user_account(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Account deleted successfully"}


# =============================================================================
# APP EVENT TRACKING (used by the Flutter app for analytics instrumentation)
# =============================================================================

class EventLogRequest(BaseModel):
    user_id: str
    event_type: str
    meta_data: Optional[Dict] = None

@app.post("/api/events")
def log_event(req: EventLogRequest):
    db.log_event(req.user_id, req.event_type, req.meta_data)
    return {"status": "ok"}


class DeviceInfoRequest(BaseModel):
    user_id: str
    display_name: Optional[str] = None
    phone_number: Optional[str] = None
    whatsapp_enabled: Optional[bool] = None

@app.post("/api/users/device-info")
def update_device_info(req: DeviceInfoRequest):
    # Optional profile fields after sign-in (display name, WhatsApp phone).
    # Intentionally does NOT collect platform/OS/app version or IP-derived country.
    db.update_user_device_info(
        req.user_id,
        display_name=req.display_name,
        phone_number=req.phone_number,
        whatsapp_enabled=req.whatsapp_enabled,
    )
    return {"status": "ok"}


class WhatsAppNumberRequest(BaseModel):
    user_id: str
    phone_number: str

@app.post("/api/users/whatsapp")
def save_whatsapp_number(req: WhatsAppNumberRequest):
    """Save / update a user's WhatsApp mobile number (from post-login screen)."""
    result = db.save_user_whatsapp(req.user_id, req.phone_number)
    if not result:
        raise HTTPException(
            status_code=400,
            detail="Invalid WhatsApp number. Enter a valid 10-digit Indian mobile.",
        )
    return {
        "status": "ok",
        "phone_number": result.get("phone_number"),
        "whatsapp_enabled": result.get("whatsapp_enabled", True),
    }


# =============================================================================
# ADMIN PANEL: AUTH
# =============================================================================

class AdminLoginRequest(BaseModel):
    username: str
    password: str

class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# Prefixed /api/admin/* so the React SPA can own /admin/* without route clashes
@app.post("/api/admin/auth/login", response_model=AdminLoginResponse)
def admin_login(req: AdminLoginRequest):
    admin = db.get_admin_by_username(req.username)
    if not admin or not verify_password(req.password, admin["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    db.touch_admin_login(req.username)
    token = create_access_token(req.username)
    return AdminLoginResponse(access_token=token)

@app.get("/api/admin/auth/me")
def admin_me(admin_username: str = Depends(require_admin)):
    return {"username": admin_username}


# =============================================================================
# ADMIN PANEL: ANALYTICS
# =============================================================================

def _default_dates(start: Optional[str], end: Optional[str]):
    from database import ist_today_iso
    today = ist_today_iso()
    return start or today, end or today

@app.get("/api/admin/dashboard/summary")
def admin_dashboard_summary(
    start: Optional[str] = None,
    end: Optional[str] = None,
    compare_start: Optional[str] = None,
    compare_end: Optional[str] = None,
    admin_username: str = Depends(require_admin),
):
    start, end = _default_dates(start, end)
    return db.get_dashboard_summary(start, end, compare_start, compare_end)

@app.get("/api/admin/users")
def admin_users_list(
    start: Optional[str] = None,
    end: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "last_active_at",
    page: int = 1,
    page_size: int = 20,
    user_filter: Optional[str] = None,
    filter: Optional[str] = None,
    admin_username: str = Depends(require_admin),
):
    start, end = _default_dates(start, end)
    return db.get_users_list(
        start,
        end,
        search=search,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
        user_filter=user_filter or filter,
    )

@app.get("/api/admin/users/{user_id}")
def admin_user_detail(user_id: str, admin_username: str = Depends(require_admin)):
    detail = db.get_user_detail(user_id)
    if not detail:
        raise HTTPException(status_code=404, detail="User not found")
    return detail

@app.get("/api/admin/users/{user_id}/timeline")
def admin_user_timeline(
    user_id: str,
    page: int = 1,
    page_size: int = 30,
    admin_username: str = Depends(require_admin),
):
    return db.get_user_timeline(user_id, page=page, page_size=page_size)


class PlanOverrideItem(BaseModel):
    plan_id: Optional[int] = None
    plan_code: Optional[str] = None
    code: Optional[str] = None
    price_inr: Optional[int] = None
    note: Optional[str] = None


class PlanOverridesBody(BaseModel):
    overrides: List[PlanOverrideItem]


class AdminPlanCreateBody(BaseModel):
    code: str
    name: str
    name_ta: Optional[str] = None
    duration_days: int
    price_inr: int
    sort_order: Optional[int] = None
    is_active: Optional[bool] = True


class AdminPlanUpdateBody(BaseModel):
    name: Optional[str] = None
    name_ta: Optional[str] = None
    duration_days: Optional[int] = None
    price_inr: Optional[int] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class AdminPlanReorderBody(BaseModel):
    ordered_ids: List[int]


@app.get("/api/plans")
def get_subscription_plans(user_id: Optional[str] = None):
    """Default or user-specific effective plan prices for the app."""
    return db.get_plans_for_user(user_id)


@app.get("/api/admin/plans")
def admin_list_plans(
    include_inactive: bool = True,
    admin_username: str = Depends(require_admin),
):
    return db.admin_list_plans(include_inactive=include_inactive)


@app.post("/api/admin/plans")
def admin_create_plan(
    body: AdminPlanCreateBody,
    admin_username: str = Depends(require_admin),
):
    try:
        return db.admin_create_plan(body.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/admin/plans/reorder")
def admin_reorder_plans(
    body: AdminPlanReorderBody,
    admin_username: str = Depends(require_admin),
):
    try:
        return db.admin_reorder_plans(body.ordered_ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/admin/plans/{plan_id}")
def admin_update_plan(
    plan_id: int,
    body: AdminPlanUpdateBody,
    admin_username: str = Depends(require_admin),
):
    try:
        data = db.admin_update_plan(plan_id, body.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not data:
        raise HTTPException(status_code=404, detail="Plan not found")
    return data


@app.delete("/api/admin/plans/{plan_id}")
def admin_delete_plan(
    plan_id: int,
    force: bool = False,
    admin_username: str = Depends(require_admin),
):
    try:
        data = db.admin_delete_plan(plan_id, force=force)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not data:
        raise HTTPException(status_code=404, detail="Plan not found")
    return data


@app.get("/api/admin/users/{user_id}/plan-prices")
def admin_get_user_plan_prices(user_id: str, admin_username: str = Depends(require_admin)):
    data = db.get_user_plan_overrides(user_id)
    if not data:
        raise HTTPException(status_code=404, detail="User not found")
    return data


@app.put("/api/admin/users/{user_id}/plan-prices")
def admin_set_user_plan_prices(
    user_id: str,
    body: PlanOverridesBody,
    admin_username: str = Depends(require_admin),
):
    try:
        data = db.set_user_plan_overrides(
            user_id,
            [item.model_dump() for item in body.overrides],
            updated_by=admin_username,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not data:
        raise HTTPException(status_code=404, detail="User not found")
    return data


class CreateOrderBody(BaseModel):
    user_id: str
    plan_code: str


class VerifyPaymentBody(BaseModel):
    user_id: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class AdminGrantPremiumBody(BaseModel):
    plan_code: Optional[str] = "1y"
    days: Optional[int] = None


@app.get("/api/payments/razorpay/config")
def razorpay_config():
    return {
        "enabled": razorpay_configured(),
        "key_id": razorpay_key_id() if razorpay_configured() else None,
    }


@app.get("/api/users/entitlement")
def user_entitlement(user_id: str = Query(...)):
    return db.get_user_entitlement(user_id)


@app.post("/api/payments/razorpay/create-order")
def create_razorpay_order(body: CreateOrderBody):
    if not razorpay_configured():
        raise HTTPException(
            status_code=503,
            detail="Razorpay not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET.",
        )
    plan = db.get_effective_plan_price(body.user_id, body.plan_code)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    amount_inr = int(plan["price_inr"])
    amount_paise = amount_inr * 100
    receipt = f"p{plan['code']}-{str(plan['user_id'])[:8]}"
    try:
        order = rz_create_order(
            amount_paise,
            receipt=receipt,
            notes={
                "user_id": str(plan["user_id"]),
                "plan_code": plan["code"],
                "email": body.user_id,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    try:
        db.create_payment_order_record(
            plan["user_id"],
            plan,
            amount_inr,
            order["id"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save payment order: {e}")
    return {
        "key_id": razorpay_key_id(),
        "order_id": order["id"],
        "amount": order["amount"],
        "currency": order.get("currency", "INR"),
        "plan_code": plan["code"],
        "plan_name": plan["name"],
        "amount_inr": amount_inr,
        "prefill": {"email": body.user_id if "@" in body.user_id else ""},
    }


@app.post("/api/payments/razorpay/verify")
def verify_razorpay_payment(body: VerifyPaymentBody):
    if not verify_payment_signature(
        body.razorpay_order_id,
        body.razorpay_payment_id,
        body.razorpay_signature,
    ):
        raise HTTPException(status_code=400, detail="Invalid payment signature")
    entitlement = db.mark_order_paid_and_grant_premium(
        body.razorpay_order_id,
        razorpay_payment_id=body.razorpay_payment_id,
        source="razorpay",
    )
    if not entitlement:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"ok": True, "entitlement": entitlement}


@app.post("/api/payments/razorpay/webhook")
async def razorpay_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    if not verify_webhook_signature(body, signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event = payload.get("event")
    if event in ("payment.captured", "order.paid"):
        payment = (payload.get("payload") or {}).get("payment", {}).get("entity") or {}
        order_id = payment.get("order_id")
        payment_id = payment.get("id")
        if not order_id and event == "order.paid":
            order = (payload.get("payload") or {}).get("order", {}).get("entity") or {}
            order_id = order.get("id")
        if order_id:
            db.mark_order_paid_and_grant_premium(
                order_id,
                razorpay_payment_id=payment_id,
                source="razorpay_webhook",
            )
    return {"ok": True}


@app.get("/api/admin/users/{user_id}/entitlement")
def admin_user_entitlement(user_id: str, admin_username: str = Depends(require_admin)):
    return db.get_user_entitlement(user_id)


@app.post("/api/admin/users/{user_id}/grant-premium")
def admin_grant_premium(
    user_id: str,
    body: AdminGrantPremiumBody,
    admin_username: str = Depends(require_admin),
):
    try:
        data = db.admin_grant_premium(
            user_id,
            plan_code=body.plan_code or "1y",
            days=body.days,
            updated_by=admin_username,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not data:
        raise HTTPException(status_code=404, detail="User not found")
    return data


@app.post("/api/admin/users/{user_id}/revoke-premium")
def admin_revoke_premium(user_id: str, admin_username: str = Depends(require_admin)):
    data = db.admin_revoke_premium(user_id)
    if not data:
        raise HTTPException(status_code=404, detail="User not found")
    return data


@app.get("/api/admin/topics")
def admin_topic_analytics(
    start: Optional[str] = None,
    end: Optional[str] = None,
    admin_username: str = Depends(require_admin),
):
    start, end = _default_dates(start, end)
    return db.get_topic_analytics(start, end)

@app.get("/api/admin/questions")
def admin_question_analytics(
    start: Optional[str] = None,
    end: Optional[str] = None,
    topic_id: Optional[int] = None,
    sort_by: str = "attempts",
    page: int = 1,
    page_size: int = 25,
    admin_username: str = Depends(require_admin),
):
    start, end = _default_dates(start, end)
    return db.get_question_analytics(start, end, topic_id=topic_id, sort_by=sort_by, page=page, page_size=page_size)


@app.get("/api/admin/leaderboard")
def admin_leaderboard(
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = 20,
    admin_username: str = Depends(require_admin),
):
    start, end = _default_dates(start, end)
    return db.get_leaderboard(start, end, limit=min(max(limit, 1), 100))


# =============================================================================
# ADMIN PANEL: SPA (built files in admin-panel/dist)
# =============================================================================

ADMIN_DIST = os.path.join(ROOT_DIR, "admin-panel", "dist")

@app.get("/admin")
@app.get("/admin/")
def admin_spa_root():
    index = os.path.join(ADMIN_DIST, "index.html")
    if not os.path.isfile(index):
        raise HTTPException(status_code=404, detail="Admin panel not built yet")
    return FileResponse(index)

@app.get("/admin/{full_path:path}")
def admin_spa_assets(full_path: str):
    # Serve real static assets when they exist; otherwise SPA fallback for client routes
    candidate = os.path.join(ADMIN_DIST, full_path)
    if os.path.isfile(candidate):
        return FileResponse(candidate)
    index = os.path.join(ADMIN_DIST, "index.html")
    if not os.path.isfile(index):
        raise HTTPException(status_code=404, detail="Admin panel not built yet")
    return FileResponse(index)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8085)
