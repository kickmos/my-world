#!/usr/bin/env python3
import csv
import io
import json
import math
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

UA = {"User-Agent": "Mozilla/5.0 capital-flow-monitor/2.0"}

SYMBOLS = {
    "local": "THB=X",
    "usd": "UUP",
    "mmf": "BIL",
    "bonds": "TLT",
    "gold": "GLD",
    "crypto": "BTC-USD",
    "stocks": "QQQ",
    "global": "ACWI",
    "dxy": "DX-Y.NYB",
    "nq": "NQ=F",
    "es": "ES=F",
    "zn": "ZN=F",
    "gc": "GC=F",
    "btcf": "BTC=F",
}

NEWS_QUERIES = {
    "local": "(Thailand economy OR Thai baht OR SET Thailand OR Bank of Thailand) when:3d",
    "usd": "(US dollar OR DXY OR Federal Reserve OR dollar liquidity) when:3d",
    "mmf": "(money market funds OR Treasury bills OR T-bills OR cash funds) when:4d",
    "bonds": "(US Treasury yields OR bond market OR credit spreads OR Treasury auction) when:3d",
    "gold": "(gold price OR gold market OR central bank gold OR COMEX gold) when:3d",
    "crypto": "(Bitcoin OR BTC OR stablecoin OR crypto market) when:3d",
    "stocks": "(S&P 500 OR Nasdaq OR US stocks OR semiconductor stocks) when:3d",
    "global": "(global markets OR Europe stocks OR Japan stocks OR China stocks OR emerging markets) when:3d",
}

TRUSTED_NEWS_SOURCES = (
    "Reuters","Bloomberg","CNBC","Associated Press","AP News","Financial Times",
    "The Wall Street Journal","MarketWatch","Yahoo Finance","Barron's",
    "CoinDesk","The Block","Nikkei Asia","Business Insider"
)

FRED_SERIES = {
    "walcl": "WALCL",           # Fed total assets; weekly
    "tga": "WTREGEN",           # Treasury General Account; weekly
    "rrp": "RRPONTSYD",         # ON RRP; daily, billions USD
    "hy_oas": "BAMLH0A0HYM2",   # US HY option-adjusted spread; daily
    "vix": "VIXCLS",             # VIX; daily
    "curve": "T10Y2Y",           # 10Y-2Y Treasury spread; daily
}

BASE_STATIONS = [
    ("local", "Local FX", "FX", "Domestic FX and local-asset pressure. THB is used as the first local-currency proxy."),
    ("usd", "USD Cash", "USD", "Global dollar funding and cash reservoir. UUP/DXY are market proxies, not direct cash-flow measurements."),
    ("mmf", "MMF / T-Bills", "CASH", "Cash-parking station. BIL is a fast market proxy; liquidity plumbing is confirmed separately."),
    ("bonds", "Bonds / Credit", "BONDS", "Duration and credit complex. TLT is the fast price proxy; HY spreads and the yield curve are confirmation layers."),
    ("gold", "Gold", "GOLD", "Monetary hedge / safe-haven station using GLD plus COMEX gold futures confirmation."),
    ("crypto", "Crypto", "BTC", "Digital-asset risk station using BTC spot plus stablecoin-liquidity confirmation."),
    ("stocks", "US Stocks", "EQUITY", "US equity risk station using QQQ plus VIX, credit and index-futures confirmation."),
    ("global", "Global Risk", "GLOBAL", "Global equity risk represented initially by ACWI, with USD and credit conditions as confirmation."),
]

