"""
Strapi CMS REST API Client for nxt.bargains.
Provides database adapter methods compatible with SupabaseManager interface,
supporting Waterfall Product Matching, Offer Ingestion, and AI Content Synchronization.
"""

import os
import requests
import logging
from typing import Dict, Any, List, Optional
from config import Config

logger = logging.getLogger(__name__)

class StrapiManager:
    def __init__(self, url: Optional[str] = None, token: Optional[str] = None):
        self.url = (url or Config.STRAPI_URL or os.getenv("STRAPI_URL", "https://cms.fxnstudio.com")).rstrip("/")
        self.token = token or Config.STRAPI_API_TOKEN or os.getenv("STRAPI_API_TOKEN", "")
        self.is_configured = bool(self.token and self.token != "your_strapi_api_token_here")

        if self.is_configured:
            logger.info(f"Initialized Strapi Manager for Strapi CMS -> {self.url}")
        else:
            logger.info("STRAPI_API_TOKEN not configured. Operating in mock/test mode for Strapi.")

    def is_connected(self) -> bool:
        return self.is_configured

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    # =========================================================================
    # WATERFALL MATCHING HELPER METHODS (Matching SupabaseManager Interface)
    # =========================================================================

    def find_canonical_by_gtin(self, gtin: str) -> Optional[Dict[str, Any]]:
        """Tier 1 Match: Search Strapi canonical-products by GTIN/UPC/EAN."""
        if not self.is_configured or not gtin:
            return None
        try:
            endpoint = f"{self.url}/api/canonical-products?filters[gtin_upc_ean][$eq]={gtin.strip()}&populate=*"
            res = requests.get(endpoint, headers=self._headers(), timeout=10)
            if res.status_code == 200:
                data = res.json().get("data", [])
                if data:
                    item = data[0]
                    attrs = item.get("attributes", {})
                    return {"id": item.get("id"), **attrs}
        except Exception as e:
            logger.error(f"Strapi GTIN query error: {e}")
        return None

    def find_canonical_by_asin(self, asin: str) -> Optional[Dict[str, Any]]:
        """Tier 2 Match: Search Strapi canonical-products by ASIN."""
        if not self.is_configured or not asin:
            return None
        try:
            endpoint = f"{self.url}/api/canonical-products?filters[asin][$eq]={asin.strip()}&populate=*"
            res = requests.get(endpoint, headers=self._headers(), timeout=10)
            if res.status_code == 200:
                data = res.json().get("data", [])
                if data:
                    item = data[0]
                    attrs = item.get("attributes", {})
                    return {"id": item.get("id"), **attrs}
        except Exception as e:
            logger.error(f"Strapi ASIN query error: {e}")
        return None

    def find_canonical_by_brand_mpn(self, brand: str, mpn: str) -> Optional[Dict[str, Any]]:
        """Tier 3 Match: Search Strapi canonical-products by Brand + MPN."""
        if not self.is_configured or not brand or not mpn:
            return None
        try:
            endpoint = f"{self.url}/api/canonical-products?filters[brand][$containsi]={brand.strip()}&filters[mpn][$eq]={mpn.strip()}&populate=*"
            res = requests.get(endpoint, headers=self._headers(), timeout=10)
            if res.status_code == 200:
                data = res.json().get("data", [])
                if data:
                    item = data[0]
                    attrs = item.get("attributes", {})
                    return {"id": item.get("id"), **attrs}
        except Exception as e:
            logger.error(f"Strapi Brand+MPN query error: {e}")
        return None

    def find_canonical_by_trigram(self, normalized_title: str, brand: Optional[str] = None) -> List[Dict[str, Any]]:
        """Tier 4 Match: Query Strapi canonical-products by brand for title similarity comparison."""
        if not self.is_configured or not normalized_title:
            return []
        try:
            endpoint = f"{self.url}/api/canonical-products?populate=*"
            if brand:
                endpoint += f"&filters[brand][$containsi]={brand.strip()}"
            res = requests.get(endpoint, headers=self._headers(), timeout=10)
            if res.status_code == 200:
                data = res.json().get("data", [])
                results = []
                for item in data:
                    attrs = item.get("attributes", {})
                    results.append({"id": item.get("id"), **attrs})
                return results
        except Exception as e:
            logger.error(f"Strapi candidate title query error: {e}")
        return []

    def fetch_all_canonical_products(self) -> List[Dict[str, Any]]:
        """Fetches all existing canonical products from Strapi REST API."""
        if not self.is_configured:
            return []
        candidate_endpoints = [
            f"{self.url}/api/canonical-products?pagination[limit]=1000&populate=*",
            f"{self.url}/api/products?pagination[limit]=1000&populate=*"
        ]
        for endpoint in candidate_endpoints:
            try:
                res = requests.get(endpoint, headers=self._headers(), timeout=20)
                if res.status_code == 200:
                    data = res.json().get("data", [])
                    results = []
                    for item in data:
                        attrs = item.get("attributes", {})
                        results.append({"id": item.get("id"), **attrs})
                    if results:
                        return results
            except Exception as e:
                logger.error(f"Error fetching canonical products from Strapi ({endpoint}): {e}")
        return []

    def fetch_all_offers(self) -> List[Dict[str, Any]]:
        """Fetches all existing offers from Strapi REST API."""
        if not self.is_configured:
            return []
        candidate_endpoints = [
            f"{self.url}/api/offers?pagination[limit]=1000&populate=*",
            f"{self.url}/api/deals?pagination[limit]=1000&populate=*",
            f"{self.url}/api/product-offers?pagination[limit]=1000&populate=*"
        ]
        for endpoint in candidate_endpoints:
            try:
                res = requests.get(endpoint, headers=self._headers(), timeout=20)
                if res.status_code == 200:
                    data = res.json().get("data", [])
                    results = []
                    for item in data:
                        attrs = item.get("attributes", {})
                        results.append({"id": item.get("id"), **attrs})
                    if results:
                        return results
            except Exception as e:
                logger.error(f"Error fetching offers from Strapi ({endpoint}): {e}")
        return []

    # =========================================================================
    # UPSERT & QUEUEING METHODS
    # =========================================================================

    def upsert_canonical_product(self, canonical_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates or updates master canonical product entry in Strapi CMS.
        """
        if not self.is_configured:
            mock_id = f"strapi-canonical-{hash(canonical_data.get('title')) & 0xffffffff:x}"
            logger.info(f"[Mock Strapi] Created Canonical Product: '{canonical_data.get('title')}' -> ID: {mock_id}")
            return {"status": "mock_success", "data": {"id": mock_id, **canonical_data}}

        payload = {"data": canonical_data}
        candidate_endpoints = [
            f"{self.url}/api/canonical-products",
            f"{self.url}/api/products"
        ]

        for endpoint in candidate_endpoints:
            try:
                res = requests.post(endpoint, headers=self._headers(), json=payload, timeout=15)
                if res.status_code in [200, 201]:
                    item = res.json().get("data", {})
                    logger.info(f"Successfully created Strapi Canonical Product ID {item.get('id')} at {endpoint}: '{canonical_data.get('title')}'")
                    return {"status": "success", "data": {"id": item.get("id"), **item.get("attributes", {})}}
                else:
                    logger.warning(f"Strapi endpoint '{endpoint}' returned HTTP {res.status_code}: {res.text[:120]}")
            except Exception as e:
                logger.error(f"Error querying Strapi endpoint '{endpoint}': {e}")

        return {"status": "error", "error": "All canonical product endpoints returned non-200"}

    def upsert_marketplace_product(self, offer_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Upserts retailer offer listing into Strapi CMS under 'offers' content-type.
        """
        if not self.is_configured:
            logger.info(f"[Mock Strapi] Upserted Offer: '{offer_data.get('title')}' (${offer_data.get('current_price')}) -> Canonical ID: {offer_data.get('canonical_product_id')}")
            return {"status": "mock_success", "data": offer_data}

        payload = {
            "data": {
                "canonical_product": offer_data.get("canonical_product_id"),
                "retailer": offer_data.get("marketplace"),
                "region": offer_data.get("region", "US"),
                "current_price": offer_data.get("current_price"),
                "original_price": offer_data.get("original_price"),
                "currency": offer_data.get("currency", "USD"),
                "product_url": offer_data.get("product_url"),
                "image_url": offer_data.get("image_url"),
                "is_available": offer_data.get("is_available", True),
                "scraped_at": offer_data.get("scraped_at")
            }
        }
        candidate_endpoints = [
            f"{self.url}/api/offers",
            f"{self.url}/api/deals",
            f"{self.url}/api/product-offers",
            f"{self.url}/api/marketplace-products"
        ]

        for endpoint in candidate_endpoints:
            try:
                res = requests.post(endpoint, headers=self._headers(), json=payload, timeout=15)
                if res.status_code in [200, 201]:
                    logger.info(f"Strapi Offer Upsert Success at {endpoint}: [{offer_data.get('marketplace').upper()}] '{offer_data.get('title')}' -> Price: ${offer_data.get('current_price')}")
                    return {"status": "success", "data": res.json()}
                else:
                    logger.warning(f"Strapi offer endpoint '{endpoint}' returned HTTP {res.status_code}: {res.text[:120]}")
            except Exception as e:
                logger.error(f"Error querying Strapi offer endpoint '{endpoint}': {e}")

        return {"status": "error", "error": "All offer endpoints returned non-200"}

    def insert_unmatched_queue(
        self,
        raw_offer: Dict[str, Any],
        suggested_canonical_id: Optional[str] = None,
        similarity_score: float = 0.0
    ) -> Dict[str, Any]:
        """
        Routes gray-area candidate matches (65% - 84% score) to Strapi 'unmatched-queues' content-type for manual review.
        """
        if not self.is_configured:
            logger.info(f"[Mock Strapi Queue] Queued gray-area match ({similarity_score*100:.1f}%) for: '{raw_offer.get('title')}'")
            return {"status": "mock_queued"}

        try:
            endpoint = f"{self.url}/api/unmatched-queues"
            payload = {
                "data": {
                    "raw_offer": raw_offer,
                    "suggested_canonical": suggested_canonical_id,
                    "similarity_score": round(similarity_score * 100, 2),
                    "status": "pending"
                }
            }
            res = requests.post(endpoint, headers=self._headers(), json=payload, timeout=15)
            if res.status_code in [200, 201]:
                logger.info(f"Queued gray-area offer ({similarity_score*100:.1f}%) to Strapi unmatched-queue: '{raw_offer.get('title')}'")
                return {"status": "success", "data": res.json()}
        except Exception as e:
            logger.error(f"Error queuing offer to Strapi unmatched-queue: {e}")
        return {"status": "error"}
