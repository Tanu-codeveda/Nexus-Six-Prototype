# CivicPulse AI

**CivicPulse AI** is an intelligent civic issue reporting and resolution platform developed by **Team Nexus Six** for the **Smart VIT Hackathon 2026**.

It addresses **SVH26005 — Crowdsourced Civic Issue Reporting and Resolution System** under the **Clean and Green Technology** theme for the **Government of Jharkhand, Department of Higher and Technical Education**.

## Overview

CivicPulse connects a citizen-facing reporting application with an administrative operations dashboard and an AI-assisted processing pipeline.

Citizens can report civic issues using GPS/location, written descriptions, photographs, and short voice notes. The platform processes reports, assigns categories, severity and departments, stores the complaint lifecycle, and exposes the information through an interactive operations dashboard with map, queue, filtering, tracking and analytics.

## Key Features

### Citizen App

- Mobile-first civic issue reporting
- Automatic GPS/location capture
- Photo capture/upload
- Voice-note recording with a 5-second limit
- Hindi/English speech transcription through the backend
- Written complaint description
- AI-assisted category and severity analysis
- Department assignment
- Complaint confirmation
- Complaint tracking
- My Reports history
- Community verification for nearby reports

### CivicPulse Ops — Admin Dashboard

- Live complaint queue
- Interactive Leaflet map centred on Ranchi, Jharkhand
- Category, severity, status, department and search filters
- Complaint detail view
- Department assignment
- Status lifecycle management:
  `Pending → Acknowledged → In Progress → Resolved`
- Priority/hotspot visualization
- Duplicate-report indicators
- Reporting analytics
- Response-time and resolution insights

## AI Pipeline

The prototype combines multiple AI and processing components:

- **Computer Vision:** OpenCV + Ultralytics/YOLO
- **Voice:** Local Whisper-based transcription
- **NLP:** Text processing and civic category/department mapping
- **Priority & Routing:** Prototype decision logic based on complaint context
- **Integration:** FastAPI connects the citizen UI, AI components, database and admin dashboard

> **Prototype disclaimer:** This is a hackathon prototype. The current AI pipeline uses lightweight/pre-trained components and prototype-level decision logic; it is not a production-trained municipal AI system.

## Technology Stack

### Backend

- Python
- FastAPI
- Uvicorn
- SQLAlchemy
- SQLite
- Pydantic
- Requests

### AI / Data

- OpenCV
- Ultralytics / YOLO
- Whisper
- spaCy
- Transformers
- Faker

### Frontend

- React
- Vite
- JavaScript / JSX
- CSS
- Leaflet / OpenStreetMap

## Project Structure

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

Recommended environment:

- Python 3.10+
- Node.js 18+
- npm
- Git
- FFmpeg available on the system `PATH`
- The YOLO model file used by the prototype, such as `yolo11n.pt`

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Tanu-codeveda/Nexus-Six-Prototype.git
cd Nexus-Six-Prototype
```

### 2. Create and activate a Python virtual environment

#### Windows / Git Bash

```bash
python -m venv .venv
source .venv/Scripts/activate
```

If `source` is unavailable:

```bash
.venv\\Scripts\\activate
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

## Running the Project

CivicPulse has two user interfaces backed by the same FastAPI API:

1. **Admin / Operations Dashboard**
2. **Citizen React App**

### Terminal 1 — Start the FastAPI backend

From the project root:

```bash
python -m uvicorn main:app --reload
```

Backend:

```text
http://127.0.0.1:8000
```

Useful URLs:

```text
http://127.0.0.1:8000/
http://127.0.0.1:8000/api/health
http://127.0.0.1:8000/docs
```

`/docs` provides interactive FastAPI API documentation.

### Terminal 2 — Run the Citizen React App

Open another terminal:

```bash
cd civicpulse-frontend
npm install
npm run dev
```

Vite will normally serve the app at:

```text
http://localhost:5173
```

Open that address in the browser.

For the complete citizen workflow, allow browser permissions for:

- Location
- Camera
- Microphone

### Admin Dashboard

Once the FastAPI backend is running, open:

```text
http://127.0.0.1:8000/
```

The admin dashboard reads complaint data from the backend and provides the map, filters, queue, status updates and analytics.

## Populate Demo Data

For a hackathon demonstration, the repository includes a Faker-based complaint seeder.

Start the backend first:

```bash
python -m uvicorn main:app --reload
```

Then, from another terminal in the project root:

