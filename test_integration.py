"""CivicPulse API integration checks. Run with FastAPI already running."""
from __future__ import annotations

import sys
import uuid

import requests

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 15


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    print("CivicPulse API Integration Test")
    health = requests.get(f"{BASE_URL}/api/health", timeout=TIMEOUT)
    check(health.status_code == 200, health.text)
    print("[PASS] health")

    marker = str(uuid.uuid4())[:8]
    payload = {
        "latitude": 23.3441,
        "longitude": 85.3096,
        "media_url": None,
        "description": f"Integration test pothole near Main Road {marker}",
        "voice_transcript": None,
    }
    analysis = requests.post(f"{BASE_URL}/api/analyze-complaint", json=payload, timeout=TIMEOUT)
    check(analysis.status_code == 200, analysis.text)
    analysis_data = analysis.json()
    check(analysis_data["ai_category"] == "Roads and Potholes", "Analysis category mapping failed")
    print("[PASS] analyze")

    created = requests.post(f"{BASE_URL}/api/complaints", json=payload, timeout=TIMEOUT)
    check(created.status_code == 201, created.text)
    record = created.json()
    complaint_id = record["id"]
    check(record["status"] == "Pending", "Default status wrong")
    check(record["updated_at"], "updated_at missing")
    print("[PASS] create")

    for status in ["Acknowledged", "In Progress", "Resolved"]:
        response = requests.patch(
            f"{BASE_URL}/api/complaints/{complaint_id}",
            json={"status": status},
            timeout=TIMEOUT,
        )
        check(response.status_code == 200, response.text)
        data = response.json()
        check(data["status"] == status, f"Status did not become {status}")
        print(f"[PASS] patch {status}")

    final = requests.get(f"{BASE_URL}/api/complaints/{complaint_id}", timeout=TIMEOUT)
    check(final.status_code == 200, final.text)
    final_data = final.json()
    check(final_data["acknowledged_at"], "acknowledged_at missing")
    check(final_data["in_progress_at"], "in_progress_at missing")
    check(final_data["resolved_at"], "resolved_at missing")
    check(final_data["updated_at"], "updated_at missing")
    print("[PASS] lifecycle timestamps")

    invalid = requests.patch(
        f"{BASE_URL}/api/complaints/{complaint_id}",
        json={"status": "Not A Real Status"},
        timeout=TIMEOUT,
    )
    check(invalid.status_code == 422, "Invalid status should return 422")
    print("[PASS] validation")

    print("ALL INTEGRATION TESTS PASSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (requests.RequestException, AssertionError) as exc:
        print(f"[FAIL] {exc}")
        raise SystemExit(1)
