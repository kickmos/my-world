const SNAPSHOT = {
  updated: "Prototype • sample data",
  regime: "Early risk-on",
  riskScore: 64,
  liquidityScore: 72,
  dominantRoute: "Cash → US Stocks",
  stations: [
    {
      id:"local", name:"Local FX", short:"FX", state:"outflow", flow:"−", velocity:"↓", confidence:63, crowding:31,
      desc:"Domestic currencies and local assets. This station represents cross-border pressure rather than a single currency pair.",
      evidence:[["FX relative strength","Mixed","Price + macro proxy"],["Foreign investor flow","Observed","Use local exchange / central-bank data"]],
      next:[
        {target:"usd",label:"USD Cash",probability:42,type:"mixed"},
        {target:"global",label:"Global Risk",probability:26,type:"inferred"},
        {target:"gold",label:"Gold",probability:18,type:"inferred"}
      ],
      futures:[
        {name:"FX futures",signal:"neutral",note:"Positioning / hedge confirmation"},
        {name:"DXY proxies",signal:"neutral",note:"Dollar pressure confirmation"}
      ]
    },
    {
      id:"usd", name:"USD Cash", short:"USD", state:"neutral", flow:"≈", velocity:"→", confidence:78, crowding:46,
      desc:"Global funding and cash reservoir. A key transit station before money is redeployed.",
      evidence:[["DXY / major FX","Observed","Market prices"],["Dollar liquidity conditions","Mixed","Fed/BIS proxies"]],
      next:[
        {target:"mmf",label:"MMF / T-Bills",probability:38,type:"inferred"},
        {target:"stocks",label:"US Stocks",probability:31,type:"mixed"},
        {target:"gold",label:"Gold",probability:14,type:"inferred"}
      ],
      futures:[
        {name:"DXY / FX futures",signal:"neutral",note:"Dollar positioning confirmation"},
        {name:"SOFR futures",signal:"positive",note:"Rates expectations / funding conditions"}
      ]
    },
    {
      id:"mmf", name:"MMF / T-Bills", short:"CASH", state:"outflow", flow:"−", velocity:"↓↓", confidence:81, crowding:57,
      desc:"Primary parking station for liquid capital. Falling balances can support a risk reallocation thesis, but are not proof of destination.",
      evidence:[["Money-market assets","Observed","ICI/Fed series"],["T-Bill yields","Observed","Treasury market"]],
      next:[
        {target:"stocks",label:"US Stocks",probability:44,type:"inferred"},
        {target:"bonds",label:"Bonds / Credit",probability:29,type:"inferred"},
        {target:"crypto",label:"Crypto",probability:9,type:"inferred"}
      ],
      futures:[
        {name:"SOFR futures",signal:"positive",note:"Policy-rate expectations"},
        {name:"Treasury bill curve",signal:"neutral",note:"Cash-parking opportunity cost"}
      ]
    },
    {
      id:"bonds", name:"Bonds / Credit", short:"BONDS", state:"neutral", flow:"+", velocity:"→", confidence:73, crowding:52,
      desc:"Duration and credit complex: Treasuries, IG, HY and inflation-linked bonds.",
      evidence:[["Yield curve","Observed","Treasury/FRED"],["Credit spreads","Observed","FRED/market proxies"]],
      next:[
        {target:"stocks",label:"US Stocks",probability:34,type:"inferred"},
        {target:"gold",label:"Gold",probability:21,type:"inferred"},
        {target:"mmf",label:"MMF / T-Bills",probability:19,type:"mixed"}
      ],
      futures:[
        {name:"ZN / UB Treasury",signal:"positive",note:"Duration positioning"},
        {name:"SOFR futures",signal:"positive",note:"Expected path of policy rates"}
      ]
    },
    {
      id:"gold", name:"Gold", short:"GOLD", state:"inflow", flow:"++", velocity:"↑", confidence:76, crowding:61,
      desc:"Monetary hedge and safe-haven station. Can attract capital during both risk-off and currency-debasement regimes.",
      evidence:[["Gold price / volume","Observed","Market data"],["Gold ETF holdings","Observed","Issuer/public data"]],
      next:[
        {target:"usd",label:"USD Cash",probability:32,type:"mixed"},
        {target:"crypto",label:"Crypto",probability:23,type:"inferred"},
        {target:"global",label:"Global Risk",probability:18,type:"inferred"}
      ],
      futures:[
        {name:"COMEX Gold (GC)",signal:"positive",note:"Leverage / positioning confirmation"},
        {name:"Open interest",signal:"positive",note:"Separates participation from price-only move"}
      ]
    },
    {
      id:"crypto", name:"Crypto", short:"BTC", state:"inflow", flow:"+", velocity:"↑", confidence:68, crowding:74,
      desc:"Digital-asset risk station. Stablecoins should be tracked separately from BTC/ETH because they also act as cash-like transit rails.",
      evidence:[["Stablecoin supply","Observed","Public on-chain data"],["BTC/ETH market trend","Observed","Market data"],["Exchange netflow","Mixed","Provider dependent"]],
      next:[
        {target:"stocks",label:"US Stocks",probability:28,type:"inferred"},
        {target:"usd",label:"USD Cash",probability:25,type:"mixed"},
        {target:"gold",label:"Gold",probability:20,type:"inferred"}
      ],
      futures:[
        {name:"CME BTC futures",signal:"positive",note:"Institutional derivatives positioning"},
        {name:"BTC perpetuals",signal:"positive",note:"Funding + open-interest leverage"}
      ]
    },
    {
      id:"stocks", name:"US Stocks", short:"EQUITY", state:"inflow", flow:"+++", velocity:"↑↑", confidence:84, crowding:69,
      desc:"US equity risk station. Sector and single-name rotation will be expanded as a deeper layer, while this map keeps top-level destinations clean.",
      evidence:[["ETF/fund flows","Mixed","Issuer + public flow reports"],["Breadth / volume","Observed","Market data"],["Relative strength","Observed","Market data"]],
      next:[
        {target:"bonds",label:"Bonds / Credit",probability:30,type:"inferred"},
        {target:"usd",label:"USD Cash",probability:24,type:"mixed"},
        {target:"global",label:"Global Risk",probability:21,type:"inferred"}
      ],
      futures:[
        {name:"NQ futures",signal:"positive",note:"Nasdaq risk expression"},
        {name:"ES futures",signal:"positive",note:"Broad US equity confirmation"},
        {name:"RTY futures",signal:"neutral",note:"Small-cap breadth confirmation"}
      ]
    },
    {
      id:"global", name:"Global Risk", short:"GLOBAL", state:"neutral", flow:"+", velocity:"→", confidence:62, crowding:43,
      desc:"Europe, Japan, China/HK, India and emerging-market risk assets outside the US.",
      evidence:[["Regional ETF relative strength","Observed","Market data"],["Cross-border banking/liquidity","Observed","BIS, lower frequency"]],
      next:[
        {target:"local",label:"Local FX",probability:33,type:"mixed"},
        {target:"usd",label:"USD Cash",probability:29,type:"inferred"},
        {target:"gold",label:"Gold",probability:17,type:"inferred"}
      ],
      futures:[
        {name:"Regional index futures",signal:"neutral",note:"Cross-market risk positioning"},
        {name:"FX futures",signal:"neutral",note:"Currency translation / hedging pressure"}
      ]
    }
  ],
  routes:[
    {from:"MMF / T-Bills",to:"US Stocks",score:82,type:"inferred"},
    {from:"USD Cash",to:"US Stocks",score:71,type:"mixed"},
    {from:"Bonds / Credit",to:"Gold",score:58,type:"inferred"}
  ]
};

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
document.getElementById("coreState").textContent = `RISK-ON ${SNAPSHOT.riskScore}`;

