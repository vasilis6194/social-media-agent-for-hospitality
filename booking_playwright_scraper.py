"""Standalone Playwright-based Booking.com scraper.

This script is invoked by the ADK tool `get_booking_com_data` via
subprocess. It prints a single JSON object to stdout.
"""

import asyncio
import json
import re
import sys
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from urllib.parse import urlparse, urlunparse


def canonicalize_booking_url(raw_url: str) -> Optional[str]:
    """Normalize Booking.com hotel URLs so the same hotel maps to one key."""
    if not raw_url:
        return None
    u = urlparse(raw_url.strip())
    if not u.netloc:
        return None
    host = u.netloc.lower()
    if host.endswith("booking.com"):
        host = "www.booking.com"
    path = (u.path or "").rstrip("/").lower()
    return urlunparse(("https", host, path, "", "", ""))


def update_url_language(url: str, language: str) -> str:
    """Adjust Booking.com URL language segment, if present."""
    language = (language or "en").lower()
    if ".en-gb.html" in url and language == "el":
        return url.replace(".en-gb.html", ".el-gr.html")
    if ".el-gr.html" in url and language == "en":
        return url.replace(".el-gr.html", ".en-gb.html")
    return url


async def scrape_booking_hotel_async(url: str, language: str = "en") -> Dict[str, Any]:
    """Core scraper logic using Playwright + BeautifulSoup."""
    url = update_url_language(url, language)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_timeout(5000)
        final_url = page.url

        # Step 1: Open image thumbnails grid.
        try:
            await page.locator("div.nha_large_photo_main_content").first.click()
            await page.wait_for_timeout(3000)
        except Exception as e:  # noqa: BLE001
            print(f"⚠️ Step 1 failed: {e}", file=sys.stderr)

        # Step 2: Open full gallery by clicking a thumbnail.
        try:
            await page.locator("div[data-testid='gallery-modal-grid'] div").first.click()
            await page.wait_for_timeout(3000)
        except Exception as e:  # noqa: BLE001
            print(f"⚠️ Step 2 failed: {e}", file=sys.stderr)

        # Step 3: Extract total image count from gallery counter.
        try:
            counter_text = await page.inner_text(
                "div[data-testid='gallery-single-view-counter-text'] div"
            )
            match = re.search(r"/\\s*(\\d+)", counter_text)
            total_images = int(match.group(1)) if match else 50
            print(f" Total images detected: {total_images}", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            print(f"⚠️ Could not detect image count, using fallback (50): {e}", file=sys.stderr)
            total_images = 50

        # Step 4: Extract all image URLs.
        image_urls: List[str] = []
        seen: set[str] = set()
        try:
            for i in range(total_images):
                img = await page.query_selector(
                    "div[data-testid='gallery-single-view'] picture img"
                )
                if img:
                    src = await img.get_attribute("src")
                    if src and src not in seen:
                        seen.add(src)
                        image_urls.append(src)
                        print(f"✅ {i+1}/{total_images} - {src}", file=sys.stderr)

                await page.mouse.click(640, 360)
                await page.wait_for_timeout(1000)
        except Exception as e:  # noqa: BLE001
            print(f"⚠️ Gallery navigation failed: {e}", file=sys.stderr)

        # Scrape hotel name and description.
        html = await page.content()
        await browser.close()

    soup = BeautifulSoup(html, "html.parser")

    try:
        hotel_name_el = soup.select_one("h2.pp-header__title")
        hotel_name = hotel_name_el.get_text(strip=True) if hotel_name_el else "Not found"
    except Exception:  # noqa: BLE001
        hotel_name = "Not found"

    try:
        desc_el = soup.select_one("p[data-testid='property-description']")
        description = desc_el.get_text(strip=True) if desc_el else "Not found"
    except Exception:  # noqa: BLE001
        description = "Not found"

    return {
        "status": "success",
        "hotel_name": hotel_name,
        "description": description,
        "image_urls": image_urls,
        "booking_url": final_url,
        "booking_url_canon": canonicalize_booking_url(final_url),
    }


def main() -> None:
    if len(sys.argv) < 2:
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": "Missing Booking.com URL argument.",
                    "hotel_name": None,
                    "description": "No description found.",
                    "image_urls": [],
                    "booking_url": None,
                    "booking_url_canon": None,
                }
            )
        )
        sys.exit(1)

    url = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 else "en"

    try:
        result = asyncio.run(scrape_booking_hotel_async(url, language))
    except Exception as e:  # noqa: BLE001
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": f"Playwright error while scraping: {e}",
                    "hotel_name": None,
                    "description": "No description found.",
                    "image_urls": [],
                    "booking_url": url,
                    "booking_url_canon": canonicalize_booking_url(url),
                }
            )
        )
        sys.exit(1)

    print(json.dumps(result))


if __name__ == "__main__":
    main()

