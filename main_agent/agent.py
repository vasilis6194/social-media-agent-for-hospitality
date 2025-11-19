from google.adk.agents import SequentialAgent

from .subagents.booking_scraper_agent import booking_scraper_agent
from .subagents.website_scraper_agent import website_scraper_agent
from .subagents.image_analysis_agent import image_analysis_agent
from .subagents.social_media_agent import social_media_agent

# --- Define a Local Subclass ---
# subclass SequentialAgent so the ADK Runner recognizes this agent
# as belonging to project (main_agent), not the library (google.adk).
class SocialMediaPipeline(SequentialAgent):
    pass

# --- 1. Define the Root Agent (The Pipeline) ---
# Use the local class instead of SequentialAgent directly
root_agent = SocialMediaPipeline(
    name="Social_Media_Pipeline_Agent",
    sub_agents=[
        booking_scraper_agent,   # Step 1: Get booking_data
        website_scraper_agent,   # Step 2: Get website_data
        image_analysis_agent,    # Step 3: Analyze images
        social_media_agent,      # Step 4: Write posts
    ],
)