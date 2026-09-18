// Executes the actual exported Code nodes and expressions with fake providers.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import crypto from 'node:crypto';
import {output as validateOutput} from '../../scripts/validate.mjs';
const wf=JSON.parse(readFileSync(new URL('../workflow_core/business_automation_core.sanitized.json',import.meta.url),'utf8'));
const fixture=JSON.parse(readFileSync(new URL('../../demo/contracts.json',import.meta.url),'utf8'));
const nodes=new Map(wf.nodes.map(n=>[n.name,n]));
const children=(name,port)=> (port===undefined ? wf.connections[name]?.main.flat() : wf.connections[name]?.main[port])?.map(e=>e.node)??[];
function reachable(start,target,blocked=new Set()) {
  const todo=[start],seen=new Set();
  while(todo.length){const n=todo.shift();if(blocked.has(n)||seen.has(n))continue;if(n===target)return true;seen.add(n);todo.push(...children(n));}return false;
}
assert.equal(nodes.size,wf.nodes.length);assert.equal(wf.active,false);
assert.deepEqual(wf.pinData,{});assert.equal(wf.settings.saveDataErrorExecution,'none');assert.equal(wf.settings.saveManualExecutions,false);
for(const n of wf.nodes){
  assert(reachable('Webhook Intake',n.name),`unreachable ${n.name}`);
  assert(!n.credentials&&!n.webhookId);
  if(n.type.endsWith('.code'))new vm.Script(n.parameters.jsCode.replace(/^return /,''));
  if(n.type.endsWith('.googleSheets')) {
    assert.equal(n.parameters.documentId.value,'YOUR_GOOGLE_SHEET_ID');assert.equal(n.parameters.sheetName.value,'Requests');
    assert.equal(n.retryOnFail,true);assert.equal(n.maxTries,3);assert.equal(n.waitBetweenTries,2000);
    if(n.parameters.operation==='read'){assert.equal(n.parameters.filtersUI.values[0].lookupColumn,'request_id');assert.equal(n.parameters.options.returnFirstMatch,false);}
    else {assert.deepEqual(n.parameters.columns.matchingColumns,['request_id']);assert.equal(n.parameters.options.cellFormat,'RAW');assert(!('message' in n.parameters.columns.value));}
  }
  if(n.onError==='continueErrorOutput')assert(children(n.name,1).length===1,`missing error branch ${n.name}`);
}
for(const [name,ports] of Object.entries(wf.connections)){assert(nodes.has(name));for(const lane of ports.main)for(const e of lane)assert(nodes.has(e.node));}
assert.equal(nodes.get('Webhook Intake').parameters.authentication,'basicAuth');
assert.equal(nodes.get('Webhook Intake').parameters.httpMethod,'POST');
assert.equal(nodes.get('Webhook Intake').parameters.responseMode,'responseNode');
assert.deepEqual(children('Valid Request?',1),['Prepare Invalid Result']);
for(const n of wf.nodes.filter(n=>['httpRequest','gmail','googleSheets'].some(t=>n.type.endsWith('.'+t))))assert(!reachable('Prepare Invalid Result',n.name));
assert.deepEqual(children('Request Exists?',0),['Prepare Final Status']);
assert(!reachable('Webhook Intake','Send Business Email',new Set(['Should Send Email?'])));
assert(!reachable('Webhook Intake','Send Business Email',new Set(['Sending Confirmed?'])));
assert(!reachable('Prepare No Send Result','Send Business Email'));
assert.equal(wf.nodes.filter(n=>n.type.endsWith('.gmail')).length,1);
assert.equal(nodes.get('Send Business Email').retryOnFail,false);
assert.equal(nodes.get('AI Classify Request').parameters.options.response.response.neverError,false);
assert.deepEqual(children('AI Classify Request',1),['AI Fallback']);
assert(reachable('AI Fallback','Log Business Request'));

