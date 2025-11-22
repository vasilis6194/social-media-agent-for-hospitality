# Hospitality Social Media Agent (Capstone Project)

Track: **Concierge Agents** – AI agents for hospitality and customer experience.  
Course: **5‑Day AI Agents Intensive with Google (Nov 10–14, 2025)** – Capstone project.

Multi‑agent pipeline that turns a hotel’s Booking.com listing (plus optional website) into ready‑to‑publish social posts with image‑aware captions and hashtags. The system is deployed as a Cloud Run backend with a Vite/React frontend for interactive use.

---

## 1. The Pitch – Problem, Solution, Value

### 1.1 Problem
- Hotels need a constant stream of fresh, on‑brand social content across channels.
- Marketing teams manually read Booking.com listings and the hotel’s own site, scan photos, and write captions/hashtags from scratch.
- This is slow, doesn’t scale, and often produces generic content that doesn’t match the images (e.g., “cozy room” for a pool photo).

### 1.2 Solution
- An **agentic social media content concierge** for hotels:
  - Input: Booking.com hotel URL (+ optional hotel website URL).
  - Agents scrape structured text and images, enrich context from the hotel’s site, analyze each image with Vision, and generate tailored captions + hashtags per image using Gemini.
  - Output: a clean JSON list of posts, consumed by a React UI or downstream workflows.

### 1.3 Value
- 10x faster content creation for social platforms.
- Captions are grounded in actual image content and hotel amenities.
- Consistent brand voice anchored in Booking.com descriptions and website copy.

---

## 2. Architecture & Agents

### 2.1 High‑Level Architecture
- **Root App (`social_media_app` in `main.py` + `main_agent/agent.py`)**
  - Uses `google.adk.apps.App` with a custom `SequentialAgent` subclass (`SocialMediaPipeline`) as the root agent.
  - Orchestrates the full pipeline as four sub‑agents.

- **Session & State Layer**
  - Primary: `DatabaseSessionService` (SQLite) for persistent sessions/events.
  - Fallback: `InMemorySessionService` if DB initialization fails.
  - `EventsCompactionConfig` for event compaction in long‑running sessions.

- **Execution & API**
  - `google.adk.runners.Runner` drives the root agent and streams events.
  - FastAPI (`server.py`) exposes:
    - `GET /` – health check.
    - `POST /generate` – triggers `run_pipeline` and returns posts.

- **Frontend (`frontend/`)**
  - Vite/React/Tailwind app for marketers.
  - Calls `POST /generate` and renders a grid of image cards (caption, hashtags, copy button).

### 2.2 Agents and Tools

**Root pipeline (`main_agent/agent.py`)**

- `SocialMediaPipeline` (`SequentialAgent`) with sub‑agents:
  1. `Booking_Scraper_Agent`
  2. `Website_Scraper_Agent`
  3. `Image_Analysis_Agent`
  4. `Social_Media_Agent`

**Sub‑Agents**

- **Booking_Scraper_Agent**
  - Type: `LlmAgent` using Gemini `gemini-2.5-flash-lite`.
  - Tool: `get_booking_com_data` (custom) from `main_agent/tools/tools.py`.
  - Implementation: wraps `booking_playwright_scraper.py` (Playwright) via subprocess to extract hotel description, canonical URL, and image URLs.
  - State key: `booking_data`.

- **Website_Scraper_Agent**
  - Type: `LlmAgent` with Gemini.
  - Tool: built‑in `google_search`.
  - Implementation: uses queries like `site:hotel.com amenities` / `site:hotel.com "about us"` to enrich context.
  - State key: `website_data`.

- **Image_Analysis_Agent**
  - Type: `LlmAgent` with Gemini.
  - Tool: `analyze_image_with_vision` (custom) using Google Cloud Vision.
  - Implementation: iterates `booking_data.image_urls`, collects labels/objects/text into marketing‑friendly tags.
  - State key: `analyzed_images` (list of `{image_url, tags}`).

