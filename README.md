# CivicPulse AI

**CivicPulse AI** is an intelligent civic issue reporting and resolution platform developed by **Team Nexus Six** for the **Smart VIT Hackathon 2026**.

It addresses **SVH26005 — Crowdsourced Civic Issue Reporting and Resolution System** under the **Clean and Green Technology** theme for the **Government of Jharkhand, Department of Higher and Technical Education**.

## What the prototype does

CivicPulse connects a citizen-facing reporting application with a municipal operations dashboard and an AI-assisted processing pipeline.

Citizens can report an issue with:

- GPS/location
- Written description
- Photo evidence
- A short voice note (maximum 5 seconds)

The backend then performs AI-assisted analysis, routes the report to a department, calculates operational priority, detects likely duplicate reports, estimates a service window, generates a probable contributing-factor insight, and stores a citizen-facing progress feed.

The operations dashboard shows the same data on a live map with a density heatmap, queue, filters, priority scores and analytics.

## Main features

### Citizen app

- Mobile-first issue reporting
- Automatic GPS capture with Ranchi fallback for demo use
- Camera/photo capture
- 5-second voice recording
- Local Whisper speech transcription
- Separate written description and voice transcript
- AI-assisted category and severity classification
- Automatic department routing
- Transparent operational priority score
- Service-time prediction using severity, category, historical resolutions and department workload
- Probable root-cause / contributing-factor insight
- Recommended municipal action
- Complaint confirmation and tracking
- Live status polling
- In-app progress notifications
- Community verification
- My Reports history

### CivicPulse Ops dashboard

- Real backend-backed complaint queue
- Leaflet/OpenStreetMap issue map centred on Ranchi
- Severity-coded complaint markers
- Toggleable complaint-density heatmap
- Automatic hotspot detection
- Category, severity, status and department filters
- Search across complaint and intelligence fields
- Transparent priority score and explanation
- Possible duplicate report indicators
- Complaint detail and submitted photo
- Department assignment
- Status lifecycle:
  `Pending → Acknowledged → In Progress → Resolved`
- Citizen-facing progress feed
- Admin progress message publishing
- Response-time analytics
- Resolution-rate analytics
- Predicted resolution-time metric
- CSV export


### IoT / Infrastructure Intelligence

- Predictive waste-bin overflow monitoring using synthetic historical telemetry and XGBoost
- OpenCV-based streetlight illumination monitoring with night-hours guard
- Drain/flood detection from configured camera zones with optional OpenWeather rainfall context
- Dedicated pothole detection path using the existing VisionAnalyzer
- IoT-generated complaints are stored in the same Complaint model and appear in the normal admin queue
- Background bin health checks and SLA escalation jobs are configurable with `CIVICPULSE_ENABLE_BACKGROUND_JOBS=0|1`

## AI / decision-support pipeline

```text
Citizen Report
(GPS + Text + Voice + Photo)
          |
          v
     FastAPI API
          |
   +------+------+----------------+
   |             |                |
   v             v                v
Whisper      NLP / Routing   Computer Vision
   |             |                |
   +-------------+----------------+
                 |
                 v
       Complaint Intelligence
                 |
      +----------+----------+
      |          |          |
      v          v          v
   Priority   Duplicate   Root Cause
    Score      Signals     Insight
      |
      v
 Resolution-time Prediction
      |
      v
 Department + Status + Progress
      |
      v
 Admin Dashboard <----> Citizen Tracking
```

### Important prototype limitation

The current AI stack uses lightweight/pre-trained components and transparent prototype decision logic. The generic YOLO model is **not** a civic-domain model trained specifically for potholes, streetlights or municipal infrastructure, so CV output should be treated as a prototype signal rather than a production-grade damage assessment.

## Technology stack

### Backend

- Python
- FastAPI
- Uvicorn
- SQLAlchemy
- SQLite
- Pydantic

### AI / data

- OpenCV
- Ultralytics / YOLO
- Whisper
- spaCy
- Transformers / BART zero-shot classification
- Faker

### Frontend

- React
- Vite
- JavaScript / JSX
- CSS
- Leaflet / OpenStreetMap
- Leaflet.heat
- Chart.js

## Project structure

```text
Nexus-Six-Prototype/
│
├── main.py
├── database.py
├── models.py
├── schemas.py
├── ai_helpers.py
├── vision_analyzer.py
├── nlp_processor.py
├── seed_data.py
├── repair_demo_timestamps.py
├── test_integration.py
├── requirements.txt
├── README.md
│
├── index.html
├── style.css
└── js/
    ├── app.js
    ├── api.js
    ├── config.js
    ├── map.js
    ├── table.js
    └── analytics.js
│
└── civicpulse-frontend/
    ├── package.json
    ├── package-lock.json
    ├── index.html
    └── src/
        ├── App.jsx
        ├── main.jsx
        └── styles.css
```

## Requirements

Recommended:

