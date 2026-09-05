from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Optional

import cv2
import numpy as np
from sqlalchemy.orm import Session

from iot_common import create_iot_complaint

logger = logging.getLogger("civicpulse.streetlight")

_ZONE_BASELINES: dict[str, float] = {}


def monitor_streetlight(
    db: Session,
    *,
    zone_id: str,
    image_path: str,
    roi: tuple[int, int, int, int] | None = None,
    threshold_luminance: float = 45.0,
    baseline_ratio: float = 0.35,
    persistent_frames: int = 1,
    demo_override: bool = False,
    latitude: float | None = None,
    longitude: float | None = None,
) -> dict:
    """Monitor street-light illumination via OpenCV luminance with night-hours guard."""
    now = datetime.now()
    hour = now.hour
    is_night = (20 <= hour <= 23) or (0 <= hour < 5)

    if not is_night and not demo_override:
        return {
            "zone_id": zone_id,
            "monitored": False,
            "reason": "Outside night monitoring hours (8 PM - 5 AM) and demo_override is false.",
            "complaint_id": None,
        }

    frame = cv2.imread(image_path)
    if frame is None:
        raise ValueError(f"Could not read image: {image_path}")

    h, w = frame.shape[:2]
    if roi:
        x1, y1, x2, y2 = roi
    else:
        x1, y1, x2, y2 = int(w * 0.2), int(h * 0.2), int(w * 0.8), int(h * 0.8)

    crop = frame[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
    gray = cv2.cvtColor(crop if crop.size else frame, cv2.COLOR_BGR2GRAY)
    luminance = float(np.mean(gray))

    baseline = _ZONE_BASELINES.get(zone_id)
    if baseline is None:
        # Initialize rolling baseline if not present
        baseline = max(luminance, 60.0)
        _ZONE_BASELINES[zone_id] = baseline
    else:
        # Update rolling baseline slowly
        _ZONE_BASELINES[zone_id] = 0.9 * baseline + 0.1 * luminance

    failed = luminance < threshold_luminance or luminance < (baseline * baseline_ratio)
    complaint_id = None

    if failed:
        complaint = create_iot_complaint(
            db,
            category="Electricity and Power",
            severity="High",
            description=(
                f"IoT streetlight failure detected in zone {zone_id}: average luminance "
                f"{luminance:.1f} fell below threshold ({threshold_luminance:.1f}) or baseline ratio."
            ),
            latitude=latitude,
            longitude=longitude,
            media_url=image_path,
            confidence=0.91,
            source="iot_detected",
        )
        db.commit()
        complaint_id = complaint.id

    return {
        "zone_id": zone_id,
        "monitored": True,
        "luminance": round(luminance, 1),
        "baseline_luminance": round(_ZONE_BASELINES[zone_id], 1),
        "failure_detected": failed,
        "complaint_id": complaint_id,
    }
