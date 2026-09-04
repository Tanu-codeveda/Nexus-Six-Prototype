import os
import logging
import tempfile
import urllib.request
from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from database import Base, engine, get_db
import models
import schemas

from ai_helpers import map_category_and_department, process_civic_vision
from nlp_processor import NLPProcessor

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

nlp_processor = None
try:
    nlp_processor = NLPProcessor()
except Exception as e:
    logger.exception("Could not load NLPProcessor:")

def process_audio_url(url: str) -> str:
    """Helper to download audio and transcribe."""
    if not nlp_processor:
        return ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            temp_path = temp_audio.name
        urllib.request.urlretrieve(url, temp_path)
        text = nlp_processor.transcribe_audio(temp_path)
        os.remove(temp_path)
        return text
    except Exception as e:
        logger.exception(f"Error processing audio URL: {e}")
        return ""

# ---------------------------------------------------------
# Health check
# ---------------------------------------------------------

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "CivicPulse AI Core API"}

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
        Vision & Audio AI
            ↓
        Category + department mapping
            ↓
        SQLite
    """

    # ---------------------------------------------
    # AI processing (Vision & NLP)
    # ---------------------------------------------
    ai_vision_res = {}
    transcribed_text = ""
    is_audio = False

    if payload.media_url:
        is_audio = any(payload.media_url.lower().endswith(ext) for ext in [".wav", ".mp3", ".m4a", ".ogg"])
        
        if is_audio:
            if os.path.exists(payload.media_url) and nlp_processor:
                transcribed_text = nlp_processor.transcribe_audio(payload.media_url)
            else:
                transcribed_text = process_audio_url(payload.media_url)
        else:
            ai_vision_res = process_civic_vision(payload.media_url)

    detected_issue = ai_vision_res.get(
        "detected_issue",
        "General",
    )

    vision_severity = ai_vision_res.get(
        "ai_severity",
        "Low",
    )

    # Combine text from description and audio transcription
    combined_text = (payload.description or "")
    if transcribed_text:
        combined_text += f" {transcribed_text}"
    combined_text = combined_text.strip()

    # ---------------------------------------------
    # Category + department mapping
    # ---------------------------------------------
    if nlp_processor:
        nlp_res = nlp_processor.extract_category_severity(combined_text, detected_issue)
        ai_category = nlp_res["category"]
        
        # Determine final severity. Use NLP if there's text, otherwise vision
        if combined_text:
            ai_severity = nlp_res["severity"]
        else:
            ai_severity = vision_severity
            
        assigned_department = nlp_res["department"]
    else:
        # Fallback to older keyword mapping if NLP failed
        ai_category, assigned_department = map_category_and_department(
            detected_issue,
            combined_text,
        )
        ai_severity = vision_severity

    # ---------------------------------------------
    # Create database record
    # ---------------------------------------------
    complaint = models.Complaint(
        latitude=payload.latitude,
        longitude=payload.longitude,
        media_url=payload.media_url,
        description=combined_text or payload.description,
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


# Serve Frontend
app.mount("/", StaticFiles(directory=".", html=True), name="static")
