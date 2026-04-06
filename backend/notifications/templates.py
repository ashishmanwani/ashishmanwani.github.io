"""
Telegram message templates for price drop alerts.
Uses Telegram MarkdownV2 format.
"""

import re
from datetime import datetime, timezone


def _escape_md(text: str) -> str:
    """Escape special MarkdownV2 characters."""
    special_chars = r"_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(special_chars)}])", r"\\\1", str(text))


def _format_price(price) -> str:
    """Format price with Indian numbering (₹1,29,990)."""
    if price is None:
        return "N/A"
    p = float(price)
    # Simple Indian number formatting
    s = f"{p:,.0f}"
    return f"₹{s}"


def build_price_drop_message(alert, price_record) -> str:
    """
    Build a MarkdownV2 formatted Telegram message for a price drop alert.
    """
    product = alert.product
    current_price = price_record.price
    target_price = alert.target_price

    site_display = {
        "amazon": "Amazon India",
        "flipkart": "Flipkart",
        "myntra": "Myntra",
    }.get(product.site, product.site.title())

    title = product.title or "Product"
    url = product.canonical_url

    detected_at = price_record.scraped_at or datetime.now(tz=timezone.utc)
    # Convert to IST
    ist_offset = 5.5 * 3600
    ist_time = detected_at.replace(tzinfo=timezone.utc)
    formatted_time = ist_time.strftime("%d %b %Y, %I:%M %p IST")

    # Calculate drop amount and percentage
    drop_amount = ""
    drop_pct = ""
    if current_price and target_price:
        if current_price < target_price:
            diff = float(target_price) - float(current_price)
            pct = (diff / float(target_price)) * 100
            drop_amount = f"₹{diff:,.0f}"
            drop_pct = f"{pct:.1f}%"

    # Escape all dynamic content for MarkdownV2
    title_escaped = _escape_md(title[:60] + ("..." if len(title) > 60 else ""))
    site_escaped = _escape_md(site_display)
    price_escaped = _escape_md(_format_price(current_price))
    target_escaped = _escape_md(_format_price(target_price))
    time_escaped = _escape_md(formatted_time)

    lines = [
        "🚨 *Price Drop Alert\\!*",
        "",
        f"📦 [{title_escaped}]({url})",
        f"🛒 {site_escaped}",
        "",
        f"💰 Current Price: *{price_escaped}*",
        f"🎯 Your Target: {target_escaped}",
    ]

    if drop_amount:
        drop_escaped = _escape_md(f"{drop_amount} ({drop_pct})")
        lines.append(f"📉 Below target by: {drop_escaped}")

    lines += [
        f"⏰ Detected: {time_escaped}",
        "",
        f"[🛍️ Buy Now]({url})",
    ]

    return "\n".join(lines)


def build_welcome_message(bot_name: str = "PriceTrackerBot") -> str:
    return (
        "✅ *Your Telegram account is now linked to Price Tracker\\!*\n\n"
        "You'll receive alerts here whenever a tracked product price drops\\.\n\n"
        "Use the web app to track products and set target prices\\."
    )
