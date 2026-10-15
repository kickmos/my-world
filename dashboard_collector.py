#!/usr/bin/env python3
import json, re, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

UA={"User-Agent":"Mozilla/5.0 MyWorldDashboard/1.0"}
BKK=ZoneInfo("Asia/Bangkok")
NY=ZoneInfo("America/New_York")

NEWS_SOURCES={
  "tech_ai":[
    ("TechCrunch","https://techcrunch.com/feed/"),
    ("The Verge","https://www.theverge.com/rss/index.xml"),
    ("Ars Technica","https://feeds.arstechnica.com/arstechnica/technology-lab"),
    ("Reuters Tech","https://news.google.com/rss/search?q=when:24h+allinurl:reuters.com/technology&hl=en-US&gl=US&ceid=US:en"),
    ("AI Labs","https://news.google.com/rss/search?q=(%22Anthropic%22+OR+%22OpenAI%22+OR+%22DeepMind%22+OR+%22xAI%22+OR+%22Mistral%22)+when:24h&hl=en-US&gl=US&ceid=US:en"),
  ],
  "markets":[
    ("CNBC Markets","https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=15839069"),
    ("Yahoo Finance","https://finance.yahoo.com/news/rssindex"),
    ("MarketWatch","https://feeds.content.dowjones.io/public/rss/mw_topstories"),
    ("Reuters Markets","https://news.google.com/rss/search?q=when:24h+allinurl:reuters.com/markets&hl=en-US&gl=US&ceid=US:en"),
    ("Benzinga","https://www.benzinga.com/feed"),
    ("Growth / AI Infra","https://news.google.com/rss/search?q=(%22AI+infrastructure%22+OR+%22data+center%22+OR+%22semiconductor%22+OR+%22NVIDIA%22+OR+%22TSMC%22+OR+%22Marvell%22)+when:24h&hl=en-US&gl=US&ceid=US:en"),
  ],
  "world":[
    ("BBC World","https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Reuters World","https://news.google.com/rss/search?q=when:24h+allinurl:reuters.com/world&hl=en-US&gl=US&ceid=US:en"),
    ("AP News","https://news.google.com/rss/search?q=when:24h+allinurl:apnews.com&hl=en-US&gl=US&ceid=US:en"),
    ("Al Jazeera","https://www.aljazeera.com/xml/rss/all.xml"),
  ],
  "politics":[
    ("US Politics","https://news.google.com/rss/search?q=(Trump+OR+White+House+OR+Congress)+when:24h&hl=en-US&gl=US&ceid=US:en"),
    ("AP Politics","https://news.google.com/rss/search?q=when:24h+allinurl:apnews.com/hub/politics&hl=en-US&gl=US&ceid=US:en"),
    ("BBC US","https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml"),
  ]
}
VIP_KEYWORDS=[
 "nvidia","nvda","tsmc","taiwan semiconductor","tsm","broadcom","avgo","marvell","mrvl",
 "openai","anthropic","microsoft","amazon","google","oracle","meta","bitcoin","btc","gold",
 "federal reserve","fed rate","inflation","cpi","nonfarm","payroll","nasdaq","s&p 500",
 "trump","white house","tariff","china","taiwan","war","iran","israel","ukraine","russia"
]
BREAKING=["breaking","urgent","alert","just in","developing","exclusive"]

