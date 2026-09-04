"""Production product ingestion for nxt.bargains.

Supabase is the only persistence layer. DataForSEO is used for broad product
and offer discovery; ZenRows is used for direct retailer/deals collection.
Nothing runs unless the selected provider and Supabase are configured.
"""

import argparse
import logging

from config import Config
from db.supabase_client import SupabaseManager
from scrapers.dataforseo_client import DataForSEOFetcher
from scrapers.daily_deals_engine import DailyDealsIngestionEngine, TARGET_DEAL_PAGES
from services.price_tracker import PriceTrackerEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("nxt_bargains_pipeline")


def parse_args():
    parser = argparse.ArgumentParser(description="Supabase-only nxt.bargains product ingestion")
    parser.add_argument("--provider", choices=["zenrows", "dataforseo", "hybrid"], default=Config.PRODUCT_PROVIDER)
    parser.add_argument("--keyword", action="append", default=[], help="Product query for DataForSEO; repeat as needed")
    parser.add_argument("--region", default="US")
    parser.add_argument("--niche", default="general")
    parser.add_argument("--category", default="General")
    parser.add_argument("--deal-target", action="append", choices=sorted(TARGET_DEAL_PAGES), default=[])
    return parser.parse_args()


def main():
    args = parse_args()
    missing = Config.validate_provider(args.provider)
    if missing:
        raise SystemExit("Missing required production configuration: " + ", ".join(missing))

    supabase = SupabaseManager()
    if not supabase.is_connected():
        raise SystemExit("Supabase connection failed; no provider calls were made")

    tracker = PriceTrackerEngine(supabase=supabase)
    summary = {"provider": args.provider, "dataforseo_offers": 0, "zenrows_offers": 0}

    if args.provider in {"dataforseo", "hybrid"}:
        if not args.keyword:
            logger.info("No --keyword supplied; skipping DataForSEO discovery")
        fetcher = DataForSEOFetcher()
        for keyword in args.keyword:
            offers = fetcher.search_google_shopping_offers(
                keyword=keyword,
                region=args.region,
                category=args.category,
                limit=10,
            )
            for offer in offers:
                offer["niche"] = args.niche
                tracker.process_incoming_offer(offer)
            summary["dataforseo_offers"] += len(offers)

    if args.provider in {"zenrows", "hybrid"}:
        deals = DailyDealsIngestionEngine(supabase=supabase, tracker=tracker).run_daily_deal_ingestion(
            deal_keys=args.deal_target or None,
        )
        summary["zenrows_offers"] = deals["total_extracted"]

        failed_targets = [
            target
            for target, result in deals.get("details", {}).items()
            if isinstance(result, dict) and result.get("error")
        ]
        if failed_targets:
            logger.error("ZenRows targets failed: %s", ", ".join(failed_targets))
            raise SystemExit(1)

    logger.info("Pipeline complete: %s", summary)


if __name__ == "__main__":
    main()
