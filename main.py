import base64
import binascii
import logging
import os
import tempfile
import urllib.request
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from database import Base, engine, get_db
import models
import schemas
from ai_helpers import map_category_and_department, process_civic_vision
from nlp_processor import NLPProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("civicpulse.api")

BASE_DIR = Path(__file__).resolve().parent

# Create new databases, then migrate older SQLite demo databases in place.
Base.metadata.create_all(bind=engine)


def ensure_schema_columns() -> None:
    inspector = inspect(engine)
    existing = {column["name"] for column in inspector.get_columns("complaints")}
    additions = {
        "voice_transcript": "TEXT",
        "ai_confidence_score": "FLOAT",
        "acknowledged_at": "DATETIME",
        "in_progress_at": "DATETIME",
        "resolved_at": "DATETIME",
        "updated_at": "DATETIME",
        "verification_count": "INTEGER DEFAULT 0",
        "last_verified_at": "DATETIME",
        "estimated_resolution_hours": "INTEGER",
        "probable_root_cause": "TEXT",
    }
    with engine.begin() as connection:
        for name, sql_type in additions.items():
            if name not in existing:
                connection.execute(text(f"ALTER TABLE complaints ADD COLUMN {name} {sql_type}"))


ensure_schema_columns()

app = FastAPI(title="CivicPulse AI Core API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

nlp_processor = None
try:
    nlp_processor = NLPProcessor()
except Exception:
    logger.exception("Could not load NLPProcessor; fallback classification will be used.")


def _combine_text(description: str | None, voice_transcript: str | None) -> str:
    parts = [part.strip() for part in (description, voice_transcript) if part and part.strip()]
    return " ".join(parts)


def _severity_rank(value: str) -> int:
    return {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}.get(value, 0)


def decision_support(category: str, severity: str, description: str | None) -> tuple[int, str]:
    """Lightweight rule-based estimates for prototype decision support."""
    base_hours = {"Critical": 24, "High": 48, "Medium": 96, "Low": 168}.get(severity, 120)
    category_adjustment = {
        "Traffic Issues": -6,
        "Electricity and Power": -8,
        "Water Supply": -4,
        "Roads and Potholes": 0,
        "Waste Management": 8,
        "Sanitation": 10,
        "Public Safety": -10,
    }.get(category, 12)
    hours = max(12, base_hours + category_adjustment)
    text = (description or "").lower()
    root = "Routine municipal maintenance"
    if any(k in text for k in ["rain", "rainwater", "waterlogging", "flood"]):
        root = "Weather-related drainage or surface deterioration"
    elif any(k in text for k in ["leak", "pipeline", "pipe burst", "water supply"]):
        root = "Water infrastructure fault"
    elif any(k in text for k in ["garbage", "waste", "dump", "litter"]):
        root = "Waste collection or disposal issue"
    elif any(k in text for k in ["light", "streetlight", "power", "electric"]):
        root = "Electrical infrastructure fault"
    elif any(k in text for k in ["pothole", "road", "crack", "pavement"]):
        root = "Road-surface deterioration"
    elif any(k in text for k in ["traffic", "signal", "congestion", "parking"]):
        root = "Traffic management or signalling issue"
    elif any(k in text for k in ["accident", "unsafe", "danger", "crime"]):
        root = "Public-safety condition requiring assessment"
    return hours, root

def analyze_complaint_inputs(
    description: str | None,
    voice_transcript: str | None,
    media_url: str | None,
) -> dict:
    combined_text = _combine_text(description, voice_transcript)

    vision_result = {}
    if media_url:
        vision_result = process_civic_vision(media_url)

    detected_issue = vision_result.get("detected_issue", "General")
    vision_severity = vision_result.get("ai_severity", "Low")
    vision_confidence = float(vision_result.get("confidence_score", 0.0) or 0.0)

    if nlp_processor:
        nlp_result = nlp_processor.extract_category_severity(
            combined_text,
            detected_issue,
        )
        ai_category = nlp_result["category"]
        nlp_severity = nlp_result["severity"]
        ai_severity = max(
            (vision_severity, nlp_severity),
            key=_severity_rank,
        )
        # A result is only presented as highly confident when either vision or
        # text classification actually produced a strong score.
        ai_confidence = max(
            vision_confidence,
            float(nlp_result.get("category_confidence", 0.0) or 0.0),
            float(nlp_result.get("severity_confidence", 0.0) or 0.0),
        )
        assigned_department = nlp_result["department"]
        extracted_location = nlp_result.get("extracted_location")
    else:
        ai_category, assigned_department = map_category_and_department(
            detected_issue,
            combined_text,
        )
        ai_severity = vision_severity
        ai_confidence = vision_confidence
        extracted_location = None

    # If text did not describe the issue but the image did, retain the vision
    # category instead of replacing it with a generic NLP result.
    if detected_issue not in {"General", "none", ""} and not combined_text:
        ai_category, assigned_department = map_category_and_department(
            detected_issue,
            "",
        )

    estimated_hours, root_cause = decision_support(ai_category, ai_severity, combined_text)
    return {
        "detected_issue": detected_issue,
        "ai_category": ai_category,
        "ai_severity": ai_severity,
        "ai_confidence_score": round(min(max(ai_confidence, 0.0), 1.0), 2),
        "assigned_department": assigned_department,
        "extracted_location": extracted_location,
        "estimated_resolution_hours": estimated_hours,
        "probable_root_cause": root_cause,
    }


def process_audio_url(url: str) -> str:
    if not nlp_processor:
        return ""
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            temp_path = temp_audio.name
        urllib.request.urlretrieve(url, temp_path)
        return nlp_processor.transcribe_audio(temp_path)
    except Exception:
        logger.exception("Error processing audio URL")
        return ""
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@app.post("/api/transcribe-audio")
def transcribe_audio(payload: dict):
    audio_data_url = payload.get("audio_data_url")
    if not isinstance(audio_data_url, str) or not audio_data_url.startswith("data:audio/"):
        raise HTTPException(422, "audio_data_url must be a valid audio data URL")
    if not nlp_processor:
        raise HTTPException(503, "NLP processor is unavailable")

    temp_path = None
    try:
        header, encoded = audio_data_url.split(",", 1)
        mime_type = header[5:].split(";", 1)[0].lower()
        extension = {
            "audio/webm": ".webm",
            "audio/ogg": ".ogg",
            "audio/mp4": ".mp4",
            "audio/m4a": ".m4a",
            "audio/wav": ".wav",
            "audio/x-wav": ".wav",
        }.get(mime_type, ".webm")
        audio_bytes = base64.b64decode(encoded, validate=True)
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_audio:
            temp_path = temp_audio.name
            temp_audio.write(audio_bytes)

        text_value = nlp_processor.transcribe_audio(temp_path)
        if not text_value:
            raise HTTPException(500, "Audio transcription returned no text")
        return {"text": text_value}
    except HTTPException:
        raise
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(422, "Invalid audio data URL") from exc
    except Exception as exc:
        logger.exception("Audio transcription failed")
        raise HTTPException(500, "Audio transcription failed") from exc
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "CivicPulse AI Core API"}


