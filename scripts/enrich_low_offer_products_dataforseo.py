import os
import sys
import logging
import argparse
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Any

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scrapers.dataforseo_client import DataForSEOFetcher
from db.supabase_client import SupabaseManager
from services.price_tracker import PriceTrackerEngine
from config import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("enrich_low_offer_products")

def enrich_low_offer_products(region: str = "US", max_products: int = 50, dry_run: bool = False):
    logger.info("=========================================================================")
    logger.info("  DATAFORSEO OFFER ENRICHMENT PIPELINE FOR PRODUCTS WITH < 3 OFFERS")
    logger.info("=========================================================================")

    dfs = DataForSEOFetcher()
    if not dfs.is_configured:
        raise SystemExit("DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD are not configured in .env")

    supabase = SupabaseManager()
    if not supabase.is_connected():
        raise SystemExit("SUPABASE_URL and SUPABASE_KEY are not configured or connection failed")

    tracker = PriceTrackerEngine(supabase=supabase)

    # 1. Retrieve all canonical products and marketplace offers
    logger.info("Querying Supabase for canonical products and active marketplace offers...")
    prods_res = supabase.client.table("canonical_products").select("id, title, brand, model, asin, category, niche, gtin_upc_ean").execute()
    prods = prods_res.data or []

    mkp_res = supabase.client.table("marketplace_products").select("id, canonical_product_id, marketplace, is_available").execute()
    mkp_offers = mkp_res.data or []

    # 2. Count active offers per canonical product
    offer_counts = defaultdict(int)
    for offer in mkp_offers:
        cid = offer.get("canonical_product_id")
        if cid and offer.get("is_available") != False:
            offer_counts[cid] += 1

    # 3. Filter products with < 3 active offers
    low_offer_prods = [p for p in prods if offer_counts[p["id"]] < 3]
    logger.info(f"Total Canonical Products: {len(prods)}")
    logger.info(f"Products already with >= 3 offers: {len(prods) - len(low_offer_prods)}")
    logger.info(f"Products needing offer enrichment (< 3 offers): {len(low_offer_prods)}")

    if not low_offer_prods:
        logger.info("All canonical products already have 3 or more active offers! Nothing to enrich.")
        return

    target_prods = low_offer_prods[:max_products]
    logger.info(f"Enriching up to {len(target_prods)} products in this run (Region: {region})...\n")

    enriched_count = 0
    new_offers_added = 0
    now_published = 0

    for idx, prod in enumerate(target_prods, 1):
        cid = prod["id"]
        current_count = offer_counts[cid]
        title = prod.get("title", "")
        brand = prod.get("brand") or ""
        asin = prod.get("asin")
        
        # Build search query
        if brand and brand.lower() not in title.lower():
            query = f"{brand} {title}"
        else:
            query = title
            
        # Clean title for clean search query (remove discount badges/long promo text)
        query = query.split("|")[0].split("- Limited")[0].strip()[:80]

        logger.info(f"[{idx}/{len(target_prods)}] Product: '{title[:60]}...' (Current Offers: {current_count})")
        logger.info(f"   ► DataForSEO Search Query: '{query}'")

        if dry_run:
            logger.info("   [DRY RUN] Skipping API call and database writes.")
            continue

        dfs_offers = dfs.search_google_shopping_offers(
            keyword=query,
            region=region,
            category=prod.get("category", "General"),
            limit=10
        )

        offers_attached = 0
        for offer in dfs_offers:
            offer["niche"] = prod.get("niche") or "smart_home"
            offer["target_canonical"] = prod
            offer["target_canonical_id"] = cid
            # Attempt matching & persistence
            res = tracker.process_incoming_offer(offer)
            match_info = res.get("match", {})
            matched_cid = match_info.get("canonical_product_id")

            if matched_cid == cid:
                offers_attached += 1

        new_offers_added += len(dfs_offers)

        # Re-check updated offer count
        updated_offers_res = supabase.client.table("marketplace_products").select("id").eq("canonical_product_id", cid).eq("is_available", True).execute()
        new_count = len(updated_offers_res.data or [])
        logger.info(f"   ► Result: Attached {offers_attached} offers. New Total: {new_count} offers.")

        if new_count >= 3:
            now_published += 1
            logger.info(f"   🎉 PUBLISHED! Product now meets 3+ offer rule and is visible on nxt.bargains frontend!")

        enriched_count += 1
        print()

    logger.info("=========================================================================")
    logger.info(f"DATAFORSEO OFFER ENRICHMENT SUMMARY:")
    logger.info(f"  • Products Processed: {enriched_count}")
    logger.info(f"  • Total DataForSEO Offers Searched: {new_offers_added}")
    logger.info(f"  • Products Promoted to Published (>= 3 Offers): {now_published}")
    logger.info("=========================================================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enrich products with < 3 offers using DataForSEO Google Shopping API")
    parser.add_argument("--region", default="US", help="Target country region (US, AU, UK, CA, DE, NZ)")
    parser.add_argument("--limit", type=int, default=15, help="Max number of low-offer products to enrich")
    parser.add_argument("--dry-run", action="store_true", help="Simulate search without writing to database")
    args = parser.parse_args()

    enrich_low_offer_products(region=args.region, max_products=args.limit, dry_run=args.dry_run)
