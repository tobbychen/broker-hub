# Merchandise Monitor Design Spec
**Date:** 2026-05-12
**Version:** 1.0

---

## 1. Overview

A new product category monitor that tracks branded merchandise prices across multiple platforms (eBay, Amazon, Alibaba, Xianyu, PDD). Designed for two use cases:
- **Own items for sale**: Track price changes of owned inventory to optimize selling timing
- **Underpriced opportunities**: Find items priced below market value for arbitrage/flipping

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     MERCHANDISE MONITORS                     │
├─────────────┬─────────────┬─────────────┬────────────┬────┤
│ eBayMonitor │AmazonMonitor│AliMonitor   │XianyuMonitor│PDD │
└─────────────┴─────────────┴─────────────┴────────────┴────┘
                            │
                     BaseMerchandiseMonitor
                     (inherits BaseMonitor)
                            │
                            ▼
              ┌─────────────────────────────┐
              │   Unified MerchandiseAlert  │
              │   (extends Alert)           │
              └─────────────────────────────┘
                            │
                            ▼
                      Scheduler
                            │
                            ▼
                      Dispatcher
```

---

## 3. Data Model

### 3.1 Watchlist Item Format

Products stored in `watchlist` table with `category = "merchandise"`:

```
symbol: "RW-875-{variant_id}"
notes: "Brand|Model|Variant|Platform|PurchasePrice|PurchaseCurrency"
```

Example:
```
symbol: "RW-875-10D"
notes: "Red Wing|875|Size 10D|eBay|149.99|USD"
```

### 3.2 Alert Types

| Alert Type | Trigger | Priority |
|------------|---------|----------|
| `owned_price_drop` | Price falls below threshold % of purchase price | high/normal |
| `arbitrage_opportunity` | Same item cheaper on another platform | high |
| `price_spike` | Significant price change in 24h | normal |

### 3.3 MerchandiseAlert Fields (extends Alert)

```python
@dataclass
class MerchandiseAlert(Alert):
    brand: str
    model: str
    variant: str
    platforms: dict  # {"eBay": 150.00, "Amazon": 145.00, ...}
    purchase_price: float
    purchase_currency: str
    current_price: float
    current_platform: str
    change_pct: float  # % change from purchase
    arbitrage_opportunity: bool = False
    source_platform: str = None  # where arbitrage was found
```

---

## 4. Platform Implementations

### 4.1 eBay Monitor (eBayMonitor)
- **API**: eBay Browse API (OAuth2)
- **Status**: Already exists — extend for merchandise
- **Note**: Reuse existing OAuth flow, adjust search query pattern

### 4.2 Amazon Monitor (AmazonMonitor)
- **API**: Product Advertising API or scrape
- **Status**: To be implemented
- **Note**: Requires AWS credentials or scraping approach

### 4.3 Alibaba Monitor (AlibabaMonitor)
- **API**: Alibaba Open Platform / 1688 API
- **Status**: To be implemented
- **Note**: May require affiliate account or scraping

### 4.4 Xianyu Monitor (XianyuMonitor)
- **API**: Xianyu / 闲鱼 unofficial API or scrape
- **Status**: To be implemented
- **Note**: Likely scraping required, may need app-based access

### 4.5 PDD Monitor (PDDMonitor)
- **API**: Pinduoduo open platform or scrape
- **Status**: To be implemented
- **Note**: Likely scraping required

---

## 5. Cross-Platform Arbitrage Detection

```
For each watched product (brand + model):
  1. Query all enabled platforms
  2. Normalize prices to CNY (using exchange rates)
  3. Find lowest price across platforms
  4. If difference > threshold (e.g., 10%) → arbitrage alert
  5. Alert includes: which platform has opportunity, potential profit margin
```

---

## 6. Configuration

### 6.1 Agent Settings (config/agent_settings.yaml)

```yaml
merchandise:
  enabled: true
  check_interval_seconds: 60  # or match global monitor interval
  price_drop_threshold: 0.10  # alert if price drops 10% below purchase
  arbitrage_threshold: 0.10   # alert if same item 10% cheaper elsewhere
  currency: CNY
  platforms:
    ebay:
      enabled: true
      priority: 1
    amazon:
      enabled: true
      priority: 2
    alibaba:
      enabled: false  # require credentials
      priority: 3
    xianyu:
      enabled: false  # require credentials
      priority: 4
    pdd:
      enabled: false  # require credentials
      priority: 5
```

### 6.2 API Credentials (config/api_providers.yaml)

```yaml
merchandise_apis:
  ebay:
    client_id: ${EBAY_CLIENT_ID}
    client_secret: ${EBAY_CLIENT_SECRET}
  amazon:
    access_key: ${AMAZON_ACCESS_KEY}
    secret_key: ${AMAZON_SECRET_KEY}
    partner_tag: ${AMAZON_PARTNER_TAG}
  # Other platforms added as implemented
