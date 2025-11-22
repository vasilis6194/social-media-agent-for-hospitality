import os
import sys
import asyncio
import logging
import json

from dotenv import load_dotenv

# --- Observability Imports ---
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Try importing Google Cloud libraries (fails gracefully if not installed / usable)
try:
    import google.cloud.logging
    from google.cloud.logging.handlers import CloudLoggingHandler
    from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
    HAS_GOOGLE_CLOUD = True
except ImportError:
    HAS_GOOGLE_CLOUD = False

load_dotenv()

from google.adk.apps.app import App, EventsCompactionConfig
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService, InMemorySessionService
from google.genai import types


# --- 1. Import the Root Agent ---
try:
    from main_agent.agent import root_agent
    print("Successfully imported root_agent from main_agent/agent.py")
except ImportError as e:
    print(f"Error: Could not import root_agent: {e}")
    sys.exit(1)


# --- 2. Configure Observability ---
def setup_observability() -> None:
    """Configures logging and tracing based on environment."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Configure OpenTelemetry tracer provider
    trace.set_tracer_provider(TracerProvider())

    # In Cloud Run, GOOGLE_CLOUD_PROJECT is set
    if HAS_GOOGLE_CLOUD and os.environ.get("GOOGLE_CLOUD_PROJECT"):
        try:
            # Cloud Logging
            client = google.cloud.logging.Client()
            handler = CloudLoggingHandler(client)
            logger.addHandler(handler)
            logging.info("Google Cloud Logging: ENABLED")

            # Cloud Trace
            exporter = CloudTraceSpanExporter()
            trace.get_tracer_provider().add_span_processor(
                BatchSpanProcessor(exporter)
            )
            logging.info("Google Cloud Trace: ENABLED")
            return
        except Exception as e:
            # Never fail startup because of logging/tracing config
            logging.warning(
                "Failed to initialize Google Cloud logging/trace; "
                "falling back to standard logging. Error: %s",
                e,
            )

    # Local / fallback logging
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logging.info("Local logging: ENABLED (trace export skipped)")


# Initialize Observability immediately on import
setup_observability()


# --- 3. Configure the ADK Application ---
compaction_config = EventsCompactionConfig(
    compaction_interval=2,
    overlap_size=1,
)

social_media_app = App(
    name="social_media_factory",
    root_agent=root_agent,
    events_compaction_config=compaction_config,
)


# --- 4. Configure the Runner and Session ---
# Use /tmp/sessions.db in Cloud Run (because only /tmp is writable)
# Locally, use sessions.db
db_path = (
    "/tmp/sessions.db"
    if os.environ.get("GOOGLE_CLOUD_PROJECT")
    else "sessions.db"
)
db_url = f"sqlite:///{db_path}"

try:
    logging.info("Initializing DatabaseSessionService with URL %s", db_url)
    session_service = DatabaseSessionService(db_url=db_url)
except Exception as e:
    logging.warning(
        "Failed to initialize DatabaseSessionService (%s). "
        "Falling back to InMemorySessionService.",
        e,
    )
    session_service = InMemorySessionService()

runner = Runner(
    app=social_media_app,
    session_service=session_service,
)


# --- Helpers ---
def _normalize_final_posts(final_posts):
    """Convert model output into a Python list for API consumption."""
    if final_posts is None:
        return None

    if isinstance(final_posts, list):
        # Normalize hashtags field in each item
        normalized = []
        for item in final_posts:
            if not isinstance(item, dict):
                continue
            hashtags = item.get("hashtags")
            if isinstance(hashtags, str):
                hashtags = [tag for tag in hashtags.split() if tag]
            item["hashtags"] = hashtags if isinstance(hashtags, list) else []
            normalized.append(item)
        return normalized or None

    if isinstance(final_posts, str):
        content = final_posts.strip()

        # Strip common ```json fences if present
        if content.startswith("```"):
            lines = content.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        # Fallback: if we still have junk around, grab the first JSON-like chunk
        if "[" in content and "]" in content:
            content = content[content.find("[") : content.rfind("]") + 1]

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            logging.error("Failed to parse final_posts JSON: %s", e)
            return None

        if isinstance(parsed, list):
            normalized = []
            for item in parsed:
                if not isinstance(item, dict):
                    continue
                hashtags = item.get("hashtags")
                if isinstance(hashtags, str):
                    hashtags = [tag for tag in hashtags.split() if tag]
                item["hashtags"] = hashtags if isinstance(hashtags, list) else []
                normalized.append(item)
            return normalized or None

    logging.error("final_posts is not a list or parseable JSON string")
    return None


# --- 5. Main Pipeline Execution ---
async def run_pipeline(booking_url: str, website_url: str | None = None) -> dict:
    """Runs the full social media content generation pipeline."""
    # Generate a unique session ID
    session_id = f"session_{os.urandom(8).hex()}"
    user_id = "rapidbounce_user"

    # Format the user prompt
    user_input = f"Generate content for Booking URL: {booking_url}"
    if website_url:
        user_input += f" and Website URL: {website_url}"

    message = types.Content(role="user", parts=[types.Part(text=user_input)])

    logging.info(
        "Starting pipeline (session=%s) for booking_url=%s",
        session_id,
        booking_url,
    )

    try:
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("run_pipeline"):
            # Create the session upfront so runner.run_async can load it
            await session_service.create_session(
                app_name=social_media_app.name,
                user_id=user_id,
                session_id=session_id,
            )

            # Execute the agent runner
            async for _event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=message,
            ):
                # We iterate to let the generator finish, but we don't log every step
                pass

            # Retrieve the final state from the session
            session = await session_service.get_session(
                app_name=social_media_app.name,
                user_id=user_id,
                session_id=session_id,
            )

            final_posts_raw = session.state.get("final_posts") if session else None
            final_posts = _normalize_final_posts(final_posts_raw)

            if final_posts:
                logging.info("Pipeline success: posts generated")
                return {"status": "success", "data": final_posts}

            logging.error(
                "Pipeline finished but 'final_posts' not found in state "
                "or could not be parsed"
            )
            return {
                "status": "error",
                "message": "Pipeline ran but no posts were generated.",
            }

    except Exception as e:
        logging.error("Pipeline error: %s", e, exc_info=True)
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    # Simple test for running main.py directly
    TEST_URL = "https://www.booking.com/hotel/gr/test-hotel.html"
    if "test-hotel" in TEST_URL:
        print("Update the TEST_URL in main.py to test directly.")
    else:
        asyncio.run(run_pipeline(TEST_URL))
