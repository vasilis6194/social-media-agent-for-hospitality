from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.genai import types
from ...tools.tools import get_booking_com_data

# Configure Retry Options
retry_config = types.HttpRetryOptions(attempts=5, exp_base=7)

# --- Define the Agent ---
booking_scraper_agent = LlmAgent(
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    name="Booking_Scraper_Agent",
    description="A specialist agent that scrapes Booking.com URLs.",
    
    instruction="""
    You are a single-task agent. Your only job is to get a Booking.com URL
    and immediately call the `get_booking_com_data` tool with it.
    Return the raw output from the tool.
    """,
    
    tools=[
        get_booking_com_data  # From tools.py
    ],
    
    # Save the output to this state variable
    output_key="booking_data"
)
