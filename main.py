import logging
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import Base, engine, get_db
import models
import schemas
from ai_helpers import map_category_and_department, process_civic_vision


# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("civicpulse.api")


# ---------------------------------------------------------
# Database
# ---------------------------------------------------------

Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------
# FastAPI
# ---------------------------------------------------------

app = FastAPI(
    title="CivicPulse AI Core API",
    version="1.0.0",
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Create complaint
# ---------------------------------------------------------

@app.post(
    "/api/complaints",
    response_model=schemas.ComplaintResponse,
    status_code=201,
)
def create_complaint(
    payload: schemas.ComplaintCreate,
    db: Session = Depends(get_db),
):
    """
    Create a civic complaint.

    Current processing pipeline:

        Citizen data
            ↓
        Vision AI
            ↓
        Category + department mapping
            ↓
        SQLite
    """

    # ---------------------------------------------
    # Vision processing
    # ---------------------------------------------

    ai_vision_res = {}

    if payload.media_url:
        ai_vision_res = process_civic_vision(payload.media_url)

    detected_issue = ai_vision_res.get(
        "detected_issue",
        "General",
    )

    ai_severity = ai_vision_res.get(
        "ai_severity",
        "Low",
    )

    # ---------------------------------------------
    # Category + department
    # ---------------------------------------------

    ai_category, assigned_department = map_category_and_department(
        detected_issue,
        payload.description or "",
    )

    # ---------------------------------------------
    # Create database record
    # ---------------------------------------------

    complaint = models.Complaint(
        latitude=payload.latitude,
        longitude=payload.longitude,
        media_url=payload.media_url,
        description=payload.description,
        ai_category=ai_category,
        ai_severity=ai_severity,
        status=schemas.ComplaintStatus.PENDING.value,
        assigned_department=assigned_department,
    )

    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    logger.info(
        "Complaint created: id=%s category=%s department=%s severity=%s",
        complaint.id,
        complaint.ai_category,
        complaint.assigned_department,
        complaint.ai_severity,
    )

    return complaint


# ---------------------------------------------------------
# Get all complaints
# ---------------------------------------------------------

@app.get(
    "/api/complaints",
    response_model=List[schemas.ComplaintResponse],
)
def get_all_complaints(
    db: Session = Depends(get_db),
):
    return (
        db.query(models.Complaint)
        .order_by(models.Complaint.created_at.desc())
        .all()
    )


# ---------------------------------------------------------
# Get one complaint
# ---------------------------------------------------------

@app.get(
    "/api/complaints/{complaint_id}",
    response_model=schemas.ComplaintResponse,
)
def get_complaint_by_id(
    complaint_id: str,
    db: Session = Depends(get_db),
):
    complaint = (
        db.query(models.Complaint)
        .filter(models.Complaint.id == complaint_id)
        .first()
    )

    if not complaint:
        raise HTTPException(
            status_code=404,
            detail="Complaint not found",
        )

    return complaint


# ---------------------------------------------------------
# Update complaint
# ---------------------------------------------------------

@app.patch(
    "/api/complaints/{complaint_id}",
    response_model=schemas.ComplaintResponse,
)
def update_complaint(
    complaint_id: str,
    update_data: schemas.ComplaintUpdate,
    db: Session = Depends(get_db),
):
    complaint = (
        db.query(models.Complaint)
        .filter(models.Complaint.id == complaint_id)
        .first()
    )

    if not complaint:
        raise HTTPException(
            status_code=404,
            detail="Complaint not found",
        )

    if update_data.status is not None:
        complaint.status = update_data.status.value

    if update_data.assigned_department is not None:
        complaint.assigned_department = (
            update_data.assigned_department.value
        )

    db.commit()
    db.refresh(complaint)

    logger.info(
        "Complaint updated: id=%s status=%s department=%s",
        complaint.id,
        complaint.status,
        complaint.assigned_department,
    )

    return complaint