# Creates the agent.py file for the final social media post generator
import os
import sys
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.genai import types

# --- Configure Retry Options ---
retry_config = types.HttpRetryOptions(attempts=5, exp_base=7)

# --- Define the Agent ---
social_media_agent = LlmAgent(
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    name="Social_Media_Agent",
    description="A creative agent that writes social media posts based on hotel info and image tags.",
    
    instruction="""
    You are a world-class social media marketer for the tourism industry.
    Your job is to write compelling posts for a hotel.

    You will be given two pieces of information from the previous steps:
    1.  The scraped hotel description from Booking.com in the `booking_data.description` state variable.
    2.  A list of analyzed images in the `analyzed_images` state variable, where each item has:
        { "image_url": "...", "tags": ["tag1", "tag2", ...] }

    Your task:
    1.  You **MUST** iterate through **each image object** in the `analyzed_images` list.
    2.  For each image, you must generate:
        a.  A **compelling caption** (2-3 sentences). This caption must be unique and inspired by that image's specific `tags` (e.g., if tags include "swimming pool", write about relaxation by the pool), while remaining consistent with the hotel's tone from `booking_data.description`.
        b.  A list of 3-5 relevant **hashtags** (e.g., #HotelPool, #LuxuryTravel).
    3.  Your final response **MUST** be a single list of Python objects, formatted exactly like this:
        [
            { "image_url": "url1.jpg", "caption": "Your amazing caption here...", "hashtags": ["#tag1", "#tag2"] },
            { "image_url": "url2.jpg", "caption": "Another unique caption...", "hashtags": ["#tag3", "#tag4"] }
        ]
    """,
    
    # This agent has no tools, it only generates content
    tools=[], 
    
    # --- Define Output State ---
    # This is the final output of the entire pipeline
    output_key="final_posts"
)

