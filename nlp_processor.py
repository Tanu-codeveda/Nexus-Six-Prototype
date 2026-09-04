import whisper
import spacy
from transformers import pipeline
import tempfile
import urllib.request
import os

CATEGORIES = [
    "Roads and Potholes", "Water Supply", "Electricity and Power", 
    "Waste Management", "Public Safety", "Sanitation", "Traffic Issues"
]
SEVERITY_LEVELS = ["Low", "Medium", "High", "Critical"]
DEPARTMENTS = {
    "Roads and Potholes": "Public Works Department (PWD)",
    "Water Supply": "Water and Sewage Board",
    "Electricity and Power": "Electricity Board",
    "Waste Management": "Municipal Solid Waste Dept",
    "Public Safety": "Local Police",
    "Sanitation": "Health and Sanitation Dept",
    "Traffic Issues": "Traffic Police"
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
            subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
            self.nlp = spacy.load("en_core_web_sm")
            
        self.classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

    def transcribe_audio(self, file_path: str) -> str:
        """Converts audio file to text using Whisper."""
        try:
            result = self.whisper_model.transcribe(file_path)
            return result["text"].strip()
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return ""

    def extract_category_severity(self, text: str, vision_detected_issue: str = ""):
        if not text:
            text = vision_detected_issue
            
        if not text:
            return {
                "category": "General Maintenance",
                "severity": "Low",
                "department": "City Municipal Corporation",
                "extracted_location": None
            }

        # 1. Location Extraction
        doc = self.nlp(text)
        locations = [ent.text for ent in doc.ents if ent.label_ in ["GPE", "LOC", "FAC"]]
        extracted_location = ", ".join(locations) if locations else None
        
        # 2. Zero-Shot Category Classification
        cat_result = self.classifier(text, CATEGORIES)
        top_category = cat_result["labels"][0]
        
        # 3. Zero-Shot Severity Classification
        sev_result = self.classifier(text, SEVERITY_LEVELS)
        severity = sev_result["labels"][0]
        
        # 4. Department Mapping
        assigned_dept = DEPARTMENTS.get(top_category, "City Municipal Corporation")
        
        return {
            "category": top_category,
            "severity": severity,
            "department": assigned_dept,
            "extracted_location": extracted_location
        }
