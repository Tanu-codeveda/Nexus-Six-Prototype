from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from database import engine, Base, get_db
import models
import schemas
from ai_helpers import process_civic_vision, map_category_and_department

Base.metadata.create_all(bind=engine)

app = FastAPI(title="CivicPulse AI Core API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/complaints", response_model=schemas.ComplaintResponse, status_code=201)
def create_complaint(payload: schemas.ComplaintCreate, db: Session = Depends(get_db)):
    ai_vision_res = process_civic_vision(payload.media_url) if payload.media_url else {}
    detected_issue = ai_vision_res.get("detected_issue", "General")
    ai_severity = ai_vision_res.get("ai_severity", "Low")

    ai_category, assigned_dept = map_category_and_department(detected_issue, payload.description or "")

    complaint = models.Complaint(
        latitude=payload.latitude,
        longitude=payload.longitude,
        media_url=payload.media_url,
        description=payload.description,
        ai_category=ai_category,
        ai_severity=ai_severity,
        status="Pending",
        assigned_department=assigned_dept
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    return complaint


@app.get("/api/complaints", response_model=List[schemas.ComplaintResponse])
def get_all_complaints(db: Session = Depends(get_db)):
    return db.query(models.Complaint).order_by(models.Complaint.created_at.desc()).all()


@app.get("/api/complaints/{complaint_id}", response_model=schemas.ComplaintResponse)
def get_complaint_by_id(complaint_id: str, db: Session = Depends(get_db)):
    """GET single complaint details by ID."""
    complaint = db.query(models.Complaint).filter(models.Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint


@app.patch("/api/complaints/{complaint_id}", response_model=schemas.ComplaintResponse)
def update_complaint(
    complaint_id: str,
    update_data: schemas.ComplaintUpdate,
    db: Session = Depends(get_db)
):
    complaint = db.query(models.Complaint).filter(models.Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    if update_data.status is not None:
        complaint.status = update_data.status
    if update_data.assigned_department is not None:
        complaint.assigned_department = update_data.assigned_department

    db.commit()
    db.refresh(complaint)
    return complaint