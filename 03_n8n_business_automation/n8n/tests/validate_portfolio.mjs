// Offline portfolio validation and presentation. Never invokes provider APIs.
import assert from 'node:assert/strict';
import {readFileSync,readdirSync,existsSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import vm from 'node:vm';
import {clientCases} from './validate_clients.mjs';
import {run,regressionCases} from './validate_workflows.mjs';
import {input as validateInput} from '../../scripts/validate.mjs';
import {loadConfig} from '../../scripts/client_config.mjs';
import {buildClient} from '../../scripts/build_client_workflow.mjs';

const root=fileURLToPath(new URL('../../',import.meta.url));
const read=p=>readFileSync(path.join(root,p),'utf8').replace(/^\uFEFF/,'');
const json=p=>JSON.parse(read(p));
const config=n=>loadConfig(path.join(root,`config/client_config.${n}.json`));
const support=buildClient(config('support-demo')),salesConfig=config('sales-demo');
const sales=buildClient(salesConfig);
const enabled=structuredClone(salesConfig);enabled.features.email_enabled=true;
const sending=buildClient(enabled).core;
const payload=n=>json(`demo/sample_payloads/${n}_request.json`);
const show=process.argv.includes('--show-demo');
let cases=0;
function check(fn){fn();cases++;}
function display(name,r){if(show)console.log(JSON.stringify({mode:'OFFLINE_SIMULATION',scenario:name,...r}));}
function present(name,r){display(name,{result:r.result,writes:r.writes,fake_sends:r.sent,ai_calls:r.aiCalls,synthetic_row:r.rows[0]?Object.fromEntries(['request_type','classification','route','status','email_status','response_version','sent_at','ai_status'].map(k=>[k,r.rows[0][k]])):null});}

check(()=>{const p=payload('support');validateInput(p);const r=run({workflow:support.core,input:p});assert.equal(r.result.route,'support_desk');assert.equal(r.result.status,'logged');assert.equal(r.result.email_status,'disabled');assert.equal(r.sent,0);assert.equal(r.aiCalls,0);assert.equal(r.writes,1);present('DEMO_1',r);});
check(()=>{const p=payload('sales');validateInput(p);const r=run({workflow:sales.core,input:p});assert.equal(r.result.route,'sales_team');assert.equal(r.result.email_status,'disabled');assert.equal(r.rows[0].response_version,'sales-ack-v1');assert.equal(r.sent,0);present('DEMO_2',r);});
let delivered;
check(()=>{delivered=run({workflow:sending,input:payload('sales')});assert.equal(delivered.result.status,'completed');assert.equal(delivered.sent,1);assert(delivered.rows[0].sent_at);const prepared=delivered.history['Prepare Business Response'][0].json;assert.equal(prepared.subject,'We received your sales inquiry');assert(prepared.body.includes('Example Sales Co'));assert(prepared.body.includes('This acknowledgement does not confirm any purchase, refund or service commitment.'));present('DEMO_3',delivered);display('DEMO_3_CONTENT',{subject:prepared.subject,body:prepared.body});});
check(()=>{assert.deepEqual(payload('duplicate'),payload('sales'));const r=run({workflow:sending,input:payload('duplicate'),rows:delivered.rows});assert.equal(r.result.status,'duplicate');assert.equal(r.result.action,'reuse');assert.equal(r.result.email_status,'sent');assert.equal(r.sent,0);assert.equal(r.writes,0);assert.deepEqual(r.rows,delivered.rows);present('DEMO_4',r);});
check(()=>{const c=config('support-demo');c.features.ai_enabled=true;c.ai.model='test-model';const r=run({workflow:buildClient(c).core,input:payload('support'),ai:'network'});assert.equal(r.result.route,'support_desk');assert.equal(r.result.logged,true);assert.equal(r.rows[0].ai_status,'unavailable');assert.equal(r.sent,0);present('DEMO_5',r);});
check(()=>{const r=run({workflow:support.core,input:payload('support'),fail:'Log Business Request'});assert.equal(r.result.logged,false);assert.equal(r.result.status,'failed');assert.equal(r.result.result_summary,'operation_failed');assert.equal(r.sent,0);present('DEMO_6',r);});
check(()=>{const r=run({workflow:sending,input:payload('sales'),gmail:'clear_failure'});assert.equal(r.result.status,'failed_safe');assert.equal(r.result.email_status,'not_sent');assert.equal(r.result.result_summary,'send_failed');assert.equal(r.rows[0].sent_at,'');assert.equal(r.sent,0);present('DEMO_7',r);});
check(()=>{const r=run({workflow:sending,input:payload('sales'),gmail:'timeout_after_accept'});assert.equal(r.result.status,'needs_reconciliation');assert.equal(r.result.email_status,'unknown');assert.equal(r.result.result_summary,'reconciliation_required');assert.equal(r.attempts['Send Business Email'],1);present('DEMO_8',r);});
check(()=>{
  let name='Error Trigger',items=[{json:{execution:{lastNodeExecuted:'Prepare Final Status',mode:'webhook'}}}];const visited=[];
  while(name){visited.push(name);const n=sales.handler.nodes.find(n=>n.name===name);let port=0;
    const context={$input:{first:()=>items[0]},$json:items[0].json};
    if(n.type.endsWith('.code'))items=vm.runInNewContext(`(function(){${n.parameters.jsCode}})()`,context,{timeout:1000});
    if(n.type.endsWith('.if'))port=items[0].json.send?0:1;
    assert(!n.type.endsWith('.gmail'),'Disabled handler cannot send');
    name=sales.handler.connections[name]?.main[port]?.[0]?.node;
  }
  assert.deepEqual(visited.slice(-2),['Notification Disabled','Notification Outcome']);assert.equal(items[0].json.notification_status,'disabled');display('DEMO_9',{result:items[0].json,fake_sends:0});
});
check(()=>{const p=payload('invalid');assert.throws(()=>validateInput(p));const r=run({workflow:sales.core,input:p});assert.equal(r.result.status,'rejected');assert.equal(r.result.request_id,null);assert.equal(r.writes,0);assert.equal(r.sent,0);assert.equal(r.aiCalls,0);present('INVALID_REQUEST',r);});

const required=['README.md','docs/PORTFOLIO_CASE_STUDY.md','docs/CLIENT_FEATURE_SUMMARY.md','demo/DEMO_SCENARIOS.md','demo/DEMO_RUNBOOK.md','docs/PORTFOLIO_SCREENSHOT_GUIDE.md','docs/EVIDENCE_INDEX.md','docs/FINAL_ACCEPTANCE_MATRIX.md','docs/ARCHITECTURE.md','docs/PORTFOLIO_SNIPPETS.md','docs/CLIENT_HANDOFF_CHECKLIST.md','docs/PRODUCTION_READINESS_CHECKLIST.md','docs/RELEASE_NOTES_BUILD_05.md','n8n/evidence/BUILD_5_FINAL_VALIDATION.md'];
check(()=>{for(const file of required)assert(existsSync(path.join(root,file)),file);});
function filesIn(dir=''){
  const out=[];
  for(const entry of readdirSync(path.join(root,dir),{withFileTypes:true})){
    const p=path.posix.join(dir,entry.name);
    assert(!entry.isSymbolicLink(),`${p}: symlink requires review`);
    if(entry.isDirectory()){assert(!['node_modules','.venv','__pycache__'].includes(entry.name),`${p}: local runtime artifact`);out.push(...filesIn(p));}else out.push(p);
  }
  return out;
}
const files=filesIn();
check(()=>{for(const file of files.filter(p=>p.endsWith('.md'))){const content=read(file).replace(/```[\s\S]*?```/g,'');for(const m of content.matchAll(/\[[^\]]*\]\(([^)]+)\)/g)){
  const link=m[1];if(/^(https?:|mailto:|#)/.test(link))continue;
  const dest=path.resolve(root,path.dirname(file),decodeURIComponent(link.split('#')[0]));
  assert(dest.startsWith(root)&&existsSync(dest),`${file}: broken local link`);
}}});
check(()=>{for(const m of read('docs/ARCHITECTURE.md').matchAll(/```mermaid\n([\s\S]*?)```/g)){
  assert(m[1].startsWith('flowchart TD\n'));let edges=0;
  for(const line of m[1].trim().split('\n').slice(1)){
    assert(/^\s*\w+(?:\[[^\]]+\]|\{[^}]+\})?\s+(?:-->|-\.->)(?:\|[^|]+\|)?\s*\w+(?:\[[^\]]+\]|\{[^}]+\})?\s*$/.test(line),'Mermaid edge syntax sanity');edges++;
  }assert(edges>0);
}});
check(()=>{
  const matrix=read('docs/FINAL_ACCEPTANCE_MATRIX.md'),index=read('docs/EVIDENCE_INDEX.md');
  for(const file of ['BUILD_2_MANUAL_ACCEPTANCE.md','BUILD_3_LIVE_ACCEPTANCE.md','BUILD_4_LIVE_ACCEPTANCE.md','BUILD_5_FINAL_VALIDATION.md']){assert(index.includes(file));assert(matrix.includes(file));}
  assert(matrix.includes('no real OpenAI call'));assert(matrix.includes('enabled alerts not live-claimed'));assert(matrix.includes('offline packaging only'));
  for(const [file,label] of [['BUILD_3_LIVE_ACCEPTANCE.md','TEST_D_GMAIL_CLEAR_FAILURE: PASS'],['BUILD_3_LIVE_ACCEPTANCE.md','TEST_H_DUPLICATE_AFTER_RECONCILIATION: PASS'],['BUILD_4_LIVE_ACCEPTANCE.md','TEST_E_SALES_ACK_CONTENT: PASS'],['BUILD_4_LIVE_ACCEPTANCE.md','TEST_F_SALES_DUPLICATE_GUARD: PASS']])assert(read('n8n/evidence/'+file).includes(label));
});
check(()=>{
  const generated=files.filter(p=>p.startsWith('n8n/generated/')&&p.endsWith('.json'));
  const before=generated.map(p=>read(p).replaceAll('\r\n','\n'));
  for(let round=0;round<2;round++){
    for(const client of ['support-demo','sales-demo'])execFileSync(process.execPath,['scripts/build_client_workflow.mjs',`config/client_config.${client}.json`],{cwd:root});
    generated.forEach((p,i)=>assert.equal(read(p).replaceAll('\r\n','\n'),before[i],`${p}: generation drift`));
  }
});
check(()=>{
  const issues=[];
  for(const file of files){
    if(/(?:^|\/)\.env(?:$|\.)/.test(file)&&!file.endsWith('.env.example'))issues.push([file,'local environment artifact']);
    if(/(?:raw_exports|credentials)\/|\.(?:png|jpe?g|gif|webp|db|sqlite\w*|pem|key|tmp|log)$/i.test(file))issues.push([file,'private or unreviewed artifact']);
    const text=read(file);
    if(/sk-[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{30,}|ya29\.[A-Za-z0-9_-]+|Bearer\s+[A-Za-z0-9_.-]{20,}|Basic\s+[A-Za-z0-9+/=]{16,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY/.test(text))issues.push([file,'secret pattern']);
    if(/["']?(?:api_key|access_token|refresh_token|client_secret|password)["']?\s*[:=]\s*["'][A-Za-z0-9_./+=-]{16,}["']/i.test(text))issues.push([file,'secret assignment']);
    if(/docs\.google\.com\/spreadsheets\/d\/[A-Za-z0-9_-]{20,}/.test(text))issues.push([file,'document identifier']);
    for(const m of text.matchAll(/[\w.+-]+@([\w.-]+\.[A-Za-z]{2,})/g))if(m[1].toLowerCase()!=='example.com')issues.push([file,'private email']);
    if(file.endsWith('.json')){let x;try{x=JSON.parse(text);}catch{issues.push([file,'invalid JSON']);continue;}
      if(x.nodes)for(const n of x.nodes){if(n.credentials||n.webhookId)issues.push([file,'credential or account binding']);if(n.type.endsWith('.googleSheets')&&n.parameters.documentId?.value!=='YOUR_GOOGLE_SHEET_ID')issues.push([file,'document identifier']);}
    }
  }
  for(const [file,category] of issues)console.error(`${file}: ${category}`);
  assert.equal(issues.length,0,'Filesystem secret/privacy/hygiene review failed; values withheld');
});
console.log(`PASS: ${cases} portfolio checks, including actual sample scenarios, local links, Mermaid syntax sanity, evidence scope, deterministic CLI generation and full-project scan.`);
console.log(`TESTS_COLLECTED: ${regressionCases+clientCases+cases}; TESTS_PASSED: ${regressionCases+clientCases+cases}; TESTS_FAILED: 0`);