const pointFor = (i,total) => {
  const angle = (-90 + (360/total)*i) * Math.PI/180;
  return {x:center.x+radius*Math.cos(angle),y:center.y+radius*Math.sin(angle)};
};

const points = SNAPSHOT.stations.map((_,i)=>pointFor(i,SNAPSHOT.stations.length));
const stationById = Object.fromEntries(SNAPSHOT.stations.map((s,i)=>[s.id,{station:s,index:i,point:points[i]}]));

function edgeEndpoints(a,b,padStart=nodeRadius+7,padEnd=nodeRadius+12){
  const dx=b.x-a.x, dy=b.y-a.y, len=Math.hypot(dx,dy) || 1;
  const ux=dx/len, uy=dy/len;
  return {
    start:{x:a.x+ux*padStart,y:a.y+uy*padStart},
    end:{x:b.x-ux*padEnd,y:b.y-uy*padEnd}
  };
}

SNAPSHOT.stations.forEach((station,i)=>{
  const a=points[i], b=points[(i+1)%points.length];
  const e=edgeEndpoints(a,b);
  const path=document.createElementNS("http://www.w3.org/2000/svg","path");
  path.setAttribute("d",`M ${e.start.x} ${e.start.y} L ${e.end.x} ${e.end.y}`);
  path.setAttribute("class",`edge ${station.id==="mmf"||station.id==="stocks"?"strong":station.state==="outflow"?"out":""}`);
  edgesG.appendChild(path);
});

