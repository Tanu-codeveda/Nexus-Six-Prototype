import base64
import logging
import os

import requests

from vision_analyzer import VisionAnalyzer


logger = logging.getLogger("civicpulse.ai")


try:
    vision_analyzer = VisionAnalyzer(model_path="yolo11n.pt")
    logger.info("Vision analyzer initialized successfully.")
except Exception:
    vision_analyzer = None
    logger.exception(
        "Failed to initialize VisionAnalyzer. Complaints will use the safe fallback."
    )


CATEGORY_TO_DEPARTMENT = {
    "Roads and Potholes": "Public Works Department (PWD)",
    "Water Supply": "Water and Sewage Board",
    "Electricity and Power": "Electricity Board",
    "Waste Management": "Municipal Solid Waste Dept",
    "Public Safety": "Local Police",
    "Sanitation": "Health and Sanitation Dept",
    "Traffic Issues": "Traffic Police",
    "General Maintenance": "City Municipal Corporation",
}


CATEGORY_KEYWORDS = {
    "Roads and Potholes": [
        "pothole", "road damage", "broken road", "damaged road",
        "road", "crack", "footpath", "pavement",
    ],
    "Water Supply": [
        "water supply", "water shortage", "no water", "water leak",
        "pipeline", "tap", "pipe burst",
    ],
    "Electricity and Power": [
        "streetlight", "street light", "broken light", "light not working",
        "electricity", "electric", "power outage", "power cut",
    ],
    "Waste Management": [
        "garbage", "trash", "waste", "litter", "dump", "dumping",
        "bottle", "plastic waste",
    ],
    "Sanitation": [
        "sanitation", "sewage", "sewer", "drain", "drainage",
        "dirty water", "stagnant water", "foul smell", "toilet",
    ],
    "Traffic Issues": [
        "traffic", "traffic signal", "signal", "stop sign",
        "traffic light", "congestion", "parking",
    ],
    "Public Safety": [
        "accident", "unsafe", "danger", "crime", "security",
        "suspicious", "public safety",
    ],
}


def _ai_fallback() -> dict:
    return {
        "detected_issue": "General",
        "ai_severity": "Low",
        "confidence_score": 0.0,
    }


def process_civic_vision(media_input: str) -> dict:
    if not media_input or vision_analyzer is None:
        return _ai_fallback()

    try:
        if media_input.startswith(("http://", "https://")):
            response = requests.get(media_input, timeout=10)
            response.raise_for_status()
            b64_data = base64.b64encode(response.content).decode("utf-8")
            return vision_analyzer.analyze(image_b64=b64_data)

        if os.path.exists(media_input):
            return vision_analyzer.analyze(image_path=media_input)

        # Only image data URLs/raw base64 should reach the image analyzer.
        if media_input.startswith("data:image/") or not media_input.startswith("data:"):
            return vision_analyzer.analyze(image_b64=media_input)

        return _ai_fallback()
    except Exception:
        logger.exception("Civic vision processing failed.")
        return _ai_fallback()


def map_category_and_department(detected_issue: str, description: str = "") -> tuple[str, str]:
    issue_lower = f"{detected_issue or ''} {description or ''}".lower()

    # Prefer explicit civic terminology before generic word matches.
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in issue_lower for keyword in keywords):
            return category, CATEGORY_TO_DEPARTMENT[category]

    return "General Maintenance", CATEGORY_TO_DEPARTMENT["General Maintenance"]
