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

# Specific phrases are deliberately preferred over broad terms such as "road".
# This prevents a complaint about a traffic signal on a road from being routed to PWD.
CATEGORY_KEYWORDS = {
    "Roads and Potholes": [
        "pothole", "road damage", "broken road", "damaged road",
        "footpath", "pavement", "road crack", "cracked road", "uneven pavement",
        "road surface", "road condition", "road",
    ],
    "Water Supply": [
        "water supply", "water shortage", "no water", "water leak",
        "pipeline", "tap", "pipe burst", "low water pressure", "water pressure",
    ],
    "Electricity and Power": [
        "streetlight", "street light", "broken light", "light not working",
        "electricity", "electric", "power outage", "power cut", "electric pole",
    ],
    "Waste Management": [
        "garbage", "trash", "waste", "litter", "dump", "dumping",
        "plastic waste", "overflowing bin", "waste bin",
    ],
    "Sanitation": [
        "sanitation", "sewage", "sewer", "drain", "drainage",
        "dirty water", "stagnant water", "foul smell", "toilet",
    ],
    "Traffic Issues": [
        "traffic signal", "traffic light", "stop sign", "signal timing",
        "traffic", "congestion", "parking", "roadside parking", "traffic control",
    ],
    "Public Safety": [
        "accident", "unsafe", "danger", "crime", "security",
        "suspicious", "public safety", "emergency",
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

        if media_input.startswith("data:image/") or not media_input.startswith("data:"):
            return vision_analyzer.analyze(image_b64=media_input)

        return _ai_fallback()
    except Exception:
        logger.exception("Civic vision processing failed.")
        return _ai_fallback()


def map_category_and_department(detected_issue: str, description: str = "") -> tuple[str, str]:
    """Map civic text to a category using weighted phrase matching.

    Longer/more specific phrases score higher than broad one-word matches.
    This makes routing deterministic for obvious civic phrases while still
    allowing the NLP zero-shot model to handle ambiguous free text upstream.
    """
    issue_lower = f"{detected_issue or ''} {description or ''}".lower()
    best_category = "General Maintenance"
    best_score = 0.0

    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0.0
        for keyword in keywords:
            if keyword in issue_lower:
                # Specific phrases carry more weight than generic words.
                score += 1.0 + min(len(keyword.split()) - 1, 3) * 0.9
        if score > best_score:
            best_score = score
            best_category = category

    return best_category, CATEGORY_TO_DEPARTMENT[best_category]