ROUTE_GRAPH = {
    "local": [("usd", 1.25), ("global", 1.00), ("gold", 0.80)],
    "usd": [("mmf", 1.25), ("stocks", 1.15), ("gold", 0.85)],
    "mmf": [("stocks", 1.25), ("bonds", 1.05), ("crypto", 0.70)],
    "bonds": [("stocks", 1.10), ("gold", 0.90), ("mmf", 0.85)],
    "gold": [("usd", 1.00), ("crypto", 0.90), ("global", 0.75)],
    "crypto": [("stocks", 1.00), ("usd", 0.95), ("gold", 0.80)],
    "stocks": [("bonds", 1.00), ("usd", 0.95), ("global", 0.90)],
    "global": [("local", 1.00), ("usd", 0.95), ("gold", 0.75)],
}

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def http_json(url, timeout=15):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def fetch_yahoo(symbol):
    q = urllib.parse.quote(symbol, safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{q}?range=1mo&interval=1d&includePrePost=false"
    data = http_json(url, 12)
    result = data["chart"]["result"][0]
    quote = result["indicators"]["quote"][0]
    raw_closes = quote.get("close", [])
    raw_volumes = quote.get("volume", [])
    timestamps = result.get("timestamp", [])
    closes = [x for x in raw_closes if x is not None]
    volumes = [x for x in raw_volumes if x is not None]
    meta = result.get("meta", {})
    if len(closes) < 2:
        raise ValueError("not enough history")
    p = float(meta.get("regularMarketPrice") or closes[-1])
    prev = float(closes[-2])
    d5base = float(closes[-6] if len(closes) >= 6 else closes[0])
    r1 = (p / prev - 1) * 100 if prev else 0.0
    r5 = (p / d5base - 1) * 100 if d5base else 0.0
    vr = 1.0
    if len(volumes) >= 6 and volumes[-1]:
        avg = sum(volumes[-6:-1]) / max(1, len(volumes[-6:-1]))
        if avg > 0:
            vr = volumes[-1] / avg
    avg_vol = None
    if len(volumes) >= 6:
        sample = [v for v in volumes[-6:-1] if v is not None]
        if sample:
            avg_vol = sum(sample) / len(sample)
    history = []
    for ts, cl in zip(timestamps, raw_closes):
        if cl is None:
            continue
        history.append({"ts": int(ts), "close": float(cl)})
    return {
        "symbol": symbol, "price": p, "r1": r1, "r5": r5,
        "volume": (volumes[-1] if volumes and volumes[-1] not in (0, None) else None),
        "avg_volume_5d": avg_vol,
        "volume_ratio": vr, "market_time": meta.get("regularMarketTime"),
        "currency": meta.get("currency"), "source": "Yahoo Finance chart endpoint",
        "history": history,
    }

def safe_fetch(symbol):
    try:
        return fetch_yahoo(symbol)
    except Exception as e:
        return {"symbol": symbol, "error": str(e), "r1": 0.0, "r5": 0.0, "volume_ratio": 1.0, "source": "unavailable"}

def fetch_fred(series_id):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={urllib.parse.quote(series_id)}"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=15) as r:
        text = r.read().decode("utf-8")
    rows = []
    for row in csv.DictReader(io.StringIO(text)):
        raw = row.get(series_id)
        if raw in (None, "", "."):
            continue
        try:
            rows.append((row.get("DATE", ""), float(raw)))
        except ValueError:
            continue
    if not rows:
        raise ValueError("no FRED observations")
    latest = rows[-1]
    prev = rows[-2] if len(rows) > 1 else rows[-1]
    return {
        "series": series_id, "date": latest[0], "value": latest[1],
        "prev_date": prev[0], "prev": prev[1], "change": latest[1] - prev[1],
        "source": "FRED"
    }

def safe_fred(series_id):
    try:
        return fetch_fred(series_id)
    except Exception as e:
        return {"series": series_id, "error": str(e), "source": "unavailable"}

def fetch_stablecoins():
    # DefiLlama's public stablecoin chart; no API key.
    data = http_json("https://stablecoins.llama.fi/stablecoincharts/all", 15)
    rows = []
    for item in data:
        total = item.get("totalCirculating", {})
        usd = total.get("peggedUSD")
        if usd is None:
            continue
        try:
            rows.append((int(item.get("date", 0)), float(usd)))
        except (TypeError, ValueError):
            continue
    if not rows:
        raise ValueError("no stablecoin observations")
    rows.sort()
    latest = rows[-1]
    prev = rows[-2] if len(rows) > 1 else rows[-1]
    seven = rows[-8] if len(rows) >= 8 else rows[0]
    return {
        "date": latest[0], "value": latest[1],
        "d1": latest[1] - prev[1], "d7": latest[1] - seven[1],
        "source": "DefiLlama stablecoins"
    }

def safe_stablecoins():
    try:
        return fetch_stablecoins()
    except Exception as e:
        return {"error": str(e), "source": "unavailable"}

def fetch_google_news(query, limit=8):
    params = urllib.parse.urlencode({"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"})
    url = f"https://news.google.com/rss/search?{params}"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=15) as r:
        raw = r.read()
    root = ET.fromstring(raw)
    items, seen = [], set()
    now = datetime.now(timezone.utc)

    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_raw = (item.findtext("pubDate") or "").strip()
        source_node = item.find("source")
        source = ((source_node.text or "").strip() if source_node is not None else "")
        if not title or not link:
            continue

        clean_title = title
        if source and title.endswith(" - " + source):
            clean_title = title[:-(len(source)+3)].strip()

        key = clean_title.lower()
        if key in seen:
            continue
        seen.add(key)

        published = None
        age_hours = None
        if pub_raw:
            try:
                published = parsedate_to_datetime(pub_raw)
                if published.tzinfo is None:
                    published = published.replace(tzinfo=timezone.utc)
                published = published.astimezone(timezone.utc)
                age_hours = max(0.0, (now - published).total_seconds() / 3600.0)
            except Exception:
                pass

        trusted = any(name.lower() in source.lower() for name in TRUSTED_NEWS_SOURCES)
        recency = max(0.0, 72.0 - (age_hours if age_hours is not None else 72.0))
        items.append({
            "title": clean_title,
            "source": source or "Google News",
            "url": link,
            "publishedAt": published.isoformat() if published else None,
            "ageHours": round(age_hours, 1) if age_hours is not None else None,
            "trusted": trusted,
            "_score": (30 if trusted else 0) + recency,
        })

    items.sort(key=lambda x: x["_score"], reverse=True)
    for x in items:
        x.pop("_score", None)
    return items[:limit]

