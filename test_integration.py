"""
CivicPulse API integration checks.

Run with the FastAPI server already running:
    python test_integration.py
"""

from __future__ import annotations

import sys
import uuid

import requests


BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 10


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    print("=" * 64)
    print("CivicPulse API Integration Test")
    print("=" * 64)

    # 1. Health
    health = requests.get(f"{BASE_URL}/api/health", timeout=TIMEOUT)
    check(health.status_code == 200, f"Health failed: {health.text}")
    check(health.json().get("status") == "ok", "Health status is not ok.")
    print("[PASS] GET /api/health")

    # 2. List
    listing = requests.get(f"{BASE_URL}/api/complaints", timeout=TIMEOUT)
    check(listing.status_code == 200, f"GET complaints failed: {listing.text}")
    complaints = listing.json()
    check(isinstance(complaints, list), "Complaint response is not a list.")
    print(f"[PASS] GET /api/complaints ({len(complaints)} records)")

    # 3. Create
    marker = str(uuid.uuid4())[:8]
    payload = {
        "latitude": 23.3441,
        "longitude": 85.3096,
        "media_url": None,
        "description": f"Integration test pothole report {marker} near Main Road.",
    }
    created = requests.post(
        f"{BASE_URL}/api/complaints",
        json=payload,
        timeout=TIMEOUT,
    )
    check(created.status_code == 201, f"POST failed: {created.text}")
    record = created.json()
    complaint_id = record["id"]
    check(record["ai_category"] == "Roads and Potholes", "Category mapping failed.")
    check(record["assigned_department"] == "Public Works Department (PWD)", "Department mapping failed.")
    check(record["status"] == "Pending", "Default status is incorrect.")
    print("[PASS] POST /api/complaints")

    # 4. Get one
    fetched = requests.get(
        f"{BASE_URL}/api/complaints/{complaint_id}",
        timeout=TIMEOUT,
    )
    check(fetched.status_code == 200, f"GET one failed: {fetched.text}")
    check(fetched.json()["id"] == complaint_id, "Returned ID mismatch.")
    print("[PASS] GET /api/complaints/{id}")

    # 5. Patch status + department
    patch = requests.patch(
        f"{BASE_URL}/api/complaints/{complaint_id}",
        json={
            "status": "In Progress",
            "assigned_department": "Public Works Department (PWD)",
        },
        timeout=TIMEOUT,
    )
    check(patch.status_code == 200, f"PATCH failed: {patch.text}")
    patched = patch.json()
    check(patched["status"] == "In Progress", "Status update failed.")
    print("[PASS] PATCH /api/complaints/{id}")

    # 6. Validation
    invalid = requests.patch(
        f"{BASE_URL}/api/complaints/{complaint_id}",
        json={"status": "Not A Real Status"},
        timeout=TIMEOUT,
    )
    check(invalid.status_code == 422, "Invalid status should return 422.")
    print("[PASS] Enum validation returns 422")

    # 7. Missing record
    missing = requests.get(
        f"{BASE_URL}/api/complaints/not-a-real-id",
        timeout=TIMEOUT,
    )
    check(missing.status_code == 404, "Missing complaint should return 404.")
    print("[PASS] Missing complaint returns 404")

    print("=" * 64)
    print("ALL INTEGRATION TESTS PASSED")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except requests.RequestException as exc:
        print(f"\n[FAIL] API connection error: {exc}")
        print("Start the server with: python -m uvicorn main:app")
        raise SystemExit(1)
    except AssertionError as exc:
        print(f"\n[FAIL] {exc}")
        raise SystemExit(1)
