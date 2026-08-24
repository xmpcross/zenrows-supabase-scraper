import sys
import time
import argparse
import logging
from config import Config
from db.supabase_client import SupabaseManager
from scrapers.zenrows_client import ZenRowsFetcher
from scrapers.marketplace_scrapers import parse_marketplace_page
from services.price_tracker import PriceTrackerEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("main")

DEFAULT_MARKETPLACE_URLS = {
    "amazon": "https://www.amazon.com/gp/goldbox/?ie=UTF8&ref_=topnav_storetab_subnav_goldbox",
    "ebay": "https://www.ebay.com/deals",
    "walmart": "https://www.walmart.com/browse/electronics/3944",
    "bestbuy": "https://www.bestbuy.com/site/electronics/top-deals/pcmcat1563299784494.c",
    "target": "https://www.target.com/c/electronics/-/N-5xtg6",
    "newegg": "https://www.newegg.com/todays-deals",
    "aliexpress": "https://www.aliexpress.com/superdeals.html"
}

def scrape_marketplace_category(
    marketplace: str,
    url: str,
    category: str = "General",
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
        custom_params = None
        if "deal-of-the-day" in url.lower() or "deals" in url.lower() or "goldbox" in url.lower():
            custom_params = {"js_render": "true", "antibot": "true", "premium_proxy": "true", "proxy_country": "us"}

        html = fetcher.fetch_marketplace_html(url, marketplace, custom_params=custom_params)
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
    parser = argparse.ArgumentParser(description="ZenRows Multi-Marketplace Product Scraper & Supabase Price Tracker CLI")
    parser.add_argument("--marketplace", choices=["amazon", "ebay", "walmart", "bestbuy", "target", "newegg", "aliexpress", "all"], default="amazon", help="Target marketplace to scrape")
    parser.add_argument("--url", type=str, help="Target Web Page URL to scrape (defaults to category best sellers link)")
    parser.add_argument("--category", type=str, default="Electronics", help="Category label for products")
    parser.add_argument("--price-check", action="store_true", help="Run automated price check on all tracked products in Supabase")
    parser.add_argument("--compare", action="store_true", help="Display cross-marketplace price comparison table")
    parser.add_argument("--demo", action="store_true", help="Run offline test demo with sample HTML fixtures")

    args = parser.parse_args()

    if args.demo:
        from demo_seed import run_demo
        run_demo()
        return

    # Check configuration status
    missing_config = Config.validate()
    if missing_config:
        print("\n" + "!"*70)
        print(" WARNING: Missing setup credentials in .env file:")
        for key in missing_config:
            print(f"   - {key}")
        print("\n Please update .env with your ZENROWS_API_KEY, SUPABASE_URL, and SUPABASE_KEY.")
        print(" To test offline without API keys, run: python main.py --demo")
        print("!"*70 + "\n")

    fetcher = ZenRowsFetcher()
    supabase = SupabaseManager()
    tracker = PriceTrackerEngine(supabase=supabase, fetcher=fetcher)

    # 1. Price Check Mode
    if args.price_check:
        print("\n=== RUNNING AUTOMATED PRICE TRACKING CHECK ===")
        results = tracker.refresh_all_tracked_prices(marketplace=None if args.marketplace == "all" else args.marketplace)
        print(f"Refreshed prices for {len(results)} items.")
        return

    # 2. Compare View Mode
    if args.compare:
        print("\n=== CROSS-MARKETPLACE PRICE COMPARISON MATRIX ===")
        products = supabase.get_tracked_products(limit=100)
        if products:
            tracker.print_price_comparison(products)
        else:
            print("No tracked products found in Supabase database. Run a scrape command first.")
        return

    # 3. Scrape Mode
    all_scraped_products = []
    target_marketplaces = ["amazon", "ebay", "walmart", "bestbuy", "target", "newegg", "aliexpress"] if args.marketplace == "all" else [args.marketplace]

    for mkp in target_marketplaces:
        target_url = args.url
        if not target_url:
            if args.category and args.category.lower() not in ["general", "deals", "today's deals", "top deals"]:
                import urllib.parse
                encoded_cat = urllib.parse.quote(args.category)
                if mkp == "amazon":
                    target_url = f"https://www.amazon.com/s?k={encoded_cat}"
                elif mkp == "ebay":
                    target_url = f"https://www.ebay.com/sch/i.html?_nkw={encoded_cat}"
                elif mkp == "walmart":
                    target_url = f"https://www.walmart.com/search?q={encoded_cat}"
                elif mkp == "bestbuy":
                    target_url = f"https://www.bestbuy.com/site/searchpage.jsp?st={encoded_cat}&intl=nosplash"
                elif mkp == "target":
                    target_url = f"https://www.target.com/s?searchTerm={encoded_cat}"
                elif mkp == "newegg":
                    target_url = f"https://www.newegg.com/p/pl?d={encoded_cat}"
                elif mkp == "aliexpress":
                    target_url = f"https://www.aliexpress.com/w/wholesale-{encoded_cat}.html"
                else:
                    target_url = DEFAULT_MARKETPLACE_URLS.get(mkp)
            else:
                target_url = DEFAULT_MARKETPLACE_URLS.get(mkp)

        print(f"\n--- SCRAPING {mkp.upper()} TOP PRODUCTS ---")
        print(f"Target URL : {target_url}")
        print(f"Category   : {args.category}")
        
        prods = scrape_marketplace_category(
            marketplace=mkp,
            url=target_url,
            category=args.category,
            fetcher=fetcher,
            supabase=supabase
        )
        all_scraped_products.extend(prods)

    if all_scraped_products:
        print(f"\nSuccessfully processed {len(all_scraped_products)} marketplace items.")
        tracker.print_price_comparison(all_scraped_products)
        
        if supabase.is_connected():
            tracker.auto_create_comparison_groups()

if __name__ == "__main__":
    main()
