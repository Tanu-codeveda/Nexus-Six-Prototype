import base64
import binascii
import json
import logging
import os
import tempfile
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean
from typing import Iterable

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

# Create the table for a fresh install, then add any newer prototype columns to
# an existing SQLite database without requiring a destructive reset.
Base.metadata.create_all(bind=engine)


def ensure_schema_columns() -> None:
    inspector = inspect(engine)
    if not inspector.has_table("complaints"):
        return
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
        "progress_updates": "TEXT",
    }
    with engine.begin() as connection:
        for name, sql_type in additions.items():
            if name not in existing:
                connection.execute(text(f"ALTER TABLE complaints ADD COLUMN {name} {sql_type}"))


ensure_schema_columns()

app = FastAPI(title="CivicPulse AI Core API", version="1.2.0")

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


SEVERITY_BASE = {"Critical": 90, "High": 72, "Medium": 50, "Low": 28}
CATEGORY_BASE_HOURS = {
    "Traffic Issues": 44,
    "Electricity and Power": 52,
    "Water Supply": 60,
    "Roads and Potholes": 84,
    "Waste Management": 88,
    "Sanitation": 92,
    "Public Safety": 36,
    "General Maintenance": 120,
}
SEVERITY_MULTIPLIER = {"Critical": 0.45, "High": 0.72, "Medium": 1.0, "Low": 1.55}
STATUS_MESSAGES = {
    "Acknowledged": "Your report has been acknowledged by municipal operations.",
    "In Progress": "The assigned department has started work on this issue.",
    "Resolved": "This issue has been marked resolved by municipal operations.",
}


def _combine_text(description: str | None, voice_transcript: str | None) -> str:
    parts = [part.strip() for part in (description, voice_transcript) if part and part.strip()]
    return " ".join(parts)


def _severity_rank(value: str) -> int:
    return {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}.get(value, 0)


def _severity_weight(value: str) -> float:
    return {"Low": 0.25, "Medium": 0.5, "High": 0.8, "Critical": 1.0}.get(value, 0.25)


def _token_set(text_value: str | None) -> set[str]:
    return {word for word in (text_value or "").lower().replace("/", " ").split() if len(word.strip(".,!?;:\"'()[]{}")) >= 4}


