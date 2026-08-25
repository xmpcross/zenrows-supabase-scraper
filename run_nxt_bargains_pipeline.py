"""
Production Orchestrator Pipeline for nxt.bargains (Strapi CMS).

Combines:
  1. DataForSEO Merchant API (Broad multi-offer search across Google Shopping)
  2. ZenRows Daily Deals Scrapers (Amazon, Best Buy, eBay, Walmart, iHerb, Sephora)
  3. 4-Tier Waterfall Product Matcher (GTIN -> ASIN -> Brand+MPN -> Trigram Similarity)
  4. Gemini AI Content Rewriter (Unique SEO titles & 2-sentence summaries)
  5. Strapi CMS API Integration (nxt.bargains canonical-products and offers)
"""

import sys
import logging
from typing import List, Dict, Any

from db.dual_db_client import DualDatabaseManager
from scrapers.dataforseo_client import DataForSEOFetcher
from scrapers.daily_deals_engine import DailyDealsIngestionEngine
from services.waterfall_matcher import WaterfallMatcher
from services.price_tracker import PriceTrackerEngine
from services.ai_content_rewriter import AIContentRewriter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("nxt_bargains_pipeline")

def run_nxt_bargains_pipeline():
    logger.info("=========================================================================")
    logger.info("  LAUNCHING NXT.BARGAINS PRODUCTION PIPELINE (DUAL SUPABASE + STRAPI SYNC)")
    logger.info("=========================================================================")

    # Initialize Dual Database Sync Manager (Supabase + Strapi)
    dual_db = DualDatabaseManager()
    matcher = WaterfallMatcher(supabase=dual_db)
    tracker = PriceTrackerEngine(supabase=dual_db, matcher=matcher)
    rewriter = AIContentRewriter()
    dataforseo = DataForSEOFetcher()
    deals_engine = DailyDealsIngestionEngine(supabase=dual_db, tracker=tracker)

    # 1. SAMPLE SEED CANONICAL CATALOG FOR DEMO / TEST VERIFICATION
    local_catalog: List[Dict[str, Any]] = [
        {
            "id": "strapi-airpods-pro-2",
            "niche": "smart_home",
            "title": "Apple AirPods Pro (2nd Generation) Wireless Earbuds with MagSafe Case",
            "brand": "Apple",
            "model": "AirPods Pro 2",
            "gtin_upc_ean": "194253397168",
            "asin": "B0B9356M39",
            "mpn": "MQD83AM/A",
            "category": "Smart Audio & Entertainment"
        },
        {
            "id": "strapi-ring-doorbell-4",
            "niche": "smart_home",
            "title": "Ring Video Doorbell 4 Smart Security Doorbell",
            "brand": "Ring",
            "model": "Doorbell 4",
            "asin": "B08N5NQ869",
            "category": "Smart Security & Access"
        },
        {
            "id": "strapi-ordinary-niacinamide",
            "niche": "beauty_skincare",
            "title": "The Ordinary Niacinamide 10% + Zinc 1% High-Strength Vitamin Serum 30ml",
            "brand": "The Ordinary",
            "variant": "30ml",
            "category": "Serums & Treatments"
        }
    ]

    # PHASE 1: Broad Multi-Retailer Search via DataForSEO API
    logger.info("\n--- PHASE 1: Broad Multi-Offer Search via DataForSEO Merchant API ---")
    search_keywords = ["Ring Video Doorbell 4", "Apple AirPods Pro 2", "The Ordinary Niacinamide"]
    dfs_extracted_count = 0

    for kw in search_keywords:
        logger.info(f"Querying DataForSEO Shopping Offers for keyword: '{kw}'...")
        offers = dataforseo.search_google_shopping_offers(kw, region="US", limit=5)
        dfs_extracted_count += len(offers)

        for offer in offers:
            # Match offer via Waterfall Matcher & Sync to Strapi
            res = tracker.process_incoming_offer(offer, local_catalog=local_catalog)
            match_info = res.get("match", {})
            
            # If new canonical product created, enrich with AI Content Rewriter
            if match_info.get("match_tier") == "tier5_new_canonical":
                canon_payload = match_info.get("canonical", {})
                ai_meta = rewriter.rewrite_product_content(
                    title=canon_payload.get("title", ""),
                    brand=canon_payload.get("brand"),
                    category=canon_payload.get("category", "General"),
                    niche=canon_payload.get("niche", "smart_home")
                )
                canon_payload["seo_title"] = ai_meta.get("seo_title")
                canon_payload["short_description"] = ai_meta.get("short_description")
                canon_payload["description"] = ai_meta.get("description")
                dual_db.upsert_canonical_product(canon_payload)

    logger.info(f"Phase 1 Complete: Processed {dfs_extracted_count} DataForSEO offers across Google Shopping.")

    # PHASE 2: Targeted Daily Deals Ingestion via ZenRows Scrapers
    logger.info("\n--- PHASE 2: Daily Deals Ingestion via ZenRows Scrapers ---")
    deals_summary = deals_engine.run_daily_deal_ingestion(local_catalog=local_catalog)
    logger.info(f"Phase 2 Complete: Ingested {deals_summary['total_extracted']} deals from ZenRows deal pages.")

    # PHASE 3: Top Best Sellers Ingestion & Ranking Update
    logger.info("\n--- PHASE 3: Top Best Sellers Ingestion & Category Ranking Update ---")
    from scrapers.best_sellers_engine import BestSellersEngine
    best_sellers_engine = BestSellersEngine(supabase=supabase, dataforseo=dfs_fetcher, matcher=matcher, rewriter=rewriter)
    best_sellers_summary = best_sellers_engine.fetch_and_ingest_best_sellers(niche="smart_home", region="US", limit_per_category=3)
    logger.info(f"Phase 3 Complete: Ingested {best_sellers_summary['total_extracted']} Best Sellers across top categories.")

    # PHASE 4: Single-Offer Product Enrichment (Upgrading < 3 Offers Products to Live Status)
    logger.info("\n--- PHASE 4: Single-Offer Product Enrichment (Upgrading Products to 3+ Offers) ---")
    from services.single_offer_enricher import SingleOfferEnricher
    enricher = SingleOfferEnricher(supabase=supabase, dataforseo=dfs_fetcher, matcher=matcher)
    enrichment_summary = enricher.enrich_single_offer_products(limit=5, region="US")
    logger.info(f"Phase 4 Complete: Enriched {enrichment_summary['enriched_count']} products | Upgraded {enrichment_summary['upgraded_to_3plus']} products to 3+ Active Offers!")

    logger.info("\n=========================================================================")
    logger.info("  NXT.BARGAINS PIPELINE EXECUTION SUCCESSFUL!")
    logger.info(f"  • DataForSEO Offers Processed: {dfs_extracted_count}")
    logger.info(f"  • ZenRows Deal Offers Ingested: {deals_summary['total_extracted']}")
    logger.info(f"  • Best Sellers Ingested: {best_sellers_summary['total_extracted']}")
    logger.info(f"  • Products Upgraded to 3+ Offers: {enrichment_summary['upgraded_to_3plus']}")
    logger.info("=========================================================================")

if __name__ == "__main__":
    run_nxt_bargains_pipeline()
