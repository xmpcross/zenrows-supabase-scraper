from scrapers.zenrows_client import ZenRowsFetcher
from bs4 import BeautifulSoup
from db.supabase_client import SupabaseManager
import re
from scrapers.marketplace_scrapers import clean_price, clean_text, extract_brand

fetcher = ZenRowsFetcher()
supabase = SupabaseManager()

url = "https://www.bestbuy.com/site/misc/deal-of-the-day/pcmcat248000050016.c?intl=nosplash"
print(f"Fetching Best Buy Deal of the Day via ZenRows JS Render: {url}")
html = fetcher.fetch_html(url, custom_params={"js_render": "true", "antibot": "true", "premium_proxy": "true", "proxy_country": "us"})

soup = BeautifulSoup(html, "lxml")
offers = soup.select("div.dotd-product-offer, div.offer-position-1, div[class*='offer' i], div[class*='dotd' i]")
print(f"Found {len(offers)} offer containers.")

products = []
seen = set()

for card in offers:
    title_elem = card.select_one("h1 a, h2 a, h3 a, h4 a, .heading-5 a, .heading-4 a, a[href*='/site/'], a[href*='/product/']")
    if not title_elem:
        continue
    title = title_elem.get_text(strip=True)
    if not title or len(title) < 5 or "See Deal of the Day" in title or "Best Buy" in title:
        continue

    link_elem = title_elem if title_elem.name == "a" else card.select_one("a[href*='/site/'], a[href*='/product/'], a[href*='/combo/']")
    if not link_elem:
        continue

    href = link_elem.get("href", "")
    if not href or href in seen:
        continue
    seen.add(href)

    product_url = f"https://www.bestbuy.com{href.split('?')[0]}" if href.startswith("/") else href.split("?")[0]
    
    sku_match = re.search(r"/(?:product|site|combo)/.*?/([A-Z0-9]{6,12}|\d{7})", product_url)
    sku_id = sku_match.group(1) if sku_match else None

    price_elem = card.select_one("span.customer-price, div.priceView-customer-price span, [class*='price' i]")
    price = clean_price(price_elem.get_text()) if price_elem else None

    img_elem = card.select_one("img.product-image, img.sku-image, img")
    image_url = img_elem.get("src") if img_elem else None

    products.append({
        "marketplace": "bestbuy",
        "external_id": sku_id,
        "title": clean_text(title),
        "brand": extract_brand(title, card),
        "category": "Deal of the Day",
        "current_price": price,
        "original_price": None,
        "currency": "USD",
        "product_url": product_url,
        "image_url": image_url,
        "is_available": True
    })

print(f"EXTRACTED {len(products)} LIVE BEST BUY DEALS OF THE DAY!")
for i, p in enumerate(products[:10]):
    print(f"#{i+1}: {p['title']} | Price: ${p['current_price']} | Brand: {p['brand']}")

if products and supabase.is_connected():
    supabase.upsert_marketplace_products_batch(products)
    print("UPSERTED TO SUPABASE CLEANLY!")
