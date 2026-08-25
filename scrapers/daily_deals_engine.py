"""
Daily Deals Ingestion Engine for Multi-Marketplace E-Commerce Aggregation.

Scrapes target Today's Deals / Flash Sale URLs across Amazon (US, AU, UK), Best Buy, eBay (US, AU), Walmart, iHerb, and Sephora using ZenRows anti-bot proxies.
Passes extracted deal offers through WaterfallMatcher to automatically link canonical products and record price snapshots in Supabase.
"""

import os
import re
import logging
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup

from scrapers.zenrows_client import ZenRowsFetcher
from scrapers.marketplace_scrapers import parse_marketplace_page, clean_price, clean_text, extract_brand
from services.price_tracker import PriceTrackerEngine
from db.supabase_client import SupabaseManager

logger = logging.getLogger(__name__)

# TARGET TODAY'S DEALS LANDING PAGES BY RETAILER & REGION
TARGET_DEAL_PAGES = {
    "amazon_us": {
        "url": "https://www.amazon.com/deals",
        "region": "US",
        "marketplace": "amazon_us",
        "proxy_country": "us",
        "niche": "smart_home"
    },
    "amazon_au": {
        "url": "https://www.amazon.com.au/deals",
        "region": "AU",
        "marketplace": "amazon_au",
        "proxy_country": "au",
        "niche": "smart_home"
    },
    "amazon_uk": {
        "url": "https://www.amazon.co.uk/deals",
        "region": "UK",
        "marketplace": "amazon_uk",
        "proxy_country": "gb",
        "niche": "smart_home"
    },
    "bestbuy": {
        "url": "https://www.bestbuy.com/site/misc/deal-of-the-day/pcmcat248000050016.c?intl=nosplash",
        "region": "US",
        "marketplace": "bestbuy",
        "proxy_country": "us",
        "niche": "smart_home"
    },
    "ebay_us": {
        "url": "https://www.ebay.com/globaldeals",
        "region": "US",
        "marketplace": "ebay_us",
        "proxy_country": "us",
        "niche": "smart_home"
    },
    "ebay_au": {
        "url": "https://www.ebay.com.au/deals",
        "region": "AU",
        "marketplace": "ebay_au",
        "proxy_country": "au",
        "niche": "smart_home"
    },
    "walmart": {
        "url": "https://www.walmart.com/shop/deals",
        "region": "US",
        "marketplace": "walmart",
        "proxy_country": "us",
        "niche": "smart_home"
    },
    "iherb": {
        "url": "https://www.iherb.com/c/specials",
        "region": "US",
        "marketplace": "iherb",
        "proxy_country": "us",
        "niche": "beauty_skincare"
    },
    "sephora": {
        "url": "https://www.sephora.com/beauty/sale",
        "region": "US",
        "marketplace": "sephora",
        "proxy_country": "us",
        "niche": "beauty_skincare"
    },
    "target": {
        "url": "https://www.target.com/c/top-deals/-/N-4xubz",
        "region": "US",
        "marketplace": "target",
        "proxy_country": "us",
        "niche": "smart_home"
    },
    "newegg": {
        "url": "https://www.newegg.com/todays-deals",
        "region": "US",
        "marketplace": "newegg",
        "proxy_country": "us",
        "niche": "smart_home"
    }
}


