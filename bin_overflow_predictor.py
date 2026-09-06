from __future__ import annotations

import logging
import os
from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from iot_common import create_iot_complaint

logger = logging.getLogger("civicpulse.bin_overflow")

MODEL_FEATURES = ["bin_id_num", "day_of_week", "is_festival_day", "rainfall_mm", "fill_level_pct"]
DEFAULT_BINS = 15
DEFAULT_DAYS = 120
OVERFLOW_THRESHOLD = 85.0

_model = None
_training_cache: pd.DataFrame | None = None


def generate_synthetic_history(num_bins: int = DEFAULT_BINS, days: int = DEFAULT_DAYS, seed: int = 42) -> pd.DataFrame:
    """Generate realistic-ish historical fill levels with pickup resets and festivals."""
    rng = np.random.default_rng(seed)
    start = date.today() - timedelta(days=days)
    rows: list[dict[str, Any]] = []
    bin_capacity = rng.uniform(0.75, 1.35, size=num_bins)
    pickup_days = set()

    for bin_id in range(1, num_bins + 1):
        fill = float(rng.uniform(10, 35))
        for offset in range(days):
            current = start + timedelta(days=offset)
            dow = current.weekday()
            is_festival = int((offset % 29 == 0) or (offset % 47 == 0))
            rainfall = float(max(0.0, rng.gamma(1.3, 4.0) - 2.0))
            if rng.random() < 0.07:
                rainfall += float(rng.uniform(15, 60))

            if offset > 0 and rng.random() < 0.18:
                pickup_days.add((bin_id, current))
                fill = float(rng.uniform(3, 12))

            growth = 5.0 * bin_capacity[bin_id - 1]
            growth += 3.0 if dow >= 5 else 0.0
            growth += 9.0 if is_festival else 0.0
            growth += min(4.0, rainfall / 20.0)
            growth += float(rng.normal(0, 2.0))
            fill = float(np.clip(fill + max(0.5, growth), 0, 100))

            rows.append({
                "bin_id": f"BIN-{bin_id:02d}",
                "date": current,
                "day_of_week": dow,
                "is_festival_day": is_festival,
                "rainfall_mm": round(rainfall, 2),
                "fill_level_pct": round(fill, 2),
            })

    return pd.DataFrame(rows)


def _prepare_training_frame(history: pd.DataFrame) -> pd.DataFrame:
    frame = history.copy().sort_values(["bin_id", "date"])
    frame["bin_id_num"] = frame["bin_id"].str.extract(r"(\d+)")[0].astype(int)
    frame["target_next_day_fill"] = frame.groupby("bin_id")["fill_level_pct"].shift(-1)
    frame = frame.dropna(subset=["target_next_day_fill"])
    return frame


def train_model(history: pd.DataFrame | None = None):
    """Train an XGBoost regressor once and cache it."""
    global _model, _training_cache
    if _model is not None:
        return _model

    try:
        from xgboost import XGBRegressor
    except ImportError as exc:
        raise RuntimeError("XGBoost is required for the bin overflow predictor. Install xgboost.") from exc

    if history is None:
        history = generate_synthetic_history()
    training = _prepare_training_frame(history)
    _training_cache = history

    model = XGBRegressor(
        n_estimators=250,
        max_depth=5,
        learning_rate=0.06,
        subsample=0.9,
        colsample_bytree=0.9,
        objective="reg:squarederror",
        random_state=42,
        n_jobs=2,
    )
    model.fit(training[MODEL_FEATURES], training["target_next_day_fill"])
    _model = model
    return model


def _future_festival_day(day: date) -> int:
    return int(day.weekday() == 6 or day.timetuple().tm_yday % 29 == 0 or day.timetuple().tm_yday % 47 == 0)


def _forecast_rainfall(rainfall_mm: float | None = None) -> float:
    return max(0.0, float(rainfall_mm if rainfall_mm is not None else 0.0))


def predict_overflow_risk(
    db: Session,
    *,
    rainfall_mm: float | None = None,
    today: date | None = None,
    latitude_by_bin: dict[str, float] | None = None,
    longitude_by_bin: dict[str, float] | None = None,
    create_complaints: bool = True,
) -> list[dict[str, Any]]:
    """Predict whether each bin crosses 85% within two days and optionally create complaints."""
    model = train_model()
    history = _training_cache if _training_cache is not None else generate_synthetic_history()
    latest = history.sort_values("date").groupby("bin_id").tail(1).copy()
    today = today or date.today()
    results: list[dict[str, Any]] = []

    for row in latest.to_dict("records"):
        bin_id = row["bin_id"]
        current_fill = float(row["fill_level_pct"])
        crossing_day = None
        predicted = []
        simulated_fill = current_fill

        for day_offset in (1, 2):
            forecast_day = today + timedelta(days=day_offset)
            features = pd.DataFrame([{
                "bin_id_num": int(bin_id.split("-")[-1]),
                "day_of_week": forecast_day.weekday(),
                "is_festival_day": _future_festival_day(forecast_day),
                "rainfall_mm": _forecast_rainfall(rainfall_mm),
                "fill_level_pct": simulated_fill,
            }])
            simulated_fill = float(np.clip(model.predict(features)[0], 0, 100))
            predicted.append(round(simulated_fill, 1))
            if simulated_fill >= OVERFLOW_THRESHOLD and crossing_day is None:
                crossing_day = day_offset

        at_risk = crossing_day is not None
        severity = "Low"
        if crossing_day == 1:
            severity = "High"
        elif crossing_day == 2:
            severity = "Medium"

        complaint_id = None
        if at_risk and create_complaints:
            description = (
                f"IoT bin overflow prediction for {bin_id}: predicted fill reaches "
                f"{predicted[crossing_day - 1]:.1f}% within {crossing_day} day(s), "
                f"above the {OVERFLOW_THRESHOLD:.0f}% intervention threshold."
            )
            complaint = create_iot_complaint(
                db,
                category="Waste Management",
                severity=severity,
                description=description,
                latitude=(latitude_by_bin or {}).get(bin_id),
                longitude=(longitude_by_bin or {}).get(bin_id),
                confidence=min(0.99, 0.65 + (predicted[crossing_day - 1] - OVERFLOW_THRESHOLD) / 100),
                source="iot_predicted",
            )
            complaint_id = complaint.id

        results.append({
            "bin_id": bin_id,
            "current_fill_level_pct": round(current_fill, 1),
            "predicted_next_2_days_pct": predicted,
            "overflow_risk": at_risk,
            "predicted_overflow_day": crossing_day,
            "severity": severity,
            "complaint_id": complaint_id,
        })

    if create_complaints:
        db.commit()
    return results
