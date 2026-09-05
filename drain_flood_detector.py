from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
from sqlalchemy.orm import Session

from iot_common import create_iot_complaint

logger = logging.getLogger("civicpulse.drain_flood")


@dataclass(frozen=True)
class DrainZone:
    zone_id: str
    latitude: float
    longitude: float
    curb_y: int
    reference_height_px: int
    coverage_threshold_pct: float = 60.0


def load_zones() -> dict[str, DrainZone]:
    raw = os.getenv("CIVICPULSE_DRAIN_ZONES", "")
    if raw:
        data = json.loads(raw)
        return {
            item["zone_id"]: DrainZone(
                zone_id=item["zone_id"],
                latitude=float(item["latitude"]),
                longitude=float(item["longitude"]),
                curb_y=int(item["curb_y"]),
                reference_height_px=int(item["reference_height_px"]),
                coverage_threshold_pct=float(item.get("coverage_threshold_pct", 60.0)),
            )
            for item in data
        }
    return {}


def fetch_openweather_rainfall(latitude: float, longitude: float, api_key: str | None = None) -> dict:
    key = api_key or os.getenv("OPENWEATHER_API_KEY")
    if not key:
        return {"available": False, "rainfall_mm": 0.0, "reason": "OPENWEATHER_API_KEY is not configured"}

    query = urllib.parse.urlencode({
        "lat": latitude,
        "lon": longitude,
        "appid": key,
        "units": "metric",
    })
    url = f"https://api.openweathermap.org/data/2.5/weather?{query}"
    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
        rain = payload.get("rain", {}) or {}
        rainfall = float(rain.get("1h", rain.get("3h", 0.0)) or 0.0)
        return {"available": True, "rainfall_mm": rainfall, "weather": payload.get("weather", [])}
    except Exception as exc:
        logger.warning("OpenWeather request failed: %s", exc)
        return {"available": False, "rainfall_mm": 0.0, "reason": str(exc)}


def estimate_water_coverage(
    frame: np.ndarray,
    *,
    curb_y: int,
    reference_height_px: int,
    coverage_threshold_pct: float = 60.0,
) -> dict:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    curb_y = int(np.clip(curb_y, 1, h - 2))
    reference_height_px = max(1, min(reference_height_px, h - curb_y - 1))
    bottom_y = min(h - 1, curb_y + reference_height_px)

    gradients = np.mean(np.abs(np.diff(gray.astype(np.float32), axis=0)), axis=1)
    search_start = curb_y + max(2, reference_height_px // 20)
    search_end = max(search_start + 1, bottom_y - max(2, reference_height_px // 20))
    local = gradients[search_start:search_end]
    candidate_y = int(search_start + np.argmax(local)) if len(local) else bottom_y

    lower = gray[curb_y:bottom_y + 1]
    lower_mean = float(np.mean(lower)) if lower.size else 0.0
    edge_strength = float(np.max(local)) if len(local) else 0.0
    coverage_pct = float(np.clip((bottom_y - candidate_y) / reference_height_px * 100.0, 0, 100))

    confidence = 0.35
    confidence += min(0.4, edge_strength / 80.0)
    confidence += 0.15 if lower_mean < 145 else 0.0
    confidence = float(np.clip(confidence, 0.0, 0.95))

    return {
        "water_coverage_pct": round(coverage_pct, 1),
        "flooding_detected": coverage_pct >= coverage_threshold_pct,
        "confidence": round(confidence, 2),
        "curb_y": curb_y,
        "reference_height_px": reference_height_px,
    }


def check_drain(
    db: Session,
    *,
    zone: DrainZone,
    frame: np.ndarray,
    api_key: str | None = None,
    create_complaint: bool = True,
) -> dict:
    weather = fetch_openweather_rainfall(zone.latitude, zone.longitude, api_key)
    vision = estimate_water_coverage(
        frame,
        curb_y=zone.curb_y,
        reference_height_px=zone.reference_height_px,
        coverage_threshold_pct=zone.coverage_threshold_pct,
    )

    rainfall = weather["rainfall_mm"]
    confirmed = bool(vision["flooding_detected"] and (rainfall >= 2.0 or vision["confidence"] >= 0.70))
    complaint_id = None
    if confirmed and create_complaint:
        confidence = min(0.98, vision["confidence"] + (0.15 if rainfall >= 2.0 else 0.0))
        complaint = create_iot_complaint(
            db,
            category="Sanitation",
            severity="High" if vision["water_coverage_pct"] >= 80 else "Medium",
            description=(
                f"IoT drain flooding alert for zone {zone.zone_id}: estimated water coverage "
                f"{vision['water_coverage_pct']:.1f}% of the configured curb reference height; "
                f"OpenWeather rainfall={rainfall:.1f} mm."
            ),
            latitude=zone.latitude,
            longitude=zone.longitude,
            confidence=round(confidence, 2),
            source="iot_detected",
        )
        db.commit()
        complaint_id = complaint.id

    return {
        "zone_id": zone.zone_id,
        "rainfall_mm": rainfall,
        "weather_available": weather["available"],
        "water_coverage_pct": vision["water_coverage_pct"],
        "flooding_detected": confirmed,
        "confidence": vision["confidence"],
        "complaint_id": complaint_id,
    }
