const SNAPSHOT = {
  updated: "Prototype • sample data",
  regime: "Early risk-on",
  riskScore: 64,
  liquidityScore: 72,
  dominantRoute: "Cash → US Stocks",
  stations: [
    {id:"local",name:"Local FX",short:"FX",state:"outflow",flow:"−",velocity:"↓",confidence:63,crowding:31,desc:"Domestic currencies and local assets. This station represents cross-border pressure rather than a single currency pair.",evidence:[["FX relative strength","Mixed","Price + macro proxy"],["Foreign investor flow","Observed","Use local exchange / central-bank data"]],next:[["USD Cash",42],["Global Equity",26],["Gold",18]]},
    {id:"usd",name:"USD Cash",short:"USD",state:"neutral",flow:"≈",velocity:"→",confidence:78,crowding:46,desc:"Global funding and cash reservoir. A key transit station before money is redeployed.",evidence:[["DXY / major FX","Observed","Market prices"],["Dollar liquidity conditions","Mixed","Fed/BIS proxies"]],next:[["MMF / T-Bills",38],["US Stocks",31],["Gold",14]]},
    {id:"mmf",name:"MMF / T-Bills",short:"CASH",state:"outflow",flow:"−",velocity:"↓↓",confidence:81,crowding:57,desc:"Primary parking station for liquid capital. Falling balances can support a risk reallocation thesis, but are not proof of destination.",evidence:[["Money-market assets","Observed","ICI/Fed series"],["T-Bill yields","Observed","Treasury market"]],next:[["US Stocks",44],["Bonds",29],["Crypto",9]]},
    {id:"bonds",name:"Bonds / Credit",short:"BONDS",state:"neutral",flow:"+",velocity:"→",confidence:73,crowding:52,desc:"Duration and credit complex: Treasuries, IG, HY and inflation-linked bonds.",evidence:[["Yield curve","Observed","Treasury/FRED"],["Credit spreads","Observed","FRED/market proxies"]],next:[["US Stocks",34],["Gold",21],["MMF / T-Bills",19]]},
    {id:"gold",name:"Gold",short:"GOLD",state:"inflow",flow:"++",velocity:"↑",confidence:76,crowding:61,desc:"Monetary hedge and safe-haven station. Can attract capital during both risk-off and currency-debasement regimes.",evidence:[["Gold price / volume","Observed","Market data"],["Gold ETF holdings","Observed","Issuer/public data"]],next:[["USD Cash",32],["Crypto",23],["Commodities",18]]},
    {id:"crypto",name:"Crypto",short:"BTC",state:"inflow",flow:"+",velocity:"↑",confidence:68,crowding:74,desc:"Digital-asset risk station. Stablecoins should be tracked separately from BTC/ETH because they also act as cash-like transit rails.",evidence:[["Stablecoin supply","Observed","Public on-chain data"],["BTC/ETH market trend","Observed","Market data"],["Exchange netflow","Mixed","Provider dependent"]],next:[["US Stocks",28],["USD Cash",25],["Alt crypto",20]]},
    {id:"stocks",name:"US Stocks",short:"EQUITY",state:"inflow",flow:"+++",velocity:"↑↑",confidence:84,crowding:69,desc:"US equity risk station. Expand later into sectors, factors and single-name leadership.",evidence:[["ETF/fund flows","Mixed","Issuer + public flow reports"],["Breadth / volume","Observed","Market data"],["Relative strength","Observed","Market data"]],next:[["Semiconductors",34],["Software / Cloud",26],["Healthcare",13]]},
    {id:"global",name:"Global Risk",short:"GLOBAL",state:"neutral",flow:"+",velocity:"→",confidence:62,crowding:43,desc:"Europe, Japan, China/HK, India and emerging-market risk assets outside the US.",evidence:[["Regional ETF relative strength","Observed","Market data"],["Cross-border banking/liquidity","Observed","BIS, lower frequency"]],next:[["Local FX",33],["USD Cash",29],["Commodities",17]]}
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
const center = {x:350,y:350};
const radius = 250;
const nodeRadius = 48;

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

SNAPSHOT.stations.forEach((station,i)=>{
  const a=points[i], b=points[(i+1)%points.length];
  const dx=b.x-a.x, dy=b.y-a.y, len=Math.hypot(dx,dy);
  const ux=dx/len, uy=dy/len;
  const x1=a.x+ux*(nodeRadius+7), y1=a.y+uy*(nodeRadius+7);
  const x2=b.x-ux*(nodeRadius+12), y2=b.y-uy*(nodeRadius+12);
  const path=document.createElementNS("http://www.w3.org/2000/svg","path");
  path.setAttribute("d",`M ${x1} ${y1} L ${x2} ${y2}`);
  path.setAttribute("class",`edge ${station.id==="mmf"||station.id==="stocks"?"strong":station.state==="outflow"?"out":""}`);
  edgesG.appendChild(path);
});

SNAPSHOT.stations.forEach((station,i)=>{
  const p=points[i];
  const g=document.createElementNS("http://www.w3.org/2000/svg","g");
  g.setAttribute("class",`node ${station.state}`);
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
});

const panel=document.getElementById("detailPanel");
const backdrop=document.getElementById("backdrop");
function openStation(station){
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
  document.getElementById("nextList").innerHTML=station.next.map(([name,p])=>`
    <div class="next-row"><strong>${name}</strong><span>${p}% route probability</span></div>`).join("");
  panel.classList.add("open"); backdrop.classList.add("show"); panel.setAttribute("aria-hidden","false");
}
function closePanel(){panel.classList.remove("open");backdrop.classList.remove("show");panel.setAttribute("aria-hidden","true")}
document.getElementById("closePanel").addEventListener("click",closePanel);
backdrop.addEventListener("click",closePanel);
document.addEventListener("keydown",e=>{if(e.key==="Escape")closePanel()});

document.getElementById("routeList").innerHTML=SNAPSHOT.routes.map(r=>`
  <div class="route">
    <div><strong>${r.from} → ${r.to}</strong><br><span>Route strength ${r.score}/100</span></div>
    <span class="badge ${r.type}">${r.type}</span>
  </div>`).join("");

if("serviceWorker" in navigator){
  window.addEventListener("load",()=>navigator.serviceWorker.register("./sw.js").catch(()=>{}));
}
