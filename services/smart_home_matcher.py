import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from db.supabase_client import SupabaseManager
from scrapers.zenrows_client import ZenRowsFetcher
from scrapers.marketplace_scrapers import parse_marketplace_page, clean_text, extract_brand

logger = logging.getLogger(__name__)

SMART_HOME_BRANDS = [
    "Ring", "Google Nest", "Nest", "Philips Hue", "Hue", "Eufy", "Arlo", "Ecobee",
    "Roborock", "Aqara", "TP-Link", "Kasa", "Tapo", "Sonos", "Eve", "Nanoleaf",
    "Blink", "Yale", "SwitchBot", "August", "Sensibo", "Netatmo", "Belkin", "Wemo",
    "Reolink", "Dyson", "iRobot", "Roomba", "Dreame", "Ecovacs", "Wyze", "Leviton",
    "Lutron", "Meross", "Govee", "Sennheiser", "Bose", "Apple", "Samsung", "LG"
]

SMART_HOME_CATEGORIES = {
    "security": ["doorbell", "camera", "lock", "alarm", "security", "chime", "keypad", "sensor", "floodlight"],
    "lighting": ["hue", "light", "bulb", "strip", "lamp", "switch", "dimmer", "govee", "nanoleaf"],
    "climate": ["thermostat", "radiator", "ac control", "sensibo", "climate", "temperature", "humidity"],
    "hubs": ["hub", "bridge", "homepod", "echo", "nest hub", "matter", "zigbee", "z-wave"],
    "vacuums": ["vacuum", "roborock", "roomba", "ecovacs", "dreame", "mop", "cleaner"],
    "audio": ["speaker", "soundbar", "sonos", "audio", "subwoofer", "bose"]
}

from services.ai_content_rewriter import AIContentRewriter

class SmartHomeMatcherEngine:
    def __init__(self, supabase: Optional[SupabaseManager] = None, fetcher: Optional[ZenRowsFetcher] = None):
        self.supabase = supabase or SupabaseManager()
        self.fetcher = fetcher or ZenRowsFetcher()
        self.rewriter = AIContentRewriter()

    def classify_smart_home_category(self, title: str) -> str:
        """Classifies product title into smart home subcategories."""
        t_lower = title.lower()
        for cat, keywords in SMART_HOME_CATEGORIES.items():
            if any(k in t_lower for k in keywords):
                if cat == "security":
                    return "Smart Security & Access"
                elif cat == "lighting":
                    return "Smart Lighting & Ambiance"
                elif cat == "climate":
                    return "Smart Climate & Energy"
                elif cat == "hubs":
                    return "Smart Hubs & Controllers"
                elif cat == "vacuums":
                    return "Robot Vacuums & Appliances"
                elif cat == "audio":
                    return "Smart Audio & Entertainment"
        return "Smart Home"

    def normalize_title(self, title: str) -> str:
        """Clean and normalize title for product matching."""
        t = title.lower()
        t = re.sub(r"[^\w\s]", "", t)
        stop_words = {"the", "a", "an", "and", "or", "for", "with", "in", "of", "new", "latest", "pack", "gen", "generation"}
        words = [w for w in t.split() if w not in stop_words and len(w) > 1]
        return " ".join(words)

    def extract_model_and_brand(self, title: str) -> Tuple[Optional[str], Optional[str]]:
        """Extracts brand and model identifiers from product title."""
        brand = None
        for b in SMART_HOME_BRANDS:
            if re.search(r"\b" + re.escape(b) + r"\b", title, re.IGNORECASE):
                brand = b
                break

        if not brand:
            brand = extract_brand(title)

        # Extract model candidate (numbers, version specs like v2, gen 4, pro, max, 4k)
        model_match = re.search(r"\b(v\d+|\d+nd gen|\d+rd gen|\d+th gen|gen \d+|pro|plus|ultra|max|4k|mini)\b", title, re.IGNORECASE)
        model = model_match.group(0).lower() if model_match else None

        return brand, model

    def calculate_similarity(self, title1: str, title2: str) -> float:
        """Calculates token overlap similarity between two titles (0.0 to 1.0)."""
        norm1 = set(self.normalize_title(title1).split())
        norm2 = set(self.normalize_title(title2).split())
        if not norm1 or not norm2:
            return 0.0
        intersection = norm1.intersection(norm2)
        union = norm1.union(norm2)
        return len(intersection) / len(union)

    def find_or_create_canonical_product(self, raw_product: Dict[str, Any], niche: str = "smart_home") -> Tuple[Dict[str, Any], bool]:
        """
        Finds existing canonical product in Supabase or creates a new AI-enriched master entry.
        """
        title = raw_product.get("title", "")
        gtin = raw_product.get("metadata", {}).get("gtin") or raw_product.get("metadata", {}).get("upc")
        brand, model = self.extract_model_and_brand(title)
        category = self.classify_smart_home_category(title)

        # If Supabase client connected, query existing canonical products
        if self.supabase.is_connected():
            if gtin:
                res = self.supabase.client.table("canonical_products").select("*").eq("gtin_upc_ean", gtin).execute()
                if res.data:
                    return res.data[0], False

            # Query by brand & similar title
            if brand:
                res = self.supabase.client.table("canonical_products").select("*").eq("brand", brand).execute()
                for existing in (res.data or []):
                    sim = self.calculate_similarity(title, existing.get("title", ""))
                    if sim >= 0.55:
                        return existing, False

        # Run AI Content Rewriter for unique SEO title & descriptions
        ai_enriched = self.rewriter.rewrite_product_content(
            title=title,
            brand=brand,
            category=category,
            raw_description=raw_product.get("short_description") or raw_product.get("description"),
            niche=niche
        )

        canonical_data = {
            "niche": niche,
            "title": ai_enriched.get("seo_title", title),
            "brand": brand or "Generic",
            "model": model,
            "gtin_upc_ean": gtin,
            "category": category,
            "image_url": raw_product.get("image_url"),
            "description": ai_enriched.get("description")
        }

        if self.supabase.is_connected():
            res = self.supabase.client.table("canonical_products").insert(canonical_data).execute()
            if res.data:
                logger.info(f"Created NEW Canonical Product (AI Enriched): '{canonical_data['title']}' [{category}]")
                return res.data[0], True

        return {**canonical_data, "id": "mock-canonical-id"}, True

