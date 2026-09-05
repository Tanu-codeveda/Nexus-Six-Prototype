from __future__ import annotations

from sqlalchemy.orm import Session

from iot_common import create_iot_complaint
from vision_analyzer import VisionAnalyzer


def detect_pothole_and_create_complaint(
    db: Session,
    *,
    image_path: str,
    latitude: float | None = None,
    longitude: float | None = None,
    media_url: str | None = None,
    model_path: str | None = None,
) -> dict:
    analyzer = VisionAnalyzer(pothole_model_path=model_path)
    result = analyzer.analyze_potholes(image_path=image_path)
    complaint_id = None
    if result["detected_issue"] == "pothole":
        complaint = create_iot_complaint(
            db,
            category="Roads and Potholes",
            severity=result["ai_severity"],
            description=(
                f"IoT camera detected a pothole with {result['confidence_score']:.2f} confidence."
            ),
            latitude=latitude,
            longitude=longitude,
            media_url=media_url or image_path,
            confidence=result["confidence_score"],
            source="iot_detected",
        )
        db.commit()
        complaint_id = complaint.id
    return {**result, "complaint_id": complaint_id}
