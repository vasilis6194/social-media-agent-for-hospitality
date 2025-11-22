# Hospitality Social Media Agent (Capstone Project)

Multi-agent pipeline that turns a hotel’s Booking.com listing (plus optional website) into ready-to-publish social posts with image-aware captions and hashtags.

---

## 1. The Pitch – Problem, Solution, Value (Category 1)

### 1.1 Problem
- Hotels struggle to produce a steady stream of fresh, on-brand social content.
- Teams manually scan Booking.com listings and photo galleries, then write posts from scratch – this is slow and doesn’t scale.
- Captions often don’t truly reflect what’s in each image (e.g., pool views described like generic rooms), reducing engagement and conversions.

### 1.2 Solution
- An **agentic content factory** for hospitality: given a Booking.com hotel URL (and optional website URL), the system:
  - Scrapes structured text and images from the listing.
  - Enriches context from the hotel’s own site.
  - Uses Gemini Vision and LLMs to understand what’s in each image.
  - Generates tailored captions and hashtags per image, aligned with the property’s brand and offering.
- The output is a clean JSON list of posts that a marketing team or frontend app can publish directly.

### 1.3 Value & Core Concept
- **Core concept:** multi-agent workflow where each agent specializes (scraping, enrichment, image analysis, copywriting) and passes structured state to the next.
- **Value for hospitality teams:**
  - 10x faster content creation for Instagram, Facebook, TikTok, etc.
  - Better visual storytelling: captions are grounded in what’s actually in each image.
  - Consistent tone of voice driven by the Booking.com description and website content.
- Agents are not just a wrapper around a single prompt—they are central to the design and own distinct responsibilities in the pipeline.

---

## 2. Architecture & Agents (Category 2 – Implementation)

### 2.1 High-Level Architecture
- **Root App (`social_media_app` in `main.py` + `main_agent/agent.py`)**
  - Defined with `google.adk.apps.App` and a custom `SequentialAgent` subclass (`SocialMediaPipeline`).
  - Orchestrates the full pipeline as a sequence of sub-agents.
- **Session & State Layer**
  - `DatabaseSessionService` (SQLite via SQLAlchemy) stores session state and events.
  - Sessions are created explicitly in `run_pipeline` and then reused by the ADK `Runner`.
  - Event compaction configured via `EventsCompactionConfig` to keep long sessions performant.
- **Execution Layer**
  - `google.adk.runners.Runner` drives the agents and streams events.
  - OpenTelemetry tracing is enabled; locally logs to stdout, in GCP logs to Cloud Logging & Cloud Trace.
- **API Layer (`server.py`)**
  - FastAPI app exposing a `/generate` endpoint that wraps `run_pipeline` for frontend or external consumers.

### 2.2 Agents and Tools

**Root Pipeline (`main_agent/agent.py`)**
- `SocialMediaPipeline` (subclass of `SequentialAgent`) with sub-agents:
  1. `Booking_Scraper_Agent` (`main_agent/subagents/booking_scraper_agent/agent.py`)
  2. `Website_Scraper_Agent` (`main_agent/subagents/website_scraper_agent/agent.py`)
  3. `Image_Analysis_Agent` (`main_agent/subagents/image_analysis_agent/agent.py`)
  4. `Social_Media_Agent` (`main_agent/subagents/social_media_agent/agent.py`)

**Sub-Agents**
- **Booking_Scraper_Agent**
  - Type: `LlmAgent` using Gemini `gemini-2.5-flash-lite`.
  - Tool: `get_booking_com_data` from `main_agent/tools/tools.py`.
  - Behavior: delegates scraping to a Playwright-based subprocess (`booking_playwright_scraper.py`) to extract:
    - Hotel name, description, canonical URL, and image URLs.
  - Output state: `booking_data`.

- **Website_Scraper_Agent**
  - Type: `LlmAgent` with Gemini.
  - Tool: `google_search` (built-in ADK tool).
  - Behavior: uses search snippets of the hotel’s website (e.g., amenities, “about us”) to enrich context.
  - Output state: `website_data`.

- **Image_Analysis_Agent**
  - Type: `LlmAgent` with Gemini.
  - Tool: `analyze_image_with_vision` from `main_agent/tools/tools.py`.
  - Behavior: iterates over `booking_data.image_urls`, calling Google Cloud Vision for each image to produce descriptive tags.
  - Output state: `analyzed_images` (list of `{image_url, tags}` objects).

