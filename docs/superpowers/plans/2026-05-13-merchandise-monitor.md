# Merchandise Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement multi-platform merchandise price monitoring for eBay, Amazon, and JD (Jingdong) to track owned items and detect arbitrage opportunities.

**Architecture:** Platform-specific monitor classes inheriting from BaseMonitor, unified MerchandiseAlert, cross-platform arbitrage detection, CNY base currency.

**Tech Stack:** Python aiosqlite/requests, eBay Browse API (OAuth2), Amazon PA-API, JD Open Platform API

---

## File Structure

```
agents/monitor/
├── base.py                           # BaseMonitor, Alert (existing)
├── ebay_monitor.py                   # sports cards (existing)
├── ebay_merchandise_monitor.py      # NEW: merchandise on eBay
├── amazon_monitor.py                 # NEW
├── jd_monitor.py                    # NEW: JD (Jingdong)
├── scheduler.py                     # add new monitors (modify)
└── __init__.py                      # exports (modify)

dashboard/backend/
├── database.py                       # add get_watchlist_items, upsert_merchandise (modify)
├── routers/
│   └── watchlist.py                 # NEW: merchandise watchlist API

config/
├── api_providers.yaml                # add amazon, jd credentials (modify)
└── agent_settings.yaml              # add merchandise config (modify)

tests/
├── test_merchandise_monitor.py      # NEW
└── test_monitor.py                  # existing

docs/superpowers/specs/
└── 2026-05-12-merchandise-monitor-design.md  # existing
```

---

## Phase 1: eBay Merchandise Extension

### Task 1: Add MerchandiseAlert dataclass to base.py

**Files:**
- Modify: `agents/monitor/base.py:1-43`
- Test: `tests/test_merchandise_monitor.py`

- [ ] **Step 1: Add MerchandiseAlert to base.py**

Add after the Alert dataclass:

```python
@dataclass
class MerchandiseAlert(Alert):
    """Alert for merchandise price changes with cross-platform data."""
    brand: str = ""
    model: str = ""
    variant: str = ""
    platforms: dict = field(default_factory=dict)  # {"eBay": 150.00, "Amazon": 145.00, ...}
    purchase_price: float = 0.0
    purchase_currency: str = "CNY"
    arbitrage_opportunity: bool = False
    source_platform: str = ""
```

- [ ] **Step 2: Write test**

```python
def test_merchandise_alert_fields():
    alert = MerchandiseAlert(
        source="ebay",
        alert_type="price_drop",
        symbol="RW-875-10D",
        exchange="eBay",
        brand="Red Wing",
        model="875",
        variant="Size 10D",
        platforms={"eBay": 150.00, "Amazon": 145.00},
        purchase_price=149.99,
        purchase_currency="USD",
        change_pct=0.01,
        arbitrage_opportunity=True,
        source_platform="Amazon",
    )
    assert alert.brand == "Red Wing"
    assert alert.arbitrage_opportunity is True
    assert alert.source_platform == "Amazon"
```

- [ ] **Step 3: Run test**

Run: `pytest tests/test_merchandise_monitor.py::test_merchandise_alert_fields -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add agents/monitor/base.py tests/test_merchandise_monitor.py
git commit -m "feat: add MerchandiseAlert dataclass to base monitor"
```

---

### Task 2: Create EbayMerchandiseMonitor

**Files:**
- Create: `agents/monitor/ebay_merchandise_monitor.py`
- Modify: `agents/monitor/scheduler.py:23-29`
- Test: `tests/test_merchandise_monitor.py`

- [ ] **Step 1: Write failing test**

```python
@pytest.mark.asyncio
async def test_ebay_merchandise_monitor_name():
    m = EbayMerchandiseMonitor()
    assert m.name == "ebay_merchandise"

@pytest.mark.asyncio
async def test_ebay_merchandise_monitor_disabled():
    m = EbayMerchandiseMonitor()
    m.config["enabled"] = False
    alerts = await m.check()
    assert alerts == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_merchandise_monitor.py -v`
Expected: FAIL - EbayMerchandiseMonitor not found

- [ ] **Step 3: Create EbayMerchandiseMonitor**

