"""Cross-platform arbitrage detection for merchandise.

Compares prices across platforms to find buying/selling opportunities.
"""
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ArbitrageDetector:
    """Detect cross-platform price arbitrage opportunities."""

    def __init__(self, threshold: float = 0.05):
        self.threshold = threshold

    def find_opportunity(
        self,
        product_name: str,
        platform_prices: dict[str, float],
        purchase_price: float = None,
    ) -> Optional[dict]:
        """
        Find arbitrage opportunity across platforms.

        Args:
            product_name: Name of the product
            platform_prices: Dict of platform -> price (in same currency)
            purchase_price: Original purchase price for reference
            threshold: Minimum % difference to trigger alert

        Returns:
            Dict with opportunity details or None if no opportunity
        """
        if len(platform_prices) < 2:
            return None

        prices = [(p, price) for p, price in platform_prices.items() if price]
        if len(prices) < 2:
            return None

        prices.sort(key=lambda x: x[1])
        best_platform, lowest_price = prices[0]
        worst_platform, highest_price = prices[-1]

        if highest_price <= 0:
            return None

        margin_pct = (highest_price - lowest_price) / highest_price

        if margin_pct >= self.threshold:
            return {
                "product_name": product_name,
                "source_platform": best_platform,
                "best_platform": best_platform,
                "worst_platform": worst_platform,
                "lowest_price": lowest_price,
                "highest_price": highest_price,
                "margin_pct": margin_pct,
                "profit_potential": highest_price - lowest_price,
                "recommendation": f"Buy on {best_platform}, consider selling on {worst_platform}",
            }

        # Also check against purchase price if provided
        if purchase_price and purchase_price > 0:
            for platform, price in platform_prices.items():
                if price < purchase_price:
                    savings_pct = (purchase_price - price) / purchase_price
                    if savings_pct >= self.threshold:
                        return {
                            "product_name": product_name,
                            "source_platform": platform,
                            "best_platform": platform,
                            "lowest_price": price,
                            "purchase_price": purchase_price,
                            "margin_pct": savings_pct,
                            "savings": purchase_price - price,
                            "recommendation": f"Current price on {platform} is {savings_pct*100:.1f}% below your purchase price",
                        }

        return None

    async def check_all_products(self, watched_items: list[dict]) -> list[dict]:
        """Check all watched merchandise for arbitrage opportunities."""
        opportunities = []

        for item in watched_items:
            platform_prices = {}
            symbol = item.get("symbol")

            from .. import database as db
            for platform in ["eBay", "Amazon", "JD"]:
                try:
                    cache = await db.get_market_cache(symbol, platform, "merchandise_price")
                    if cache:
                        raw = cache.get("raw_data", "{}")
                        if isinstance(raw, str):
                            raw = json.loads(raw)
                        price = raw.get("price") if isinstance(raw, dict) else None
                        if price:
                            platform_prices[platform] = price
                except Exception:
                    pass

            if len(platform_prices) >= 2:
                meta = item.get("notes", "").split("|")
                purchase_price = float(meta[3]) if len(meta) > 3 and meta[3] else None
                product_name = f"{meta[0]} {meta[1]}".strip() if len(meta) >= 2 else symbol

                opp = self.find_opportunity(product_name, platform_prices, purchase_price)
                if opp:
                    opp["symbol"] = symbol
                    opportunities.append(opp)

        return opportunities