@app.post("/api/analyze-complaint", response_model=schemas.ComplaintAnalysisResponse)
def analyze_complaint(payload: schemas.ComplaintCreate):
    """Run the same AI pipeline as creation, without writing a record."""
    try:
        return analyze_complaint_inputs(
            payload.description,
            payload.voice_transcript,
            payload.media_url,
        )
    except Exception as exc:
        logger.exception("Complaint analysis failed")
        raise HTTPException(500, "Complaint analysis failed") from exc


@app.post("/api/complaints", response_model=schemas.ComplaintResponse, status_code=201)
def create_complaint(payload: schemas.ComplaintCreate, db: Session = Depends(get_db)):
    result = analyze_complaint_inputs(
        payload.description,
        payload.voice_transcript,
        payload.media_url,
    )
    complaint = models.Complaint(
        latitude=payload.latitude,
        longitude=payload.longitude,
        media_url=payload.media_url,
        description=payload.description,
        voice_transcript=payload.voice_transcript,
        ai_category=result["ai_category"],
        ai_severity=result["ai_severity"],
        ai_confidence_score=result["ai_confidence_score"],
        status=schemas.ComplaintStatus.PENDING.value,
        assigned_department=result["assigned_department"],
        updated_at=datetime.utcnow(),
        verification_count=0,
        estimated_resolution_hours=result.get("estimated_resolution_hours"),
        probable_root_cause=result.get("probable_root_cause"),
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    logger.info(
        "Complaint created: id=%s category=%s department=%s severity=%s",
        complaint.id, complaint.ai_category, complaint.assigned_department, complaint.ai_severity,
    )
    return complaint


@app.get("/api/complaints", response_model=list[schemas.ComplaintResponse])
def get_all_complaints(db: Session = Depends(get_db)):
    return db.query(models.Complaint).order_by(models.Complaint.created_at.desc()).all()


@app.get("/api/complaints/{complaint_id}", response_model=schemas.ComplaintResponse)
def get_complaint_by_id(complaint_id: str, db: Session = Depends(get_db)):
    complaint = db.query(models.Complaint).filter(models.Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(404, "Complaint not found")
    return complaint


@app.post(
    "/api/complaints/{complaint_id}/verify",
    response_model=schemas.ComplaintVerificationResponse,
)
def verify_complaint(complaint_id: str, db: Session = Depends(get_db)):
    """Record one community confirmation for a complaint."""
    try:
        complaint = db.query(models.Complaint).filter(models.Complaint.id == complaint_id).first()
        if not complaint:
            raise HTTPException(404, "Complaint not found")
        complaint.verification_count = int(complaint.verification_count or 0) + 1
        complaint.last_verified_at = datetime.utcnow()
        complaint.updated_at = complaint.last_verified_at
        db.commit()
        db.refresh(complaint)
        return {
            "complaint_id": complaint.id,
            "verification_count": complaint.verification_count,
            "last_verified_at": complaint.last_verified_at,
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Complaint verification failed for %s", complaint_id)
        raise HTTPException(500, f"Could not verify complaint: {exc}") from exc


@app.patch("/api/complaints/{complaint_id}", response_model=schemas.ComplaintResponse)
def update_complaint(
    complaint_id: str,
    update_data: schemas.ComplaintUpdate,
    db: Session = Depends(get_db),
):
    """Atomically update workflow metadata and record UTC audit timestamps."""
    try:
        ensure_schema_columns()
        complaint = db.query(models.Complaint).filter(models.Complaint.id == complaint_id).first()
        if not complaint:
            raise HTTPException(404, "Complaint not found")

        now = datetime.utcnow()
        changed = False

        if update_data.status is not None:
            new_status = update_data.status.value
            if complaint.status != new_status:
                complaint.status = new_status
                changed = True
                if new_status == schemas.ComplaintStatus.ACKNOWLEDGED.value and complaint.acknowledged_at is None:
                    complaint.acknowledged_at = now
                elif new_status == schemas.ComplaintStatus.IN_PROGRESS.value and complaint.in_progress_at is None:
                    complaint.in_progress_at = now
                elif new_status == schemas.ComplaintStatus.RESOLVED.value and complaint.resolved_at is None:
                    complaint.resolved_at = now

        if update_data.assigned_department is not None:
            new_dept = update_data.assigned_department.value
            if complaint.assigned_department != new_dept:
                complaint.assigned_department = new_dept
                changed = True

        if changed:
            complaint.updated_at = now

        db.commit()
        db.refresh(complaint)
        logger.info(
            "Complaint updated: id=%s status=%s department=%s updated_at=%s",
            complaint.id, complaint.status, complaint.assigned_department, complaint.updated_at,
        )
        return complaint
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Complaint update failed for %s", complaint_id)
        raise HTTPException(500, f"Could not update complaint: {exc}") from exc


# API routes are registered before the static root so /api/* remains reachable.
app.mount("/", StaticFiles(directory=str(BASE_DIR), html=True), name="static")
