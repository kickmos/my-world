const FALLBACK = {
  updated: "Waiting for first live snapshot",
  regime: "Transition",
  riskScore: 50,
  liquidityScore: 50,
  dominantRoute: "Waiting for data",
  stations: [
    ["local","Local FX","FX"],["usd","USD Cash","USD"],["mmf","MMF / T-Bills","CASH"],["bonds","Bonds / Credit","BONDS"],
    ["gold","Gold","GOLD"],["crypto","Crypto","BTC"],["stocks","US Stocks","EQUITY"],["global","Global Risk","GLOBAL"]
  ].map(([id,name,short])=>({id,name,short,state:"neutral",flow:"≈",velocity:"→",confidence:35,crowding:40,desc:"Live data is not available yet.",evidence:[["Status","Mixed","Waiting for the next collector run"]],next:[],futures:[]})),
  routes:[]
};

const SNAPSHOT = window.LIVE_SNAPSHOT || FALLBACK;
const svg = document.getElementById("flowSvg");
const nodesG = document.getElementById("nodes");
const edgesG = document.getElementById("edges");
const projectedG = document.getElementById("projectedEdges");
const futureLayer = document.getElementById("futureLayer");
const center = {x:350,y:350};
const radius = 250;
const nodeRadius = 48;
let projectedEnabled = true;
let futuresEnabled = false;
let activeStation = null;

document.getElementById("updated").textContent = SNAPSHOT.updated;
document.getElementById("regime").textContent = SNAPSHOT.regime;
document.getElementById("riskScore").textContent = SNAPSHOT.riskScore;
document.getElementById("liquidityScore").textContent = SNAPSHOT.liquidityScore;
document.getElementById("dominantRoute").textContent = SNAPSHOT.dominantRoute;
document.getElementById("coreState").textContent = `${SNAPSHOT.regime.toUpperCase()} ${SNAPSHOT.riskScore}`;

const pointFor=(i,total)=>{const a=(-90+(360/total)*i)*Math.PI/180;return{x:center.x+radius*Math.cos(a),y:center.y+radius*Math.sin(a)}};
const points=SNAPSHOT.stations.map((_,i)=>pointFor(i,SNAPSHOT.stations.length));
const stationById=Object.fromEntries(SNAPSHOT.stations.map((s,i)=>[s.id,{station:s,index:i,point:points[i]}]));

function edgeEndpoints(a,b,padStart=nodeRadius+7,padEnd=nodeRadius+12){
  const dx=b.x-a.x,dy=b.y-a.y,len=Math.hypot(dx,dy)||1,ux=dx/len,uy=dy/len;
  return{start:{x:a.x+ux*padStart,y:a.y+uy*padStart},end:{x:b.x-ux*padEnd,y:b.y-uy*padEnd}};
}

SNAPSHOT.stations.forEach((station,i)=>{
  const a=points[i],b=points[(i+1)%points.length],e=edgeEndpoints(a,b);
  const path=document.createElementNS("http://www.w3.org/2000/svg","path");
  path.setAttribute("d",`M ${e.start.x} ${e.start.y} L ${e.end.x} ${e.end.y}`);
  path.setAttribute("class",`edge ${station.state==="inflow"?"strong":station.state==="outflow"?"out":""}`);
  edgesG.appendChild(path);
});

function createNode(station,i){
  const p=points[i],g=document.createElementNS("http://www.w3.org/2000/svg","g");
  g.setAttribute("class",`node ${station.state}`); g.setAttribute("data-station-id",station.id); g.setAttribute("tabindex","0"); g.setAttribute("role","button"); g.setAttribute("aria-label",station.name); g.setAttribute("transform",`translate(${p.x},${p.y})`);
  const newsCount=(station.news||[]).filter(n=>!n.error).length;
  g.innerHTML=`<circle r="${nodeRadius}"></circle><text text-anchor="middle" y="-3">${station.short}</text><text class="sub" text-anchor="middle" y="17">${station.flow} • ${station.confidence}%</text>
    <g class="node-news" transform="translate(36,-36)" tabindex="0" role="button" aria-label="News for ${station.name}">
      <circle r="12"></circle>
      <path d="M 2 -8 L -5 1 L 0 1 L -3 8 L 7 -3 L 1 -3 Z"></path>
      <text class="news-count" x="11" y="-9" text-anchor="middle">${newsCount?Math.min(newsCount,9):""}</text>
    </g>`;
  const newsBadge=g.querySelector(".node-news");
  if(newsBadge){
    newsBadge.addEventListener("click",e=>{e.stopPropagation();openNews(station)});
    newsBadge.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();e.stopPropagation();openNews(station)}});
  }
  g.addEventListener("click",()=>openStation(station));
  g.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();openStation(station)}});
  nodesG.appendChild(g);
}
SNAPSHOT.stations.forEach(createNode);

