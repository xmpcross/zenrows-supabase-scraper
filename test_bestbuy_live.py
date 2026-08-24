from scrapers.zenrows_client import ZenRowsFetcher
from scrapers.marketplace_scrapers import parse_bestbuy_bestsellers
from db.supabase_client import SupabaseManager

fetcher = ZenRowsFetcher()
supabase = SupabaseManager()

url = "https://www.bestbuy.com/site/searchpage.jsp?st=laptops&intl=nosplash"
print(f"Fetching Best Buy search page: {url}")
html = fetcher.fetch_marketplace_html(url, "bestbuy", custom_params={"js_render": "true", "antibot": "true", "premium_proxy": "true", "proxy_country": "us"})

products = parse_bestbuy_bestsellers(html, "Laptops")
print(f"Extracted Best Buy Products: {len(products)}")

for i, p in enumerate(products[:5]):
    print(f"#{i+1}: {p['title']} - ${p['current_price']}")

if products and supabase.is_connected():
    res = supabase.upsert_marketplace_products_batch(products)
    print("Upserted Best Buy products to Supabase!")