```python
"""eBay merchandise monitor for branded products.

Searches eBay by brand + model to track prices of owned merchandise.
"""
import asyncio
import json
import logging
import os
import requests
from datetime import datetime
from ..config import get_market_data_config
from .base import BaseMonitor, MerchandiseAlert

logger = logging.getLogger(__name__)


class EbayMerchandiseMonitor(BaseMonitor):
    """Monitor branded merchandise prices via eBay Browse API."""

    BASE_URL = "https://api.ebay.com/buy/browse/v1"
    TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"

    @property
    def name(self) -> str:
        return "ebay_merchandise"

    def __init__(self):
        config = get_market_data_config().get("ebay", {})
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

    async def _get_token(self) -> str | None:
        client_id = self.config.get("client_id")
        client_secret = self.config.get("client_secret")
        if not client_id or not client_secret:
            logger.warning("[ebay_merchandise] No credentials configured")
            return None

        data = {
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope",
        }

        try:
            resp = requests.post(
                self.TOKEN_URL,
                data=data,
                auth=(client_id, client_secret),
                proxies=self._proxies,
                timeout=15,
            )
            if resp.status_code != 200:
                logger.warning(f"[ebay_merchandise] Token failed: {resp.status_code}")
                return None
            return resp.json()["access_token"]
        except Exception as e:
            logger.error(f"[ebay_merchandise] Token error: {e}")
            return None

    def _parse_notes(self, notes: str) -> dict:
        """Parse pipe-separated merchandise metadata.

        Format: Brand|Model|Variant|PurchasePrice|PurchaseCurrency
        Example: Red Wing|875|Size 10D|149.99|USD
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
        """Check all watched merchandise from SQLite for price changes."""
        if not self.config.get("enabled", True):
            return []

        token = await self._get_token()
        if not token:
            return []

        alerts = []
        from .. import database as db
        try:
            watched = await db.get_watchlist_items("merchandise")
        except Exception as e:
            logger.error(f"[ebay_merchandise] Failed to read watchlist: {e}")
            return alerts

        for item in watched:
            try:
                alert = await self._check_item(token, item)
                if alert:
                    alerts.append(alert)
            except Exception as e:
                logger.error(f"[ebay_merchandise] Error checking {item.get('symbol')}: {e}")

        self.last_check = datetime.now()
        return alerts

    async def _check_item(self, token: str, item: dict) -> MerchandiseAlert | None:
        meta = self._parse_notes(item.get("notes", ""))
        search_term = f"{meta.get('brand', '')} {meta.get('model', '')}".strip()
        if not search_term:
            return None

        current_price = await self._fetch_price(token, search_term, meta.get("variant"))
        if current_price is None:
            return None

        purchase_price = meta.get("purchase_price")
        symbol = item.get("symbol", search_term)

        # Store in cache
        try:
            from .. import database as db
            await db.set_market_cache(
                symbol=symbol,
                data_type="merchandise_price",
                raw_data={"price": current_price, "purchase_price": purchase_price},
                exchange="eBay",
            )
        except Exception:
            pass

        if purchase_price:
            # Check for price drop from purchase
            change_pct = (current_price - purchase_price) / purchase_price
            if change_pct < -self.threshold:
                return MerchandiseAlert(
                    source="ebay_merchandise",
                    alert_type="owned_price_drop",
                    symbol=symbol,
                    exchange="eBay",
                    brand=meta.get("brand", ""),
                    model=meta.get("model", ""),
                    variant=meta.get("variant", ""),
                    platforms={"eBay": current_price},
                    purchase_price=purchase_price,
                    purchase_currency=meta.get("purchase_currency", "CNY"),
                    current_price=current_price,
                    current_platform="eBay",
                    change_pct=change_pct,
                    details={"search_term": search_term},
                    priority="high" if change_pct < -0.10 else "normal",
                )

        return None

    async def _fetch_price(self, token: str, search_term: str, variant: str = "") -> float | None:
        """Query eBay sold/completed listings and return median price."""
        headers = {
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
            "Content-Type": "application/json",
        }

        params = {
            "q": search_term,
            "filter": "buyingOptions:FIXED_PRICE",
            "sort": "endDate:asc",
            "limit": "10",
        }

        if variant:
            params["q"] = f"{search_term} {variant}"

        try:
            resp = requests.get(
                f"{self.BASE_URL}/item_summary/search",
                headers=headers,
                params=params,
                proxies=self._proxies,
                timeout=15,
            )
            if resp.status_code != 200:
                logger.warning(f"[ebay_merchandise] API {resp.status_code}")
                return None

            items = resp.json().get("itemSummaries", [])
            if not items:
                return None

            prices = [float(i.get("price", {}).get("value", 0)) for i in items if i.get("price", {}).get("value")]
            if not prices:
                return None

            return sorted(prices)[len(prices) // 2]
        except Exception as e:
            logger.error(f"[ebay_merchandise] Request error: {e}")
            return None

    async def get_watchlist(self) -> list[dict]:
        """Return eBay merchandise watchlist items with current prices."""
        items = []
        from .. import database as db
        try:
            watched = await db.get_watchlist_items("merchandise")
        except Exception:
            return items

        for item in watched:
            meta = self._parse_notes(item.get("notes", ""))
            items.append({
                "symbol": item.get("symbol", ""),
                "brand": meta.get("brand", ""),
                "model": meta.get("model", ""),
                "variant": meta.get("variant", ""),
                "purchase_price": meta.get("purchase_price"),
                "purchase_currency": meta.get("purchase_currency", "CNY"),
                "exchange": "eBay",
            })
        return items
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_merchandise_monitor.py -v`
Expected: PASS

