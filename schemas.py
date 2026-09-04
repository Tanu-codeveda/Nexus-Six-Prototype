from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


# ---------------------------------------------------------
# Canonical CivicPulse values
# ---------------------------------------------------------

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


class ComplaintUpdate(BaseModel):
    status: Optional[ComplaintStatus] = None
    assigned_department: Optional[ComplaintDepartment] = None


class ComplaintResponse(BaseModel):
    id: str
    latitude: Optional[float]
    longitude: Optional[float]
    media_url: Optional[str]
    description: Optional[str]
    ai_category: str
    ai_severity: str
    status: str
    assigned_department: str
    created_at: Optional[datetime]

    class Config:
        orm_mode = True
        from_attributes = True