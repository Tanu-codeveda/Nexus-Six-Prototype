import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime
from database import Base


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    media_url = Column(String, nullable=True)
    description = Column(String, nullable=True)
    ai_category = Column(String, default="General Maintenance")
    ai_severity = Column(String, default="Low")
    status = Column(String, default="Pending")
    assigned_department = Column(String, default="Unassigned")
    created_at = Column(DateTime, default=datetime.utcnow)