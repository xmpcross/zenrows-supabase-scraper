"""
Single-Offer Product Enrichment Engine for nxt.bargains.

Identifies canonical products in the database that currently have fewer than 3 active offers,
executes targeted multi-retailer searches via DataForSEO, runs incoming offers through
WaterfallMatcher, and links 2+ additional retailer offers so products satisfy the 3+ Offers Site Rule!
"""

import logging
from typing import Dict, Any, List, Optional
from db.supabase_client import SupabaseManager
from scrapers.dataforseo_client import DataForSEOFetcher
from services.waterfall_matcher import WaterfallMatcher
from services.price_tracker import PriceTrackerEngine

logger = logging.getLogger(__name__)

class SingleOfferEnricher:
    def __init__(
        self,
        supabase: Optional[SupabaseManager] = None,
        dataforseo: Optional[DataForSEOFetcher] = None,
        matcher: Optional[WaterfallMatcher] = None
    ):
        self.supabase = supabase or SupabaseManager()
        self.dataforseo = dataforseo or DataForSEOFetcher()
        self.matcher = matcher or WaterfallMatcher(supabase=self.supabase)
        self.tracker = PriceTrackerEngine(supabase=self.supabase, matcher=self.matcher)

    def find_single_offer_canonicals(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Queries Supabase for canonical products that have fewer than 3 active retailer offers.
        """
        if not self.supabase.is_connected():
            logger.info("[Mock Mode] Simulated 3 single-offer canonical products.")
            return [
                {"id": "canon-ring-doorbell", "title": "Ring Video Doorbell 4", "brand": "Ring", "offer_count": 1},
                {"id": "canon-roborock-s8", "title": "Roborock S8 Pro Ultra Robot Vacuum", "brand": "Roborock", "offer_count": 1},
                {"id": "canon-nest-learning", "title": "Google Nest Learning Thermostat 3rd Gen", "brand": "Google", "offer_count": 1}
            ]

        try:
            # Query canonical products
            res = self.supabase.client.table("canonical_products").select("*, marketplace_products(id)").execute()
            data = res.data or []
            single_offer_items = []

            for item in data:
                mkp_offers = item.get("marketplace_products", [])
                offer_count = len(mkp_offers)
                if offer_count < 3:
                    single_offer_items.append({
                        "id": item.get("id"),
                        "title": item.get("title"),
                        "brand": item.get("brand"),
                        "gtin": item.get("gtin_upc_ean"),
                        "asin": item.get("asin"),
                        "offer_count": offer_count
                    })

            logger.info(f"Found {len(single_offer_items)} canonical products with < 3 active offers.")
            return single_offer_items[:limit]
        except Exception as e:
            logger.error(f"Error querying single offer canonicals from Supabase: {e}")
            return []

    def enrich_single_offer_products(self, limit: int = 10, region: str = "US") -> Dict[str, Any]:
        """
        Executes targeted searches for single-offer products to fetch Amazon, eBay, Walmart,
        Target, Best Buy, and Newegg offers, upgrading them to satisfy the 3+ Offers Rule.
        """
        target_items = self.find_single_offer_canonicals(limit=limit)
        if not target_items:
            logger.info("No single-offer products found requiring enrichment.")
            return {"status": "success", "enriched_count": 0, "upgraded_to_3plus": 0}

        logger.info(f"=========================================================================")
        logger.info(f"  STARTING SINGLE-OFFER ENRICHMENT PIPELINE ({len(target_items)} TARGET PRODUCTS)")
        logger.info(f"=========================================================================")

        enriched_count = 0
        upgraded_to_3plus = 0

        for item in target_items:
            c_id = item.get("id")
            title = item.get("title")
            brand = item.get("brand") or ""
            current_offers = item.get("offer_count", 1)

            search_query = f"{brand} {title}".strip()
            logger.info(f"\n   ► Enriching: '{title}' (Current Offers: {current_offers}) | Querying DataForSEO: '{search_query}'")

            # Fetch multi-merchant offers from DataForSEO
            new_offers = self.dataforseo.search_google_shopping_offers(search_query, region=region, limit=8)
            added_offers = 0

            for offer in new_offers:
                offer["region"] = region
                res = self.tracker.process_incoming_offer(offer)
                match_info = res.get("match", {})
                if match_info.get("canonical_product_id") == c_id:
                    added_offers += 1

            new_total_offers = current_offers + added_offers
            enriched_count += 1
            if new_total_offers >= 3:
                upgraded_to_3plus += 1
                logger.info(f"   ✅ UPGRADED TO LIVE STATUS! '{title}' now has {new_total_offers} active offers (Satisfies 3+ Offers Rule)!")
            else:
                logger.info(f"   ℹ Added {added_offers} new offers (Total: {new_total_offers}/3).")

        logger.info(f"=========================================================================")
        logger.info(f"  SINGLE-OFFER ENRICHMENT COMPLETE!")
        logger.info(f"  • Target Products Processed: {enriched_count}")
        logger.info(f"  • Upgraded to 3+ Offers (Live on Website): {upgraded_to_3plus}")
        logger.info(f"=========================================================================")

        return {
            "status": "success",
            "enriched_count": enriched_count,
            "upgraded_to_3plus": upgraded_to_3plus
        }
