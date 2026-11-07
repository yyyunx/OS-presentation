'use strict';
const $ = id => document.getElementById(id);
const scenes = {
 safety: {kicker:'01 / INVENTORY INTEGRITY',title:'Four fans. One last seat.',description:'Run the original C++ demos: four buyers compete for one ticket. Compare the complete check-and-decrement operation with and without a mutex.',caption:'Four buyers reach the ticket check. A mutex admits one buyer at a time.',conclusion:'Run the experiment to compare measured purchases and remaining inventory.'},
 connections100:{kicker:'02 / THE WAITING CROWD',title:'The rush before the sale.',description:'100 idle TCP connections per server: blocking on 8081 versus epoll on 8082. Successful connections are not ticket purchases. Both architectures need socket FDs.',caption:'Fans wait at the entrance. This animation illustrates waiting connections only.',conclusion:'Run to measure connections, failures, server threads, and total process FDs.'},
 connections500:{kicker:'02 / EPOLL ENCORE',title:'A bigger waiting crowd.',description:'500 idle connections to epoll on 8082 only. No BUY requests are sent. This is a connection experiment, not 500 successful purchases.',caption:'One event loop watches many waiting connections; each still needs an FD.',conclusion:'Run to measure 500 attempted idle connections. FD limits still apply.'},
 traffic:{kicker:'03 / ADMISSION & BACKPRESSURE',title:'Let the queue breathe.',description:'An independent local simulation: 1,000 incoming requests, four workers, and 10 ms simulated work. Protected pending queue capacity = 20 (excluding work in progress). No network ticket transactions.',caption:'Incoming → pending queue → four workers. Protected admission caps pending work at 20.',conclusion:'Run to compare queue policies. Processed + Rejected must equal Incoming.'}
};
let scene='safety', state={status:'Waiting',results:{}}, token='', pending=false, offline=false, requestError='';
const views = {};
function metric(label,value,kind=''){return `<div class="metric ${kind}"><strong>${value ?? '—'}</strong><small>${label}</small></div>`;}
function card(title,badge,content,note,single=false){return `<article class="card ${single?'single':''}"><h4>${title}</h4><span class="badge">${badge}</span><div class="numbers">${content}</div><p class="note">${note}</p></article>`;}
function bar(label,value,max,mint=false){return `<div class="bar-row"><span>${label}</span><div class="track"><div class="bar ${mint?'mint':''}" data-width="${value==null?0:Math.max(0,value)/max*100}"></div></div><strong>${value??'—'}</strong></div>`;}
function render(){
 const config=scenes[scene], current=views[scene] || {status:'Waiting',results:{},message:'Choose Run to collect real measurements.'};
 const r=current.results, running=state.status==='Running';
 $('scene-kicker').textContent=config.kicker; $('scene-title').textContent=config.title; $('scene-description').textContent=config.description;
 $('connection-options').hidden=!scene.startsWith('connections'); $('mode').value=scene.startsWith('connections')?scene:'connections100';
 $('status').textContent=current.status; $('status').className='status '+current.status;
 $('message').textContent=requestError || (offline?'Controller unavailable. Displayed values, if any, are historical. Reconnect or restart make demo-ui.':current.message);
 $('message').className='message '+(requestError||offline||current.status==='Error'?'error':'');
 $('run').disabled=running||pending||offline; $('reset').disabled=pending||offline;
 $('stop').disabled=!running||pending||offline;
 document.querySelectorAll('.tab').forEach(b=>b.classList.toggle('active',b.dataset.scene===scene || b.dataset.scene==='connections100'&&scene==='connections500'));
 $('provenance').textContent=(current.sampled_at ? `${current.status==='Running'&&!offline?'Latest actual sample':'Historical result'} · ${new Date(current.sampled_at*1000).toLocaleTimeString()}`:'No measurements yet · — means unavailable')+(current.run_id?` · Run ${current.run_id.slice(0,8)}`:'');
 $('logs').textContent=current.logs||'No process output yet.';
 $('animation-caption').textContent=config.caption;
 $('animation').classList.toggle('running',current.status==='Running'&&!offline);
 if($('animation').dataset.scene!==scene){$('animation').dataset.scene=scene; $('animation').innerHTML=scene==='safety'?'<span class="fan">A</span><span class="fan">B</span><span class="fan">C</span><span class="fan">D</span><span class="ticket">1 SEAT</span>':Array.from({length:scene==='traffic'?10:12},()=>'<span class="queue-slot"></span>').join('');}
 let cards='',bars='',conclusion=config.conclusion;
 if(scene==='safety'){
  for(const [key,title] of [['without','Without Mutex'],['with','With Mutex']]){
   const v=r[key]; cards+=card(title,'4 BUYERS / 1 TICKET',metric('Successful purchases',v?.purchases,'primary-number')+metric('Tickets remaining',v?.remaining)+metric('Overselling',v?(v.oversold?'YES':'NO'):'—',v?.oversold?'bad':'good'),v?'Parsed from completed C++ process output.':'Waiting for actual C++ output.');
  }
  if(r.with&&r.without) conclusion=`Measured: without mutex, ${r.without.purchases} purchases and ${r.without.remaining} tickets remain; with mutex, ${r.with.purchases} purchase and ${r.with.remaining} remain. Protect check + decrement together. The race demo forces the competing checks with a teaching rendezvous.`;
 }else if(scene==='traffic'){
  for(const [key,title] of [['uncontrolled','Uncontrolled'],['protected','Protected']]){
   const v=r[key]; cards+=card(title,key==='protected'?'PENDING CAPACITY = 20':'UNBOUNDED PENDING QUEUE',metric('Incoming',v?.Incoming)+metric('Processed',v?.Processed,'good')+metric('Rejected',v?.Rejected)+metric('Max Queue',v?.['Max queue size'],'primary-number'),v?`Conservation: ${v.Processed} + ${v.Rejected} = ${v.Incoming} ✓ · Workers: ${v['Worker threads']} · Queue drained`:'Local simulation summary appears when the process finishes.');
  }
  const max=Math.max(20,r.uncontrolled?.['Max queue size']||0,r.protected?.['Max queue size']||0);
  bars='<h4>Measured maximum pending queue · shared scale</h4>'+bar('Uncontrolled',r.uncontrolled?.['Max queue size'],max)+bar('Protected',r.protected?.['Max queue size'],max,true);
  if(r.protected&&r.uncontrolled) conclusion=`Protected peak queue: ${r.protected['Max queue size']} / 20. It processed ${r.protected.Processed} and rejected ${r.protected.Rejected}; their sum is ${r.protected.Incoming}. Bounded waiting trades admission for a controlled backlog. Rejection counts vary with scheduling.`;
 }else{
  const names=scene==='connections500'?['epoll_server']:['blocking_server','epoll_server'];
  for(const key of names){const v=r[key];cards+=card(key==='epoll_server'?'epoll / event loop':'Blocking / thread per client',`${scene==='connections500'?500:100} IDLE CONNECTION ATTEMPTS`,metric('Connected',v?.connected,'primary-number')+metric('Threads',v?.threads)+metric('Total FDs',v?.fds)+metric('Failures',v?.failures,v?.failures?'bad':''),v?`PID ${v.pid} · ${v.phase} · Baseline FDs ${v.baseline_fds}`:'Waiting for client output and Linux /proc sampling.',names.length===1);}
  for(const [field,label] of [['threads','Measured server threads'],['fds','Measured total process FDs']]){
   const max=Math.max(1,...names.map(n=>r[n]?.[field]||0)); bars+=`<h4>${label} · shared scale</h4>`+names.map(n=>bar(n==='epoll_server'?'epoll':'Blocking',r[n]?.[field],max,n==='epoll_server')).join('');
  }
  if(names.every(n=>r[n])) conclusion=scene==='connections500'?`Measured ${r.epoll_server.connected} idle connections, ${r.epoll_server.threads} thread(s), ${r.epoll_server.fds} total process FDs. Each accepted connection still consumes an FD. No tickets were purchased.`:`At the latest held samples: blocking used ${r.blocking_server.threads} threads; epoll used ${r.epoll_server.threads}. Total FDs: ${r.blocking_server.fds} vs ${r.epoll_server.fds}. epoll reduces waiting threads, not socket FDs. These connections did not purchase tickets.`;
 }
 if(current.status==='Error') conclusion='Experiment did not complete: '+current.message+'. Any displayed measurements are partial evidence; inspect Technical Logs before drawing a conclusion.';
 $('metrics').innerHTML=cards; $('bars').innerHTML=bars;
 document.querySelectorAll('[data-width]').forEach(e=>{e.style.width=e.dataset.width+'%';});
 $('conclusion').textContent=conclusion;
}
async function api(path,body){const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Demo-Token':token},body:JSON.stringify(body||{})});const data=await response.json();if(!response.ok)throw Error(data.error||'Request failed');return data;}
async function poll(){try{const response=await fetch('/api/state');if(!response.ok)throw Error('State unavailable');state=await response.json();offline=false;if(state.scene)views[state.scene]=state;render();}catch(e){offline=true;render();}}
async function act(path,body){requestError='';pending=true;render();try{const data=await api(path,body);state=data;if(path==='/api/reset'){Object.keys(views).forEach(k=>delete views[k]);}else if(data.scene)views[data.scene]=data;await poll();}catch(e){requestError=e.message;}finally{pending=false;render();}}
document.querySelectorAll('.tab').forEach(b=>b.addEventListener('click',()=>{scene=b.dataset.scene;render();}));
$('mode').addEventListener('change',e=>{scene=e.target.value;render();});
$('run').addEventListener('click',()=>act('/api/run',{scene}));$('stop').addEventListener('click',()=>act('/api/stop'));$('reset').addEventListener('click',()=>act('/api/reset'));
async function boot(){render();try{const response=await fetch('/api/session');if(!response.ok)throw Error('Session unavailable');token=(await response.json()).token;await poll();}catch(e){offline=true;render();}setInterval(poll,400);}
boot();
