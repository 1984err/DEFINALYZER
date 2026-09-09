// Run with: node --test tests/dashboard_reader.test.cjs
// Exercise UI state without a browser, server, or AI provider.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const {readFileSync}=require('node:fs');
const {join}=require('node:path');
const vm=require('node:vm');

function setup(){
  const nodes=new Map(), classes=new Set(), listeners={};
  const document={
    body:{classList:{
      toggle(name,on){on?classes.add(name):classes.delete(name)},
      contains(name){return classes.has(name)},
    }},
    getElementById(id){
      if(!nodes.has(id))nodes.set(id,{
        hidden:false, attributes:{}, textContent:'',value:'',innerHTML:'',children:[],
        appendChild(child){this.children.push(child)},
        closest(){return this}, close(){this.open=false}, showModal(){this.open=true},
        setAttribute(name,value){this.attributes[name]=value},
        focus(){this.focused=true},
      });
      return nodes.get(id);
    },
    addEventListener(name,callback){listeners[name]=callback},
    querySelector(){return document.openDialog?{}:null},
    querySelectorAll(){return []},
    createElement(){return {}},
  };
  const context=vm.createContext({
    document, console, location:{hash:''},
    // Leave bootstrap pending so no network or background polling occurs.
    fetch:()=>new Promise(()=>{}), setTimeout(){}, setInterval(){},
  });
  vm.runInContext(readFileSync(join(__dirname,'../definalyzer/dashboard_assets/app.js'),'utf8'),context);
  vm.runInContext(readFileSync(join(__dirname,'../definalyzer/dashboard_assets/reports-v2.js'),'utf8'),context);
  return {document, nodes, classes, listeners, context};
}

test('jobs needing attention are terminal and never display Working',()=>{
  const {context}=setup();
  const html=vm.runInContext(`jobProgress({status:'needs_attention'})`,context);
  assert.match(html,/Needs attention/);
  assert.doesNotMatch(html,/Working|indeterminate/);
});

test('stop controls distinguish cancellation requested from stopped',()=>{
  const {context,nodes}=setup();
  vm.runInContext(`state.jobs=[{job_id:'abc',action:'analyze',status:'running',project:'pump-fun',messages:[]}];renderJobs();`,context);
  assert.match(nodes.get('jobs').innerHTML,/data-job-stop="abc"/);
  assert.match(nodes.get('active-progress').innerHTML,/>Stop</);
  vm.runInContext(`state.jobs[0].status='stopping';renderJobs();`,context);
  assert.match(nodes.get('jobs').innerHTML,/disabled>Stopping/);
  assert.equal(nodes.get('job-count').textContent,1);
  vm.runInContext(`state.jobs[0].status='cancelled';renderJobs();`,context);
  assert.match(nodes.get('jobs').innerHTML,/Stopped/);
  assert.doesNotMatch(nodes.get('jobs').innerHTML,/data-job-stop|Working/);
  assert.equal(nodes.get('active-progress').hidden,true);
});

test('stop click posts cancellation once and does not restart research',async()=>{
  const {context,document}=setup();
  const button={dataset:{jobStop:'abc'},disabled:false};
  document.querySelectorAll=selector=>selector==='[data-job-stop]'?[button]:[];
  vm.runInContext(`state.jobs=[{job_id:'abc',status:'running'}];api=async(path,options)=>{globalThis.cancelRequest={path,options};return {job:{job_id:'abc',status:'stopping'}}};renderJobs=()=>{};pollJobs=()=>{};bindStopJobs();`,context);
  await button.onclick();
  assert.equal(button.disabled,true);
  assert.equal(vm.runInContext('cancelRequest.path',context),'/api/jobs/abc/cancel');
  assert.equal(vm.runInContext('cancelRequest.options.method',context),'POST');
  assert.equal(vm.runInContext('state.jobs[0].status',context),'stopping');
});

