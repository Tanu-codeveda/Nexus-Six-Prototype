import base64
import os
import requests
from vision_analyzer import VisionAnalyzer

try:
    vision_analyzer = VisionAnalyzer(model_path="yolo11n.pt")
except Exception:
    vision_analyzer = None


def process_civic_vision(media_input: str) -> dict:
    """Processes media input (URL, local file, or base64) through VisionAnalyzer."""
    if not media_input or not vision_analyzer:
        return {"detected_issue": "General", "ai_severity": "Low", "confidence_score": 0.0}

    try:
        # Case 1: Remote HTTP/HTTPS URL -> Download and convert to base64
        if media_input.startswith("http://") or media_input.startswith("https://"):
            resp = requests.get(media_input, timeout=10)
            if resp.status_code == 200:
                b64_data = base64.b64encode(resp.content).decode("utf-8")
                return vision_analyzer.analyze(image_b64=b64_data)
            return {"detected_issue": "General", "ai_severity": "Low", "confidence_score": 0.0}

        # Case 2: Local file path
        if os.path.exists(media_input):
            return vision_analyzer.analyze(image_path=media_input)

        # Case 3: Raw base64 string
        return vision_analyzer.analyze(image_b64=media_input)
    except Exception:
        return {"detected_issue": "General", "ai_severity": "Low", "confidence_score": 0.0}


def map_category_and_department(detected_issue: str, description: str = "") -> tuple[str, str]:
    """Map detected issue / text context to Municipal Department and AI Category."""
    issue_lower = (detected_issue + " " + (description or "")).lower()

    if any(k in issue_lower for k in ["pothole", "road", "crack"]):
        return "Roads & PWD", "PWD - Road Maintenance"
    elif any(k in issue_lower for k in ["garbage", "trash", "waste", "litter", "bottle"]):
        return "Sanitation Dept", "Solid Waste Management"
    elif any(k in issue_lower for k in ["light", "streetlight", "electric"]):
        return "Electrical & Power", "Zonal Lighting Office"
    elif any(k in issue_lower for k in ["water", "leak", "drain"]):
        return "Water & Sewage", "Water Supply Dept"
    return "General Maintenance", "City Municipal Corporation"