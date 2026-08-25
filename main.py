import sys
import time
import argparse
import logging
from config import Config
from db.supabase_client import SupabaseManager
from scrapers.zenrows_client import ZenRowsFetcher
from scrapers.dataforseo_client import DataForSEOFetcher
from scrapers.marketplace_scrapers import parse_marketplace_page
from services.price_tracker import PriceTrackerEngine
from services.smart_home_matcher import SmartHomeMatcherEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("main")

DEFAULT_MARKETPLACE_URLS = {
    "amazon_au": "https://www.amazon.com.au/gp/bestsellers/electronics/",
    "jbhifi": "https://www.jbhifi.com.au/collections/home-appliances/smart-home-security",
    "harveynorman": "https://www.harveynorman.com.au/connected-home-smart-home.html",
    "thegoodguys": "https://www.thegoodguys.com.au/smart-home",
    "ebay_au": "https://www.ebay.com.au/b/Smart-Home-Electronics/184470/bn_7116521743",
    "amazon": "https://www.amazon.com/gp/bestsellers/electronics/",
    "bestbuy": "https://www.bestbuy.com/site/electronics/smart-home/pcmcat311200050005.c",
    "walmart": "https://www.walmart.com/browse/smart-home/3944_1229875",
    "target": "https://www.target.com/c/smart-home-electronics/-/N-55k0x"
}

def scrape_marketplace_category(
    marketplace: str,
    url: str,
    category: str = "Smart Home",
    fetcher: ZenRowsFetcher = None,
    supabase: SupabaseManager = None
):
    """
    Scrapes category top products from a specific marketplace using ZenRows presets
    and stores parsed products into Supabase.
    """
    fetcher = fetcher or ZenRowsFetcher()
    supabase = supabase or SupabaseManager()
    
    start_time = time.time()
    logger.info(f"Starting scrape for {marketplace.upper()} URL: {url}")
    
    status = "failed"
    products = []
    error_msg = None

    try:
        html = fetcher.fetch_marketplace_html(url, marketplace)
        products = parse_marketplace_page(html, url, marketplace, category)
        logger.info(f"Successfully extracted {len(products)} products from {marketplace.upper()}.")

        if supabase.is_connected() and products:
            supabase.upsert_marketplace_products_batch(products)
        status = "success"
    except Exception as e:
        logger.error(f"Failed to scrape {marketplace} URL {url}: {e}", exc_info=True)
        error_msg = str(e)

    execution_time_ms = int((time.time() - start_time) * 1000)

    if supabase.is_connected():
        supabase.log_scrape_run(
            target_url=url,
            marketplace=marketplace,
            target_type="bestsellers",
            status=status,
            items_count=len(products),
            execution_time_ms=execution_time_ms,
            error_message=error_msg
        )

    return products

def main():
    parser = argparse.ArgumentParser(description="ZenRows + Supabase Multi-Niche Price Comparison CLI")
    parser.add_argument("--site", choices=["au", "intl", "beauty"], default="au", help="Target site: 'au' (nxtsmarthome.com.au), 'intl' (nxtsmart.homes), or 'beauty' (www.bestlooking.skin)")
    parser.add_argument("--provider", choices=["auto", "dataforseo", "zenrows"], default="auto", help="Ingestion provider: 'dataforseo' (Google Shopping API), 'zenrows' (Direct Web Scraper), or 'auto'")
    parser.add_argument("--marketplace", type=str, default="auto", help="Target marketplace or 'auto' for site default")
    parser.add_argument("--url", type=str, help="Target Web Page URL to scrape")
    parser.add_argument("--category", type=str, default="General", help="Category label for products")
    parser.add_argument("--smarthome", action="store_true", help="Run smart home discovery and multi-offer matcher")
    parser.add_argument("--skincare", action="store_true", help="Run beauty & skincare discovery and multi-offer matcher")
    parser.add_argument("--min-offers", type=int, default=3, help="Minimum offers required per product (default 3)")
    parser.add_argument("--price-check", action="store_true", help="Run automated price check on tracked products")
    parser.add_argument("--compare", action="store_true", help="Display 3+ offer comparison matrix for target site")
    parser.add_argument("--demo", action="store_true", help="Run offline test demo with sample HTML fixtures")

    args = parser.parse_args()

    if args.demo:
        from demo_seed import run_demo
        run_demo()
        return

    fetcher = ZenRowsFetcher()
    supabase = SupabaseManager()
    tracker = PriceTrackerEngine(supabase=supabase, fetcher=fetcher)
    matcher = SmartHomeMatcherEngine(supabase=supabase, fetcher=fetcher)

    site_name = "nxtsmarthome.com.au" if args.site == "au" else ("www.bestlooking.skin" if args.site == "beauty" else "nxtsmart.homes")
    region_label = "AU (Australia)" if args.site == "au" else ("Global (US, UK, CA, EU, AU, NZ)" if args.site == "beauty" else "International (US, UK, CA, EU)")

    print("\n" + "="*80)
    print(f" [PRICE COMPARISON ENGINE] TARGET SITE: {site_name}")
    print(f" Region Scope: {region_label} | Min Offers Rule: {args.min_offers}+")
    print("="*80 + "\n")

    # 1. Compare View Mode (Querying 3+ offer views)
    if args.compare:
        print(f"=== FETCHING VALID COMPARISONS (MIN {args.min_offers} OFFERS) FOR: {site_name} ===")
        comparisons = supabase.get_valid_comparisons(site=args.site, limit=50)
        print(f"Found {len(comparisons)} canonical products with >= {args.min_offers} active offers:\n")
        
        for c in comparisons:
            print(f"-> [{c.get('category', 'General')}] {c.get('canonical_title')} ({c.get('brand')})")
            print(f"   Offers Count: {c.get('active_offers_count')} | Price Range: ${c.get('lowest_price_aud', c.get('lowest_price'))} - ${c.get('highest_price_aud', c.get('highest_price'))} {c.get('currency', 'USD')}")
            for offer in c.get('offers', []):
                print(f"   - {offer.get('retailer_name')}: ${offer.get('price')} ({offer.get('product_url')})")
            print("-" * 75)
        return

    # 2. Smart Home Seed & Matcher Mode
    if args.smarthome:
        target_marketplaces = ["amazon_au", "jbhifi", "harveynorman"] if args.site == "au" else ["amazon", "bestbuy", "walmart"]
        print(f"Running Smart Home Seed Crawl across: {target_marketplaces}")

        for mkp in target_marketplaces:
            url = DEFAULT_MARKETPLACE_URLS.get(mkp)
            print(f"\n--- SCRAPING {mkp.upper()} SMART HOME CATALOG ---")
            prods = scrape_marketplace_category(mkp, url, category=args.category, fetcher=fetcher, supabase=supabase)
            
            for prod in prods:
                canonical, created = matcher.find_or_create_canonical_product(prod)
                if created or True:
                    # Enforce fetching at least 3 offers
                    matcher.fetch_offers_for_canonical_product(canonical, region="AU" if args.site == "au" else "US")

        print("\nSmart Home catalog indexing complete. Run 'python main.py --site " + args.site + " --compare' to view valid 3-offer comparison sets.")
        return

    # 3. Standard Price Check Mode
    if args.price_check:
        print("\n=== RUNNING AUTOMATED PRICE TRACKING CHECK ===")
        results = tracker.refresh_all_tracked_prices()
        print(f"Refreshed prices for {len(results)} items.")
        return

    # Default fallback: run demo/help guidance
    print("Use --smarthome to discover products, or --compare to view current comparison sets.")

if __name__ == "__main__":
    main()

