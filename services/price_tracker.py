import logging
import re
from typing import Dict, Any, List, Optional
from db.supabase_client import SupabaseManager
from scrapers.zenrows_client import ZenRowsFetcher
from scrapers.marketplace_scrapers import parse_marketplace_page
from services.waterfall_matcher import WaterfallMatcher, calculate_trigram_similarity

from services.affiliate_linker import AffiliateLinker

logger = logging.getLogger(__name__)

class PriceTrackerEngine:
    def __init__(
        self,
        supabase: Optional[SupabaseManager] = None,
        fetcher: Optional[ZenRowsFetcher] = None,
        matcher: Optional[WaterfallMatcher] = None,
        affiliate_linker: Optional[AffiliateLinker] = None
    ):
        self.supabase = supabase or SupabaseManager()
        self.fetcher = fetcher or ZenRowsFetcher()
        self.matcher = matcher or WaterfallMatcher(supabase=self.supabase)
        self.affiliate_linker = affiliate_linker or AffiliateLinker()

    def refresh_product_price(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Re-scrapes a single product URL via ZenRows, extracts the latest price,
        and updates Supabase (which triggers automatic price_history logging).
        """
        product_url = product.get("product_url")
        marketplace = product.get("marketplace", "amazon")
        old_price = product.get("current_price")

        logger.info(f"Refreshing price for [{marketplace.upper()}] '{product.get('title')}' at {product_url}")

        try:
            html = self.fetcher.fetch_marketplace_html(product_url, marketplace)
            parsed_items = parse_marketplace_page(html, product_url, marketplace)

            if parsed_items:
                latest_item = parsed_items[0]
                new_price = latest_item.get("current_price")

                # Merge updated details into product record
                product["current_price"] = new_price
                product["is_available"] = latest_item.get("is_available", True)
                if new_price and old_price and new_price < old_price:
                    logger.info(f"PRICE DROP DETECTED for '{product.get('title')}': ${old_price} -> ${new_price}")

                if self.supabase.is_connected():
                    self.supabase.upsert_marketplace_product(product)

                return {
                    "product_id": product.get("id"),
                    "title": product.get("title"),
                    "marketplace": marketplace,
                    "old_price": old_price,
                    "new_price": new_price,
                    "price_changed": old_price != new_price
                }
        except Exception as e:
            logger.error(f"Error refreshing price for {product_url}: {e}")

        return {"product_id": product.get("id"), "error": "Failed to refresh price"}

    def refresh_all_tracked_prices(self, marketplace: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetches all tracked products from Supabase and refreshes their current prices.
        """
        products = self.supabase.get_tracked_products(marketplace=marketplace)
        logger.info(f"Found {len(products)} products to refresh price data.")

        results = []
        for prod in products:
            res = self.refresh_product_price(prod)
            results.append(res)
        return results

    def normalize_title(self, title: str) -> str:
        """
        Normalizes product title for matching identical products across marketplaces.
        """
        t = title.lower()
        t = re.sub(r"[^\w\s]", "", t)
        words = [w for w in t.split() if len(w) > 2 and w not in ["the", "and", "for", "with", "new"]]
        return " ".join(sorted(words[:6]))

    def process_incoming_offer(
        self,
        raw_offer: Dict[str, Any],
        local_catalog: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Runs incoming scraped offer through WaterfallMatcher (GTIN -> ASIN -> Brand+MPN -> Trigram),
        links canonical_product_id, and upserts into marketplace_products table.
        """
        # Monetize URL with Affiliate Tracking Tags
        orig_url = raw_offer.get("product_url", "")
        raw_offer["product_url"] = self.affiliate_linker.monetize_url(
            url=orig_url, 
            marketplace=raw_offer.get("marketplace", "")
        )

        match_result = self.matcher.match_offer(raw_offer, local_catalog=local_catalog)
        canonical_id = match_result.get("canonical_product_id")

        raw_offer["canonical_product_id"] = canonical_id

        if self.supabase.is_connected():
            upsert_res = self.supabase.upsert_marketplace_product(raw_offer)
            return {
                "match": match_result,
                "upsert": upsert_res
            }

        return {
            "match": match_result,
            "offer": raw_offer
        }

    def auto_create_comparison_groups(self) -> int:
        """
        Scans marketplace_products in Supabase, groups listings with similar normalized titles,
        and links them under product_comparison_groups for cross-marketplace comparison.
        """
        products = self.supabase.get_tracked_products(limit=200)
        if not products:
            return 0

        title_buckets: Dict[str, List[Dict[str, Any]]] = {}
        for prod in products:
            norm = self.normalize_title(prod.get("title", ""))
            if norm not in title_buckets:
                title_buckets[norm] = []
            title_buckets[norm].append(prod)

        groups_created = 0
        for norm_title, items in title_buckets.items():
            if len(items) > 1:
                # Group items across different marketplaces
                marketplaces = set(item.get("marketplace") for item in items)
                if len(marketplaces) > 1:
                    group_name = items[0].get("title")
                    group = self.supabase.create_comparison_group(name=group_name, normalized_title=norm_title)
                    group_id = group.get("id")
                    if group_id:
                        for item in items:
                            if item.get("id"):
                                self.supabase.link_product_to_group(group_id, item.get("id"))
                        groups_created += 1

        logger.info(f"Auto-created {groups_created} cross-marketplace comparison groups.")
        return groups_created

    def print_price_comparison(self, products: List[Dict[str, Any]]) -> str:
        """
        Renders a human-readable text comparison table of products across marketplaces.
        """
        lines = []
        lines.append("\n" + "=" * 90)
        lines.append(f"{'MARKETPLACE':<12} | {'PRODUCT TITLE':<45} | {'PRICE':<10} | {'RANK':<6} | {'RATING':<6}")
        lines.append("=" * 90)

        # Sort products by price ascending
        valid_prods = sorted(products, key=lambda x: x.get("current_price") or 999999)

        for p in valid_prods:
            mkp = str(p.get("marketplace", "")).upper()
            title = str(p.get("title", ""))[:42] + ("..." if len(str(p.get("title", ""))) > 42 else "")
            price = f"${p.get('current_price'):.2f}" if p.get("current_price") is not None else "N/A"
            rank = f"#{p.get('rank_position')}" if p.get("rank_position") else "-"
            rating = f"{p.get('rating')}/5" if p.get("rating") else "-"
            lines.append(f"{mkp:<12} | {title:<45} | {price:<10} | {rank:<6} | {rating:<6}")

        lines.append("=" * 90 + "\n")
        output = "\n".join(lines)
        clean_output = output.encode("ascii", "ignore").decode("ascii")
        print(clean_output)
        return clean_output
