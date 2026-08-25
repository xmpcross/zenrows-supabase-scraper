"""
Migration Script: Strapi CMS to Supabase PostgreSQL Database.
Fetches all existing legacy products and offer listings from Strapi (cms.fxnstudio.com),
runs them through WaterfallMatcher, and populates your Supabase PostgreSQL database tables.
"""

import sys
import logging
from typing import Dict, Any, List

from db.strapi_client import StrapiManager
from db.supabase_client import SupabaseManager
from services.waterfall_matcher import WaterfallMatcher, normalize_title

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("migrate_strapi_to_supabase")

def run_migration():
    logger.info("=========================================================================")
    logger.info("  STARTING MIGRATION PIPELINE: STRAPI CMS -> SUPABASE POSTGRESQL")
    logger.info("=========================================================================")

    strapi = StrapiManager()
    supabase = SupabaseManager()
    matcher = WaterfallMatcher(supabase=supabase)

    # 1. Fetch all Canonical Products from Strapi
    logger.info("Fetching existing canonical products from Strapi REST API...")
    strapi_products = strapi.fetch_all_canonical_products()
    logger.info(f"Retrieved {len(strapi_products)} canonical products from Strapi.")

    migrated_canonicals = 0
    if supabase.is_connected() and strapi_products:
        for p in strapi_products:
            payload = {
                "title": p.get("title"),
                "brand": p.get("brand"),
                "model": p.get("model") or p.get("mpn"),
                "mpn": p.get("mpn"),
                "asin": p.get("asin"),
                "gtin_upc_ean": p.get("gtin_upc_ean") or p.get("gtin"),
                "normalized_title": normalize_title(p.get("title", "")),
                "category": p.get("category", "General"),
                "description": p.get("description") or p.get("summary_description")
            }
            res = supabase.upsert_canonical_product(payload)
            if res.get("status") == "success":
                migrated_canonicals += 1

    # 2. Fetch all Offers from Strapi
    logger.info("Fetching existing retailer offers from Strapi REST API...")
    strapi_offers = strapi.fetch_all_offers()
    logger.info(f"Retrieved {len(strapi_offers)} retailer offers from Strapi.")

    migrated_offers = 0
    if supabase.is_connected() and strapi_offers:
        for offer in strapi_offers:
            # Process offer through Waterfall Matcher to resolve Supabase canonical ID
            match_res = matcher.match_offer(offer)
            cid = match_res.get("canonical_product_id")

            offer_payload = {
                "canonical_product_id": cid,
                "marketplace": offer.get("retailer") or offer.get("marketplace", "generic"),
                "region": offer.get("region", "US"),
                "title": offer.get("title") or offer.get("name", "Product Offer"),
                "current_price": offer.get("current_price") or offer.get("price"),
                "original_price": offer.get("original_price"),
                "currency": offer.get("currency", "USD"),
                "product_url": offer.get("product_url") or offer.get("url"),
                "image_url": offer.get("image_url"),
                "is_available": offer.get("is_available", True)
            }

            res = supabase.upsert_marketplace_product(offer_payload)
            if res.get("status") == "success":
                migrated_offers += 1

    logger.info("=========================================================================")
    logger.info("  MIGRATION PIPELINE COMPLETE!")
    logger.info(f"  • Strapi Canonical Products Migrated to Supabase: {migrated_canonicals} / {len(strapi_products)}")
    logger.info(f"  • Strapi Retailer Offers Migrated to Supabase: {migrated_offers} / {len(strapi_offers)}")
    logger.info("=========================================================================")

if __name__ == "__main__":
    run_migration()
