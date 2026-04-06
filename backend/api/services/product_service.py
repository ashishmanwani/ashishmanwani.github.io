import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

TRACKING_PARAMS = {
    "amazon": {"ref", "ref_", "pf_rd_p", "pf_rd_r", "pf_rd_s", "pf_rd_t",
               "pf_rd_i", "pf_rd_m", "sprefix", "crid", "keywords", "qid",
               "sr", "smid", "linkCode", "tag", "camp", "creative", "creativeASIN",
               "linkId", "ascsubtag"},
    "flipkart": {"marketplace", "srno", "otracker", "otracker1", "lid", "ssid",
                 "affid", "affExtParam1", "affExtParam2"},
    "myntra": {"src", "skuId"},
}

SITE_PATTERNS = {
    "amazon": re.compile(r"amazon\.in"),
    "flipkart": re.compile(r"flipkart\.com"),
    "myntra": re.compile(r"myntra\.com"),
}


def detect_site(url: str) -> str | None:
    for site, pattern in SITE_PATTERNS.items():
        if pattern.search(url):
            return site
    return None


def normalize_amazon_url(parsed) -> str:
    """Extract ASIN and build clean Amazon URL."""
    asin_match = re.search(r"/dp/([A-Z0-9]{10})", parsed.path)
    if not asin_match:
        asin_match = re.search(r"/gp/product/([A-Z0-9]{10})", parsed.path)
    if asin_match:
        asin = asin_match.group(1)
        # ?th=1&psc=1 — skip variant page, force main product
        return f"https://www.amazon.in/dp/{asin}?th=1&psc=1"
    return _strip_tracking_params(parsed, "amazon")


def normalize_flipkart_url(parsed) -> str:
    """Keep pid param (product ID) and strip the rest."""
    qs = parse_qs(parsed.query, keep_blank_values=False)
    keep = {k: v for k, v in qs.items() if k == "pid"}
    clean_query = urlencode(keep, doseq=True)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", clean_query, ""))


def normalize_myntra_url(parsed) -> str:
    """Myntra URLs encode product ID in path — strip query entirely."""
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def _strip_tracking_params(parsed, site: str) -> str:
    params_to_strip = TRACKING_PARAMS.get(site, set())
    qs = parse_qs(parsed.query, keep_blank_values=False)
    clean = {k: v for k, v in qs.items() if k not in params_to_strip}
    clean_query = urlencode(clean, doseq=True)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", clean_query, ""))


def canonicalize_url(url: str) -> tuple[str, str]:
    """
    Returns (canonical_url, site).
    Raises ValueError if the URL is unsupported.
    """
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)
    site = detect_site(url)
    if site is None:
        raise ValueError(f"Unsupported site: {url}")

    if site == "amazon":
        canonical = normalize_amazon_url(parsed)
    elif site == "flipkart":
        canonical = normalize_flipkart_url(parsed)
    elif site == "myntra":
        canonical = normalize_myntra_url(parsed)
    else:
        canonical = url

    return canonical, site
