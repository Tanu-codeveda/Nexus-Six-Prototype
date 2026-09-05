from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class ComplaintStatus(str, Enum):
    PENDING = "Pending"
    ACKNOWLEDGED = "Acknowledged"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"


class ComplaintDepartment(str, Enum):
    UNASSIGNED = "Unassigned"
    PWD = "Public Works Department (PWD)"
    WATER = "Water and Sewage Board"
    ELECTRICITY = "Electricity Board"
    SOLID_WASTE = "Municipal Solid Waste Dept"
    POLICE = "Local Police"
    SANITATION = "Health and Sanitation Dept"
    TRAFFIC = "Traffic Police"
    MUNICIPAL = "City Municipal Corporation"


class ComplaintCreate(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    media_url: Optional[str] = None
    description: Optional[str] = None
    voice_transcript: Optional[str] = None


class ComplaintUpdate(BaseModel):
    status: Optional[ComplaintStatus] = None
    assigned_department: Optional[ComplaintDepartment] = None
    progress_message: Optional[str] = Field(default=None, max_length=500)


class ProgressUpdate(BaseModel):
    timestamp: str
    message: str
    kind: str = "system"


class ComplaintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    latitude: Optional[float]
    longitude: Optional[float]
    media_url: Optional[str]
    description: Optional[str]
    voice_transcript: Optional[str] = None
    ai_category: str
    ai_severity: str
    ai_confidence_score: Optional[float] = None
    status: str
    assigned_department: str
    created_at: Optional[datetime]
    acknowledged_at: Optional[datetime] = None
    in_progress_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    verification_count: int = 0
    last_verified_at: Optional[datetime] = None

    estimated_resolution_hours: Optional[int] = None
    probable_root_cause: Optional[str] = None
    root_cause_factors: list[str] = Field(default_factory=list)
    root_cause_confidence: Optional[float] = None
    recommended_action: Optional[str] = None
    prediction_basis: Optional[str] = None

    priority_score: int = 0
    priority_reason: str = ""
    nearby_report_count: int = 0
    duplicate_count: int = 0
    possible_duplicate_ids: list[str] = Field(default_factory=list)
    progress_updates: list[ProgressUpdate] = Field(default_factory=list)

    @field_serializer(
        "created_at",
        "acknowledged_at",
        "in_progress_at",
        "resolved_at",
        "updated_at",
        "last_verified_at",
        when_used="json",
    )
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()


class ComplaintVerificationResponse(BaseModel):
    complaint_id: str
    verification_count: int
    last_verified_at: datetime
    priority_score: int
    priority_reason: str
    nearby_report_count: int
    duplicate_count: int


class ComplaintAnalysisResponse(BaseModel):
    detected_issue: str
    ai_category: str
    ai_severity: str
    ai_confidence_score: Optional[float] = None
    assigned_department: str
    extracted_location: Optional[str] = None
    estimated_resolution_hours: Optional[int] = None
    probable_root_cause: Optional[str] = None
    root_cause_factors: list[str] = Field(default_factory=list)
    root_cause_confidence: Optional[float] = None
    recommended_action: Optional[str] = None
    prediction_basis: Optional[str] = None