- **Social_Media_Agent**
  - Type: `LlmAgent` with Gemini.
  - Inputs from state: `booking_data.description` and `analyzed_images`.
  - Behavior: per image:
    - Generates a 2–3 sentence caption grounded in tags and hotel description.
    - Produces 3–5 hashtags.
  - Output state: `final_posts` (list of `{image_url, caption, hashtags}`).

---

## 3. Technical Implementation & Key Concepts (Category 2 – Technical Implementation)

This project demonstrates multiple key concepts from the course:

1. **Multi-Agent Orchestration**
   - Uses a `SequentialAgent`-based pipeline to structure work into specialized sub-agents.
   - Each agent reads and writes named state keys (e.g., `booking_data`, `website_data`, `analyzed_images`, `final_posts`).

2. **Tool Use & External Integrations**
   - Custom tool `get_booking_com_data`:
     - Wraps a Playwright scraper script (`booking_playwright_scraper.py`) via a subprocess for robust HTML scraping.
   - Custom tool `analyze_image_with_vision`:
     - Calls Google Cloud Vision API to extract labels, objects, and text, then converts them into marketing tags.
   - Built-in tool `google_search`:
     - Used to fetch contextual snippets from the hotel’s website.

3. **Session Management & State Persistence**
   - `DatabaseSessionService` persists session state and events in SQLite (`sessions.db` or `/tmp/sessions.db` in Cloud Run).
   - Explicit session creation in `run_pipeline` ensures the `Runner` can always load the correct session.
   - Event compaction keeps histories manageable over repeated invocations.

4. **Observability & Tracing**
   - OpenTelemetry tracing around the pipeline (`run_pipeline` span).
   - Google Cloud Logging & Cloud Trace integration when running in GCP via `GOOGLE_CLOUD_PROJECT` environment variable.
   - Local fallback to standard logging with structured log messages.

