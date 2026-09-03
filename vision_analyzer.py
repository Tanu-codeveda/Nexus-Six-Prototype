from __future__ import annotations

import base64
import binascii
import json
import logging
import os
from typing import Optional, TypedDict

import cv2
import numpy as np
from ultralytics import YOLO

logger = logging.getLogger("vision_analyzer")


class AnalysisResult(TypedDict):
    detected_issue: str
    ai_severity: str
    confidence_score: float


CIVIC_CLASS_MAP = {
    # Civic specific labels (for fine-tuned weights)
    "pothole": "pothole",
    "garbage": "garbage_accumulation",
    "trash": "garbage_accumulation",
    "litter": "garbage_accumulation",
    "broken_streetlight": "broken_streetlight",
    "streetlight_off": "broken_streetlight",
    # COCO pre-trained proxies (for demo testing with standard yolo11n.pt)
    "bottle": "garbage_accumulation",
    "cup": "garbage_accumulation",
    "traffic light": "broken_streetlight",
    "stop sign": "broken_streetlight",
    "car": "pothole",
}

SEVERITY_THRESHOLDS = {
    "High": {"min_confidence": 0.75, "min_area_ratio": 0.08},
    "Medium": {"min_confidence": 0.55, "min_area_ratio": 0.02},
}


class VisionAnalyzer:
    def __init__(
        self,
        model_path: str = "yolo11n.pt",
        confidence_threshold: float = 0.35,
        device: Optional[str] = None,
    ) -> None:
        self.confidence_threshold = confidence_threshold
        self.device = device

        logger.info("Loading YOLO model from %s", model_path)
        self.model = YOLO(model_path)
        if device:
            self.model.to(device)

        self.model_class_names: dict[int, str] = self.model.names

    def analyze(
        self,
        image_path: Optional[str] = None,
        image_b64: Optional[str] = None,
    ) -> AnalysisResult:
        if not image_path and not image_b64:
            raise ValueError("Provide either image_path or image_b64.")
        if image_path and image_b64:
            raise ValueError("Provide only one of image_path or image_b64, not both.")

        frame, temp_file = self._load_image(image_path, image_b64)
        try:
            return self._run_inference(frame)
        finally:
            if temp_file and os.path.exists(temp_file):
                os.remove(temp_file)

    def analyze_to_json(self, **kwargs) -> str:
        return json.dumps(self.analyze(**kwargs))

    def _load_image(
        self, image_path: Optional[str], image_b64: Optional[str]
    ) -> tuple[np.ndarray, Optional[str]]:
        if image_path:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image path does not exist: {image_path}")
            frame = cv2.imread(image_path)
            if frame is None:
                raise ValueError(f"Could not decode image at: {image_path}")
            return frame, None

        raw = self._decode_base64(image_b64)
        arr = np.frombuffer(raw, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("Could not decode base64 image data.")
        return frame, None

    @staticmethod
    def _decode_base64(b64_string: str) -> bytes:
        if "," in b64_string and b64_string.strip().startswith("data:"):
            b64_string = b64_string.split(",", 1)[1]
        try:
            return base64.b64decode(b64_string, validate=True)
        except binascii.Error as exc:
            raise ValueError(f"Invalid base64 image data: {exc}") from exc

    def _run_inference(self, frame: np.ndarray) -> AnalysisResult:
        height, width = frame.shape[:2]
        frame_area = float(height * width)

        results = self.model.predict(
            source=frame,
            conf=self.confidence_threshold,
            device=self.device,
            verbose=False,
        )

        best = self._select_best_detection(results, frame_area)

        if best is None:
            return {
                "detected_issue": "none",
                "ai_severity": "Low",
                "confidence_score": 0.0,
            }

        detected_issue, confidence, area_ratio = best
        severity = self._score_severity(confidence, area_ratio)

        return {
            "detected_issue": detected_issue,
            "ai_severity": severity,
            "confidence_score": round(float(confidence), 2),
        }

    def _select_best_detection(
        self, results, frame_area: float
    ) -> Optional[tuple[str, float, float]]:
        candidates: list[tuple[str, float, float]] = []

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            xyxy = boxes.xyxy.cpu().numpy()
            confs = boxes.conf.cpu().numpy()
            class_ids = boxes.cls.cpu().numpy().astype(int)

            for (x1, y1, x2, y2), conf, class_id in zip(xyxy, confs, class_ids):
                raw_name = self.model_class_names.get(int(class_id), "")
                mapped = CIVIC_CLASS_MAP.get(raw_name.lower())
                if mapped is None:
                    continue

                box_area = max(0.0, (x2 - x1)) * max(0.0, (y2 - y1))
                area_ratio = box_area / frame_area if frame_area else 0.0
                candidates.append((mapped, float(conf), float(area_ratio)))

        if not candidates:
            return None

        candidates.sort(key=lambda c: (c[1], c[2]), reverse=True)
        return candidates[0]

    @staticmethod
    def _score_severity(confidence: float, area_ratio: float) -> str:
        high = SEVERITY_THRESHOLDS["High"]
        medium = SEVERITY_THRESHOLDS["Medium"]

        if confidence >= high["min_confidence"] and area_ratio >= high["min_area_ratio"]:
            return "High"
        if confidence >= medium["min_confidence"] and area_ratio >= medium["min_area_ratio"]:
            return "Medium"
        return "Low"


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python vision_analyzer.py <image_path>")
        sys.exit(1)

    analyzer = VisionAnalyzer()
    output = analyzer.analyze(image_path=sys.argv[1])
    print(json.dumps(output, indent=2))