- [ ] **Step 5: Add to scheduler**

Modify `agents/monitor/scheduler.py`:
```python
from .ebay_merchandise_monitor import EbayMerchandiseMonitor

MONITORS = [
    BinanceMonitor(),
    OKXMonitor(),
    AKShareMonitor(),
    YFinanceMonitor(),
    EbayMonitor(),               # sports cards
    EbayMerchandiseMonitor(),    # NEW: merchandise
]
```

- [ ] **Step 6: Commit**

```bash
git add agents/monitor/ebay_merchandise_monitor.py agents/monitor/scheduler.py tests/test_merchandise_monitor.py
git commit -m "feat: add EbayMerchandiseMonitor for branded merchandise tracking"
```

---

## Phase 2: Amazon Monitor

### Task 3: Create AmazonMonitor

**Files:**
- Create: `agents/monitor/amazon_monitor.py`
- Modify: `config/api_providers.yaml`
- Modify: `config/agent_settings.yaml`
- Test: `tests/test_merchandise_monitor.py`

- [ ] **Step 1: Add Amazon config**

Add to `config/api_providers.yaml`:
```yaml
amazon:
  access_key: ${AMAZON_ACCESS_KEY}
  secret_key: ${AMAZON_SECRET_KEY}
  partner_tag: ${AMAZON_PARTNER_TAG}
```

Add to `config/agent_settings.yaml`:
```yaml
amazon:
  enabled: true
  marketplace: "ATVPDKIKX0DER"  # US marketplace
```

- [ ] **Step 2: Write failing test**

```python
def test_amazon_monitor_name():
    m = AmazonMonitor()
    assert m.name == "amazon"
```

- [ ] **Step 3: Run test**

Run: `pytest tests/test_merchandise_monitor.py::test_amazon_monitor_name -v`
Expected: FAIL

- [ ] **Step 4: Create AmazonMonitor**

```python
"""Amazon PA-API monitor for merchandise prices.

Requires Amazon Affiliate/PA-API credentials.
"""
import hashlib
import hmac
import time
import logging
import requests
from datetime import datetime
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
        import os
        for var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
            val = os.environ.get(var)
            if val:
                return {"http": val, "https": val}
        return None

    def is_market_open(self) -> bool:
        return True

    def _get_aws_sig(self, method: str, url: str, payload: str, access_key: str, secret_key: str) -> dict:
        """Generate AWS Signature Version 4 headers for PA-API."""
        import datetime as dt
        now = dt.datetime.utcnow()
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
        from urllib.parse import urlparse

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
                        prices.append(float(price.replace("$", "").replace(",", "")))

            if not prices:
                return None

            return sorted(prices)[len(prices) // 2]
        except Exception as e:
            logger.error(f"[amazon] Request error: {e}")
            return None
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_merchandise_monitor.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add agents/monitor/amazon_monitor.py config/api_providers.yaml config/agent_settings.yaml tests/test_merchandise_monitor.py
git commit -m "feat: add AmazonMonitor for merchandise price tracking"
```

---