function projectedControlPoint(a,b){
  const va={x:a.x-center.x,y:a.y-center.y},vb={x:b.x-center.x,y:b.y-center.y}; let sx=va.x+vb.x,sy=va.y+vb.y,len=Math.hypot(sx,sy);
  if(len<20){sx=-va.y;sy=va.x;len=Math.hypot(sx,sy)||1} const cr=155; return{x:center.x+(sx/len)*cr,y:center.y+(sy/len)*cr};
}
function quadPoint(a,c,b,t){const mt=1-t;return{x:mt*mt*a.x+2*mt*t*c.x+t*t*b.x,y:mt*mt*a.y+2*mt*t*c.y+t*t*b.y}}
function clearProjectedRoutes(){projectedG.innerHTML="";document.querySelectorAll(".node").forEach(n=>n.classList.remove("active","projected-target"))}
function renderProjectedRoutes(station){
  clearProjectedRoutes(); if(!station||!projectedEnabled)return; const source=stationById[station.id]; if(!source)return;
  const sn=document.querySelector(`.node[data-station-id="${station.id}"]`); if(sn)sn.classList.add("active");
  (station.next||[]).forEach(route=>{
    const target=stationById[route.target]; if(!target)return; const tn=document.querySelector(`.node[data-station-id="${route.target}"]`); if(tn)tn.classList.add("projected-target");
    const e=edgeEndpoints(source.point,target.point,nodeRadius+10,nodeRadius+15),c=projectedControlPoint(source.point,target.point),path=document.createElementNS("http://www.w3.org/2000/svg","path");
    const opacity=Math.max(.22,Math.min(.84,.16+route.probability/55)),width=Math.max(1.4,Math.min(5,1.2+route.probability/12));
    path.setAttribute("d",`M ${e.start.x} ${e.start.y} Q ${c.x} ${c.y} ${e.end.x} ${e.end.y}`); path.setAttribute("class",`projected-edge ${route.probability<15?"low":""}`); path.style.opacity=opacity; path.style.strokeWidth=width; projectedG.appendChild(path);
    const lp=quadPoint(e.start,c,e.end,.5),label=document.createElementNS("http://www.w3.org/2000/svg","text"); label.setAttribute("x",lp.x);label.setAttribute("y",lp.y-6);label.setAttribute("text-anchor","middle");label.setAttribute("class","projected-label");label.textContent=`${route.probability}%`;projectedG.appendChild(label);
  });
}

function renderFutureLayer(){
  futureLayer.innerHTML=""; SNAPSHOT.stations.forEach((station,i)=>{if(!station.futures?.length)return;const p=points[i],vx=p.x-center.x,vy=p.y-center.y,len=Math.hypot(vx,vy)||1,ux=vx/len,uy=vy/len,chip={x:p.x+ux*72,y:p.y+uy*72};
    const link=document.createElementNS("http://www.w3.org/2000/svg","line");link.setAttribute("x1",p.x+ux*(nodeRadius+4));link.setAttribute("y1",p.y+uy*(nodeRadius+4));link.setAttribute("x2",chip.x-ux*25);link.setAttribute("y2",chip.y-uy*12);link.setAttribute("class","future-link");futureLayer.appendChild(link);
    const g=document.createElementNS("http://www.w3.org/2000/svg","g");g.setAttribute("class","future-chip");g.setAttribute("transform",`translate(${chip.x-37},${chip.y-13})`);const label=station.futures[0].name.replace(" futures","").replace("Treasury","UST").slice(0,12);g.innerHTML=`<rect width="74" height="26" rx="9"></rect><text x="37" y="17" text-anchor="middle">${label}</text>`;futureLayer.appendChild(g);
  });
}
renderFutureLayer();