test('saved V2 reports remain readable without preparation or mutation controls',()=>{
  const {context,document}=setup();
  const card={innerHTML:''};
  document.querySelectorAll=selector=>selector==='#report-list .report-card'?[card]:[];
  vm.runInContext(`state.reports=[{report_id:'v2-saved',schema_version:2,title:'Saved review',status:'needs_attention',revision:1,report_page:'Report.md',analyst_notes_page:'Notes.md',actions:{generate_draft:{available:true}},recovery:{kind:'prepare'}}];renderReports();`,context);
  assert.match(card.innerHTML,/Read report/);
  assert.match(card.innerHTML,/Compare versions/);
  assert.doesNotMatch(card.innerHTML,/data-report-action="(?:prepare|draft|revise|refresh|edit|finalize|export)"/);
});

test('new reports use the normal workflow despite leftover V2 preparation',async()=>{
  const {context}=setup();
  vm.runInContext(`state.project={slug:'example'};state.reports=[{report_id:'v2-saved',schema_version:2,recovery:{kind:'prepare'}}];openForm=value=>globalThis.form=value;
    api=async(path,options)=>{globalThis.request={path,body:JSON.parse(options.body)};return {report:{report_id:'review',schema_version:1}}};
    toast=()=>{};startJob=async(action,payload)=>{globalThis.dispatched={action,payload}};newReportForm();`,context);
  assert.equal(vm.runInContext('form.title',context),'New report');
  await vm.runInContext(`form.handler({title:'Review',mode:'question',question:'What risks are documented?'})`,context);
  assert.equal(vm.runInContext('request.path',context),'/api/projects/example/reports');
  assert.notEqual(vm.runInContext('request.body.schema_version',context),2);
  assert.equal(vm.runInContext('dispatched.action',context),'report-generate');
  assert.equal(vm.runInContext('dispatched.payload.report_id',context),'review');
});

test('V2 actions and direct preparation cannot dispatch jobs',async()=>{
  const {context}=setup();
  vm.runInContext(`state.reports=[{report_id:'v2-saved',schema_version:2}];startReportJob=()=>{throw new Error('Unexpected dispatch')};`,context);
  for(const action of ['prepare','repair','draft','refresh','revise','edit','reconcile','finalize','export'])
    await assert.rejects(vm.runInContext(`openReportAction('${action}','v2-saved')`,context),/read-only/);
  await assert.rejects(vm.runInContext('openResearchPreparation()',context),/disabled/);
});

test('completed report generation opens that report and keeps the selected project',async()=>{
  const {context}=setup();
  vm.runInContext(`state.project={slug:'northstar'};state.pendingReport={project:'northstar',id:'v2-review'};
    api=async()=>({jobs:[]});renderJobs=()=>{};selectedSupplyTarget=()=>null;renderSupplyAction=()=>{};
    selectProject=async slug=>{globalThis.project=slug;state.reports=[{report_id:'v2-review',report_page:'Reports/review/Report.md'}]};
    openPage=async path=>globalThis.opened=path;`,context);
  await vm.runInContext('pollJobs()',context);
  assert.equal(vm.runInContext('project',context),'northstar');
  assert.equal(vm.runInContext('opened',context),'Reports/review/Report.md');
  assert.equal(vm.runInContext('state.pendingReport',context),null);
});

test('asset navigation uses names and does not open its originating protocol',async()=>{
  const {context,nodes}=setup();
  vm.runInContext(`state.projects=[{slug:'harbor',name:'Harbor Protocol',entity_type:'protocol'}];
    state.tokens=[{asset_id:'a'.repeat(32),symbol:'HBR',title:'Harbor Governance (HBR)',path:'Tokens/harbor--id/Index.md',projects:['harbor'],contexts:[]}];
    openPage=async path=>{state.page={path}};
    renderProjects();`,context);
  assert.match(nodes.get('projects').innerHTML,/Harbor Governance \(HBR\)/);
  await vm.runInContext(`openTokenPage('Tokens/harbor--id/Index.md')`,context);
  assert.equal(nodes.get('project-title').textContent,'Harbor Governance (HBR)');
  assert.equal(vm.runInContext('state.project',context),null);
  assert.equal(nodes.get('tools-toggle').hidden,true);
  assert.equal(nodes.get('markdown').children[0].textContent,'Research this asset');
});

