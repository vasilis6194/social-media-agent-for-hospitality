from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import google_search
from google.genai import types

# Configure Retry Options
retry_config = types.HttpRetryOptions(attempts=5, exp_base=7)

# --- Define the Agent ---
website_scraper_agent = LlmAgent(
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    name="Website_Scraper_Agent",
    description="A specialist agent that scrapes hotel websites using Google Search.",
    
    instruction="""
    You are a single-task agent. Your only job is to get a hotel website URL
    and call the `google_search` tool to find its description.
    Use a query like `site:THE_URL amenities` or `site:THE_URL about us` to get relevant text.
    Return the raw search snippets.
    """,
    
    tools=[
        google_search  # The built-in tool
    ],
    
    # Save the output to this state variable
    output_key="website_data"
)