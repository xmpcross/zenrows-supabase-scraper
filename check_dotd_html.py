from scrapers.zenrows_client import ZenRowsFetcher
from bs4 import BeautifulSoup

fetcher = ZenRowsFetcher()
url = "https://www.bestbuy.com/site/misc/deal-of-the-day/pcmcat248000050016.c?intl=nosplash"
html = fetcher.fetch_html(url, js_render=True, antibot=True, premium_proxy=True, custom_params={"proxy_country": "us"})
soup = BeautifulSoup(html, "lxml")

print("Title:", soup.title.string if soup.title else "No Title")
print("HTML Size:", len(html))
print("Divs:", len(soup.find_all("div")))
print("Links:", len(soup.find_all("a")))