LIFE_EVENTS=[
 {"title":"INTERSTELLAR LIVE","date":"2026-10-28","time":"19:00","venue":"UOB LIVE, EMSPHERE","type":"Live to Film + Orchestra","booking":"Eventpop","url":"https://www.eventpop.me/s/interstellar-live-concert-th","status":"tickets"},
 {"title":"5 Seconds of Summer: EVERYONE’S A STAR! WORLD TOUR","date":"2026-11-09","time":"20:00","venue":"UOB LIVE, EMSPHERE","type":"Concert","booking":"ThaiTicketMajor","url":"https://www.thaiticketmajor.com/concert/5SOS-EVERYONES-A-STAR-WORLD-TOUR.html","status":"tickets"},
 {"title":"LANY: soft world tour Bangkok","date":"2026-11-10","time":"20:00","venue":"UOB LIVE, EMSPHERE","type":"Concert","booking":"ThaiTicketMajor","url":"https://uoblive.asia/th/event/lany-soft-world-tour-bangkok","status":"tickets"},
 {"title":"wave to earth – the pieces tour in Bangkok","date":"2026-11-12","time":"20:00","venue":"UOB LIVE, EMSPHERE","type":"Concert","booking":"Live Nation Tero / official ticket link","url":"https://uoblive.asia/event/wave-to-earth---the-pieces-tour-in-bangkok","status":"tickets"},
 {"title":"Harry Potter and The Goblet of Fire™ in Concert","date":"2026-11-21","time":"TBA","venue":"UOB LIVE, EMSPHERE","type":"Live Film Concert","booking":"UOB LIVE official ticket link","url":"https://uoblive.asia/th/event/harry-potter-and-the-goblet-of-fire-tm-in-concert","status":"tickets"},
 {"title":"FKJ – Tyber Tour","date":"2026-11-27","time":"TBA","venue":"UOB LIVE, EMSPHERE","type":"Concert","booking":"Ticketmaster Thailand","url":"https://uoblive.asia/event/fkj---tyber-tour","status":"tickets"},
 {"title":"Khalid: It's Always Summer Somewhere Tour","date":"2026-11-29","time":"20:00","venue":"UOB LIVE, EMSPHERE","type":"Concert","booking":"Ticketmaster Thailand","url":"https://uoblive.asia/th/event/khalid-its-always-summer-somewhere-tour","status":"tickets"},
 {"title":"Malcolm Todd: Do That Again Tour","date":"2026-12-06","time":"TBA","venue":"UOB LIVE, EMSPHERE","type":"Concert","booking":"Ticketmaster Thailand","url":"https://uoblive.asia/th/event/malcolm-todd-do-that-again-tour","status":"tickets"},
]

TRAVEL_PROVIDERS=[
 {"provider":"Trip.com","query":"site:trip.com (sale OR deals OR promo OR discount) (Thailand OR hotel OR flight) when:7d","bookingUrl":"https://th.trip.com/sale/deals/"},
 {"provider":"Agoda","query":"site:agoda.com (sale OR deals OR promotion OR discount) Thailand hotel when:14d","bookingUrl":"https://www.agoda.com/deals"},
 {"provider":"Traveloka","query":"site:traveloka.com/en-th (promo OR promotion OR deals OR sale) when:14d","bookingUrl":"https://www.traveloka.com/en-th/promotion"},
 {"provider":"Klook","query":"site:klook.com (Thailand OR Bangkok) (promo OR sale OR discount OR deal) when:14d","bookingUrl":"https://www.klook.com/en-TH/coureg/12-thailand-things-to-do/"}
]

FOMC_END_DATES=[
 "2026-10-28","2026-12-09",
 "2027-01-27","2027-03-17","2027-04-28","2027-06-09",
 "2027-07-28","2027-09-15","2027-10-27","2027-12-08"
]

def get_bytes(url,timeout=15):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=timeout) as r:return r.read()

def clean(s):
    s=re.sub(r"<[^>]+>"," ",s or "")
    return re.sub(r"\s+"," ",s).strip()

def parse_date(text):
    if not text:return None
    try:
        dt=parsedate_to_datetime(text)
        if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:return None

def rss_items(url,source,limit=20):
    try:root=ET.fromstring(get_bytes(url))
    except Exception:return []
    out=[]
    for item in root.findall(".//item"):
        title=clean(item.findtext("title"))
        link=clean(item.findtext("link"))
        pub=clean(item.findtext("pubDate") or item.findtext("date"))
        desc=clean(item.findtext("description"))
        if not title or not link:continue
        dt=parse_date(pub)
        out.append({"title":title,"url":link,"source":source,"publishedAt":dt.isoformat() if dt else None,"summary":desc[:260]})
    if not out:
        ns={"a":"http://www.w3.org/2005/Atom"}
        for item in root.findall(".//a:entry",ns):
            title=clean(item.findtext("a:title",default="",namespaces=ns))
            link_node=item.find("a:link",ns);link=link_node.attrib.get("href","") if link_node is not None else ""
            pub=clean(item.findtext("a:updated",default="",namespaces=ns) or item.findtext("a:published",default="",namespaces=ns))
            dt=parse_date(pub)
            if title and link:out.append({"title":title,"url":link,"source":source,"publishedAt":dt.isoformat() if dt else None,"summary":""})
    return out[:limit]

