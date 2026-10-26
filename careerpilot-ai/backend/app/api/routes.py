from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Application, RoadmapSnapshot, InterviewSession, User, ResumeAnalysis
from ..schemas import (
    MatchRequest,
    RoadmapRequest,
    EvaluateRequest,
    ApplicationCreate,
    ApplicationUpdate,
    UserRegister,
    UserLogin,
    UserOut,
    TokenResponse,
)
from ..services.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    get_optional_user,
)
from ..services.ml import extract_skills, match_texts, analyze_role_gap, build_roadmap
from ..services.resume import extract_resume_text
from ..services.interviews import get_questions, evaluate_answer

router = APIRouter(prefix="/api")

SAMPLE_JOBS = [
    {"id": "demo-1", "title": "Junior Data Analyst (Sample)", "company": "Demo Analytics Co.", "location": "Remote demo", "description": "Python SQL pandas data analysis communication dashboard", "source_url": None, "is_demo": True},
    {"id": "demo-2", "title": "Junior ML Engineer (Sample)", "company": "Demo AI Lab", "location": "Remote demo", "description": "Python machine learning scikit-learn numpy pandas REST API Docker SQL", "source_url": None, "is_demo": True},
    {"id": "demo-3", "title": "Frontend Developer Intern (Sample)", "company": "Demo Web Studio", "location": "Demo listing", "description": "HTML CSS JavaScript TypeScript React Next.js Git REST API", "source_url": None, "is_demo": True},
    {"id": "demo-4", "title": "Cybersecurity Analyst Intern (Sample)", "company": "Demo Security Lab", "location": "Demo listing", "description": "Cybersecurity Python communication Git security analysis", "source_url": None, "is_demo": True},
]

from ..config import ACCESS_TOKEN_EXPIRE_MINUTES, COOKIE_SECURE

# ── Authentication Endpoints ─────────────────────────────────────────────────────

def _set_auth_cookie(response: Response, token: str):
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="none" if COOKIE_SECURE else "lax",
        secure=COOKIE_SECURE,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )


@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, response: Response, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )
    hashed = hash_password(payload.password)
    user = User(
        email=payload.email,
        hashed_password=hashed,
        full_name=payload.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, {"email": user.email})
    _set_auth_cookie(response, token)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
    }


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: UserLogin, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        )

    token = create_access_token(user.id, {"email": user.email})
    _set_auth_cookie(response, token)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
    }


@router.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(
        key="access_token",
        httponly=True,
        samesite="none" if COOKIE_SECURE else "lax",
        secure=COOKIE_SECURE,
        path="/",
    )
    return {"status": "ok", "message": "Logged out successfully."}


@router.get("/auth/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
    }


# ── Public Job & ML Services ─────────────────────────────────────────────────────

@router.get("/jobs")
def list_jobs():
    return {"items": SAMPLE_JOBS, "notice": "These are synthetic sample listings, not live vacancies."}


