import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from database import Base


class Complaint(Base):
    __tablename__ = "complaints"

    # IoT / SLA integration fields. Existing demo databases are upgraded
    # additively by main.py at startup.
    source = Column(String, default="citizen", nullable=False)
    escalation_level = Column(Integer, default=1, nullable=False)
    current_assignee = Column(String, default="Level 1 Field Officer")
    sla_deadline = Column(DateTime, nullable=True)

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    media_url = Column(String, nullable=True)
    resolution_media_url = Column(String, nullable=True)
    description = Column(String, nullable=True)
    voice_transcript = Column(String, nullable=True)
    ai_category = Column(String, default="General Maintenance")
    ai_severity = Column(String, default="Low")
    ai_confidence_score = Column(Float, nullable=True)
    status = Column(String, default="Pending")
    assigned_department = Column(String, default="Unassigned")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    acknowledged_at = Column(DateTime, nullable=True)
    in_progress_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    verification_count = Column(Integer, default=0, nullable=False)
    last_verified_at = Column(DateTime, nullable=True)
    estimated_resolution_hours = Column(Integer, nullable=True)
    probable_root_cause = Column(String, nullable=True)

    is_escalated = Column(Integer, default=0, nullable=False)
    delay_reason = Column(String, nullable=True)
    close_confirmed_at = Column(DateTime, nullable=True)

    # JSON array stored as TEXT so the SQLite demo database remains simple.
    progress_updates = Column(Text, nullable=True, default="[]")


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
