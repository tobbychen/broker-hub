"""Amazon PA-API monitor for merchandise prices.

Requires Amazon Affiliate/PA-API credentials.
"""
import hashlib
import hmac
import json
import logging
import os
import time
import requests
from datetime import datetime
from urllib.parse import urlparse
from ..config import get_market_data_config
from .base import BaseMonitor, MerchandiseAlert

logger = logging.getLogger(__name__)


class AmazonMonitor(BaseMonitor):
    """Monitor branded merchandise prices via Amazon PA-API."""

    PA_API_URL = "https://webservices.amazon.com/paapi5/searchitems"

    @property
    def name(self) -> str:
        return "amazon"

    def __init__(self):
        config = get_market_data_config().get("amazon", {})
        config["enabled"] = config.get("enabled", True)
        super().__init__(config)
        self.threshold = self.config.get("price_change_threshold", 0.05)
        self._proxies = self._detect_proxy()

    def _detect_proxy(self) -> dict | None:
        for var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
            val = os.environ.get(var)
            if val:
                return {"http": val, "https": val}
        return None

    def is_market_open(self) -> bool:
        return True

    def _get_aws_sig(self, method: str, url, payload: str, access_key: str, secret_key: str) -> dict:
        """Generate AWS Signature Version 4 headers for PA-API."""
        now = datetime.utcnow()
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Host": "webservices.amazon.com",
            "X-Amz-Date": amz_date,
        }

        signed_headers = "content-type;host;x-amz-date"
        payload_hash = hashlib.sha256(payload.encode()).hexdigest()

        canonical_request = f"{method}\n{url.path}\n\n"
        for h in sorted(headers.keys()):
            canonical_request += f"{h.lower()}:{headers[h]}\n"
        canonical_request += f"\n{signed_headers}\n{payload_hash}"

        algorithm = "AWS4-HMAC-SHA256"
        credential_scope = f"{date_stamp}/us-east-1/execute-api/aws4_request"
        string_to_sign = f"{algorithm}\n{amz_date}\n{credential_scope}\n"
        string_to_sign += hashlib.sha256(canonical_request.encode()).hexdigest()

        k_date = hmac.new(f"AWS4{secret_key}".encode(), date_stamp.encode(), hashlib.sha256).digest()
        k_region = hmac.new(k_date, b"us-east-1", hashlib.sha256).digest()
        k_service = hmac.new(k_region, b"execute-api", hashlib.sha256).digest()
        k_signing = hmac.new(k_service, b"aws4_request", hashlib.sha256).digest()
        signature = hmac.new(k_signing, string_to_sign.encode(), hashlib.sha256).hexdigest()

        authorization = f"{algorithm} Credential={access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
        headers["Authorization"] = authorization

        return headers

    def _parse_notes(self, notes: str) -> dict:
        """Parse pipe-separated merchandise metadata.

        Format: Brand|Model|Variant|PurchasePrice|PurchaseCurrency
        """
        parts = notes.split("|")
        return {
            "brand": parts[0] if len(parts) > 0 else "",
            "model": parts[1] if len(parts) > 1 else "",
            "variant": parts[2] if len(parts) > 2 else "",
            "purchase_price": float(parts[3]) if len(parts) > 3 and parts[3] else None,
            "purchase_currency": parts[4] if len(parts) > 4 else "CNY",
        }

    async def check(self) -> list[MerchandiseAlert]:
        if not self.config.get("enabled", True):
            return []

        access_key = self.config.get("access_key")
        secret_key = self.config.get("secret_key")
        partner_tag = self.config.get("partner_tag")

        if not all([access_key, secret_key, partner_tag]):
            logger.warning("[amazon] Missing credentials")
            return []

        alerts = []
        from .. import database as db
        try:
            watched = await db.get_watchlist_items("merchandise")
        except Exception as e:
            logger.error(f"[amazon] Failed to read watchlist: {e}")
            return alerts

        for item in watched:
            try:
                alert = await self._check_item(access_key, secret_key, partner_tag, item)
                if alert:
                    alerts.append(alert)
            except Exception as e:
                logger.error(f"[amazon] Error checking {item.get('symbol')}: {e}")

        self.last_check = datetime.now()
        return alerts

    async def _check_item(self, access_key: str, secret_key: str, partner_tag: str, item: dict) -> MerchandiseAlert | None:
        meta = self._parse_notes(item.get("notes", ""))
        search_term = f"{meta.get('brand', '')} {meta.get('model', '')}".strip()
        if not search_term:
            return None

        current_price = await self._fetch_price(access_key, secret_key, partner_tag, search_term)
        if current_price is None:
            return None

        purchase_price = meta.get("purchase_price")
        symbol = item.get("symbol", search_term)

        if purchase_price:
            change_pct = (current_price - purchase_price) / purchase_price
            if change_pct < -self.threshold:
                return MerchandiseAlert(
                    source="amazon",
                    alert_type="owned_price_drop",
                    symbol=symbol,
                    exchange="Amazon",
                    brand=meta.get("brand", ""),
                    model=meta.get("model", ""),
                    variant=meta.get("variant", ""),
                    platforms={"Amazon": current_price},
                    purchase_price=purchase_price,
                    purchase_currency=meta.get("purchase_currency", "CNY"),
                    current_price=current_price,
                    current_platform="Amazon",
                    change_pct=change_pct,
                    details={"search_term": search_term},
                    priority="high" if change_pct < -0.10 else "normal",
                )

        return None

    async def _fetch_price(self, access_key: str, secret_key: str, partner_tag: str, search_term: str) -> float | None:
        payload = {
            "Keywords": search_term,
            "Resources": ["ITEMINFO", "OFFERS"],
            "PartnerTag": partner_tag,
            "PartnerType": "Associates",
            "Marketplace": "www.amazon.com",
        }
        payload_str = json.dumps(payload)
        url = urlparse(self.PA_API_URL)

        headers = self._get_aws_sig("POST", url, payload_str, access_key, secret_key)

        try:
            resp = requests.post(
                self.PA_API_URL,
                data=payload_str,
                headers=headers,
                proxies=self._proxies,
                timeout=15,
            )
            if resp.status_code != 200:
                logger.warning(f"[amazon] PA-API {resp.status_code}: {resp.text[:200]}")
                return None

            data = resp.json()
            items = data.get("ItemsResult", {}).get("Items", [])
            if not items:
                return None

            prices = []
            for item in items:
                offers = item.get("Offers", {}).get("Listings", [])
                for offer in offers:
                    price = offer.get("Price", {}).get("DisplayAmount")
                    if price:
                        try:
                            prices.append(float(price.replace("$", "").replace(",", "")))
                        except ValueError:
                            pass

            if not prices:
                return None

            return sorted(prices)[len(prices) // 2]
        except Exception as e:
            logger.error(f"[amazon] Request error: {e}")
            return None