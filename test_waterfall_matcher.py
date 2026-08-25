"""
Test Suite for 4-Tier Product Matching Waterfall Strategy.
Verifies GTIN, ASIN, Brand+MPN, Trigram Similarity, and Gray-Area Queueing across multi-marketplace offers.
"""

import sys
import logging
from typing import Dict, Any, List

from services.waterfall_matcher import WaterfallMatcher, calculate_trigram_similarity, normalize_title
from services.price_tracker import PriceTrackerEngine
from db.supabase_client import SupabaseManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("test_waterfall_matcher")

def run_tests():
    logger.info("=========================================================================")
    logger.info("  STARTING WATERFALL PRODUCT MATCHING ENGINE TEST SUITE")
    logger.info("=========================================================================")

    # 1. Mock Master Canonical Catalog
    mock_canonical_catalog: List[Dict[str, Any]] = [
        {
            "id": "canon-airpods-pro-2",
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
            "id": "canon-hue-bulb",
            "niche": "smart_home",
            "title": "Philips Hue White and Color Ambiance A19 E26 Smart Bulb",
            "brand": "Philips Hue",
            "model": "A19 E26",
            "mpn": "929002226601",
            "gtin_upc_ean": "046677548483",
            "category": "Smart Lighting & Ambiance"
        },
        {
            "id": "canon-ordinary-niacinamide",
            "niche": "beauty_skincare",
            "title": "The Ordinary Niacinamide 10% + Zinc 1% High-Strength Vitamin Serum 30ml",
            "brand": "The Ordinary",
            "variant": "30ml",
            "category": "Serums & Treatments"
        },
        {
            "id": "canon-cerave-cream-454g",
            "niche": "beauty_skincare",
            "title": "CeraVe Moisturizing Cream for Normal to Dry Skin 454g",
            "brand": "CeraVe",
            "variant": "454g",
            "category": "Moisturizers & Creams"
        }
    ]

    supabase = SupabaseManager()
    matcher = WaterfallMatcher(supabase=supabase, auto_link_threshold=0.85, gray_area_threshold=0.65)
    tracker = PriceTrackerEngine(supabase=supabase, matcher=matcher)

    test_passed = 0
    test_failed = 0

    # -------------------------------------------------------------------------
    # TEST 1: Tier 1 GTIN Exact Match
    # -------------------------------------------------------------------------
    logger.info("\n--- TEST 1: Tier 1 GTIN Match ---")
    offer_gtin = {
        "title": "Apple AirPods Pro 2 MagSafe",
        "brand": "Apple",
        "gtin": "194253397168",
        "marketplace": "ebay",
        "current_price": 189.99,
        "product_url": "https://www.ebay.com/itm/123456"
    }
    res1 = matcher.match_offer(offer_gtin, local_catalog=mock_canonical_catalog)
    if res1["match_tier"] == "tier1_gtin" and res1["canonical_product_id"] == "canon-airpods-pro-2":
        logger.info("✅ TEST 1 PASSED: Successfully matched via Tier 1 GTIN!")
        test_passed += 1
    else:
        logger.error(f"❌ TEST 1 FAILED: {res1}")
        test_failed += 1

    # -------------------------------------------------------------------------
    # TEST 2: Tier 2 ASIN Exact Match
    # -------------------------------------------------------------------------
    logger.info("\n--- TEST 2: Tier 2 ASIN Match ---")
    offer_asin = {
        "title": "Apple AirPods Pro (2nd Generation)",
        "brand": "Apple",
        "product_url": "https://www.amazon.com/dp/B0B9356M39?tag=affiliate",
        "marketplace": "amazon",
        "current_price": 199.00
    }
    res2 = matcher.match_offer(offer_asin, local_catalog=mock_canonical_catalog)
    if res2["match_tier"] == "tier2_asin" and res2["canonical_product_id"] == "canon-airpods-pro-2":
        logger.info("✅ TEST 2 PASSED: Successfully matched via Tier 2 ASIN!")
        test_passed += 1
    else:
        logger.error(f"❌ TEST 2 FAILED: {res2}")
        test_failed += 1

    # -------------------------------------------------------------------------
    # TEST 3: Tier 3 Brand + MPN Match
    # -------------------------------------------------------------------------
    logger.info("\n--- TEST 3: Tier 3 Brand + MPN Match ---")
    offer_mpn = {
        "title": "Philips Hue Smart LED Bulb A19",
        "brand": "Philips Hue",
        "mpn": "929002226601",
        "marketplace": "bestbuy",
        "current_price": 49.99,
        "product_url": "https://www.bestbuy.com/site/123456.p"
    }
    res3 = matcher.match_offer(offer_mpn, local_catalog=mock_canonical_catalog)
    if res3["match_tier"] == "tier3_brand_mpn" and res3["canonical_product_id"] == "canon-hue-bulb":
        logger.info("✅ TEST 3 PASSED: Successfully matched via Tier 3 Brand+MPN!")
        test_passed += 1
    else:
        logger.error(f"❌ TEST 3 FAILED: {res3}")
        test_failed += 1

    # -------------------------------------------------------------------------
    # TEST 4: Tier 4 Trigram Similarity High Match (>= 85%)
    # -------------------------------------------------------------------------
    logger.info("\n--- TEST 4: Tier 4 High Trigram Similarity Match (Beauty/Skincare) ---")
    offer_trigram = {
        "title": "The Ordinary Niacinamide 10% + Zinc 1% High-Strength Vitamin Serum 30ml",
        "brand": "The Ordinary",
        "marketplace": "sephora",
        "current_price": 6.00,
        "product_url": "https://www.sephora.com/product/123456"
    }
    res4 = matcher.match_offer(offer_trigram, local_catalog=mock_canonical_catalog)
    if res4["match_tier"] == "tier4_trigram" and res4["canonical_product_id"] == "canon-ordinary-niacinamide":
        logger.info(f"✅ TEST 4 PASSED: Successfully matched via Tier 4 Trigram Similarity ({res4['confidence_score']*100:.1f}%)!")
        test_passed += 1
    else:
        logger.error(f"❌ TEST 4 FAILED: {res4}")
        test_failed += 1

    # -------------------------------------------------------------------------
    # TEST 5: Gray-Area Queueing (65% <= Similarity < 85%)
    # -------------------------------------------------------------------------
    logger.info("\n--- TEST 5: Gray-Area Queueing (65% - 84% Similarity) ---")
    offer_gray = {
        "title": "CeraVe Moisturizing Cream for Dry Skin 454g Tub",
        "brand": "CeraVe",
        "marketplace": "boots",
        "current_price": 14.50,
        "product_url": "https://www.boots.com/cerave-cream-454g"
    }
    res5 = matcher.match_offer(offer_gray, local_catalog=mock_canonical_catalog)
    if res5["match_tier"] == "queued_review" and res5["suggested_canonical_id"] == "canon-cerave-cream-454g":
        logger.info(f"✅ TEST 5 PASSED: Gray-area match ({res5['confidence_score']*100:.1f}%) successfully routed to unmatched_queue!")
        test_passed += 1
    else:
        logger.error(f"❌ TEST 5 FAILED: {res5}")
        test_failed += 1

    # -------------------------------------------------------------------------
    # TEST 6: Tier 5 New Canonical Creation (< 65%)
    # -------------------------------------------------------------------------
    logger.info("\n--- TEST 6: Tier 5 New Canonical Creation ---")
    offer_new = {
        "title": "Dyson Zone Absolute Noise Cancelling Headphones",
        "brand": "Dyson",
        "marketplace": "amazon",
        "current_price": 699.99,
        "product_url": "https://www.amazon.com/dp/B0CX123456"
    }
    res6 = matcher.match_offer(offer_new, local_catalog=mock_canonical_catalog)
    if res6["match_tier"] == "tier5_new_canonical" and res6["canonical_product_id"]:
        logger.info(f"✅ TEST 6 PASSED: Created new canonical product record ID: {res6['canonical_product_id']}!")
        test_passed += 1
    else:
        logger.error(f"❌ TEST 6 FAILED: {res6}")
        test_failed += 1

    # -------------------------------------------------------------------------
    # TEST 7: PriceTracker Engine End-to-End Offer Ingestion & 3+ Offers Rule
    # -------------------------------------------------------------------------
    logger.info("\n--- TEST 7: End-to-End Ingestion & Offer Linking ---")
    offers_list = [
        {"title": "The Ordinary Niacinamide 10% + Zinc 1% High-Strength Vitamin Serum 30ml", "brand": "The Ordinary", "marketplace": "sephora", "current_price": 6.00, "product_url": "https://www.sephora.com/niacinamide"},
        {"title": "The Ordinary Niacinamide 10% + Zinc 1% High-Strength Vitamin Serum 30ml", "brand": "The Ordinary", "marketplace": "ulta", "current_price": 6.00, "product_url": "https://www.ulta.com/niacinamide"},
        {"title": "The Ordinary Niacinamide 10% + Zinc 1% High-Strength Vitamin Serum 30ml", "brand": "The Ordinary", "marketplace": "boots", "current_price": 6.50, "product_url": "https://www.boots.com/niacinamide"}
    ]

    matched_canonical_ids = set()
    for off in offers_list:
        out = tracker.process_incoming_offer(off, local_catalog=mock_canonical_catalog)
        cid = out["match"].get("canonical_product_id")
        matched_canonical_ids.add(cid)

    if len(matched_canonical_ids) == 1 and "canon-ordinary-niacinamide" in matched_canonical_ids:
        logger.info("✅ TEST 7 PASSED: 3 distinct retail offers successfully linked under 1 canonical product (satisfying 3+ Offers Rule for site view)!")
        test_passed += 1
    else:
        logger.error(f"❌ TEST 7 FAILED: {matched_canonical_ids}")
        test_failed += 1

    # -------------------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------------------
    logger.info("\n=========================================================================")
    logger.info(f"  TEST SUITE COMPLETE: {test_passed} PASSED, {test_failed} FAILED")
    logger.info("=========================================================================")

    if test_failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
