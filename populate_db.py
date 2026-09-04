from database import SessionLocal
import models
from datetime import datetime, timedelta
import random

db = SessionLocal()

# Realistic locations in Ranchi, Jharkhand
locations = [
    (23.3441, 85.3096),
    (23.3551, 85.3116),
    (23.3321, 85.3236),
    (23.3641, 85.2956),
    (23.3751, 85.3346),
    (23.3211, 85.2816)
]

categories = [
    "Roads and Potholes",
    "Water Supply",
    "Electricity and Power",
    "Waste Management",
    "Public Safety"
]

departments = {
    "Roads and Potholes": "Public Works Department (PWD)",
    "Water Supply": "Water and Sewage Board",
    "Electricity and Power": "Electricity Board",
    "Waste Management": "Municipal Solid Waste Dept",
    "Public Safety": "Local Police"
}

descriptions = [
    "Huge pothole on the main road causing severe traffic jams.",
    "No water supply for the past 3 days in our area.",
    "Street light pole is broken and wires are hanging dangerously.",
    "Garbage has not been collected for a week, it smells terrible.",
    "Suspicious activity near the abandoned building."
]

now = datetime.utcnow()

for i in range(15):
    cat = random.choice(categories)
    lat, lng = random.choice(locations)
    # add slight jitter to coordinates
    lat += random.uniform(-0.02, 0.02)
    lng += random.uniform(-0.02, 0.02)
    
    c = models.Complaint(
        id=f"COMP-{random.randint(1000,9999)}-{i}",
        latitude=lat,
        longitude=lng,
        media_url="",
        description=random.choice(descriptions),
        ai_category=cat,
        ai_severity=random.choice(["Low", "Medium", "High", "Critical"]),
        status=random.choice(["Pending", "Acknowledged", "In Progress", "Resolved"]),
        assigned_department=departments[cat],
        created_at=now - timedelta(days=random.randint(0, 10), hours=random.randint(0, 23))
    )
    db.add(c)

db.commit()
print("Successfully populated the database with 15 mock complaints!")
