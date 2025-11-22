import sys
import os
import logging
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- Import your existing agent logic ---
# We verify imports to ensure the file is placed correctly
try:
    from main import run_pipeline
except ImportError as e:
    print("Error: Could not import 'run_pipeline' from 'main.py'.")
    print("Ensure api_server.py is in the same directory as main.py")
    sys.exit(1)

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_server")

# --- FastAPI App Setup ---
app = FastAPI(title="Hospitality Agent API")

# Configure CORS to allow requests from the local Vite dev server
# and from any future hosted frontend if needed.
allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,  # No cookies/credentials needed for this API
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Data Models ---
class GenerateRequest(BaseModel):
    booking_url: str
    website_url: Optional[str] = None

class Post(BaseModel):
    image_url: str
    caption: str
    hashtags: List[str]

class GenerateResponse(BaseModel):
    status: str
    data: List[Post]
    message: Optional[str] = None

# --- Endpoints ---

@app.get("/")
async def health_check():
    return {"status": "online", "service": "social_media_agent"}

@app.post("/generate", response_model=GenerateResponse)
async def generate_content(request: GenerateRequest):
    """
    Triggers the social media agent pipeline.
    """
    logger.info(f"Received request for: {request.booking_url}")
    
    if not request.booking_url:
        raise HTTPException(status_code=400, detail="Booking.com URL is required")

    try:
        # Call the existing run_pipeline function from main.py
        # Note: run_pipeline is async, so we await it.
        result = await run_pipeline(
            booking_url=request.booking_url, 
            website_url=request.website_url
        )

        if result.get("status") == "success":
            return GenerateResponse(
                status="success",
                data=result.get("data", [])
            )
        else:
            # If the agent reported an error internally
            return GenerateResponse(
                status="error",
                data=[],
                message=result.get("message", "Unknown agent error")
            )

    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    print("Starting API Server...")
    print("Swagger Docs available at: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