```bash
python seed_data.py
```

The default command generates **50 demo complaints around Ranchi, Jharkhand**.

Custom count:

```bash
python seed_data.py --count 100
```

Custom API URL:

```bash
python seed_data.py --base-url http://127.0.0.1:8000
```

After seeding, refresh the admin dashboard.

## Integration Testing

Start the backend:

```bash
python -m uvicorn main:app --reload
```

Then, from the project root in a second terminal:

```bash
python test_integration.py
```

The integration tests cover the core API flow, including:

- Health check
- Complaint listing
- Complaint creation
- Fetching an individual complaint
- Complaint updates

## API Overview

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | API health check |
| `POST` | `/api/complaints` | Create a complaint |
| `GET` | `/api/complaints` | List complaints |
| `GET` | `/api/complaints/{id}` | Get one complaint |
| `PATCH` | `/api/complaints/{id}` | Update status/department |
| `POST` | `/api/transcribe-audio` | Transcribe voice input |
| `POST` | `/api/analyze-complaint` | Run complaint analysis |

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

## Demo Data Coverage

The included seeder uses **Ranchi, Jharkhand** as its centre and generates reports around areas such as:

- Main Road
- Harmu
- Lalpur
- Doranda
- Morabadi
- Kanke Road
- Booty More
- Ashok Nagar
- Argora
- Ratu Road
- Hinoo
- Kokar
- Kadru
- Bariatu
- Namkum

## End-to-End Architecture

```text
               ┌──────────────────────┐
               │    Citizen App       │
               │       React          │
               └──────────┬───────────┘
                          │
               GPS / Photo / Voice / Text
                          │
                          ▼
               ┌──────────────────────┐
               │     FastAPI API      │
               └──────────┬───────────┘
                          │
           ┌──────────────┼──────────────┐
           │              │              │
           ▼              ▼              ▼
      Computer        Whisper/NLP    Priority &
       Vision            AI           Routing
           │              │              │
           └──────────────┼──────────────┘
                          ▼
                   ┌──────────────┐
                   │ SQLAlchemy + │
                   │    SQLite    │
                   └──────┬───────┘
                          │
                          ▼
               ┌──────────────────────┐
               │  CivicPulse Ops      │
               │  Admin Dashboard     │
               └──────────┬───────────┘
                          │
               ┌──────────┼──────────┐
               ▼          ▼          ▼
              Map       Queue     Analytics
                          │
                          ▼
                 Department + Status
                      Updates
                          │
                          ▼
                   Citizen Tracking
```

## Troubleshooting

### Python module is missing

Make sure the virtual environment is activated:

```bash
.venv\\Scripts\\activate
```

Then reinstall:

```bash
pip install -r requirements.txt
```

### Frontend cannot connect to the API

Make sure the FastAPI server is running:

```bash
python -m uvicorn main:app --reload
```

Then reload the React app.

### Voice transcription is not working

Check:

```bash
ffmpeg -version
```

Also verify that the Python AI dependencies from `requirements.txt` are installed.

### Camera, microphone or location does not work

Allow the browser to use:

- Camera
- Microphone
- Location

### Dashboard has no demo complaints

Run:

```bash
python seed_data.py --count 50
```

Then refresh:

```text
http://127.0.0.1:8000/
```

## Recommended Hackathon Demo Flow

```text
1. Start FastAPI
       ↓
2. Seed 50 Ranchi complaints
       ↓
3. Open CivicPulse Ops dashboard
       ↓
4. Show live map + queue + analytics
       ↓
5. Open the Citizen React App
       ↓
6. Submit a report using text/photo/voice/GPS
       ↓
7. Show AI analysis + department assignment
       ↓
8. Return to Admin Dashboard
       ↓
9. Update complaint status
       ↓
10. Show the updated citizen tracking state
```

## Team

### Team Nexus Six

**Hackathon:** Smart VIT Hackathon 2026  
**Problem Statement:** SVH26005  
**Problem:** Crowdsourced Civic Issue Reporting and Resolution System  
**Theme:** Clean and Green Technology  
**Organization:** Government of Jharkhand — Department of Higher and Technical Education

## Production Considerations

This repository represents a hackathon prototype. A production civic deployment would require, among other things:

- Stronger validation of AI models on civic-domain datasets
- Secure authentication and authorization
- Production-grade media storage
- A production database
- Monitoring and observability
- Rate limiting
- Privacy controls
- Deployment hardening
