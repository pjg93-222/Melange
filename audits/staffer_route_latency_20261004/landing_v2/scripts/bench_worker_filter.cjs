// Cost of the record browser's filter() on a population the size of the real one: old filter (722a55ba7, embedded in the test) vs the new worker.
// usage: node bench_worker_filter.cjs <path to the worktree>
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=process.argv[2];
const source=fs.readFileSync(path.join(root,'fec/surfaces/staffer_live/staffer-inventory-worker.js'),'utf8');
const testSource=fs.readFileSync(path.join(root,'fec/tests/surfaces/test_staffer_inventory_worker_ids.cjs'),'utf8');
const OLD_FILTER=eval('String.raw`'+testSource.split('String.raw`')[1].split('`;')[0]+'`');
const rand=(()=>{let a=12345;return()=>{a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};})();
const hex=n=>Array.from({length:n},()=>'0123456789abcdef'[Math.floor(rand()*16)]).join('');
const words=['Alex','Adams','Elodie','Gagne','Casey','Rivera','Jordan','Lee','Morgan','Quill','Priya','Nair','Pat','Orwell','Zed','Zeta','Beatrice','Hale','Staff','Cole','Porter'];
const pick=l=>l[Math.floor(rand()*l.length)];
const N=145000,people=[];
for(let i=0;i<N;i++){
  const id=i%3?'politico:'+[8,4,4,4,12].map(hex).join('-'):'hill:person:'+hex(10);
  people.push([id,pick(words)+' '+pick(words)+' '+(i%97),rand()<.5?'Director of '+pick(words):'',rand()<.5?'A00'+Math.floor(rand()*9999):'','','','Payroll|Politico',false,'person',false,'unknown','']);
}
async function worker(oldFilter){
  const pending=[],context=vm.createContext({onmessage:null,postMessage:()=>{},fetch:()=>new Promise(r=>pending.push(r))});
  vm.runInContext(source,context);if(oldFilter)vm.runInContext(OLD_FILTER,context);
  const send=data=>context.onmessage({data});
  const loading=send({type:'load',epoch:0,text:'',kind:'person'});
  pending[0]({ok:true,json:async()=>({ready:true,people,total:N,people_total:N})});await loading;
  return send;
}
(async()=>{
  const whole=people[777][0];
  const queries=[['2 letters "ab"','ab'],['a name "alex adams"','alex adams'],['a whole id',whole],['an upper-case whole id','  '+whole.toUpperCase()+' '],['a piece of an id "3f2a"','3f2a']];
  console.log('rows',N);
  for(const [label,q] of queries){
    const out=[];
    for(const oldFilter of [true,false]){
      const send=await worker(oldFilter),times=[];
      for(let k=0;k<7;k++){const t=performance.now();await send({type:'query',epoch:k+1,text:q,kind:'person'});times.push(performance.now()-t);}
      times.sort((a,b)=>a-b);out.push(times[3]);
    }
    console.log('%s  old %s ms  new %s ms',label.padEnd(26),out[0].toFixed(0).padStart(5),out[1].toFixed(0).padStart(5));
  }
  console.log('peak rss MB',Math.round(process.memoryUsage().rss/2**20));
})();
