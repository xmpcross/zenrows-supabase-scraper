import os
import time
import base64
import requests
import logging
from typing import List, Dict, Any, Optional
from config import Config

logger = logging.getLogger(__name__)

# DataForSEO Location Codes
LOCATION_CODES = {
    "AU": 2036,  # Australia
    "US": 2840,  # United States
    "UK": 2826,  # United Kingdom
    "CA": 2124,  # Canada
    "DE": 2276,  # Germany
    "NZ": 2554   # New Zealand
}

class DataForSEOFetcher:
    """
    Client for DataForSEO Merchant & Google Shopping API.
    Provides structured e-commerce offer aggregation across multi-retailer platforms.
    """

    BASE_URL = "https://api.dataforseo.com/v3/merchant/google"

    def __init__(self, login: Optional[str] = None, password: Optional[str] = None):
        self.login = login or Config.DATAFORSEO_LOGIN or os.getenv("DATAFORSEO_LOGIN", "")
        self.password = password or Config.DATAFORSEO_PASSWORD or os.getenv("DATAFORSEO_PASSWORD", "")
        self.is_configured = bool(self.login and self.password and self.login != "your_dataforseo_login_email")

        if self.is_configured:
            pw = self.password.strip()
            # If pw is already base64 encoded string (e.g. starting with 'a3Jpd...'), use directly
            try:
                decoded = base64.b64decode(pw).decode("utf-8")
                if ":" in decoded:
                    self.auth_header = f"Basic {pw}"
                else:
                    raw_pair = f"{self.login}:{pw}"
                    self.auth_header = f"Basic {base64.b64encode(raw_pair.encode()).decode()}"
            except Exception:
                if ":" in pw:
                    self.auth_header = f"Basic {base64.b64encode(pw.encode()).decode()}"
                else:
                    raw_pair = f"{self.login}:{pw}"
                    self.auth_header = f"Basic {base64.b64encode(raw_pair.encode()).decode()}"
            logger.info("DataForSEO Fetcher initialized with active credentials.")
        else:
            self.auth_header = ""
            logger.info("DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD not configured. Live calls are disabled.")

    def search_google_shopping_offers(
        self,
        keyword: str,
        region: str = "US",
        category: str = "General",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Searches Google Shopping via DataForSEO Merchant API to retrieve 
        multi-retailer offers for a specific keyword in a target region.
        """
        if not self.is_configured:
            logger.error("DataForSEO credentials are not configured; refusing to search offers.")
            return []

        location_code = LOCATION_CODES.get(region.upper(), 2840)
        post_endpoint = f"{self.BASE_URL}/products/task_post"

        payload = [{
            "keyword": keyword,
            "location_code": location_code,
            "language_code": "en",
            "depth": limit,
            "priority": 2
        }]

        headers = {
            "Authorization": self.auth_header,
            "Content-Type": "application/json"
        }

        try:
            logger.info(f"Posting DataForSEO Shopping Task: '{keyword}' (Region: {region}, LocCode: {location_code})")
            res = requests.post(
                post_endpoint,
                headers=headers,
                json=payload,
                timeout=30
            )

            if res.status_code != 200:
                logger.error(f"DataForSEO API error HTTP {res.status_code}: {res.text}")
                return []

            data = res.json()
            tasks = data.get("tasks", [])
            if not tasks or not tasks[0].get("id"):
                logger.warning(f"Failed to create DataForSEO task for keyword '{keyword}'.")
                return []

            task_id = tasks[0]["id"]
            get_endpoint = f"{self.BASE_URL}/products/task_get/advanced/{task_id}"

            items = []
            for attempt in range(8):
                time.sleep(2)
                get_res = requests.get(get_endpoint, headers=headers, timeout=30)
                if get_res.status_code != 200:
                    continue
                get_data = get_res.json()
                task_results = get_data.get("tasks", [{}])[0].get("result")
                if task_results and len(task_results) > 0 and task_results[0] and task_results[0].get("items"):
                    items = task_results[0]["items"]
                    break

            if not items:
                logger.warning(f"DataForSEO task {task_id} returned no items for keyword '{keyword}'.")
                return []

            extracted_offers = []
            rank = 1

            for item in items:
                title = item.get("title")
                price = item.get("price")
                seller = item.get("seller") or item.get("seller_name") or item.get("domain") or "Marketplace Store"
                product_url = item.get("url") or item.get("shopping_url")
                image_url = item.get("image_url") or (item.get("product_images") or [None])[0]
                rating = item.get("rating", {}).get("value") if isinstance(item.get("rating"), dict) else (item.get("product_rating", {}).get("value") if isinstance(item.get("product_rating"), dict) else None)

                if not title or not price or not product_url:
                    continue

                raw_seller = seller.lower().strip()
                if "best buy" in raw_seller or "bestbuy" in raw_seller:
                    mkp_tag = "bestbuy"
                elif "walmart" in raw_seller:
                    mkp_tag = "walmart"
                elif "amazon" in raw_seller:
                    mkp_tag = "amazon_us"
                elif "target" in raw_seller:
                    mkp_tag = "target"
                elif "apple" in raw_seller:
                    mkp_tag = "apple_store"
                elif "ebay" in raw_seller:
                    mkp_tag = "ebay"
                elif "verizon" in raw_seller:
                    mkp_tag = "verizon"
                elif "att" in raw_seller or "at&t" in raw_seller:
                    mkp_tag = "att"
                elif "tmobile" in raw_seller or "t-mobile" in raw_seller:
                    mkp_tag = "tmobile"
                else:
                    import re
                    mkp_tag = re.sub(r"[^a-z0-9_]", "", raw_seller.replace(" ", "_").replace(".", "_")) or "marketplace_store"

                extracted_offers.append({
                    "marketplace": mkp_tag,
                    "region": region.upper(),
                    "external_id": str(item.get("product_id") or rank),
                    "title": title,
                    "brand": item.get("brand") or (title.split()[0] if title else "Brand"),
                    "category": category,
                    "current_price": float(price),
                    "original_price": float(item["original_price"]) if item.get("original_price") else None,
                    "discount_percent": None,
                    "currency": item.get("currency") or ("AUD" if region == "AU" else "USD"),
                    "rank_position": rank,
                    "rating": float(rating) if rating else None,
                    "review_count": item.get("reviews_count") or 0,
                    "seller_name": seller,
                    "is_available": True,
                    "product_url": product_url,
                    "image_url": image_url,
                    "images": [image_url] if image_url else [],
                    "metadata": {"provider": "dataforseo", "search_keyword": keyword}
                })
                rank += 1

            logger.info(f"DataForSEO successfully retrieved {len(extracted_offers)} offers for '{keyword}' ({region}).")
            return extracted_offers

        except Exception as e:
            logger.error(f"Failed to query DataForSEO API: {e}")
            return []