function createNode(station,i){
  const p=points[i];
  const g=document.createElementNS("http://www.w3.org/2000/svg","g");
  g.setAttribute("class",`node ${station.state}`);
  g.setAttribute("data-station-id",station.id);
  g.setAttribute("tabindex","0");
  g.setAttribute("role","button");
  g.setAttribute("aria-label",station.name);
  g.setAttribute("transform",`translate(${p.x},${p.y})`);
  g.innerHTML=`
    <circle r="${nodeRadius}"></circle>
    <text text-anchor="middle" y="-3">${station.short}</text>
    <text class="sub" text-anchor="middle" y="17">${station.flow} • ${station.confidence}%</text>
  `;
  g.addEventListener("click",()=>openStation(station));
  g.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();openStation(station)}});
  nodesG.appendChild(g);
}
SNAPSHOT.stations.forEach(createNode);

function projectedControlPoint(a,b){
  const va={x:a.x-center.x,y:a.y-center.y};
  const vb={x:b.x-center.x,y:b.y-center.y};
  let sx=va.x+vb.x, sy=va.y+vb.y;
  let len=Math.hypot(sx,sy);
  if(len<20){
    sx=-va.y;
    sy=va.x;
    len=Math.hypot(sx,sy) || 1;
  }
  const controlRadius=155;
  return {x:center.x+(sx/len)*controlRadius,y:center.y+(sy/len)*controlRadius};
}

function quadPoint(a,c,b,t){
  const mt=1-t;
  return {
    x:mt*mt*a.x+2*mt*t*c.x+t*t*b.x,
    y:mt*mt*a.y+2*mt*t*c.y+t*t*b.y
  };
}

function clearProjectedRoutes(){
  projectedG.innerHTML="";
  document.querySelectorAll(".node").forEach(n=>n.classList.remove("active","projected-target"));
}

function renderProjectedRoutes(station){
  clearProjectedRoutes();
  if(!station || !projectedEnabled) return;
  const source=stationById[station.id];
  const sourceNode=document.querySelector(`.node[data-station-id="${station.id}"]`);
  if(sourceNode) sourceNode.classList.add("active");

  station.next.forEach(route=>{
    const target=stationById[route.target];
    if(!target) return;
    const targetNode=document.querySelector(`.node[data-station-id="${route.target}"]`);
    if(targetNode) targetNode.classList.add("projected-target");

    const e=edgeEndpoints(source.point,target.point,nodeRadius+10,nodeRadius+15);
    const c=projectedControlPoint(source.point,target.point);
    const path=document.createElementNS("http://www.w3.org/2000/svg","path");
    const opacity=Math.max(.22,Math.min(.84,.16+route.probability/55));
    const width=Math.max(1.4,Math.min(5,1.2+route.probability/12));
    path.setAttribute("d",`M ${e.start.x} ${e.start.y} Q ${c.x} ${c.y} ${e.end.x} ${e.end.y}`);
    path.setAttribute("class",`projected-edge ${route.probability<15?"low":""}`);
    path.style.opacity=opacity;
    path.style.strokeWidth=width;
    projectedG.appendChild(path);

    const labelPos=quadPoint(e.start,c,e.end,.5);
    const label=document.createElementNS("http://www.w3.org/2000/svg","text");
    label.setAttribute("x",labelPos.x);
    label.setAttribute("y",labelPos.y-6);
    label.setAttribute("text-anchor","middle");
    label.setAttribute("class","projected-label");
    label.textContent=`${route.probability}%`;
    projectedG.appendChild(label);
  });
}

