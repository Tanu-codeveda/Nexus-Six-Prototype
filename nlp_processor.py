from __future__ import annotations

import os
import logging
import spacy
import whisper
from transformers import pipeline

CATEGORIES = [
    "Roads and Potholes",
    "Water Supply",
    "Electricity and Power",
    "Waste Management",
    "Public Safety",
    "Sanitation",
    "Traffic Issues",
]
SEVERITY_LEVELS = ["Low", "Medium", "High", "Critical"]
DEPARTMENTS = {
    "Roads and Potholes": "Public Works Department (PWD)",
    "Water Supply": "Water and Sewage Board",
    "Electricity and Power": "Electricity Board",
    "Waste Management": "Municipal Solid Waste Dept",
    "Public Safety": "Local Police",
    "Sanitation": "Health and Sanitation Dept",
    "Traffic Issues": "Traffic Police",
    "General Maintenance": "City Municipal Corporation",
}

# The backend already performs a fast civic keyword pass. This second layer is
# intentionally conservative and exists mainly for ambiguous free-text reports.
FAST_CATEGORY_KEYWORDS = {
    "Roads and Potholes": (
        "pothole", "road damage", "broken road", "damaged road", "footpath",
        "pavement", "road crack", "cracked road", "uneven pavement",
        "road surface", "road condition",
    ),
    "Water Supply": (
        "water supply", "water shortage", "no water", "water leak", "pipeline",
        "tap", "pipe burst", "low water pressure", "water pressure",
    ),
    "Electricity and Power": (
        "streetlight", "street light", "broken light", "light not working",
        "electricity", "power outage", "power cut", "electric pole",
    ),
    "Waste Management": (
        "garbage", "trash", "waste", "litter", "dump", "dumping",
        "plastic waste", "overflowing bin", "waste bin",
    ),
    "Sanitation": (
        "sanitation", "sewage", "sewer", "drainage", "dirty water",
        "stagnant water", "foul smell", "toilet",
    ),
    "Traffic Issues": (
        "traffic signal", "traffic light", "stop sign", "signal timing",
        "traffic", "congestion", "parking", "roadside parking", "traffic control",
    ),
    "Public Safety": (
        "accident", "unsafe", "danger", "crime", "security", "suspicious",
        "public safety", "emergency",
    ),
}

CRITICAL_TERMS = (
    "emergency", "life threatening", "life-threatening", "major accident",
    "electrocution", "fire", "collapsed", "collapse", "severe flooding",
)
HIGH_TERMS = (
    "dangerous", "critical", "severe", "major", "large pothole", "deep pothole",
    "risk to life", "blocking road", "completely blocked", "overflowing",
    "not working", "no water for days", "power outage",
)
MEDIUM_TERMS = (
    "moderate", "repeated", "frequent", "leaking", "damaged", "broken",
    "accumulating", "persistent",
)
LOW_TERMS = (
    "minor", "small", "slight", "cosmetic",
)


def _keyword_category(text: str) -> tuple[str | None, float]:
    text = (text or "").lower()
    best_category = None
    best_score = 0.0
    for category, keywords in FAST_CATEGORY_KEYWORDS.items():
        score = 0.0
        for keyword in keywords:
            if keyword in text:
                score += 1.0 + min(len(keyword.split()) - 1, 3) * 0.8
        if score > best_score:
            best_category = category
            best_score = score
    return best_category, best_score


def _heuristic_severity(text: str) -> tuple[str | None, float]:
    text = (text or "").lower()
    if any(term in text for term in CRITICAL_TERMS):
        return "Critical", 0.96
    if any(term in text for term in HIGH_TERMS):
        return "High", 0.90
    if any(term in text for term in MEDIUM_TERMS):
        return "Medium", 0.78
    if any(term in text for term in LOW_TERMS):
        return "Low", 0.78
    return None, 0.0


