#!/usr/bin/env python3
import json
import math
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

UA = {"User-Agent": "Mozilla/5.0 capital-flow-monitor/1.0"}

SYMBOLS = {
    "local": "THB=X",          # USD/THB proxy
    "usd": "UUP",             # broad USD ETF proxy
    "mmf": "BIL",             # 1-3m Treasury ETF / cash parking proxy
    "bonds": "TLT",           # duration proxy
    "gold": "GLD",            # gold ETF proxy
    "crypto": "BTC-USD",
    "stocks": "QQQ",          # US growth/equity proxy
    "global": "ACWI",         # global equity proxy
    "dxy": "DX-Y.NYB",
    "nq": "NQ=F",
    "es": "ES=F",
    "zn": "ZN=F",
    "gc": "GC=F",
    "btcf": "BTC=F",
}

BASE_STATIONS = [
    ("local", "Local FX", "FX", "Domestic FX and local-asset pressure. THB is used as the first local-currency proxy."),
    ("usd", "USD Cash", "USD", "Global dollar funding and cash reservoir. UUP/DXY are market proxies, not direct cash-flow measurements."),
    ("mmf", "MMF / T-Bills", "CASH", "Cash-parking station. BIL is used as a fast market proxy; true MMF flow data updates more slowly."),
    ("bonds", "Bonds / Credit", "BONDS", "Duration and credit complex. TLT is the first fast proxy; credit-spread data will be layered in later."),
    ("gold", "Gold", "GOLD", "Monetary hedge / safe-haven station using GLD plus COMEX gold futures confirmation."),
    ("crypto", "Crypto", "BTC", "Digital-asset risk station using BTC spot first; stablecoin and on-chain flow layers will be added separately."),
    ("stocks", "US Stocks", "EQUITY", "US equity risk station using QQQ first; sector and single-name expansion comes next."),
    ("global", "Global Risk", "GLOBAL", "Global equity risk outside the US, represented initially by ACWI."),
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


def fetch_yahoo(symbol):
    q = urllib.parse.quote(symbol, safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{q}?range=1mo&interval=1d&includePrePost=false"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=12) as r:
        data = json.loads(r.read().decode("utf-8"))
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
        "symbol": symbol,
        "price": p,
        "r1": r1,
        "r5": r5,
        "volume_ratio": vr,
        "market_time": meta.get("regularMarketTime"),
        "currency": meta.get("currency"),
        "source": "Yahoo Finance chart endpoint",
    }


def safe_fetch(symbol):
    try:
        return fetch_yahoo(symbol)
    except Exception as e:
        return {"symbol": symbol, "error": str(e), "r1": 0.0, "r5": 0.0, "volume_ratio": 1.0, "source": "unavailable"}


def score_market(m):
    if m.get("error"):
        return 0.0
    # Momentum + participation proxy. This is deliberately NOT labelled observed fund flow.
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
    r1, r5 = m["r1"], m["r5"] / 5
    accel = r1 - r5
    if accel > 1.0:
        return "↑↑"
    if accel > 0.25:
        return "↑"
    if accel < -1.0:
        return "↓↓"
    if accel < -0.25:
        return "↓"
    return "→"


def confidence_from(m):
    if m.get("error"):
        return 35
    c = 70
    if abs(m.get("r1", 0)) > 0.25:
        c += 5
    if abs(m.get("r5", 0)) > 0.8:
        c += 5
    vr = m.get("volume_ratio", 1)
    if vr > 1.1:
        c += 5
    return int(clamp(c, 55, 88))


def crowding_from(m):
    if m.get("error"):
        return 40
    return int(clamp(38 + abs(m.get("r5", 0)) * 5 + max(0, m.get("volume_ratio", 1)-1) * 12, 20, 92))


def future_signal(m):
    s = score_market(m)
    if s > 9:
        return "positive"
    if s < -9:
        return "negative"
    return "neutral"


def route_probabilities(source_id, scores):
    raw = []
    for target, weight in ROUTE_GRAPH[source_id]:
        # destination attractiveness + structural prior; keep every branch visible
        attraction = clamp(50 + scores.get(target, 0) * 0.45 - scores.get(source_id, 0) * 0.10, 8, 92)
        raw.append((target, max(1.0, weight * attraction)))
    total = sum(v for _, v in raw) or 1
    vals = [(t, int(round(v / total * 100))) for t, v in raw]
    # keep total exactly 100 after rounding
    diff = 100 - sum(v for _, v in vals)
    if vals:
        vals[0] = (vals[0][0], vals[0][1] + diff)
    return vals


def fmt_num(v):
    if v is None:
        return "n/a"
    if abs(v) >= 1000:
        return f"{v:,.0f}"
    if abs(v) >= 100:
        return f"{v:,.1f}"
    return f"{v:,.2f}"


def main():
    markets = {}
    for key, symbol in SYMBOLS.items():
        markets[key] = safe_fetch(symbol)
        time.sleep(0.15)

    scores = {k: score_market(markets[k]) for k in [x[0] for x in BASE_STATIONS]}

    # USD/THB rises = THB weak / local FX pressure, so invert for local-risk interpretation.
    scores["local"] = -scores["local"]

    risk_score = int(clamp(50 + scores["stocks"] * .22 + scores["global"] * .12 + scores["crypto"] * .08 - scores["usd"] * .10, 0, 100))
    liquidity_score = int(clamp(50 + scores["mmf"] * .18 - scores["usd"] * .08 + (100-risk_score) * .08, 0, 100))
    if risk_score >= 62:
        regime = "Risk-on"
    elif risk_score <= 38:
        regime = "Risk-off"
    else:
        regime = "Transition"

    labels = {sid:name for sid,name,_,_ in BASE_STATIONS}
    stations = []
    route_candidates = []

    for sid, name, short, desc in BASE_STATIONS:
        m = markets[sid]
        s = scores[sid]
        state, flow = state_from_score(s)
        probs = route_probabilities(sid, scores)
        nxt = []
        for target, prob in probs:
            nxt.append({"target":target,"label":labels[target],"probability":prob,"type":"inferred"})
            route_candidates.append((prob, name, labels[target]))

        evidence = [
            [f"{m.get('symbol')} market proxy", "Observed", f"Price {fmt_num(m.get('price'))} | 1D {m.get('r1',0):+.2f}% | 5D {m.get('r5',0):+.2f}%"],
            ["Flow interpretation", "Mixed", "Momentum + relative strength + volume proxy; not transaction-level fund flow"],
        ]

        futures = []
        if sid == "usd":
            futures = [
                {"name":"DXY", "signal":future_signal(markets["dxy"]), "note":f"1D {markets['dxy'].get('r1',0):+.2f}% | free market proxy"},
            ]
        elif sid == "bonds":
            futures = [
                {"name":"10Y Treasury futures (ZN)", "signal":future_signal(markets["zn"]), "note":f"1D {markets['zn'].get('r1',0):+.2f}% | delayed/free feed"},
            ]
        elif sid == "gold":
            futures = [
                {"name":"COMEX Gold (GC)", "signal":future_signal(markets["gc"]), "note":f"1D {markets['gc'].get('r1',0):+.2f}% | delayed/free feed"},
            ]
        elif sid == "stocks":
            futures = [
                {"name":"NQ futures", "signal":future_signal(markets["nq"]), "note":f"1D {markets['nq'].get('r1',0):+.2f}% | Nasdaq confirmation"},
                {"name":"ES futures", "signal":future_signal(markets["es"]), "note":f"1D {markets['es'].get('r1',0):+.2f}% | S&P confirmation"},
            ]
        elif sid == "crypto":
            futures = [
                {"name":"CME BTC futures", "signal":future_signal(markets["btcf"]), "note":("free delayed proxy" if not markets["btcf"].get("error") else "free feed unavailable; spot BTC remains primary")},
            ]
        else:
            futures = [{"name":"Derivatives confirmation", "signal":"neutral", "note":"No robust free futures feed wired for this station yet"}]

        stations.append({
            "id":sid,"name":name,"short":short,"state":state,"flow":flow,
            "velocity":velocity_from(m),"confidence":confidence_from(m),"crowding":crowding_from(m),
            "desc":desc,"evidence":evidence,"next":nxt,"futures":futures,
            "market":{"symbol":m.get("symbol"),"price":m.get("price"),"r1":round(m.get("r1",0),3),"r5":round(m.get("r5",0),3),"score":round(s,1)}
        })

    route_candidates.sort(reverse=True)
    top_routes = [
        {"from":frm,"to":to,"score":int(clamp(prob,0,100)),"type":"inferred"}
        for prob, frm, to in route_candidates[:3]
    ]
    dominant = f"{top_routes[0]['from']} → {top_routes[0]['to']}" if top_routes else "n/a"

    now = datetime.now(timezone.utc)
    snapshot = {
        "updated": now.strftime("%Y-%m-%d %H:%M UTC"),
        "generatedAt": now.isoformat(),
        "mode":"live-free-proxy",
        "regime":regime,
        "riskScore":risk_score,
        "liquidityScore":liquidity_score,
        "dominantRoute":dominant,
        "stations":stations,
        "routes":top_routes,
        "methodology":{
            "flow":"Market-flow proxy from price momentum, relative strength and volume participation.",
            "routes":"Inferred probabilities; not observed transaction paths.",
            "futures":"Free/delayed public market proxies where available.",
            "cadence":"GitHub Actions target cadence: every 30 minutes; actual scheduled runs may be delayed."
        }
    }

    with open("snapshot.json","w",encoding="utf-8") as f:
        json.dump(snapshot,f,ensure_ascii=False,indent=2)
    with open("snapshot.js","w",encoding="utf-8") as f:
        f.write("window.LIVE_SNAPSHOT = ")
        json.dump(snapshot,f,ensure_ascii=False,separators=(",",":"))
        f.write(";\n")
    print(json.dumps({"updated":snapshot["updated"],"regime":regime,"riskScore":risk_score,"dominantRoute":dominant},ensure_ascii=False))

if __name__ == "__main__":
    main()
