#!/usr/bin/env python3
import csv
import io
import json
import math
import time
import urllib.parse
import urllib.request
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
    closes = [x for x in quote.get("close", []) if x is not None]
    volumes = [x for x in quote.get("volume", []) if x is not None]
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
    return {
        "symbol": symbol, "price": p, "r1": r1, "r5": r5,
        "volume_ratio": vr, "market_time": meta.get("regularMarketTime"),
        "currency": meta.get("currency"), "source": "Yahoo Finance chart endpoint",
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
        if sid == "usd":
            futures = [{"name":"DXY","signal":future_signal(markets["dxy"]),"note":f"1D {markets['dxy'].get('r1',0):+.2f}% | free market proxy"}]
        elif sid == "bonds":
            futures = [{"name":"10Y Treasury futures (ZN)","signal":future_signal(markets["zn"]),"note":f"1D {markets['zn'].get('r1',0):+.2f}% | delayed/free feed"}]
        elif sid == "gold":
            futures = [{"name":"COMEX Gold (GC)","signal":future_signal(markets["gc"]),"note":f"1D {markets['gc'].get('r1',0):+.2f}% | delayed/free feed"}]
        elif sid == "stocks":
            futures = [
                {"name":"NQ futures","signal":future_signal(markets["nq"]),"note":f"1D {markets['nq'].get('r1',0):+.2f}% | Nasdaq confirmation"},
                {"name":"ES futures","signal":future_signal(markets["es"]),"note":f"1D {markets['es'].get('r1',0):+.2f}% | S&P confirmation"},
            ]
        elif sid == "crypto":
            futures = [{"name":"CME BTC futures","signal":future_signal(markets["btcf"]),"note":("free delayed proxy" if not markets["btcf"].get("error") else "free futures feed unavailable; spot BTC remains primary")}]
        else:
            futures = [{"name":"Derivatives confirmation","signal":"neutral","note":"No robust free futures feed wired for this station yet"}]

        stations.append({
            "id":sid,"name":name,"short":short,"state":state,"flow":flow,
            "velocity":velocity_from(m),"confidence":confidence_from(m,institutional),"crowding":crowding_from(m),
            "desc":desc,"evidence":evidence,"institutional":institutional,"next":nxt,"futures":futures,
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
        "mode":"live-free-proxy-v2",
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
            "futures":"Free/delayed market proxies where available.",
            "cadence":"GitHub Actions target cadence: minute 07 and 37 each hour; GitHub may delay scheduled runs."
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
        "stablecoinsAvailable":not stable.get("error")
    },ensure_ascii=False))

if __name__ == "__main__":
    main()