class NLPProcessor:
    def __init__(self):
        print("Loading NLP and Voice Models...")

        # Load Whisper once at startup so the first voice report does not also
        # pay the model initialization cost.
        self.whisper_model = whisper.load_model("tiny")

        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            import subprocess
            import sys

            subprocess.run(
                [sys.executable, "-m", "spacy", "download", "en_core_web_sm"],
                check=True,
            )
            self.nlp = spacy.load("en_core_web_sm")

        # BART is deliberately lazy: obvious civic reports are handled by the
        # deterministic fast path and never need the zero-shot model at all.
        self.classifier = None
        self.zero_shot_model = os.getenv(
            "CIVICPULSE_ZERO_SHOT_MODEL", "facebook/bart-large-mnli"
        )
        self.enable_zero_shot_severity = os.getenv(
            "CIVICPULSE_ZERO_SHOT_SEVERITY", "0"
        ).lower() in {"1", "true", "yes"}

    def _get_classifier(self):
        if self.classifier is None:
            self.classifier = pipeline(
                "zero-shot-classification",
                model=self.zero_shot_model,
            )
        return self.classifier

    def transcribe_audio(self, file_path: str) -> str:
        try:
            # Whisper auto-detects the spoken language. The project is optimized
            # for Hindi and English voice reporting.
            result = self.whisper_model.transcribe(file_path)
            return result.get("text", "").strip()
        except Exception as exc:
            print(f"Error transcribing audio: {exc}")
            return ""

    def extract_category_severity(self, text: str, vision_detected_issue: str = ""):
        text = (text or "").strip()
        if not text:
            text = (vision_detected_issue or "").strip()

        if not text:
            return {
                "category": "General Maintenance",
                "severity": "Low",
                "department": DEPARTMENTS["General Maintenance"],
                "extracted_location": None,
                "category_confidence": 0.0,
                "severity_confidence": 0.0,
            }

        doc = self.nlp(text)
        locations = [
            ent.text
            for ent in doc.ents
            if ent.label_ in {"GPE", "LOC", "FAC"}
        ]
        extracted_location = ", ".join(locations) if locations else None

        # Fast path: do not invoke a transformer when civic keywords are clear.
        keyword_category, keyword_score = _keyword_category(text)
        heuristic_severity, heuristic_confidence = _heuristic_severity(text)
        if keyword_category:
            severity = heuristic_severity or "Medium"
            severity_confidence = heuristic_confidence or 0.64
            return {
                "category": keyword_category,
                "severity": severity,
                "department": DEPARTMENTS.get(
                    keyword_category, DEPARTMENTS["General Maintenance"]
                ),
                "extracted_location": extracted_location,
                "category_confidence": round(
                    min(0.99, 0.72 + keyword_score * 0.06), 2
                ),
                "severity_confidence": round(severity_confidence, 2),
            }

        # Ambiguous reports use one zero-shot category pass. Severity is
        # deliberately heuristic by default, avoiding a second expensive model
        # inference. The old behavior can be enabled with
        # CIVICPULSE_ZERO_SHOT_SEVERITY=1 when accuracy matters more than speed.
        classifier = self._get_classifier()
        cat_result = classifier(text, CATEGORIES)
        top_category = cat_result["labels"][0]
        category_confidence = float(cat_result["scores"][0])

        severity, severity_confidence = _heuristic_severity(text)
        if severity is None:
            if self.enable_zero_shot_severity:
                sev_result = classifier(text, SEVERITY_LEVELS)
                severity = sev_result["labels"][0]
                severity_confidence = float(sev_result["scores"][0])
            else:
                # Neutral default for ambiguous free text. We intentionally do
                # not call the transformer a second time in the normal demo path.
                severity = "Medium"
                severity_confidence = 0.55

        return {
            "category": top_category,
            "severity": severity,
            "department": DEPARTMENTS.get(
                top_category, DEPARTMENTS["General Maintenance"]
            ),
            "extracted_location": extracted_location,
            "category_confidence": round(category_confidence, 2),
            "severity_confidence": round(severity_confidence, 2),
        }