- Python 3.10+
- Node.js 20.19+ (or Node.js 22.12+)
- npm
- Git
- FFmpeg on `PATH`
- Internet access on the first run for model/CDN resources
- `yolo11n.pt` for the current YOLO prototype

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Tanu-codeveda/Nexus-Six-Prototype.git
cd Nexus-Six-Prototype
```

### 2. Create a Python virtual environment

#### Windows / Git Bash

```bash
python -m venv .venv
source .venv/Scripts/activate
```

Alternative:

```bash
.venv\Scripts\activate
```

#### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Python dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Verify FFmpeg:

```bash
ffmpeg -version
```

## Run the project

CivicPulse uses one FastAPI backend for both the operations dashboard and the React citizen app.

### Terminal 1 — FastAPI backend

From the project root:

```bash
python -m uvicorn main:app --reload
```

Admin dashboard:

```text
http://127.0.0.1:8000/
```

API health:

```text
http://127.0.0.1:8000/api/health
```

Swagger API docs:

```text
http://127.0.0.1:8000/docs
```

### Terminal 2 — Citizen app

```bash
cd civicpulse-frontend
npm install
npm run dev
```

Vite will normally show:

```text
http://localhost:5173/
```

Allow browser permissions for:

- Location
- Camera
- Microphone

## Populate demo complaints

The project includes a Faker-based Ranchi demo seeder.

Start the backend first, then from a second terminal in the project root:

```bash
python seed_data.py --count 50
```

The default dataset is clustered around Ranchi areas such as Main Road, Harmu, Lalpur, Doranda, Morabadi, Kanke Road, Hinoo and other localities.

After seeding, refresh the admin dashboard.

## Demo flow

A strong end-to-end demonstration is:

```text
1. Start FastAPI
2. Seed 50 Ranchi complaints
3. Open CivicPulse Ops
4. Show map + heatmap + queue + analytics
5. Open the Citizen React app
6. Capture GPS
7. Enter a complaint such as:
   "Large pothole on Main Road causing danger to two-wheelers after rain."
8. Add a photo
9. Record the short voice note
10. Run AI analysis
11. Show category + severity + department
12. Show priority + duplicate signal + root-cause insight
13. Submit the complaint
14. Open tracking
15. In Ops, acknowledge / start work / resolve it
16. Publish a progress message
17. Show the live citizen notification and updated timeline
18. Confirm the issue using community verification
```

## Example API test payload

```json
{
  "latitude": 23.3441,
  "longitude": 85.3096,
  "media_url": null,
  "description": "Large pothole on Main Road causing danger to two-wheelers after rain.",
  "voice_transcript": "Large pothole on Main Road causing danger to bikes."
}
```

Send it to:

```text
POST /api/analyze-complaint
```

or create a real complaint with:

```text
POST /api/complaints
```

## Integration testing

With FastAPI running:

```bash
python test_integration.py
```

The integration checks cover:

- API health
- AI analysis and category routing
- complaint creation
- priority and decision-support fields
- admin progress-message publishing
- status lifecycle timestamps
- citizen-facing progress events
- community verification and priority recalculation
- request validation

## API overview

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | API health check |
| `POST` | `/api/analyze-complaint` | Run AI/decision-support analysis without creating a record |
| `POST` | `/api/complaints` | Create a complaint |
| `GET` | `/api/complaints` | List complaints with intelligence fields |
| `GET` | `/api/complaints/{id}` | Get one complaint and its progress feed |
| `PATCH` | `/api/complaints/{id}` | Update status, department and progress message |
| `POST` | `/api/complaints/{id}/verify` | Record community confirmation and recalculate priority |
| `POST` | `/api/transcribe-audio` | Transcribe voice input |

## Decision-support details

### Dynamic priority

The priority score combines:

- Severity
- Nearby active-report density
- Likely duplicate reports
- Community confirmations
- Age of unresolved complaints
- Public-safety category weighting

The API also returns a human-readable `priority_reason` so the dashboard can explain the score instead of showing a black-box number.

### Duplicate detection

Likely duplicates are identified using a small geospatial radius plus category and text-context similarity. This is intentionally lightweight and intended for demo-scale data.

### Resolution-time prediction

The service window uses historical resolved complaints where enough history exists, then adjusts for severity and the current open workload of the assigned department. With limited history, it falls back to a transparent category/severity baseline.

### Root-cause insight

The prototype derives a probable contributing factor from the issue category and report context, for example drainage-related deterioration for a rain-linked pothole report. It also exposes supporting signals and a recommended municipal action.

### Citizen notifications

Notifications are implemented as an in-app progress feed tied to the backend record. Status changes, department assignments, community confirmations and admin-written progress messages are stored as timestamped events. This is a prototype notification mechanism; push/SMS/email delivery is a future deployment layer.

## Troubleshooting

### `vite` is not recognized

Run:

```bash
cd civicpulse-frontend
npm install
npm run dev
```

`node_modules` is intentionally excluded from Git and must be recreated per machine.

### Frontend cannot reach the API

Make sure the backend is running:

```bash
python -m uvicorn main:app --reload
```

Then reload the React app.

### Voice transcription fails

Check:

```bash
ffmpeg -version
```

Also make sure the Python AI dependencies are installed and the local Whisper model can load.

### Camera / microphone / GPS fails

Allow browser permissions and retry. When browser GPS is unavailable, the citizen demo falls back to Ranchi coordinates.

### Model downloads appear on first startup

The first startup may download the YOLO and Hugging Face model resources. Subsequent runs should use the local model cache where available.

## Current prototype boundary

This repository is a functional hackathon prototype, not a production municipal platform. Production deployment would additionally require stronger civic-domain model validation, authentication/authorization, secure media storage, a production database, monitoring, rate limiting, privacy controls, push/SMS/email notification infrastructure and deployment hardening.

### Privacy-preserving report tracking

Each citizen report receives a random pseudonymous tracking token (`CP-XXXXXXXXXX`). The token is returned by the API and shown on the citizen submission/tracking screens, allowing a report to be referenced without storing a citizen name, email or phone number on the complaint.

## Team Nexus Six

**Hackathon:** Smart VIT Hackathon 2026
**Problem Statement:** SVH26005
**Problem:** Crowdsourced Civic Issue Reporting and Resolution System
**Theme:** Clean and Green Technology
**Team ID:** svh-10125
**Organization:** Government of Jharkhand — Department of Higher and Technical Education
