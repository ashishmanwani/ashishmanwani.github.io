#!/usr/bin/env python3
"""
CLI script to trigger an immediate scrape for a product by ID or URL.
Usage:
  python scripts/force_scrape.py --product-id <uuid>
  python scripts/force_scrape.py --url https://www.flipkart.com/...
"""

import argparse
import asyncio
import sys

sys.path.insert(0, "/app")


async def scrape_by_id(product_id: str):
    from scraper.registry import get_scraper
    from proxy.manager import proxy_manager
    from sqlalchemy import select
    from api.db.session import AsyncSessionLocal
    from api.models.product import Product
    import uuid

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Product).where(Product.id == uuid.UUID(product_id))
        )
        product = result.scalar_one_or_none()
        if not product:
            print(f"Product {product_id} not found")
            sys.exit(1)

    print(f"Scraping: {product.canonical_url} (site={product.site})")
    scraper = get_scraper(product.site)
    proxy_model = proxy_manager.get_proxy(product.site)
    proxy_dict = proxy_model.as_dict if proxy_model else None

    if proxy_dict:
        print(f"Using proxy: {proxy_model.host}:{proxy_model.port}")
    else:
        print("No proxy configured — using direct connection")

    result = await scraper.scrape(product.canonical_url, proxy_dict)

    print("\n── Scrape Result ──────────────────────────────")
    print(f"  Success:    {result.success}")
    print(f"  Price:      ₹{result.price}" if result.price else "  Price:      N/A")
    print(f"  Title:      {result.title or 'N/A'}")
    print(f"  Method:     {result.extraction_method}")
    print(f"  Confidence: {result.confidence:.2f}")
    print(f"  OOS:        {result.is_out_of_stock}")
    if result.error:
        print(f"  Error:      {result.error}")
    print("───────────────────────────────────────────────")


async def scrape_by_url(url: str):
    from api.services.product_service import canonicalize_url
    from scraper.registry import get_scraper
    from proxy.manager import proxy_manager

    try:
        canonical_url, site = canonicalize_url(url)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"Scraping: {canonical_url} (site={site})")
    scraper = get_scraper(site)
    proxy_model = proxy_manager.get_proxy(site)
    proxy_dict = proxy_model.as_dict if proxy_model else None

    result = await scraper.scrape(canonical_url, proxy_dict)

    print("\n── Scrape Result ──────────────────────────────")
    print(f"  Success:    {result.success}")
    print(f"  Price:      ₹{result.price}" if result.price else "  Price:      N/A")
    print(f"  Title:      {result.title or 'N/A'}")
    print(f"  Method:     {result.extraction_method}")
    print(f"  Confidence: {result.confidence:.2f}")
    print(f"  OOS:        {result.is_out_of_stock}")
    if result.error:
        print(f"  Error:      {result.error}")
    print("───────────────────────────────────────────────")


def main():
    parser = argparse.ArgumentParser(description="Force-scrape a product")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--product-id", help="Product UUID")
    group.add_argument("--url", help="Product URL")
    args = parser.parse_args()

    if args.product_id:
        asyncio.run(scrape_by_id(args.product_id))
    else:
        asyncio.run(scrape_by_url(args.url))


if __name__ == "__main__":
    main()