def haversine_km(a: models.Complaint, b: models.Complaint) -> float:
    from math import asin, cos, pi, sin, sqrt

    if a.latitude is None or a.longitude is None or b.latitude is None or b.longitude is None:
        return float("inf")
    radius = 6371.0
    lat1 = a.latitude * pi / 180
    lat2 = b.latitude * pi / 180
    d_lat = (b.latitude - a.latitude) * pi / 180
    d_lon = (b.longitude - a.longitude) * pi / 180
    x = sin(d_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(d_lon / 2) ** 2
    return 2 * radius * asin(sqrt(max(0.0, min(1.0, x))))


def find_duplicate_candidates(complaint: models.Complaint, all_complaints: Iterable[models.Complaint]) -> list[models.Complaint]:
    candidates: list[tuple[float, models.Complaint]] = []
    own_text = _combine_text(complaint.description, complaint.voice_transcript)
    own_words = _token_set(own_text)
    for other in all_complaints:
        if other.id == complaint.id:
            continue
        distance = haversine_km(complaint, other)
        if distance > 0.35:
            continue
        if complaint.ai_category and other.ai_category and complaint.ai_category != other.ai_category:
            continue
        other_words = _token_set(_combine_text(other.description, other.voice_transcript))
        union = len(own_words | other_words) or 1
        similarity = len(own_words & other_words) / union
        recent = False
        if complaint.created_at and other.created_at:
            recent = abs(complaint.created_at - other.created_at) <= timedelta(hours=24)
        if similarity >= 0.25 or (recent and len(own_words & other_words) >= 1):
            candidates.append((distance, other))
    candidates.sort(key=lambda item: item[0])
    return [item[1] for item in candidates[:5]]


def calculate_priority(complaint: models.Complaint, all_complaints: list[models.Complaint]) -> tuple[int, str, int, list[str]]:
    if complaint.status == schemas.ComplaintStatus.RESOLVED.value:
        return 0, "Resolved — no active operational priority.", 0, []

    nearby = [
        other for other in all_complaints
        if other.id != complaint.id and haversine_km(complaint, other) <= 0.65
    ]
    nearby_open = [other for other in nearby if other.status != schemas.ComplaintStatus.RESOLVED.value]
    duplicates = find_duplicate_candidates(complaint, all_complaints)

    score = SEVERITY_BASE.get(complaint.ai_severity, 28)
    reasons: list[str] = [f"{complaint.ai_severity or 'Low'} severity"]
    if nearby_open:
        score += min(15, len(nearby_open) * 3)
        reasons.append(f"{len(nearby_open)} nearby active reports")
    if duplicates:
        score += min(10, len(duplicates) * 4)
        reasons.append(f"{len(duplicates)} likely duplicate{'' if len(duplicates) == 1 else 's'}")
    confirmations = int(complaint.verification_count or 0)
    if confirmations:
        score += min(10, confirmations * 2)
        reasons.append(f"{confirmations} community confirmation{'' if confirmations == 1 else 's'}")

    if complaint.created_at:
        age_hours = max(0.0, (datetime.utcnow() - complaint.created_at).total_seconds() / 3600)
        if age_hours >= 48:
            score += 5
            reasons.append("open for 48+ hours")

    if complaint.ai_category == "Public Safety":
        score += 5
        reasons.append("public-safety category")

    return min(100, int(round(score))), " + ".join(reasons), len(nearby_open), [item.id for item in duplicates]


def predict_resolution_hours(complaint: models.Complaint, all_complaints: list[models.Complaint]) -> tuple[int, str]:
    category = complaint.ai_category or "General Maintenance"
    dept = complaint.assigned_department or "Unassigned"
    severity = complaint.ai_severity or "Low"

    history: list[float] = []
    for item in all_complaints:
        if item.id == complaint.id:
            continue
        if item.status != schemas.ComplaintStatus.RESOLVED.value:
            continue
        if item.ai_category != category or not item.created_at or not item.resolved_at:
            continue
        hours = (item.resolved_at - item.created_at).total_seconds() / 3600
        if 0 < hours <= 24 * 30:
            history.append(hours)

    open_same_dept = sum(
        1 for item in all_complaints
        if item.id != complaint.id
        and item.assigned_department == dept
        and item.status != schemas.ComplaintStatus.RESOLVED.value
    )

    if len(history) >= 3:
        category_baseline = mean(history)
        basis = f"historical average from {len(history)} resolved {category} reports"
    else:
        category_baseline = CATEGORY_BASE_HOURS.get(category, 120)
        basis = "prototype category/severity baseline"

    hours = category_baseline * SEVERITY_MULTIPLIER.get(severity, 1.0)
    workload_factor = 1 + min(0.25, open_same_dept / 20)
    hours *= workload_factor
    hours = max(6, min(24 * 14, round(hours)))
    basis += f" + current {dept} workload ({open_same_dept} open)"
    return int(hours), basis


def infer_root_cause(category: str, text_value: str, nearby_count: int) -> tuple[str, list[str], float, str]:
    text_lower = (text_value or "").lower()
    factors: list[str] = []

    if category == "Roads and Potholes":
        root = "Road-surface deterioration"
        if any(word in text_lower for word in ["rain", "rainwater", "waterlogging", "flood", "drain"]):
            root = "Drainage-related pavement deterioration"
            factors.extend(["standing water", "drainage pressure", "surface wear"])
        elif any(word in text_lower for word in ["traffic", "heavy vehicle", "truck", "bus"]):
            root = "Traffic-load driven pavement wear"
            factors.extend(["repeated traffic loading", "surface fatigue", "maintenance backlog"])
        else:
            factors.extend(["surface wear", "weather exposure", "maintenance cycle"])
        action = "Inspect the affected road section and verify drainage/surface condition before patching."
    elif category == "Water Supply":
        root = "Water-network fault or pressure loss"
        factors.extend(["pipe/network condition", "pressure variation"])
        if "leak" in text_lower or "burst" in text_lower:
            factors.append("visible leakage")
        action = "Inspect the local pipeline section, isolate the fault if needed, and verify pressure after repair."
    elif category == "Electricity and Power":
        root = "Electrical distribution or lighting fault"
        factors.extend(["fixture/pole condition", "power supply continuity"])
        if "streetlight" in text_lower or "light" in text_lower:
            factors.append("lighting fixture failure")
        action = "Dispatch an electrical inspection team to test the fixture, pole and local supply circuit."
    elif category == "Waste Management":
        root = "Collection-route or disposal-point overflow"
        factors.extend(["collection frequency", "bin capacity", "waste accumulation"])
        action = "Inspect the collection point, clear accumulated waste, and review pickup frequency."
    elif category == "Sanitation":
        root = "Blocked drainage or sanitation network"
        factors.extend(["drain/sewer blockage", "standing water", "maintenance frequency"])
        action = "Inspect the drain/sewer segment, clear blockage, and confirm free flow after cleaning."
    elif category == "Traffic Issues":
        root = "Traffic-management or signalling bottleneck"
        factors.extend(["signal timing", "vehicle volume", "roadside activity"])
        action = "Review the traffic-control point and adjust signalling, signage or enforcement as appropriate."
    elif category == "Public Safety":
        root = "Local public-safety condition requiring assessment"
        factors.extend(["visibility", "site conditions", "reported risk context"])
        action = "Route the report for on-site safety assessment and immediate mitigation where necessary."
    else:
        root = "Routine municipal maintenance condition"
        factors.extend(["reported site condition", "maintenance cycle"])
        action = "Inspect the reported location and assign the appropriate municipal maintenance action."

    if nearby_count >= 3:
        factors.append("recurring local complaint cluster")
        confidence = min(0.92, 0.70 + min(0.18, nearby_count * 0.03))
    else:
        confidence = 0.67 if len(factors) >= 2 else 0.58
    return root, list(dict.fromkeys(factors))[:4], round(confidence, 2), action


def _load_progress(value: str | None) -> list[dict]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (TypeError, json.JSONDecodeError):
        return []


def _utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.replace(microsecond=0).isoformat() + "Z"


def append_progress(complaint: models.Complaint, message: str, kind: str = "system") -> None:
    updates = _load_progress(complaint.progress_updates)
    updates.append({
        "timestamp": _utc_iso(datetime.utcnow()),
        "message": message.strip()[:500],
        "kind": kind,
    })
    complaint.progress_updates = json.dumps(updates[-20:], ensure_ascii=False)


def build_complaint_view(complaint: models.Complaint, all_complaints: list[models.Complaint]) -> dict:
    priority, reason, nearby_count, duplicate_ids = calculate_priority(complaint, all_complaints)
    estimated_hours, prediction_basis = predict_resolution_hours(complaint, all_complaints)
    root, factors, root_confidence, action = infer_root_cause(
        complaint.ai_category or "General Maintenance",
        _combine_text(complaint.description, complaint.voice_transcript),
        nearby_count,
    )
    updates = _load_progress(complaint.progress_updates)
    return {
        "id": complaint.id,
        "latitude": complaint.latitude,
        "longitude": complaint.longitude,
        "media_url": complaint.media_url,
        "description": complaint.description,
        "voice_transcript": complaint.voice_transcript,
        "ai_category": complaint.ai_category,
        "ai_severity": complaint.ai_severity,
        "ai_confidence_score": complaint.ai_confidence_score,
        "status": complaint.status,
        "assigned_department": complaint.assigned_department,
        "created_at": complaint.created_at,
        "acknowledged_at": complaint.acknowledged_at,
        "in_progress_at": complaint.in_progress_at,
        "resolved_at": complaint.resolved_at,
        "updated_at": complaint.updated_at,
        "verification_count": int(complaint.verification_count or 0),
        "last_verified_at": complaint.last_verified_at,
        "estimated_resolution_hours": estimated_hours,
        "probable_root_cause": root,
        "root_cause_factors": factors,
        "root_cause_confidence": root_confidence,
        "recommended_action": action,
        "prediction_basis": prediction_basis,
        "priority_score": priority,
        "priority_reason": reason,
        "nearby_report_count": nearby_count,
        "duplicate_count": len(duplicate_ids),
        "possible_duplicate_ids": duplicate_ids,
        "progress_updates": updates,
    }


def decision_support(category: str, severity: str, description: str | None, all_complaints: list[models.Complaint] | None = None) -> dict:
    """Return transparent prototype decision support for a new/unpersisted report."""
    temp = models.Complaint(
        ai_category=category,
        ai_severity=severity,
        description=description,
        assigned_department={
            "Roads and Potholes": "Public Works Department (PWD)",
            "Water Supply": "Water and Sewage Board",
            "Electricity and Power": "Electricity Board",
            "Waste Management": "Municipal Solid Waste Dept",
            "Public Safety": "Local Police",
            "Sanitation": "Health and Sanitation Dept",
            "Traffic Issues": "Traffic Police",
        }.get(category, "City Municipal Corporation"),
    )
    if all_complaints is None:
        all_complaints = []
    estimated_hours, prediction_basis = predict_resolution_hours(temp, all_complaints)
    root, factors, root_confidence, action = infer_root_cause(category, description or "", 0)
    return {
        "estimated_resolution_hours": estimated_hours,
        "probable_root_cause": root,
        "root_cause_factors": factors,
        "root_cause_confidence": root_confidence,
        "recommended_action": action,
        "prediction_basis": prediction_basis,
    }


def analyze_complaint_inputs(
    description: str | None,
    voice_transcript: str | None,
    media_url: str | None,
    all_complaints: list[models.Complaint] | None = None,
) -> dict:
    combined_text = _combine_text(description, voice_transcript)
    all_complaints = all_complaints or []

    vision_result = process_civic_vision(media_url) if media_url else {}
    detected_issue = vision_result.get("detected_issue", "General")
    vision_severity = vision_result.get("ai_severity", "Low")
    vision_confidence = float(vision_result.get("confidence_score", 0.0) or 0.0)

    ai_category = "General Maintenance"
    assigned_department = "City Municipal Corporation"
    extracted_location = None
    nlp_confidence = 0.0
    nlp_severity_confidence = 0.0
    nlp_severity = "Low"

    # Explicit civic keywords are used first so obvious phrases such as
    # "large pothole" are not accidentally pulled into a generic zero-shot class.
    keyword_category, keyword_department = map_category_and_department("", combined_text)
    if keyword_category != "General Maintenance":
        ai_category = keyword_category
        assigned_department = keyword_department
    elif nlp_processor:
        nlp_result = nlp_processor.extract_category_severity(combined_text, detected_issue)
        ai_category = nlp_result["category"]
        assigned_department = nlp_result["department"]
        extracted_location = nlp_result.get("extracted_location")
        nlp_confidence = float(nlp_result.get("category_confidence", 0.0) or 0.0)
        nlp_severity_confidence = float(nlp_result.get("severity_confidence", 0.0) or 0.0)
        nlp_severity = nlp_result.get("severity", "Low")
    else:
        ai_category, assigned_department = map_category_and_department(detected_issue, combined_text)
        nlp_severity = "Low"

    ai_severity = max(
        (vision_severity or "Low", nlp_severity or "Low"),
        key=_severity_rank,
    )
    ai_confidence = max(vision_confidence, nlp_confidence, nlp_severity_confidence)

    # If only the image provided a civic label, preserve it rather than replacing
    # it with a generic NLP category.
    if detected_issue not in {"General", "none", ""} and not combined_text:
        ai_category, assigned_department = map_category_and_department(detected_issue, "")

    support = decision_support(ai_category, ai_severity, combined_text, all_complaints)
    return {
        "detected_issue": detected_issue,
        "ai_category": ai_category,
        "ai_severity": ai_severity,
        "ai_confidence_score": round(min(max(ai_confidence, 0.0), 1.0), 2),
        "assigned_department": assigned_department,
        "extracted_location": extracted_location,
        **support,
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
    return {
        "status": "ok",
        "service": "CivicPulse AI Core API",
        "version": app.version,
        "ai_ready": nlp_processor is not None,
    }


@app.post("/api/analyze-complaint", response_model=schemas.ComplaintAnalysisResponse)
def analyze_complaint(payload: schemas.ComplaintCreate, db: Session = Depends(get_db)):
    """Run the same AI/decision-support pipeline as creation, without writing a record."""
    try:
        existing = db.query(models.Complaint).all()
        return analyze_complaint_inputs(
            payload.description,
            payload.voice_transcript,
            payload.media_url,
            existing,
        )
    except Exception as exc:
        logger.exception("Complaint analysis failed")
        raise HTTPException(500, "Complaint analysis failed") from exc


@app.post("/api/complaints", response_model=schemas.ComplaintResponse, status_code=201)
def create_complaint(payload: schemas.ComplaintCreate, db: Session = Depends(get_db)):
    if not _combine_text(payload.description, payload.voice_transcript) and not payload.media_url:
        raise HTTPException(422, "Provide a description, voice transcript, or photo evidence")

    existing = db.query(models.Complaint).all()
    result = analyze_complaint_inputs(
        payload.description,
        payload.voice_transcript,
        payload.media_url,
        existing,
    )
    now = datetime.utcnow()
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
        created_at=now,
        updated_at=now,
        verification_count=0,
        estimated_resolution_hours=result.get("estimated_resolution_hours"),
        probable_root_cause=result.get("probable_root_cause"),
    )
    append_progress(complaint, "Report submitted and added to the CivicPulse operations queue.")
    append_progress(
        complaint,
        f"AI analysis completed and routed to {complaint.assigned_department}.",
        kind="ai",
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    all_after = existing + [complaint]
    logger.info(
        "Complaint created: id=%s category=%s department=%s severity=%s priority=%s",
        complaint.id,
        complaint.ai_category,
        complaint.assigned_department,
        complaint.ai_severity,
        calculate_priority(complaint, all_after)[0],
    )
    return build_complaint_view(complaint, all_after)


@app.get("/api/complaints", response_model=list[schemas.ComplaintResponse])
def get_all_complaints(db: Session = Depends(get_db)):
    complaints = db.query(models.Complaint).order_by(models.Complaint.created_at.desc()).all()
    return [build_complaint_view(complaint, complaints) for complaint in complaints]


@app.get("/api/complaints/{complaint_id}", response_model=schemas.ComplaintResponse)
def get_complaint_by_id(complaint_id: str, db: Session = Depends(get_db)):
    complaints = db.query(models.Complaint).all()
    complaint = next((item for item in complaints if item.id == complaint_id), None)
    if not complaint:
        raise HTTPException(404, "Complaint not found")
    return build_complaint_view(complaint, complaints)


@app.post(
    "/api/complaints/{complaint_id}/verify",
    response_model=schemas.ComplaintVerificationResponse,
)
def verify_complaint(complaint_id: str, db: Session = Depends(get_db)):
    """Record one community confirmation for a complaint."""
    try:
        complaints = db.query(models.Complaint).all()
        complaint = next((item for item in complaints if item.id == complaint_id), None)
        if not complaint:
            raise HTTPException(404, "Complaint not found")
        complaint.verification_count = int(complaint.verification_count or 0) + 1
        complaint.last_verified_at = datetime.utcnow()
        complaint.updated_at = complaint.last_verified_at
        append_progress(complaint, "Community confirmation received for this issue.", kind="community")
        db.commit()
        db.refresh(complaint)
        complaints = db.query(models.Complaint).all()
        priority, reason, nearby_count, duplicate_ids = calculate_priority(complaint, complaints)
        return {
            "complaint_id": complaint.id,
            "verification_count": complaint.verification_count,
            "last_verified_at": complaint.last_verified_at,
            "priority_score": priority,
            "priority_reason": reason,
            "nearby_report_count": nearby_count,
            "duplicate_count": len(duplicate_ids),
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
    """Update workflow metadata, citizen-facing progress, and audit timestamps."""
    try:
        ensure_schema_columns()
        complaints = db.query(models.Complaint).all()
        complaint = next((item for item in complaints if item.id == complaint_id), None)
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
                elif new_status == schemas.ComplaintStatus.IN_PROGRESS.value:
                    if complaint.acknowledged_at is None:
                        complaint.acknowledged_at = now
                    if complaint.in_progress_at is None:
                        complaint.in_progress_at = now
                elif new_status == schemas.ComplaintStatus.RESOLVED.value:
                    if complaint.acknowledged_at is None:
                        complaint.acknowledged_at = now
                    if complaint.in_progress_at is None:
                        complaint.in_progress_at = now
                    if complaint.resolved_at is None:
                        complaint.resolved_at = now
                append_progress(complaint, STATUS_MESSAGES.get(new_status, f"Status changed to {new_status}."))

        if update_data.assigned_department is not None:
            new_dept = update_data.assigned_department.value
            if complaint.assigned_department != new_dept:
                complaint.assigned_department = new_dept
                changed = True
                append_progress(complaint, f"Report routed to {new_dept}.", kind="assignment")

        if update_data.progress_message and update_data.progress_message.strip():
            append_progress(complaint, update_data.progress_message, kind="admin")
            changed = True

        if changed:
            complaint.updated_at = now

        db.commit()
        db.refresh(complaint)
        complaints = db.query(models.Complaint).all()
        logger.info(
            "Complaint updated: id=%s status=%s department=%s updated_at=%s",
            complaint.id,
            complaint.status,
            complaint.assigned_department,
            complaint.updated_at,
        )
        return build_complaint_view(complaint, complaints)
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Complaint update failed for %s", complaint_id)
        raise HTTPException(500, f"Could not update complaint: {exc}") from exc


import hashlib

@app.post("/api/register", response_model=schemas.UserResponse, status_code=201)
def register_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(400, "Email already registered")
    
    hashed_password = hashlib.sha256(payload.password.encode()).hexdigest()
    user = models.User(
        name=payload.name,
        email=payload.email,
        hashed_password=hashed_password,
        created_at=datetime.utcnow()
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.post("/api/login", response_model=schemas.UserResponse)
def login_user(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user:
        raise HTTPException(401, "Invalid email or password")
    
    hashed_password = hashlib.sha256(payload.password.encode()).hexdigest()
    if user.hashed_password != hashed_password:
        raise HTTPException(401, "Invalid email or password")
    return user

# API routes are registered before the static root so /api/* remains reachable.
app.mount("/", StaticFiles(directory=str(BASE_DIR), html=True), name="static")