test('an asset with its own project has one navigation entry and opens that context',async()=>{
  const {context,nodes}=setup();
  vm.runInContext(`state.projects=[{slug:'token-project',name:'Harbor Governance (HBR)',entity_type:'token'}];
    state.tokens=[{symbol:'HBR',title:'Harbor Governance (HBR)',path:'Tokens/id/Index.md',projects:['token-project'],subject_projects:['token-project']}];
    selectProject=async(slug,path)=>{globalThis.selected={slug,path}};
    renderProjects();`,context);
  assert.equal((nodes.get('projects').innerHTML.match(/Harbor Governance \(HBR\)/g)||[]).length,1);
  await vm.runInContext(`openTokenPage('Tokens/id/Index.md')`,context);
  assert.equal(vm.runInContext('selected.slug',context),'token-project');
  assert.equal(vm.runInContext('selected.path',context),'Tokens/id/Index.md');
});

test('expand and restore update layout and accessible button state',()=>{
  const {nodes,classes}=setup();
  const button=nodes.get('expand-reader');
  button.onclick();
  assert.equal(classes.has('reader-expanded'),true);
  assert.equal(button.attributes['aria-pressed'],'true');
  assert.equal(button.textContent,'Restore layout');
  button.onclick();
  assert.equal(classes.has('reader-expanded'),false);
  assert.equal(button.attributes['aria-pressed'],'false');
  assert.equal(button.textContent,'Expand page');
});

test('Escape restores layout and returns focus to the toggle',()=>{
  const {nodes,classes,listeners}=setup();
  const button=nodes.get('expand-reader');
  button.onclick();
  listeners.keydown({key:'Escape'});
  assert.equal(classes.has('reader-expanded'),false);
  assert.equal(button.focused,true);
});

test('Escape belongs to an open dialog before the expanded reader',()=>{
  const {document,nodes,classes,listeners}=setup();
  nodes.get('expand-reader').onclick();
  document.openDialog=true;
  listeners.keydown({key:'Escape'});
  assert.equal(classes.has('reader-expanded'),true);
  document.openDialog=false;
  listeners.keydown({key:'Escape'});
  assert.equal(classes.has('reader-expanded'),false);
});

test('an empty reader cannot enter expanded mode',()=>{
  const {document,nodes,classes}=setup();
  document.getElementById('reader').hidden=true;
  nodes.get('expand-reader').onclick();
  assert.equal(classes.has('reader-expanded'),false);
});

test('token clicks open populated research with the token heading and no duplicate identity page',async()=>{
  const {context,nodes}=setup();
  vm.runInContext(`state.tokens=[{asset_id:'a'.repeat(32),symbol:'HBR',title:'Harbor Governance (HBR)',path:'Tokens/id/Index.md',contexts:[{path:'Tokens/id/Contexts/harbor.md',title:'Harbor',project:'harbor'}]}];
    openPage=async path=>{state.page={path};document.getElementById('markdown').innerHTML=path.endsWith('harbor.md')?'Saved allocation, emissions and utility':'Identity only'};`,context);
  await vm.runInContext(`openTokenPage('Tokens/id/Index.md')`,context);
  assert.equal(nodes.get('markdown').innerHTML,'Saved allocation, emissions and utility');
  assert.equal(nodes.get('project-title').textContent,'Harbor Governance (HBR)');
  assert.equal(vm.runInContext('state.pages.length',context),1);
  assert.equal(nodes.get('markdown').children.length,0);
  assert.match(nodes.get('projects').innerHTML,/project-link active/);
});