const panel=document.getElementById("detailPanel"),backdrop=document.getElementById("backdrop");
const newsSheet=document.getElementById("newsSheet"),newsBackdrop=document.getElementById("newsBackdrop");
const esc=s=>String(s??"").replace(/[&<>"\']/g,ch=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","\'":"&#039;"}[ch]));
function relativeTime(iso,ageHours){
  if(iso){
    const ms=Date.now()-new Date(iso).getTime();
    if(Number.isFinite(ms)){const h=Math.max(0,ms/3600000);if(h<1)return Math.max(1,Math.round(h*60))+"m ago";if(h<24)return Math.round(h)+"h ago";return Math.round(h/24)+"d ago";}
  }
  if(ageHours!=null){if(ageHours<1)return Math.max(1,Math.round(ageHours*60))+"m ago";if(ageHours<24)return Math.round(ageHours)+"h ago";return Math.round(ageHours/24)+"d ago";}
  return "";
}
function openNews(station){
  if(!station)return;
  document.getElementById("newsTitle").textContent="Headlines for "+station.name;
  document.getElementById("newsUpdated").textContent="Snapshot "+SNAPSHOT.updated+" • best-effort free feed";
  const items=station.news||[];
  document.getElementById("newsList").innerHTML=items.length?items.map(item=>{
    const meta=[relativeTime(item.publishedAt,item.ageHours),item.source].filter(Boolean).join(" • ");
    const badge=item.trusted?'<span class="news-source-badge">source-ranked</span>':"";
    if(item.error||!item.url)return '<article class="news-item muted"><div class="news-meta">'+esc(meta)+'</div><h3>'+esc(item.title||"News unavailable")+'</h3></article>';
    return '<a class="news-item" href="'+esc(item.url)+'" target="_blank" rel="noopener noreferrer"><div class="news-meta">'+esc(meta)+" "+badge+'</div><h3>'+esc(item.title)+'</h3></a>';
  }).join(""):'<article class="news-item muted"><h3>No recent headlines in this snapshot</h3></article>';
  newsSheet.classList.add("open");newsBackdrop.classList.add("show");newsSheet.setAttribute("aria-hidden","false");
}
function closeNews(){newsSheet.classList.remove("open");newsBackdrop.classList.remove("show");newsSheet.setAttribute("aria-hidden","true");}
function openStation(station){
  activeStation=station;renderProjectedRoutes(station);document.getElementById("detailTitle").textContent=station.name;document.getElementById("detailDesc").textContent=station.desc;document.getElementById("detailFlow").textContent=station.flow;document.getElementById("detailVelocity").textContent=station.velocity;document.getElementById("detailConfidence").textContent=station.confidence+"%";document.getElementById("detailCrowding").textContent=station.crowding+"%";
  document.getElementById("evidenceList").innerHTML=(station.evidence||[]).map(([name,type,note])=>`<div class="evidence"><div class="evidence-top"><strong>${name}</strong><span class="badge ${type.toLowerCase()}">${type}</span></div><p>${note}</p></div>`).join("");
  document.getElementById("institutionalList").innerHTML=(station.institutional||[]).map(item=>`<div class="institutional-item"><div><strong>${item.name}</strong><br><span>${item.note||""}</span></div><div class="institutional-value"><b>${item.value||""}</b><span class="future-state ${item.signal||"neutral"}">${item.signal||"neutral"}</span></div></div>`).join("")||`<div class="institutional-item"><span>No institutional confirmation wired yet</span></div>`;
  document.getElementById("nextList").innerHTML=(station.next||[]).map(r=>`<div class="next-row"><strong>${r.label}</strong><span>${r.probability}% inferred route</span></div>`).join("")||`<div class="next-row"><span>No route estimate yet</span></div>`;
  document.getElementById("futureList").innerHTML=(station.futures||[]).map(item=>{
    const fmt=n=>n==null?"n/a":Number(n).toLocaleString(undefined,{maximumFractionDigits:2});
    const pct=n=>n==null?"n/a":(Number(n)>=0?"+":"")+Number(n).toFixed(2)+"%";
    const cot=item.assetManager||item.leveragedFunds||item.nonCommercial;
    const cotRows=[];
    if(item.assetManager){
      cotRows.push(`<div class="cot-row"><span>Asset Manager</span><b>${fmt(item.assetManager.net)}</b><em>Δnet ${fmt(item.assetManager.deltaNet)}</em></div>`);
    }
    if(item.leveragedFunds){
      cotRows.push(`<div class="cot-row"><span>Leveraged Funds</span><b>${fmt(item.leveragedFunds.net)}</b><em>Δnet ${fmt(item.leveragedFunds.deltaNet)}</em></div>`);
    }
    if(item.nonCommercial){
      cotRows.push(`<div class="cot-row"><span>Non-commercial</span><b>${fmt(item.nonCommercial.net)}</b><em>Δnet ${fmt(item.nonCommercial.deltaNet)}</em></div>`);
    }
    return `<article class="future-card">
      <div class="future-card-head">
        <div><strong>${item.name}</strong><span class="future-horizon">${item.horizon||""}</span></div>
        <span class="positioning-pill ${item.signal||"neutral"}">${item.positioning||"unavailable"}</span>
      </div>
      <p class="future-explain">${item.note||""}</p>
      <div class="future-metrics">
        <div><span>Price 1D</span><b>${pct(item.priceChange1D)}</b></div>
        <div><span>Price 5D</span><b>${pct(item.priceChange5D)}</b></div>
        <div><span>Volume</span><b>${fmt(item.volume)}</b></div>
        <div><span>Vol / 5D avg</span><b>${item.volumeRatio==null?"n/a":Number(item.volumeRatio).toFixed(2)+"×"}</b></div>
        <div><span>Open interest</span><b>${fmt(item.openInterest)}</b></div>
        <div><span>ΔOI weekly</span><b>${fmt(item.deltaOI)}</b></div>
      </div>
      <div class="cot-block">
        <div class="cot-title"><span>CFTC COT</span><em>${item.reportDate||"date unavailable"}</em></div>
        ${cotRows.join("")||'<div class="cot-empty">COT breakdown unavailable for this contract</div>'}
      </div>
      <div class="future-source">${item.source||""}</div>
    </article>`;
  }).join("")||`<div class="future-item"><span>No futures proxy yet</span></div>`;
  panel.classList.add("open");backdrop.classList.add("show");panel.setAttribute("aria-hidden","false");
  const newsBtn=document.getElementById("openNewsFromDetail");if(newsBtn)newsBtn.onclick=()=>openNews(station);
}
function closePanel(){panel.classList.remove("open");backdrop.classList.remove("show");panel.setAttribute("aria-hidden","true");activeStation=null;clearProjectedRoutes()}
document.getElementById("closePanel").addEventListener("click",closePanel);backdrop.addEventListener("click",closePanel);document.getElementById("closeNews").addEventListener("click",closeNews);newsBackdrop.addEventListener("click",closeNews);document.addEventListener("keydown",e=>{if(e.key==="Escape"){closeNews();closePanel()}});

const projectedToggle=document.getElementById("projectedToggle");projectedToggle.addEventListener("click",()=>{projectedEnabled=!projectedEnabled;projectedToggle.classList.toggle("active",projectedEnabled);projectedToggle.setAttribute("aria-pressed",String(projectedEnabled));if(activeStation)renderProjectedRoutes(activeStation);else clearProjectedRoutes()});
const futuresToggle=document.getElementById("futuresToggle");futuresToggle.addEventListener("click",()=>{futuresEnabled=!futuresEnabled;futuresToggle.classList.toggle("active",futuresEnabled);futuresToggle.setAttribute("aria-pressed",String(futuresEnabled));svg.classList.toggle("future-layer-on",futuresEnabled)});

document.getElementById("routeList").innerHTML=(SNAPSHOT.routes||[]).map(r=>`<div class="route"><div><strong>${r.from} → ${r.to}</strong><br><span>Model route score ${r.score}/100</span></div><span class="badge ${r.type}">${r.type}</span></div>`).join("")||`<div class="route"><span>Waiting for live route model</span></div>`;

if("serviceWorker" in navigator){window.addEventListener("load",()=>navigator.serviceWorker.register("./sw.js").catch(()=>{}));}