from scrapers.dataforseo_client import DataForSEOFetcher

class SmartHomeMatcherEngine:
    def __init__(
        self,
        supabase: Optional[SupabaseManager] = None,
        fetcher: Optional[ZenRowsFetcher] = None,
        dataforseo_fetcher: Optional[DataForSEOFetcher] = None
    ):
        self.supabase = supabase or SupabaseManager()
        self.fetcher = fetcher or ZenRowsFetcher()
        self.dataforseo = dataforseo_fetcher or DataForSEOFetcher()
        self.rewriter = AIContentRewriter()

    def fetch_offers_for_canonical_product(
        self,
        canonical_product: Dict[str, Any],
        region: str = "AU",
        provider: str = "hybrid"
    ) -> List[Dict[str, Any]]:
        """
        Searches target regional stores via DataForSEO or ZenRows to find competing offers
        and ensure canonical product has AT LEAST 3 offers.
        """
        product_id = canonical_product.get("id")
        title = canonical_product.get("title")
        brand = canonical_product.get("brand", "")

        logger.info(f"Searching competing offers for '{title}' in Region '{region}' (Provider: {provider})...")

        search_query = f"{brand} {title}" if brand and brand not in title else title
        search_query_clean = "+".join(self.normalize_title(search_query).split()[:4])

        collected_offers = []

        # Use DataForSEO as primary when configured or requested
        if provider in ["dataforseo", "hybrid"] and self.dataforseo.is_configured:
            collected_offers = self.dataforseo.search_google_shopping_offers(
                keyword=search_query,
                region=region,
                category=canonical_product.get("category", "General")
            )

        # Fallback to ZenRows direct web scraper if DataForSEO produced < 3 offers
        if provider in ["zenrows", "hybrid"] and (provider == "zenrows" or len(collected_offers) < 3):
            if region == "AU":
                sources = [
                    ("amazon_au", f"https://www.amazon.com.au/s?k={search_query_clean}"),
                    ("jbhifi", f"https://www.jbhifi.com.au/search?query={search_query_clean}"),
                    ("harveynorman", f"https://www.harveynorman.com.au/catalogsearch/result/?q={search_query_clean}"),
                    ("thegoodguys", f"https://www.thegoodguys.com.au/search?q={search_query_clean}")
                ]
            else:
                sources = [
                    ("amazon_us", f"https://www.amazon.com/s?k={search_query_clean}"),
                    ("bestbuy", f"https://www.bestbuy.com/site/searchpage.jsp?st={search_query_clean}"),
                    ("walmart", f"https://www.walmart.com/search?q={search_query_clean}"),
                    ("target", f"https://www.target.com/s?searchTerm={search_query_clean}")
                ]

            for mkp, search_url in sources:
                try:
                    html = self.fetcher.fetch_marketplace_html(search_url, mkp)
                    parsed = parse_marketplace_page(html, search_url, mkp, category=canonical_product.get("category", "Smart Home"))
                    for item in parsed[:2]:
                        sim = self.calculate_similarity(title, item.get("title", ""))
                        if sim >= 0.40:
                            collected_offers.append(item)
                except Exception as e:
                    logger.warning(f"Error fetching ZenRows offers from {mkp}: {e}")

        # Attach canonical_product_id and save to Supabase
        for offer in collected_offers:
            offer["canonical_product_id"] = product_id

        if self.supabase.is_connected() and collected_offers:
            self.supabase.upsert_marketplace_products_batch(collected_offers)

        logger.info(f"Collected {len(collected_offers)} offers for canonical product '{title}'.")
        return collected_offers