def safe_news(query, limit=8):
    try:
        return fetch_google_news(query, limit)
    except Exception as e:
        return [{
            "title": "News feed temporarily unavailable",
            "source": "System",
            "url": "",
            "publishedAt": None,
            "ageHours": None,
            "trusted": False,
            "error": str(e),
        }]

def score_market(m):
    if m.get("error"):
        return 0.0
    score = m["r1"] * 14 + m["r5"] * 6 + (m.get("volume_ratio", 1.0) - 1) * 12
    return clamp(score, -100, 100)

def state_from_score(s):
    if s >= 10:
        return "inflow", "+" if s < 28 else "++" if s < 55 else "+++"
    if s <= -10:
        return "outflow", "−" if s > -28 else "−−" if s > -55 else "−−−"
    return "neutral", "≈"

def velocity_from(m):
    if m.get("error"):
        return "?"
    accel = m["r1"] - m["r5"] / 5
    if accel > 1.0: return "↑↑"
    if accel > 0.25: return "↑"
    if accel < -1.0: return "↓↓"
    if accel < -0.25: return "↓"
    return "→"

def future_signal(m):
    s = score_market(m)
    if s > 9: return "positive"
    if s < -9: return "negative"
    return "neutral"

CFTC_DATASETS = {
    "tff_futures": "gpe5-46if",
    "legacy_futures": "6dca-aqww",
}

CFTC_CODES = {
    "nq": "209742",   # Nasdaq Mini / E-mini Nasdaq-100
    "es": "13874A",   # E-mini S&P 500
    "zn": "043602",   # UST 10Y Note
    "dxy": "098662",  # USD Index
    "btcf": "133741", # CME Bitcoin
    "gc": "088691",   # COMEX Gold
}

CFTC_MATCH = {
    "nq": ["NASDAQ MINI", "NASDAQ-100"],
    "es": ["E-MINI S&P 500", "S&P 500 CONSOLIDATED"],
    "zn": ["UST 10Y NOTE", "10Y NOTE"],
    "dxy": ["USD INDEX", "U.S. DOLLAR INDEX"],
    "btcf": ["BITCOIN - CHICAGO MERCANTILE EXCHANGE", "BITCOIN"],
    "gc": ["GOLD - COMMODITY EXCHANGE", "GOLD"],
}

def _num(row, *names):
    for name in names:
        raw = row.get(name)
        if raw not in (None, "", "."):
            try:
                return float(raw)
            except (TypeError, ValueError):
                pass
    return None

def _txt(row, *names):
    for name in names:
        raw = row.get(name)
        if raw not in (None, ""):
            return str(raw)
    return ""

def fetch_socrata(dataset_id, limit=5000):
    params = urllib.parse.urlencode({
        "$limit": str(limit),
        "$order": "report_date_as_yyyy_mm_dd DESC",
    })
    return http_json(f"https://publicreporting.cftc.gov/resource/{dataset_id}.json?{params}", 20)

def safe_socrata(dataset_id, limit=5000):
    try:
        data = fetch_socrata(dataset_id, limit)
        return data if isinstance(data, list) else []
    except Exception:
        return []

