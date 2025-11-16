import os
import sys
import asyncio
import json
from dotenv import load_dotenv  # <-- 1. IMPORT
load_dotenv()                   # <-- 2. LOAD KEYS

# --- Check that keys are loaded ---
if not os.environ.get("GOOGLE_API_KEY"):
    print("❌ Error: GOOGLE_API_KEY not found in .env file.")
    sys.exit(1)
if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
    print("❌ Error: GOOGLE_APPLICATION_CREDENTIALS not found in .env file.")
    sys.exit(1)

from google.adk.apps.app import App, EventsCompactionConfig
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types

# --- 1. Import the Root Agent ---
# This imports the 'root_agent' variable from your main_agent/agent.py file
try:
    from main_agent.agent import root_agent
    print("✅ Successfully imported root_agent from main_agent/agent.py")
except ImportError as e:
    print(f"❌ Error: Could not import root_agent: {e}")
    print("Please make sure 'main_agent/agent.py' and 'subagents/__init__.py' exist.")
    sys.exit(1)


# --- 2. Configure the ADK Application ---
# We wrap the root_agent in an App to add critical features like
# context compaction, which is essential for this large pipeline.
compaction_config = EventsCompactionConfig(
    compaction_interval=2,  # Compact context after 2 steps
    overlap_size=1
)

social_media_app = App(
    name="social_media_factory",
    root_agent=root_agent,  # <-- Use the imported root_agent
    events_compaction_config=compaction_config
)

# --- 3. Configure the Runner and Session ---
# We use DatabaseSessionService for persistence, which is ideal
# for a Streamlit app to retrieve results from.
db_url = "sqlite:///sessions.db"
session_service = DatabaseSessionService(db_url=db_url)

# The Runner is what executes the App
runner = Runner(
    app=social_media_app,
    session_service=session_service
)

# --- 4. Main Function to Run the Pipeline ---
# This is how you will execute the agent (e.g., from your Streamlit app)
async def run_pipeline(booking_url: str, website_url: str = None) -> dict:
    """
    Runs the full social media content generation pipeline.
    
    Args:
        booking_url: The Booking.com URL.
        website_url: (Optional) The hotel's main website URL.
        
    Returns:
        A dictionary containing the final generated posts or an error.
    """
    # Use os.urandom for a simple, unique session ID
    session_id = f"session_{os.urandom(8).hex()}"
    user_id = "rapidbounce_user"
    
    # Format the initial user message for the first agent
    user_input = f"Generate content for Booking URL: {booking_url}"
    if website_url:
        user_input += f" and Website URL: {website_url}"
        
    message = types.Content(role="user", parts=[types.Part(text=user_input)])
    
    print(f"--- 🚀 Starting Pipeline (Session: {session_id}) ---")
    
    try:
        # Run the agent and wait for it to complete
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=message
        ):
            # We can log steps here if needed, but we'll wait for the end.
            if event.is_final_response():
                print("--- ✅ Pipeline Complete ---")

        # After the run, get the session to retrieve the final state
        session = await session_service.get_session(
            app_name=social_media_app.name,
            user_id=user_id,
            session_id=session_id
        )
        
        # Get the final output from the 'social_media_agent'
        final_posts = session.state.get("final_posts")
        
        if final_posts:
            return {"status": "success", "data": final_posts}
        else:
            return {"status": "error", "message": "Pipeline ran but 'final_posts' was not found in state."}
            
    except Exception as e:
        print(f"--- ❌ Pipeline Error ---")
        print(f"An error occurred: {e}")
        return {"status": "error", "message": str(e)}

# --- 5. Test Run Entry Point ---
# This block lets you run 'python main.py' to test the whole system.
if __name__ == "__main__":
    # !!! IMPORTANT: REPLACE WITH YOUR TEST URLS !!!
    TEST_BOOKING_URL = "https://www.booking.com/hotel/gr/your-test-hotel.html"
    TEST_WEBSITE_URL = "https://www.your-test-hotel-website.com"
    
    if "your-test-hotel" in TEST_BOOKING_URL:
        print("⚠️ Please update the TEST_BOOKING_URL in main.py before running.")
    else:
        # Check for Google API Key
        if not os.environ.get("GOOGLE_API_KEY"):
            print("❌ Error: GOOGLE_API_KEY environment variable not set.")
            print("Please set it in your terminal: $env:GOOGLE_API_KEY='your_key_here'")
        else:
            print("Starting test run...")
            # Run the async main function
            result = asyncio.run(run_pipeline(TEST_BOOKING_URL, TEST_WEBSITE_URL))
            
            if result["status"] == "success":
                print("\n--- 🏁 FINAL RESULT ---")
                print(json.dumps(result["data"], indent=2))
            else:
                print(f"\n--- 🏁 TEST FAILED ---")
                print(result["message"])