## Phase 3: JD (Jingdong) Monitor

### Task 4: Create JDMonitor

**Files:**
- Create: `agents/monitor/jd_monitor.py`
- Modify: `config/api_providers.yaml`
- Modify: `config/agent_settings.yaml`
- Test: `tests/test_merchandise_monitor.py`

- [ ] **Step 1: Add JD config**

Add to `config/api_providers.yaml`:
```yaml
jd:
  app_key: ${JD_APP_KEY}
  app_secret: ${JD_APP_SECRET}
```

Add to `config/agent_settings.yaml`:
```yaml
jd:
  enabled: true
```

- [ ] **Step 2: Write failing test**

```python
def test_jd_monitor_name():
    m = JDMonitor()
    assert m.name == "jd"
```

- [ ] **Step 3: Run test**

Run: `pytest tests/test_merchandise_monitor.py::test_jd_monitor_name -v`
Expected: FAIL

- [ ] **Step 4: Create JDMonitor**

```python
"""JD (Jingdong) Open Platform monitor for merchandise prices.

Uses JD Open Platform API for product search and pricing.
"""
import hashlib
import time
import json
import logging
import requests
from datetime import datetime
from ..config import get_market_data_config
from .base import BaseMonitor, MerchandiseAlert

logger = logging.getLogger(__name__)


class JDMonitor(BaseMonitor):
    """Monitor branded merchandise prices via JD Open Platform."""

    BASE_URL = "https://router.jd.com/api"

    @property
    def name(self) -> str:
        return "jd"

    def __init__(self):
        config = get_market_data_config().get("jd", {})
        config["enabled"] = config.get("enabled", True)
        super().__init__(config)
        self.threshold = self.config.get("price_change_threshold", 0.05)
        self._proxies = self._detect_proxy()

    def _detect_proxy(self) -> dict | None:
        import os
        for var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
            val = os.environ.get(var)
            if val:
                return {"http": val, "https": val}
        return None

    def is_market_open(self) -> bool:
        return True

    def _generate_sign(self, params: dict, app_secret: str) -> str:
        """Generate JD API sign using MD5."""
        sorted_params = sorted(params.items(), key=lambda x: x[0])
        sign_str = app_secret + "".join(f"{k}{v}" for k, v in sorted_params) + app_secret
        return hashlib.md5(sign_str.encode()).hexdigest().upper()

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

        app_key = self.config.get("app_key")
        app_secret = self.config.get("app_secret")

        if not app_key or not app_secret:
            logger.warning("[jd] Missing credentials")
            return []

        alerts = []
        from .. import database as db
        try:
            watched = await db.get_watchlist_items("merchandise")
        except Exception as e:
            logger.error(f"[jd] Failed to read watchlist: {e}")
            return alerts

        for item in watched:
            try:
                alert = await self._check_item(app_key, app_secret, item)
                if alert:
                    alerts.append(alert)
            except Exception as e:
                logger.error(f"[jd] Error checking {item.get('symbol')}: {e}")

        self.last_check = datetime.now()
        return alerts

    async def _check_item(self, app_key: str, app_secret: str, item: dict) -> MerchandiseAlert | None:
        meta = self._parse_notes(item.get("notes", ""))
        search_term = f"{meta.get('brand', '')} {meta.get('model', '')}".strip()
        if not search_term:
            return None

        current_price = await self._fetch_price(app_key, app_secret, search_term)
        if current_price is None:
            return None

        purchase_price = meta.get("purchase_price")
        symbol = item.get("symbol", search_term)

        if purchase_price:
            change_pct = (current_price - purchase_price) / purchase_price
            if change_pct < -self.threshold:
                return MerchandiseAlert(
                    source="jd",
                    alert_type="owned_price_drop",
                    symbol=symbol,
                    exchange="JD",
                    brand=meta.get("brand", ""),
                    model=meta.get("model", ""),
                    variant=meta.get("variant", ""),
                    platforms={"JD": current_price},
                    purchase_price=purchase_price,
                    purchase_currency=meta.get("purchase_currency", "CNY"),
                    current_price=current_price,
                    current_platform="JD",
                    change_pct=change_pct,
                    details={"search_term": search_term},
                    priority="high" if change_pct < -0.10 else "normal",
                )

        return None

    async def _fetch_price(self, app_key: str, app_secret: str, search_term: str) -> float | None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        params = {
            "app_key": app_key,
            "v": "1.0",
            "method": "jd.union.open.goods.query",
            "timestamp": timestamp,
            "format": "json",
            "sign_method": "md5",
            "360buy_param_json": json.dumps({
                "goodsReq": {
                    "keyword": search_term,
                    "page_size": 10,
                }
            }),
        }

        params["sign"] = self._generate_sign(params, app_secret)

        try:
            resp = requests.get(
                self.BASE_URL,
                params=params,
                proxies=self._proxies,
                timeout=15,
            )
            if resp.status_code != 200:
                logger.warning(f"[jd] API {resp.status_code}")
                return None

            data = resp.json()
            # JD API response structure varies, adjust based on actual API
            # This is a placeholder for the actual response parsing
            if data.get("jd_union_open_goods_query_response", {}).get("code") != "0":
                logger.warning(f"[jd] API error: {data}")
                return None

            goods_list = data.get("jd_union_open_goods_query_response", {}).get("goodsList", [])
            if not goods_list:
                return None

            # Extract lowest price from results
            prices = []
            for item in goods_list:
                price_info = item.get("priceInfo", {})
                lowest_price = price_info.get("lowestPrice")
                if lowest_price:
                    prices.append(float(lowest_price))

            if not prices:
                return None

            return min(prices)
        except Exception as e:
            logger.error(f"[jd] Request error: {e}")
            return None
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_merchandise_monitor.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add agents/monitor/jd_monitor.py config/api_providers.yaml config/agent_settings.yaml tests/test_merchandise_monitor.py
git commit -m "feat: add JDMonitor for merchandise price tracking"
```

