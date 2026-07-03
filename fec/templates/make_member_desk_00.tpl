<!DOCTYPE html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Moneyball — Member Desk</title>
<style>
:root{--bg:#0d1117;--panel:#11161d;--panel2:#161b22;--line:#21262d;--line2:#30363d;--ink:#e6edf3;--muted:#9098a4;--faint:#7d8694;--blue:#1f6feb;--green:#16a34a}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--ink);font:13px/1.45 -apple-system,Segoe UI,Roboto,sans-serif;-webkit-font-smoothing:antialiased}
.mono{font-variant-numeric:tabular-nums;font-family:ui-monospace,Menlo,Consolas,monospace}
a{color:#58a6ff;text-decoration:none}a:hover{text-decoration:underline}
/* accessibility: visible keyboard focus everywhere */
button,select,input,a,.tgt,.sugg,.chip,summary,tbody tr{outline:none}
button:focus-visible,select:focus-visible,input:focus-visible,a:focus-visible,summary:focus-visible,.chip:focus-visible,tbody tr:focus-visible{outline:2px solid var(--blue);outline-offset:2px;border-radius:4px}
button,select,.chip,summary,.seg button{transition:background .12s,border-color .12s,color .12s}
select:hover,input:hover{border-color:#3d4650}
header{padding:11px 18px;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;gap:18px;flex-wrap:wrap;background:var(--panel)}
.brand .kick{font-size:10px;letter-spacing:.22em;text-transform:uppercase;color:#7fb7a9;font-weight:700}
.brand h1{font-size:16px;font-weight:700}
.topnav{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.seg{display:inline-flex;border:1px solid var(--line2);border-radius:6px;overflow:hidden}
.seg button{background:var(--bg);color:#9ca3af;border:0;padding:6px 12px;cursor:pointer;font-size:12px}
.seg button.on{background:var(--blue);color:#fff;font-weight:600}
.ghostbtn{background:var(--bg);color:#9ca3af;border:1px solid var(--line2);border-radius:6px;padding:6px 11px;cursor:pointer;font-size:12px;display:inline-block}
.ghostbtn:hover{border-color:var(--blue);color:#fff;text-decoration:none}
.netlink{border:1px solid var(--line2);border-radius:6px;padding:6px 11px;font-size:12px;color:#9ca3af}
.view{padding:14px 18px;max-width:1280px;margin:0 auto}
.view[hidden]{display:none}
/* ---- staff directory (2026-07-02) ---- */
.stfcard{border:1px solid var(--line,#2a2f3a);border-radius:10px;padding:8px 10px;margin:6px 0;background:rgba(255,255,255,.02)}
.stfcard.gold{border:2px solid #d4a017;box-shadow:0 0 6px rgba(212,160,23,.45)}
.stfhead{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.stfhead b{font-size:13.5px}
.stftitle{color:var(--faint);font-size:12px}
.stfstar{cursor:pointer;font-size:15px;color:#555;user-select:none}
.stfstar.on{color:#eab308}
.stfmeta{font-size:12px;margin:3px 0;color:var(--faint)}
.stfmeta a{color:inherit}
.stfctl{display:flex;gap:6px;flex-wrap:wrap;margin-top:4px}
.stfctl .mini{font-size:11px;padding:2px 8px;border-radius:6px;border:1px solid var(--line,#2a2f3a);background:transparent;color:var(--faint);cursor:pointer}
.stfctl .mini.on{border-color:#d4a017;color:#d4a017}
.stfnote textarea{width:100%;min-height:44px;margin-top:5px;font-size:12px;background:rgba(0,0,0,.25);color:inherit;border:1px solid var(--line,#2a2f3a);border-radius:6px}
.stfmedia{display:flex;gap:6px;flex-wrap:wrap;margin-top:4px}
.stfmedia .chip{font-size:11px;border:1px solid var(--line,#2a2f3a);border-radius:10px;padding:1px 8px}
.stfmedia .chip .x{cursor:pointer;margin-left:5px;color:var(--faint)}
#contactbody .memgrp{margin:12px 0}
#contactbody .memgrp h3{cursor:pointer;margin:4px 0}
.stfsearch{width:100%;margin:4px 0 6px;padding:5px 8px;font-size:12px;background:rgba(0,0,0,.25);color:inherit;border:1px solid var(--line,#2a2f3a);border-radius:6px}
/* ranked */
.controls{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:10px}
input,select{background:var(--bg);color:var(--ink);border:1px solid var(--line2);border-radius:6px;padding:7px 10px;font-size:13px}
.search{position:relative}.search input{width:240px;padding-left:30px}.search svg{position:absolute;left:9px;top:8px;color:var(--faint)}
.toggle{display:flex;align-items:center;gap:6px;color:var(--muted);font-size:12px}
.chips{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:10px}
.chip{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line2);border-radius:20px;padding:4px 11px;cursor:pointer;font-size:12px;color:#9ca3af}
.chip.on{background:#1b2230;border-color:var(--blue);color:#fff}
.chip .dot{width:8px;height:8px;border-radius:50%}
.countline{color:var(--muted);font-size:12px;margin-bottom:8px;display:flex;justify-content:space-between}
.tablewrap{border:1px solid var(--line);border-radius:10px;overflow-x:auto}
table{width:100%;border-collapse:collapse;min-width:680px}
th{text-align:left;font-size:10px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);padding:9px 12px;border-bottom:1px solid var(--line);background:var(--panel2)}
td{padding:9px 12px;border-bottom:1px solid var(--line);vertical-align:middle}
tr:last-child td{border-bottom:0}
tbody tr{cursor:pointer}tbody tr:hover{background:#161b22}
.num{text-align:right;font-variant-numeric:tabular-nums}
.rk{font-weight:700;font-variant-numeric:tabular-nums}
.nm{font-weight:600}.dist{color:var(--muted);font-size:11px}
.tier{display:inline-flex;align-items:center;gap:6px;border-radius:20px;padding:2px 9px;font-size:11px;font-weight:600}
.tier .d{width:7px;height:7px;border-radius:50%;background:currentColor}
.spark{display:inline-flex;align-items:flex-end;gap:3px;height:24px}
.spark i{width:7px;border-radius:2px 2px 0 0;display:block;min-height:3px}
.scorecell{display:flex;align-items:center;gap:8px}
.sbar{flex:1;height:7px;background:#1b2129;border-radius:4px;overflow:hidden;min-width:60px}
.sbar i{display:block;height:100%;background:linear-gradient(90deg,#1f6feb,#34d399)}
.sval{font-variant-numeric:tabular-nums;font-weight:700;width:38px;text-align:right}
/* member */
.mhead{display:flex;align-items:flex-start;justify-content:space-between;gap:18px;flex-wrap:wrap;margin-bottom:14px}
.mhead h2{font-size:24px;font-weight:800}
.mhead .meta{color:var(--muted);font-size:13px;margin-top:3px}
.verdict{display:inline-flex;align-items:center;gap:7px;border-radius:20px;padding:4px 12px;font-size:12px;font-weight:700;margin-bottom:8px}
.verdict .d{width:8px;height:8px;border-radius:50%;background:currentColor}
.figs{display:flex;gap:10px;flex-wrap:wrap}
.fig{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:11px 15px;min-width:120px}
.fig .v{font-size:21px;font-weight:800;font-variant-numeric:tabular-nums}
.fig .l{color:var(--muted);font-size:11px;margin-top:2px}
.fig.accent .v{color:#34d399}
.gen{display:grid;grid-template-columns:1.3fr 1fr;gap:14px;margin-bottom:14px}
@media(max-width:880px){.gen{grid-template-columns:1fr}}
@media(max-width:640px){
  .view{padding:10px 11px}
  header{padding:9px 11px;gap:9px}h1{font-size:16px}
  .topnav{gap:7px;width:100%}
  .controls{gap:7px}
  .search{flex:1 1 100%}.search input{width:100%}
  .tablewrap{overflow-x:auto;-webkit-overflow-scrolling:touch;width:100%}
  .mhead{gap:10px}.figs{gap:7px}.fig{flex:1 1 calc(50% - 7px);min-width:0;padding:9px 12px}
  button,select,input,.ghostbtn,.seg button{min-height:40px}
  .povsel{min-height:34px}
}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:15px}
.eyebrow{font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);font-weight:700;margin-bottom:10px}
.sec{margin-bottom:12px}
.sec>summary{cursor:pointer;list-style:none;display:flex;align-items:center;justify-content:space-between;
  background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:13px 15px;font-weight:700;font-size:14px}
.sec>summary::-webkit-details-marker{display:none}
.sec[open]>summary{border-radius:12px 12px 0 0;border-bottom:0}
.sec .body{background:var(--panel);border:1px solid var(--line);border-top:0;border-radius:0 0 12px 12px;padding:15px}
.sec .chev{color:var(--faint);font-size:12px;transition:transform .15s}
.sec[open] .chev{transform:rotate(90deg)}
.mrow{display:flex;justify-content:space-between;padding:5px 0;font-size:12.5px;border-bottom:1px solid #1b2129;gap:10px}
.mrow:last-child{border-bottom:0}.mrow b{font-variant-numeric:tabular-nums;color:#fff}
.arealist{max-height:420px;overflow-y:auto}
.arow{display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid #1b2129;font-size:12px}
.arow:last-child{border-bottom:0}
.arow .aname{flex:1;color:#c9d1d9;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.arow .arank{color:var(--muted);font-variant-numeric:tabular-nums;white-space:nowrap;min-width:62px;text-align:right}
.dgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
@media(max-width:560px){.dgrid{grid-template-columns:repeat(2,1fr)}}
.dcell{background:var(--panel2);border:1px solid var(--line);border-radius:9px;padding:10px}
.dcell .v{font-size:16px;font-weight:800;font-variant-numeric:tabular-nums}.dcell .l{color:var(--muted);font-size:11px;margin-top:3px}
.bars{display:flex;flex-direction:column;gap:6px}
.barrow{display:grid;grid-template-columns:150px 1fr 46px;align-items:center;gap:9px;font-size:12px}
.barrow .t{color:#c9d1d9;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.barrow .track{height:8px;background:#1b2129;border-radius:4px;overflow:hidden}
.barrow .track i{display:block;height:100%}
.barrow .val{text-align:right;font-variant-numeric:tabular-nums;color:#fff}
.areasel{display:flex;gap:8px;align-items:center;margin-bottom:11px;flex-wrap:wrap}
.partner{display:grid;grid-template-columns:1fr 70px 1fr;align-items:center;gap:9px;font-size:12px;padding:4px 0;cursor:pointer;border-bottom:1px solid #1b2129}
.partner:hover{background:#161b22}.partner .pn{font-weight:600}
.ev{border:1px solid var(--line);border-radius:10px;padding:11px 13px;margin-bottom:9px;border-left:3px solid var(--faint)}
.ev[data-pol="1"]{border-left-color:#34d399}.ev[data-pol="-1"]{border-left-color:#ef4444}.ev[data-pol="0"]{border-left-color:#9ca3af}
.ev-top{display:flex;justify-content:space-between;font-size:11px;color:var(--muted);margin-bottom:4px;gap:8px}
.ev-title{font-weight:600;display:block;margin-bottom:3px}
.ev-sig,.ev-note{font-size:11.5px;color:var(--muted);margin-top:3px}
.ev-basis{color:var(--faint)}
.cnt{color:var(--muted);font-size:11px;margin-bottom:8px}
.billrow{border:1px solid var(--line);border-radius:9px;padding:10px 12px;margin-bottom:8px}
.billtop{display:flex;align-items:center;gap:9px;margin-bottom:3px}
.rolebadge{font-size:9.5px;font-weight:700;border-radius:5px;padding:2px 7px;text-transform:uppercase;letter-spacing:.03em}
.billno{font-weight:700;font-variant-numeric:tabular-nums}
.billcong{color:var(--faint);font-size:11px;margin-left:auto}
.billtitle{font-weight:600;font-size:13px;margin-bottom:3px}
.billmeta{color:var(--muted);font-size:11.5px}
.billsum{color:var(--muted);font-size:11.5px;margin-top:5px;line-height:1.5}
.empty{color:var(--faint);font-size:12.5px;padding:6px 0;font-style:italic}
.notebox{width:100%;min-height:90px;background:var(--bg);color:var(--ink);border:1px solid var(--line2);border-radius:8px;padding:10px;font:13px/1.5 inherit;resize:vertical}
.filelist{display:flex;flex-direction:column;gap:5px;margin:8px 0}
.fileitem{display:flex;justify-content:space-between;align-items:center;background:var(--panel2);border:1px solid var(--line);border-radius:7px;padding:6px 10px;font-size:12px}
.btn{background:var(--blue);color:#fff;border:0;border-radius:6px;padding:7px 13px;cursor:pointer;font-size:12px;margin-top:8px;margin-right:6px}
.btn.ghost{background:var(--bg);color:#9ca3af;border:1px solid var(--line2)}
.del{color:#f87171;cursor:pointer;font-size:11px}
.savednote{white-space:pre-wrap;font-size:13px;line-height:1.55;color:#c9d1d9}
.backbtn{background:var(--bg);color:#9ca3af;border:1px solid var(--line2);border-radius:6px;padding:6px 11px;cursor:pointer;font-size:12px}
/* coalition builder */
.cbgrid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:880px){.cbgrid{grid-template-columns:1fr}}
.coalchip{display:inline-flex;align-items:center;gap:7px;background:#1b2230;border:1px solid var(--line2);border-radius:20px;padding:4px 8px 4px 11px;margin:3px;font-size:12px}
.coalchip .x{cursor:pointer;color:#f87171;font-weight:700}
.sugg{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:7px 9px;border-radius:8px;cursor:pointer;font-size:12.5px;border-bottom:1px solid #1b2129}
.sugg:hover{background:#161b22}.sugg .add{color:#34d399;font-weight:700}
.legendrow{display:flex;gap:14px;flex-wrap:wrap;font-size:11px;color:var(--muted);margin-top:8px}
.legendrow span{display:inline-flex;align-items:center;gap:5px}
.pdot{width:9px;height:9px;border-radius:50%}
/* investment efficiency */
.methnote{margin:-2px 0 12px;max-width:760px}
.methnote>summary{cursor:pointer;list-style:none;color:var(--blue);font-size:12px;display:inline-flex;align-items:center;gap:5px}
.methnote>summary::-webkit-details-marker{display:none}
.methnote>summary::before{content:'ⓘ';font-size:11px}
.methnote[open]>summary{margin-bottom:6px}
.methbody{font-size:11.5px;color:var(--muted);line-height:1.7;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px 12px}
.effcell{display:flex;align-items:center;gap:8px}
.effval{font-variant-numeric:tabular-nums;font-weight:700;width:42px;text-align:right}
.effbar{position:relative;height:8px;background:#1b2129;border-radius:4px;flex:1;min-width:70px}
.effbar .effmid{position:absolute;left:50%;top:-1px;bottom:-1px;width:1px;background:#30363d}
.effbar i{position:absolute;top:0;bottom:0;display:block;border-radius:3px}
/* engagement tracker */
.trackgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
@media(max-width:640px){.trackgrid{grid-template-columns:1fr}}
.trackgrid label{display:flex;flex-direction:column;gap:4px;font-size:11px;color:var(--muted)}
.trackgrid input,.trackgrid select{font-size:13px;color:var(--ink)}
/* print / PDF: just the member one-pager, ink-friendly */
@media print{
  header,#view-ranked,#view-efficiency,#view-coalition,#backbtn,#printbtn,.netlink,#app-network{display:none!important}
  html,body{background:#fff!important;color:#000!important}
  .view{max-width:none;margin:0;padding:0}
  details.sec>.body{display:block!important}
  .sec[open]>summary,.sec>summary{border:1px solid #ccc!important}
  .card,.sec>summary,.sec .body,.fig,.dcell,.billrow,.ev,.notebox,input,select{background:#fff!important;color:#000!important;border-color:#ccc!important;box-shadow:none!important}
  .eyebrow,.nm,.dist,.meta,.l,.billmeta,.billsum,.ev-top,.ev-basis,.cnt,.mrow span,.trackgrid label{color:#333!important}
  h2,.nm,.billtitle,.dcell .v,.fig .v,b{color:#000!important}
  a{color:#000!important;text-decoration:none}
  svg text{fill:#333!important} svg path[stroke="#1f2630"],svg line{stroke:#ccc!important}
}
.ev-ov{display:flex;align-items:center;gap:8px;margin-top:7px;flex-wrap:wrap}
.ovlabel{font-size:11px;color:var(--faint)}
.povsel{font-size:11px;padding:2px 7px;border-radius:6px;background:#161b22;color:#e6edf3;border:1px solid #30363d;cursor:pointer}
.ovtag{font-size:10px;font-weight:600;padding:2px 8px;border-radius:999px;letter-spacing:.02em}
</style></head><body>
<header>
  <div class=brand><div class=kick>Advocacy Allocation Model</div><h1>Moneyball — Member Desk</h1></div>
  <div class=topnav>
    <span class=seg id=viewseg><button data-v=ranked class=on>Ranked list</button><button data-v=efficiency>Investment efficiency</button><button data-v=coalition>Coalition builder</button><button data-v=contact>In contact</button></span>
    <a class=netlink href="Moneyball Dashboard.html">◀ Network view</a>
    <button class=ghostbtn id=exportbtn>⭳ Export notes</button>
    <label class=ghostbtn for=importfile>⭱ Import notes</label><input id=importfile type=file accept="application/json,.json" hidden>
    <button class=ghostbtn id=povexport title="Download your manual article-stance calls (press_overrides_from_dashboard.json). Apply with: python fec/apply_press_overrides.py">⭳ Export stance overrides</button>
    <label class=ghostbtn for=povimport>⭱ Import overrides</label><input id=povimport type=file accept="application/json,.json" hidden>
    <span id=povhint style="color:var(--faint);font-size:11px"></span>
  </div>
</header>

<section id=view-ranked class=view>
  <div class=controls>
    <div class=search><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="11" cy="11" r="7"></circle><path d="m21 21-4.3-4.3"></path></svg><input id=q placeholder="Search member or district…" autocomplete=off></div>
    <span class=seg id=chamber><button data-v=all class=on>All</button><button data-v=House>House</button><button data-v=Senate>Senate</button></span>
    <select id=area><option value="">All legislative areas</option></select>
    <select id=stancefilter><option value="">All stances</option></select>
    <select id=sort><option value=rank>Sort: Rank</option><option value=score>Sort: Score</option><option value=invested>Sort: Invested ($)</option><option value=name>Sort: Name</option></select>
    <label class=toggle><input type=checkbox id=fundedOnly> Funded only</label>
  </div>
  <div class=countline><span id=count></span><span id=stancehint style=color:var(--faint)>Click any member for the full profile</span></div>
  <div class=tablewrap><table><thead><tr>
    <th class=num style=width:54px>Rank</th><th>Member</th><th style=width:170px id=th-stance>Stance</th>
    <th style=width:96px id=th-profile>Profile</th><th style=width:150px id=th-score>Score</th>
  </tr></thead><tbody id=rows></tbody></table></div>
</section>

<section id=view-member class=view hidden><div id=memberbody></div></section>
<section id=view-contact class=view hidden><div id=contactbody></div></section>

<section id=view-coalition class=view hidden>
  <h2 style=font-size:20px;font-weight:800;margin-bottom:4px>Coalition builder</h2>
  <div style=color:var(--muted);margin-bottom:12px>Add cosponsors to a bill, then the cosponsorship network suggests the most likely next cosponsors (propagation probability to your current set). Bias the search toward a legislative area if you like.</div>
  <div class=areasel>
    <div class=search><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="11" cy="11" r="7"></circle><path d="m21 21-4.3-4.3"></path></svg><input id=cbsearch placeholder="Add a cosponsor…" list=allnames autocomplete=off></div>
    <datalist id=allnames></datalist>
    <select id=cbarea><option value="">No area bias</option></select>
    <button class=ghostbtn id=cbclear>Clear</button>
  </div>
  <div class=cbgrid>
    <div class=card><div class=eyebrow>Bill cosponsors <span id=cbcount style=color:var(--faint)></span></div><div id=cblist></div><div id=cbstats style=margin-top:10px></div>
      <button class=btn id=cbnet style=display:none>View coalition in network ↗</button></div>
    <div class=card><div class=eyebrow>Suggested next cosponsors</div><div id=cbsugg></div></div>
  </div>
</section>

<section id=view-efficiency class=view hidden>
  <h2 style=font-size:20px;font-weight:800;margin-bottom:4px>Investment efficiency</h2>
  <div style=color:var(--muted);margin-bottom:10px;max-width:760px>Where the next credit-union dollar moves the most. Sorted by <b style=color:#34d399>ROI</b> — expected co-sponsors gained from the next $10k.</div>
  <details class=methnote><summary>How these are computed</summary><div class=methbody>
    <b style=color:#34d399>ROI</b> — expected flips from the next $10k (one PAC's cycle max), from the capacity- &amp; competition-aware Linear-Threshold flip model. The rigorous metric: it rewards genuinely <i>movable</i> targets.<br>
    <b>Suggested</b> — the Golovin–Krause adaptive-submodular optimizer's allocation. <b>Gap</b> = suggested − already invested (FEC).<br>
    <b>Value</b> — influence-percentile − spend-percentile: a quick "undervalued" triage heuristic (ordinal; ignores winnability, so it can disagree with ROI).</div></details>
  <div class=controls>
    <div class=search><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="11" cy="11" r="7"></circle><path d="m21 21-4.3-4.3"></path></svg><input id=effq placeholder="Search member…" autocomplete=off></div>
    <span class=seg id=effch><button data-v=all class=on>All</button><button data-v=House>House</button><button data-v=Senate>Senate</button></span>
    <select id=effsort>
      <option value=roi>Sort: ROI · flips per $10k</option>
      <option value=value>Sort: Undervalued (value)</option>
      <option value=gap>Sort: Funding gap</option>
      <option value=invested>Sort: Invested (high→low)</option>
      <option value=rank>Sort: Overall rank</option>
    </select>
  </div>
  <div class=countline><span id=effcount></span><span style=color:var(--faint)>Click any member for the full profile</span></div>
  <div class=tablewrap><table><thead><tr>
    <th class=num style=width:50px>Rank</th><th>Member</th>
    <th class=num style=width:82px>Invested</th><th class=num style=width:88px>Suggested</th>
    <th class=num style=width:82px>Gap</th><th class=num style=width:58px>Value</th>
    <th style=width:160px>ROI · flips / $10k</th>
  </tr></thead><tbody id=effrows></tbody></table></div>
</section>

<script>
const D=__BUNDLE__;
const M=D.members, CATS=D.cats, DEF=new Set(D.defensive), COAL=D.coalitions, WT=D.weights;
const EXTRA=D.art_extra_cats, DEMO_AXES=D.demo_axes;
const byName={}; M.forEach((m,i)=>byName[m.name]=i);
// cosponsor adjacency for builder
const ADJ={}; D.adj.forEach(([a,b,w])=>{(ADJ[a]=ADJ[a]||[]).push([b,w]);(ADJ[b]=ADJ[b]||[]).push([a,w]);});
const PE=w=>w/(w+6);
const STCOL={C:'#16a34a',F:'#2dd4bf',A:'#86efac',H:'#38bdf8',P:'#7dd3fc',G:'#bae6fd',T:'#9ca3af',N:'#8b949e',L:'#fde3c0',S:'#f59e0b',K:'#f97316',O:'#ef4444','-':'#3a414b'};
const PTCOL={Democrat:'#3b82f6',Republican:'#ef4444',Independent:'#a855f7','':'#6b7280'};
const PILL={press:{c:'#2f6f9f',l:'Press',w:WT.press},comm:{c:'#8458ae',l:'Committee',w:WT.comm},leg:{c:'#0e7c66',l:'Legislative',w:WT.leg},demo:{c:'#c2862a',l:'Demographic',w:WT.demo}};
const $=s=>document.querySelector(s);
const money=n=>(n&&n>0)?'$'+Math.round(n).toLocaleString():'—';
const f2=v=>v==null?'—':Number(v).toFixed(2);
const f3=v=>v==null?'—':Number(v).toFixed(3);
const pc=v=>v==null?'—':Number(v).toFixed(1)+'%';
const n0=n=>n==null?'—':Number(n).toLocaleString();
const last=n=>n.split(' ').slice(-1)[0];
/* ---- stance system (Champion..Opponent), per legislative area ---- */
const STANCE_ORDER=['C','F','A','H','P','G','T','N','L','S','K','O'];      // champion -> opponent (symmetric middle)
const POSTURE={C:'activate',F:'reinforce',A:'reinforce',H:'persuade',P:'persuade',G:'nurture',T:'qualify',N:'qualify',L:'monitor',S:'defend',K:'defend',O:'defend / avoid','-':'qualify'};
const stanceName=t=>(D.tiername&&D.tiername[t])||'—';
function stanceAt(m,area){ if(!area) return m.overall_stance||'-'; const i=CATS.indexOf(area); return (i>=0&&m.stances)?(m.stances[i]||'-'):'-'; }
function stanceBadge(t){const col=STCOL[t]||'#6b7280';return `<span class=tier style="color:${col};background:${col}1A"><span class=d></span>${stanceName(t)}</span>`;}

/* ---------- manual notes: localStorage + baked-in fold-in ---------- */
const LSKEY='mdesk_manual_v1';
let MAN={}; try{MAN=JSON.parse(localStorage.getItem(LSKEY))||{}}catch(e){MAN={}}
function saveMAN(){localStorage.setItem(LSKEY,JSON.stringify(MAN));}
function manField(name,field,baked){const o=MAN[name]||{}; return (o[field]!=null&&o[field]!=='')?o[field]:(baked||null);}
function setMan(name,field,val){MAN[name]=MAN[name]||{}; MAN[name][field]=val; saveMAN();}
function filesOf(name){return (MAN[name]&&MAN[name].files)||[];}

/* ---------- staff-directory state: gold(contacted)/star/meeting/notes/media (localStorage) ---------- */
const STFKEY='mdesk_staffdir_v1';
let STF={}; try{STF=JSON.parse(localStorage.getItem(STFKEY))||{}}catch(e){STF={}}
function saveSTF(){localStorage.setItem(STFKEY,JSON.stringify(STF));}
function stf(id){return STF[id]||{};}
function setStf(id,k,v){(STF[id]=STF[id]||{})[k]=v;saveSTF();}
const STFIDX={};
D.members.forEach((m,i)=>(m.staffdir||[]).forEach(sf=>STFIDX[sf.id]={s:sf,m:m.name,mi:i}));

/* ---------- manual PRESS-STANCE overrides: localStorage -> press_overrides_from_dashboard.json ---------- */
const POVKEY='mdesk_pressov_v1';
let POV={}; try{POV=JSON.parse(localStorage.getItem(POVKEY))||{}}catch(e){POV={}}   // url -> {stance,title}
const POVCOL={support:'#34d399',oppose:'#ef4444',neutral:'#9ca3af'};
function savePOV(){localStorage.setItem(POVKEY,JSON.stringify(POV));}
function setPOV(url,stance,title){ if(!url)return; if(!stance){delete POV[url];} else {POV[url]={stance:stance,title:title||''};} savePOV(); }
function povOf(url){return (POV[url]&&POV[url].stance)||null;}
function povCount(){return Object.keys(POV).length;}
function updatePovHint(){const h=$('#povhint');if(h)h.textContent=povCount()?('✎ '+povCount()+' pending override'+(povCount()>1?'s':'')+' — Export to apply'):'';}

/* ---------- radar chart (SVG) ---------- */
function radar(vals,labels,color,R){
  const n=vals.length, padX=96, padY=44, cx=R+padX, cy=R+padY, W=2*cx, H=2*cy;
  const pt=(i,r)=>{const a=-Math.PI/2+i*2*Math.PI/n; return [cx+Math.cos(a)*r*R, cy+Math.sin(a)*r*R];};
  // FIXED pixel height + fully-QUOTED attributes + explicit closing tags. (Unquoted attrs ending in "…1/>"
  // get the slash swallowed into the value in HTML parsing, so the tag never self-closes and every following
  // element nests inside the first path and vanishes — that was the "radar not loading" bug.)
  let s=`<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" preserveAspectRatio="xMidYMid meet" style="display:block;width:100%;max-width:${W}px;height:${H}px;margin:0 auto">`;
  for(const g of [0.2,0.4,0.6,0.8,1]){let p='';for(let i=0;i<n;i++){const[x,y]=pt(i,g);p+=(i?'L':'M')+x.toFixed(1)+' '+y.toFixed(1);}s+=`<path d="${p}Z" fill="none" stroke="#2b3340" stroke-width="1"></path>`;}
  for(let i=0;i<n;i++){const[x,y]=pt(i,1);s+=`<line x1="${cx}" y1="${cy}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="#2b3340" stroke-width="1"></line>`;}
  let p='';for(let i=0;i<n;i++){const[x,y]=pt(i,Math.max(0.02,vals[i]||0));p+=(i?'L':'M')+x.toFixed(1)+' '+y.toFixed(1);}
  s+=`<path d="${p}Z" fill="${color}33" stroke="${color}" stroke-width="2" stroke-linejoin="round"></path>`;
  for(let i=0;i<n;i++){const[x,y]=pt(i,Math.max(0.02,vals[i]||0));s+=`<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="2.4" fill="${color}"></circle>`;}
  for(let i=0;i<n;i++){const[x,y]=pt(i,1.14);const c=Math.cos(-Math.PI/2+i*2*Math.PI/n);const anch=Math.abs(c)<0.34?'middle':(c>0?'start':'end');
    s+=`<text x="${x.toFixed(1)}" y="${y.toFixed(1)}" font-size="9" fill="#8b949e" text-anchor="${anch}" dominant-baseline="middle">${esc(labels[i]||'')}</text>`;}
  return s+'</svg>';
}

/* ---------- electoral history (two-series inline SVG: general % + primary %, 2016-2024) ---------- */
function evChart(h){
  const YEARS=[2016,2018,2020,2022,2024];
  const gm={},pm={}; (h.general||[]).forEach(g=>gm[g.year]=g); (h.primary||[]).forEach(p=>pm[p.year]=p);
  const W=560,H=196,padL=30,padR=12,padT=12,padB=24;
  const X=y=>padL+YEARS.indexOf(y)/(YEARS.length-1)*(W-padL-padR);
  const Y=v=>padT+(1-v/100)*(H-padT-padB);
  let s=`<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" preserveAspectRatio="xMidYMid meet" style="display:block;max-width:${W}px;margin:2px auto 0">`;
  for(const g of [0,25,50,75,100]){const yy=Y(g).toFixed(1);
    s+=`<line x1="${padL}" y1="${yy}" x2="${W-padR}" y2="${yy}" stroke="#21262d" stroke-width="1"></line>`;
    s+=`<text x="${(padL-5).toFixed(1)}" y="${yy}" font-size="9" fill="#7d8694" text-anchor="end" dominant-baseline="middle">${g}</text>`;}
  YEARS.forEach(y=>{s+=`<text x="${X(y).toFixed(1)}" y="${(H-7).toFixed(1)}" font-size="9" fill="#7d8694" text-anchor="middle">'${String(y).slice(2)}</text>`;});
  function draw(mp,col,isP){
    const val=y=>mp[y]?(mp[y].pct!=null?mp[y].pct:(isP&&mp[y].unopposed?100:null)):null;
    const pts=YEARS.filter(y=>val(y)!=null).map(y=>[X(y),Y(val(y)),y]);
    let o='';
    if(pts.length>1){let p='';pts.forEach((q,i)=>p+=(i?'L':'M')+q[0].toFixed(1)+' '+q[1].toFixed(1));
      o+=`<path d="${p}" fill="none" stroke="${col}" stroke-width="2" stroke-linejoin="round"></path>`;}
    pts.forEach(q=>{const uo=isP&&mp[q[2]]&&mp[q[2]].unopposed&&mp[q[2]].pct==null;
      o+= uo ? `<circle cx="${q[0].toFixed(1)}" cy="${q[1].toFixed(1)}" r="3.4" fill="#11161d" stroke="${col}" stroke-width="1.6"></circle>`
             : `<circle cx="${q[0].toFixed(1)}" cy="${q[1].toFixed(1)}" r="3" fill="${col}"></circle>`;});
    return o;
  }
  s+=draw(gm,'#58a6ff',false);   // general
  s+=draw(pm,'#f59e0b',true);    // primary (unopposed -> hollow ring at 100)
  return s+'</svg>';
}
function evCardHTML(m){
  const h=m.electoral;
  if(!h) return `<div class=card style=margin-bottom:14px><div class=eyebrow>Electoral history</div><div class=empty>No federal-election history on file — first elected 2024, or not matched to the FEC / MEDSL records.</div></div>`;
  const fc=h.forecast||{}, sec=fc.security; let lbl='—',lc='#9ca3af';
  if(sec!=null){ if(sec>=0.66){lbl='Safe';lc='#34d399';} else if(sec>=0.33){lbl='Lean / likely';lc='#f59e0b';} else {lbl='Competitive';lc='#ef4444';} }
  const badge=`<span style="font-weight:700;font-size:11px;color:${lc};background:${lc}1A;border:1px solid ${lc}55;border-radius:20px;padding:3px 11px">Current outlook: ${lbl}</span>`;
  const leg=`<div style="display:flex;gap:16px;font-size:11px;color:var(--muted);margin-top:6px;flex-wrap:wrap">
    <span><span style="display:inline-block;width:13px;height:2px;background:#58a6ff;vertical-align:middle;margin-right:5px"></span>General %</span>
    <span><span style="display:inline-block;width:13px;height:2px;background:#f59e0b;vertical-align:middle;margin-right:5px"></span>Primary %</span>
    <span><span style="display:inline-block;width:7px;height:7px;border:1.5px solid #f59e0b;border-radius:50%;vertical-align:middle;margin-right:5px"></span>Unopposed primary</span></div>`;
  return `<div class=card style=margin-bottom:14px>
    <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:4px;flex-wrap:wrap">
      <div class=eyebrow style=margin-bottom:0>Electoral history — vote share by cycle</div>${badge}</div>
    ${evChart(h)}${leg}
    <div style="font-size:10.5px;color:var(--faint);margin-top:7px">Primary &amp; general from the FEC <i>Federal Elections</i> books (2016–2022); 2024 general from MEDSL; 2024 primary pending. Outlook = Ballotpedia competitiveness percentile.</div>
  </div>`;
}

/* ---------- populate area selects ---------- */
const allAreas=CATS.concat(EXTRA);
[$('#area'),$('#cbarea')].forEach(sel=>{CATS.forEach(c=>{const o=document.createElement('option');o.value=c;o.textContent=c;sel.appendChild(o);});});
M.forEach(m=>{const o=document.createElement('option');o.value=m.name;$('#allnames').appendChild(o);});

/* ======================= RANKED VIEW ======================= */
// stance filter dropdown (Champion..Opponent)
STANCE_ORDER.forEach(t=>{const o=document.createElement('option');o.value=t;o.textContent=stanceName(t);$('#stancefilter').appendChild(o);});
const rstate={q:'',chamber:'all',funded:false,sort:'rank',area:'',stance:''};
$('#q').oninput=e=>{rstate.q=e.target.value.toLowerCase().trim();renderRanked();};
$('#fundedOnly').onchange=e=>{rstate.funded=e.target.checked;renderRanked();};
$('#sort').onchange=e=>{rstate.sort=e.target.value;renderRanked();};
$('#area').onchange=e=>{rstate.area=e.target.value;renderRanked();};
$('#stancefilter').onchange=e=>{rstate.stance=e.target.value;renderRanked();};
document.querySelectorAll('#chamber button').forEach(b=>b.onclick=()=>{document.querySelectorAll('#chamber button').forEach(x=>x.classList.remove('on'));b.classList.add('on');rstate.chamber=b.dataset.v;renderRanked();});
function sparkHTML(m){return `<div class=spark>`+['press','comm','leg','demo'].map(k=>{const v=m[k+'_n']||0;return `<i style="height:${Math.max(12,v*100)}%;background:${PILL[k].c}"></i>`;}).join('')+`</div>`;}
function renderRanked(){
  const area=rstate.area, ai=area?CATS.indexOf(area):-1;
  let r=M.filter(m=>{
    if(rstate.q&&!(m.name.toLowerCase().includes(rstate.q)||(m.district||'').toLowerCase().includes(rstate.q)))return false;
    if(rstate.chamber!=='all'&&m.chamber!==rstate.chamber)return false;
    if(rstate.funded&&!(m.invested>0))return false;
    if(rstate.stance&&stanceAt(m,area)!==rstate.stance)return false;   // stance filter, for the selected area
    return true;
  });
  if(area){r.sort((a,b)=>(b.radar[ai]||0)-(a.radar[ai]||0));}
  else{const s=rstate.sort;r.sort((a,b)=>s==='score'?(b.score||0)-(a.score||0):s==='invested'?(b.invested||0)-(a.invested||0):s==='name'?a.name.localeCompare(b.name):(a.rank||9999)-(b.rank||9999));}
  $('#count').textContent=`Showing ${r.length} of ${M.length} members`+(area?` · ${area}`:'');
  $('#th-stance').textContent=area?('Stance · '+area):'Stance · overall';
  $('#th-score').textContent=area?area:'Score';
  $('#rows').innerHTML=r.map((m,i)=>{
    const scoreCell=area
      ? `<div class=scorecell><div class=sbar><i style=width:${(m.radar[ai]||0)*100}%></i></div><span class=sval>${f2(m.radar[ai])}</span></div>`
      : `<div class=scorecell><div class=sbar><i style=width:${(m.score||0)*100}%></i></div><span class=sval>${f2(m.score)}</span></div>`;
    const rk=area?('#'+(m.adjrank[area]||'—')):(m.rank??'—');
    return `<tr data-i=${byName[m.name]}>
      <td class=num><span class=rk>${rk}</span></td>
      <td><div class=nm>${m.name}</div><div class=dist>${m.chamber} · ${m.party||'—'} · ${m.district||''}</div></td>
      <td>${stanceBadge(stanceAt(m,area))}</td>
      <td>${sparkHTML(m)}</td>
      <td>${scoreCell}</td></tr>`;
  }).join('');
  document.querySelectorAll('#rows tr').forEach(tr=>tr.onclick=()=>openMember(+tr.dataset.i));
}

/* ======================= MEMBER VIEW ======================= */
function openMember(i){
  const m=M[i]; if(!m)return;
  setView('member'); window.scrollTo(0,0);
  history.replaceState(null,'','?m='+encodeURIComponent(m.name));
  const os=m.overall_stance||'-', col=STCOL[os]||'#6b7280';   // overall stance tier drives the verdict
  // per-area stance, sorted champion -> opponent (then by score)
  const areaRows=CATS.map((cat,ix)=>({cat,ix,st:(m.stances&&m.stances[ix])||'-',score:m.radar[ix],rank:m.adjrank[cat],def:DEF.has(cat)}))
    .sort((a,b)=>{const na=STANCE_ORDER.indexOf(a.st),nb=STANCE_ORDER.indexOf(b.st);return (na<0?99:na)-(nb<0?99:nb)||(b.score-a.score);});
  const stanceByArea=areaRows.map(a=>`<div class=arow><span class=aname>${a.cat}${a.def?' <span style=color:var(--faint)>(def)</span>':''}</span>${stanceBadge(a.st)}<span class=arank>#${a.rank||'—'} · ${f2(a.score)}</span></div>`).join('');
  const legRadar=radar(m.radar,D.cats_short,'#34d399',90);
  const evLbl=m.ev_play, evVal=m.ev_value;
  // pillars
  const pillars=['press','comm','leg','demo'].map(k=>{const v=m[k+'_n'],raw=m[k+'_raw'];
    return `<div class=barrow><span class=t><span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${PILL[k].c};margin-right:5px"></span>${PILL[k].l} <span style=color:var(--faint)>×${PILL[k].w.toFixed(2)}</span></span><span class=track><i style="width:${(v||0)*100}%;background:${PILL[k].c}"></i></span><span class=val>${f2(v)}</span></div>`;}).join('');
  let h=`<div class=mhead>
    <div>
      <div class=verdict style="color:${col};background:${col}26"><span class=d></span>${stanceName(os)} · ${POSTURE[os]||'qualify'} <span style=opacity:.7;font-weight:500>· overall</span></div>
      <h2>${m.name}</h2><div class=meta>${m.chamber} · ${m.party||'—'} · ${m.district||''}</div>
    </div>
    <div style=display:flex;gap:8px>
      <button class=backbtn id=backbtn>◀ Ranked list</button>
      <button class=backbtn id=printbtn>⎙ Print / PDF</button>
      <a class=netlink href="Moneyball Dashboard.html">Open network ↗</a>
    </div>
  </div>
  <div class=figs style=margin-bottom:14px>
    <div class=fig><div class=v>#${m.rank??'—'}</div><div class=l>Overall rank</div></div>
    <div class=fig><div class=v>${f2(m.score)}</div><div class=l>Composite score</div></div>
    <div class=fig accent><div class=v>${money(m.invested)}</div><div class=l>Invested · FEC</div></div>
    <div class=fig><div class=v>${money(m.ind_money)}</div><div class=l>Opposing $</div></div>
    <div class=fig><div class=v>${(m.roi||0).toFixed(3)}</div><div class=l>ROI · flips/$10k</div></div>
    <div class=fig><div class=v>${evVal>0?money(evVal):'—'}</div><div class=l>Electoral-vuln. $${evLbl&&evLbl!=='No active play'?' · <span style=color:#f59e0b>'+evLbl+'</span>':''}</div></div>
  </div>
  <div class=gen>
    <div class=card><div class=eyebrow>Legislative strengths — relative to all members</div>${legRadar}
      <div class=mrow style=margin-top:8px><span>Pillar composition</span><span></span></div>${pillars}</div>
    <div class=card><div class=eyebrow>Stance by legislative area</div><div class=arealist>${stanceByArea}</div></div>
  </div>
  ${evCardHTML(m)}
  <div class=card id=trackcard style=margin-bottom:14px>${trackerHTML(m)}</div>`;
  // sections
  h+=section('Staff','staff',staffHTML(m));
  h+=section('Biographical','bio',bioHTML(m));
  h+=section('Relational','rel',relHTML(m));
  h+=section('Committee positions','cttee',committeeHTML(m));
  h+=section('Demographics','demo',demoHTML(m));
  h+=section('Psychometrics','psych',psychHTML(m));
  h+=section('Legislative actions','leg',legHTML(m));
  h+=section('Press & social media','press',pressHTML(m));
  $('#memberbody').innerHTML=h;
  $('#backbtn').onclick=()=>{setView('ranked');history.replaceState(null,'','./');};
  $('#printbtn').onclick=()=>{document.querySelectorAll('#app-member details.sec').forEach(d=>d.open=true);window.print();};
  wireManual(m);
  wireTracker(m);
  wireSectionFilters(m);
}
function section(title,key,inner){
  return `<details class=sec ${key==='staff'?'':''}><summary>${title}<span class=chev>▸</span></summary><div class=body>${inner}</div></details>`;
}
/* ---- engagement tracker (CRM-lite, localStorage) ---- */
const TRK_STATUS=['—','Not started','Researching','Outreach sent','Meeting set','Met','Committed','Declined'];
const TRK_COL={'Committed':'#34d399','Met':'#2dd4bf','Meeting set':'#7dd3fc','Outreach sent':'#fcd9a8','Researching':'#9ca3af','Not started':'#6e7681','Declined':'#ef4444'};
function trackerHTML(m){
  const t=(MAN[m.name]&&MAN[m.name].tracker)||{}, cur=t.status||'—';
  return `<div class=eyebrow>Engagement tracker <span style=color:var(--faint);font-weight:400;text-transform:none>· saved on this device, included in Export notes</span></div>
    <div class=trackgrid>
      <label>Status<select class=trk data-f=status>${TRK_STATUS.map(s=>`<option ${s===cur?'selected':''}>${s}</option>`).join('')}</select></label>
      <label>Last contact<input class=trk data-f=last type=date value="${esc(t.last||'')}"></label>
      <label>Owner<input class=trk data-f=owner value="${esc(t.owner||'')}" placeholder="lead staffer"></label>
      <label style=grid-column:1/-1>Next step<input class=trk data-f=next value="${esc(t.next||'')}" placeholder="e.g. schedule interchange meeting before markup"></label>
    </div>`;
}
function wireTracker(m){
  document.querySelectorAll('#trackcard .trk').forEach(el=>el.onchange=()=>{
    MAN[m.name]=MAN[m.name]||{}; MAN[m.name].tracker=MAN[m.name].tracker||{};
    MAN[m.name].tracker[el.dataset.f]=el.value; saveMAN();
  });
}
/* ----- section renderers ----- */
function stfCard(sf){
  const st=stf(sf.id);
  const starred=st.star!=null?st.star:sf.star;
  const media=(st.media||[]).map((mm,k)=>`<span class=chip><a href="${esc(mm.u)}" target=_blank rel=noopener>${esc(mm.l||mm.u)}</a><span class=x data-act=delmedia data-sid=${sf.id} data-k=${k}>×</span></span>`).join('');
  return `<div class="stfcard${st.gold?' gold':''}" data-sid=${sf.id}>
    <div class=stfhead><span class="stfstar${starred?' on':''}" data-act=star data-sid=${sf.id} title="industry-relevant — click to toggle">${starred?'★':'☆'}</span><b>${esc(sf.n)}</b><span class=stftitle>${esc(sf.t)}</span></div>
    <div class=stfmeta>${sf.e?`<a href="mailto:${esc(sf.e)}">${esc(sf.e)}</a>`:''}${sf.e&&sf.p?' · ':''}${sf.p?`<a href="tel:${esc(sf.p)}">${esc(sf.p)}</a>`:''}</div>
    <div class=stfctl>
      <button class="mini${st.gold?' on':''}" data-act=gold data-sid=${sf.id} title="contact established — gold outline">${st.gold?'✓ Contacted':'Mark contacted'}</button>
      <button class="mini${st.meet?' on':''}" data-act=meet data-sid=${sf.id} title="show in the In-contact panel">${st.meet?'🤝 Meeting set':'Set up meeting'}</button>
      <button class=mini data-act=note data-sid=${sf.id}>Note</button>
      <button class=mini data-act=media data-sid=${sf.id}>+ Media</button>
    </div>
    <div class=stfnote ${st.note?'':'hidden'}><textarea class=stfnotebox data-sid=${sf.id} placeholder="notes…">${esc(st.note||'')}</textarea></div>
    <div class=stfmedia>${media}</div>
  </div>`;
}
function staffHTML(m){
  const note=manField(m.name,'staff',m.staff);const files=filesOf(m.name);
  const dir=(m.staffdir||[]);
  const dirHTML=dir.length?`<input class=stfsearch data-stfsearch placeholder="filter ${dir.length} staffers (name/title)…">
    <div class=stflist>${dir.map(stfCard).join('')}</div>`:`<div class=empty>No staffer directory rows matched for this office.</div>`;
  return `<div id=staff-view>${dirHTML}<hr style="border-color:var(--line,#2a2f3a);margin:10px 0">
  ${note?`<div class=savednote>${esc(note)}</div>`:`<div class=empty>No office-level staff notes yet.</div>`}
    ${files.length?`<div class=filelist>`+files.map((f,k)=>`<div class=fileitem><a href="${f.data}" download="${esc(f.name)}">📎 ${esc(f.name)}</a><span class=del data-f=${k} data-field=staff>remove</span></div>`).join('')+`</div>`:''}
    <button class=btn data-edit=staff>${note?'Edit':'Add'} note</button><label class=btn for=file-staff style=cursor:pointer>Upload file</label><input id=file-staff type=file data-field=staff hidden multiple>
    <div id=staff-edit hidden><textarea class=notebox data-field=staff>${esc(note||'')}</textarea><button class=btn data-save=staff>Save</button><button class="btn ghost" data-cancel=staff>Cancel</button></div></div>`;
}
function psychHTML(m){
  const note=manField(m.name,'psych',m.psychometrics);
  return `<div id=psych-view>${note?`<div class=savednote>${esc(note)}</div>`:`<div class=empty>No psychometric profile yet. Add disposition, motivations, persuasion notes, communication style.</div>`}
    <button class=btn data-edit=psych>${note?'Edit':'Add'} note</button>
    <div id=psych-edit hidden><textarea class=notebox data-field=psych>${esc(note||'')}</textarea><button class=btn data-save=psych>Save</button><button class="btn ghost" data-cancel=psych>Cancel</button></div></div>`;
}
function bioHTML(m){
  const b=m.bio||{};const rows=[];
  const add=(l,v)=>{if(v)rows.push(`<div class=mrow><span>${l}</span><b>${v}</b></div>`);};
  add('Full name',(b.first_name&&b.last_name)?b.first_name+' '+b.last_name:m.name);
  add('State',b.state);add('Born',b.birthday);add('Gender',b.gender==='M'?'Male':b.gender==='F'?'Female':b.gender);
  add('Bioguide ID',b.bioguide);
  const links=[];if(b.url)links.push(`<a href="${b.url}" target=_blank>Official site</a>`);
  if(b.twitter)links.push(`<a href="https://twitter.com/${b.twitter}" target=_blank>X/@${b.twitter}</a>`);
  if(b.ballotpedia_id)links.push(`<a href="https://ballotpedia.org/${encodeURIComponent(b.ballotpedia_id)}" target=_blank>Ballotpedia</a>`);
  if(b.wikipedia_id)links.push(`<a href="https://en.wikipedia.org/wiki/${encodeURIComponent(b.wikipedia_id)}" target=_blank>Wikipedia</a>`);
  if(b.bioguide)links.push(`<a href="https://bioguide.congress.gov/search/bio/${b.bioguide}" target=_blank>Congress bio</a>`);
  const note=manField(m.name,'bio',m.bio_manual);
  return `${rows.join('')||'<div class=empty>No structured bio on file.</div>'}
    ${links.length?`<div style=margin-top:8px>${links.join(' · ')}</div>`:''}
    <div style=margin-top:12px><div class=eyebrow>Notes</div><div id=bio-view>${note?`<div class=savednote>${esc(note)}</div>`:'<div class=empty>Add background, career, district history, prior interactions.</div>'}
    <button class=btn data-edit=bio>${note?'Edit':'Add'} note</button>
    <div id=bio-edit hidden><textarea class=notebox data-field=bio>${esc(note||'')}</textarea><button class=btn data-save=bio>Save</button><button class="btn ghost" data-cancel=bio>Cancel</button></div></div></div>`;
}
function relHTML(m){
  const partners=m.partners||[];
  const maxw=Math.max(1,...partners.map(p=>p.w));
  const ptHTML=partners.length?partners.map(p=>{const col=PTCOL[{D:'Democrat',R:'Republican',I:'Independent'}[p.party]||'']||'#6b7280';
    return `<div class=partner data-i=${byName[p.name]??-1}><span class=pn>${p.name}</span><span class=track style="height:8px;background:#1b2129;border-radius:4px;overflow:hidden"><i style="display:block;height:100%;width:${(p.w/maxw)*100}%;background:${col}"></i></span><span style=color:var(--muted);text-align:right>#${p.rank} · ${p.w}</span></div>`;}).join(''):'<div class=empty>No cosponsorship ties in the network for this member.</div>';
  const st=m.state;const sm=st?M.filter(x=>x.state===st&&x.name!==m.name).sort((a,b)=>(a.rank||9999)-(b.rank||9999)):[];
  const smHTML=sm.length?sm.map(x=>`<div class=partner data-i=${byName[x.name]}><span class=pn>${x.name}</span><span style=color:var(--muted)>${x.chamber}</span><span style=color:var(--muted);text-align:right>#${x.rank??'—'}</span></div>`).join(''):'<div class=empty>No other members parsed for this state.</div>';
  return `<div class=eyebrow>Top cosponsorship partners</div>${ptHTML}
    <div class=eyebrow style=margin-top:14px>Same-state delegation — ${st||'?'}</div>${smHTML}`;
}
const RELCOL={Highly:'#16a34a',Moderately:'#f59e0b',Slightly:'#8b949e'};
function committeeHTML(m){
  const cs=m.committees||[];
  if(!cs.length) return '<div class=empty>No committee assignments parsed for this member.</div>';
  // full committees, jurisdiction-relevant first (Highly>Moderately>Slightly), full committees before subs
  const rank={Highly:0,Moderately:1,Slightly:2};
  const rows=cs.slice().sort((a,b)=>(rank[a.rel]??9)-(rank[b.rel]??9)).map(c=>{
    const rc=RELCOL[c.rel]||'#6b7280';
    const role=c.role?`<span style="font-size:11px;font-weight:700;color:#0e1116;background:#cbb46a;padding:1px 6px;border-radius:4px;margin-left:6px">${c.role}</span>`:'';
    return `<div class=arow><span class=aname>${c.name}${role}</span><span style="font-size:11px;font-weight:700;color:${rc};background:${rc}22;border:1px solid ${rc}55;padding:1px 8px;border-radius:10px">${c.rel}</span></div>`;}).join('');
  const sc=m.committee_score!=null?(+m.committee_score).toFixed(2):'—';
  return `<div class=eyebrow>Committee &amp; subcommittee seats <span style=color:var(--faint)>· badge = jurisdictional relevance to CU issues · committee score ${sc}</span></div>${rows}`;
}
function demoHTML(m){
  const d=m.demo||{};
  const dr=radar(m.demo_radar||[],D.demo_short,'#c2862a',82);
  const cells=[[money(d.income),'Median household income'],[pc(d.pct_costburden),'Mortgaged HHs cost-burdened'],
    [pc(d.pct_finance),'Workers in finance / RE'],[n0(d.constituents),'Constituents'],
    [pc(d.pct_ownerocc_mort),'Owner-occ. w/ mortgage'],[n0(d.establishments),'Business establishments'],
    [d.median_age!=null?d.median_age:'—','Median age'],[pc(d.poverty_rate),'Poverty rate'],[money(d.percap),'Per-capita income']]
    .map(([v,l])=>`<div class=dcell><div class=v>${v}</div><div class=l>${l}</div></div>`).join('');
  return `<div class=gen style=margin-bottom:12px><div>${dr}</div><div class=dgrid>${cells}</div></div>
    <div class=empty>District-level demographics shown. Standout / largest employers by name are not in the current dataset — add via the notes fields or a future data pull.</div>`;
}
const ROLEBADGE={sponsor:['Sponsor','#16a34a'],original:['Orig. cosponsor','#2dd4bf'],cosponsor:['Cosponsor','#7dd3fc']};
function legHTML(m){
  const bills=m.bills||[];
  if(!bills.length)return '<div class=empty>No tracked CU-relevant bills for this member (as sponsor, original cosponsor, or cosponsor).</div>';
  const areas=[...new Set(bills.flatMap(b=>b.areas||[]))].sort();
  const roleSeg=`<span class=seg id=legrole><button data-r="" class=on>All roles</button><button data-r=sponsor>Sponsored</button><button data-r=original>Orig. cosponsor</button><button data-r=cosponsor>Cosponsor</button></span>`;
  const areaSel=`<select class=secarea data-for=leg><option value="">All areas</option>${areas.map(c=>`<option value="${esc(c)}">${esc(c)}</option>`).join('')}</select>`;
  return `<div class=areasel>${roleSeg}${areaSel}</div><div id=leg-body></div>`;
}
function legBody(m,area,role){
  const bills=(m.bills||[]).filter(b=>(!area||(b.areas||[]).includes(area))&&(!role||b.role===role));
  if(!bills.length)return '<div class=empty>No bills'+(role?' as '+(ROLEBADGE[role][0].toLowerCase()):'')+(area?' in '+esc(area):'')+'.</div>';
  return `<div class=cnt>${bills.length} bill${bills.length>1?'s':''}</div>`+bills.map(b=>{const r=ROLEBADGE[b.role]||['',''];
    return `<div class=billrow>
      <div class=billtop><span class=rolebadge style="color:${r[1]};background:${r[1]}1f">${r[0]}</span>
        ${b.url?`<a class=billno href="${b.url}" target=_blank rel=noopener>${esc(b.bill)}</a>`:`<span class=billno>${esc(b.bill)}</span>`}
        <span class=billcong>${b.congress?b.congress+'th Cong.':''}</span></div>
      <div class=billtitle>${esc(b.title)}</div>
      <div class=billmeta>${(b.areas||[]).map(esc).join(' · ')} · ${esc(b.sponsor)}${b.ncos?` · ${b.ncos} cosponsors`:''}</div>
      ${b.summary?`<div class=billsum>${esc(b.summary)}</div>`:''}</div>`;}).join('');
}
// graded sentiment scale (score_label), most positive -> most negative
const SENT_ORDER=['Very strongly positive','Strongly positive','Positive','Weakly positive','Very weakly positive','Neutral','Very weakly negative','Weakly negative','Negative','Strongly negative','Very strongly negative'];
const SENT_NEU=SENT_ORDER.indexOf('Neutral');
function sentCol(l){const i=SENT_ORDER.indexOf(l);if(i<0||i===SENT_NEU)return '#9ca3af';return i<SENT_NEU?'#34d399':'#ef4444';}
function pressHTML(m){
  const arts=m.articles||[];
  if(!arts.length)return '<div class=empty>No tracked credit-union press items on record for this member. The press pillar reflects this absence.</div>';
  const areas=[...new Set(arts.flatMap(a=>a.cats||[]))].sort();
  const present=[...new Set(arts.map(a=>a.label).filter(Boolean))];
  const ordered=SENT_ORDER.filter(l=>present.includes(l)).concat(present.filter(l=>SENT_ORDER.indexOf(l)<0));
  const sentSel=`<select class=secsent data-for=press><option value="">All sentiment</option>${ordered.map(l=>`<option value="${esc(l)}">${esc(l)} (${arts.filter(a=>a.label===l).length})</option>`).join('')}</select>`;
  const areaSel=`<select class=secarea data-for=press><option value="">All areas</option>${areas.map(c=>`<option value="${esc(c)}">${esc(c)}</option>`).join('')}</select>`;
  return `<div class=areasel>${sentSel}${areaSel}</div><div id=press-body></div>`;
}
function pressBody(m,area,sent){
  const arts=(m.articles||[]).filter(a=>(!area||(a.cats||[]).includes(area))&&(!sent||a.label===sent));
  if(!arts.length)return '<div class=empty>No '+(sent?esc(sent).toLowerCase()+' ':'')+'press items'+(area?' in '+esc(area):'')+' for this member.</div>';
  return `<div class=cnt>${arts.length} article${arts.length>1?'s':''}${sent?' · '+esc(sent):''}${area?' · '+esc(area):''}</div>`+arts.map(a=>{
    const base=({support:'support',oppose:'oppose',neutral:'neutral'}[a.stance])||'neutral';   // current call (model + any baked file correction)
    const ov=povOf(a.url); const cur=ov||base; const effPol={support:1,oppose:-1,neutral:0}[cur];
    const eu=encodeURIComponent(a.url||''), et=encodeURIComponent(a.title||'');
    const opts=['support','oppose','neutral'].map(o=>`<option value="${o}"${cur===o?' selected':''}>${o[0].toUpperCase()+o.slice(1)}</option>`).join('');
    const tag=(ov&&ov!==base)?`<span class=ovtag style="color:${POVCOL[ov]};background:${POVCOL[ov]}1A">✎ edited → ${ov} (was ${base})</span>`:(a.corr?`<span class=ovtag style="color:#a78bfa;background:#a78bfa1A">✎ file-corrected</span>`:'');
    return `<div class=ev data-pol="${effPol}">
    <div class=ev-top><span>${a.date||''}${a.dest==='est'?' <span style=color:var(--faint)>(est.)</span>':''}</span><span>${(a.cats||[]).slice(0,3).map(esc).join(' · ')}</span></div>
    <a class=ev-title href="${a.url}" target=_blank rel=noopener>${esc(a.title||'')}</a>
    <div class=ev-sig>${a.label?`<b style="color:${sentCol(a.label)}">${esc(a.label)}</b>`:''}<span class=ev-basis> · ${a.ssrc==='bill'?'via tracked-bill direction':('DEBATE stance: '+esc(a.stance||'n/a')+(a.sconf?` (${Math.round(a.sconf*100)}% conf)`:''))}${a.rel?' · '+esc(a.rel):''}</span></div>
    <div class=ev-ov>${tag}<span class=ovlabel>CU stance:</span><select class=povsel data-povurl="${eu}" data-povtitle="${et}" data-base="${base}">${opts}</select></div></div>`;
  }).join('');
}
function esc(s){return (s==null?'':String(s)).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}

/* ----- wire section area filters + member links ----- */
function wireSectionFilters(m){
  const ls={area:'',role:''}, ps={area:'',sent:''};
  const renderLeg=()=>{const lb=$('#leg-body');if(lb)lb.innerHTML=legBody(m,ls.area,ls.role);};
  const renderPress=()=>{const pb=$('#press-body');if(pb)pb.innerHTML=pressBody(m,ps.area,ps.sent);};
  renderLeg(); renderPress();
  const _pbox=$('#press-body');
  if(_pbox)_pbox.addEventListener('change',e=>{const s=e.target.closest('.povsel');if(!s)return;
    const val=s.value, base=s.dataset.base;                       // picking the baseline clears the override
    setPOV(decodeURIComponent(s.dataset.povurl||''), val===base?null:val, decodeURIComponent(s.dataset.povtitle||''));
    renderPress(); updatePovHint();});
  document.querySelectorAll('.secarea').forEach(sel=>sel.onchange=()=>{
    if(sel.dataset.for==='leg'){ls.area=sel.value;renderLeg();}
    else {ps.area=sel.value;renderPress();}
  });
  const ssel=document.querySelector('.secsent[data-for=press]');
  if(ssel)ssel.onchange=()=>{ps.sent=ssel.value;renderPress();};
  const rseg=document.getElementById('legrole');
  if(rseg)rseg.querySelectorAll('button').forEach(b=>b.onclick=()=>{rseg.querySelectorAll('button').forEach(x=>x.classList.remove('on'));b.classList.add('on');ls.role=b.dataset.r;renderLeg();});
  document.querySelectorAll('.partner').forEach(el=>el.onclick=()=>{const i=+el.dataset.i;if(i>=0)openMember(i);});
}
/* ----- wire manual edit/save/upload ----- */
function wireManual(m){
  document.querySelectorAll('[data-edit]').forEach(b=>b.onclick=()=>{const k=b.dataset.edit;$('#'+k+'-edit').hidden=false;b.hidden=true;});
  document.querySelectorAll('[data-cancel]').forEach(b=>b.onclick=()=>{openMember(byName[m.name]);});
  document.querySelectorAll('[data-save]').forEach(b=>b.onclick=()=>{const k=b.dataset.save;const ta=document.querySelector('textarea[data-field='+k+']');setMan(m.name,k,ta.value.trim());openMember(byName[m.name]);});
  document.querySelectorAll('input[type=file][data-field]').forEach(inp=>inp.onchange=e=>{
    const k=inp.dataset.field;const fs=[...e.target.files];let left=fs.length;
    MAN[m.name]=MAN[m.name]||{};MAN[m.name].files=MAN[m.name].files||[];
    fs.forEach(file=>{const rd=new FileReader();rd.onload=()=>{MAN[m.name].files.push({name:file.name,type:file.type,data:rd.result,field:k});if(--left===0){saveMAN();openMember(byName[m.name]);}};rd.readAsDataURL(file);});
  });
  document.querySelectorAll('.del[data-f]').forEach(el=>el.onclick=()=>{const k=+el.dataset.f;MAN[m.name].files.splice(k,1);saveMAN();openMember(byName[m.name]);});
}

/* ======================= COALITION BUILDER ======================= */
let coal=new Set(), cbArea='';
$('#cbsearch').onchange=e=>{const i=byName[e.target.value.trim()];if(i!=null){coal.add(i);e.target.value='';renderCoal();}};
$('#cbarea').onchange=e=>{cbArea=e.target.value;renderCoal();};
$('#cbclear').onclick=()=>{coal.clear();renderCoal();};
$('#cbnet').onclick=()=>{if(!coal.size)return;const names=[...coal].map(i=>M[i].name);if(window.gotoNetworkCoalition)window.gotoNetworkCoalition(names);else alert('Network view is available in the combined dashboard.');};
function suggest(){
  const sc={};
  coal.forEach(s=>{(ADJ[s]||[]).forEach(([v,w])=>{if(!coal.has(v))sc[v]=(sc[v]||0)+PE(w);});});
  let arr=Object.entries(sc).map(([v,s])=>[+v,s]);
  if(cbArea){const ai=CATS.indexOf(cbArea);arr.forEach(a=>a[1]*=(1+(M[a[0]].radar[ai]||0)));}
  arr.sort((a,b)=>b[1]-a[1]);return arr.slice(0,16);
}
function reachEstimate(){ // expected coverage = members with >=1 tie to coalition (1-Π(1-PE))
  if(!coal.size)return 0;const cov=new Float64Array(M.length);
  coal.forEach(s=>{cov[s]=1;(ADJ[s]||[]).forEach(([v,w])=>{cov[v]=1-(1-cov[v])*(1-PE(w));});});
  let r=0;for(let i=0;i<cov.length;i++)r+=cov[i];return r;
}
function renderCoal(){
  $('#cbcount').textContent=coal.size?`· ${coal.size}`:'';
  const list=[...coal].map(i=>M[i]);
  $('#cblist').innerHTML=coal.size?list.map(m=>{const col=PTCOL[m.party]||'#6b7280';return `<span class=coalchip><span class=pdot style=background:${col}></span>${m.name}<span class=x data-i=${byName[m.name]}>✕</span></span>`;}).join(''):'<div class=empty>Search above to add bill cosponsors. Suggestions appear once you add the first.</div>';
  // party split + reach
  if(coal.size){const dd=list.filter(m=>m.party==='Democrat').length,rr=list.filter(m=>m.party==='Republican').length,ii=coal.size-dd-rr;
    $('#cbstats').innerHTML=`<div class=mrow><span>Coalition size</span><b>${coal.size}</b></div><div class=mrow><span>Party split (D · R · I)</span><b>${dd} · ${rr} · ${ii}</b></div><div class=mrow><span>Expected network reach</span><b>~${reachEstimate().toFixed(0)} members</b></div>
    <div class=legendrow><span><span class=pdot style=background:#3b82f6></span>Dem</span><span><span class=pdot style=background:#ef4444></span>Rep</span><span><span class=pdot style=background:#a855f7></span>Ind</span></div>`;}
  else $('#cbstats').innerHTML='';
  $('#cbnet').style.display=coal.size?'inline-block':'none';
  // suggestions
  const sg=suggest();const mx=Math.max(0.001,...sg.map(s=>s[1]));
  $('#cbsugg').innerHTML=coal.size?(sg.length?sg.map(([i,s])=>{const m=M[i];const col=PTCOL[m.party]||'#6b7280';
    return `<div class=sugg data-i=${i}><span><span class=pdot style="background:${col};display:inline-block;margin-right:6px"></span>${m.name} <span style=color:var(--faint)>${m.chamber} · #${m.rank??'—'}${cbArea?' · '+f2(m.radar[CATS.indexOf(cbArea)])+' '+cbArea.split(' ')[0]:''}</span></span><span class=add>+ ${(s/mx*100).toFixed(0)}</span></div>`;}).join(''):'<div class=empty>No further cosponsor ties from the current set.</div>'):'<div class=empty>Add a cosponsor to see suggested next members.</div>';
  document.querySelectorAll('#cblist .x').forEach(el=>el.onclick=()=>{coal.delete(+el.dataset.i);renderCoal();});
  document.querySelectorAll('#cbsugg .sugg').forEach(el=>el.onclick=()=>{coal.add(+el.dataset.i);renderCoal();});
}
[$('#cbarea')].forEach(()=>{});CATS.forEach(c=>{});  // (areas already populated above)

/* ======================= INVESTMENT EFFICIENCY ======================= */
const effState={q:'',chamber:'all',sort:'roi'};
$('#effq').oninput=e=>{effState.q=e.target.value.toLowerCase().trim();renderEff();};
$('#effsort').onchange=e=>{effState.sort=e.target.value;renderEff();};
document.querySelectorAll('#effch button').forEach(b=>b.onclick=()=>{document.querySelectorAll('#effch button').forEach(x=>x.classList.remove('on'));b.classList.add('on');effState.chamber=b.dataset.v;renderEff();});
const MAXROI=Math.max(0.001,...M.map(m=>m.roi||0));
function renderEff(){
  let r=M.filter(m=>(!effState.q||m.name.toLowerCase().includes(effState.q))&&(effState.chamber==='all'||m.chamber===effState.chamber));
  const s=effState.sort;
  r.sort((a,b)=> s==='gap'?(b.gap||0)-(a.gap||0) : s==='invested'?(b.invested||0)-(a.invested||0) : s==='rank'?((a.rank||9999)-(b.rank||9999)) : s==='value'?(b.eff_value||0)-(a.eff_value||0) : (b.roi||0)-(a.roi||0));
  $('#effcount').textContent=`Showing ${r.length} of ${M.length} members`;
  $('#effrows').innerHTML=r.map(m=>{
    const ev=m.eff_value||0, roi=m.roi||0, gap=m.gap||0;
    const gapTxt=gap>0?('+$'+Math.abs(gap).toLocaleString()):gap<0?('−$'+Math.abs(gap).toLocaleString()):'—';
    const gapCol=gap>0?'#34d399':gap<0?'#ef4444':'var(--muted)';
    return `<tr data-i=${byName[m.name]}>
      <td class=num><span class=rk>${m.rank??'—'}</span></td>
      <td><div class=nm>${m.name}</div><div class=dist>${m.chamber} · ${m.party||'—'} · <span style="color:${STCOL[m.overall_stance]||'#888'}">${stanceName(m.overall_stance)}</span></div></td>
      <td class=num>${money(m.invested)}</td>
      <td class=num>${m.opt_alloc>0?money(m.opt_alloc):'—'}</td>
      <td class=num style="color:${gapCol}">${gapTxt}</td>
      <td class=num style="color:${ev>=0?'#86efac':'#f0a0a0'}">${ev>=0?'+':''}${ev.toFixed(2)}</td>
      <td><div class=scorecell><div class=sbar><i style="width:${(roi/MAXROI*100).toFixed(1)}%;background:linear-gradient(90deg,#0e7c66,#34d399)"></i></div><span class=sval>${roi.toFixed(3)}</span></div></td>
    </tr>`;}).join('');
  document.querySelectorAll('#effrows tr').forEach(tr=>tr.onclick=()=>openMember(+tr.dataset.i));
}

/* ======================= VIEW SWITCH + EXPORT/IMPORT ======================= */
function setView(v){
  document.querySelectorAll('.view').forEach(s=>s.hidden=true);
  $('#view-'+v).hidden=false;
  document.querySelectorAll('#viewseg button').forEach(b=>b.classList.toggle('on',b.dataset.v===v||(v==='member'&&false)));
  if(v==='coalition')renderCoal();
  if(v==='efficiency')renderEff();
  if(v==='contact')renderContact();
}
document.querySelectorAll('#viewseg button').forEach(b=>b.onclick=()=>{setView(b.dataset.v);if(b.dataset.v==='ranked')history.replaceState(null,'','./');});
$('#exportbtn').onclick=()=>{const blob=new Blob([JSON.stringify(MAN,null,1)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='member_desk_manual.json';a.click();};
$('#importfile').onchange=e=>{const f=e.target.files[0];if(!f)return;const rd=new FileReader();rd.onload=()=>{try{const o=JSON.parse(rd.result);Object.keys(o).forEach(k=>{MAN[k]=Object.assign(MAN[k]||{},o[k]);});saveMAN();alert('Imported notes for '+Object.keys(o).length+' members.');}catch(err){alert('Invalid JSON.');}};rd.readAsText(f);};
$('#povexport').onclick=()=>{
  const cs=Object.keys(POV).map(u=>({url:u,stance:POV[u].stance,note:"manual override via dashboard"+(POV[u].title?(" — "+POV[u].title):"")}));
  if(!cs.length){alert("No manual overrides set yet. Use the Set-CU-stance dropdown on any press article first.");return;}
  const out={_README:"Manual press-stance calls from the dashboard. Apply with:  python fec/apply_press_overrides.py  (merges into press_stance_overrides.json, re-flows the press pillar so ranks move; next make_member_desk regen shows them). Match by url (exact). stance: support|oppose|neutral.",corrections:cs};
  const b=new Blob([JSON.stringify(out,null,2)],{type:"application/json"});const a=document.createElement("a");a.href=URL.createObjectURL(b);a.download="press_overrides_from_dashboard.json";a.click();
};
$('#povimport').onchange=e=>{const f=e.target.files[0];if(!f)return;const rd=new FileReader();rd.onload=()=>{try{const o=JSON.parse(rd.result);let n=0;(o.corrections||[]).forEach(c=>{if(c.url&&c.stance){POV[c.url]={stance:c.stance,title:c.note||""};n++;}});savePOV();updatePovHint();alert("Imported "+n+" override(s). Reopen a member Press section to see them.");}catch(err){alert("Invalid JSON.");}};rd.readAsText(f);};

/* ======================= STAFF DIRECTORY interactions ======================= */
document.addEventListener('click',e=>{
  const el=e.target.closest('[data-act]'); if(!el)return;
  const id=el.dataset.sid, act=el.dataset.act, st=stf(id), card=el.closest('.stfcard');
  if(act==='gold'){setStf(id,'gold',!st.gold); if(card){card.classList.toggle('gold',!st.gold); el.classList.toggle('on',!st.gold); el.textContent=!st.gold?'✓ Contacted':'Mark contacted';} if(!$('#view-contact').hidden)renderContact();}
  else if(act==='star'){const cur=(st.star!=null?st.star:(STFIDX[id]?STFIDX[id].s.star:0)); setStf(id,'star',cur?0:1); el.classList.toggle('on',!cur); el.textContent=!cur?'★':'☆';}
  else if(act==='meet'){setStf(id,'meet',!st.meet); if(el.classList){el.classList.toggle('on',!st.meet); el.textContent=!st.meet?'🤝 Meeting set':'Set up meeting';} if(!$('#view-contact').hidden)renderContact();}
  else if(act==='note'){const box=card.querySelector('.stfnote'); box.hidden=!box.hidden; if(!box.hidden)box.querySelector('textarea').focus();}
  else if(act==='media'){const u=prompt('Media URL (article, clip, photo, doc link):'); if(!u)return; const l=prompt('Label (optional):')||u.replace(/^https?:\/\//,'').slice(0,40); const md=(st.media||[]).concat([{u:u,l:l}]); setStf(id,'media',md); const wrap=card.querySelector('.stfmedia'); const k=md.length-1; wrap.insertAdjacentHTML('beforeend',`<span class=chip><a href="${esc(u)}" target=_blank rel=noopener>${esc(l)}</a><span class=x data-act=delmedia data-sid=${id} data-k=${k}>×</span></span>`);}
  else if(act==='delmedia'){const md=(st.media||[]); md.splice(+el.dataset.k,1); setStf(id,'media',md); const wrap=el.closest('.stfmedia'); if(wrap){wrap.innerHTML=md.map((mm,k)=>`<span class=chip><a href="${esc(mm.u)}" target=_blank rel=noopener>${esc(mm.l||mm.u)}</a><span class=x data-act=delmedia data-sid=${id} data-k=${k}>×</span></span>`).join('');}}
  else if(act==='openmem'){openMember(+el.dataset.mi); setView('member');}
});
document.addEventListener('change',e=>{
  if(e.target.classList&&e.target.classList.contains('stfnotebox')) setStf(e.target.dataset.sid,'note',e.target.value.trim());
});
document.addEventListener('input',e=>{
  if(e.target.hasAttribute&&e.target.hasAttribute('data-stfsearch')){
    const q=e.target.value.toLowerCase();
    e.target.parentElement.querySelectorAll('.stfcard').forEach(c=>{
      const sf=STFIDX[c.dataset.sid]; const hay=sf?(sf.s.n+' '+sf.s.t).toLowerCase():'';
      c.style.display=hay.includes(q)?'':'none';});
  }
});
function renderContact(){
  const groups={};
  Object.keys(STF).forEach(id=>{ if(STF[id].meet&&STFIDX[id]){ (groups[STFIDX[id].m]=groups[STFIDX[id].m]||[]).push(id); } });
  const mems=Object.keys(groups).sort();
  const inner=mems.length?mems.map(mn=>{
    const mi=STFIDX[groups[mn][0]].mi;
    return `<div class=memgrp><h3 data-act=openmem data-mi=${mi}>${esc(mn)} ▸</h3>`+groups[mn].map(id=>stfCard(STFIDX[id].s)).join('')+`</div>`;
  }).join(''):`<div class=empty>No meetings set up yet. Open a member's Staff section and hit “Set up meeting”.</div>`;
  const ngold=Object.keys(STF).filter(id=>STF[id].gold).length;
  $('#contactbody').innerHTML=`<h2>In contact</h2>
    <div style="color:var(--faint);font-size:12px;margin-bottom:8px">${mems.length} office(s) · ${Object.keys(groups).reduce((a,m)=>a+groups[m].length,0)} staffer(s) with meetings · ${ngold} contacted overall
    &nbsp; <button class=ghostbtn id=stfexport>⭳ Export staff state</button> <label class=ghostbtn for=stfimport>⭱ Import</label><input id=stfimport type=file accept=".json" hidden></div>${inner}`;
  const ex=$('#stfexport'); if(ex)ex.onclick=()=>{const b=new Blob([JSON.stringify(STF,null,1)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='staff_state.json';a.click();};
  const im=$('#stfimport'); if(im)im.onchange=e=>{const f=e.target.files[0];if(!f)return;const rd=new FileReader();rd.onload=()=>{try{const o=JSON.parse(rd.result);Object.keys(o).forEach(k=>{STF[k]=Object.assign(STF[k]||{},o[k]);});saveSTF();renderContact();alert('Imported staff state for '+Object.keys(o).length+' staffer(s).');}catch(err){alert('Invalid JSON.');}};rd.readAsText(f);};
}
updatePovHint();

/* ---------- init ---------- */
renderRanked();
const qp=new URLSearchParams(location.search).get('m');
if(qp&&byName[qp]!=null)openMember(byName[qp]); else setView('ranked');
</script></body></html>