class DailyDealsIngestionEngine:
    def __init__(
        self,
        fetcher: Optional[ZenRowsFetcher] = None,
        supabase: Optional[SupabaseManager] = None,
        tracker: Optional[PriceTrackerEngine] = None
    ):
        self.fetcher = fetcher or ZenRowsFetcher()
        self.supabase = supabase or SupabaseManager()
        self.tracker = tracker or PriceTrackerEngine(supabase=self.supabase)

    def run_daily_deal_ingestion(
        self,
        deal_keys: Optional[List[str]] = None,
        local_catalog: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Executes daily deals ingestion across configured retailer deal pages.
        """
        target_keys = deal_keys or list(TARGET_DEAL_PAGES.keys())
        total_offers_extracted = 0
        total_offers_matched = 0
        summary_results = {}

        logger.info(f"=== STARTING DAILY DEALS INGESTION FOR {len(target_keys)} RETAILER TARGETS ===")

        for key in target_keys:
            if key not in TARGET_DEAL_PAGES:
                logger.warning(f"Unknown deal target key: '{key}'. Skipping.")
                continue

            config = TARGET_DEAL_PAGES[key]
            logger.info(f"\n--- Ingesting Deals for [{key.upper()}] ({config['region']}) -> {config['url']} ---")

            try:
                if self.fetcher.is_configured:
                    html = self.fetcher.fetch_html(
                        config["url"],
                        custom_params={
                            "js_render": "true",
                            "antibot": "true",
                            "premium_proxy": "true",
                            "proxy_country": config["proxy_country"]
                        }
                    )
                    extracted_offers = parse_marketplace_page(html, config["url"], config["marketplace"])
                else:
                    logger.info(f"[Mock Daily Deals] Generating simulated deals for target key '{key}'.")
                    extracted_offers = self._generate_mock_daily_deals(key, config)

                logger.info(f"Extracted {len(extracted_offers)} live deal offers from {key.upper()}.")

                matched_count = 0
                processed_items = []
                for offer in extracted_offers:
                    offer["region"] = config["region"]
                    offer["niche"] = config["niche"]

                    res = self.tracker.process_incoming_offer(offer, local_catalog=local_catalog)
                    match_info = res.get("match", {})
                    cid = match_info.get("canonical_product_id")

                    if cid:
                        matched_count += 1

                    processed_items.append({
                        "title": offer.get("title"),
                        "price": offer.get("current_price"),
                        "canonical_id": cid,
                        "match_tier": match_info.get("match_tier")
                    })

                total_offers_extracted += len(extracted_offers)
                total_offers_matched += matched_count

                summary_results[key] = {
                    "extracted_count": len(extracted_offers),
                    "matched_count": matched_count,
                    "sample": processed_items[:3]
                }

            except Exception as e:
                logger.error(f"Failed to ingest daily deals for {key}: {e}")
                summary_results[key] = {"error": str(e)}

        logger.info("\n=========================================================================")
        logger.info(f"DAILY DEALS INGESTION COMPLETE: Extracted {total_offers_extracted} offers | Matched {total_offers_matched} to Canonical Products")
        logger.info("=========================================================================")

        return {
            "total_extracted": total_offers_extracted,
            "total_matched": total_offers_matched,
            "details": summary_results
        }

    def _generate_mock_daily_deals(self, key: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Mock fallback daily deals data for testing without live ZenRows tokens."""
        if "beauty" in config["niche"] or key in ["iherb", "sephora"]:
            return [
                {
                    "marketplace": config["marketplace"],
                    "title": "The Ordinary Niacinamide 10% + Zinc 1% High-Strength Vitamin Serum 30ml",
                    "brand": "The Ordinary",
                    "category": "Serums & Treatments",
                    "current_price": 5.90,
                    "original_price": 6.50,
                    "discount_percent": 9.2,
                    "currency": "USD",
                    "product_url": f"https://www.{key}.com/ordinary-niacinamide-deal",
                    "image_url": "https://m.media-amazon.com/images/I/ordinary.jpg",
                    "is_available": True
                },
                {
                    "marketplace": config["marketplace"],
                    "title": "CeraVe Moisturizing Cream for Normal to Dry Skin 454g Tub",
                    "brand": "CeraVe",
                    "category": "Moisturizers & Creams",
                    "current_price": 13.99,
                    "original_price": 16.99,
                    "discount_percent": 17.6,
                    "currency": "USD",
                    "product_url": f"https://www.{key}.com/cerave-cream-deal",
                    "image_url": "https://m.media-amazon.com/images/I/cerave.jpg",
                    "is_available": True
                }
            ]
        
        return [
            {
                "marketplace": config["marketplace"],
                "title": "Apple AirPods Pro (2nd Generation) Wireless Earbuds with MagSafe Case",
                "brand": "Apple",
                "asin": "B0B9356M39",
                "gtin": "194253397168",
                "category": "Smart Audio & Entertainment",
                "current_price": 189.99,
                "original_price": 249.00,
                "discount_percent": 23.7,
                "currency": "USD" if config["region"] != "AU" else "AUD",
                "product_url": f"https://www.{key}.com/airpods-pro-2-deal",
                "image_url": "https://m.media-amazon.com/images/I/airpods.jpg",
                "is_available": True
            },
            {
                "marketplace": config["marketplace"],
                "title": "Philips Hue White and Color Ambiance A19 E26 Smart Bulb",
                "brand": "Philips Hue",
                "mpn": "929002226601",
                "category": "Smart Lighting & Ambiance",
                "current_price": 39.99,
                "original_price": 49.99,
                "discount_percent": 20.0,
                "currency": "USD" if config["region"] != "AU" else "AUD",
                "product_url": f"https://www.{key}.com/hue-bulb-deal",
                "image_url": "https://m.media-amazon.com/images/I/hue.jpg",
                "is_available": True
            }
        ]