---

## Phase 4: Cross-Platform Arbitrage Detection

### Task 5: Implement ArbitrageDetector

**Files:**
- Create: `agents/monitor/arbitrage.py`
- Modify: `agents/monitor/scheduler.py`
- Test: `tests/test_merchandise_monitor.py`

- [ ] **Step 1: Write failing test**

```python
@pytest.mark.asyncio
async def test_arbitrage_detector_find_opportunity():
    detector = ArbitrageDetector()
    prices = {"eBay": 150.0, "Amazon": 135.0, "JD": 140.0}
    opp = detector.find_opportunity("Test Item", prices, threshold=0.05)
    assert opp is not None
    assert opp["source_platform"] == "Amazon"
    assert opp["best_platform"] == "eBay"
    assert opp["margin_pct"] == pytest.approx(0.10, rel=0.01)
```

- [ ] **Step 2: Run test**

Run: `pytest tests/test_merchandise_monitor.py::test_arbitrage_detector_find_opportunity -v`
Expected: FAIL

- [ ] **Step 3: Create ArbitrageDetector**

```python
"""Cross-platform arbitrage detection for merchandise.

Compares prices across platforms to find buying/selling opportunities.
"""
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
                "source_platform": best_platform,  # where to buy
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
        """Check all watched merchandise for arbitrage opportunities.

        This would be called by the scheduler to aggregate prices from
        all platforms and detect opportunities.
        """
        opportunities = []

        for item in watched_items:
            # Collect prices from market cache for all platforms
            platform_prices = {}

            from .. import database as db
            symbol = item.get("symbol")

            for platform in ["eBay", "Amazon", "JD"]:
                try:
                    cache = await db.get_market_cache(symbol, platform, "merchandise_price")
                    if cache:
                        raw = cache.get("raw_data", "{}")
                        if isinstance(raw, str):
                            import json
                            raw = json.loads(raw)
                        price = raw.get("price") if isinstance(raw, dict) else None
                        if price:
                            platform_prices[platform] = price
                except Exception as e:
                    logger.debug(f"[arbitrage] Could not get {platform} price for {symbol}: {e}")

            if len(platform_prices) >= 2:
                meta = item.get("notes", "").split("|")
                purchase_price = float(meta[3]) if len(meta) > 3 and meta[3] else None
                product_name = f"{meta[0]} {meta[1]}".strip() if len(meta) >= 2 else symbol

                opp = self.find_opportunity(product_name, platform_prices, purchase_price)
                if opp:
                    opp["symbol"] = symbol
                    opportunities.append(opp)

        return opportunities
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_merchandise_monitor.py::test_arbitrage_detector_find_opportunity -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/monitor/arbitrage.py tests/test_merchandise_monitor.py
git commit -m "feat: add ArbitrageDetector for cross-platform price comparison"
```

