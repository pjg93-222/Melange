<!DOCTYPE html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Moneyball — Per-Issue Influence Dashboard</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0d1117;color:#e6edf3;font:13px/1.45 -apple-system,Segoe UI,Roboto,sans-serif;overflow:hidden}
#app{display:grid;grid-template-rows:auto auto 1fr;height:100vh}
header{padding:10px 16px;border-bottom:1px solid #21262d;display:flex;align-items:baseline;gap:14px;flex-wrap:nowrap}
header h1{font-size:16px;font-weight:700;letter-spacing:.2px;flex-shrink:0}
header .sub{color:#8b949e;font-size:12px;flex:1 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#bar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;padding:9px 16px;border-bottom:1px solid #21262d;background:#11161d}
#bar label{color:#8b949e;font-size:11px;text-transform:uppercase;letter-spacing:.4px;margin-right:4px}
select{background:#0d1117;color:#e6edf3;border:1px solid #30363d;border-radius:6px;padding:6px 9px;font-size:13px;min-width:260px}
.seg{display:inline-flex;border:1px solid #30363d;border-radius:6px;overflow:hidden}
.seg button{background:#0d1117;color:#9ca3af;border:0;padding:6px 12px;cursor:pointer;font-size:12px}
.seg button.on{background:#1f6feb;color:#fff;font-weight:600}
input#search{background:#0d1117;color:#e6edf3;border:1px solid #30363d;border-radius:6px;padding:6px 9px;width:170px}
#main{display:grid;grid-template-columns:236px 1fr 250px;min-height:0}
canvas{touch-action:none}
@media(max-width:640px){
  #app{height:auto;min-height:100vh}
  #main{grid-template-columns:1fr}
  #left{display:none}                          /* phone: hide aggregate stats/budget/optimizer -> graph-first */
  #netwrap{height:66vh;min-height:340px}        /* canvas up top, prominent */
  #right{border:0;border-top:1px solid #21262d;max-height:none}   /* member details appear BELOW the graph on tap */
  header{flex-wrap:wrap;gap:6px}header .sub{white-space:normal;flex-basis:100%}
  #bar{padding:8px 11px;gap:8px}
  select{min-width:0;width:100%}input#search{width:100%}
  .seg button{padding:9px 13px}
}
#left,#right{padding:12px 14px;overflow:auto;border-right:1px solid #21262d}
#right{border-right:0;border-left:1px solid #21262d}
#left h3,#right h3{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:#8b949e;margin-bottom:9px;font-weight:700}
.stat{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #1b2129}
.stat b{font-variant-numeric:tabular-nums}
.big{font-size:22px;font-weight:800;margin:4px 0}
.pill{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;vertical-align:middle}
.tgt{padding:6px 7px;border-radius:6px;cursor:pointer;display:flex;justify-content:space-between;gap:6px;align-items:center}
.tgt:hover{background:#1b2230}
.tgt small{color:#8b949e}
#cv{display:block;width:100%;height:100%;cursor:grab}
#netwrap{position:relative;min-width:0}
#tip{position:fixed;pointer-events:none;background:#161b22ee;border:1px solid #30363d;border-radius:7px;padding:8px 10px;font-size:12px;max-width:250px;display:none;z-index:9;box-shadow:0 6px 24px #000a}
#tip b{color:#fff}
#legend{position:absolute;left:10px;bottom:10px;background:#0d1117cc;border:1px solid #21262d;border-radius:8px;padding:8px 10px;font-size:11px}
#legend span{display:inline-flex;align-items:center;margin-right:10px}
.hint{color:#6e7681;font-size:11px;margin-top:8px}
#slider{width:100%;margin:8px 0 2px;accent-color:#1f6feb}
.frow{display:flex;justify-content:space-between;font-size:11px;color:#8b949e}
#optcard{margin-top:16px;border-top:1px solid #21262d;padding-top:12px}
.optline{font-size:12px;color:#c9d1d9;margin-bottom:6px}
.optline b{color:#fff;font-variant-numeric:tabular-nums}
.oa{display:flex;justify-content:space-between;padding:3px 6px;border-radius:5px;cursor:pointer;font-size:12px}
.oa:hover{background:#1b2230}.oa small{color:#8b949e}
.conv{color:#16a34a}
#mpanel{display:none}
.mrow{display:flex;justify-content:space-between;padding:4px 0;font-size:12px;border-bottom:1px solid #1b2129}
.mrow b{font-variant-numeric:tabular-nums;color:#fff}
.scc label{display:block;font-size:11px;color:#8b949e;margin:8px 0 2px}
.scc input[type=range]{width:100%;accent-color:#16a34a}
.scc input.comp{accent-color:#ef4444}
.delta{font-weight:800;font-variant-numeric:tabular-nums}.up{color:#16a34a}.down{color:#ef4444}
.recipe{font-size:12px;color:#c9d1d9;line-height:1.55}.recipe b{color:#fff}
.recruit{display:inline-block;background:#1b2230;border:1px solid #30363d;border-radius:5px;padding:1px 6px;margin:2px 3px 0 0;font-size:11px;cursor:pointer}
.recruit:hover{border-color:#1f6feb}
.abtn{background:#1f6feb;color:#fff;border:0;border-radius:6px;padding:6px 11px;cursor:pointer;font-size:12px;margin:10px 6px 0 0}
.abtn.ghost{background:#0d1117;color:#9ca3af;border:1px solid #30363d}
.scout{margin-top:8px;font-size:12px}
.defwarn{color:#f59e0b;font-weight:700}
#engchk{position:absolute;right:10px;bottom:10px;font-size:10px;color:#6e7681;background:#0d1117cc;border:1px solid #21262d;border-radius:6px;padding:4px 7px}
#mdlink{position:absolute;left:10px;top:10px;display:none;background:#1f6feb;color:#fff;border-radius:7px;padding:7px 12px;font-size:12px;font-weight:600;cursor:pointer;box-shadow:0 4px 16px #0007;z-index:8}
#mdlink:hover{background:#388bfd;text-decoration:none}#mdlink small{font-weight:400;opacity:.85}
.h2h{display:flex;height:15px;border-radius:7px;overflow:hidden;margin:7px 0 3px;border:1px solid #30363d}
.h2h>span{display:block}.h2h .cu{background:#16a34a}.h2h .ind{background:#ef4444}
.h2hlab{display:flex;justify-content:space-between;font-size:10px;color:#8b949e}
.h2hbe{font-size:11px;color:#c9d1d9;margin-top:4px}.h2hbe b{color:#fff}
#rtog{margin:2px 0 0}#rtog button,#pmode button,#execseg button{padding:4px 9px;font-size:11px}
.desklink{align-self:center;flex-shrink:0;border:1px solid #30363d;border-radius:6px;padding:7px 13px;font-size:12px;font-weight:600;color:#c9d1d9;text-decoration:none;white-space:nowrap}
.desklink:hover{border-color:#1f6feb;color:#fff;background:#1b2230}
:where(button,select,input,a,.tgt,.oa) :focus-visible,button:focus-visible,select:focus-visible,input:focus-visible,a:focus-visible{outline:2px solid #1f6feb;outline-offset:1px}
</style></head><body><div id=app>
<header><h1>Moneyball — Per-Issue Influence Dashboard</h1>
<span class=sub>533 members · cosponsorship network · per-category stance × competitive influence-maximization</span>
<a id=desklink class=desklink href="cu-member-desk.html">Member desk ▸</a></header>
<div id=bar>
<span><label>Issue</label><select id=issue></select></span>
<span><label>Mode</label><span class=seg id=mode><button data-m=coal class=on>Coalition (build)</button><button data-m=flip>Flip (persuade)</button></span></span>
<span><label>Color</label><span class=seg id=color><button data-c=issue class=on>Issue stance</button><button data-c=party>Party</button><button data-c=gen>Overall</button><button data-c=elec>Electoral</button></span></span>
<span><label>Layout</label><span class=seg id=ltog><button data-l=cosp class=on>Cosponsorship</button><button data-l=committee>Committees</button></span></span>
<span><label>Find</label><input id=search placeholder="member name…" list=names><datalist id=names></datalist></span>
</div>
<div id=main>
 <div id=left>
   <h3>This issue</h3>
   <div id=istats></div>
   <div id=budgetwrap>
     <h3 style=margin-top:16px id=bhdr>Budget frontier</h3>
     <input type=range id=slider min=0 max=100 value=100>
     <div class=frow><span>$0</span><span id=bmax>$2M</span></div>
     <div class=big id=money>$0</div>
     <div id=mdetail class=hint></div>
   </div>
   <div id=optcard>
     <h3>Adaptive optimizer · $2M</h3>
     <div id=optbody></div>
   </div>
 </div>
 <div id=netwrap><canvas id=cv></canvas><a id=mdlink href=#></a>
   <div id=legend></div>
   <div id=engchk>engine —</div>
 </div>
 <div id=right>
   <div id=tpanel><h3>Targets <span id=tgtmode style=color:#6e7681></span> <span style=float:right;color:#6e7681;font-weight:400;text-transform:none>click a node →</span></h3>
     <span class=seg id=rtog><button data-r=alloc class=on>Allocation</button><button data-r=flip>Cheapest to flip</button></span>
     <div id=targets style=margin-top:8px></div></div>
   <div id=mpanel>
     <h3 id=mname></h3><div id=mstance></div>
     <h3 style=margin-top:14px>Flip this member <span style=color:#6e7681;font-weight:400;text-transform:none>· internal pressure</span></h3>
     <div id=mprime class=recipe></div>
     <h3 style=margin-top:14px>Scenario <span style=color:#6e7681;font-weight:400;text-transform:none>· live what-if</span></h3>
     <div class=scc>
       <label>CU money &nbsp;<b id=culab style=color:#16a34a>$0k</b></label><input type=range id=cusl min=0 max=20 step=1 value=0>
       <label>Competitor money &nbsp;<b id=colab style=color:#ef4444>$0k</b></label><input type=range id=cosl class=comp min=0 max=30 step=1 value=0>
       <div id=scout class=scout></div>
       <div style=margin-top:10px><div class=h2hlab><span style=color:#16a34a>CU pull</span><span>flip odds <b id=h2hpct style=color:#e6edf3>50%</b></span><span style=color:#ef4444>industry</span></div>
         <div class=h2h><span class=cu id=h2hcu style=width:50%></span><span class=ind id=h2hind style=width:50%></span></div>
         <div class=h2hbe id=h2hbe></div></div>
     </div>
     <h3 style=margin-top:14px>Co-sponsor pathfinder <span style=color:#6e7681;font-weight:400;text-transform:none>· provably-optimal routes</span></h3>
     <div class=scc>
       <span class=seg id=pmode style=margin-bottom:5px><button data-p=path class=on>Path</button><button data-p=best>Best</button><button data-p=multi>Multi</button><button data-p=budget>Budget</button></span>
       <label id=plabel>bill sponsor <b id=seednm style=color:#16a34a></b> → reach target:</label>
       <input id=tgtsearch placeholder="target member…" list=names style="background:#0d1117;color:#e6edf3;border:1px solid #30363d;border-radius:6px;padding:5px 8px;width:100%;margin:5px 0;font-size:12px">
       <button class=abtn id=pathbtn>Build</button>
       <button class=abtn ghost id=backbtn>← Targets</button>
       <div id=pathout class=scout></div>
       <h3 style=margin-top:13px;border-top:1px solid #21262d;padding-top:11px>System shocks <span style=color:#6e7681;font-weight:400;text-transform:none>structural what-ifs</span></h3>
       <label>members drop out of the bill:</label>
       <input id=dropsearch placeholder="who backs out (comma-sep)" list=names style="background:#0d1117;color:#e6edf3;border:1px solid #30363d;border-radius:6px;padding:5px 8px;width:100%;margin:5px 0;font-size:12px">
       <label style=margin-top:4px>executive branch:</label>
       <span class=seg id=execseg style=margin-top:3px><button data-e=none class=on>neutral</button><button data-e=oppose>opposes</button><button data-e=support>supports</button></span>
       <div id=shockout class=scout></div>
       <div style=font-size:10px;color:#6e7681;margin-top:7px;line-height:1.45>Path = max-product (strongest) chain. "Holds" = P(every ASK lands first-try) using an active-recruitment rate (deliberate, funded ask via an existing tie — odds ~14x passive diffusion; ASKM is a tunable model dial, NOT empirically estimated); a no-reroute floor, rerouting only improves it. Budget = (1−1/e) max-coverage greedy w/ GCOMB locality (Manchanda et&nbsp;al. NeurIPS&nbsp;'20). Influence: Sotoudeh–Porter–Krishnagopal · communities: Porter–Mucha–Newman, Kim–Kunisky · coalitions: Aref–Neal · co-partisan info: Furnas et&nbsp;al.</div>
     </div>
   </div>
 </div>
</div></div><div id=tip></div>
<script>
const DATA=__DATA__;
const N=DATA.name.length;
// live node positions (tweened between the cosponsorship layout and the committee-cluster layout)
let LX=DATA.x.slice(), LY=DATA.y.slice(), layout='cosp';
const SC={C:'Champion',F:'Defender',A:'Ally',H:'Highly Persuadable',P:'Persuadable',G:'Lean Persuadable',T:'True Neutral',L:'Lean Skeptic',N:'Neutral',S:'Skeptic',K:'Highly Skeptical',O:'Opponent','-':'—'};
const STCOL={C:'#16a34a',F:'#2dd4bf',A:'#86efac',H:'#38bdf8',P:'#7dd3fc',G:'#bae6fd',T:'#9ca3af',N:'#8b949e',L:'#fde3c0',S:'#f59e0b',K:'#f97316',O:'#ef4444','-':'#3a414b'};
const PTCOL={D:'#3b82f6',R:'#ef4444',I:'#a855f7','?':'#6b7280'};
const ELCOL={c:'#f97316',g:'#d946ef',d:'#22d3ee',n:'#3a414b'};   // contest·primary / contest·general / defend / none
const PLAYLBL={c:'contest · primary',g:'contest · general',d:'defend',n:'none'};
let issue=3, mode='coal', colorBy='issue', hi=-1, sel=-1, budget=1000000, rmode='alloc', flipHi=null, pmodeVal='path';
let ORD=[], FUND={}, SPREAD=null;
// build issue dropdown
const isel=document.getElementById('issue');
DATA.issues.forEach((s,i)=>{let o=document.createElement('option');o.value=i;o.textContent=s;isel.appendChild(o);});
isel.value=issue;
const dl=document.getElementById('names');
DATA.name.forEach(n=>{let o=document.createElement('option');o.value=n;dl.appendChild(o);});
const slider=document.getElementById('slider');
// canvas + camera
const cv=document.getElementById('cv'),ctx=cv.getContext('2d');
let DPR=Math.min(devicePixelRatio||1,2),W=0,H=0;
let cam={s:1,tx:0,ty:0},drag=null,panMoved=false;
function resize(){const r=cv.parentElement.getBoundingClientRect();W=r.width;H=r.height;cv.width=W*DPR;cv.height=H*DPR;cv.style.width=W+'px';cv.style.height=H+'px';fit();draw();}
function fit(){const s=Math.min(W,H)/1000*0.96;cam.s=s;cam.tx=(W-1000*s)/2;cam.ty=(H-1000*s)/2;}
function toScreen(x,y){return [x*cam.s+cam.tx, y*cam.s+cam.ty];}
// funded set: flip = static per-target; coalition = budget-frontier seeds up to the slider budget (live lookup of precomputed path)
function fundedOrdered(){
  if(mode==='flip'){return Object.entries(DATA.flip[issue]).map(([i,v])=>[+i,v]).sort((a,b)=>b[1]-a[1]);}
  const f=DATA.frontier[issue];
  if(!f){return Object.entries(DATA.coal[issue]).map(([i,v])=>[+i,v]).sort((a,b)=>b[1]-a[1]);}
  const out=[];for(const [b,s,si] of f.path){if(b<=budget&&si>=0)out.push([si,Math.round(b/1000)]);}
  return out;
}
function frontierSpread(){const f=DATA.frontier[issue];if(!f)return null;let sp=f.base;for(const [b,s,si] of f.path){if(b<=budget)sp=s;}return sp;}
function computeFund(){ORD=fundedOrdered();FUND={};ORD.forEach(([i,v])=>FUND[i]=(mode==='flip'?v:50));SPREAD=(mode==='coal'&&DATA.frontier[issue])?frontierSpread():null;}
function allocOf(i){return FUND[i]||0;}
function colOf(i){if(colorBy==='party')return PTCOL[DATA.party[i]];if(colorBy==='gen')return STCOL[DATA.gen[i]];if(colorBy==='elec')return ELCOL[DATA.play[i]];return STCOL[DATA.stance[i][issue]];}
function radOf(i){const a=allocOf(i);return 2.0+(a>0?Math.min(Math.sqrt(a)*0.8,7):0);}   // capped so outsized-influence nodes don't swamp smaller ones
function draw(){
 ctx.setTransform(DPR,0,0,DPR,0,0);ctx.clearRect(0,0,W,H);
 if(layout==='cosp'){ctx.lineWidth=0.5;ctx.strokeStyle='rgba(139,148,158,0.10)';ctx.beginPath();   // cosponsorship ties hidden in committee view (they'd crisscross the clusters)
 for(const [a,b] of DATA.edges){const A=toScreen(LX[a],LY[a]),B=toScreen(LX[b],LY[b]);ctx.moveTo(A[0],A[1]);ctx.lineTo(B[0],B[1]);}
 ctx.stroke();}
 const order=[...Array(N).keys()].sort((p,q)=>allocOf(p)-allocOf(q));
 for(const i of order){const [sx,sy]=toScreen(LX[i],LY[i]);const r=radOf(i)*Math.max(1,cam.s*1);
   ctx.beginPath();ctx.arc(sx,sy,r,0,7);ctx.fillStyle=colOf(i);
   let al=(colorBy==='issue'&&DATA.stance[i][issue]==='-')?0.45:(colorBy==='elec'&&DATA.play[i]==='n')?0.3:1;
   if(r>4.5)al*=0.78;   // big (funded/high-influence) nodes go translucent so smaller ones underneath show through
   ctx.globalAlpha=al;ctx.fill();ctx.globalAlpha=1;
   if(allocOf(i)>0){ctx.lineWidth=1.1;ctx.strokeStyle='#fff';ctx.stroke();}
   if(i===hi||i===sel){ctx.lineWidth=2;ctx.strokeStyle='#fbbf24';ctx.beginPath();ctx.arc(sx,sy,r+3,0,7);ctx.stroke();}
 }
 if(flipHi){ctx.lineWidth=1.6;ctx.strokeStyle='#a78bfa';for(const i of flipHi){const [sx,sy]=toScreen(LX[i],LY[i]);const r=radOf(i)*Math.max(1,cam.s);ctx.beginPath();ctx.arc(sx,sy,r+3,0,7);ctx.stroke();}}
 if(route&&route.edges){   // recruitment route (chain or shared tree): green edges + dots, green sponsor ring, gold target rings
   ctx.strokeStyle='#34d399';ctx.lineWidth=2.2;ctx.beginPath();
   for(const [u,v] of route.edges){const A=toScreen(LX[u],LY[u]),Bp=toScreen(LX[v],LY[v]);ctx.moveTo(A[0],A[1]);ctx.lineTo(Bp[0],Bp[1]);}
   ctx.stroke();ctx.fillStyle='#34d399';
   for(const i of route.nodes){const [sx,sy]=toScreen(LX[i],LY[i]);ctx.beginPath();ctx.arc(sx,sy,3.5,0,7);ctx.fill();}
   const ring=(idx,col)=>{const [sx,sy]=toScreen(LX[idx],LY[idx]);ctx.strokeStyle=col;ctx.lineWidth=2;ctx.beginPath();ctx.arc(sx,sy,7,0,7);ctx.stroke();};
   if(route.seed!=null)ring(route.seed,'#16a34a');for(const t of (route.targets||[]))ring(t,'#fbbf24');
 }
 if(dropped.size){ctx.strokeStyle='#ef4444';ctx.lineWidth=2;for(const i of dropped){const [sx,sy]=toScreen(LX[i],LY[i]);ctx.beginPath();ctx.moveTo(sx-5,sy-5);ctx.lineTo(sx+5,sy+5);ctx.moveTo(sx+5,sy-5);ctx.lineTo(sx-5,sy+5);ctx.stroke();}}
 if(layout==='committee'&&DATA.comms){ctx.save();ctx.textAlign='center';ctx.textBaseline='middle';ctx.font='700 13px system-ui,Segoe UI,sans-serif';
   for(const c of DATA.comms){const [lx,ly]=toScreen(c[1],c[2]);ctx.lineWidth=3.5;ctx.strokeStyle='rgba(13,17,23,0.85)';ctx.fillStyle='rgba(255,255,255,0.96)';
     ctx.strokeText(c[0],lx,ly);ctx.fillText(c[0],lx,ly);}ctx.restore();}
}
// interaction
cv.addEventListener('mousemove',e=>{
 const r=cv.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top;
 if(drag){cam.tx+=mx-drag.x;cam.ty+=my-drag.y;drag.x=mx;drag.y=my;panMoved=true;draw();return;}
 let best=-1,bd=99;for(let i=0;i<N;i++){const [sx,sy]=toScreen(LX[i],LY[i]);const d=Math.hypot(sx-mx,sy-my);if(d<Math.max(6,radOf(i)+3)&&d<bd){bd=d;best=i;}}
 hi=best;const tip=document.getElementById('tip');
 if(best>=0){const i=best,a=allocOf(i);const pl=PLAYLBL[DATA.play[i]];
  tip.style.display='block';tip.style.left=Math.min(e.clientX+14,innerWidth-260)+'px';tip.style.top=(e.clientY+14)+'px';
  tip.innerHTML=`<b>${DATA.name[i]}</b> (${DATA.party[i]}) · rank ${DATA.rank[i]} · <b>${DATA.bp[i]}%</b> bipartisan · conf <b>${DATA.cf?DATA.cf[i]:'-'}</b><br>On <b>${DATA.issues[issue]}</b>: <b style=color:${STCOL[DATA.stance[i][issue]]}>${SC[DATA.stance[i][issue]]}</b><br>Overall: ${SC[DATA.gen[i]]} · electoral: <b style=color:${ELCOL[DATA.play[i]]}>${pl}</b><br>${mode==='coal'?'Coalition seed':'Flip target'}: <b>${a?(mode==='coal'?'enters @ $'+a+'k':'$'+a+'k'):'—'}</b>`;}
 else tip.style.display='none';
 draw();
});
cv.addEventListener('mouseleave',()=>{hi=-1;document.getElementById('tip').style.display='none';draw();});
cv.addEventListener('mousedown',e=>{const r=cv.getBoundingClientRect();drag={x:e.clientX-r.left,y:e.clientY-r.top};panMoved=false;cv.style.cursor='grabbing';});
cv.addEventListener('click',()=>{if(!panMoved&&hi>=0)selectMember(hi);});
addEventListener('mouseup',()=>{drag=null;cv.style.cursor='grab';});
cv.addEventListener('wheel',e=>{e.preventDefault();const r=cv.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top;const f=e.deltaY<0?1.12:0.893;const nx=mx-(mx-cam.tx)*f,ny=my-(my-cam.ty)*f;cam.s*=f;cam.tx=nx;cam.ty=ny;draw();},{passive:false});
// --- touch (mobile): 1-finger pan + tap-to-select, 2-finger pinch-zoom ---
let tdrag=null,pinch=null;
cv.addEventListener('touchstart',e=>{const r=cv.getBoundingClientRect();
 if(e.touches.length===1){const t=e.touches[0];tdrag={x:t.clientX-r.left,y:t.clientY-r.top};panMoved=false;pinch=null;}
 else if(e.touches.length>=2){const a=e.touches[0],b=e.touches[1];pinch={d:Math.hypot(a.clientX-b.clientX,a.clientY-b.clientY),cx:(a.clientX+b.clientX)/2-r.left,cy:(a.clientY+b.clientY)/2-r.top};tdrag=null;}},{passive:true});
cv.addEventListener('touchmove',e=>{e.preventDefault();const r=cv.getBoundingClientRect();
 if(pinch&&e.touches.length>=2){const a=e.touches[0],b=e.touches[1],nd=Math.hypot(a.clientX-b.clientX,a.clientY-b.clientY),cx=(a.clientX+b.clientX)/2-r.left,cy=(a.clientY+b.clientY)/2-r.top,f=nd/(pinch.d||nd);
  cam.tx+=cx-pinch.cx;cam.ty+=cy-pinch.cy;cam.tx=cx-(cx-cam.tx)*f;cam.ty=cy-(cy-cam.ty)*f;cam.s*=f;pinch={d:nd,cx:cx,cy:cy};panMoved=true;draw();}
 else if(tdrag&&e.touches.length===1){const t=e.touches[0],mx=t.clientX-r.left,my=t.clientY-r.top;cam.tx+=mx-tdrag.x;cam.ty+=my-tdrag.y;tdrag.x=mx;tdrag.y=my;panMoved=true;draw();}},{passive:false});
cv.addEventListener('touchend',e=>{if(e.touches.length===0){if(tdrag&&!panMoved){const mx=tdrag.x,my=tdrag.y;let best=-1,bd=99;for(let i=0;i<N;i++){const [sx,sy]=toScreen(LX[i],LY[i]);const d=Math.hypot(sx-mx,sy-my);if(d<Math.max(12,radOf(i)+8)&&d<bd){bd=d;best=i;}}if(best>=0){selectMember(best);if(window.innerWidth<=640){const rp=document.getElementById('right');if(rp)setTimeout(function(){rp.scrollIntoView({behavior:'smooth',block:'start'});},70);}}}tdrag=null;pinch=null;}},{passive:true});
function flyTo(i){cam.s=2.4;cam.tx=W/2-LX[i]*cam.s;cam.ty=H/2-LY[i]*cam.s;draw();}
// ============ LIVE SCENARIO/PATHFINDER ENGINE (faithful port of flip_model + competitive cascade + lt_priming) ============
const EG=DATA.engine,K=EG.const,BPF=EG.bpf,PTY=DATA.party;
const ADJ=Array.from({length:N},()=>({}));for(const [u,v,w] of EG.adj){ADJ[u][v]=w;ADJ[v][u]=w;}
function cpf(u,v){return (PTY[u]!==PTY[v]&&'DR'.indexOf(PTY[u])>=0&&'DR'.indexOf(PTY[v])>=0)?(K.DCROSS+(1-K.DCROSS)*Math.sqrt(BPF[u]*BPF[v])):1;}   // CALIBRATED: cross-party DIFFUSION damped 0.4-1.0x (homophily: Harmon; Andris; cross<within)
function align(u,v){if(PTY[u]===PTY[v]&&'DR'.indexOf(PTY[u])>=0)return K.SRCPRO;if(PTY[u]!==PTY[v]&&'DR'.indexOf(PTY[u])>=0&&'DR'.indexOf(PTY[v])>=0)return K.SRCANTI;return 1;}   // SOURCE-ALIGNMENT for persuasion: co-partisan x1.7 / out x0.5 (Furnas/Bakker)
const PE=Array.from({length:N},()=>({}));for(let u=0;u<N;u++)for(const v in ADJ[u]){const wc=ADJ[u][v]*cpf(u,+v);PE[u][v]=wc/(wc+6);}
const SCN={C:'Champion',F:'Defender',A:'Ally',H:'Highly Persuadable',T:'True Neutral',L:'Lean Skeptic',N:'Neutral',S:'Skeptic',O:'Opponent','-':'—'};
const CAMP=t=>('CFA'.indexOf(t)>=0?'pro':'OS'.indexOf(t)>=0?'anti':'neu');
const PERS=EG.pers,THETA=EG.theta;
function baseTiers(i){const t=new Array(N);for(let u=0;u<N;u++)t[u]=DATA.stance[u][i];return t;}
function flipModel(i,tiers,cu,ind){
  const nA=new Float64Array(N),nB=new Float64Array(N);
  for(let u=0;u<N;u++){let a=0,b=0;const nb=ADJ[u];for(const v in nb){const c=CAMP(tiers[v]);if(c==='neu')continue;const wc=nb[v]*align(u,+v);if(c==='pro')a+=wc;else b+=wc;}nA[u]=a;nB[u]=b;}   // persuasion proximity uses SOURCE-ALIGNMENT
  let mA=1,mB=1;for(let u=0;u<N;u++){if(nA[u]>mA)mA=nA[u];if(nB[u]>mB)mB=nB[u];}
  const eng=EG.eng[i];let total=0;const pf=new Float64Array(N),tg=new Float64Array(N);
  for(let u=0;u<N;u++){const a=K.WM*(cu[u]+1)/((cu[u]+1)+K.HALFF*EG.rcp[u])+K.WP*nA[u]/mA;const b=K.WM*(ind[u]+1)/((ind[u]+1)+K.HALFF*EG.rcp[u])+K.WP*nB[u]/mB;const p=(a+b)>0?a/(a+b):0;pf[u]=p;tg[u]=(eng[u]+K.BASE*EG.sco[u]/K.smax)*(PERS[SCN[tiers[u]]]||0)*(1+0.3*BPF[u]);total+=tg[u]*p;}   // +PASSAGE bonus (Volden-Wiseman)
  return {pf,tg,nA,nB,mA,mB,total};
}
function pflipOf(u,nAu,nBu,mA,mB,cu,ind){const a=K.WM*(cu+1)/((cu+1)+K.HALFF*EG.rcp[u])+K.WP*nAu/mA;const b=K.WM*(ind+1)/((ind+1)+K.HALFF*EG.rcp[u])+K.WP*nBu/mB;return (a+b)>0?a/(a+b):0;}
function shiftLean(u,dollars){const r=dollars/EG.rcp[u];return K.MAXSHIFT*(r/(r+K.HALF));}
function dollarsForUnits(u,units){units=Math.min(units,0.98);return K.HALF*EG.rcp[u]*units/(1-units);}
function prime(v,i){   // lt_priming: cheapest pressure+money to flip member v on issue i
  const code=DATA.stance[v][i],tier=SCN[code];
  if(!(tier in THETA)||CAMP(code)==='pro')return null;
  const theta=THETA[tier]+Math.max(0,-(EG.nlraw[v])/120);
  let pressure=0;const cand=[];
  for(const u in PE[v]){const c=CAMP(DATA.stance[+u][i]);if(c==='pro')pressure+=PE[v][u];else if(c!=='anti')cand.push([+u,PE[v][u]]);}
  const gap=theta-pressure;
  if(gap<=1e-6)return {tier,theta,pressure,gap,money:0,recruits:[]};
  const cap=Math.min(0.97,gap),avg=dollarsForUnits(v,cap)/cap;
  cand.sort((a,b)=>(K.CEDGE/Math.max(0.1,a[1]))/a[1]-(K.CEDGE/Math.max(0.1,b[1]))/b[1]);
  let got=0;const recruits=[];for(const [u,add] of cand){if(got>=gap)break;if((K.CEDGE/Math.max(0.1,add))/add<avg){got+=add;recruits.push(u);}}
  const resid=Math.max(0,gap-got);if(resid>0.97)return {tier,theta,pressure,gap,money:null,recruits};
  return {tier,theta,pressure,gap,money:resid>1e-6?Math.round(dollarsForUnits(v,resid)):0,recruits};
}
function cheapestFlips(i,n){   // batch: cheapest members to tip into co-sponsoring on issue i (lt_priming, sorted by $)
  const out=[];for(let v=0;v<N;v++){const r=prime(v,i);if(r&&r.money!==null&&(r.money>0||r.recruits.length>0))out.push([v,r.money||0,r.recruits.length]);}
  out.sort((a,b)=>a[1]-b[1]);return out.slice(0,n);
}
function sm(n){var lo=n>>>0,hi=(n/4294967296)>>>0,h=Math.imul(lo^hi,2654435761)>>>0;h=Math.imul(h^(h>>>15),2246822519)>>>0;h=Math.imul(h^(h>>>13),3266489917)>>>0;h^=h>>>16;return (h>>>0)/4294967296;}   // deterministic integer hash -> [0,1); plain 32-bit math (keys fit in 2^53)
const NMb=N;
function spread(tiers,ind){   // competitive cascade, edge-keyed CRN; SHOCKS (Noble-Turner 2024 going public): the exec cue is
  // PARTY-ASYMMETRIC and ISSUE-DEPENDENT, not a flat dial.  Per-issue regime mixture EG.sal[issue]: P(rally)=p,
  // P(retreat)=q, P(backfire)=b, estimated from the D-R stance gap z.  Co-partisans of the exec always respond MORE
  // (beta_co > beta_out); on polarized issues (q high) an exec SUPPORT cue makes out-party bystanders COUNTER-mobilize
  // (Lee 2009 partisan retreat) and an OPPOSE cue demobilizes them.  Old flat 1.6/0.6 = the special case p=1,q=b=0.
  const sal=(EG.sal&&EG.sal[issue])||{p:.6,q:.3,b:.1};
  const efm=u=>{const co=PTY[u]===(K.EXECP||'R');
    if(execMode==='oppose') return co?1+0.8*(sal.p+sal.q):Math.max(0.2,1+0.8*(sal.p-sal.q-sal.b));
    if(execMode==='support')return co?Math.max(0.2,1-0.7*(sal.p+sal.q)):Math.max(0.2,1-0.7*(sal.p-sal.q-sal.b));
    return 1;};
  const A=[],anti=[];for(let u=0;u<N;u++){if(dropped.has(u))continue;const c=CAMP(tiers[u]);if(c==='pro')A.push(u);else if(c==='anti')anti.push(u);}
  let tot=0;
  for(let it=0;it<K.MC;it++){
    const B=anti.slice(),bk=(700000000+it)*NMb;
    for(let u=0;u<N;u++)if(!dropped.has(u)&&CAMP(tiers[u])==='neu'&&sm(bk+u)<Math.min(0.95,(ind[u]||0)*efm(u)/K.BSCALE))B.push(u);
    const col=new Int8Array(N);for(const dz of dropped)col[dz]=3;for(const s of A)col[s]=1;for(const s of B)col[s]=2;
    let fr=[];for(const s of A)fr.push(s*2);for(const s of B)fr.push(s*2+1);
    const itb=it*NMb*NMb;
    while(fr.length){const nf=[];for(const e of fr){const u=e>>1,c=(e&1)?2:1;const ub=u*NMb;for(const v in PE[u]){if(col[v]===0&&sm(itb+ub+(+v))<PE[u][v]){col[v]=c;nf.push((+v)*2+(c-1));}}}fr=nf;}
    for(let k=0;k<N;k++)if(col[k]===1)tot++;
  }
  return tot/K.MC;
}
// ---- multi-objective co-sponsor pathfinder (RELINK-style): grow a recruitment TREE from ONE seed that
// maximizes co-sponsor spread (recruitability x onward reach) while steering toward a key persuadable target ----
const DEG=PE.map(o=>Object.keys(o).length);let route=null,dropped=new Set(),execMode='none';
function distToTarget(t){const d=new Float64Array(N);d[t]=1;const done=new Uint8Array(N);while(true){let u=-1,bu=0;for(let k=0;k<N;k++)if(!done[k]&&d[k]>bu){bu=d[k];u=k;}if(u<0)break;done[u]=1;for(const v in PE[u]){const np=d[u]*PE[u][v];if(np>d[+v])d[+v]=np;}}return d;}   // max-product proximity to target
// PROVABLY-OPTIMAL recruitment chain: max-product path = the single MOST-RELIABLE chain (Dijkstra on -log p).
// Reliability = product of per-ask success probs = P(the whole chain holds). This is the "mathematical certainty":
// not a guarantee the bill passes, but the exact, maximal probability of the optimal recruitment route.
// Grounded in Sotoudeh-Porter-Krishnagopal (cosponsorship *influence*, not count, drives passage) + reliability theory.
function tracePath(sponsor,target,dT){const path=[sponsor],seen=new Set([sponsor]);let cur=sponsor,g=0;while(cur!==target&&g++<N){let nx=-1,bn=-1;for(const v in PE[cur]){const vi=+v;if(seen.has(vi)||dropped.has(vi))continue;const sc=PE[cur][v]*dT[vi];if(sc>bn){bn=sc;nx=vi;}}if(nx<0)break;path.push(nx);seen.add(nx);cur=nx;}return {path,reached:cur===target};}
// FEC-realistic recruitment cost: a PAC -> candidate is capped at ~$5k/election ($10k/cycle); harder asks cost
// MORE relationship/information (Furnas et al.: money is capped, info is the lever) but the DOLLARS never exceed
// the legal ceiling. So difficulty shows up in RELIABILITY, not in a $100k check. cost in [$1k, $10k].
function recruitCost(p){return Math.round(1000+9000*(1-Math.max(0,Math.min(1,p))));}
function pathReliability(path){let p=1;for(let k=1;k<path.length;k++)p*=PE[path[k-1]][path[k]];return p;}   // passive-diffusion product (used only for RANKING paths)
// ACTIVE-recruitment ask success: a deliberate, FUNDED ask that leverages an existing cosponsorship tie lands far
// more often than spontaneous diffusion (cosponsoring is low-risk — Fowler; reciprocity — Bratton-Rouse). ~14x the passive odds.
const ASKM=0.07;
function activeP(p){return p/(p+(1-p)*ASKM);}
function chainWeak(path){let w=1;for(let k=1;k<path.length;k++)w=Math.min(w,activeP(PE[path[k-1]][path[k]]));return w;}   // the bottleneck ask (removed chainConf geomean -- it was the flattering, non-probabilistic number)
function chainHold(path){let p=1;for(let k=1;k<path.length;k++)p*=activeP(PE[path[k-1]][path[k]]);return p;}   // HONEST whole-chain: P(every ask lands first-try, no reroute) -- a conservative floor (rerouting only improves it)
function pathCost(path){let t=0;for(let k=1;k<path.length;k++)t+=recruitCost(PE[path[k-1]][path[k]]);return t;}
function buildPath(sponsor,target){
  const dT=distToTarget(target),{path,reached}=tracePath(sponsor,target,dT),hops=[];let total=0;
  for(let k=1;k<path.length;k++){const p=PE[path[k-1]][path[k]],cost=recruitCost(p);total+=cost;hops.push({cost,p});}
  return {path,hops,total,reached,target,seed:sponsor,rel:pathReliability(path)};
}
// BEST SPONSOR for a target: among members already PRO on the issue (eligible bill introducers), the one whose
// optimal chain to the target is most reliable / cheapest. One Dijkstra (dT), then O(path) per candidate. (Paper 04.)
function bestSponsors(target,n){
  const dT=distToTarget(target),out=[];
  for(let u=0;u<N;u++){if(u===target||'CFA'.indexOf(DATA.stance[u][issue])<0)continue;const {path,reached}=tracePath(u,target,dT);if(reached&&path.length>1)out.push({sponsor:u,ch:chainHold(path),cost:pathCost(path),hops:path.length-1,path});}
  out.sort((a,b)=>b.ch-a.ch||a.cost-b.cost);return out.slice(0,n);   // rank by whole-chain hold (active), then cost
}
// MULTI-TARGET: from one sponsor, the union of optimal chains to several targets (shared recruitment tree).
// Grounded in Aref-Neal optimal signed-coalition partition: targets in one coalition share recruitment substrate.
function multiTarget(sponsor,targets){
  const tree=new Set([sponsor]),edges=[],paths=[];let reached=0,total=0;
  for(const t of targets){const dT=distToTarget(t),{path,reached:rc}=tracePath(sponsor,t,dT);if(rc)reached++;paths.push({t,path,reached:rc,rel:pathReliability(path)});
    for(let k=1;k<path.length;k++){tree.add(path[k]);if(!edges.some(e=>e[0]===path[k-1]&&e[1]===path[k])){edges.push([path[k-1],path[k]]);total+=recruitCost(PE[path[k-1]][path[k]]);}}}
  return {tree,edges,paths,reached,n:targets.length,total};
}
// GCOMB-grounded BUDGET-CONSTRAINED recruitment (Manchanda et al., NeurIPS'20): cost-bounded max-coverage greedy.
// Marginal gain counts only NEWLY-covered members (GCOMB locality loc(v,S)=|N(v)\∪N(u)|) so co-located recruits
// aren't redundant; candidates pruned to non-trivial degree (GCOMB pruning). Monotone-submodular coverage -> the
// classic greedy keeps the (1-1/e)≈0.63 guarantee (GCOMB matches it: 0.998 vs greedy 0.99 vs optimal 1.0), no ML
// needed at our scale. cov[v] = prob v is covered = 1-Π(1-p) over selected recruiters; reach = Σ cov.
const meanDeg=DEG.reduce((a,b)=>a+b,0)/N;
function budgetRecruit(sponsor,nSeeds,target){
  const dT=(target!=null&&target>=0)?distToTarget(target):null,cov=new Float64Array(N),sel=[sponsor],inSel=new Uint8Array(N);
  inSel[sponsor]=1;cov[sponsor]=1;for(const v in PE[sponsor])cov[+v]=1-(1-cov[+v])*(1-PE[sponsor][v]);
  while(sel.length<nSeeds){
    let best=-1,bg=1e-9;
    for(let c=0;c<N;c++){if(inSel[c]||DEG[c]<Math.max(1,0.1*meanDeg))continue;
      let g=1-cov[c];for(const v in PE[c])g+=PE[c][v]*(1-cov[+v]);if(dT)g*=(1+2*dT[c]);
      if(g>bg){bg=g;best=c;}}
    if(best<0)break;sel.push(best);inSel[best]=1;cov[best]=1;for(const v in PE[best])cov[+v]=1-(1-cov[+v])*(1-PE[best][v]);
  }
  let reach=0;for(let u=0;u<N;u++)reach+=cov[u];return {sel,reach};
}
function cascadeReach(seedArr){   // influence cascade: seed the recruited chain as co-sponsors, spread through the network vs the opposition
  const S=new Set(seedArr),tiers=baseTiers(issue);
  for(let u=0;u<N;u++){if(CAMP(tiers[u])==='anti')continue;tiers[u]=S.has(u)?'C':'N';}
  return spread(tiers,EG.ind);
}
// ---- member panel + live scenario ----
const cusl=document.getElementById('cusl'),cosl=document.getElementById('cosl');
let baseCache=null,cascStr='';
function cacheBaseline(v){baseCache=[];for(let i=0;i<DATA.issues.length;i++){const m=flipModel(i,baseTiers(i),EG.cu,EG.ind);baseCache.push({nAsel:m.nA[v],nBsel:m.nB[v],mA:m.mA,mB:m.mB,tgsel:m.tg[v],pfbase:m.pf[v]});}}
function selectMember(v){
  sel=v;document.getElementById('tpanel').style.display='none';document.getElementById('mpanel').style.display='block';
  document.getElementById('mname').textContent=DATA.name[v];
  const code=DATA.stance[v][issue],pl=PLAYLBL[DATA.play[v]];
  document.getElementById('mstance').innerHTML=
    `<div class=mrow><span>On ${DATA.issues[issue]}</span><b style=color:${STCOL[code]}>${SC[code]}</b></div>`+
    `<div class=mrow><span>Overall · party</span><b>${SC[DATA.gen[v]]} · ${DATA.party[v]}</b></div>`+
    `<div class=mrow><span>Bipartisan · conf · rank</span><b>${DATA.bp[v]}% · ${DATA.cf[v]} · #${DATA.rank[v]}</b></div>`+
    `<div class=mrow><span>Electoral play</span><b style=color:${ELCOL[DATA.play[v]]}>${pl}</b></div>`;
  cusl.value=0;cosl.value=0;cascStr='';route=null;
  const _sn=document.getElementById('seednm');if(_sn)_sn.textContent=DATA.name[v].split(' ').slice(-1)[0];
  document.getElementById('tgtsearch').value='';document.getElementById('pathout').innerHTML='';
  const _md=document.getElementById('mdlink');_md.href='cu-member-desk.html?m='+encodeURIComponent(DATA.name[v]);_md.innerHTML='▤ Member details <small>· '+DATA.name[v]+'</small>';_md.style.display='block';
  cacheBaseline(v);renderPrime();runScenario();flyTo(v);draw();
}
function renderPrime(){
  const r=prime(sel,issue),el=document.getElementById('mprime');
  if(!r){el.innerHTML=`<span style=color:#6e7681>Already pro / committed on this issue — no flip needed.</span>`;return;}
  if(r.money===null){el.innerHTML=`<b style=color:#f59e0b>Hard to flip</b> on ${DATA.issues[issue]}: gap <b>${r.gap.toFixed(2)}</b> exceeds what pressure+money can close.`;return;}
  const rc=r.recruits.slice(0,6).map(u=>`<span class=recruit data-i=${u}>${DATA.name[u].split(' ').slice(-1)[0]}</span>`).join('');
  el.innerHTML=`Tier <b>${r.tier}</b> · resistance θ <b>${r.theta.toFixed(2)}</b>, current pro-pressure <b>${r.pressure.toFixed(2)}</b> → gap <b>${r.gap.toFixed(2)}</b>.<br>`
   +`Cheapest tip: <b>$${(r.money/1000).toFixed(0)}k</b> CU money${r.recruits.length?` + activate <b>${r.recruits.length}</b> already-pro / neutral neighbors`:''}.`
   +(rc?`<div style=margin-top:5px>recruit: ${rc}</div>`:'');
  el.querySelectorAll('.recruit').forEach(s=>{s.onmouseenter=()=>{hi=+s.dataset.i;draw();};s.onclick=()=>selectMember(+s.dataset.i);});
}
function runScenario(){
  const cu=+cusl.value*1000,co=+cosl.value*1000;
  document.getElementById('culab').textContent='$'+cusl.value+'k';document.getElementById('colab').textContent='$'+cosl.value+'k';
  let dThis=0,dAll=0;
  for(let i=0;i<DATA.issues.length;i++){const c=baseCache[i],pfn=pflipOf(sel,c.nAsel,c.nBsel,c.mA,c.mB,EG.cu[sel]+cu,EG.ind[sel]+co);const d=c.tgsel*(pfn-c.pfbase);dAll+=d;if(i===issue)dThis=d;}
  const lean=shiftLean(sel,cu)-shiftLean(sel,co),defects=Math.abs(lean)>=K.DTHRESH;
  const sg=x=>(x>=0?'up':'down'),ar=x=>(x>=0?'+':'');
  document.getElementById('scout').innerHTML=
    `<div class=mrow><span>Winnability · this issue</span><b class="delta ${sg(dThis)}">${ar(dThis)}${dThis.toFixed(3)}</b></div>`
   +`<div class=mrow><span>Winnability · all 17 issues</span><b class="delta ${sg(dAll)}">${ar(dAll)}${dAll.toFixed(2)}</b></div>`
   +`<div class=mrow><span>Net-lean shift</span><b class="delta ${sg(lean)}">${ar(lean)}${lean.toFixed(1)}</b></div>`
   +(defects?`<div class=defwarn style=margin-top:6px>⚠ crosses defection threshold (${K.DTHRESH}) — overall stance would shift ${lean>0?'toward pro':'toward anti'}.</div>`:'')
   +cascStr;
  // HEAD-TO-HEAD (this issue): CU pull vs industry pull -> flip odds + break-even spend
  const c=baseCache[issue];
  const A=K.WM*(EG.cu[sel]+cu+1)/((EG.cu[sel]+cu+1)+K.HALFF*EG.rcp[sel])+K.WP*c.nAsel/c.mA;
  const Bv=K.WM*(EG.ind[sel]+co+1)/((EG.ind[sel]+co+1)+K.HALFF*EG.rcp[sel])+K.WP*c.nBsel/c.mB;
  const pct=Math.round(100*A/(A+Bv));
  document.getElementById('h2hcu').style.width=pct+'%';document.getElementById('h2hind').style.width=(100-pct)+'%';document.getElementById('h2hpct').textContent=pct+'%';
  const tA=c.pfbase*Bv/(1-c.pfbase),q=(tA-K.WP*c.nAsel/c.mA)/K.WM;let be;
  if(co===0)be='<span style=color:#6e7681>add competitor $ to see the CU break-even</span>';
  else if(q>=1)be='<b style=color:#f59e0b>CU money alone can’t fully offset</b> $'+(co/1000)+'k of competitor spend here';
  else{const need=Math.max(0,Math.round((q*K.HALFF*EG.rcp[sel]/(1-q))-1-EG.cu[sel]));be='to neutralize $'+(co/1000)+'k competitor → <b>$'+Math.round(need/1000)+'k</b> CU money';}
  document.getElementById('h2hbe').innerHTML=be;
}
const pedges=p=>p.slice(1).map((v,k)=>[p[k],v]);
function runPath(){
  const po=document.getElementById('pathout'),tv=document.getElementById('tgtsearch').value.trim(),last=i=>DATA.name[i].split(' ').slice(-1)[0];
  if(pmodeVal==='best'){   // who should introduce the bill to reach this target? (paper 04)
    const t=DATA.name.indexOf(tv);
    if(t<0){po.innerHTML='<span style=color:#f59e0b>Type the target vote you need, then Build.</span>';route=null;draw();return;}
    const bs=bestSponsors(t,8);
    if(!bs.length){po.innerHTML='<span style=color:#f59e0b>No pro member can reach this target on this issue.</span>';route=null;draw();return;}
    const b0=bs[0];route={edges:pedges(b0.path),nodes:b0.path,seed:b0.sponsor,targets:[t]};
    po.innerHTML=`<div class=mrow><span>Best sponsor → ${last(t)}</span><b>${last(b0.sponsor)}</b></div>`
     +`<div class=mrow><span>Whole chain holds · cost</span><b>${(b0.ch*100).toFixed(0)}% · $${(b0.cost/1000).toFixed(0)}k</b></div>`
     +`<div style=margin-top:6px;font-size:11px;color:#c9d1d9;line-height:1.6>`+bs.map((s,i)=>`<span style=color:#6e7681>${i+1}.</span> <span class=lnk data-i=${s.sponsor} style=cursor:pointer;text-decoration:underline>${DATA.name[s.sponsor]}</span> <span style=color:#8b949e>${(s.ch*100).toFixed(0)}% · $${Math.round(s.cost/1000)}k · ${s.hops}h</span>`).join('<br>')+`</div>`;
    po.querySelectorAll('.lnk').forEach(el=>el.onclick=()=>selectMember(+el.dataset.i));draw();return;
  }
  if(pmodeVal==='budget'){   // GCOMB budget-constrained max-coverage recruitment (diversified set)
    const bk=parseFloat(tv)||0;
    if(bk<=0){po.innerHTML='<span style=color:#f59e0b>Enter a budget in $k (e.g. 300).</span>';route=null;draw();return;}
    const ns=Math.max(2,Math.round(bk*1000/K.CEDGE)),br=budgetRecruit(sel,ns,-1);
    route={edges:[],nodes:br.sel,seed:sel,targets:[]};
    po.innerHTML=`<div class=mrow><span>Budget · recruits</span><b>$${bk}k · ${br.sel.length}</b></div>`
     +`<div class=mrow><span>Expected reach (coverage)</span><b>~${br.reach.toFixed(0)} members</b></div>`
     +`<div style=margin-top:6px;font-size:11px;color:#c9d1d9;line-height:1.6>`+br.sel.slice(1,13).map((v,k)=>`<span style=color:#6e7681>${k+1}.</span> ${DATA.name[v]}`).join('<br>')+(br.sel.length>13?`<br><span style=color:#6e7681>+${br.sel.length-13} more</span>`:'')+`</div>`;
    draw();return;
  }
  if(pmodeVal==='multi'){   // reach several targets from one sponsor (shared tree; paper 06 coalitions)
    const ts=tv.split(',').map(s=>DATA.name.indexOf(s.trim())).filter(i=>i>=0&&i!==sel);
    if(!ts.length){po.innerHTML='<span style=color:#f59e0b>Type targets separated by commas.</span>';route=null;draw();return;}
    const mt=multiTarget(sel,ts);route={edges:mt.edges,nodes:[...mt.tree],seed:sel,targets:ts};
    po.innerHTML=`<div class=mrow><span>Reached</span><b class="delta ${mt.reached===mt.n?'up':'down'}">${mt.reached}/${mt.n} targets</b></div>`
     +`<div class=mrow><span>Shared tree · cost</span><b>${mt.tree.size} members · $${(mt.total/1000).toFixed(0)}k</b></div>`
     +`<div style=margin-top:6px;font-size:11px;color:#c9d1d9;line-height:1.6>`+mt.paths.map(p=>`${DATA.name[p.t]} <span style=color:${p.reached?'#16a34a':'#ef4444'}>${p.reached?(chainHold(p.path)*100).toFixed(0)+'% holds':'unreachable'}</span>`).join('<br>')+`</div>`;
    draw();return;
  }
  // sponsor -> target
  const t=DATA.name.indexOf(tv);
  if(t<0){po.innerHTML='<span style=color:#f59e0b>Type a target member to build the path toward.</span>';route=null;draw();return;}
  if(t===sel){po.innerHTML='<span style=color:#f59e0b>Sponsor and target are the same member.</span>';route=null;draw();return;}
  const r=buildPath(sel,t);r.reach=cascadeReach(r.path);route={edges:pedges(r.path),nodes:r.path,seed:sel,targets:[t]};
  po.innerHTML=`<div class=mrow><span>Path · <b>${r.path.length}</b> members</span><b class="delta ${r.reached?'up':'down'}">${r.reached?'reaches target':'unreachable'}</b></div>`
   +`<div class=mrow><span>Whole chain holds · weakest ask</span><b>${(chainHold(r.path)*100).toFixed(0)}% · ${(chainWeak(r.path)*100).toFixed(0)}%</b></div>`
   +`<div class=mrow><span>Direct recruitment</span><b>$${(r.total/1000).toFixed(0)}k</b></div>`
   +`<div class=mrow><span>Influence cascade</span><b>~${r.reach.toFixed(0)} co-sponsors</b></div>`
   +`<div style=margin-top:7px;font-size:11px;color:#c9d1d9;line-height:1.65>`
   +r.path.map((v,k)=>`<span style=color:#6e7681>${k+1}.</span> ${DATA.name[v]}`+(k===0?' <span style=color:#16a34a>· sponsor</span>':` <span style=color:#8b949e>+$${Math.round(r.hops[k-1].cost/1000)}k · ${(activeP(r.hops[k-1].p)*100).toFixed(0)}% ask</span>`)+(v===t?' <span style=color:#fbbf24>· target</span>':'')).join('<br>')+`</div>`;
  draw();
}
function backToTargets(){sel=-1;route=null;document.getElementById('mpanel').style.display='none';document.getElementById('tpanel').style.display='block';document.getElementById('mdlink').style.display='none';draw();}
function applyShocks(){
  const ds=document.getElementById('dropsearch').value.trim();
  dropped=new Set(ds?ds.split(',').map(x=>DATA.name.indexOf(x.trim())).filter(i=>i>=0):[]);
  let parts=[];
  if(dropped.size)parts.push('<b>'+[...dropped].map(i=>DATA.name[i].split(' ').slice(-1)[0]).join(', ')+'</b> out');
  if(execMode!=='none'){const s=(EG.sal&&EG.sal[issue])||{p:.6,q:.3,b:.1,z:0};
   parts.push('exec <b class="'+(execMode==='oppose'?'down':'up')+'">'+execMode+'s</b> · going-public regime (Noble–Turner): rally '+Math.round(s.p*100)+'% / retreat '+Math.round(s.q*100)+'% / backfire '+Math.round(s.b*100)+'%'+(execMode==='support'&&s.q>s.p?' — <span style=color:#f59e0b>polarized issue: out-party counter-mobilizes</span>':''));
   if(EG.adv&&EG.adv[issue])parts.push('CU advisory: <b>'+EG.adv[issue]+'</b>');}
  document.getElementById('shockout').innerHTML=parts.length?('shock active \u2014 '+parts.join(' \u00b7 ')):'';
  if(sel>=0&&document.getElementById('tgtsearch').value.trim())runPath();
  draw();
}
function updateEngChk(){const r=DATA.engine.refflip[issue];if(!r){document.getElementById('engchk').innerHTML='engine — aggregate layer';return;}const t=flipModel(issue,baseTiers(issue),EG.cu,EG.ind).total,ok=Math.abs(t-r)<=Math.max(0.2,0.03*r);document.getElementById('engchk').innerHTML=`engine ${ok?'✓':'⚠'} flip ${t.toFixed(2)} = py ${r.toFixed(2)}`;}
// panels
function fmt(n){return '$'+Math.round(n).toLocaleString();}
function refresh(){
 const f=DATA.frontier[issue], useSlider=(mode==='coal'&&!!f);
 const st=DATA.stats[issue];
 document.getElementById('istats').innerHTML=
   `<div class=stat><span><span class=pill style=background:${STCOL.C}></span>Champions</span><b>${st.champ}</b></div>`+
   `<div class=stat><span><span class=pill style=background:${STCOL.A}></span>Allies</span><b>${st.ally}</b></div>`+
   `<div class=stat><span><span class=pill style=background:${STCOL.S}></span>Skeptics</span><b>${st.skep}</b></div>`+
   `<div class=stat><span><span class=pill style=background:${STCOL.O}></span>Opponents</span><b>${st.opp}</b></div>`;
 document.getElementById('bhdr').textContent=useSlider?'Budget frontier':(mode==='coal'?'Money deployed':'Money deployed');
 slider.style.display=useSlider?'block':'none';
 document.querySelector('#budgetwrap .frow').style.display=useSlider?'flex':'none';
 if(useSlider){const mx=f.path[f.path.length-1][0];budget=(+slider.value/100)*mx;document.getElementById('bmax').textContent='$'+(mx/1e6).toFixed(1)+'M';}
 computeFund();
 if(useSlider){
   document.getElementById('money').textContent='$'+(budget/1e6).toFixed(2)+'M';
   document.getElementById('mdetail').innerHTML=`coalition spread <b>${f.base.toFixed(0)} → ${SPREAD.toFixed(0)}</b> co-sponsors · <b>${ORD.length}</b> seeds funded · knee $${(f.knee/1000).toFixed(0)}k · drag to set budget`;
 }else if(DATA.engine.refflip[issue]===0){   // Overall = aggregate stance layer; summing every issue's budget is meaningless
   document.getElementById('money').textContent='—';
   document.getElementById('mdetail').innerHTML='aggregate stance view (no single budget) — your <b>$2M total</b> plan is the optimizer card below';
 }else{
   const tot=mode==='coal'?st.coal:st.flip;
   document.getElementById('money').textContent=fmt(tot);
   document.getElementById('mdetail').innerHTML=(mode==='coal'?`competitive cascade · ${st.coalN} seeds (capped $50k)`:`competitive linear-threshold · persuadable targets`)+' <span style=color:#6e7681>· this is your full $2M focused on THIS issue — issues are alternatives, not additive</span>';
 }
 if(rmode==='flip'){
   document.getElementById('tgtmode').textContent='· internal pressure to flip';
   const cf=cheapestFlips(issue,16),tot=cf.reduce((s,r)=>s+r[1],0);flipHi=new Set(cf.map(r=>r[0]));
   document.getElementById('targets').innerHTML=(cf.length?`<div class=hint style=margin-bottom:6px>cheapest tip-ins on this issue · <b style=color:#c9d1d9>$${(tot/1000).toFixed(0)}k</b> to flip ${cf.length}</div>`:'')+cf.map(([v,m,nr])=>
     `<div class=tgt data-i=${v}><span><span class=pill style=background:${STCOL[DATA.stance[v][issue]]}></span>${DATA.name[v]}</span><small>$${Math.round(m/1000)}k${nr?' +'+nr:''}</small></div>`).join('')||'<div class=hint>none primeable with money on this issue</div>';
 }else{
   flipHi=null;
   document.getElementById('tgtmode').textContent='· '+(mode==='coal'?'coalition (entry order)':'flip ($)');
   const arr=ORD.slice(0,16);
   document.getElementById('targets').innerHTML=arr.map(([i,v])=>
     `<div class=tgt data-i=${i}><span><span class=pill style=background:${STCOL[DATA.stance[i][issue]]}></span>${DATA.name[i]}</span><small>${mode==='coal'&&useSlider?'@$'+v+'k':'$'+v+'k'}</small></div>`).join('')||'<div class=hint>no funded targets</div>';
 }
 document.querySelectorAll('.tgt').forEach(el=>el.onclick=()=>selectMember(+el.dataset.i));
 if(sel>=0){cacheBaseline(sel);renderPrime();runScenario();}   // keep member panel in sync with issue/mode
 updateEngChk();
 draw();
}
// optimizer card (static cross-topic CU allocation)
function optCard(){
 const o=DATA.opt;if(!o){document.getElementById('optbody').innerHTML='<div class=hint>not available</div>';return;}
 const top=o.alloc.slice(0,8);
 let h=`<div class=optline>winnability <b>${o.base.toFixed(1)} → ${o.final.toFixed(1)}</b> (<b>+${(o.final-o.base).toFixed(1)}</b> expected flips)</div>`;
 h+=`<div class=optline style=color:#8b949e>$${(o.budget/1e6).toFixed(1)}M across 17 issues · ${o.alloc.length} members${o.conv.length?` · ${o.conv.length} convert`:''}</div>`;
 h+=top.map(([i,v])=>`<div class=oa data-i=${i}><span>${o.conv.includes(i)?'<span class=conv>● </span>':''}${DATA.name[i]}</span><small>$${v}k</small></div>`).join('');
 document.getElementById('optbody').innerHTML=h;
 document.querySelectorAll('.oa').forEach(el=>el.onclick=()=>selectMember(+el.dataset.i));
}
// legend
function legend(){
 let items;
 if(colorBy==='elec')items=[['c','Contest · primary'],['g','Contest · general'],['d','Defend'],['n','No play']].map(([k,lb])=>`<span><span class=pill style=background:${ELCOL[k]}></span>${lb}</span>`).join('');
 else if(colorBy==='party')items=[['D','Democrat'],['R','Republican'],['I','Independent']].map(([k,lb])=>`<span><span class=pill style=background:${PTCOL[k]}></span>${lb}</span>`).join('');
 else items=[['C','Champion'],['A','Ally'],['H','Hi-Persuad'],['P','Persuad'],['G','Lean-Pers'],['T','Neutral'],['L','Lean-Skep'],['S','Skeptic'],['K','Hi-Skeptic'],['O','Opponent']].map(([k,lb])=>`<span><span class=pill style=background:${STCOL[k]}></span>${lb}</span>`).join('');
 document.getElementById('legend').innerHTML=items+'<br><span style=color:#6e7681>○ white ring = funded · size = $ · scroll to zoom, drag to pan</span>';
}
// controls
isel.onchange=()=>{issue=+isel.value;slider.value=100;refresh();};
slider.oninput=()=>refresh();
document.querySelectorAll('#mode button').forEach(b=>b.onclick=()=>{document.querySelectorAll('#mode button').forEach(x=>x.classList.remove('on'));b.classList.add('on');mode=b.dataset.m;refresh();});
document.querySelectorAll('#color button').forEach(b=>b.onclick=()=>{document.querySelectorAll('#color button').forEach(x=>x.classList.remove('on'));b.classList.add('on');colorBy=b.dataset.c;legend();draw();});
// LAYOUT toggle: animate node positions between the cosponsorship layout (DATA.x/y) and the committee-cluster
// layout (DATA.cx/cy, Porter committee-interlock anchors). Members glide into committee clusters.
function setLayout(L){
  if(L===layout||!DATA.cx)return; layout=L;
  document.querySelectorAll('#ltog button').forEach(x=>x.classList.toggle('on',x.dataset.l===L));
  const tx=L==='committee'?DATA.cx:DATA.x, ty=L==='committee'?DATA.cy:DATA.y;
  const x0=LX.slice(), y0=LY.slice(), t0=performance.now(), dur=700;
  (function anim(now){const k=Math.min(1,(now-t0)/dur), e=k<.5?2*k*k:1-Math.pow(-2*k+2,2)/2;
    for(let i=0;i<N;i++){LX[i]=x0[i]+(tx[i]-x0[i])*e; LY[i]=y0[i]+(ty[i]-y0[i])*e;}
    draw(); if(k<1)requestAnimationFrame(anim);})(t0);
}
document.querySelectorAll('#ltog button').forEach(b=>b.onclick=()=>setLayout(b.dataset.l));
document.querySelectorAll('#rtog button').forEach(b=>b.onclick=()=>{document.querySelectorAll('#rtog button').forEach(x=>x.classList.remove('on'));b.classList.add('on');rmode=b.dataset.r;refresh();});
document.getElementById('search').onchange=e=>{const i=DATA.name.indexOf(e.target.value);if(i>=0)selectMember(i);};
cusl.oninput=runScenario;cosl.oninput=runScenario;
document.getElementById('pathbtn').onclick=runPath;
document.getElementById('dropsearch').onchange=applyShocks;
document.querySelectorAll('#execseg button').forEach(b=>b.onclick=()=>{document.querySelectorAll('#execseg button').forEach(x=>x.classList.remove('on'));b.classList.add('on');execMode=b.dataset.e;applyShocks();});
document.getElementById('backbtn').onclick=backToTargets;
document.querySelectorAll('#pmode button').forEach(b=>b.onclick=()=>{document.querySelectorAll('#pmode button').forEach(x=>x.classList.remove('on'));b.classList.add('on');pmodeVal=b.dataset.p;
  const lab=document.getElementById('plabel'),inp=document.getElementById('tgtsearch');
  if(pmodeVal==='best'){lab.textContent='find the best sponsor to reach:';inp.placeholder='target vote…';}
  else if(pmodeVal==='multi'){lab.textContent='reach targets (from this member):';inp.placeholder='target1, target2, …';}
  else if(pmodeVal==='budget'){lab.textContent='budget $k from this member (diversified recruits):';inp.placeholder='e.g. 300';}
  else{lab.innerHTML='bill sponsor <b id=seednm style=color:#16a34a></b> → reach target:';inp.placeholder='target member…';if(sel>=0)document.getElementById('seednm').textContent=DATA.name[sel].split(' ').slice(-1)[0];}
  document.getElementById('pathout').innerHTML='';route=null;draw();});
addEventListener('resize',resize);
legend();optCard();resize();refresh();
</script></body></html>