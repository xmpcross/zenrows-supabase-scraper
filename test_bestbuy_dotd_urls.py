from scrapers.zenrows_client import ZenRowsFetcher
from bs4 import BeautifulSoup

fetcher = ZenRowsFetcher()
urls = [
    "https://www.bestbuy.com/site/misc/deal-of-the-day/pcmcat248000050016.c?intl=nosplash",
    "https://www.bestbuy.com/site/misc/deal-of-the-day/pcmcat248000050016.c",
    "https://www.bestbuy.com/site/electronics/top-deals/pcmcat1563299784494.c?intl=nosplash"
]

for url in urls:
    print(f"\n--- Testing URL: {url} ---")
    html = fetcher.fetch_html(url, custom_params={"js_render": "true", "antibot": "true", "premium_proxy": "true", "proxy_country": "us"})
    soup = BeautifulSoup(html, "lxml")
    print("Page Title:", soup.title.string if soup.title else "No Title")
    print("HTML Length:", len(html))
    links = soup.select("a[href*='/site/'], a[href*='/product/'], a[href*='/combo/']")
    print("Product Links Found:", len(links))
    if links:
        print("Sample Link:", links[0].get("href"))