function renderFutureLayer(){
  futureLayer.innerHTML="";
  SNAPSHOT.stations.forEach((station,i)=>{
    if(!station.futures?.length) return;
    const p=points[i];
    const vx=p.x-center.x, vy=p.y-center.y;
    const len=Math.hypot(vx,vy)||1;
    const ux=vx/len, uy=vy/len;
    const chip={x:p.x+ux*72,y:p.y+uy*72};
    const link=document.createElementNS("http://www.w3.org/2000/svg","line");
    link.setAttribute("x1",p.x+ux*(nodeRadius+4));
    link.setAttribute("y1",p.y+uy*(nodeRadius+4));
    link.setAttribute("x2",chip.x-ux*25);
    link.setAttribute("y2",chip.y-uy*12);
    link.setAttribute("class","future-link");
    futureLayer.appendChild(link);

    const g=document.createElementNS("http://www.w3.org/2000/svg","g");
    g.setAttribute("class","future-chip");
    g.setAttribute("transform",`translate(${chip.x-37},${chip.y-13})`);
    const label=station.futures[0].name.replace(" futures","").replace("Treasury","UST").slice(0,12);
    g.innerHTML=`<rect width="74" height="26" rx="9"></rect><text x="37" y="17" text-anchor="middle">${label}</text>`;
    futureLayer.appendChild(g);
  });
}
renderFutureLayer();

const panel=document.getElementById("detailPanel");
const backdrop=document.getElementById("backdrop");

function openStation(station){
  activeStation=station;
  renderProjectedRoutes(station);
  document.getElementById("detailTitle").textContent=station.name;
  document.getElementById("detailDesc").textContent=station.desc;
  document.getElementById("detailFlow").textContent=station.flow;
  document.getElementById("detailVelocity").textContent=station.velocity;
  document.getElementById("detailConfidence").textContent=station.confidence+"%";
  document.getElementById("detailCrowding").textContent=station.crowding+"%";
  document.getElementById("evidenceList").innerHTML=station.evidence.map(([name,type,note])=>`
    <div class="evidence">
      <div class="evidence-top"><strong>${name}</strong><span class="badge ${type.toLowerCase()}">${type}</span></div>
      <p>${note}</p>
    </div>`).join("");
  document.getElementById("nextList").innerHTML=station.next.map(route=>`
    <div class="next-row">
      <strong>${route.label}</strong>
      <span>${route.probability}% route probability</span>
    </div>`).join("");
  document.getElementById("futureList").innerHTML=station.futures.map(item=>`
    <div class="future-item">
      <div><strong>${item.name}</strong><br><span>${item.note}</span></div>
      <span class="future-state ${item.signal}">${item.signal}</span>
    </div>`).join("");
  panel.classList.add("open");
  backdrop.classList.add("show");
  panel.setAttribute("aria-hidden","false");
}

function closePanel(){
  panel.classList.remove("open");
  backdrop.classList.remove("show");
  panel.setAttribute("aria-hidden","true");
  activeStation=null;
  clearProjectedRoutes();
}
document.getElementById("closePanel").addEventListener("click",closePanel);
backdrop.addEventListener("click",closePanel);
document.addEventListener("keydown",e=>{if(e.key==="Escape")closePanel()});

const projectedToggle=document.getElementById("projectedToggle");
projectedToggle.addEventListener("click",()=>{
  projectedEnabled=!projectedEnabled;
  projectedToggle.classList.toggle("active",projectedEnabled);
  projectedToggle.setAttribute("aria-pressed",String(projectedEnabled));
  if(activeStation) renderProjectedRoutes(activeStation);
  else clearProjectedRoutes();
});

const futuresToggle=document.getElementById("futuresToggle");
futuresToggle.addEventListener("click",()=>{
  futuresEnabled=!futuresEnabled;
  futuresToggle.classList.toggle("active",futuresEnabled);
  futuresToggle.setAttribute("aria-pressed",String(futuresEnabled));
  svg.classList.toggle("future-layer-on",futuresEnabled);
});

document.getElementById("routeList").innerHTML=SNAPSHOT.routes.map(r=>`
  <div class="route">
    <div><strong>${r.from} → ${r.to}</strong><br><span>Route strength ${r.score}/100</span></div>
    <span class="badge ${r.type}">${r.type}</span>
  </div>`).join("");

if("serviceWorker" in navigator){
  window.addEventListener("load",()=>navigator.serviceWorker.register("./sw.js").catch(()=>{}));
}
