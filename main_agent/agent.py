from google.adk.agents import SequentialAgent

from .subagents.booking_scraper_agent import booking_scraper_agent
from .subagents.website_scraper_agent import website_scraper_agent
from .subagents.image_analysis_agent import image_analysis_agent
from .subagents.social_media_agent import social_media_agent


# --- 1. Define the Root Agent (The Pipeline) ---
# This agent connects all your specialist agents in a fixed order.
root_agent = SequentialAgent(
    name="Social_Media_Pipeline_Agent",
    sub_agents=[
        booking_scraper_agent,   # Step 1: Get booking_data (description + image_urls)
        website_scraper_agent,   # Step 2: Optionally get website_data snippets
        image_analysis_agent,    # Step 3: Analyze images (output_key='analyzed_images')
        social_media_agent,      # Step 4: Write posts (output_key='final_posts')
    ],
)
