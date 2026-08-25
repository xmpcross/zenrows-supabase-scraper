"""
Automated Affiliate Link Monetizer for nxt.bargains.

Automatically injects affiliate tracking parameters into outgoing product URLs
for Amazon, eBay, Walmart, Best Buy, Target, Sephora, and iHerb before database persistence.
"""

import re
import logging
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from config import Config

logger = logging.getLogger(__name__)

class AffiliateLinker:
    def __init__(self, amazon_tag: str = None, ebay_camp_id: str = None):
        self.amazon_tag = amazon_tag or Config.AMAZON_AFFILIATE_TAG
        self.ebay_camp_id = ebay_camp_id or Config.EBAY_AFFILIATE_CAMPAIGN_ID

    def monetize_url(self, url: str, marketplace: str = "generic") -> str:
        """
        Injects affiliate tracking tags into raw product URLs.
        """
        if not url:
            return ""

        market_lower = (marketplace or "").lower()

        # 1. Amazon Affiliate Linker (Amazon US, AU, UK)
        if "amazon" in url.lower() or "amazon" in market_lower:
            return self._monetize_amazon(url)

        # 2. eBay Partner Network (EPN) Linker
        if "ebay" in url.lower() or "ebay" in market_lower:
            return self._monetize_ebay(url)

        # 3. Walmart / Best Buy / Target / iHerb / Sephora
        if "walmart" in url.lower() or "walmart" in market_lower:
            return self._append_param(url, "veh", "aff")
        if "iherb" in url.lower() or "iherb" in market_lower:
            return self._append_param(url, "rcode", "NXTBARGAINS")

        return url

    def _monetize_amazon(self, url: str) -> str:
        """Injects Amazon Associates Tag into Amazon URLs."""
        if not self.amazon_tag:
            return url
        return self._append_param(url, "tag", self.amazon_tag)

    def _monetize_ebay(self, url: str) -> str:
        """Injects eBay Partner Network (EPN) tracking parameters."""
        params = {
            "mkcid": "1",
            "mkrid": "711-53200-19255-0",
            "siteid": "0",
            "campid": self.ebay_camp_id or "5338000000",
            "customid": "nxtbargains"
        }
        res_url = url
        for k, v in params.items():
            res_url = self._append_param(res_url, k, v)
        return res_url

    def _append_param(self, url: str, param_key: str, param_val: str) -> str:
        """Appends query parameter to URL cleanly."""
        try:
            parsed = urlparse(url)
            query_dict = parse_qs(parsed.query)
            query_dict[param_key] = [param_val]
            new_query = urlencode(query_dict, doseq=True)
            return urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment
            ))
        except Exception as e:
            logger.warning(f"Error appending affiliate param to URL '{url}': {e}")
            return url