---

## Phase 5: Database & Dashboard Integration

### Task 6: Add merchandise watchlist database functions

**Files:**
- Modify: `dashboard/backend/database.py`
- Modify: `agents/__init__.py`
- Test: `tests/test_merchandise_monitor.py`

- [ ] **Step 1: Add get_watchlist_items for merchandise**

Add to `dashboard/backend/database.py`:

```python
async def get_watchlist_items(category: str = None) -> list[dict]:
    """Get watchlist items, optionally filtered by category."""
    db = await get_db()
    try:
        if category:
            cursor = await db.execute(
                "SELECT * FROM watchlist WHERE asset_class=? ORDER BY created_at DESC",
                (category,)
            )
        else:
            cursor = await db.execute("SELECT * FROM watchlist ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()
```

Also export this from agents/database.py for monitor access.

- [ ] **Step 2: Add upsert_merchandise function**

```python
async def upsert_merchandise(
    symbol: str,
    brand: str,
    model: str,
    variant: str,
    purchase_price: float,
    purchase_currency: str = "CNY",
    exchange: str = "eBay",
) -> int:
    """Add or update merchandise in watchlist."""
    notes = f"{brand}|{model}|{variant}|{purchase_price}|{purchase_currency}"
    db = await get_db()
    try:
        await db.execute(
            """
            INSERT INTO watchlist (asset_class, symbol, exchange, notes)
            VALUES ('merchandise', ?, ?, ?)
            ON CONFLICT(asset_class, symbol, exchange)
            DO UPDATE SET notes=excluded.notes
            """,
            (symbol, exchange, notes),
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT id FROM watchlist WHERE asset_class='merchandise' AND symbol=? AND exchange=?",
            (symbol, exchange),
        )
        row = await cursor.fetchone()
        return row["id"] if row else 0
    finally:
        await db.close()
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_merchandise_monitor.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add dashboard/backend/database.py agents/__init__.py
git commit -m "feat: add merchandise watchlist database functions"
```

---

## Phase 6: Update Scheduler with All Monitors

### Task 7: Finalize scheduler integration

**Files:**
- Modify: `agents/monitor/scheduler.py`

- [ ] **Step 1: Add all monitors to scheduler**

```python
from .ebay_merchandise_monitor import EbayMerchandiseMonitor
from .amazon_monitor import AmazonMonitor
from .jd_monitor import JDMonitor

MONITORS = [
    BinanceMonitor(),
    OKXMonitor(),
    AKShareMonitor(),
    YFinanceMonitor(),
    EbayMonitor(),               # sports cards
    EbayMerchandiseMonitor(),    # NEW
    AmazonMonitor(),             # NEW
    JDMonitor(),                # NEW
]
```

- [ ] **Step 2: Add arbitrage check after monitor cycle**

In `run_monitor_cycle()`, after collecting all alerts, add:

```python
from .arbitrage import ArbitrageDetector

async def run_monitor_cycle() -> list[Alert]:
    # ... existing code ...

    # Run arbitrage detection
    try:
        detector = ArbitrageDetector(threshold=0.10)
        arbitrage_alerts = await detector.check_all_products([])
        for opp in arbitrage_alerts:
            alerts.append(Alert(
                source="arbitrage",
                alert_type="arbitrage_opportunity",
                symbol=opp.get("symbol", ""),
                exchange="multi",
                details=opp,
                priority="high",
            ))
    except Exception as e:
        logger.error(f"[scheduler] Arbitrage detection error: {e}")

    return all_alerts
```

- [ ] **Step 3: Commit**

```bash
git add agents/monitor/scheduler.py
git commit -m "feat: integrate all merchandise monitors into scheduler"
```

---

## Verification Checklist

After all tasks complete, verify:

- [ ] All tests pass: `pytest tests/test_merchandise_monitor.py -v`
- [ ] Scheduler starts without errors: `python -m agents.monitor.scheduler`
- [ ] Database schema includes merchandise category
- [ ] Config files have placeholder credentials for Amazon and JD
- [ ] eBay merchandise uses existing OAuth flow
