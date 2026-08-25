"""
Smart Database-First Search & Price Provider for nxt.bargains.

Architecture:
  1. Searches Supabase Database FIRST for cached canonical products & multi-retailer offers (<10ms latency, zero API cost).
  2. Enforces the 3+ Active Offers Rule via database views.
  3. If missing or fewer than 3 offers, falls back to live DataForSEO / ZenRows ingestion, runs Waterfall Matcher, enriches via Gemini AI Rewriter, upserts to Supabase, and returns fresh comparison dataset.
"""

import logging
from typing import Dict, Any, List, Optional
from db.supabase_client import SupabaseManager
from scrapers.dataforseo_client import DataForSEOFetcher
from services.waterfall_matcher import WaterfallMatcher
from services.price_tracker import PriceTrackerEngine
from services.ai_content_rewriter import AIContentRewriter

logger = logging.getLogger(__name__)

class SmartSearchProvider:
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

    def get_product_comparison(
        self,
        keyword: str,
        region: str = "US",
        niche: str = "smart_home",
        site: str = "intl",
        min_offers: int = 3
    ) -> Dict[str, Any]:
        """
        Database-First Product Search & Comparison Provider:
        Checks Supabase first -> Falls back to DataForSEO/ZenRows if missing or < 3 offers.
        """
        logger.info(f"[Smart Search] Searching for '{keyword}' (Region: {region}, Niche: {niche})...")

        # STEP 1: Query Supabase Database First
        cached_results = []
        if self.supabase.is_connected():
            valid_comparisons = self.supabase.get_valid_comparisons(site=site, limit=50)
            kw_lower = keyword.lower()
            for comp in valid_comparisons:
                c_title = comp.get("canonical_title", "").lower()
                c_brand = (comp.get("brand") or "").lower()
                if kw_lower in c_title or kw_lower in c_brand:
                    cached_results.append(comp)

        if cached_results:
            logger.info(f"   ► SUPABASE CACHE HIT! Found {len(cached_results)} matching products with >= 3 offers.")
            return {
                "source": "supabase_cache",
                "keyword": keyword,
                "region": region,
                "count": len(cached_results),
                "products": cached_results
            }

        # STEP 2: Fallback to Live DataForSEO / ZenRows Search
        logger.info(f"   ► SUPABASE CACHE MISS or < {min_offers} offers. Triggering live DataForSEO fetch...")
        raw_offers = self.dataforseo.search_google_shopping_offers(keyword, region=region, limit=10)

        ingested_count = 0
        canonical_ids = set()

        for offer in raw_offers:
            offer["region"] = region
            offer["niche"] = niche

            res = self.tracker.process_incoming_offer(offer)
            match_info = res.get("match", {})
            cid = match_info.get("canonical_product_id")

            if match_info.get("match_tier") == "tier5_new_canonical":
                canon_payload = match_info.get("canonical", {})
                ai_meta = self.rewriter.rewrite_product_content(
                    title=canon_payload.get("title", ""),
                    brand=canon_payload.get("brand"),
                    category=canon_payload.get("category", "General"),
                    niche=niche
                )
                canon_payload["seo_title"] = ai_meta.get("seo_title")
                canon_payload["short_description"] = ai_meta.get("short_description")
                canon_payload["description"] = ai_meta.get("description")
                self.supabase.upsert_canonical_product(canon_payload)

            if cid:
                canonical_ids.add(cid)
                ingested_count += 1

        # Re-query Supabase to return fresh canonical comparison set
        fresh_comparisons = self.supabase.get_valid_comparisons(site=site, limit=50) if self.supabase.is_connected() else []
        filtered_fresh = [c for c in fresh_comparisons if any(cid == c.get("canonical_product_id") for cid in canonical_ids)]

        return {
            "source": "live_dataforseo_ingest",
            "keyword": keyword,
            "region": region,
            "offers_ingested": ingested_count,
            "products": filtered_fresh if filtered_fresh else fresh_comparisons
        }