def find_cftc_row(rows, code, aliases):
    code_u = (code or "").strip().upper()
    for row in rows:
        row_code = _txt(row, "cftc_contract_market_code").strip().upper()
        if code_u and row_code == code_u:
            return row
    best = None
    for row in rows:
        name = (_txt(row, "market_and_exchange_names", "contract_market_name", "commodity_name") or "").upper()
        if any(alias.upper() in name for alias in aliases):
            if best is None:
                best = row
            if any(ex in name for ex in ("CHICAGO MERCANTILE", "CHICAGO BOARD", "COMMODITY EXCHANGE", "CME", "CBOT", "COMEX")):
                return row
    return best

def extract_tff(row):
    if not row:
        return None
    oi = _num(row, "open_interest_all")
    doi = _num(row, "change_in_open_interest_all", "change_in_open_interest")
    am_long = _num(row, "asset_mgr_positions_long", "asset_mgr_positions_long_all")
    am_short = _num(row, "asset_mgr_positions_short", "asset_mgr_positions_short_all")
    am_chg_long = _num(row, "change_in_asset_mgr_long", "change_in_asset_mgr_long_all")
    am_chg_short = _num(row, "change_in_asset_mgr_short", "change_in_asset_mgr_short_all")
    lev_long = _num(row, "lev_money_positions_long", "leveraged_funds_positions_long", "lev_money_positions_long_all")
    lev_short = _num(row, "lev_money_positions_short", "leveraged_funds_positions_short", "lev_money_positions_short_all")
    lev_chg_long = _num(row, "change_in_lev_money_long", "change_in_lev_money_long_all")
    lev_chg_short = _num(row, "change_in_lev_money_short", "change_in_lev_money_short_all")
    return {
        "reportDate": _txt(row, "report_date_as_yyyy_mm_dd"),
        "market": _txt(row, "market_and_exchange_names", "contract_market_name"),
        "openInterest": oi,
        "deltaOI": doi,
        "assetManager": {
            "long": am_long, "short": am_short,
            "net": (am_long-am_short) if am_long is not None and am_short is not None else None,
            "deltaLong": am_chg_long, "deltaShort": am_chg_short,
            "deltaNet": (am_chg_long-am_chg_short) if am_chg_long is not None and am_chg_short is not None else None,
        },
        "leveragedFunds": {
            "long": lev_long, "short": lev_short,
            "net": (lev_long-lev_short) if lev_long is not None and lev_short is not None else None,
            "deltaLong": lev_chg_long, "deltaShort": lev_chg_short,
            "deltaNet": (lev_chg_long-lev_chg_short) if lev_chg_long is not None and lev_chg_short is not None else None,
        }
    }

def extract_legacy(row):
    if not row:
        return None
    oi = _num(row, "open_interest_all")
    doi = _num(row, "change_in_open_interest_all", "change_in_open_interest")
    nl = _num(row, "noncomm_positions_long_all")
    ns = _num(row, "noncomm_positions_short_all")
    chl = _num(row, "change_in_noncomm_long_all", "change_in_noncomm_long")
    chs = _num(row, "change_in_noncomm_short_all", "change_in_noncomm_short")
    return {
        "reportDate": _txt(row, "report_date_as_yyyy_mm_dd"),
        "market": _txt(row, "market_and_exchange_names", "contract_market_name"),
        "openInterest": oi,
        "deltaOI": doi,
        "nonCommercial": {
            "long": nl, "short": ns,
            "net": (nl-ns) if nl is not None and ns is not None else None,
            "deltaLong": chl, "deltaShort": chs,
            "deltaNet": (chl-chs) if chl is not None and chs is not None else None,
        }
    }

