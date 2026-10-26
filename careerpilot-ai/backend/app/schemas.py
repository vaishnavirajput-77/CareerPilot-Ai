from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any
from enum import Enum

class ApplicationStatus(str, Enum):
    saved = "Saved"
    applied = "Applied"
    assessment = "Assessment"
    interview = "Interview"
    offer = "Offer"
    rejected = "Rejected"
    withdrawn = "Withdrawn"

class MatchRequest(BaseModel):
    resume_text: str = Field(min_length=10, max_length=50000)
    job_description: str = Field(min_length=10, max_length=20000)
    role: Optional[str] = None

class RoadmapRequest(BaseModel):
    target_role: str = Field(min_length=2, max_length=120)
    current_skills: List[str] = Field(default_factory=list)
    weeks: int = Field(default=8, ge=1, le=52)

class EvaluateRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    answer: str = Field(min_length=1, max_length=10000)
    role: str = Field(default="Software Developer", max_length=120)

class ApplicationCreate(BaseModel):
    company: str = Field(min_length=1, max_length=160)
    role: str = Field(min_length=1, max_length=160)
    status: ApplicationStatus = ApplicationStatus.saved
    source_url: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = Field(default=None, max_length=5000)

class ApplicationUpdate(BaseModel):
    company: Optional[str] = Field(default=None, min_length=1, max_length=160)
    role: Optional[str] = Field(default=None, min_length=1, max_length=160)
    status: Optional[ApplicationStatus] = None
    source_url: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = Field(default=None, max_length=5000)

# ── History schemas ─────────────────────────────────────────────────────────────
class RoadmapHistoryItem(BaseModel):
    id: int
    target_role: str
    current_skills: str
    weeks: int
    result_json: Any
    created_at: str

class InterviewHistoryItem(BaseModel):
    id: int
    role: str
    category: str
    question: str
    answer: str
    practice_score: int
    rubric_json: Any
    suggestions_json: Any
    created_at: str

# ── Auth schemas ───────────────────────────────────────────────────────────────
class UserRegister(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128, description="Password must be at least 8 characters")
    full_name: Optional[str] = Field(default=None, max_length=120)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v

class UserLogin(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()

class UserOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    created_at: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


