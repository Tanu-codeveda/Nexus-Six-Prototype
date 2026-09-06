from __future__ import annotations

import os
from typing import Optional

import cv2
from sqlalchemy.orm import Session

from bin_overflow_predictor import predict_overflow_risk
from drain_flood_detector import check_drain, load_zones
from streetlight_monitor import monitor_streetlight


def run_bin_check(db: Session, rainfall_mm: float | None = None) -> list[dict]:
    return predict_overflow_risk(db, rainfall_mm=rainfall_mm)


def run_streetlight_check(
    db: Session,
    *,
    zone_id: str,
    image_path: str,
    demo_override: bool = False,
    latitude: float | None = None,
    longitude: float | None = None,
) -> dict:
    return monitor_streetlight(
        db,
        zone_id=zone_id,
        image_path=image_path,
        demo_override=demo_override,
        latitude=latitude,
        longitude=longitude,
    )


def run_drain_check(db: Session, *, zone_id: str, image_path: str) -> dict:
    zones = load_zones()
    if zone_id not in zones:
        raise KeyError(f"Drain zone '{zone_id}' is not configured")
    frame = cv2.imread(image_path)
    if frame is None:
        raise ValueError(f"Could not read image: {image_path}")
    return check_drain(db, zone=zones[zone_id], frame=frame)
