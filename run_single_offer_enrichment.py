"""
Runner script for Single-Offer Product Enrichment Engine.
Identifies products with fewer than 3 offers in Supabase, executes targeted DataForSEO searches,
and upgrades them to satisfy the 3+ Offers Rule for nxt.bargains frontend sites.
"""

import sys
import logging
from services.single_offer_enricher import SingleOfferEnricher

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("run_single_offer_enrichment")

def main():
    enricher = SingleOfferEnricher()
    res = enricher.enrich_single_offer_products(limit=10, region="US")
    print(f"\nEnrichment Summary: Processed {res['enriched_count']} products | Upgraded {res['upgraded_to_3plus']} products to 3+ Active Offers!")

if __name__ == "__main__":
    main()