def cot_aligned_return(market, report_date):
    if not report_date or not market.get("history"):
        return None
    try:
        dt = datetime.fromisoformat(str(report_date).replace("Z","+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None
    target = dt.timestamp()
    prior = target - 7 * 86400

    hist = sorted(market["history"], key=lambda x: x["ts"])
    def nearest_on_or_before(ts):
        candidates = [x for x in hist if x["ts"] <= ts + 18*3600]
        return candidates[-1] if candidates else None

    cur = nearest_on_or_before(target)
    prv = nearest_on_or_before(prior)
    if not cur or not prv or not prv.get("close"):
        return None
    return (cur["close"] / prv["close"] - 1) * 100

def classify_positioning(price_change_pct, delta_oi):
    if delta_oi is None:
        return {"label":"unavailable","bias":"neutral","explanation":"Open-interest change unavailable"}
    # Require a meaningful move; otherwise call it mixed/flat.
    if abs(price_change_pct or 0) < 0.10 or abs(delta_oi) < 1:
        return {"label":"mixed / flat","bias":"neutral","explanation":"Price or open-interest change is too small for a directional classification"}
    if price_change_pct > 0 and delta_oi > 0:
        return {"label":"new longs","bias":"positive","explanation":"Price rose while open interest increased"}
    if price_change_pct > 0 and delta_oi < 0:
        return {"label":"short covering","bias":"positive","explanation":"Price rose while open interest decreased"}
    if price_change_pct < 0 and delta_oi > 0:
        return {"label":"new shorts","bias":"negative","explanation":"Price fell while open interest increased"}
    return {"label":"long liquidation","bias":"negative","explanation":"Price fell while open interest decreased"}

def futures_positioning(markets, tff_rows, legacy_rows):
    out = {}
    for key in ("nq","es","zn","dxy","btcf"):
        row = find_cftc_row(tff_rows, CFTC_CODES[key], CFTC_MATCH[key])
        cot = extract_tff(row)
        m = markets[key]
        cot_week_return = cot_aligned_return(m, cot.get("reportDate") if cot else None)
        classifier_return = cot_week_return if cot_week_return is not None else m.get("r5",0)
        pos = classify_positioning(classifier_return, cot.get("deltaOI") if cot else None)
        out[key] = {
            "symbol": m.get("symbol"),
            "price": m.get("price"),
            "priceChange1D": round(m.get("r1",0),3),
            "priceChange5D": round(m.get("r5",0),3),
            "priceChangeCotWeek": round(cot_week_return,3) if cot_week_return is not None else None,
            "volume": m.get("volume"),
            "avgVolume5D": m.get("avg_volume_5d"),
            "volumeRatio": round(m.get("volume_ratio",1),2),
            "cot": cot,
            "positioning": pos,
            "horizon":"COT-week price vs weekly CFTC ΔOI",
            "source":"Yahoo market proxy + CFTC TFF Futures Only"
        }

    row = find_cftc_row(legacy_rows, CFTC_CODES["gc"], CFTC_MATCH["gc"])
    cot = extract_legacy(row)
    m = markets["gc"]
    cot_week_return = cot_aligned_return(m, cot.get("reportDate") if cot else None)
    classifier_return = cot_week_return if cot_week_return is not None else m.get("r5",0)
    pos = classify_positioning(classifier_return, cot.get("deltaOI") if cot else None)
    out["gc"] = {
        "symbol":m.get("symbol"),
        "price":m.get("price"),
        "priceChange1D":round(m.get("r1",0),3),
        "priceChange5D":round(m.get("r5",0),3),
        "priceChangeCotWeek":round(cot_week_return,3) if cot_week_return is not None else None,
        "volume":m.get("volume"),
        "avgVolume5D":m.get("avg_volume_5d"),
        "volumeRatio":round(m.get("volume_ratio",1),2),
        "cot":cot,
        "positioning":pos,
        "horizon":"COT-week price vs weekly CFTC ΔOI",
        "source":"Yahoo market proxy + CFTC Legacy Futures Only"
    }
    return out

def fred_change_signal(m, positive_when_up=True, threshold=0.0):
    if m.get("error"):
        return "neutral"
    ch = m.get("change", 0.0)
    signed = ch if positive_when_up else -ch
    if signed > threshold: return "positive"
    if signed < -threshold: return "negative"
    return "neutral"

def institutional_context(fred, stable):
    walcl, tga, rrp = fred["walcl"], fred["tga"], fred["rrp"]
    net_liq = None
    net_liq_prev = None
    if not walcl.get("error") and not tga.get("error") and not rrp.get("error"):
        # WALCL and WTREGEN are millions USD; RRPONTSYD is billions USD.
        net_liq = walcl["value"] - tga["value"] - rrp["value"] * 1000.0
        net_liq_prev = walcl["prev"] - tga["prev"] - rrp["prev"] * 1000.0

    hy = fred["hy_oas"]
    vix = fred["vix"]
    curve = fred["curve"]

    risk_confirmation = 0.0
    if not hy.get("error"):
        risk_confirmation += clamp(-hy.get("change", 0.0) * 35, -20, 20)
    if not vix.get("error"):
        risk_confirmation += clamp(-vix.get("change", 0.0) * 2.5, -20, 20)
    if net_liq is not None and net_liq_prev is not None:
        risk_confirmation += clamp((net_liq - net_liq_prev) / 10000.0, -15, 15)

    crypto_liq = 0.0
    if not stable.get("error") and stable.get("value"):
        crypto_liq = clamp(stable.get("d7", 0) / stable["value"] * 100 * 12, -18, 18)

    return {
        "net_liquidity_musd": net_liq,
        "net_liquidity_prev_musd": net_liq_prev,
        "risk_confirmation": clamp(risk_confirmation, -40, 40),
        "crypto_liquidity": crypto_liq,
        "hy_oas": hy,
        "vix": vix,
        "curve": curve,
    }

def confirmation_adjustments(ctx):
    r = ctx["risk_confirmation"]
    c = ctx["crypto_liquidity"]
    return {
        "local": r * 0.10,
        "usd": -r * 0.15,
        "mmf": -r * 0.25,
        "bonds": -r * 0.05,
        "gold": -r * 0.06,
        "crypto": r * 0.20 + c,
        "stocks": r * 0.42,
        "global": r * 0.32,
    }

def route_probabilities(source_id, scores, confirms):
    raw = []
    for target, weight in ROUTE_GRAPH[source_id]:
        attraction = clamp(
            50 + scores.get(target, 0) * 0.42
            + confirms.get(target, 0) * 0.48
            - scores.get(source_id, 0) * 0.08,
            8, 92
        )
        raw.append((target, max(1.0, weight * attraction)))
    total = sum(v for _, v in raw) or 1
    vals = [(t, int(round(v / total * 100))) for t, v in raw]
    diff = 100 - sum(v for _, v in vals)
    if vals:
        vals[0] = (vals[0][0], vals[0][1] + diff)
    return vals

def confidence_from(m, institutionals):
    if m.get("error"):
        base = 40
    else:
        base = 68
        if abs(m.get("r1", 0)) > 0.25: base += 4
        if abs(m.get("r5", 0)) > 0.8: base += 4
        if m.get("volume_ratio", 1) > 1.1: base += 4
    available = sum(1 for x in institutionals if x.get("status") != "unavailable")
    base += min(10, available * 2)
    return int(clamp(base, 40, 92))

def crowding_from(m):
    if m.get("error"): return 40
    return int(clamp(38 + abs(m.get("r5", 0)) * 5 + max(0, m.get("volume_ratio", 1)-1) * 12, 20, 92))

def fmt_num(v):
    if v is None: return "n/a"
    if abs(v) >= 1000: return f"{v:,.0f}"
    if abs(v) >= 100: return f"{v:,.1f}"
    return f"{v:,.2f}"

def inst_item(name, value, note, signal="neutral", status="observed"):
    return {"name": name, "value": value, "note": note, "signal": signal, "status": status}

def station_institutionals(sid, fred, stable, ctx):
    out = []
    if sid in ("usd", "mmf", "stocks", "global"):
        nl, prev = ctx["net_liquidity_musd"], ctx["net_liquidity_prev_musd"]
        if nl is not None:
            delta = nl - prev
            sig = "positive" if delta > 0 else "negative" if delta < 0 else "neutral"
            out.append(inst_item("Fed net-liquidity proxy", f"{delta/1000:+,.1f}B Δ", "WALCL − TGA − ON RRP; mixed-frequency liquidity plumbing proxy", sig))
        else:
            out.append(inst_item("Fed net-liquidity proxy", "unavailable", "One or more FRED inputs failed", "neutral", "unavailable"))

    if sid in ("stocks", "global", "bonds"):
        hy = fred["hy_oas"]
        if not hy.get("error"):
            sig = "positive" if hy["change"] < 0 else "negative" if hy["change"] > 0 else "neutral"
            out.append(inst_item("US HY credit spread", f"{hy['value']:.2f}% ({hy['change']:+.2f})", "Narrowing spread confirms risk appetite; widening spread warns of stress", sig))
        vix = fred["vix"]
        if sid in ("stocks", "global") and not vix.get("error"):
            sig = "positive" if vix["change"] < 0 else "negative" if vix["change"] > 0 else "neutral"
            out.append(inst_item("VIX", f"{vix['value']:.2f} ({vix['change']:+.2f})", "Volatility confirmation, not capital flow", sig))

    if sid == "bonds":
        curve = fred["curve"]
        if not curve.get("error"):
            sig = "positive" if curve["value"] > 0 else "negative"
            out.append(inst_item("10Y–2Y curve", f"{curve['value']:+.2f}%", "Macro regime / curve-shape confirmation", sig))

    if sid == "crypto":
        if not stable.get("error"):
            denom = stable["value"] or 1
            d7pct = stable["d7"] / denom * 100
            sig = "positive" if stable["d7"] > 0 else "negative" if stable["d7"] < 0 else "neutral"
            out.append(inst_item("Stablecoin supply", f"{stable['value']/1e9:,.1f}B", f"7D change {stable['d7']/1e9:+,.2f}B ({d7pct:+.2f}%) via DefiLlama", sig))
        else:
            out.append(inst_item("Stablecoin supply", "unavailable", "DefiLlama public feed failed", "neutral", "unavailable"))

    if sid == "gold":
        out.append(inst_item("Macro confirmation", "USD + liquidity", "Gold confirmation currently comes from DXY, liquidity proxy and COMEX futures; ETF holdings layer comes next", "neutral", "mixed"))

    if sid == "local":
        out.append(inst_item("Cross-border layer", "pending", "BOT/SET foreign-flow series will be the next local institutional source", "neutral", "pending"))

    return out

def load_previous_history():
    url = "https://kickmos.github.io/my-world/data/history.json"
    try:
        data = http_json(url, 8)
        return data if isinstance(data, list) else []
    except Exception:
        return []

def main():
    markets = {}
    for key, symbol in SYMBOLS.items():
        markets[key] = safe_fetch(symbol)
        time.sleep(0.10)

    fred = {key: safe_fred(series) for key, series in FRED_SERIES.items()}
    stable = safe_stablecoins()
    tff_rows = safe_socrata(CFTC_DATASETS["tff_futures"], 800)
    legacy_rows = safe_socrata(CFTC_DATASETS["legacy_futures"], 800)
    futpos = futures_positioning(markets, tff_rows, legacy_rows)
    news_by_station = {}
    for sid, query in NEWS_QUERIES.items():
        news_by_station[sid] = safe_news(query, 8)
        time.sleep(0.12)
    ctx = institutional_context(fred, stable)

    ids = [x[0] for x in BASE_STATIONS]
    scores = {k: score_market(markets[k]) for k in ids}
    scores["local"] = -scores["local"]
    confirms = confirmation_adjustments(ctx)

    risk_score = int(clamp(
        50 + scores["stocks"]*.20 + scores["global"]*.11 + scores["crypto"]*.07
        - scores["usd"]*.08 + ctx["risk_confirmation"]*.35, 0, 100))
    liquidity_score = int(clamp(
        50 + scores["mmf"]*.10 - scores["usd"]*.06
        + (ctx["risk_confirmation"] * .30), 0, 100))

    regime = "Risk-on" if risk_score >= 62 else "Risk-off" if risk_score <= 38 else "Transition"

    labels = {sid:name for sid,name,_,_ in BASE_STATIONS}
    stations, route_candidates = [], []

    for sid, name, short, desc in BASE_STATIONS:
        m, s = markets[sid], scores[sid]
        state, flow = state_from_score(s)
        probs = route_probabilities(sid, scores, confirms)
        nxt = []
        for target, prob in probs:
            nxt.append({"target":target,"label":labels[target],"probability":prob,"type":"inferred"})
            route_candidates.append((prob, name, labels[target]))

        evidence = [
            [f"{m.get('symbol')} market proxy", "Observed", f"Price {fmt_num(m.get('price'))} | 1D {m.get('r1',0):+.2f}% | 5D {m.get('r5',0):+.2f}%"],
            ["Flow interpretation", "Mixed", "Momentum + relative strength + volume proxy; not transaction-level fund flow"],
        ]
        institutional = station_institutionals(sid, fred, stable, ctx)

        futures = []
        def fut_item(label, key):
            d = futpos.get(key, {})
            cot = d.get("cot") or {}
            p = d.get("positioning") or {"label":"unavailable","bias":"neutral","explanation":""}
            return {
                "name": label,
                "signal": p.get("bias","neutral"),
                "note": p.get("explanation",""),
                "positioning": p.get("label","unavailable"),
                "price": d.get("price"),
                "priceChange1D": d.get("priceChange1D"),
                "priceChange5D": d.get("priceChange5D"),
                "priceChangeCotWeek": d.get("priceChangeCotWeek"),
                "volume": d.get("volume"),
                "avgVolume5D": d.get("avgVolume5D"),
                "volumeRatio": d.get("volumeRatio"),
                "openInterest": cot.get("openInterest"),
                "deltaOI": cot.get("deltaOI"),
                "reportDate": cot.get("reportDate"),
                "assetManager": cot.get("assetManager"),
                "leveragedFunds": cot.get("leveragedFunds"),
                "nonCommercial": cot.get("nonCommercial"),
                "horizon": d.get("horizon"),
                "source": d.get("source"),
            }

        if sid == "usd":
            futures = [fut_item("U.S. Dollar Index futures", "dxy")]
        elif sid == "bonds":
            futures = [fut_item("10Y Treasury futures (ZN)", "zn")]
        elif sid == "gold":
            futures = [fut_item("COMEX Gold (GC)", "gc")]
        elif sid == "stocks":
            futures = [fut_item("Nasdaq-100 futures (NQ)", "nq"), fut_item("S&P 500 futures (ES)", "es")]
        elif sid == "crypto":
            futures = [fut_item("CME Bitcoin futures", "btcf")]
        else:
            futures = [{"name":"Derivatives confirmation","signal":"neutral","positioning":"unavailable","note":"No robust free futures positioning contract mapped for this station yet"}]

        stations.append({
            "id":sid,"name":name,"short":short,"state":state,"flow":flow,
            "velocity":velocity_from(m),"confidence":confidence_from(m,institutional),"crowding":crowding_from(m),
            "desc":desc,"evidence":evidence,"institutional":institutional,"next":nxt,"futures":futures,
            "news":news_by_station.get(sid, []),
            "market":{"symbol":m.get("symbol"),"price":m.get("price"),"r1":round(m.get("r1",0),3),"r5":round(m.get("r5",0),3),"score":round(s,1)},
            "confirmationScore":round(confirms.get(sid,0),1)
        })

    route_candidates.sort(reverse=True)
    top_routes = [{"from":frm,"to":to,"score":int(clamp(prob,0,100)),"type":"inferred"} for prob,frm,to in route_candidates[:3]]
    dominant = f"{top_routes[0]['from']} → {top_routes[0]['to']}" if top_routes else "n/a"

    now = datetime.now(timezone.utc)
    snapshot = {
        "updated":now.strftime("%Y-%m-%d %H:%M UTC"),
        "generatedAt":now.isoformat(),
        "mode":"live-free-proxy-v3",
        "regime":regime,"riskScore":risk_score,"liquidityScore":liquidity_score,
        "dominantRoute":dominant,"stations":stations,"routes":top_routes,
        "macro":{
            "riskConfirmation":round(ctx["risk_confirmation"],1),
            "stablecoinLiquidity":round(ctx["crypto_liquidity"],1),
            "fred":fred,
            "stablecoins":stable
        },
        "methodology":{
            "flow":"Market-flow proxy from price momentum, relative strength and volume participation.",
            "institutional":"Public macro/liquidity confirmation layer from FRED plus stablecoin supply; not prime-broker or custodian flow.",
            "routes":"Inferred probabilities using market attraction + confirmation scores; not observed transaction paths.",
            "futures":"Daily futures price/volume proxies plus weekly CFTC futures-only open interest and trader positioning. Positioning labels align price to the CFTC report week where history is available; they are interpretive, not transaction-level proof.",
            "news":"Per-station headlines aggregated from Google News RSS and ranked by recency plus recognized financial-news sources.",
            "cadence":"GitHub Actions target cadence: approximately hourly; scheduled runs are best-effort and may be delayed on the free service."
        }
    }

    with open("snapshot.json","w",encoding="utf-8") as f:
        json.dump(snapshot,f,ensure_ascii=False,indent=2)
    with open("snapshot.js","w",encoding="utf-8") as f:
        f.write("window.LIVE_SNAPSHOT = ")
        json.dump(snapshot,f,ensure_ascii=False,separators=(",",":"))
        f.write(";\n")

    history = load_previous_history()
    point = {
        "t":snapshot["generatedAt"],"risk":risk_score,"liquidity":liquidity_score,
        "regime":regime,
        "scores":{s["id"]:s["market"]["score"] for s in stations}
    }
    if not history or history[-1].get("t") != point["t"]:
        history.append(point)
    history = history[-336:]  # ~7 days at 30-min target cadence
    import os
    os.makedirs("data",exist_ok=True)
    with open("data/history.json","w",encoding="utf-8") as f:
        json.dump(history,f,ensure_ascii=False,separators=(",",":"))

    print(json.dumps({
        "updated":snapshot["updated"],"regime":regime,"riskScore":risk_score,
        "dominantRoute":dominant,"historyPoints":len(history),
        "fredAvailable":sum(1 for v in fred.values() if not v.get("error")),
        "stablecoinsAvailable":not stable.get("error"),
        "newsItems":sum(len(v) for v in news_by_station.values()),
        "cftcTffRows":len(tff_rows),"cftcLegacyRows":len(legacy_rows)
    },ensure_ascii=False))

if __name__ == "__main__":
    main()
