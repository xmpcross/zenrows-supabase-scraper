"""
Runner script for Daily Deals Ingestion Pipeline.
Executes daily deal scrapers against Amazon (US, AU, UK), Best Buy, eBay (US, AU), Walmart, iHerb, and Sephora deal URLs.
Links offers to master canonical products via WaterfallMatcher to satisfy the 3+ active offers site view rule.
"""

import sys
import logging
from typing import Dict, Any, List
from scrapers.daily_deals_engine import DailyDealsIngestionEngine
from db.supabase_client import SupabaseManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("run_daily_deals")

def main():
    logger.info("=========================================================================")
    logger.info("  STARTING AUTOMATED MULTI-RETAILER DAILY DEALS INGESTION PIPELINE")
    logger.info("=========================================================================")

    # Seed Canonical Product Fixtures for Local Verification
    local_canonical_catalog: List[Dict[str, Any]] = [
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
            "title": "CeraVe Moisturizing Cream for Normal to Dry Skin 454g Tub",
            "brand": "CeraVe",
            "variant": "454g",
            "category": "Moisturizers & Creams"
        }
    ]

    engine = DailyDealsIngestionEngine()
    results = engine.run_daily_deal_ingestion(local_catalog=local_canonical_catalog)

    logger.info("\n------------------- INGESTION SUMMARY REPORT -------------------")
    logger.info(f"Total Daily Deal Offers Extracted: {results['total_extracted']}")
    logger.info(f"Total Offers Linked to Canonical Products: {results['total_matched']}")
    logger.info("----------------------------------------------------------------")

    for key, detail in results["details"].items():
        if "error" in detail:
            logger.error(f"Target '{key}': FAILED ({detail['error']})")
        else:
            logger.info(f"Target '{key:<12}': Extracted {detail['extracted_count']} deals | Linked {detail['matched_count']} canonical offers")

    logger.info("=========================================================================")

if __name__ == "__main__":
    main()