```

---

## 7. Scheduler Integration

New monitors added to `MONITORS` list in scheduler:

```python
MONITORS = [
    BinanceMonitor(),
    OKXMonitor(),
    AKShareMonitor(),
    YFinanceMonitor(),
    EbayMonitor(),          # sports cards
    EbayMerchandiseMonitor(),   # NEW: merchandise on eBay
    AmazonMonitor(),            # NEW
    AlibabaMonitor(),           # NEW
    XianyuMonitor(),           # NEW
    PDDMonitor(),              # NEW
]
```

---

## 8. Dashboard Integration

### 8.1 Watchlist Management
- Add merchandise via: Brand + Model + Variant + Purchase Price + Platform
- View all tracked merchandise with current prices per platform
- Edit/Delete merchandise entries

### 8.2 Alert Display
- Same decision card format as sports cards
- Shows: Brand, Model, Variant, Price change %, Platforms comparison
- Action buttons: "View Details", "Adjust Price", "Remove"

---

## 9. Implementation Phases

### Phase 1: eBay Extension (Immediate)
- Extend existing EbayMonitor to support merchandise category
- Reuse OAuth flow, adjust search to brand+model pattern
- Add merchandise-specific watchlist parsing

### Phase 2: Amazon Monitor (Week 2)
- Implement AmazonMonitor
- Investigate API vs scraping approach
- Add credentials to config

### Phase 3: China Platforms (Week 3-4)
- Implement Xianyu, PDD, Alibaba monitors
- Handle CNY-only pricing
- Investigate data access methods per platform

---

## 10. File Structure

```
agents/monitor/
├── base.py                    # BaseMonitor, Alert (existing)
├── ebay_monitor.py            # sports cards (existing)
├── ebay_merchandise_monitor.py # NEW: merchandise on eBay
├── amazon_monitor.py          # NEW
├── alibaba_monitor.py         # NEW
├── xianyu_monitor.py          # NEW
├── pdd_monitor.py             # NEW
└── scheduler.py               # update MONITORS list
```

---

## 11. API Access Investigation

### 11.1 Alibaba / 1688

**Official API Options:**
- **Alibaba Open Platform** (open.alibaba.com): Requires enterprise account, API access for affiliates/partners
- **1688 API**: Similar requirements — typically need 1688 store or affiliate account
- **Aliexpress API**: More accessible but different product ecosystem

**Alternative Approaches:**
- **Affiliate API**: Alibaba affiliate program provides product data access
- **Third-party data services**: Services like 蝉妈妈 (chanmama), 飞瓜 (feigua) aggregate 1688/AliExpress data
- **Web scraping**: Possible with proxies, but violates ToS

**Recommended Path:** Check if you have Alibaba affiliate account access, or investigate 蝉妈妈/飞瓜 for data aggregation APIs

---

### 11.2 Xianyu (闲鱼)

**Official API Options:**
- **No public API**: Xianyu (Taobao's C2C platform) has no official developer API
- **Taobao Open Platform**: Different ecosystem, requires store/enterprise account

**Alternative Approaches:**
- **App-based scraping**: Xianyu is mobile-first, web access limited
- **Unofficial APIs**: Some community projects exist but unreliable/unstable
- **WeChat mini-program**: Alternative access point, also unofficial
- **Third-party aggregators**: Some tools aggregate Xianyu listings

**Recommended Path:** Likely requires scraping via mobile app automation (e.g., ADB + custom app) or third-party data services

---

### 11.3 Pinduoduo (拼多多)

**Official API Options:**
- **PDD Open Platform**: Requires business license + application
- Access is restricted — not publicly available for individual developers

**Alternative Approaches:**
- **Pinduoduo Alliance APIs**: Some affiliate/referral APIs exist
- **Third-party services**: 多多客 (duoduoke), 折疯了 (zhefengmai) aggregate PDD data
- **Web scraping**: Challenging due to aggressive anti-bot measures, requires residential proxies

**Recommended Path:** Check PDD affiliate program or use third-party data aggregation services

---

### 11.4 Summary Table

| Platform | Official API | Access Difficulty | Recommended Approach |
|----------|--------------|-------------------|---------------------|
| eBay | Yes (Browse API) | Easy (OAuth2) | Direct API - existing |
| Amazon | Yes (PA-API) | Medium (AWS creds) | PA-API or scraping |
| Alibaba/1688 | Partial | Hard (enterprise) | Affiliate API or 蝉妈妈 |
| Xianyu | No | Very Hard | App scraping or third-party |
| PDD | Partial | Hard | Affiliate API or third-party |

---

### 11.5 Action Items for User

Please verify:
1. Do you have Alibaba affiliate account access?
2. Do you have PDD merchant/affiliate access?
3. Are you willing to use third-party data services (蝉妈妈, 飞瓜, etc.)?
4. Are you comfortable with app-based scraping if needed (for Xianyu)?
