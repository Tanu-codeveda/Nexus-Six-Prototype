import os
import tempfile
import urllib.request
from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from database import engine, Base, get_db
import models
import schemas
from ai_helpers import process_civic_vision
from nlp_processor import NLPProcessor

Base.metadata.create_all(bind=engine)

app = FastAPI(title="CivicPulse AI Core API", version="1.0.0")

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
    print("Could not load NLPProcessor:", e)

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
        print(f"Error processing audio URL: {e}")
        return ""

@app.post("/api/complaints", response_model=schemas.ComplaintResponse, status_code=201)
def create_complaint(payload: schemas.ComplaintCreate, db: Session = Depends(get_db)):
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

    detected_issue = ai_vision_res.get("detected_issue", "General")
    vision_severity = ai_vision_res.get("ai_severity", "Low")

    # Combine text from description and audio transcription
    combined_text = (payload.description or "")
    if transcribed_text:
        combined_text += f" {transcribed_text}"
    combined_text = combined_text.strip()

    if nlp_processor:
        nlp_res = nlp_processor.extract_category_severity(combined_text, detected_issue)
        ai_category = nlp_res["category"]
        
        # Determine final severity. Use NLP if there's text, otherwise vision
        if combined_text:
            ai_severity = nlp_res["severity"]
        else:
            ai_severity = vision_severity
            
        assigned_dept = nlp_res["department"]
    else:
        # Fallback if NLPProcessor failed to load
        ai_category = "General Maintenance"
        ai_severity = vision_severity
        assigned_dept = "City Municipal Corporation"

    complaint = models.Complaint(
        latitude=payload.latitude,
        longitude=payload.longitude,
        media_url=payload.media_url,
        description=combined_text or payload.description,
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

# Serve Frontend
app.mount("/", StaticFiles(directory=".", html=True), name="static")
