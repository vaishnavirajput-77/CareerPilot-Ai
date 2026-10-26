from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    applications = relationship("Application", back_populates="owner", cascade="all, delete-orphan")
    roadmaps = relationship("RoadmapSnapshot", back_populates="owner", cascade="all, delete-orphan")
    interviews = relationship("InterviewSession", back_populates="owner", cascade="all, delete-orphan")
    resumes = relationship("ResumeAnalysis", back_populates="owner", cascade="all, delete-orphan")

class Application(Base):
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    company = Column(String(160), nullable=False)
    role = Column(String(160), nullable=False)
    status = Column(String(40), nullable=False, default="Saved")
    source_url = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    owner = relationship("User", back_populates="applications")

class RoadmapSnapshot(Base):
    __tablename__ = "roadmap_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    target_role = Column(String(160), nullable=False)
    current_skills = Column(Text, nullable=False)        # comma-separated
    weeks = Column(Integer, nullable=False, default=8)
    result_json = Column(JSON, nullable=False)           # full build_roadmap() output
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    owner = relationship("User", back_populates="roadmaps")

class InterviewSession(Base):
    __tablename__ = "interview_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    role = Column(String(120), nullable=False)
    category = Column(String(40), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    practice_score = Column(Integer, nullable=False)
    rubric_json = Column(JSON, nullable=False)
    suggestions_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    owner = relationship("User", back_populates="interviews")

class ResumeAnalysis(Base):
    __tablename__ = "resume_analyses"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    filename = Column(String(255), nullable=False)
    extracted_text_preview = Column(Text, nullable=False)
    character_count = Column(Integer, nullable=False, default=0)
    skill_count = Column(Integer, nullable=False, default=0)
    skills = Column(JSON, nullable=False)
    sections_detected = Column(JSON, nullable=False)
    suggestions = Column(JSON, nullable=False)
    notice = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    owner = relationship("User", back_populates="resumes")


