from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.genai import types

from ...tools.tools import get_booking_com_data


# Configure Retry Options
retry_config = types.HttpRetryOptions(attempts=5, exp_base=7)


booking_scraper_agent = LlmAgent(
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    name="Booking_Scraper_Agent",
    description="A specialist agent that scrapes Booking.com URLs using a Playwright-based scraper.",
    instruction="""
    You are a single-task agent. The user will give you a Booking.com hotel URL.

    1. You MUST call the `get_booking_com_data` tool with that URL (and optionally a language code like "en" or "el").
    2. The tool returns a JSON object with at least:
       {
         "status": "success" | "error",
         "hotel_name": "<name or null>",
         "description": "<text>",
         "image_urls": ["<url1>", "<url2>", ...],
         "booking_url": "<final url>",
         "booking_url_canon": "<canonical url or null>"
       }
    3. You MUST return the tool's JSON result as your final answer, without inventing or modifying any image URLs.
    """,
    tools=[
        get_booking_com_data,
    ],
    output_key="booking_data",
)
