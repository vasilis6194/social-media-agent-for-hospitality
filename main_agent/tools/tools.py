import json
import os
import subprocess
import sys
from typing import Any, Dict, List

import requests
from google.cloud import vision


# --- Booking.com Scraper (Playwright via subprocess) ---

def get_booking_com_data(booking_url: str, language: str = "en") -> Dict[str, Any]:
    """
    Scrapes a Booking.com hotel URL for its main description and image URLs.

    This implementation delegates to an external Playwright-based script
    (`booking_playwright_scraper.py`) run in a separate process so that
    the ADK event loop does not need to manage browser subprocesses.

    The script is expected to print a single JSON object to stdout:
        {
            "status": "success" | "error",
            "hotel_name": "...",
            "description": "...",
            "image_urls": ["url1", "url2", ...],
            "booking_url": "...",
            "booking_url_canon": "...",
            "message": "optional error/info message"
        }
    """
    print(f"--- Calling Tool: get_booking_com_data for {booking_url} ---")

    # Resolve the scraper script path relative to this file.
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    script_path = os.path.join(project_root, "booking_playwright_scraper.py")

    if not os.path.isfile(script_path):
        msg = f"Playwright scraper script not found at {script_path}"
        print(f"[Booking Scraper] {msg}")
        return {
            "status": "error",
            "message": msg,
            "description": "No description found.",
            "image_urls": [],
            "booking_url": booking_url,
        }

    cmd = [sys.executable, script_path, booking_url, language]
    try:
        completed = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.CalledProcessError as e:
        msg = f"Playwright scraper failed: {e.stderr or e.stdout}"
        print(f"[Booking Scraper] {msg}")
        return {
            "status": "error",
            "message": msg,
            "description": "No description found.",
            "image_urls": [],
            "booking_url": booking_url,
        }
    except subprocess.TimeoutExpired:
        msg = "Playwright scraper timed out."
        print(f"[Booking Scraper] {msg}")
        return {
            "status": "error",
            "message": msg,
            "description": "No description found.",
            "image_urls": [],
            "booking_url": booking_url,
        }

    stdout = (completed.stdout or "").strip()
    try:
        result = json.loads(stdout)
    except json.JSONDecodeError as e:
        msg = f"Could not parse scraper JSON output: {e}"
        print(f"[Booking Scraper] {msg}")
        print(f"[Booking Scraper] Raw output: {stdout[:200]}", file=sys.stderr)
        return {
            "status": "error",
            "message": msg,
            "description": "No description found.",
            "image_urls": [],
            "booking_url": booking_url,
        }

    # Ensure required keys exist.
    if "description" not in result:
        result["description"] = "No description found."
    if "image_urls" not in result:
        result["image_urls"] = []
    if "booking_url" not in result:
        result["booking_url"] = booking_url

    print(
        f"--- [Booking Scraper] Result summary: status={result.get('status')}, "
        f"desc_len={len(result.get('description', ''))}, "
        f"images={len(result.get('image_urls', []))} ---"
    )

    return result


# --- Google Cloud Vision Analyzer ---

def analyze_image_with_vision(image_url: str) -> Dict[str, Any]:
    """
    Uses the Google Cloud Vision API to analyze a single image URL and extract relevant marketing tags.
    It fetches labels, objects, and any detected text.

    Args:
        image_url: The publicly accessible URL of the image to analyze.

    Returns:
        A dictionary with status and a list of descriptive tags.
        Example (success):
        {
            "status": "success",
            "tags": ["Swimming Pool", "Ocean View", "Sun Lounger", "Palm Tree", "Blue Sky"]
        }
        Example (error):
        {
            "status": "error",
            "message": "Vision API error."
        }
    """
    print(f"--- Calling Tool: analyze_image_with_vision for {image_url} ---")
    try:
        # Instantiate a client
        client = vision.ImageAnnotatorClient()

        # Create the image object
        image = vision.Image()
        image.source.image_uri = image_url

        # Define the features we want, as discussed
        features = [
            {"type_": vision.Feature.Type.LABEL_DETECTION, "max_results": 10},
            {"type_": vision.Feature.Type.OBJECT_LOCALIZATION, "max_results": 5},
            {"type_": vision.Feature.Type.TEXT_DETECTION, "max_results": 5},
        ]

        # Perform the request
        response = client.annotate_image({'image': image, 'features': features})

        if response.error.message:
            raise Exception(response.error.message)

        # Process the results into a single tag list
        tags = set() # Use a set to avoid duplicate tags

        # 1. Add Labels
        for label in response.label_annotations:
            if label.score > 0.75: # Only add confident labels
                tags.add(label.description)

        # 2. Add Objects
        for obj in response.localized_object_annotations:
            if obj.score > 0.6: # Only add confident objects
                tags.add(obj.name)
        
        # 3. Add Text
        for text in response.text_annotations:
            # The first text_annotation is the full block of text, 
            # subsequent ones are individual words. We'll skip the first.
            if ' ' not in text.description: # A rough way to filter for single words/phrases
                tags.add(text.description)
        
        # Remove the first, full-text annotation if it got added
        if response.text_annotations:
            tags.discard(response.text_annotations[0].description)

        if not tags:
            return {"status": "error", "message": "No relevant features found in the image."}

        return {
            "status": "success",
            "tags": list(tags)
        }

    except Exception as e:
        print(f"Error in Vision API: {e}")
        return {"status": "error", "message": f"Error analyzing image: {e}"}
