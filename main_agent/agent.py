from google.adk.agents import SequentialAgent

from .subagents.content_ingestion_agent import content_ingestion_agent
from .subagents.image_analysis_agent import image_analysis_agent
from .subagents.social_media_agent import social_media_agent


# --- 1. Define the Root Agent (The Pipeline) ---
# This agent connects all your specialist agents in a fixed order.
root_agent = SequentialAgent(
    name="Social_Media_Pipeline_Agent",
    sub_agents=[
        content_ingestion_agent,  # Step 1: Get content (output_key='ingested_content')
        image_analysis_agent,     # Step 2: Analyze images (output_key='analyzed_images')
        social_media_agent        # Step 3: Write posts (output_key='final_posts')
    ]
)