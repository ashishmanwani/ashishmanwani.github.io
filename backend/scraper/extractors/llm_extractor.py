import logging
import re
from decimal import Decimal, InvalidOperation

from bs4 import BeautifulSoup

from api.config import settings
from scraper.extractors.base_extractor import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)

LLM_SYSTEM_PROMPT = """You are a price extraction assistant for Indian e-commerce websites.
Given an HTML fragment from a product page, extract the CURRENT selling price in INR.

Rules:
- Return ONLY the standard selling price a customer pays at checkout (no special cards needed)
- DO NOT return EMI/monthly prices, bank card offer prices, or crossed-out original prices
- If the product is out of stock, return out_of_stock=true and price=null
- If you cannot find a clear price, return price=null

Respond ONLY with valid JSON: {"price": <float or null>, "currency": "INR", "confidence": <0.0-1.0>, "out_of_stock": <bool>}"""

PRICE_AREA_RE = re.compile(r"[₹\d,\.]+\s*(?:rs\.?|inr)?", re.IGNORECASE)


def extract_price_fragment(html: str, max_chars: int = 3000) -> str:
    """
    Extract a focused HTML fragment around price-related elements.
    Keeps token count small for LLM cost efficiency.
    """
    soup = BeautifulSoup(html, "lxml")

    # Remove script, style, nav, footer to reduce noise
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    # Find elements containing ₹ or price-related text
    candidates = []
    for el in soup.find_all(string=PRICE_AREA_RE):
        parent = el.parent
        if parent:
            candidates.append(parent)

    if candidates:
        # Take up to 5 candidate elements and their parents
        fragments = []
        seen = set()
        for el in candidates[:5]:
            grandparent = el.parent or el
            el_id = id(grandparent)
            if el_id not in seen:
                seen.add(el_id)
                fragments.append(str(grandparent))

        combined = "\n".join(fragments)
        return combined[:max_chars]

    # Fallback: first max_chars of body text
    body = soup.find("body")
    return str(body)[:max_chars] if body else html[:max_chars]


class LlmExtractor(BaseExtractor):
    """
    LLM-based price extraction — Layer 4 fallback.
    Uses Ollama (local) or OpenAI/Anthropic (cloud) based on config.
    Only invoked when CSS and JSON-LD extraction fail or have low confidence.
    """

    def extract(self, html: str, site: str) -> ExtractionResult:
        fragment = extract_price_fragment(html)

        try:
            response = self._call_llm(fragment)
            return self._parse_response(response)
        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}")
            return ExtractionResult(price=None, confidence=0.0, method="llm_text")

    def _call_llm(self, html_fragment: str) -> dict:
        provider = settings.LLM_PROVIDER.lower()

        if provider == "ollama":
            return self._call_ollama(html_fragment)
        elif provider == "openai":
            return self._call_openai(html_fragment)
        elif provider == "anthropic":
            return self._call_anthropic(html_fragment)
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

    def _call_ollama(self, fragment: str) -> dict:
        import json
        import httpx

        payload = {
            "model": "llama3.2:3b",
            "messages": [
                {"role": "system", "content": LLM_SYSTEM_PROMPT},
                {"role": "user", "content": f"HTML fragment:\n{fragment}"},
            ],
            "stream": False,
            "format": "json",
        }
        response = httpx.post(
            f"{settings.OLLAMA_BASE_URL}/api/chat",
            json=payload,
            timeout=30.0,
        )
        response.raise_for_status()
        content = response.json()["message"]["content"]
        return json.loads(content)

    def _call_openai(self, fragment: str) -> dict:
        import json
        from openai import OpenAI

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": LLM_SYSTEM_PROMPT},
                {"role": "user", "content": f"HTML fragment:\n{fragment}"},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        return json.loads(response.choices[0].message.content)

    def _call_anthropic(self, fragment: str) -> dict:
        import json
        import anthropic

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            system=LLM_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": f"HTML fragment:\n{fragment}"},
            ],
        )
        return json.loads(message.content[0].text)

    def _parse_response(self, data: dict) -> ExtractionResult:
        out_of_stock = data.get("out_of_stock", False)
        confidence = float(data.get("confidence", 0.0))
        raw_price = data.get("price")

        if out_of_stock:
            return ExtractionResult(
                price=None,
                is_out_of_stock=True,
                confidence=confidence,
                method="llm_text",
            )

        if raw_price is None:
            return ExtractionResult(price=None, confidence=0.0, method="llm_text")

        try:
            price = Decimal(str(raw_price)).quantize(Decimal("0.01"))
            if price <= 0:
                return ExtractionResult(price=None, confidence=0.0, method="llm_text")
            return ExtractionResult(
                price=price,
                confidence=confidence,
                method="llm_text",
                metadata={"raw_response": data},
            )
        except InvalidOperation:
            return ExtractionResult(price=None, confidence=0.0, method="llm_text")


class LlmVisionExtractor:
    """
    Vision-based price extraction — Layer 5 (optional, expensive).
    Takes a screenshot, crops to upper-right area (typical price location),
    and sends to a vision LLM.
    Only enabled when ENABLE_VISION_FALLBACK=true.
    """

    def extract_from_screenshot(self, screenshot_bytes: bytes, site: str) -> ExtractionResult:
        if not settings.ENABLE_VISION_FALLBACK:
            return ExtractionResult(price=None, confidence=0.0, method="llm_vision")

        try:
            return self._call_vision_llm(screenshot_bytes)
        except Exception as e:
            logger.warning(f"Vision LLM extraction failed: {e}")
            return ExtractionResult(price=None, confidence=0.0, method="llm_vision")

    def _call_vision_llm(self, screenshot_bytes: bytes) -> ExtractionResult:
        import base64
        import json
        from openai import OpenAI

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        b64 = base64.b64encode(screenshot_bytes).decode()

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"{LLM_SYSTEM_PROMPT}\n\nAnalyze this product page screenshot and extract the selling price.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64}"},
                        },
                    ],
                }
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        data = json.loads(response.choices[0].message.content)
        raw_price = data.get("price")
        confidence = float(data.get("confidence", 0.0))

        if raw_price is None:
            return ExtractionResult(price=None, confidence=0.0, method="llm_vision")

        try:
            price = Decimal(str(raw_price)).quantize(Decimal("0.01"))
            return ExtractionResult(price=price, confidence=confidence, method="llm_vision")
        except InvalidOperation:
            return ExtractionResult(price=None, confidence=0.0, method="llm_vision")
