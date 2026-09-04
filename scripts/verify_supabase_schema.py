import sys
import logging
import requests
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("verify_supabase_schema")

def check_schema():
    if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
        logger.error("SUPABASE_URL and SUPABASE_KEY must be set in .env")
        return False

    url = f"{Config.SUPABASE_URL.rstrip('/')}/rest/v1/canonical_products?select=count"
    headers = {
        "apikey": Config.SUPABASE_KEY,
        "Authorization": f"Bearer {Config.SUPABASE_KEY}"
    }

    logger.info(f"Checking Supabase table 'canonical_products' at {url}...")
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            logger.info("✅ SUCCESS: 'canonical_products' table exists in Supabase schema!")
            return True
        else:
            logger.warning(f"❌ Table missing or error returned (HTTP {resp.status_code}): {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Failed to connect to Supabase: {e}")
        return False

if __name__ == "__main__":
    success = check_schema()
    if not success:
        print("\nACTION REQUIRED:")
        print("Please copy the contents of 'schema.sql' and run it in your Supabase SQL Editor:")
        print("https://supabase.com/dashboard/project/vofmdniuvsqrawfojcmp/sql\n")
        sys.exit(1)
    else:
        print("\nSchema verification passed! Ready to run ZenRows ingestion.")
        sys.exit(0)