@router.post("/analyze/resume")
async def analyze_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    content = await file.read()
    try:
        text = extract_resume_text(file.filename or "resume.txt", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    skills = extract_skills(text)
    sections = [s for s in ["education", "experience", "projects", "skills"] if s in text.lower()]
    suggestions = [
        "Use clear headings and quantify project outcomes where possible.",
        "Tailor the skills section to the role without adding skills you do not have.",
        "Review the extracted skills and correct any parsing mistakes.",
    ]
    notice = "Skill extraction is taxonomy-based and may miss context or synonyms. Review before using."

    analysis_record = ResumeAnalysis(
        user_id=current_user.id if current_user else None,
        filename=file.filename or "resume.txt",
        extracted_text_preview=text[:3000],
        character_count=len(text),
        skills=skills,
        skill_count=len(skills),
        sections_detected=sections,
        suggestions=suggestions,
        notice=notice,
    )
    db.add(analysis_record)
    db.commit()

    return {
        "id": analysis_record.id,
        "filename": file.filename,
        "extracted_text_preview": text[:3000],
        "character_count": len(text),
        "skills": skills,
        "skill_count": len(skills),
        "sections_detected": sections,
        "suggestions": suggestions,
        "notice": notice,
    }


@router.get("/analyze/resume/latest")
def get_latest_resume(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    query = db.query(ResumeAnalysis)
    if current_user:
        query = query.filter(ResumeAnalysis.user_id == current_user.id)
    else:
        query = query.filter(ResumeAnalysis.user_id.is_(None))
    item = query.order_by(ResumeAnalysis.created_at.desc()).first()
    if not item:
        return {"item": None}
    return {
        "item": {
            "id": item.id,
            "filename": item.filename,
            "extracted_text_preview": item.extracted_text_preview,
            "character_count": item.character_count,
            "skill_count": item.skill_count,
            "skills": item.skills,
            "sections_detected": item.sections_detected,
            "suggestions": item.suggestions,
            "notice": item.notice,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
    }


@router.post("/match")
def match_job(request: MatchRequest):
    result = match_texts(request.resume_text, request.job_description)
    if request.role:
        result["role_gap"] = analyze_role_gap(request.role, result["resume_skills"])
    return result


@router.post("/roadmap")
def roadmap(
    request: RoadmapRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    result = build_roadmap(request.target_role, request.current_skills, request.weeks)
    snapshot = RoadmapSnapshot(
        user_id=current_user.id if current_user else None,
        target_role=request.target_role,
        current_skills=", ".join(request.current_skills),
        weeks=request.weeks,
        result_json=result,
    )
    db.add(snapshot)
    db.commit()
    return result


@router.get("/roadmap/latest")
def get_latest_roadmap(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    query = db.query(RoadmapSnapshot)
    if current_user:
        query = query.filter(RoadmapSnapshot.user_id == current_user.id)
    else:
        query = query.filter(RoadmapSnapshot.user_id.is_(None))
    item = query.order_by(RoadmapSnapshot.created_at.desc()).first()
    if not item:
        return {"item": None}
    return {
        "item": {
            "id": item.id,
            "target_role": item.target_role,
            "current_skills": item.current_skills,
            "weeks": item.weeks,
            "result_json": item.result_json,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
    }


@router.get("/roadmap/history")
def roadmap_history(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    query = db.query(RoadmapSnapshot)
    if current_user:
        query = query.filter(RoadmapSnapshot.user_id == current_user.id)
    else:
        query = query.filter(RoadmapSnapshot.user_id.is_(None))

    items = query.order_by(RoadmapSnapshot.created_at.desc()).limit(min(limit, 100)).all()
    return {"items": [
        {
            "id": x.id,
            "target_role": x.target_role,
            "current_skills": x.current_skills,
            "weeks": x.weeks,
            "result_json": x.result_json,
            "user_id": x.user_id,
            "created_at": x.created_at.isoformat() if x.created_at else None,
        }
        for x in items
    ]}


@router.get("/interviews/questions")
def interview_questions(role: str = "Software Developer", category: str = "technical", limit: int = 5):
    if category.lower() not in {"technical", "hr", "behavioral"}:
        raise HTTPException(status_code=400, detail="Category must be technical, hr, or behavioral.")
    return {"items": get_questions(category, role, limit)}


@router.post("/interviews/evaluate")
def interview_evaluate(
    request: EvaluateRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    result = evaluate_answer(request.question, request.answer, request.role)
    session = InterviewSession(
        user_id=current_user.id if current_user else None,
        role=request.role,
        category="practice",
        question=request.question,
        answer=request.answer,
        practice_score=result["practice_score"],
        rubric_json=result["rubric"],
        suggestions_json=result["suggestions"],
    )
    db.add(session)
    db.commit()
    return result


@router.get("/interviews/latest")
def get_latest_interview(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    query = db.query(InterviewSession)
    if current_user:
        query = query.filter(InterviewSession.user_id == current_user.id)
    else:
        query = query.filter(InterviewSession.user_id.is_(None))
    item = query.order_by(InterviewSession.created_at.desc()).first()
    if not item:
        return {"item": None}
    return {
        "item": {
            "id": item.id,
            "role": item.role,
            "category": item.category,
            "question": item.question,
            "answer": item.answer,
            "practice_score": item.practice_score,
            "rubric_json": item.rubric_json,
            "suggestions_json": item.suggestions_json,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
    }


@router.get("/interviews/history")
def interview_history(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    query = db.query(InterviewSession)
    if current_user:
        query = query.filter(InterviewSession.user_id == current_user.id)
    else:
        query = query.filter(InterviewSession.user_id.is_(None))

    items = query.order_by(InterviewSession.created_at.desc()).limit(min(limit, 100)).all()
    return {"items": [
        {
            "id": x.id,
            "role": x.role,
            "category": x.category,
            "question": x.question[:200] + ("..." if len(x.question) > 200 else ""),
            "practice_score": x.practice_score,
            "rubric_json": x.rubric_json,
            "suggestions_json": x.suggestions_json,
            "user_id": x.user_id,
            "created_at": x.created_at.isoformat() if x.created_at else None,
        }
        for x in items
    ]}



# ── Protected Applications (User-Specific Data Ownership) ─────────────────────────

def _serialize_application(item: Application):
    return {
        "id": item.id,
        "company": item.company,
        "role": item.role,
        "status": item.status,
        "source_url": item.source_url,
        "notes": item.notes,
        "user_id": item.user_id,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


@router.get("/applications")
def list_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = (
        db.query(Application)
        .filter(Application.user_id == current_user.id)
        .order_by(Application.created_at.desc())
        .all()
    )
    return {"items": [_serialize_application(x) for x in items]}


@router.post("/applications", status_code=201)
def create_application(
    payload: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = payload.model_dump()
    data["status"] = data["status"].value
    item = Application(**data, user_id=current_user.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_application(item)


@router.patch("/applications/{application_id}")
def update_application(
    application_id: int,
    payload: ApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.get(Application, application_id)
    if not item or item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Application not found.")

    updates = payload.model_dump(exclude_unset=True)
    if "status" in updates and updates["status"] is not None:
        updates["status"] = updates["status"].value
    for key, value in updates.items():
        setattr(item, key, value)
    item.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return _serialize_application(item)


@router.delete("/applications/{application_id}", status_code=204)
def delete_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.get(Application, application_id)
    if not item or item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Application not found.")
    db.delete(item)
    db.commit()
    return None
