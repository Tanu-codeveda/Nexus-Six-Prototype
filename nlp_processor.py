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


class NLPProcessor:
    def __init__(self):
        print("Loading NLP and Voice Models...")
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

        self.classifier = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",
        )

    def transcribe_audio(self, file_path: str) -> str:
        try:
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

        cat_result = self.classifier(text, CATEGORIES)
        sev_result = self.classifier(text, SEVERITY_LEVELS)
        top_category = cat_result["labels"][0]
        severity = sev_result["labels"][0]

        return {
            "category": top_category,
            "severity": severity,
            "department": DEPARTMENTS.get(top_category, DEPARTMENTS["General Maintenance"]),
            "extracted_location": extracted_location,
            "category_confidence": float(cat_result["scores"][0]),
            "severity_confidence": float(sev_result["scores"][0]),
        }
