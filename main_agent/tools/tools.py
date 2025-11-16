from typing import Dict, Any, List

import requests
from bs4 import BeautifulSoup
from google.cloud import vision


# --- Tool 1: Booking.com Scraper (HTTP + BeautifulSoup) ---

def get_booking_com_data(booking_url: str) -> Dict[str, Any]:
    """
    Scrapes a Booking.com hotel URL for its main description and a set of
    high-resolution image URLs using plain HTTP + BeautifulSoup.

    This version avoids Playwright because the ADK runtime's event loop
    cannot spawn subprocesses reliably on Windows.

    Returns a dictionary like:
        {
            "status": "success" | "error",
            "description": "...",
            "image_urls": [...],
            "hotel_name": "...",        # when detected
            "booking_url": "original url",
            "message": "optional error/info message"
        }
    """
    print(f"--- Calling Tool: get_booking_com_data for {booking_url} ---")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
    }

    try:
        resp = requests.get(booking_url, headers=headers, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[Booking Scraper] HTTP error: {e}")
        return {
            "status": "error",
            "message": f"HTTP error fetching Booking.com page: {e}",
            "description": "No description found.",
            "image_urls": [],
            "booking_url": booking_url,
        }

    soup = BeautifulSoup(resp.text, "html.parser")

    # Hotel name (header on the page)
    hotel_name = None
    try:
        name_el = soup.select_one("h2.pp-header__title")
        if name_el:
            hotel_name = name_el.get_text(strip=True)
    except Exception:
        hotel_name = None

    # Description: prefer modern data-testid, fall back to older id
    description = "No description found."
    desc_el = soup.select_one('[data-testid="property-description"]')
    if desc_el:
        description = desc_el.get_text(" ", strip=True)
    else:
        desc_div = soup.find(id="property_description_content")
        if desc_div:
            description = desc_div.get_text(" ", strip=True)

    # Image URLs: Booking hotel photos are usually served from cf.bstatic.com/xdata/images/hotel
    image_urls: List[str] = []
    seen = set()
    for img in soup.find_all("img"):
        src = img.get("src") or ""
        if "cf.bstatic.com/xdata/images/hotel" in src:
            if src not in seen:
                seen.add(src)
                image_urls.append(src)

    result: Dict[str, Any] = {
        "status": "success" if image_urls else "error",
        "description": description,
        "image_urls": image_urls,
        "booking_url": booking_url,
    }
    if hotel_name:
        result["hotel_name"] = hotel_name
    if not image_urls:
        result["message"] = "No hotel images found on the page."

    print(
        f"--- [Booking Scraper] Result summary: status={result['status']}, "
        f"desc_len={len(description)}, images={len(image_urls)} ---"
    )

    return result


# --- Tool 2: Google Cloud Vision Analyzer ---

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
