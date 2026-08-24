import logging
import requests
from typing import Dict, Any, Optional
from zenrows import ZenRowsClient
from config import Config

logger = logging.getLogger(__name__)

MARKETPLACE_PRESETS = {
    "amazon": {
        "js_render": "true",
        "antibot": "true",
        "premium_proxy": "true",
        "proxy_country": "us"
    },
    "walmart": {
        "js_render": "true",
        "antibot": "true",
        "premium_proxy": "true",
        "proxy_country": "us"
    },
    "bestbuy": {
        "js_render": "true",
        "antibot": "true",
        "premium_proxy": "true",
        "proxy_country": "us"
    },
    "target": {
        "js_render": "true",
        "antibot": "true",
        "premium_proxy": "true",
        "proxy_country": "us"
    },
    "newegg": {
        "js_render": "true",
        "antibot": "true",
        "premium_proxy": "true",
        "proxy_country": "us"
    },
    "aliexpress": {
        "js_render": "true",
        "antibot": "true",
        "premium_proxy": "true"
    },
    "ebay": {
        "js_render": "false",
        "antibot": "true",
        "premium_proxy": "false"
    }
}

class ZenRowsFetcher:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or Config.ZENROWS_API_KEY
        if self.api_key and self.api_key != "your_zenrows_api_key_here":
            self.client = ZenRowsClient(self.api_key)
        else:
            self.client = None
            logger.warning("ZenRows API Key missing or default. Direct HTTP requests will be used as fallback.")

    def fetch_html(
        self,
        url: str,
        js_render: bool = Config.DEFAULT_JS_RENDER,
        premium_proxy: bool = Config.DEFAULT_PREMIUM_PROXY,
        antibot: bool = Config.DEFAULT_ANTIBOT,
        custom_params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Fetches raw HTML content of a target URL using ZenRows API.
        """
        if not self.client:
            logger.info(f"ZenRows API key not set. Attempting direct GET request to {url}")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9"
            }
            resp = requests.get(url, headers=headers, timeout=20)
            resp.raise_for_status()
            return resp.text

        params = {}
        if js_render:
            params["js_render"] = "true"
        if premium_proxy:
            params["premium_proxy"] = "true"
        if antibot:
            params["antibot"] = "true"
            
        if custom_params:
            params.update(custom_params)

        logger.info(f"Fetching via ZenRows: {url} | Params: {params}")
        response = self.client.get(url, params=params)
        
        if response.status_code != 200:
            logger.error(f"ZenRows API returned status code {response.status_code}: {response.text}")
            response.raise_for_status()

        return response.text

    def fetch_marketplace_html(
        self,
        url: str,
        marketplace: str,
        custom_params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Fetches HTML configured with optimal ZenRows presets for specific marketplaces.
        """
        marketplace_key = marketplace.lower()
        preset = MARKETPLACE_PRESETS.get(marketplace_key, {
            "js_render": "true" if Config.DEFAULT_JS_RENDER else "false",
            "antibot": "true" if Config.DEFAULT_ANTIBOT else "false",
            "premium_proxy": "true" if Config.DEFAULT_PREMIUM_PROXY else "false"
        })

        merged_params = dict(preset)
        if custom_params:
            merged_params.update(custom_params)

        if not self.client:
            logger.info(f"ZenRows API key not set. Direct fallback request to {marketplace} URL: {url}")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9"
            }
            resp = requests.get(url, headers=headers, timeout=20)
            resp.raise_for_status()
            return resp.text

        logger.info(f"Fetching {marketplace.upper()} page via ZenRows. Params: {merged_params}")
        response = self.client.get(url, params=merged_params)
        if response.status_code != 200:
            logger.error(f"ZenRows API error for {marketplace}: status {response.status_code}")
            response.raise_for_status()

        return response.text