def google_news(query,source,limit=12):
    q=urllib.parse.quote_plus(query)
    return rss_items(f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en",source,limit)

def collect_news():
    now=datetime.now(timezone.utc); cutoff=now-timedelta(hours=36)
    buckets={}
    seen=set()
    for cat,sources in NEWS_SOURCES.items():
        arr=[]
        for source,url in sources:
            for x in rss_items(url,source,16):
                key=re.sub(r"\W+","",x["title"].lower())[:100]
                if key in seen:continue
                dt=parse_date(x["publishedAt"])
                if dt and dt<cutoff:continue
                seen.add(key)
                text=(x["title"]+" "+x.get("summary","")).lower()
                x["breaking"]=any(k in text for k in BREAKING)
                x["vip"]=any(k in text for k in VIP_KEYWORDS)
                x["category"]=cat
                arr.append(x)
        arr.sort(key=lambda x:(x.get("breaking",False),x.get("vip",False),x.get("publishedAt") or ""),reverse=True)
        buckets[cat]=arr[:10]
    pool=[x for v in buckets.values() for x in v]
    pool.sort(key=lambda x:(x.get("breaking",False),x.get("vip",False),x.get("publishedAt") or ""),reverse=True)
    buckets["top"]=pool[:16]
    return buckets

def parse_ics_dt(value,params):
    value=value.strip()
    tz=NY if "America/New_York" in params else timezone.utc
    for fmt in ("%Y%m%dT%H%M%S","%Y%m%dT%H%M","%Y%m%d"):
        try:
            dt=datetime.strptime(value.rstrip("Z"),fmt)
            if value.endswith("Z"):return dt.replace(tzinfo=timezone.utc)
            return dt.replace(tzinfo=tz)
        except Exception:pass
    return None

def bls_events():
    out=[]
    try:
        raw=get_bytes("https://www.bls.gov/schedule/news_release/bls.ics").decode("utf-8","ignore")
        raw=re.sub(r"\r?\n[ \t]","",raw)
        for block in raw.split("BEGIN:VEVENT")[1:]:
            summary=re.search(r"SUMMARY:(.+)",block)
            dtm=re.search(r"DTSTART([^:]*):([^\r\n]+)",block)
            if not summary or not dtm:continue
            title=summary.group(1).strip()
            kind=None
            if "Employment Situation" in title:kind="NONFARM"
            elif "Consumer Price Index" in title:kind="CPI"
            if not kind:continue
            dt=parse_ics_dt(dtm.group(2),dtm.group(1))
            if not dt:continue
            local=dt.astimezone(BKK)
            out.append({"kind":kind,"title":"Nonfarm Payrolls / Employment Situation" if kind=="NONFARM" else "US CPI","impact":"HIGH","date":local.strftime("%Y-%m-%d"),"timeTH":local.strftime("%H:%M"),"iso":local.isoformat(),"source":"BLS","url":"https://www.bls.gov/schedule/news_release/"})
    except Exception:pass
    return out

def fallback_bls():
    rows=[
      ("NONFARM","2026-11-06"),("CPI","2026-11-10"),("NONFARM","2026-12-04"),("CPI","2026-12-10"),
      ("NONFARM","2027-01-08"),("CPI","2027-01-13")
    ]
    out=[]
    for kind,d in rows:
        dt=datetime.fromisoformat(d+"T08:30:00").replace(tzinfo=NY).astimezone(BKK)
        out.append({"kind":kind,"title":"Nonfarm Payrolls / Employment Situation" if kind=="NONFARM" else "US CPI","impact":"HIGH","date":dt.strftime("%Y-%m-%d"),"timeTH":dt.strftime("%H:%M"),"iso":dt.isoformat(),"source":"BLS fallback","url":"https://www.bls.gov/schedule/news_release/"})
    return out

def macro_events():
    now=datetime.now(BKK)
    items=bls_events() or fallback_bls()
    for d in FOMC_END_DATES:
        dt=datetime.fromisoformat(d+"T14:00:00").replace(tzinfo=NY).astimezone(BKK)
        items.append({"kind":"FED","title":"FOMC Rate Decision","impact":"HIGH","date":dt.strftime("%Y-%m-%d"),"timeTH":dt.strftime("%H:%M"),"iso":dt.isoformat(),"source":"Federal Reserve","url":"https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"})
    items=[x for x in items if datetime.fromisoformat(x["iso"])>=now-timedelta(hours=2)]
    items.sort(key=lambda x:x["iso"])
    return items[:12]

def life_events():
    today=datetime.now(BKK).date()
    return [x for x in LIFE_EVENTS if datetime.fromisoformat(x["date"]).date()>=today]

def travel_promos():
    arr=[]
    for p in TRAVEL_PROVIDERS:
        for x in google_news(p["query"],p["provider"],8):
            text=(x["title"]+" "+x.get("summary",""))
            m=re.search(r"(?<!\d)(\d{2,3})\s*%\s*(?:off|OFF|discount)?",text)
            pct=int(m.group(1)) if m else None
            if pct and pct>90:pct=None
            x.update({"provider":p["provider"],"discountPct":pct,"hot":bool(pct and pct>=50),"bookingUrl":p["bookingUrl"]})
            arr.append(x)
    # verified current seeds / official provider pages
    arr.extend([
      {"provider":"Trip.com","title":"GO THAILAND hotels save up to 50% OFF","discountPct":50,"hot":True,"source":"Trip.com Deals","publishedAt":None,"url":"https://th.trip.com/sale/deals/","bookingUrl":"https://th.trip.com/sale/deals/"},
      {"provider":"Traveloka","title":"Thailand hotel deals: selected properties showing 60%+ savings","discountPct":60,"hot":True,"source":"Traveloka Thailand","publishedAt":None,"url":"https://www.traveloka.com/en-th","bookingUrl":"https://www.traveloka.com/en-th"},
    ])
    seen=set();out=[]
    arr.sort(key=lambda x:(x.get("hot",False),x.get("discountPct") or 0,x.get("publishedAt") or ""),reverse=True)
    for x in arr:
        key=(x.get("provider"),re.sub(r"\W+","",x.get("title","").lower())[:80])
        if key in seen:continue
        seen.add(key);out.append(x)
    return out[:18]

def main():
    data={
      "updated":datetime.now(timezone.utc).isoformat(),
      "news":collect_news(),
      "financeEvents":macro_events(),
      "lifeEvents":life_events(),
      "travelPromos":travel_promos(),
      "sources":{
        "news":"LineNofity source pool adapted for dashboard: Reuters/Google News, CNBC, Yahoo Finance, MarketWatch, BBC, AP, TechCrunch, The Verge, Ars.",
        "calendar":"BLS official calendar + Federal Reserve FOMC calendar.",
        "life":"Official organizer/venue links curated for upcoming Bangkok events.",
        "travel":"Provider promo/deal discovery; verify net price and eligibility at checkout."
      }
    }
    with open("dashboard-data.json","w",encoding="utf-8") as f:json.dump(data,f,ensure_ascii=False,indent=2)
    with open("dashboard-data.js","w",encoding="utf-8") as f:
        f.write("window.DASHBOARD_DATA=");json.dump(data,f,ensure_ascii=False,separators=(",",":"));f.write(";\n")
    print(json.dumps({"dashboardUpdated":data["updated"],"topNews":len(data["news"].get("top",[])),"financeEvents":len(data["financeEvents"]),"lifeEvents":len(data["lifeEvents"]),"travelPromos":len(data["travelPromos"])},ensure_ascii=False))

if __name__=="__main__":main()