- **Social_Media_Agent**
  - Type: `LlmAgent` with Gemini.
  - Inputs: `booking_data.description` + `analyzed_images`.
  - Implementation: per image, writes a 2–3 sentence caption grounded in tags and hotel description, plus 3–5 hashtags.
  - State key: `final_posts` (list of `{image_url, caption, hashtags}`).

---

## 3. Key Concepts Applied (Capstone “Features To Include”)

This project demonstrates several of the required concepts:

1. **Multi‑agent system (Sequential agents + LLM agents)**  
   - Root `SequentialAgent` pipeline (`SocialMediaPipeline`) with four specialized Gemini‑powered agents.

2. **Tools (custom tools + built‑in tools)**  
   - Custom `get_booking_com_data` tool (Playwright scraper).  
   - Custom `analyze_image_with_vision` tool (Cloud Vision).  
   - Built‑in `google_search` tool for website context.

3. **Sessions & Memory / Context engineering**  
   - `DatabaseSessionService` (SQLite) with fallback to `InMemorySessionService`.  
   - `EventsCompactionConfig` for basic context compaction.  
   - Explicit session creation in `run_pipeline` so `Runner` always finds a session and aggregated state.

4. **Observability: logging & tracing**  
   - OpenTelemetry tracing around `run_pipeline`.  
   - Google Cloud Logging + Cloud Trace when `GOOGLE_CLOUD_PROJECT` is set.  
   - Local structured logging to stdout as fallback.

5. **Agent deployment (Cloud Run)**  
   - Containerized via `Dockerfile` and deployed as a Cloud Run service with increased resources (`--memory=2Gi --cpu=2 --concurrency=1`) to support Playwright/Chromium and the agents.

