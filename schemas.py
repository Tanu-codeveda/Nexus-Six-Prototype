from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ComplaintCreate(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    media_url: Optional[str] = None 
    description: Optional[str] = None


class ComplaintUpdate(BaseModel):
    status: Optional[str] = None
    assigned_department: Optional[str] = None


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