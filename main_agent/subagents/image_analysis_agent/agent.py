from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.genai import types
from typing import List, Dict, Any
from ...tools.tools import analyze_image_with_vision

# --- Configure Retry Options ---
retry_config = types.HttpRetryOptions(attempts=5, exp_base=7)

# --- Define the Agent ---
image_analysis_agent = LlmAgent(
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    name="Image_Analysis_Agent",
    description="Analyzes a list of image URLs using Google Vision API.",
    
    instruction="""
    You are a specialist image analyst.
    Your job is to analyze a list of image URLs provided in the `{ingested_content.image_urls}` variable.

    1.  You **MUST** call the `analyze_image_with_vision` tool for **every single URL** in the list.
    2.  After you have called the tool for all images, you must collate the results.
    3.  Your final output must be a single list of objects, where each object contains the original 'image_url' and its 'tags'.
        Example Output:
        [
            { "image_url": "url1.jpg", "tags": ["pool", "sky", "hotel"] },
            { "image_url": "url2.jpg", "tags": ["bedroom", "king bed", "lamp"] }
        ]
    """,
    
    tools=[
        analyze_image_with_vision  # From tools.py
    ],
    
    # --- Define Output State ---
    # The list of analyzed images will be saved to this variable
    output_key="analyzed_images"
)
