import base64
import logging
import os
import requests

from vision_analyzer import VisionAnalyzer


logger = logging.getLogger("civicpulse.ai")


# ---------------------------------------------------------
# Vision AI
# ---------------------------------------------------------

try:
    vision_analyzer = VisionAnalyzer(model_path="yolo11n.pt")
    logger.info("Vision analyzer initialized successfully.")
except Exception:
    vision_analyzer = None
    logger.exception(
        "Failed to initialize VisionAnalyzer. "
        "Complaints will use the safe fallback."
    )


def _ai_fallback() -> dict:
    """
    Safe fallback when AI processing cannot be completed.
    """
    return {
        "detected_issue": "General",
        "ai_severity": "Low",
        "confidence_score": 0.0,
    }


def process_civic_vision(media_input: str) -> dict:
    """
    Process an image supplied as:
      1. HTTP/HTTPS URL
      2. Local file path
      3. Raw base64 string

    Returns:
        detected_issue
        ai_severity
        confidence_score
    """

    if not media_input:
        return _ai_fallback()

    if vision_analyzer is None:
        logger.warning("Vision analyzer unavailable; using fallback.")
        return _ai_fallback()

    try:

        # -------------------------------------------------
        # Case 1: Remote image URL
        # -------------------------------------------------
        if media_input.startswith(("http://", "https://")):
            response = requests.get(media_input, timeout=10)
            response.raise_for_status()

            b64_data = base64.b64encode(response.content).decode("utf-8")

            return vision_analyzer.analyze(image_b64=b64_data)

        # -------------------------------------------------
        # Case 2: Local image path
        # -------------------------------------------------
        if os.path.exists(media_input):
            return vision_analyzer.analyze(image_path=media_input)

        # -------------------------------------------------
        # Case 3: Raw base64 image
        # -------------------------------------------------
        return vision_analyzer.analyze(image_b64=media_input)

    except Exception:
        logger.exception("Civic vision processing failed.")
        return _ai_fallback()


# ---------------------------------------------------------
# Category + Department Mapping
# ---------------------------------------------------------

def map_category_and_department(
    detected_issue: str,
    description: str = "",
) -> tuple[str, str]:
    """
    Convert AI detection + citizen description into the
    canonical CivicPulse category and department.

    IMPORTANT:
    These values must exactly match the frontend taxonomy
    in js/config.js.
    """

    issue_lower = f"{detected_issue or ''} {description or ''}".lower()

    # -----------------------------------------------------
    # Roads / potholes
    # -----------------------------------------------------
    if any(
        keyword in issue_lower
        for keyword in [
            "pothole",
            "road damage",
            "road",
            "crack",
            "broken road",
            "damaged road",
            "footpath",
            "pavement",
        ]
    ):
        return (
            "Roads and Potholes",
            "Public Works Department (PWD)",
        )

    # -----------------------------------------------------
    # Water supply
    # -----------------------------------------------------
    if any(
        keyword in issue_lower
        for keyword in [
            "water",
            "water supply",
            "water shortage",
            "no water",
            "water leak",
            "pipeline",
            "tap",
            "pipe burst",
        ]
    ):
        return (
            "Water Supply",
            "Water and Sewage Board",
        )

    # -----------------------------------------------------
    # Electricity / streetlights
    # -----------------------------------------------------
    if any(
        keyword in issue_lower
        for keyword in [
            "streetlight",
            "street light",
            "broken light",
            "light not working",
            "electricity",
            "electric",
            "power outage",
            "power cut",
        ]
    ):
        return (
            "Electricity and Power",
            "Electricity Board",
        )

    # -----------------------------------------------------
    # Waste / garbage
    # -----------------------------------------------------
    if any(
        keyword in issue_lower
        for keyword in [
            "garbage",
            "trash",
            "waste",
            "litter",
            "dump",
            "dumping",
            "bottle",
            "plastic waste",
        ]
    ):
        return (
            "Waste Management",
            "Municipal Solid Waste Dept",
        )

    # -----------------------------------------------------
    # Sanitation
    # -----------------------------------------------------
    if any(
        keyword in issue_lower
        for keyword in [
            "sanitation",
            "sewage",
            "sewer",
            "drain",
            "drainage",
            "dirty water",
            "stagnant water",
            "foul smell",
            "toilet",
        ]
    ):
        return (
            "Sanitation",
            "Health and Sanitation Dept",
        )

    # -----------------------------------------------------
    # Traffic
    # -----------------------------------------------------
    if any(
        keyword in issue_lower
        for keyword in [
            "traffic",
            "traffic signal",
            "signal",
            "stop sign",
            "traffic light",
            "congestion",
            "parking",
        ]
    ):
        return (
            "Traffic Issues",
            "Traffic Police",
        )

    # -----------------------------------------------------
    # Public safety
    # -----------------------------------------------------
    if any(
        keyword in issue_lower
        for keyword in [
            "accident",
            "unsafe",
            "danger",
            "crime",
            "security",
            "suspicious",
            "public safety",
        ]
    ):
        return (
            "Public Safety",
            "Local Police",
        )

    # -----------------------------------------------------
    # Default
    # -----------------------------------------------------
    return (
        "Public Safety",
        "City Municipal Corporation",
    )