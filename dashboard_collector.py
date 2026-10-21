#!/usr/bin/env python3
import json, re, os, html as htmlmod, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor

UA={"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
GEMINI_API_KEY=os.environ.get("GEMINI_API_KEY","")
GEMINI_MODEL="gemini-2.5-flash-lite"
OG_CACHE={}

POSITIVE_WORDS=[
 "beat","beats","surge","surges","rally","rallies","gain","gains","upgrade","upgrades",
 "record high","approval","approved","partnership","deal","contract","expands","expansion",
 "growth","strong demand","raises guidance","profit rises","revenue rises","wins","breakthrough",
 "investment","invests","launch success","cuts prices","eases","ceasefire",
 "revenue up","revenue rises","profit up","profit rises","sales up","orders up","raises target","raises forecast","outperforms"
]
NEGATIVE_WORDS=[
 "miss","misses","plunge","plunges","drop","drops","downgrade","downgrades","lawsuit",
 "tariff","war","attack","strikes","layoff","layoffs","cuts jobs","weak guidance","delay",
 "delays","crackdown","ban","bans","investigation","probe","fraud","loss widens","default",
 "inflation rises","hot inflation","higher inflation","sanctions","escalation","slump","falls",
 "mass shooting","shooting plot","arrest","arrests","killed","death","deaths","crash","collapse","warning","recall"
]
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


CORPORATE_EVENT_QUERIES=[
 {"query":"(stock offering OR secondary offering OR public offering OR registered direct offering) when:3d","type":"OFFERING","risk":"HIGH"},
 {"query":"(stock dilution OR dilutive offering OR ATM offering OR shelf registration) when:3d","type":"DILUTION","risk":"HIGH"},
 {"query":"(warrant exercise OR warrants issued OR warrant agreement) stock when:5d","type":"WARRANT","risk":"HIGH"},
 {"query":"(reverse stock split OR stock split) when:5d","type":"SPLIT","risk":"MEDIUM"},
 {"query":"(capital raise OR raises capital OR share issuance OR new shares) company when:3d","type":"CAPITAL RAISE","risk":"HIGH"},
]

EVENT_TYPE_LABELS={
 "EARNINGS":"ผลประกอบการ",
 "XD":"ขึ้น XD / Ex-Dividend",
 "OFFERING":"เสนอขายหุ้น / Offering",
 "DILUTION":"Dilution / ATM / Shelf",
 "WARRANT":"Warrant",
 "SPLIT":"Split / Reverse Split",
 "CAPITAL RAISE":"เพิ่มทุน / ออกหุ้นใหม่",
 "OTHER":"Corporate Action",
}

def get_bytes(url,timeout=15):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=timeout) as r:return r.read()

def clean(s):
    s=htmlmod.unescape(s or "")
    s=re.sub(r"<[^>]+>"," ",s)
    s=s.replace("\xa0"," ")
    return re.sub(r"\s+"," ",s).strip()

def headline_sentiment(title, summary=""):
    text=(title+" "+summary).lower()
    pos=sum(1 for w in POSITIVE_WORDS if w in text)
    neg=sum(1 for w in NEGATIVE_WORDS if w in text)
    if pos>=2 and pos>neg:return "positive"
    if neg>=2 and neg>pos:return "negative"
    if pos==1 and neg==0:return "positive"
    if neg==1 and pos==0:return "negative"
    return "neutral"

def short_summary(title, summary=""):
    title_clean=clean(title)
    text=clean(summary)
    if text:
        text=re.sub(r"^[^:]{0,45}:\s*","",text)
        # strip publisher suffixes commonly repeated by Google News descriptions
        text=re.sub(r"\s+(Reuters|Bloomberg|CNBC|WSJ|Yahoo Finance|Breakingthenews\.net)\s*$","",text,flags=re.I)
        parts=re.split(r"(?<=[.!?])\s+",text)
        out=" ".join(parts[:2]).strip()
        if len(out)>190:out=out[:187].rsplit(" ",1)[0]+"..."
        norm=lambda x:re.sub(r"\W+","",x.lower())
        if out and norm(out)!=norm(title_clean) and norm(title_clean) not in norm(out):
            return out
    return "สรุป: "+title_clean