test('supply action is visible on token research and queues only that asset in its source project',async()=>{
  const {context,nodes}=setup();
  vm.runInContext(`state.tokens=[{asset_id:'selected-id',title:'Harbor (HBR)',kind:'token',path:'Tokens/id/Index.md',contexts:[{path:'Tokens/id/Contexts/harbor.md',project:'harbor'}]}];
    state.page={path:'Tokens/id/Contexts/harbor.md'};
    api=async(path,options)=>{globalThis.request={path,payload:JSON.parse(options.body)};return {job:{action:'market-data',status:'queued',project:'harbor'}}};
    renderJobs=()=>{};toast=()=>{};pollJobs=()=>{};renderSupplyAction();`,context);
  assert.equal(nodes.get('refresh-token-supply').hidden,false);
  await nodes.get('refresh-token-supply').onclick();
  assert.equal(vm.runInContext('request.path',context),'/api/projects/harbor/jobs');
  assert.equal(vm.runInContext('request.payload.asset_id',context),'selected-id');
  assert.equal(vm.runInContext('request.payload.refresh',context),true);
  assert.equal(nodes.get('refresh-token-supply').disabled,true);
  vm.runInContext(`state.page={path:'Protocols/Harbor/Index.md'};renderSupplyAction()`,context);
  assert.equal(nodes.get('refresh-token-supply').hidden,true);
  assert.equal(vm.runInContext(`tools.some(row=>row[0]==='market-data')`,context),false);
});

test('native coin research labels the supply button correctly',()=>{
  const {context,nodes}=setup();
  vm.runInContext(`state.coins=[{asset_id:'coin-id',kind:'coin',path:'Coins/id/Index.md',contexts:[{path:'Coins/id/Contexts/chain.md',project:'chain'}]}];state.page={path:'Coins/id/Contexts/chain.md'};renderSupplyAction();`,context);
  assert.equal(nodes.get('refresh-token-supply').hidden,false);
  assert.equal(nodes.get('refresh-token-supply').textContent,'Refresh coin supply');
});

test('completed supply refresh reloads the visible token page without switching to its protocol',async()=>{
  const {context}=setup();
  vm.runInContext(`state.tokens=[{asset_id:'id',path:'Tokens/id/Index.md',contexts:[{path:'Tokens/id/Contexts/protocol.md',project:'protocol'}]}];
    state.page={path:'Tokens/id/Contexts/protocol.md'};
    state.project=null;api=async()=>({jobs:[]});renderJobs=()=>{};
    openPage=async path=>{globalThis.reloaded=path};
    selectProject=async()=>{throw new Error('Must stay on token page')};`,context);
  await vm.runInContext('pollJobs()',context);
  assert.equal(vm.runInContext('reloaded',context),'Tokens/id/Contexts/protocol.md');
});

test('leftover scope never displays experimental controls',()=>{
  const {context,nodes}=setup();
  vm.runInContext(`state.scope={researching:'Example',research_retry:{unfinished_batches:5}};renderScope();`,context);
  assert.equal(nodes.get('scope-summary').hidden,true);
  assert.equal(vm.runInContext("tools.some(row=>row[0]==='scope')",context),false);
});

test('source viewer shows escaped original passages after one click',async()=>{
  const {context,document,nodes}=setup();
  const link={getAttribute:()=>'/api/projects/northstar/facts/'+'a'.repeat(64)};
  document.querySelectorAll=selector=>selector==='.fact-source'?[link]:[];
  document.getElementById('markdown').classList={toggle(){}};
  document.getElementById('fact-dialog').showModal=function(){this.open=true};
  vm.runInContext(`renderPages=()=>{};renderSupplyAction=()=>{};
    api=async path=>path.startsWith('/api/page')?{title:'Architecture',path:'Architecture.md',html:'Saved research'}:
      {subject:'Northstar',statement:'Checked claim',evidence:[{path:'core.md',start_line:1,end_line:2,quote:'<img src=x onerror=alert(1)>',context:'Full original context'}]};`,context);
  await vm.runInContext(`openPage('Architecture.md')`,context);
  await link.onclick({preventDefault(){}});
  assert.equal(nodes.get('fact-dialog').open,true);
  assert.equal(nodes.get('fact-title').textContent,'Source support');
  assert.match(nodes.get('fact-content').innerHTML,/Full original context/);
  assert.match(nodes.get('fact-content').innerHTML,/&lt;img/);
  assert.doesNotMatch(nodes.get('fact-content').innerHTML,/<img/);
});

