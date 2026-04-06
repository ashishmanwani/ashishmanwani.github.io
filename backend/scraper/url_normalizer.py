# Re-export from api.services.product_service for convenience
from api.services.product_service import canonicalize_url, detect_site

__all__ = ["canonicalize_url", "detect_site"]
