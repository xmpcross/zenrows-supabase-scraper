import json
import logging
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def parse_blog_page(html_content: str, url: str) -> Dict[str, Any]:
    """
    Parses HTML content of a blog or news article page into a structured schema.
    Uses JSON-LD, OpenGraph meta tags, and BeautifulSoup heuristics.
    """
    soup = BeautifulSoup(html_content, "lxml")

    title = None
    author = None
    published_at = None
    content = None
    excerpt = None
    category = None
    tags = []
    metadata = {}

    # 1. Attempt JSON-LD Schema.org parsing
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "{}")
            if isinstance(data, list):
                data = data[0] if data else {}
            
            graph = data.get("@graph", [])
            items_to_check = [data] + (graph if isinstance(graph, list) else [])
            
            for item in items_to_check:
                item_type = str(item.get("@type", "")).lower()
                if any(t in item_type for t in ["article", "blogposting", "newsarticle"]):
                    title = item.get("headline") or item.get("name")
                    author_obj = item.get("author")
                    if isinstance(author_obj, dict):
                        author = author_obj.get("name")
                    elif isinstance(author_obj, list) and author_obj:
                        author = author_obj[0].get("name") if isinstance(author_obj[0], dict) else str(author_obj[0])
                    elif isinstance(author_obj, str):
                        author = author_obj
                    
                    published_at = item.get("datePublished") or item.get("dateCreated")
                    excerpt = item.get("description")
                    category = item.get("articleSection")
                    metadata["json_ld"] = item
                    break
        except Exception:
            continue

    # 2. OpenGraph Meta Tags Fallback
    if not title:
        og_title = soup.find("meta", property="og:title")
        if og_title:
            title = og_title.get("content")

    if not excerpt:
        og_desc = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
        if og_desc:
            excerpt = og_desc.get("content")

    if not category:
        og_cat = soup.find("meta", property="article:section")
        if og_cat:
            category = og_cat.get("content")

    # 3. DOM / HTML Element Fallbacks
    if not title:
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)
        elif soup.title:
            title = soup.title.get_text(strip=True)

    if not content:
        # Article tag or main content area
        article_elem = soup.find("article") or soup.find("main") or soup.find("div", class_=lambda c: c and "post" in c.lower())
        if article_elem:
            paragraphs = [p.get_text(strip=True) for p in article_elem.find_all("p") if p.get_text(strip=True)]
            content = "\n\n".join(paragraphs)
        else:
            paragraphs = [p.get_text(strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 40]
            content = "\n\n".join(paragraphs)

    # Clean fallback title
    title = title or "Untitled Article"

    return {
        "url": url,
        "title": title,
        "content": content,
        "excerpt": excerpt,
        "author": author,
        "category": category,
        "tags": tags,
        "published_at": published_at,
        "metadata": metadata
    }
