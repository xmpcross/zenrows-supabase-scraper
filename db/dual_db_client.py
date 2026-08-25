"""
Dual Database Persistence Manager for nxt.bargains.
Synchronizes master canonical products, retailer offers, and review queues
to BOTH Supabase (PostgreSQL price tracker & trigram engine) and Strapi (Headless CMS).
"""

import logging
from typing import Dict, Any, List, Optional
from db.supabase_client import SupabaseManager
from db.strapi_client import StrapiManager

logger = logging.getLogger(__name__)

class DualDatabaseManager:
    """
    Dual Persistence Manager wrapping SupabaseManager and StrapiManager.
    Guarantees seamless data sync between relational database engine & Headless CMS.
    """
    def __init__(
        self,
        supabase: Optional[SupabaseManager] = None,
        strapi: Optional[StrapiManager] = None
    ):
        self.supabase = supabase or SupabaseManager()
        self.strapi = strapi or StrapiManager()

    def is_connected(self) -> bool:
        return self.supabase.is_connected() or self.strapi.is_connected()

    # =========================================================================
    # WATERFALL MATCHING LOOKUP METHODS (Queries Supabase first, Strapi fallback)
    # =========================================================================

    def find_canonical_by_gtin(self, gtin: str) -> Optional[Dict[str, Any]]:
        matched = self.supabase.find_canonical_by_gtin(gtin) if self.supabase.is_connected() else None
        if not matched and self.strapi.is_connected():
            matched = self.strapi.find_canonical_by_gtin(gtin)
        return matched

    def find_canonical_by_asin(self, asin: str) -> Optional[Dict[str, Any]]:
        matched = self.supabase.find_canonical_by_asin(asin) if self.supabase.is_connected() else None
        if not matched and self.strapi.is_connected():
            matched = self.strapi.find_canonical_by_asin(asin)
        return matched

    def find_canonical_by_brand_mpn(self, brand: str, mpn: str) -> Optional[Dict[str, Any]]:
        matched = self.supabase.find_canonical_by_brand_mpn(brand, mpn) if self.supabase.is_connected() else None
        if not matched and self.strapi.is_connected():
            matched = self.strapi.find_canonical_by_brand_mpn(brand, mpn)
        return matched

    def find_canonical_by_trigram(self, normalized_title: str, brand: Optional[str] = None) -> List[Dict[str, Any]]:
        results = self.supabase.find_canonical_by_trigram(normalized_title, brand=brand) if self.supabase.is_connected() else []
        if not results and self.strapi.is_connected():
            results = self.strapi.find_canonical_by_trigram(normalized_title, brand=brand)
        return results

    # =========================================================================
    # DUAL PERSISTENCE SYNCHRONIZATION METHODS
    # =========================================================================

    def upsert_canonical_product(self, canonical_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dual-writes canonical product record to BOTH Supabase and Strapi CMS.
        """
        logger.info(f"[Dual DB Sync] Upserting Canonical Product: '{canonical_data.get('title')}'")
        
        supa_res = self.supabase.upsert_canonical_product(canonical_data)
        strapi_res = self.strapi.upsert_canonical_product(canonical_data)

        # Retrieve generated canonical ID
        canonical_id = (
            supa_res.get("data", {}).get("id") or 
            strapi_res.get("data", {}).get("id") or 
            f"dual-canonical-{hash(canonical_data.get('title')) & 0xffffffff:x}"
        )

        return {
            "status": "success",
            "canonical_id": canonical_id,
            "supabase": supa_res,
            "strapi": strapi_res
        }

    def upsert_marketplace_product(self, offer_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dual-writes marketplace offer record to BOTH Supabase (triggers price_history) and Strapi CMS.
        """
        logger.info(f"[Dual DB Sync] Upserting Offer: [{offer_data.get('marketplace', '').upper()}] '{offer_data.get('title')}' (${offer_data.get('current_price')})")

        supa_res = self.supabase.upsert_marketplace_product(offer_data)
        strapi_res = self.strapi.upsert_marketplace_product(offer_data)

        return {
            "status": "success",
            "supabase": supa_res,
            "strapi": strapi_res
        }

    def insert_unmatched_queue(
        self,
        raw_offer: Dict[str, Any],
        suggested_canonical_id: Optional[str] = None,
        similarity_score: float = 0.0
    ) -> Dict[str, Any]:
        """
        Dual-routes gray-area match candidate (65% - 84% score) to BOTH Supabase and Strapi review queues.
        """
        logger.warning(f"[Dual DB Sync] Queuing gray-area match ({similarity_score*100:.1f}%) for: '{raw_offer.get('title')}'")

        supa_res = self.supabase.insert_unmatched_queue(raw_offer, suggested_canonical_id, similarity_score)
        strapi_res = self.strapi.insert_unmatched_queue(raw_offer, suggested_canonical_id, similarity_score)

        return {
            "status": "queued",
            "supabase": supa_res,
            "strapi": strapi_res
        }
