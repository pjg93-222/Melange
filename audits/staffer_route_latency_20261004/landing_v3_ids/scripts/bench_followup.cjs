// Cost of the two follow-up searches on populations the size of the real ones, before (86631c454, read from git) and after (the worktree file).
//   node bench_followup.cjs <path to the worktree>
// 1. the record browser's filter() on 145,000 rows: five queries, median of 7 runs each, per worker.
// 2. the map's matchesQuery() over 20,000 nodes (the page's FULL_MAX_NODES): cold (index empty) and warm (index filled), per page.
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),{execFileSync}=require('node:child_process');
const root=process.argv[2];
const BEFORE='86631c454815533798eb1ad81136ddb1a76a23b9';
const show=rel=>execFileSync('git',['-C',root,'show',BEFORE+':'+rel],{encoding:'utf8',maxBuffer:1<<25});
const WORKER='fec/surfaces/staffer_live/staffer-inventory-worker.js',LIVE='fec/surfaces/staffer_live/staffer-live.js';
const read=rel=>fs.readFileSync(path.join(root,rel),'utf8');
const rand=(()=>{let a=12345;return()=>{a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};})();
const hex=n=>Array.from({length:n},()=>'0123456789abcdef'[Math.floor(rand()*16)]).join('');
const words=['Alex','Adams','Elodie','Gagne','Casey','Rivera','Jordan','Lee','Morgan','Quill','Priya','Nair','Pat','Orwell','Zed','Zeta','Beatrice','Hale','Staff','Cole','Porter'];
const pick=l=>l[Math.floor(rand()*l.length)];
const median=a=>{a=[...a].sort((x,y)=>x-y);return a[Math.floor(a.length/2)];};

// ---- 1. the record browser
const N=145000,people=[];
for(let i=0;i<N;i++){
  const id=i%3?'politico:'+[8,4,4,4,12].map(hex).join('-'):'hill:person:'+hex(10);
  people.push([id,pick(words)+' '+pick(words)+' '+(i%97),rand()<.5?'Director of '+pick(words):'',rand()<.5?'A00'+Math.floor(rand()*9999):'',rand()<.2?'HSBA':'',rand()<.2?'BANKING':'','Payroll|Politico',false,'person',false,'unknown','']);
}
async function worker(code){
  const pending=[],context=vm.createContext({onmessage:null,postMessage:()=>{},fetch:()=>new Promise(r=>pending.push(r))});
  vm.runInContext(code,context);
  const send=data=>context.onmessage({data});
  const loading=send({type:'load',epoch:0,text:'',kind:'person'});
  pending[0]({ok:true,json:async()=>({ready:true,people,total:N,people_total:N})});await loading;
  return send;
}
async function browser(){
  const whole=people[777][0],code=people.find(r=>r[3])[3];
  const queries=[['2 letters "ab"','ab'],['a name "alex adams"','alex adams'],['a whole node id',whole],['an upper-case whole id','  '+whole.toUpperCase()+' '],['a piece of an id "3f2a"','3f2a'],
    ['a whole member id',code],['a piece of a member id "a00"','a00'],['a whole committee id','HSBA']];
  console.log('record browser, rows',N,'(median of 7, ms)');
  const sources=[['before (86631c454)',show(WORKER)],['after',read(WORKER)]];
  for(const [label,q] of queries){
    const out=[];
    for(const [,code2] of sources){
      const send=await worker(code2),times=[];
      for(let k=0;k<7;k++){const t=performance.now();await send({type:'query',epoch:k+1,text:q,kind:'person'});times.push(performance.now()-t);}
      out.push(median(times));
    }
    console.log('  %s  before %s  after %s',label.padEnd(30),out[0].toFixed(0).padStart(5),out[1].toFixed(0).padStart(5));
  }
}

// ---- 2. the map's matchesQuery
function page(code){
  const elements=new Map(),ctx=new Proxy({},{get:(t,k)=>k in t?t[k]:()=>({width:0}),set:(t,k,v)=>{t[k]=v;return true;}});
  const element=id=>({id,children:[],textContent:'',className:'',hidden:false,disabled:false,style:{},dataset:{},append(...n){this.children.push(...n);},replaceChildren(...n){this.children=n;},addEventListener(){},
    setPointerCapture(){},getContext:()=>ctx,getBoundingClientRect:()=>({left:0,top:0,right:1000,bottom:700,width:1000,height:700})});
  const document={getElementById:id=>{if(!elements.has(id))elements.set(id,element(id));return elements.get(id);},createElement:tag=>element(tag)};
  const window={dispatchEvent(){}};
  const context=vm.createContext({document,window,history:{replaceState(){}},location:{href:'http://localhost/',origin:'http://localhost'},fetch:()=>new Promise(()=>{}),setTimeout:()=>0,clearTimeout(){},
    setInterval:()=>0,requestAnimationFrame:()=>0,performance:{now:()=>0},ResizeObserver:class{observe(){}},CustomEvent:class{},URL,AbortController});
  vm.runInContext(code.replace(/^(\s*setLayers\(defaults\);refresh\(\);setInterval\(poll,30000\);)/m,'  window.__test={matchesQuery,state};\n$1'),context);
  return window.__test;
}
function mapPage(){
  const M=20000,nodes=[];
  for(let i=0;i<M;i++)nodes.push({id:i%3?'politico:'+[8,4,4,4,12].map(hex).join('-'):'hill:person:'+hex(10),kind:'person',label:pick(words)+' '+pick(words)+' '+(i%97),
    source_summary:rand()<.5?'Director of '+pick(words)+' · last reported 2024-05-01':'',member_ids:rand()<.5?['A00'+Math.floor(rand()*9999)]:[],committee_ids:rand()<.2?['HSBA']:[],policy_ids:rand()<.2?['BANKING']:[]});
  console.log('map query filter, nodes',M,'(ms for one pass over every node; cold = index empty, warm = index filled; median of 7)');
  const queries=[['2 letters "ab"','ab'],['a name "alex adams"','alex adams'],['a whole node id',nodes[777].id],['a piece of an id "3f2a"','3f2a'],['a whole member id',nodes.find(n=>n.member_ids.length).member_ids[0]]];
  for(const [label,q] of queries){
    const row=[];
    for(const code of [show(LIVE),read(LIVE)]){
      const t=page(code);for(const n of nodes)t.state.nodes.set(n.id,n);
      const cold=[],warm=[];
      for(let k=0;k<7;k++){t.state.searchIndex.clear();t.state.query=q;let s=performance.now();for(const n of t.state.nodes.values())t.matchesQuery(n);cold.push(performance.now()-s);
        s=performance.now();for(const n of t.state.nodes.values())t.matchesQuery(n);warm.push(performance.now()-s);}
      row.push(median(cold),median(warm));
    }
    console.log('  %s  cold before %s after %s   warm before %s after %s',label.padEnd(26),row[0].toFixed(1).padStart(6),row[2].toFixed(1).padStart(6),row[1].toFixed(1).padStart(6),row[3].toFixed(1).padStart(6));
  }
}
(async()=>{await browser();mapPage();console.log('peak rss MB',Math.round(process.memoryUsage().rss/2**20));})();
