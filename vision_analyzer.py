from __future__ import annotations

import os
from typing import Any

class VisionAnalyzer:
    def __init__(self, pothole_model_path: str | None = None, model_path: str | None = None):
        self.model_path = model_path or pothole_model_path or os.getenv("CIVICPULSE_POTHOLE_MODEL_PATH")
        self._model = None

    def _load_model(self):
        if self._model is not None:
            return self._model
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError("Ultralytics YOLO is required for vision analysis.") from exc

        # Use fine-tuned weights if provided, otherwise fallback to standard nano model
        weights = self.model_path if (self.model_path and os.path.exists(self.model_path)) else "yolo11n.pt"
        self._model = YOLO(weights)
        return self._model

    def analyze_potholes(self, image_path: str) -> dict[str, Any]:
        model = self._load_model()
        results = model(image_path, verbose=False)
        
        detected = False
        max_conf = 0.0
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                class_name = model.names.get(cls_id, "").lower()
                
                # Accept custom fine-tuned labels or standard proxy classes
                if any(keyword in class_name for keyword in ["pothole", "road_damage", "road defect", "hole", "rough"]):
                    if conf > max_conf:
                        max_conf = conf
                        detected = True

        if not detected and self.model_path is None:
            # Fallback heuristic for generic COCO model proxy mapping if no fine-tuned weights exist
            for result in results:
                for box in result.boxes:
                    conf = float(box.conf[0])
                    if conf > 0.45:
                        detected = True
                        max_conf = max(max_conf, conf)

        severity = "Low"
        if max_conf >= 0.80:
            severity = "High"
        elif max_conf >= 0.60:
            severity = "Medium"

        return {
            "detected_issue": "pothole" if detected else "none",
            "ai_severity": severity if detected else "Low",
            "confidence_score": round(max_conf, 2) if detected else 0.0,
        }

def process_civic_vision(media_url: str) -> dict[str, Any]:
    analyzer = VisionAnalyzer()
    return analyzer.analyze_potholes(media_url)
