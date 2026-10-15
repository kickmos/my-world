
const widgets=[
{id:"flow",icon:"◎",name:"Global Capital Flow",desc:"ระบบติดตามเส้นทางเงินทุนโลก พร้อมแผนภาพการเคลื่อนย้ายระหว่าง USD, หุ้น, พันธบัตร, Gold และ Crypto",tags:["Liquidity","Route Probability"],url:"./capital-flow.html",label:"เปิด Capital Flow"},
{id:"watchlist",icon:"▥",name:"My Watchlist",desc:"ติดตามหุ้นและสินทรัพย์ที่สนใจ เช่น NVDA, TSM, AVGO, MRVL, ORCL, AMZN, BTC และ XAUUSD โดยไม่แสดงราคาหากยังไม่มีข้อมูลอัปเดต",tags:["Equity","Crypto","Gold"],url:"./notifications.html",label:"ดู Watchlist"},
{id:"calendar",icon:"▦",name:"Economic & Market Calendar",desc:"พื้นที่สำหรับ CPI, PPI, PCE, FOMC, Earnings รวมถึงวันหยุดตลาดหุ้นและ Bank Holidays; อยู่ระหว่างวางระบบปฏิทินจริง",tags:["Economic Events","Market Holidays"],url:"#finance",label:"ไปที่ Finance"},
{id:"alerts",icon:"♧",name:"Alerts & Monitoring",desc:"รายการ ChatGPT Automation ที่ตรวจสอบไว้และ Watchlist ใหม่ แยกสถานะทำงานจริงกับรายการที่ยังไม่ได้ตั้งแจ้งเตือน",tags:["Monitoring","Snapshot"],url:"./notifications.html",label:"เปิด Alerts Center"},
{id:"travel",icon:"✈",name:"Travel Price Watch",desc:"พื้นที่วางแผนบินและโรงแรม พร้อมงบรวมและลิงก์ผู้ให้บริการเมื่อได้รับข้อมูลที่ตรวจสอบได้จริง",tags:["Flights","Hotels"],url:"#travel",label:"ไปที่ Travel"},
{id:"world",icon:"◈",name:"World News & Trends",desc:"ข่าวเศรษฐกิจ การเมือง ความขัดแย้งและเทรนด์ Social — อยู่ระหว่างเตรียมแหล่งข่าวและระบบจัดอันดับ",tags:["World","Social"],url:"#discover",label:"ไปที่ Discover"}
];
const defaultOrder=["flow","watchlist","calendar","alerts","travel","world"];
const key="myworld.v2.dashboard.layout";let layout=readLayout();let editing=false;let mode="dashboard";
function readLayout(){try{const d=JSON.parse(localStorage.getItem(key));if(d&&Array.isArray(d.order))return {order:[...new Set([...d.order.filter(x=>defaultOrder.includes(x)),...defaultOrder])],hidden:Array.isArray(d.hidden)?d.hidden.filter(x=>defaultOrder.includes(x)):[],large:Array.isArray(d.large)?d.large.filter(x=>defaultOrder.includes(x)):["flow"]}}catch{}return {order:[...defaultOrder],hidden:["travel","world"],large:["flow"]}}
function save(){try{localStorage.setItem(key,JSON.stringify(layout))}catch{}}
function make(tag,className,txt){let x=document.createElement(tag);if(className)x.className=className;if(txt!==undefined)x.textContent=txt;return x}
function button(text,fn,disabled=false){const b=make("button","btn small ghost",text);b.type="button";b.disabled=disabled;b.addEventListener("click",fn);return b}
function modify(fn){fn();save();drawWidgets()}
function move(id,step){modify(()=>{const i=layout.order.indexOf(id),j=i+step;if(j>=0&&j<layout.order.length)[layout.order[i],layout.order[j]]=[layout.order[j],layout.order[i]]})}
function drawWidgets(){const area=document.getElementById("widgetGrid");area.replaceChildren();const active=layout.order.filter(id=>!layout.hidden.includes(id));for(const id of active){const w=widgets.find(x=>x.id===id);const card=make("article","widget"+(layout.large.includes(id)?" large":""));const top=make("div","widget-title");top.append(make("span","tileicon",w.icon));const heading=make("div","grow");heading.append(make("h3","",w.name),make("div","status","Widget · Your dashboard"));top.append(heading);card.append(top,make("p","",w.desc));const tagarea=make("div");for(const t of w.tags)tagarea.append(make("span","chip",t));card.append(tagarea);const link=make("a","cardlink",w.label+" →");link.href=w.url;card.append(link);if(editing){const controls=make("div","controls");const i=layout.order.indexOf(id);controls.append(button("↑",()=>move(id,-1),i===0),button("↓",()=>move(id,1),i===layout.order.length-1),button(layout.large.includes(id)?"Small":"Large",()=>modify(()=>{layout.large=layout.large.includes(id)?layout.large.filter(x=>x!==id):[...layout.large,id]})),button("Hide",()=>modify(()=>layout.hidden.push(id))));card.append(controls)}area.append(card)}const box=document.getElementById("widgetPicker");box.classList.toggle("hidden",!editing);const picker=document.getElementById("pickerItems");picker.replaceChildren();for(const id of layout.order.filter(x=>layout.hidden.includes(x))){const w=widgets.find(x=>x.id===id);picker.append(button("+ "+w.name,()=>modify(()=>layout.hidden=layout.hidden.filter(x=>x!==id))))}if(!picker.childNodes.length)picker.append(make("div","status","เปิดการ์ดครบแล้ว"));document.getElementById("customize").textContent=editing?"✓ Done":"⚙ Customize"}
document.getElementById("customize").onclick=()=>{editing=!editing;drawWidgets()};
const fallbackSnapshots=[
{topic:"US Inflation News Watch",kind:"Macro",impact:95,relevance:95,freshness:35,credibility:65,urgency:75,brief:"ติดตาม CPI, PPI และผลต่อ USD, Bond Yields, หุ้น, BTC และ XAUUSD ต้องรอ Actual และข้อมูลยืนยันก่อนสรุปสถานะตลาด",url:"./notifications.html"},
{topic:"NVDA / TSM / AVGO / MRVL",kind:"Equity",impact:75,relevance:92,freshness:30,credibility:60,urgency:40,brief:"อ่านความเชื่อมโยงของ AI Capex กับ GPU, Foundry, Custom ASIC และ Optical Networking ผ่านรายการเฝ้าติดตาม",url:"./notifications.html"},
{topic:"Oracle & AI Data Centers",kind:"Equity",impact:65,relevance:82,freshness:30,credibility:60,urgency:35,brief:"จุดที่ต้องติดตามคือ OCI, Capex, Financing และ Free Cash Flow; ยังไม่ใช่การยืนยันข่าวใหม่",url:"./notifications.html"},
{topic:"Travel: Bangkok – Fukuoka",kind:"Travel",impact:38,relevance:78,freshness:30,credibility:60,urgency:20,brief:"งานตรวจราคาเที่ยวบินตามเกณฑ์เดิม หากพบดีลที่ตรวจสอบได้จึงควรแจ้งพร้อมยอดสุทธิและรายละเอียดสัมภาระ",url:"./notifications.html"}
];
const weights={impact:.30,relevance:.25,freshness:.20,credibility:.15,urgency:.10};
function score(e){return Object.entries(weights).reduce((sum,[k,v])=>sum+e[k]*v,0)}
function drawFeed(){
  const list=document.getElementById("feedList");list.replaceChildren();
  const live=(window.DASHBOARD_DATA?.news?.top||[]);
  if(live.length){
    for(const [i,n] of live.slice(0,12).entries()){
      const card=make("article","feeditem");
      card.append(make("div","rank",String(i+1).padStart(2,"0")));
      const body=make("div","grow");
      const meta=[n.category?.toUpperCase(),n.source,n.publishedAt?new Date(n.publishedAt).toLocaleString("th-TH",{timeZone:"Asia/Bangkok",dateStyle:"short",timeStyle:"short"}):""].filter(Boolean).join(" · ");
      const sentiment=n.sentiment==="positive"?"👍":n.sentiment==="negative"?"👎":"";
      const titleRow=make("div","news-title-row");
      if(sentiment){const s=make("span","sentiment "+n.sentiment,sentiment);titleRow.append(s)}
      titleRow.append(make("h3","",n.title));
      body.append(make("div","feedmeta",(n.breaking?"BREAKING · ":"")+(n.vip?"VIP · ":"")+meta),titleRow);
      if(n.imageUrl){const img=document.createElement("img");img.className="feedthumb";img.src=n.imageUrl;img.alt="";img.loading="lazy";body.append(img)}
      body.append(make("p","news-summary",n.summaryShort||n.summary||""));
      const a=make("a","cardlink","อ่านต้นทาง →");a.href=n.url;a.target="_blank";a.rel="noopener noreferrer";body.append(a);
      card.append(body);list.append(card);
    }
    return;
  }
  for(const [i,f] of [...fallbackSnapshots].sort((a,b)=>score(b)-score(a)).entries()){
    const card=make("article","feeditem");card.append(make("div","rank",String(i+1).padStart(2,"0")));
    const body=make("div","grow");body.append(make("div","feedmeta","TOPIC BRIEF · SNAPSHOT · "+f.kind),make("h3","",f.topic),make("p","",f.brief),make("div","priority","Priority score "+score(f).toFixed(0)+"/100 · fallback"));
    const a=make("a","cardlink","ดูรายละเอียด →");a.href=f.url;body.append(a);card.append(body);list.append(card);
  }
}
function setMode(next){mode=next;document.getElementById("dashboardView").classList.toggle("hidden",next!=="dashboard");document.getElementById("feedView").classList.toggle("hidden",next!=="feed");document.getElementById("dashboardToggle").classList.toggle("active",next==="dashboard");document.getElementById("feedToggle").classList.toggle("active",next==="feed");}
document.getElementById("dashboardToggle").onclick=()=>setMode("dashboard");document.getElementById("feedToggle").onclick=()=>setMode("feed");
const pages=["home","finance","discover","travel","life","alerts"];function route(){let current=location.hash.replace("#","")||"home";if(!pages.includes(current))current="home";for(const p of pages)document.getElementById("page-"+p).classList.toggle("hidden",current!==p);document.querySelectorAll("[data-route]").forEach(el=>{el.classList.toggle("active",el.dataset.route===current);if(el.dataset.route===current)el.setAttribute("aria-current","page");else el.removeAttribute("aria-current")});window.scrollTo(0,0)}
window.addEventListener("hashchange",route);document.getElementById("resetLayout").onclick=()=>{layout={order:[...defaultOrder],hidden:["travel","world"],large:["flow"]};save();drawWidgets()};drawWidgets();drawFeed();route();


