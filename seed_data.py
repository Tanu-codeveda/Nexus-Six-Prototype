"""
CivicPulse AI - realistic Ranchi demo data seeder.

Usage:
    python seed_data.py
    python seed_data.py --count 50
    python seed_data.py --base-url http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import random
import time

import requests
from faker import Faker


RANCHI_CENTER = (23.3441, 85.3096)

LOCALITIES = [
    "Main Road",
    "Harmu",
    "Lalpur",
    "Doranda",
    "Morabadi",
    "Kanke Road",
    "Booty More",
    "Ashok Nagar",
    "Argora",
    "Ratu Road",
    "Hinoo",
    "Kokar",
    "Kadru",
    "Bariatu",
    "Namkum",
]

TEMPLATES = {
    "Roads and Potholes": [
        "Large pothole near {locality} is causing two-wheelers to swerve into traffic.",
        "Road surface has broken down badly around {locality}; rainwater is collecting in the damaged section.",
        "Deep road crack and uneven pavement reported near {locality}.",
        "Damaged footpath and broken pavement along {locality} are difficult for pedestrians to use.",
    ],
    "Water Supply": [
        "Low water pressure has been reported near {locality} since morning.",
        "Pipeline leak near {locality} is wasting water onto the roadside.",
        "Several homes near {locality} have reported a water supply interruption.",
        "Possible pipe burst near {locality}; water is flowing continuously onto the street.",
    ],
    "Electricity and Power": [
        "Street light is not working near {locality}, leaving the road poorly lit after sunset.",
        "Repeated power cut reported around {locality}; residents are requesting inspection.",
        "Multiple streetlights appear faulty near {locality}.",
        "Broken electric light pole reported near {locality}; area becomes dark at night.",
    ],
    "Waste Management": [
        "Garbage accumulation reported near {locality}; collection appears overdue.",
        "Mixed waste has been dumped beside the road near {locality}.",
        "Plastic waste and litter are scattered around a collection point in {locality}.",
        "Overflowing waste bin reported near {locality}, causing bad smell and litter.",
    ],
    "Sanitation": [
        "Open drain near {locality} is clogged and overflowing after recent rain.",
        "Stagnant water and foul smell reported near a drainage line in {locality}.",
        "Sewage overflow reported near {locality}; pedestrians are unable to pass comfortably.",
        "Drainage blockage near {locality} is causing dirty water to collect on the roadside.",
    ],
    "Traffic Issues": [
        "Traffic signal timing appears faulty near {locality}, causing congestion.",
        "Heavy traffic congestion reported at {locality} during peak hours.",
        "Illegal roadside parking near {locality} is narrowing the carriageway.",
        "A stop sign / traffic-control issue has been reported near {locality}.",
    ],
    "Public Safety": [
        "Poorly monitored public area near {locality} has been reported as unsafe after dark.",
        "Suspicious activity reported near {locality}; residents requested a safety check.",
        "A minor road accident was reported near {locality}; signage and safety measures may need review.",
        "Residents report a potentially dangerous public-safety situation near {locality}.",
    ],
}

SEVERITY_MODIFIERS = {
    "Critical": "Emergency: immediate danger is reported and urgent municipal response is required.",
    "High": "This is dangerous and could cause harm if left unattended.",
    "Medium": "The issue is persistent and needs attention soon.",
    "Low": "Minor issue observed; there is no immediate danger.",
}

# Deliberately balanced for a convincing dashboard demo: roughly 4% critical,
# 20% high, 44% medium and 32% low when --count 50 is used.
SEVERITY_SEQUENCE = [
    "Critical", "Critical",
    *(["High"] * 10),
    *(["Medium"] * 22),
    *(["Low"] * 16),
]

CATEGORY_WEIGHTS = {
    "Roads and Potholes": 22,
    "Water Supply": 14,
    "Electricity and Power": 13,
    "Waste Management": 15,
    "Sanitation": 13,
    "Traffic Issues": 10,
    "Public Safety": 13,
}

FALLBACK_LAT, FALLBACK_LON = RANCHI_CENTER

fake = Faker("en_IN")


def build_payload(category: str, severity: str) -> dict:
    locality = random.choice(LOCALITIES)
    template = random.choice(TEMPLATES[category])
    description = f"{SEVERITY_MODIFIERS[severity]} {template.format(locality=locality)}"

    # Small cluster around Ranchi rather than a uniform city-wide scatter.
    latitude = FALLBACK_LAT + random.uniform(-0.045, 0.045)
    longitude = FALLBACK_LON + random.uniform(-0.045, 0.045)

    # Add a little realistic variation without introducing fields the API
    # does not currently support.
    if random.random() < 0.35:
        description += f" Reference: {fake.bothify(text='CP-####-??')}."

    return {
        "latitude": round(latitude, 6),
        "longitude": round(longitude, 6),
        "media_url": None,
        "description": description,
    }


def choose_category() -> str:
    categories = list(CATEGORY_WEIGHTS)
    weights = list(CATEGORY_WEIGHTS.values())
    return random.choices(categories, weights=weights, k=1)[0]


def wait_for_api(base_url: str) -> bool:
    try:
        response = requests.get(f"{base_url}/api/health", timeout=3)
        return response.ok and response.json().get("status") == "ok"
    except requests.RequestException:
        return False


def seed(base_url: str, count: int) -> None:
    print("=" * 64)
    print("CivicPulse AI - Demo Data Seeder")
    print("=" * 64)
    print(f"API: {base_url}")
    print("Location: Ranchi, Jharkhand")
    print(f"Complaints: {count}")
    print()

    if not wait_for_api(base_url):
        print("ERROR: CivicPulse API is not reachable.")
        print("Start the backend first:")
        print("python -m uvicorn main:app")
        return

    success = 0
    failed = 0

    severity_counts = {level: 0 for level in SEVERITY_MODIFIERS}

    for index in range(1, count + 1):
        category = choose_category()
        severity = SEVERITY_SEQUENCE[(index - 1) % len(SEVERITY_SEQUENCE)]
        severity_counts[severity] += 1
        payload = build_payload(category, severity)

        try:
            response = requests.post(
                f"{base_url}/api/complaints",
                json=payload,
                timeout=10,
            )

            if response.status_code == 201:
                data = response.json()
                success += 1
                print(
                    f"[{index:02d}/{count}] "
                    f"{data['ai_category']:<24} "
                    f"| {data['assigned_department']:<30} "
                    f"| severity={data.get('ai_severity', 'n/a'):<8} "
                    f"| priority={data.get('priority_score', 'n/a')}"
                )
            else:
                failed += 1
                print(
                    f"[{index:02d}/{count}] FAILED "
                    f"{response.status_code}: {response.text[:160]}"
                )
        except requests.RequestException as exc:
            failed += 1
            print(f"[{index:02d}/{count}] FAILED: {exc}")

        time.sleep(0.05)

    print()
    print("=" * 64)
    print("SEED COMPLETE")
    print("=" * 64)
    print(f"Successful : {success}")
    print(f"Failed     : {failed}")
    print("Severity target mix:")
    print("  " + ", ".join(f"{level}={severity_counts[level]}" for level in SEVERITY_MODIFIERS))

    if success:
        print(f"\nDashboard: {base_url}")
        print(f"API docs : {base_url}/docs")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed CivicPulse demo complaints.")
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.count < 1:
        raise SystemExit("--count must be at least 1.")

    random.seed(42)
    Faker.seed(42)
    seed(args.base_url.rstrip("/"), args.count)


if __name__ == "__main__":
    main()