def extract_rss_image(item):
    for child in list(item):
        tag=child.tag.lower()
        if tag.endswith("thumbnail") or tag.endswith("content") or tag.endswith("enclosure"):
            url=child.attrib.get("url") or child.attrib.get("href")
            typ=(child.attrib.get("type") or "").lower()
            medium=(child.attrib.get("medium") or "").lower()
            if url and ("image" in typ or medium=="image" or tag.endswith("thumbnail")):
                return url
    desc=item.findtext("description") or ""
    m=re.search(r'<img[^>]+src=["\']([^"\']+)["\']',desc,re.I)
    return htmlmod.unescape(m.group(1)) if m else None

def fetch_og_image(url, timeout=8):
    if not url:return None
    if url in OG_CACHE:return OG_CACHE[url]
    try:
        raw=get_bytes(url,timeout).decode("utf-8","ignore")[:120000]
        pats=[
          r'<meta[^>]+property=["\']og:image(?::url)?["\'][^>]+content=["\']([^"\']+)["\']',
          r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image(?::url)?["\']',
          r'<meta[^>]+name=["\']twitter:image(?::src)?["\'][^>]+content=["\']([^"\']+)["\']',
          r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image(?::src)?["\']',
        ]
        for p in pats:
            m=re.search(p,raw,re.I)
            if m:
                image=htmlmod.unescape(m.group(1)).strip()
                if image.startswith("//"):image="https:"+image
                if image.startswith("http"):
                    OG_CACHE[url]=image;return image
    except Exception:pass
    OG_CACHE[url]=None
    return None

def fallback_image(category):
    return {
      "markets":"https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1000&q=70",
      "politics":"https://images.unsplash.com/photo-1529107386315-e1a2ed48a620?auto=format&fit=crop&w=1000&q=70",
      "world":"https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1000&q=70",
      "tech_ai":"https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1000&q=70",
      "concert":"https://images.unsplash.com/photo-1501386761578-eac5c94b800a?auto=format&fit=crop&w=1000&q=70",
      "travel":"https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1000&q=70",
    }.get(category,"https://images.unsplash.com/photo-1495020689067-958852a7765e?auto=format&fit=crop&w=1000&q=70")

def enrich_item_image(item, category, url_key="url"):
    if item.get("imageUrl"):return item
    url=item.get(url_key) or item.get("bookingUrl") or item.get("url")
    item["imageUrl"]=fetch_og_image(url,6) or fallback_image(category)
    return item

def enrich_images_parallel(items, category, max_workers=8):
    if not items:return items
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        list(ex.map(lambda x: enrich_item_image(x,category),items))
    return items

def gemini_refine(items):
    if not GEMINI_API_KEY or not items:return items
    slim=[{"id":i,"title":x.get("title",""),"summary":x.get("summary","")} for i,x in enumerate(items)]
    prompt="""คุณเป็น editor ข่าวธุรกิจภาษาไทย ประเมิน tone ของข่าวทั่วไป ไม่ใช่ผลต่อสินทรัพย์เฉพาะตัว
สำหรับแต่ละข่าว:
- sentiment ต้องเป็น positive, negative หรือ neutral
- summary_th สรุปข้อเท็จจริง 1 ประโยคสั้น ไม่เกิน 150 ตัวอักษร
- ห้ามเพิ่มข้อมูลที่ไม่มีใน title/summary
ตอบ JSON array เท่านั้น รูปแบบ [{\"id\":0,\"sentiment\":\"neutral\",\"summary_th\":\"...\"}]
INPUT:
"""+json.dumps(slim,ensure_ascii=False)
    try:
        url=f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key="+urllib.parse.quote(GEMINI_API_KEY)
        body=json.dumps({"contents":[{"parts":[{"text":prompt}]}],"generationConfig":{"temperature":0.1,"responseMimeType":"application/json"}}).encode()
        req=urllib.request.Request(url,data=body,headers={**UA,"Content-Type":"application/json"})
        with urllib.request.urlopen(req,timeout=30) as r:data=json.loads(r.read().decode())
        text=data["candidates"][0]["content"]["parts"][0]["text"]
        parsed=json.loads(text)
        by_id={int(x["id"]):x for x in parsed if isinstance(x,dict) and "id" in x}
        for i,item in enumerate(items):
            v=by_id.get(i,{})
            if v.get("sentiment") in ("positive","negative","neutral"):item["sentiment"]=v["sentiment"]
            if v.get("summary_th"):item["summaryShort"]=clean(v["summary_th"])[:180]
    except Exception as e:
        print("Gemini dashboard refine fallback:",str(e)[:160])
    return items

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
        img=extract_rss_image(item)
        out.append({"title":title,"url":link,"source":source,"publishedAt":dt.isoformat() if dt else None,"summary":desc[:400],"imageUrl":img})
    if not out:
        ns={"a":"http://www.w3.org/2005/Atom"}
        for item in root.findall(".//a:entry",ns):
            title=clean(item.findtext("a:title",default="",namespaces=ns))
            link_node=item.find("a:link",ns);link=link_node.attrib.get("href","") if link_node is not None else ""
            pub=clean(item.findtext("a:updated",default="",namespaces=ns) or item.findtext("a:published",default="",namespaces=ns))
            dt=parse_date(pub)
            if title and link:out.append({"title":title,"url":link,"source":source,"publishedAt":dt.isoformat() if dt else None,"summary":"","imageUrl":None})
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
                x["sentiment"]=headline_sentiment(x["title"],x.get("summary",""))
                x["summaryShort"]=short_summary(x["title"],x.get("summary",""))
                arr.append(x)
        arr.sort(key=lambda x:(x.get("breaking",False),x.get("vip",False),x.get("publishedAt") or ""),reverse=True)
        visible=arr[:10]
        enrich_images_parallel(visible,cat,8)
        buckets[cat]=visible
    pool=[x for v in buckets.values() for x in v]
    unique=[];seen_ids=set()
    for x in pool:
        key=x.get("url") or x.get("title")
        if key in seen_ids:continue
        seen_ids.add(key);unique.append(x)
    gemini_refine(unique[:32])
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
    today=datetime.now(BKK).date();out=[]
    for raw in LIFE_EVENTS:
        if datetime.fromisoformat(raw["date"]).date()<today:continue
        x=dict(raw);x["imageUrl"]=None;out.append(x)
    enrich_images_parallel(out,"concert",6)
    return out

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
        seen.add(key);x["imageUrl"]=None;out.append(x)
    selected=out[:18]
    enrich_images_parallel(selected,"travel",8)
    return selected


def nasdaq_json(path, timeout=15):
    url="https://api.nasdaq.com"+path
    headers={
      **UA,
      "Accept":"application/json, text/plain, */*",
      "Accept-Language":"en-US,en;q=0.9",
      "Origin":"https://www.nasdaq.com",
      "Referer":"https://www.nasdaq.com/",
    }
    req=urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def parse_market_cap(text):
    if text in (None,"","N/A"):return 0
    s=str(text).replace("$","").replace(",","").strip().upper()
    m=re.match(r"([0-9.]+)\s*([KMBT]?)",s)
    if not m:return 0
    n=float(m.group(1));mult={"":1,"K":1e3,"M":1e6,"B":1e9,"T":1e12}.get(m.group(2),1)
    return n*mult

def normalize_event_date(text):
    if not text:return None
    for fmt in ("%m/%d/%Y","%Y-%m-%d","%b %d, %Y","%B %d, %Y"):
        try:return datetime.strptime(str(text).strip(),fmt).date().isoformat()
        except Exception:pass
    return None

def fetch_nasdaq_earnings(days=21):
    today=datetime.now(BKK).date();out=[]
    for offset in range(days):
        d=today+timedelta(days=offset)
        try:
            data=nasdaq_json("/api/calendar/earnings?date="+d.isoformat(),12)
            rows=((data.get("data") or {}).get("rows") or [])
        except Exception:
            rows=[]
        for row in rows:
            symbol=clean(row.get("symbol") or "")
            name=clean(row.get("name") or row.get("companyName") or "")
            if not symbol or not name:continue
            time_label=clean(row.get("time") or row.get("timeOfDay") or "")
            eps=clean(row.get("epsForecast") or "")
            fiscal=clean(row.get("fiscalQuarterEnding") or "")
            cap=clean(row.get("marketCap") or "")
            status="confirmed" if time_label and "not" not in time_label.lower() and "unsupplied" not in time_label.lower() else "estimated"
            out.append({
              "symbol":symbol,"company":name,"eventType":"EARNINGS","eventLabel":EVENT_TYPE_LABELS["EARNINGS"],
              "date":d.isoformat(),"status":status,"timeMarket":time_label or "TBA",
              "risk":"MEDIUM","source":"Nasdaq Earnings Calendar",
              "url":"https://www.nasdaq.com/market-activity/earnings",
              "detail":("EPS forecast "+eps if eps else "Earnings release")+((" · "+fiscal) if fiscal else ""),
              "marketCap":cap,"marketCapValue":parse_market_cap(cap),
              "discovery":True,
            })
    return out

def fetch_nasdaq_dividends(days=35):
    today=datetime.now(BKK).date();out=[]
    for offset in range(days):
        d=today+timedelta(days=offset)
        try:
            data=nasdaq_json("/api/calendar/dividends?date="+d.isoformat(),12)
            rows=((data.get("data") or {}).get("calendar") or {}).get("rows") or ((data.get("data") or {}).get("rows") or [])
        except Exception:
            rows=[]
        for row in rows:
            symbol=clean(row.get("symbol") or "")
            name=clean(row.get("companyName") or row.get("name") or "")
            exdate=normalize_event_date(row.get("dividend_Ex_Date") or row.get("exOrEffDate") or row.get("exDate")) or d.isoformat()
            if not symbol:continue
            amount=clean(row.get("amount") or row.get("cashAmount") or "")
            out.append({
              "symbol":symbol,"company":name or symbol,"eventType":"XD","eventLabel":EVENT_TYPE_LABELS["XD"],
              "date":exdate,"status":"confirmed","timeMarket":"Market date",
              "risk":"LOW","source":"Nasdaq Dividend Calendar",
              "url":"https://www.nasdaq.com/market-activity/dividends",
              "detail":("Dividend "+amount if amount else "Ex-dividend date"),
              "marketCap":"","marketCapValue":0,"discovery":True,
            })
    return out

def infer_ticker(title):
    patterns=[
      r"\$([A-Z]{1,5})(?:\b|$)",
      r"\((?:NASDAQ|NYSE|AMEX|OTC)[:\s]+([A-Z]{1,5})\)",
      r"\bNASDAQ[:\s]+([A-Z]{1,5})\b",
      r"\bNYSE[:\s]+([A-Z]{1,5})\b",
    ]
    for p in patterns:
        m=re.search(p,title or "")
        if m:return m.group(1)
    return ""

def collect_corporate_action_news():
    out=[];seen=set()
    for spec in CORPORATE_EVENT_QUERIES:
        for x in google_news(spec["query"],"Corporate Action",10):
            title=x.get("title","");key=re.sub(r"\W+","",title.lower())[:120]
            if key in seen:continue
            seen.add(key)
            symbol=infer_ticker(title)
            dt=parse_date(x.get("publishedAt"))
            event_date=(dt.astimezone(BKK).date().isoformat() if dt else datetime.now(BKK).date().isoformat())
            lower=(title+" "+x.get("summary","")).lower()
            event_type=spec["type"]
            if "warrant" in lower:event_type="WARRANT"
            elif "reverse split" in lower or "stock split" in lower:event_type="SPLIT"
            elif "atm offering" in lower or "shelf registration" in lower or "dilut" in lower:event_type="DILUTION"
            elif "offering" in lower:event_type="OFFERING"
            elif "capital raise" in lower or "share issuance" in lower or "new shares" in lower:event_type="CAPITAL RAISE"
            out.append({
              "symbol":symbol or "—","company":title,"eventType":event_type,"eventLabel":EVENT_TYPE_LABELS.get(event_type,event_type),
              "date":event_date,"status":"confirmed","timeMarket":"News / filing signal",
              "risk":"HIGH" if event_type in ("OFFERING","DILUTION","WARRANT","CAPITAL RAISE") else spec["risk"],
              "source":x.get("source") or "News signal","url":x.get("url"),"detail":short_summary(title,x.get("summary","")),
              "marketCap":"","marketCapValue":0,"discovery":True,"publishedAt":x.get("publishedAt")
            })
    return out

def corporate_events():
    events=[]
    events.extend(fetch_nasdaq_earnings(18))
    events.extend(fetch_nasdaq_dividends(24))
    events.extend(collect_corporate_action_news())

    # Discovery ranking: imminent events, large companies, and high-risk corporate actions rise to the top.
    today=datetime.now(BKK).date()
    risk_score={"HIGH":80,"MEDIUM":45,"LOW":15}
    for e in events:
        try:days=(datetime.fromisoformat(e["date"]).date()-today).days
        except Exception:days=99
        proximity=max(0,40-min(abs(days),20)*2)
        cap=e.get("marketCapValue",0) or 0
        cap_score=35 if cap>=2e11 else 28 if cap>=5e10 else 20 if cap>=1e10 else 8 if cap>=1e9 else 0
        confirmed=12 if e.get("status")=="confirmed" else 4
        e["attentionScore"]=min(100,risk_score.get(e.get("risk"),20)+proximity+cap_score+confirmed)
        e["dateStatusLabel"]="CONFIRMED" if e.get("status")=="confirmed" else "ESTIMATED"

    # Avoid overwhelming the dashboard with routine dividends; keep high-profile XD names only.
    earnings=sorted([e for e in events if e["eventType"]=="EARNINGS"],key=lambda x:(x["date"],-x["attentionScore"]))[:55]
    actions=sorted([e for e in events if e["eventType"] not in ("EARNINGS","XD")],key=lambda x:(-x["attentionScore"],x["date"]))[:30]
    dividends=sorted([e for e in events if e["eventType"]=="XD"],key=lambda x:(-x.get("marketCapValue",0),x["date"]))[:15]
    merged=earnings+actions+dividends
    merged.sort(key=lambda x:(x["date"],-x["attentionScore"]))
    return merged[:80]

def main():
    data={
      "updated":datetime.now(timezone.utc).isoformat(),
      "news":collect_news(),
      "financeEvents":macro_events(),
      "lifeEvents":life_events(),
      "travelPromos":travel_promos(),
      "corporateEvents":corporate_events(),
      "sources":{
        "news":"LineNofity source pool adapted for dashboard: Reuters/Google News, CNBC, Yahoo Finance, MarketWatch, BBC, AP, TechCrunch, The Verge, Ars.",
        "calendar":"BLS official calendar + Federal Reserve FOMC calendar.",
        "life":"Official organizer/venue links curated for upcoming Bangkok events.",
        "travel":"Provider promo/deal discovery; verify net price and eligibility at checkout.",
        "corporateEvents":"Nasdaq earnings/dividend calendars plus recent public corporate-action news signals. Confirm filings before trading."
      }
    }
    with open("dashboard-data.json","w",encoding="utf-8") as f:json.dump(data,f,ensure_ascii=False,indent=2)
    with open("dashboard-data.js","w",encoding="utf-8") as f:
        f.write("window.DASHBOARD_DATA=");json.dump(data,f,ensure_ascii=False,separators=(",",":"));f.write(";\n")
    print(json.dumps({"dashboardUpdated":data["updated"],"topNews":len(data["news"].get("top",[])),"financeEvents":len(data["financeEvents"]),"lifeEvents":len(data["lifeEvents"]),"travelPromos":len(data["travelPromos"]),"corporateEvents":len(data["corporateEvents"])},ensure_ascii=False))

if __name__=="__main__":main()
