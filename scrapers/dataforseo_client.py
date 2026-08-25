import os
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
            logger.info("DataForSEO Fetcher initialized with active credentials.")
        else:
            logger.info("DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD not configured. Operating in fallback / demo mode.")

    def search_google_shopping_offers(
        self,
        keyword: str,
        region: str = "AU",
        category: str = "General",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Searches Google Shopping via DataForSEO Merchant API to retrieve 
        multi-retailer offers for a specific keyword in a target region.
        """
        if not self.is_configured:
            logger.info(f"[DataForSEO Fallback] Returning simulated multi-offer response for '{keyword}' ({region}).")
            return self._mock_offers_fallback(keyword, region, category)

        location_code = LOCATION_CODES.get(region.upper(), 2840)
        endpoint = f"{self.BASE_URL}/products/live"

        payload = [{
            "keyword": keyword,
            "location_code": location_code,
            "language_code": "en",
            "depth": limit
        }]

        try:
            logger.info(f"Posting DataForSEO Shopping Search: '{keyword}' (Region: {region}, LocCode: {location_code})")
            res = requests.post(
                endpoint,
                auth=(self.login, self.password),
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            if res.status_code != 200:
                logger.error(f"DataForSEO API error HTTP {res.status_code}: {res.text}")
                return self._mock_offers_fallback(keyword, region, category)

            data = res.json()
            tasks = data.get("tasks", [])
            if not tasks or not tasks[0].get("result"):
                logger.warning(f"No DataForSEO results found for keyword '{keyword}'.")
                return []

            items = tasks[0]["result"][0].get("items", [])
            extracted_offers = []
            rank = 1

            for item in items:
                title = item.get("title")
                price = item.get("price")
                seller = item.get("seller_name") or item.get("domain") or "Marketplace Store"
                product_url = item.get("url") or item.get("shopping_url")
                image_url = item.get("image_url")
                rating = item.get("rating", {}).get("value") if isinstance(item.get("rating"), dict) else None

                if not title or not price or not product_url:
                    continue

                mkp_tag = seller.lower().replace(" ", "_").replace(".", "_")

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
            return self._mock_offers_fallback(keyword, region, category)

    def _mock_offers_fallback(self, keyword: str, region: str, category: str) -> List[Dict[str, Any]]:
        """Simulates 3+ retailer offers when credentials are pending."""
        reg = region.upper()
        curr = "AUD" if reg == "AU" else "USD"
        
        if reg == "AU":
            stores = [("amazon_au", "Amazon Australia", 189.00), ("jbhifi", "JB Hi-Fi", 199.00), ("harveynorman", "Harvey Norman", 209.00)]
        elif category == "Beauty & Skincare":
            stores = [("sephora", "Sephora", 38.00), ("iherb", "iHerb", 35.50), ("amazon", "Amazon", 36.00)]
        else:
            stores = [("amazon", "Amazon US", 179.99), ("bestbuy", "Best Buy", 189.99), ("walmart", "Walmart", 185.00)]

        offers = []
        for idx, (mkp, seller, pr) in enumerate(stores, 1):
            offers.append({
                "marketplace": mkp,
                "region": reg,
                "external_id": f"dfs-{idx}",
                "title": f"{keyword} (Official Release)",
                "brand": keyword.split()[0] if keyword else "Brand",
                "category": category,
                "current_price": pr,
                "original_price": round(pr * 1.15, 2),
                "discount_percent": 13.0,
                "currency": curr,
                "rank_position": idx,
                "rating": 4.7,
                "review_count": 120,
                "seller_name": seller,
                "is_available": True,
                "product_url": f"https://www.{mkp}.com/item/{keyword.lower().replace(' ', '-')}",
                "image_url": "https://m.media-amazon.com/images/I/71H8XhwlwpL._AC_UL320_.jpg",
                "images": [],
                "metadata": {"provider": "dataforseo_demo", "search_keyword": keyword}
            })
        return offers
