"""CivicPulse API integration checks. Run with FastAPI already running."""
from __future__ import annotations

import sys
import uuid

import requests

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 20


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    print("CivicPulse API Integration Test")

    health = requests.get(f"{BASE_URL}/api/health", timeout=TIMEOUT)
    check(health.status_code == 200, health.text)
    check(health.json().get("status") == "ok", health.text)
    print("[PASS] health")

    marker = str(uuid.uuid4())[:8]
    payload = {
        "latitude": 23.3441,
        "longitude": 85.3096,
        "media_url": None,
        "description": f"Large pothole on Main Road causing danger to two-wheelers after rain {marker}",
        "voice_transcript": "Large pothole on Main Road causing danger to bikes.",
    }

    analysis = requests.post(f"{BASE_URL}/api/analyze-complaint", json=payload, timeout=TIMEOUT)
    check(analysis.status_code == 200, analysis.text)
    analysis_data = analysis.json()
    check(analysis_data["ai_category"] == "Roads and Potholes", f"Unexpected category: {analysis_data}")
    check(analysis_data.get("estimated_resolution_hours"), "Resolution prediction missing")
    check(analysis_data.get("probable_root_cause"), "Root cause signal missing")
    check(analysis_data.get("recommended_action"), "Recommended action missing")
    print("[PASS] analyze + decision support")

    created = requests.post(f"{BASE_URL}/api/complaints", json=payload, timeout=TIMEOUT)
    check(created.status_code == 201, created.text)
    record = created.json()
    complaint_id = record["id"]
    check(record["status"] == "Pending", "Default status wrong")
    check(record.get("updated_at"), "updated_at missing")
    check(isinstance(record.get("priority_score"), int), "priority_score missing")
    check(record.get("priority_reason"), "priority_reason missing")
    check(record.get("estimated_resolution_hours"), "estimated_resolution_hours missing")
    check(record.get("probable_root_cause"), "probable_root_cause missing")
    check(isinstance(record.get("progress_updates"), list) and record["progress_updates"], "progress_updates missing")
    print("[PASS] create + operational intelligence")

    progress_patch = requests.patch(
        f"{BASE_URL}/api/complaints/{complaint_id}",
        json={"progress_message": "Crew scheduled to inspect the road section tomorrow morning."},
        timeout=TIMEOUT,
    )
    check(progress_patch.status_code == 200, progress_patch.text)
    progress_data = progress_patch.json()
    check(any("Crew scheduled" in item["message"] for item in progress_data["progress_updates"]), "Admin progress message not stored")
    print("[PASS] admin progress communication")

    for status in ["Acknowledged", "In Progress", "Resolved"]:
        response = requests.patch(
            f"{BASE_URL}/api/complaints/{complaint_id}",
            json={"status": status},
            timeout=TIMEOUT,
        )
        check(response.status_code == 200, response.text)
        data = response.json()
        check(data["status"] == status, f"Status did not become {status}")
        check(data.get("progress_updates"), "Workflow notification missing")
        print(f"[PASS] patch {status}")

    final = requests.get(f"{BASE_URL}/api/complaints/{complaint_id}", timeout=TIMEOUT)
    check(final.status_code == 200, final.text)
    final_data = final.json()
    check(final_data["acknowledged_at"], "acknowledged_at missing")
    check(final_data["in_progress_at"], "in_progress_at missing")
    check(final_data["resolved_at"], "resolved_at missing")
    check(final_data["updated_at"], "updated_at missing")
    check(final_data["status"] == "Resolved", "Final status wrong")
    print("[PASS] lifecycle timestamps")

    verification = requests.post(f"{BASE_URL}/api/complaints/{complaint_id}/verify", timeout=TIMEOUT)
    check(verification.status_code == 200, verification.text)
    verification_data = verification.json()
    check(verification_data["verification_count"] == 1, "Verification count did not increment")
    check("priority_score" in verification_data, "Priority was not recalculated")
    print("[PASS] community verification + priority recalculation")

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
        sys.exit(1)
