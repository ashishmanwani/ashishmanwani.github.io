"""
Per-site CSS selector configurations.
Selectors are ordered by reliability (most reliable first).
Each entry: (selector, confidence_score)
"""

AMAZON_PRICE_SELECTORS = [
    # Most reliable — hidden span inside .a-price has clean ₹ text
    (".a-price .a-offscreen", 0.95),
    # Deal/sale price block
    ("#priceblock_dealprice", 0.90),
    # Regular price block
    ("#priceblock_ourprice", 0.90),
    # Apex offer display (newer PDP layout)
    (".apexPriceToPay .a-offscreen", 0.88),
    ("#apex_offerDisplay_desktop .a-price .a-offscreen", 0.85),
    # Newer format — span with data attribute
    ("span[data-a-color='price'] .a-offscreen", 0.82),
    # Core price widget
    ("#corePrice_feature_div .a-price .a-offscreen", 0.82),
    # Generic fallback
    (".a-price-whole", 0.60),
]

AMAZON_OUT_OF_STOCK_SELECTORS = [
    "#availability .a-color-price",
    "#outOfStock",
    ".availabilityInsideBuyBox_feature_div",
]

AMAZON_TITLE_SELECTORS = [
    "#productTitle",
    "#title",
]

AMAZON_IMAGE_SELECTORS = [
    "#imgTagWrapperId img",
    "#landingImage",
    "#main-image",
]

# ─────────────────────────────────────────────────────────────────────────────

FLIPKART_PRICE_SELECTORS = [
    # Current primary price class (changes ~2x/year)
    ("._30jeq3._16Jk6d", 0.90),
    ("._30jeq3", 0.88),
    # Alternative class names observed
    ("._1_WHN1", 0.82),
    (".CEmiEU > .Nx9bqj", 0.80),
    (".Nx9bqj.CxhGGd", 0.80),
    # Generic price text
    ("[class*='price']", 0.50),
]

FLIPKART_OUT_OF_STOCK_SELECTORS = [
    "._16FRp0",  # "Notify Me" button implies OOS
    "._1AtVbE ._2bFr-S",
]

FLIPKART_TITLE_SELECTORS = [
    ".B_NuCI",
    "h1.yhB1nd",
    "span.B_NuCI",
]

# ─────────────────────────────────────────────────────────────────────────────

MYNTRA_PRICE_SELECTORS = [
    (".pdp-price strong", 0.92),
    (".pdp-price__discounted", 0.90),
    (".pdpDesktop-priceContainer .pdp-price strong", 0.88),
    # Older layout
    (".pdp-discounted-price", 0.82),
    (".pdp-price", 0.75),
]

MYNTRA_OUT_OF_STOCK_SELECTORS = [
    ".size-buttons-notify-me",
    ".pdp-out-of-stock",
]

MYNTRA_TITLE_SELECTORS = [
    ".pdp-title h1",
    "h1.pdp-name",
    ".pdp-product-description-content h1",
]