const clone=x=>JSON.parse(JSON.stringify(x));
function run({input=fixture.input,config={},rows=[],ai='success',fail,empty,mutate}={}) {
  const state={rows:clone(rows),writes:0,sent:0,aiCalls:0,visited:[],result:null,aiBody:null,code:null};
  const history={};let name='Webhook Intake',items=[{json:{body:clone(input)}}];
  for(let step=0;name&&step<100;step++) {
    const n=nodes.get(name);state.visited.push(name);
    const context={$json:items[0]?.json,$input:{first:()=>items[0],all:()=>items},$:key=>({first:()=>history[key][0],all:()=>history[key]}),require:key=>{assert.equal(key,'crypto');return crypto;}};
    const evaluate=v=>typeof v==='string'&&v.startsWith('={{')?vm.runInNewContext('('+v.slice(3,-2)+')',context,{timeout:1000}):v;
    let port=0;
    if(name===fail){assert.equal(n.onError,'continueErrorOutput');port=1;items=[{json:{error:{message:'PRIVATE_PROVIDER_DIAGNOSTIC'}}}];}
    else if(n.type.endsWith('.code')) {
      items=vm.runInNewContext(`(function(){${n.parameters.jsCode}})()`,context,{timeout:1000});
      if(name==='Apply Business Rules')Object.assign(items[0].json.config,config);
    } else if(n.type.endsWith('.if')) {
      const c=n.parameters.conditions.conditions[0];assert.equal(c.operator.type,'boolean');const v=evaluate(c.leftValue);assert.equal(typeof v,'boolean');port=v?0:1;
    } else if(n.type.endsWith('.googleSheets')) {
      const p=n.parameters;
      if(p.operation==='read'){
        const id=evaluate(p.filtersUI.values[0].lookupValue);
        items=state.rows.filter(r=>r.request_id===id).map(json=>({json:clone(json)}));
      } else {
        const row=Object.fromEntries(Object.entries(p.columns.value).map(([k,v])=>[k,evaluate(v)]));
        const i=state.rows.findIndex(r=>r.request_id===row.request_id);
        assert(i>=0||p.operation==='appendOrUpdate');
        state.writes++;if(i<0)state.rows.push(row);else state.rows[i]={...state.rows[i],...row};items=[{json:row}];
      }
      if(!items.length||name===empty)items=[{json:{}}];
    } else if(n.type.endsWith('.httpRequest')) {
      state.aiCalls++;state.aiBody=evaluate(n.parameters.jsonBody);
      assert.equal(state.aiBody.store,false);assert.equal(state.aiBody.text.format.strict,true);
      const aiInput=JSON.parse(state.aiBody.input);assert.deepEqual(Object.keys(aiInput).sort(),['message','request_type']);
      if(ai==='error'){port=1;items=[{json:{error:{message:'PRIVATE_PROVIDER_DIAGNOSTIC'}}}];}
      else items=[{json:{status:ai==='incomplete'?'incomplete':'completed',output:[{content:ai==='refusal'?[{type:'refusal'}]:[{type:'output_text',text:ai==='malformed'?'bad':JSON.stringify(ai==='extra'?{classification:'sales',priority:'high',summary:'safe',send:true}:{classification:'billing',priority:'high',summary:'Synthetic summary'})}]}]}}];
    } else if(n.type.endsWith('.gmail')) {
      assert.equal(evaluate(n.parameters.sendTo),fixture.input.email);assert(!evaluate(n.parameters.message).includes('Synthetic summary'));
      state.sent++;items=[{json:{id:'synthetic-message'}}];
    } else if(n.type.endsWith('.respondToWebhook')) {state.result=clone(evaluate(n.parameters.responseBody));state.code=evaluate(n.parameters.options.responseCode);}
    if(mutate)mutate(name,items);
    history[name]=clone(items);name=children(name,port)[0];
  }
  assert(state.result,'workflow must return a result');validateOutput(state.result);
  assert(!JSON.stringify(state.result).includes('PRIVATE_PROVIDER_DIAGNOSTIC'));
  assert(!JSON.stringify(state.result).includes(fixture.input.email));
  state.history=history;return state;
}
let cases=0;
const enabled={email_enabled:true,acknowledgement_policy:true};
const aiEnabled={ai_enabled:true,ai_model:'test-model'};
const first=run();assert.deepEqual(first.result,fixture.output);assert.equal(first.writes,1);assert.equal(first.sent,0);cases++;
for(const type of ['sales','support','general']){const r=run({input:{...fixture.input,request_type:type},config:enabled});assert.equal(r.sent,1);assert.equal(r.result.status,'completed');assert.equal(r.rows[0].email_status,'sent');assert.equal(r.rows[0].notes,'');cases++;}
for(const patch of [{request_id:undefined},{email:'bad'},{requires_response:'true'},{request_type:'SALES'},{source:'invalid'},{message:'x'},{extra:'bad'}]) {
  const r=run({input:{...fixture.input,...patch},config:{...enabled,...aiEnabled}});assert.equal(r.code,400);assert.equal(r.writes,0);assert.equal(r.aiCalls,0);assert.equal(r.sent,0);cases++;
}
for(const input of [null,[],{}]){const r=run({input});assert.equal(r.code,400);assert.equal(r.writes,0);cases++;}
const noResponse=run({input:{...fixture.input,requires_response:false},config:enabled});assert.equal(noResponse.result.email_status,'not_requested');assert.equal(noResponse.sent,0);cases++;
for(const type of ['billing','complaint']){const r=run({input:{...fixture.input,request_type:type,priority_hint:'low'},config:enabled});assert.equal(r.sent,0);assert.equal(r.code,202);assert.equal(r.result.email_status,'pending_approval');if(type==='complaint')assert.equal(r.result.priority,'high');cases++;}
const pending=run({config:{email_enabled:true}});assert.equal(pending.result.status,'awaiting_approval');assert.equal(pending.sent,0);cases++;
for(const ai of ['success','error','malformed','extra','refusal','incomplete']){
  const r=run({config:aiEnabled,ai});assert.equal(r.aiCalls,1);assert.equal(r.result.classification,'sales');assert.equal(r.sent,0);assert.equal(r.rows[0].ai_status,ai==='success'?'success':'fallback');cases++;
}
assert.equal(first.rows[0].ai_status,'unavailable');
for(const email_status of ['sent','sending','unknown','pending_approval','disabled']){
  const rows=[{...first.rows[0],email_status,notes:'Keep review state'}];
  const r=run({config:{...enabled,...aiEnabled},rows});assert.equal(r.result.status,'duplicate');assert.equal(r.aiCalls,0);assert.equal(r.writes,0);assert.equal(r.sent,0);assert.deepEqual(r.rows,rows);cases++;
}
const conflict=run({rows:first.rows,input:{...fixture.input,message:'A different valid request.'}});assert.equal(conflict.code,409);assert.equal(conflict.writes,0);cases++;
const duplicateRows=run({rows:[...first.rows,...first.rows]});assert.equal(duplicateRows.code,409);assert.equal(duplicateRows.sent,0);cases++;
for(const fail of ['Find Existing Request','Log Business Request']){const r=run({config:enabled,fail});assert.equal(r.code,503);assert.equal(r.sent,0);cases++;}
for(const fail of ['Mark Sending','Send Business Email','Mark Sent']){const r=run({config:enabled,fail});assert.equal(r.code,202);assert.equal(r.result.email_status,'unknown');assert.equal(r.rows[0].email_status,'unknown');assert.equal(r.sent,fail==='Mark Sent'?1:0);cases++;}
for(const empty of ['Log Business Request','Mark Sending','Mark Sent']){const r=run({config:enabled,empty});assert.notEqual(r.result.status,'completed');assert.equal(r.sent,empty==='Mark Sent'?1:0);cases++;}
const unknownWriteFailure=run({config:enabled,fail:'Mark Unknown',mutate:(name,items)=>{if(name==='Confirm Sent')items[0].json.sent=false;}});assert.equal(unknownWriteFailure.result.status,'needs_reconciliation');assert.equal(unknownWriteFailure.sent,1);cases++;
const privacy=run({config:aiEnabled,input:{...fixture.input,message:'Demo Customer customer@example.com 00000000-0000-4000-8000-000000000001 please help.'}});
for(const value of [fixture.input.email,fixture.input.customer_name,fixture.input.request_id])assert(!privacy.aiBody.input.includes(value));cases++;
console.log(`PASS: ${nodes.size} nodes, ${cases} offline scenarios, JSON/graph safety. No live calls.`);
