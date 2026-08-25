import logging
from typing import Dict, Any, List, Optional
from supabase import create_client, Client
from config import Config

from services.category_classifier import classify_product_category

logger = logging.getLogger(__name__)

class SupabaseManager:
    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        self.url = url or Config.SUPABASE_URL
        self.key = key or Config.SUPABASE_KEY
        self.client: Optional[Client] = None
        
        if self.url and self.key and self.url != "https://your-project-id.supabase.co":
            try:
                self.client = create_client(self.url, self.key)
                logger.info("Successfully initialized Supabase client.")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
        else:
            logger.warning("Supabase URL or Key missing. Database operations will operate in mock/log mode.")

    def is_connected(self) -> bool:
        return self.client is not None

    def upsert_marketplace_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Upsert a marketplace product into 'marketplace_products' table.
        Triggers automatic price_history logging in PostgreSQL on price change.
        """
        if not self.client:
            logger.warning(f"[Mock DB] Skipping Supabase upsert for: {product_data.get('title')}")
            return {"status": "skipped", "reason": "No Supabase client connected"}

        try:
            # Auto-classify product category if missing or generic
            title = product_data.get("title", "")
            raw_cat = product_data.get("category", "")
            product_data["category"] = classify_product_category(title, raw_cat)

            response = self.client.table("marketplace_products").upsert(
                product_data, on_conflict="product_url"
            ).execute()
            logger.info(f"Upserted {product_data.get('marketplace', '').upper()} product: '{product_data.get('title')}' -> [{product_data['category']}]")
            return {"status": "success", "data": response.data}
        except Exception as e:
            logger.error(f"Error upserting product to Supabase: {e}")
            return {"status": "error", "error": str(e)}

    def upsert_marketplace_products_batch(self, products_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Batch upsert list of marketplace products.
        """
        results = []
        for prod in products_list:
            res = self.upsert_marketplace_product(prod)
            results.append(res)
        return results

    def get_tracked_products(self, marketplace: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch tracked marketplace products from Supabase.
        """
        if not self.client:
            return []

        try:
            query = self.client.table("marketplace_products").select("*")
            if marketplace:
                query = query.eq("marketplace", marketplace.lower())
            response = query.limit(limit).execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Failed to fetch tracked products: {e}")
            return []

    def get_price_history(self, listing_id: str) -> List[Dict[str, Any]]:
        """
        Fetch price change snapshots for a specific marketplace listing.
        """
        if not self.client:
            return []

        try:
            response = self.client.table("price_history") \
                .select("*") \
                .eq("listing_id", listing_id) \
                .order("recorded_at", desc=True) \
                .execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Failed to fetch price history for {listing_id}: {e}")
            return []

    def create_comparison_group(self, name: str, normalized_title: str, gtin_upc_ean: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a comparison group linking identical/similar products across marketplaces.
        """
        if not self.client:
            return {"id": "mock-group-id", "name": name}

        try:
            data = {
                "name": name,
                "normalized_title": normalized_title.lower().strip(),
                "gtin_upc_ean": gtin_upc_ean
            }
            response = self.client.table("product_comparison_groups").insert(data).execute()
            return response.data[0] if response.data else {}
        except Exception as e:
            logger.error(f"Error creating comparison group: {e}")
            return {}

    def link_product_to_group(self, group_id: str, listing_id: str) -> bool:
        """
        Link a marketplace product listing to a comparison group.
        """
        if not self.client:
            return True

        try:
            self.client.table("comparison_group_items").upsert({
                "group_id": group_id,
                "listing_id": listing_id
            }).execute()
            return True
        except Exception as e:
            logger.error(f"Error linking listing {listing_id} to group {group_id}: {e}")
            return False

    def get_comparison_view(self, group_id: str) -> Dict[str, Any]:
        """
        Fetch cross-marketplace price comparison matrix for a specific group.
        """
        if not self.client:
            return {}

        try:
            response = self.client.table("comparison_group_items") \
                .select("group_id, marketplace_products(*)") \
                .eq("group_id", group_id) \
                .execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error fetching comparison matrix: {e}")
            return []

    def upsert_canonical_product(self, canonical_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Upsert master smart home product into 'canonical_products' table.
        """
        if not self.client:
            logger.warning(f"[Mock DB] Skipping canonical product upsert for: {canonical_data.get('title')}")
            return {"status": "skipped", "id": "mock-canonical-id"}

        try:
            res = self.client.table("canonical_products").upsert(canonical_data).execute()
            logger.info(f"Upserted Canonical Product: '{canonical_data.get('title')}'")
            return {"status": "success", "data": res.data[0] if res.data else {}}
        except Exception as e:
            logger.error(f"Error upserting canonical product: {e}")
            return {"status": "error", "error": str(e)}

    def get_valid_comparisons(self, site: str = "au", limit: int = 50) -> List[Dict[str, Any]]:
        """
        Queries database views for:
        - 'au': nxtsmarthome.com.au (v_au_smart_home_comparisons)
        - 'intl': nxtsmart.homes (v_intl_smart_home_comparisons)
        - 'beauty': www.bestlooking.skin (v_beauty_skincare_comparisons)
        Returns ONLY products that have AT LEAST 3 active retailer offers.
        """
        if not self.client:
            logger.info(f"[Mock DB] Returning sample 3-offer comparison set for site: {site}")
            if site.lower() == "beauty":
                return [
                    {
                        "canonical_product_id": "mock-ordinary-niacinamide",
                        "canonical_title": "The Ordinary Niacinamide 10% + Zinc 1%",
                        "brand": "The Ordinary",
                        "category": "Serums & Treatments",
                        "active_offers_count": 3,
                        "lowest_price": 6.00,
                        "currency": "USD",
                        "offers": [
                            {"marketplace": "sephora", "price": 6.00, "retailer_name": "Sephora"},
                            {"marketplace": "ulta", "price": 6.00, "retailer_name": "Ulta Beauty"},
                            {"marketplace": "boots", "price": 6.50, "retailer_name": "Boots UK"}
                        ]
                    }
                ]

            return [
                {
                    "canonical_product_id": "mock-ring-doorbell-id",
                    "canonical_title": "Ring Video Doorbell 4",
                    "brand": "Ring",
                    "category": "Smart Security & Access",
                    "active_offers_count": 3,
                    "lowest_price": 249.00 if site == "au" else 159.99,
                    "currency": "AUD" if site == "au" else "USD",
                    "offers": [
                        {"marketplace": "amazon_au" if site == "au" else "amazon_us", "price": 249.00, "retailer_name": "Amazon"},
                        {"marketplace": "jbhifi" if site == "au" else "bestbuy", "price": 259.00, "retailer_name": "JB Hi-Fi" if site == "au" else "Best Buy"},
                        {"marketplace": "harveynorman" if site == "au" else "walmart", "price": 269.00, "retailer_name": "Harvey Norman" if site == "au" else "Walmart"}
                    ]
                }
            ]

        s_lower = site.lower()
        if s_lower in ["beauty", "skincare", "bestlooking"]:
            view_name = "v_beauty_skincare_comparisons"
        elif s_lower == "au":
            view_name = "v_au_smart_home_comparisons"
        else:
            view_name = "v_intl_smart_home_comparisons"

        try:
            res = self.client.table(view_name).select("*").limit(limit).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Error querying {view_name}: {e}")
            return []

    def log_scrape_run(
        self,
        target_url: str,
        marketplace: str,
        target_type: str,
        status: str,
        items_count: int = 0,
        execution_time_ms: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        Record execution details into 'scrape_logs' table.
        """
        if not self.client:
            return

        try:
            log_entry = {
                "target_url": target_url,
                "marketplace": marketplace,
                "target_type": target_type,
                "status": status,
                "items_count": items_count,
                "execution_time_ms": execution_time_ms,
                "error_message": error_message
            }
            self.client.table("scrape_logs").insert(log_entry).execute()
        except Exception as e:
            logger.warning(f"Failed to log scrape run to Supabase: {e}")

    # =========================================================================
    # COUPONS & PROMO CODES HELPER METHODS
    # =========================================================================

    def upsert_coupon(self, coupon_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Upsert a store-wide promo coupon / discount code into 'coupons' table.
        """
        if not self.client:
            logger.info(f"[Mock DB] Upserted Coupon: '{coupon_data.get('code')}' ({coupon_data.get('discount_description')}) for {coupon_data.get('marketplace')}")
            return {"status": "mock_success", "data": coupon_data}

        try:
            res = self.client.table("coupons").upsert(coupon_data).execute()
            logger.info(f"Upserted Supabase Coupon: [{coupon_data.get('marketplace').upper()}] '{coupon_data.get('code')}' -> {coupon_data.get('discount_description')}")
            return {"status": "success", "data": res.data}
        except Exception as e:
            logger.error(f"Error upserting coupon to Supabase: {e}")
            return {"status": "error", "error": str(e)}

    def get_active_coupons(self, marketplace: Optional[str] = None, region: str = "US") -> List[Dict[str, Any]]:
        """
        Fetches active, verified coupons from Supabase for a specific store or region.
        """
        if not self.client:
            return [
                {
                    "marketplace": marketplace or "amazon",
                    "region": region,
                    "code": "SAVE20",
                    "discount_description": "20% Off Sitewide Flash Sale",
                    "discount_type": "percentage",
                    "discount_value": 20.0,
                    "is_verified": True
                }
            ]

        try:
            query = self.client.table("coupons").select("*").eq("is_verified", True).eq("region", region.upper())
            if marketplace:
                query = query.eq("marketplace", marketplace.lower())
            res = query.order("created_at", desc=True).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Error fetching active coupons from Supabase: {e}")
            return []

    # =========================================================================
    # WATERFALL MATCHING HELPER METHODS
    # =========================================================================

    def find_canonical_by_gtin(self, gtin: str) -> Optional[Dict[str, Any]]:
        """Tier 1 Match: Search canonical_products by GTIN/UPC/EAN."""
        if not self.client or not gtin:
            return None
        try:
            res = self.client.table("canonical_products").select("*").eq("gtin_upc_ean", gtin.strip()).limit(1).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error querying GTIN match '{gtin}': {e}")
            return None

    def find_canonical_by_asin(self, asin: str) -> Optional[Dict[str, Any]]:
        """Tier 2 Match: Search canonical_products by Amazon ASIN."""
        if not self.client or not asin:
            return None
        try:
            res = self.client.table("canonical_products").select("*").eq("asin", asin.strip()).limit(1).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error querying ASIN match '{asin}': {e}")
            return None

    def find_canonical_by_brand_mpn(self, brand: str, mpn: str) -> Optional[Dict[str, Any]]:
        """Tier 3 Match: Search canonical_products by Brand + MPN."""
        if not self.client or not brand or not mpn:
            return None
        try:
            res = self.client.table("canonical_products").select("*") \
                .ilike("brand", brand.strip()) \
                .ilike("mpn", mpn.strip()) \
                .limit(1).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error querying Brand+MPN match '{brand} / {mpn}': {e}")
            return None

    def find_canonical_by_trigram(self, normalized_title: str, brand: Optional[str] = None) -> List[Dict[str, Any]]:
        """Tier 4 Match: Fetch candidate canonical products by brand or similarity for trigram matching."""
        if not self.client or not normalized_title:
            return []
        try:
            query = self.client.table("canonical_products").select("*")
            if brand:
                query = query.ilike("brand", brand.strip())
            res = query.limit(20).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Error querying trigram candidate titles: {e}")
            return []

    def insert_unmatched_queue(
        self,
        raw_offer: Dict[str, Any],
        suggested_canonical_id: Optional[str] = None,
        similarity_score: float = 0.0
    ) -> Dict[str, Any]:
        """Routes 65% - 84% gray-area matches to unmatched_queue for manual human review."""
        if not self.client:
            logger.info(f"[Mock DB] Queued gray-area match ({similarity_score*100:.1f}%) for: {raw_offer.get('title')}")
            return {"status": "mock_queued"}

        try:
            payload = {
                "raw_offer": raw_offer,
                "suggested_canonical_id": suggested_canonical_id,
                "similarity_score": round(similarity_score * 100, 2),
                "status": "pending"
            }
            res = self.client.table("unmatched_queue").insert(payload).execute()
            logger.info(f"Queued gray-area match ({similarity_score*100:.1f}%) for review: '{raw_offer.get('title')}'")
            return {"status": "success", "data": res.data}
        except Exception as e:
            logger.error(f"Error queuing offer to unmatched_queue: {e}")
            return {"status": "error", "error": str(e)}