6. **Robust API contract**  
   - Pydantic models in `server.py` define request/response for `/generate`.  
   - `run_pipeline` normalizes `final_posts` to a strict Python list (parsing any JSON‑string from the LLM, stripping ```json fences, coercing hashtags to lists) so the API and frontend always receive valid data.

---

## 4. Project Journey & Design Decisions

- Started as a simple “Booking.com URL → single caption” experiment.
- Added website scraping via `google_search` to incorporate brand voice and amenities.
- Introduced `Image_Analysis_Agent` + Vision to avoid generic captions and ground each post in image content.
- Upgraded from in‑memory sessions to `DatabaseSessionService` plus explicit session creation so the runner always finds a session history.
- Added normalization logic for `final_posts` when the LLM returns JSON wrapped in Markdown fences.
- Deployed to Cloud Run; increased memory/CPU after hitting default 512 MiB limits due to Playwright/Chromium.
- Built a React UI to make the pipeline tangible for marketers and judges instead of only inspecting JSON.

---

## 5. Setup & Local Development

### 5.1 Prerequisites
- Python 3.10+
- Node.js (for the frontend)
- A Gemini API key (`GOOGLE_API_KEY`).
- Google Cloud Vision credentials (service‑account JSON) if image analysis is enabled.
- Playwright installed for Booking.com scraping.

### 5.2 Backend Installation
```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 5.3 Backend Environment Variables
Create a `.env` file (do **not** commit real values):

```bash
GOOGLE_API_KEY=your-gemini-api-key-here
GOOGLE_APPLICATION_CREDENTIALS=service-account-key.json
GOOGLE_CLOUD_PROJECT=your-gcp-project-id        # optional, enables Cloud Logging/Trace
```

### 5.4 Playwright (for Booking.com scraper)
```bash
pip install playwright
playwright install chromium
```

### 5.5 Frontend Installation
```bash
cd frontend
npm install
```

---

## 6. Running Locally

### 6.1 Start the API Server
From the project root:
```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

### 6.2 Test the API
```http
POST http://localhost:8000/generate
Content-Type: application/json

{
  "booking_url": "https://www.booking.com/hotel/gr/example.html",
  "website_url": "https://example-hotel.com"
}
```

Example response shape:
```json
[
  {
    "image_url": "https://cf.bstatic.com/.../pool.jpg",
    "caption": "Relax by our sea-view infinity pool and enjoy golden sunsets just steps from your room.",
    "hashtags": ["#SeasideEscape", "#InfinityPool", "#GreeceGetaway"]
  }
]
```

### 6.3 Direct CLI Test
```bash
python main.py
```
Edit `TEST_URL` in `main.py` to point to a real Booking.com hotel URL.

### 6.4 Frontend (local dev)

The frontend reads the backend base URL from a Vite env var defined in `frontend/.env.local`:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

For development against a deployed Cloud Run backend, set `VITE_API_BASE_URL` to **your** Cloud Run service URL (for example `https://<your-service>-<hash>.<region>.run.app`).  
Then run:

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173` to use the UI.

---

## 7. Deployment (Cloud Run)

### 7.1 General Cloud Run Design

While deployment is not required for grading, this project is designed to run well on **Cloud Run** or similar platforms:

- Uses `/tmp/sessions.db` automatically when `GOOGLE_CLOUD_PROJECT` is set (Cloud Run’s writable directory).
- Stateless application layer (FastAPI + ADK runner); state is persisted in SQLite and can be migrated to Cloud SQL by changing `db_url` in `main.py`.
- OpenTelemetry tracing and Google Cloud Logging integrate automatically in GCP.

Typical deployment flow (from Cloud Shell) looks like:

```bash
REGION=<your-region>        # e.g. europe-west1
PROJECT_ID=<your-project-id>
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/hospitality/hospitality-agent:vX"

gcloud builds submit --tag "$IMAGE" .

gcloud run deploy hospitality-social-agent \
  --image "$IMAGE" \
  --platform managed \
  --region "$REGION" \
  --set-env-vars=GOOGLE_API_KEY=YOUR_GEMINI_API_KEY \
  --memory=2Gi \
  --cpu=2 \
  --concurrency=1
```

The actual Cloud Run URL is environment‑specific and should be configured in the frontend via `VITE_API_BASE_URL` rather than hard‑coded in the repo.

---

## 8. Effective Use of Gemini (Bonus)

- All LLM agents use `gemini-2.5-flash-lite` with retry options configured via `HttpRetryOptions`.
- Gemini is used not only for direct text generation, but also to orchestrate tools (Playwright scraper, Google Search, Cloud Vision) and summarize their outputs.

This satisfies the “Effective Use of Gemini” bonus by making Gemini central to the multi‑agent workflow rather than a single isolated call.

---

## 9. Safety & Secrets

- No API keys or passwords are checked into the repository.
- All credentials are read from environment variables (`.env` locally, Cloud Run env vars in production).
- When extending this project:
  - Validate and sanitize user‑provided URLs.
  - Add rate limiting and error handling for external APIs (Booking.com, Vision, Gemini).
  - Store service‑account keys securely (e.g., Secret Manager in production).

---

## 10. Repository Overview

- `main.py` – Pipeline setup, observability, session service, `run_pipeline` orchestration.
- `server.py` – FastAPI server exposing `/` and `/generate` endpoints.
- `main_agent/agent.py` – Root `SocialMediaPipeline` agent definition.
- `main_agent/subagents/*` – Agents for Booking.com scraping, website enrichment, image analysis, and social media copywriting.
- `main_agent/tools/tools.py` – Custom tools for Booking.com scraping and Google Cloud Vision.
- `booking_playwright_scraper.py` – Playwright‑based HTML scraper invoked as a subprocess.
- `frontend/` – Vite/React/Tailwind frontend that calls `POST /generate` and renders posts.
- `sessions.db` – Local SQLite DB used by `DatabaseSessionService` (Cloud Run uses `/tmp/sessions.db`).

This README is the main documentation for the capstone submission, covering the **problem, solution, architecture, applied concepts, setup, deployment, and Gemini usage** in line with the course rubric.