function fmtBangkok(iso){
  try{return new Date(iso).toLocaleString("th-TH",{timeZone:"Asia/Bangkok",dateStyle:"medium",timeStyle:"short"})}catch{return iso||""}
}
function renderMacro(){
  const box=document.getElementById("macroEventTable"); if(!box)return;
  const rows=window.DASHBOARD_DATA?.financeEvents||[];
  box.innerHTML=rows.length?`<div class="macro-table">
    <div class="macro-row macro-head"><span>Event</span><span>วันที่</span><span>เวลาไทย</span><span>Impact</span></div>
    ${rows.map(e=>`<a class="macro-row" href="${e.url}" target="_blank" rel="noopener"><strong>${e.title}</strong><span>${e.date}</span><span>${e.timeTH}</span><span class="impact-red">HIGH</span></a>`).join("")}
  </div>`:'<div class="status">ยังดึงปฏิทินไม่ได้</div>';
}
function renderDiscover(){
  const box=document.getElementById("discoverNews"); if(!box)return;
  const data=window.DASHBOARD_DATA?.news||{};
  const cats=[["markets","Markets / Crypto"],["politics","Politics"],["world","World / Geopolitics"],["tech_ai","Tech / AI"]];
  box.innerHTML=cats.map(([key,label])=>`<section class="news-col"><h2>${label}</h2>${(data[key]||[]).slice(0,6).map(n=>`<a class="news-row" href="${n.url}" target="_blank" rel="noopener">${n.imageUrl?'<img class="news-row-img" src="'+n.imageUrl+'" alt="" loading="lazy">':""}<div class="news-row-body"><div class="news-row-meta">${n.breaking?'<b>BREAKING</b> ':''}${n.vip?'<i>VIP</i> ':''}${n.source||""}</div><div class="news-title-line">${n.sentiment==="positive"?'<span class="sentiment positive">👍</span>':n.sentiment==="negative"?'<span class="sentiment negative">👎</span>':""}<strong>${n.title}</strong></div><p class="news-summary">${n.summaryShort||n.summary||""}</p><span>${n.publishedAt?fmtBangkok(n.publishedAt):""}</span></div></a>`).join("")||'<div class="status">No recent items</div>'}</section>`).join("");
  const u=document.getElementById("discoverUpdated");if(u&&window.DASHBOARD_DATA?.updated)u.textContent="Updated "+fmtBangkok(window.DASHBOARD_DATA.updated);
  const cp=document.getElementById("connectorPlan");if(cp)cp.innerHTML='<span class="chip">X / posts</span><span class="chip">Reddit</span><span class="chip">YouTube</span><span class="chip">Google Trends</span>';
}
function renderLife(){
  const box=document.getElementById("lifeEventList");if(!box)return;
  const rows=window.DASHBOARD_DATA?.lifeEvents||[];
  box.innerHTML=rows.map(e=>`<article class="event-card visual-card">${e.imageUrl?'<img class="event-hero" src="'+e.imageUrl+'" alt="" loading="lazy">':""}<div class="event-content"><div class="event-date"><b>${e.date}</b><span>${e.time}</span></div><div class="grow"><div class="event-type">${e.type}</div><h3>${e.title}</h3><p>${e.venue}</p><a class="cardlink" href="${e.url}" target="_blank" rel="noopener">จอง/ดูรายละเอียดกับ ${e.booking} →</a></div></div></article>`).join("")||'<div class="status">ยังไม่มี event ที่ยืนยัน</div>';
}
function renderTravel(){
  const box=document.getElementById("travelPromoList");if(!box)return;
  const rows=window.DASHBOARD_DATA?.travelPromos||[];
  box.innerHTML=rows.map(p=>`<article class="deal-card ${p.hot?"hot":""} visual-deal">${p.imageUrl?'<img class="deal-hero" src="'+p.imageUrl+'" alt="" loading="lazy">':""}<div class="deal-body">${p.hot?'<span class="hotdeal">HOT DEAL ≥50%</span>':""}<div class="deal-provider">${p.provider||p.source||""}</div><h3>${p.title}</h3>${p.discountPct?'<div class="deal-discount">-'+p.discountPct+'%</div>':""}<p>${p.publishedAt?"พบเมื่อ "+fmtBangkok(p.publishedAt):"ตรวจสอบ availability และราคาสุทธิที่หน้า provider"}</p><div class="deal-actions"><a href="${p.bookingUrl||p.url}" target="_blank" rel="noopener">ไปจอง/ดูโปร →</a>${p.url&&p.url!==p.bookingUrl?'<a class="secondary" href="'+p.url+'" target="_blank" rel="noopener">แหล่งที่พบ</a>':""}</div></div></article>`).join("")||'<div class="status">ยังไม่พบโปรล่าสุด</div>';
}
function renderLiveDashboard(){renderMacro();renderDiscover();renderLife();renderTravel();}
renderLiveDashboard();
