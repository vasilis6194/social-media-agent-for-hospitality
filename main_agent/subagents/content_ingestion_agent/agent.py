import sys
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import AgentTool
from google.genai import types

# --- Import the Specialist Agents ---
# We import the agents themselves to wrap them in AgentTool
try:
    from ..booking_scraper_agent.agent import booking_scraper_agent
    from ..website_scraper_agent.agent import website_scraper_agent
except ImportError:
    print("Error: Could not import sub-agents. Make sure they exist and paths are correct.")
    sys.exit(1)

# --- Configure Retry Options ---
retry_config = types.HttpRetryOptions(attempts=5, exp_base=7)

# --- Define the Agent ---
content_ingestion_agent = LlmAgent(
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    name="Content_Ingestion_Agent",
    description="Manages two sub-agents to gather all hotel content.",
    
    instruction="""
    You are a content manager. Your job is to get a hotel description and a list of image URLs by coordinating two specialist agents.
    The user will provide one or two URLs.

    1.  You **MUST** identify the 'booking.com' URL and call the `Booking_Scraper_Agent` tool with it exactly once. That agent calls a tool named `get_booking_com_data(booking_url: str)` and returns a JSON object like:

        {
          "status": "success" | "error",
          "description": "<text>",
          "image_urls": ["<url1>", "<url2>", ...],
          "hotel_name": "<optional>",
          "booking_url": "<url>"
        }

        - If `booking_data.status == "success"` you **MUST NOT** ask the user for any additional website URL just because you feel like it. You must continue using the `description` and `image_urls` from `booking_data`.
        - Only if `booking_data.status == "error"` or both `booking_data.description` and `booking_data.image_urls` are empty are you allowed to ask the user for the hotel's main website URL.

    2.  If the user also provides a second URL (the hotel's main website), then you **MUST** call the `Website_Scraper_Agent` with that URL. That agent returns text snippets to the `website_data` variable (for example, `website_data.snippets`).

    3.  After your tools have run, you must consolidate the results:
        -   The final `image_urls` list comes *only* from `booking_data.image_urls`.
        -   The final `description` must be a high-quality merge of `booking_data.description` and (if it exists) `website_data.snippets`.

    4.  Your final output must be a **single JSON object** with exactly these keys:

        {
          "description": "<merged_description>",
          "image_urls": ["<url1>", "<url2>", ...]
        }

        Do not add any extra commentary outside this JSON object.
    """,
    
    # --- Define Agent Tools ---
    # This agent's tools are the other agents
    tools=[
        AgentTool(agent=booking_scraper_agent),
        AgentTool(agent=website_scraper_agent)
    ],
    
    # --- Define Output State ---
    # This agent's consolidated findings are saved here
    output_key="ingested_content"
)
