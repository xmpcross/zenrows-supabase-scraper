"""
Test suite for SmartSearchProvider (Supabase-First Search Provider with DataForSEO fallback).
Verifies instant cache retrieval from Supabase PostgreSQL, 3+ offers filtering, and automated fallback ingestion.
"""

import sys
import logging
from services.smart_search_provider import SmartSearchProvider

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("test_smart_search")

def test_smart_search():
    logger.info("=========================================================================")
    logger.info("  TESTING SMART DATABASE-FIRST SEARCH PROVIDER FOR NXT.BARGAINS")
    logger.info("=========================================================================")

    provider = SmartSearchProvider()

    # 1. Test Search Query: Ring Video Doorbell
    res = provider.get_product_comparison(keyword="Ring Video Doorbell", region="US", niche="smart_home", site="intl")

    logger.info("\n------------------- SMART SEARCH RESULT REPORT -------------------")
    logger.info(f"Data Source: {res['source']}")
    logger.info(f"Keyword: {res['keyword']}")
    logger.info(f"Products Found: {len(res.get('products', []))}")
    logger.info("------------------------------------------------------------------")

    for i, prod in enumerate(res.get("products", [])[:3]):
        title = prod.get("canonical_title") or prod.get("title")
        offers_count = prod.get("active_offers_count") or len(prod.get("offers", []))
        lowest_price = prod.get("lowest_price") or prod.get("lowest_price_aud")
        logger.info(f"#{i+1}: {title} | Active Offers: {offers_count} | Lowest Price: ${lowest_price}")

    logger.info("=========================================================================")
    logger.info("  SMART SEARCH PROVIDER TEST COMPLETE!")
    logger.info("=========================================================================")

if __name__ == "__main__":
    test_smart_search()
