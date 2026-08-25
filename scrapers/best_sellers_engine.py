"""
Best Sellers Ingestion & Curation Engine for nxt.bargains.

Fetches and updates top-ranking Best Seller products per category/niche
across Amazon, Google Shopping, and database comparison metrics.
"""

import logging
from typing import Dict, Any, List, Optional
from db.supabase_client import SupabaseManager
from scrapers.dataforseo_client import DataForSEOFetcher
from services.waterfall_matcher import WaterfallMatcher
from services.price_tracker import PriceTrackerEngine
from services.ai_content_rewriter import AIContentRewriter

logger = logging.getLogger(__name__)

# Configurable Best Seller Target Categories & Keywords per Niche
BEST_SELLER_CONFIG = {
    "smart_home": [
        "Smart Video Doorbells",
        "Robot Vacuum Cleaners",
        "Smart Security Cameras",
        "Smart Lighting & Bulbs",
        "Smart Thermostats"
    ],
    "beauty_skincare": [
        "Facial Serums & Treatments",
        "Sunscreen & Sun Care",
        "Moisturizers & Cream",
        "Haircare & Styling Tools",
        "Cleansers & Toners"
    ],
    "tech_deals": [
        "Wireless Earbuds & Headphones",
        "Smartwatches & Fitness Trackers",
        "Portable Bluetooth Speakers",
        "Smart Monitors & Displays"
    ]
}

class BestSellersEngine:
    def __init__(
        self,
        supabase: Optional[SupabaseManager] = None,
        dataforseo: Optional[DataForSEOFetcher] = None,
        matcher: Optional[WaterfallMatcher] = None,
        rewriter: Optional[AIContentRewriter] = None
    ):
        self.supabase = supabase or SupabaseManager()
        self.dataforseo = dataforseo or DataForSEOFetcher()
        self.matcher = matcher or WaterfallMatcher(supabase=self.supabase)
        self.tracker = PriceTrackerEngine(supabase=self.supabase, matcher=self.matcher)
        self.rewriter = rewriter or AIContentRewriter()

    def fetch_and_ingest_best_sellers(
        self,
        niche: str = "smart_home",
        region: str = "US",
        limit_per_category: int = 5
    ) -> Dict[str, Any]:
        """
        Fetches top Best Sellers for configured categories in a niche,
        runs them through Waterfall Matcher, enriches via AI, and stores in database.
        """
        target_categories = BEST_SELLER_CONFIG.get(niche, BEST_SELLER_CONFIG["smart_home"])
        logger.info(f"[Best Sellers] Ingesting Best Sellers for niche '{niche}' (Region: {region})...")

        total_extracted = 0
        total_matched = 0

        for category in target_categories:
            logger.info(f"   ► Ingesting Best Sellers for Category: '{category}'...")
            raw_offers = self.dataforseo.search_google_shopping_offers(
                query=f"best seller {category}",
                region=region,
                limit=limit_per_category
            )

            for offer in raw_offers:
                total_extracted += 1
                offer["region"] = region
                offer["niche"] = niche
                offer["category"] = category

                # Track position as best seller rank
                offer["rank_position"] = offer.get("rank_position") or total_extracted

                res = self.tracker.process_incoming_offer(offer)
                match_info = res.get("match", {})
                
                # If new canonical created, enrich via AI Copywriter
                if match_info.get("match_tier") == "tier5_new_canonical":
                    canon_payload = match_info.get("canonical", {})
                    ai_meta = self.rewriter.rewrite_product_content(
                        title=canon_payload.get("title", ""),
                        brand=canon_payload.get("brand"),
                        category=category,
                        niche=niche
                    )
                    canon_payload["seo_title"] = ai_meta.get("seo_title")
                    canon_payload["short_description"] = ai_meta.get("short_description")
                    canon_payload["description"] = ai_meta.get("description")
                    self.supabase.upsert_canonical_product(canon_payload)

                total_matched += 1

        logger.info(f"[Best Sellers] Ingestion Complete: Extracted {total_extracted} offers | Ingested {total_matched} Best Sellers.")
        return {
            "niche": niche,
            "region": region,
            "categories_processed": len(target_categories),
            "total_extracted": total_extracted,
            "total_matched": total_matched
        }

    def get_top_best_sellers(
        self,
        niche: str = "smart_home",
        region: str = "US",
        limit: int = 12
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top Best Sellers from Supabase ordered by discount percent, rating, and offer count.
        """
        if not self.supabase.is_connected():
            return []

        try:
            site_map = {"smart_home": "intl", "beauty_skincare": "beauty"}
            site = site_map.get(niche, "intl")
            valid_comps = self.supabase.get_valid_comparisons(site=site, limit=limit)
            
            # Sort by active offers count, discount percent, and rating
            sorted_best_sellers = sorted(
                valid_comps,
                key=lambda x: (
                    x.get("active_offers_count", 0),
                    x.get("max_discount_percent", 0) or 0
                ),
                reverse=True
            )
            return sorted_best_sellers[:limit]
        except Exception as e:
            logger.error(f"Error fetching top best sellers: {e}")
            return []
