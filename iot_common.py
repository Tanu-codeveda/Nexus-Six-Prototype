from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

import models


CATEGORY_DEPARTMENT = {
    "Waste Management": "Municipal Solid Waste Dept",
    "Electricity and Power": "Electricity Board",
    "Roads and Potholes": "Public Works Department (PWD)",
    "Sanitation": "Health and Sanitation Dept",
}


def create_iot_complaint(
    db: Session,
    *,
    category: str,
    severity: str,
    description: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    media_url: Optional[str] = None,
    confidence: Optional[float] = None,
    source: str = "iot_detected",
    department: Optional[str] = None,
) -> models.Complaint:
    """Create a Complaint using the existing CivicPulse Complaint model."""
    if source not in {"citizen", "iot_predicted", "iot_detected"}:
        raise ValueError(f"Unsupported complaint source: {source}")

    now = datetime.utcnow()
    complaint = models.Complaint(
        latitude=latitude,
        longitude=longitude,
        media_url=media_url,
        description=description,
        ai_category=category,
        ai_severity=severity,
        ai_confidence_score=confidence,
        status="Pending",
        assigned_department=department or CATEGORY_DEPARTMENT.get(category, "City Municipal Corporation"),
        created_at=now,
        updated_at=now,
        verification_count=0,
    )
    db.add(complaint)
    db.flush()
    return complaint