test('comparison opens a readable diff without modifying the page',async()=>{
  const {context,document,nodes}=setup();
  const link={getAttribute:()=>'/api/projects/northstar/research-diff/architecture'};
  document.querySelectorAll=selector=>selector==='.research-comparison'?[link]:[];
  document.getElementById('markdown').classList={toggle(){}};
  document.getElementById('fact-dialog').showModal=function(){this.open=true};
  vm.runInContext(`renderPages=()=>{};renderSupplyAction=()=>{};
    api=async path=>path.startsWith('/api/page')?{title:'Architecture',path:'Architecture.md',html:'Saved research'}:{diff:'-Original notes\\n+Supported claim'};`,context);
  await vm.runInContext(`openPage('Architecture.md')`,context);
  await link.onclick({preventDefault(){}});
  assert.equal(nodes.get('fact-title').textContent,'Compare changes');
  assert.match(nodes.get('fact-content').innerHTML,/-Original notes/);
  assert.equal(nodes.get('markdown').innerHTML,'Saved research');
});

test('delete works for saved V2 reports without generation',async()=>{
 const {context}=setup();
 vm.runInContext(`state.project={slug:'example'};state.reports=[{report_id:'v2-old',schema_version:2,title:'Old report'}];openForm=value=>globalThis.form=value;refreshReports=async()=>{};toast=()=>{};api=async(path,options)=>{globalThis.deleted={path,options};return {}};`,context);
 await vm.runInContext("openReportAction('delete','v2-old')",context);
 assert.equal(vm.runInContext('form.submit',context),'Delete report');
 await vm.runInContext('form.handler()',context);
 assert.equal(vm.runInContext('deleted.path',context),'/api/projects/example/reports/v2-old/delete');
});
test('clear finished refreshes activity without cancelling active work',async()=>{
 const {context}=setup();
 vm.runInContext(`api=async(path,options)=>{globalThis.cleared={path,options};return {cleared:2,jobs:[{job_id:'active',status:'running'}]}};renderJobs=()=>{};toast=()=>{};`,context);
 await vm.runInContext('clearFinishedActivity()',context);
 assert.equal(vm.runInContext('cleared.path',context),'/api/jobs/clear');
 assert.equal(vm.runInContext('state.jobs[0].status',context),'running');
});


test('normal reports offer one generation action and direct PDF download before finalization',()=>{
  const {context,nodes}=setup();
  vm.runInContext(`state.project={slug:'example'};state.reports=[{report_id:'one',title:'One',status:'scoped',actions:{generate:{available:true}}}];renderReports();`,context);
  assert.match(nodes.get('report-list').innerHTML,/Generate report/);
  assert.doesNotMatch(nodes.get('report-list').innerHTML,/Prepare evidence|Generate draft|Download PDF/);
  vm.runInContext(`state.reports[0]={report_id:'one',title:'One',status:'draft',readiness:'partial',report_page:'Reports/One/Report.md',actions:{}};renderReports();`,context);
  assert.match(nodes.get('report-list').innerHTML,/Download PDF/);
  assert.match(nodes.get('report-list').innerHTML,/reports\/one\/download.pdf/);
  vm.runInContext(`state.reports[0].readiness='insufficient';renderReports();`,context);
  assert.doesNotMatch(nodes.get('report-list').innerHTML,/Download PDF/);
});

test('new report form starts the combined workflow',async()=>{
  const {context}=setup();
  vm.runInContext(`state.project={slug:'example'};openForm=options=>globalThis.form=options;api=async()=>({report:{report_id:'new-report'}});startReportJob=async(...args)=>globalThis.started=args;newReportForm();`,context);
  assert.equal(vm.runInContext('form.submit',context),'Generate report');
  await vm.runInContext('form.handler({title:"New report",mode:"full_review"})',context);
  assert.equal(vm.runInContext('JSON.stringify(started)',context),'["generate","new-report"]');
});
