from decimal import Decimal

from api.models.alert import Alert
from api.models.price_record import PriceRecord


def should_notify(alert: Alert, price_record: PriceRecord) -> bool:
    """
    Determine if a notification should be sent for this alert + new price.
    Returns True if the user should be notified.
    """
    if not alert.is_active:
        return False
    if price_record.is_out_of_stock or price_record.price is None:
        return False

    current_price = price_record.price

    # Primary condition: price at or below target
    if current_price <= alert.target_price:
        return True

    # Secondary: notify on any drop from last known price (if enabled)
    if alert.notify_on_any_drop and alert.product.current_price is not None:
        if current_price < alert.product.current_price:
            return True

    return False


def compute_scrape_tier(product) -> str:
    """
    Compute the scrape tier based on how close the current price is to the lowest target.
    Falls back to 'low' if no active alerts exist.
    """
    active_alerts = [a for a in product.alerts if a.is_active]
    if not active_alerts:
        return "low"

    current = product.current_price
    if current is None:
        return "normal"

    # Find closest target
    min_target = min(a.target_price for a in active_alerts)
    ratio = float(current) / float(min_target)

    if ratio <= 1.10:  # within 10% of target (or at/below target)
        return "critical"
    elif ratio <= 1.25:
        return "high"
    else:
        return "normal"


TIER_INTERVALS_SECONDS = {
    "critical": 30 * 60,    # 30 min
    "high": 60 * 60,        # 1 hour
    "normal": 4 * 60 * 60,  # 4 hours
    "low": 24 * 60 * 60,    # 24 hours
}