5. **Robust API Contract**
   - Pydantic models in `server.py` define the request and response schema.
   - `run_pipeline` normalizes `final_posts` to a strict Python list (parsing any JSON-string output, stripping ```json fences, and coercing hashtags to lists) to satisfy FastAPI validation.

These choices ensure that agents, tools, sessions, and the API work together in a coherent, production-style architecture.

---

## 4. Project Journey & Design Decisions (Category 1 – Writeup)

- **Start:** The initial idea was a “social media autopilot” for hotels based solely on a Booking.com URL.
- **Iteration on data sources:** Early versions only used the Booking.com description. To increase relevance and brand consistency, a website scraping agent was added using ADK’s `google_search` tool.
- **Image understanding:** To move beyond generic captions, the `Image_Analysis_Agent` and the `analyze_image_with_vision` tool were introduced, ensuring each caption is grounded in actual image content.
- **Reliability and state:** The first runs used in-memory sessions; these failed when the runner expected persisted state. The design was upgraded to `DatabaseSessionService` with explicit session creation, enabling consistent pipeline execution and supporting longer-lived sessions.
- **API & output hardening:** The social media agent sometimes returned JSON as a string with Markdown fences. A normalization step was added in `main.py` so the FastAPI `GenerateResponse` model always receives a valid list of posts.
- **Observability:** Tracing and logging were added early to debug issues like “session not found” and malformed outputs, and to make the system easier to operate in Cloud Run.

This journey reflects a progression from a simple prompt prototype to a robust, multi-agent, tool-using system suitable as a capstone project.

---

## 5. Setup & Local Development (Category 2 – Documentation)

### 5.1 Prerequisites
- Python 3.10+
- A Google Gemini API key (for `gemini-2.5-flash-lite`).
- Google Cloud Vision credentials (service account JSON) if you want to enable image analysis.
- Playwright installed for Booking.com scraping.

### 5.2 Installation
```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 5.3 Environment Variables
Create a `.env` file at the project root (do **not** commit real values):

```bash
GOOGLE_API_KEY=your-gemini-api-key-here           # Gemini / Generative Language API key
GOOGLE_APPLICATION_CREDENTIALS=service-account-key.json  # Vision credentials
GOOGLE_CLOUD_PROJECT=your-gcp-project-id                 # Optional, enables Cloud Logging/Trace
```

### 5.4 Playwright (for Booking.com scraper)
If you plan to use the Playwright-based scraper:
```bash
pip install playwright
playwright install chromium
```

---

## 6. Running the Agent

### 6.1 Start the API Server
From the project root:
```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

### 6.2 Generate Social Media Posts
Send a POST request to the `/generate` endpoint:

```http
POST http://localhost:8000/generate
Content-Type: application/json

{
  "booking_url": "https://www.booking.com/hotel/gr/example.html",
  "website_url": "https://example-hotel.com"
}
```

### 6.3 Sample Output Shape
```json
[
  {
    "image_url": "https://cf.bstatic.com/…/pool.jpg",
    "caption": "Relax by our sea-view infinity pool and enjoy golden sunsets just steps from your room.",
    "hashtags": ["#SeasideEscape", "#InfinityPool", "#GreeceGetaway"]
  }
]
```

### 6.4 Direct CLI Test
You can also run a quick pipeline test without the API:
```bash
python main.py
```
Edit `TEST_URL` in `main.py` to point to a real Booking.com hotel URL first.

---

## 7. Deployment (Optional)

While deployment is not required for grading, this project is designed to run well on **Cloud Run** or similar platforms:

- Uses `/tmp/sessions.db` automatically when `GOOGLE_CLOUD_PROJECT` is set (Cloud Run’s writable directory).
- Stateless application layer (FastAPI + ADK runner); state is persisted in SQLite and can be moved to Cloud SQL or another database by changing the `db_url` in `main.py`.
- OpenTelemetry tracing and Google Cloud Logging integrate automatically when running in a GCP project.

To deploy, you can:
- Build a container using the provided `Dockerfile`.
- Set environment variables for Gemini, Vision, and `GOOGLE_CLOUD_PROJECT` at deploy time.

Documenting the exact deploy command for your environment (e.g., `gcloud run deploy ...`) can be added in your final submission notes.

### 7.1 Current Deployment Used in This Project

- Backend is deployed to Cloud Run as service `hospitality-social-agent` in project `first-agent-472509` (region `europe-west1`).
- The container is built from this repository’s `Dockerfile` and runs with increased resources (e.g. `--memory=2Gi --cpu=2 --concurrency=1`) to support Playwright/Chromium and the multi‑agent pipeline without hitting the default 512 MiB limit.
- The public base URL used by the frontend is:

  `https://hospitality-social-agent-818843143471.europe-west1.run.app`

- The React/Vite frontend under `frontend/` is run locally during development (`npm run dev`) and calls the backend’s `/generate` endpoint as described in section 6.

---

## 8. Effective Use of Gemini (Bonus)

This project uses Gemini in multiple, meaningful ways:

- **Gemini as the core LLM for all agents**
  - Model: `gemini-2.5-flash-lite` with `HttpRetryOptions` configured for robustness.
  - Powers the reasoning of:
    - `Booking_Scraper_Agent` (interpreting and structuring scraped data).
    - `Website_Scraper_Agent` (crafting effective search queries and summarizing snippets).
    - `Image_Analysis_Agent` (orchestrating calls to the Vision tool and structuring tags).
    - `Social_Media_Agent` (writing high-quality, image-aware captions and hashtags).

- **Gemini + Tools**
  - Gemini agents are not standalone; they orchestrate tools (Playwright scraper, Google Search, Cloud Vision) to ground outputs in real data.

This satisfies the “Effective Use of Gemini” bonus by making Gemini central to the agent workflow rather than a simple one-off call.

---

## 9. Safety & Secrets

- No API keys or passwords are checked into the repository.
- All credentials are loaded via environment variables (`.env` locally).
- When extending this project, you should:
  - Validate and sanitize any user-provided URLs.
  - Apply rate limiting and error handling for external APIs (Booking.com, Vision, Gemini).
  - Ensure that service account keys are stored securely (e.g., Secret Manager in production).

---

## 10. Repository Overview

- `main.py` – Entry-point pipeline setup, observability, session service, and `run_pipeline` orchestration.
- `server.py` – FastAPI server exposing the `/generate` endpoint and Pydantic models.
- `main_agent/agent.py` – Root `SocialMediaPipeline` agent definition.
- `main_agent/subagents/*` – Individual agents for scraping, website enrichment, image analysis, and social media copywriting.
- `main_agent/tools/tools.py` – Custom tools for Booking.com scraping and Google Cloud Vision analysis.
- `booking_playwright_scraper.py` – Playwright-based HTML scraper invoked as a subprocess.
- `sessions.db` – Local SQLite database used by `DatabaseSessionService` for session storage.

This README is intended to serve as the primary documentation for the capstone submission, covering the **problem, solution, value, architecture, technical implementation, setup instructions, and Gemini usage**, in line with the provided rubric.
