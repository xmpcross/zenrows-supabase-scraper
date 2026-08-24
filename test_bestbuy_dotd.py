from scrapers.zenrows_client import ZenRowsFetcher
from bs4 import BeautifulSoup
import re

fetcher = ZenRowsFetcher()
url = "https://www.bestbuy.com/site/misc/deal-of-the-day/pcmcat248000050016.c?id=pcmcat248000050016&intl=nosplash"
print(f"Fetching Best Buy Deal of the Day: {url}")
html = fetcher.fetch_marketplace_html(url, "bestbuy", custom_params={"js_render": "true", "antibot": "true", "premium_proxy": "true", "proxy_country": "us"})

soup = BeautifulSoup(html, "lxml")
print("HTML Size:", len(html))
print("Page Title:", soup.title.string if soup.title else "No Title")

# Search for deal of the day containers
offers = soup.select(".offer-position-1, .dotd-product-offer, [class*='offer' i], [class*='dotd' i], [class*='deal' i]")
print("Offer containers found:", len(offers))

# Look for links containing /site/
product_links = soup.select("a[href*='/site/'][href*='.p']")
print("Product links found:", len(product_links))

for i, a in enumerate(product_links[:10]):
    title = a.get_text(strip=True)
    href = a.get("href")
    card = a.find_parent("div")
    price_elem = card.select_one("[class*='price' i]") if card else None
    price = price_elem.get_text(strip=True) if price_elem else ""
    if title and len(title) > 5:
        print(f"Deal #{i+1}: {title} | Price: {price[:30]} | Link: {href[:60]}")
