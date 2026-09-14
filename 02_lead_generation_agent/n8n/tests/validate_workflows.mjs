// Offline template/Code-node checks. No n8n instance or network client is used.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const load = path => JSON.parse(readFileSync(new URL(path, import.meta.url), 'utf8'));
const A = load('../workflow_a_lead_intake/lead_intake_routing.sanitized.json');
const B = load('../workflow_b_approval_followup/approval_followup.sanitized.json');
const ID = '00000000-0000-4000-8000-000000000001';
const lead = route => ({id: ID, name: 'Demo Buyer', email: 'buyer@example.com', company: 'Example Store',
  created_at: '2026-01-01T00:00:00Z', source: 'form', service_interest: 'lead_generation',
  lead_score: 47, qualification: route, final_qualification: route, priority: 'medium',
  recommended_action: 'review', final_priority: 'medium', final_recommended_action: 'review', ai_status: 'fallback'});
const row = status => ({lead_id: ID, approval_status: 'pending', follow_up_status: status, follow_up_sent_at: ''});

function reachable(wf, start, target) {
  const queue = [start], seen = new Set();
  while (queue.length) {
    const current = queue.shift();
    if (current === target) return true;
    if (seen.has(current)) continue;
    seen.add(current);
    for (const lane of wf.connections[current]?.main ?? []) for (const edge of lane) queue.push(edge.node);
  }
  return false;
}

for (const wf of [A, B]) {
  const names = new Set(wf.nodes.map(n=>n.name));
  assert.equal(names.size, wf.nodes.length);
  assert.equal(wf.active, false);
  assert.equal(wf.settings.saveDataErrorExecution, 'none');
  for (const [source, ports] of Object.entries(wf.connections)) {
    assert(names.has(source));
    for (const lane of ports.main) for (const edge of lane) assert(names.has(edge.node));
  }
  for (const n of wf.nodes) {
    assert(reachable(wf, wf.nodes[0].name, n.name), `Disconnected node: ${n.name}`);
    assert(!n.credentials && !n.webhookId);
    assert.equal(n.onError, 'stopWorkflow');
    if (n.type.endsWith('.code')) new vm.Script(`(function(){${n.parameters.jsCode}\n})()`);
    if (['httpRequest','googleSheets','gmail'].some(t=>n.type.endsWith('.'+t))) {
      assert.equal(n.retryOnFail, true); assert.equal(n.maxTries, 3); assert.equal(n.waitBetweenTries, 2000);
    }
    if (n.type.endsWith('.googleSheets')) {
      assert.equal(n.parameters.documentId.value, 'YOUR_GOOGLE_SHEET_ID');
      if (n.parameters.operation === 'read') {
        assert.equal(n.parameters.filtersUI.values[0].lookupColumn, 'lead_id');
        assert.equal(n.parameters.options.returnFirstMatch, false);
        assert.equal(n.alwaysOutputData, true);
      } else {
        assert.deepEqual(n.parameters.columns.matchingColumns, ['lead_id']);
        assert.equal(n.parameters.options.cellFormat, 'RAW');
      }
    }
  }
}
assert.equal(A.nodes.find(n=>n.name==='Capture Lead').parameters.url, 'http://127.0.0.1:8000/leads?use_ai=true');
// n8n IF output 0 is TRUE; output 1 is FALSE. Reject extra branch edges too.
assert.deepEqual(A.connections['CRM Exists'].main, [
  [{node:'Intake Result',type:'main',index:0}],
  [{node:'Upsert CRM Lead',type:'main',index:0}],
]);
assert(!reachable(A, 'Intake Result', 'Upsert CRM Lead'), 'Existing branch must bypass upsert');
assert(reachable(A, 'Upsert CRM Lead', 'Intake Result'), 'New branch must reach result');
assert(reachable(A, 'Intake Result', 'Intake Response'));
assert(B.nodes.find(n=>n.name==='Fetch Stored Lead').parameters.url.includes('http://127.0.0.1:8000/leads/'));
assert(!A.nodes.some(n=>n.type.endsWith('.gmail')));
assert.equal(B.nodes.filter(n=>n.type.endsWith('.gmail')).length, 1);
assert.equal(B.nodes[0].parameters.authentication, 'basicAuth');
assert(!reachable(B, 'Prepare Rejection', 'Send Approved Gmail'));
assert(reachable(B, 'Send Approved Gmail', 'Mark Sent'));
assert.deepEqual(B.connections['Approved Decision'].main[0].map(e=>e.node), ['Prepare Follow-up']);

function run(wf, {route='warm', decision='approve', rows=[], created=true, fail=null, email, input}={}) {
  const state={rows:structuredClone(rows),sent:0,visited:[],response:null,crmWrites:0,resultInput:null};
  const history = {};
  let name=wf.nodes[0].name;
  let items=[{json: input ?? (wf===A ? {body:{name:'Demo Buyer',email:'buyer@example.com',message:'Please tell me more.',source:'form'}} : {lead_id:ID,decision,notes:'Reviewed'})}];
  try {
    while (name) {
      const n=wf.nodes.find(n=>n.name===name); state.visited.push(name);
      if (name==='Intake Result') state.resultInput=structuredClone(items[0].json);
      if (name===fail) throw new Error('Simulated service failure');
      const ctx={$input:{first:()=>items[0],all:()=>items},$json:items[0]?.json,
        $:key=>({first:()=>history[key]?.[0],all:()=>history[key]})};
      const expr=value=>typeof value==='string' && value.startsWith('={{')
        ? vm.runInNewContext(`(${value.slice(3,-2)})`,ctx,{timeout:1000}) : value;
      let port=0;
      if (n.type.endsWith('.code')) items=vm.runInNewContext(`(function(){${n.parameters.jsCode}\n})()`,ctx,{timeout:1000});
      else if (n.type.endsWith('.if')) {
        const condition=n.parameters.conditions.conditions[0];
        port=expr(condition.leftValue)===condition.rightValue?0:1;
      } else if (n.type.endsWith('.httpRequest')) {
        const data=lead(route); if (email!==undefined) data.email=email;
        items=[{json:wf===A?{created,lead:data}:data}];
      } else if (n.type.endsWith('.googleSheets')) {
        if (n.parameters.operation==='read') {
          const key=expr(n.parameters.filtersUI.values[0].lookupValue);
          items=state.rows.filter(r=>r.lead_id===key).map(json=>({json:structuredClone(json)}));
          if (!items.length) items=[{json:{}}];
        } else {
          state.crmWrites++;
          const data=Object.fromEntries(Object.entries(n.parameters.columns.value).map(([k,v])=>[k,expr(v)]));
          const index=state.rows.findIndex(r=>r.lead_id===data.lead_id);
          if (index<0 && n.parameters.operation==='update') throw new Error('Missing CRM row');
          if (index<0) state.rows.push(data); else state.rows[index]={...state.rows[index],...data};
          items=[{json:data}];
        }
      } else if (n.type.endsWith('.gmail')) {
        assert.equal(expr(n.parameters.sendTo), email??'buyer@example.com');
        const body=expr(n.parameters.message);
        assert(!/lead score|classified|risk_flags|CRM status/i.test(body));
        state.sent++; items=[{json:{accepted:true}}];
      } else if (n.type.endsWith('.respondToWebhook')) state.response=expr(n.parameters.responseBody);
      history[name]=structuredClone(items);
      name=wf.connections[name]?.main[port]?.[0]?.node;
    }
  } catch (error) {state.error=error.message;}
  return state;
}

let cases=0;
for (const route of ['hot','warm','cold']) {
  const result=run(A,{route}); assert(!result.error); assert.equal(result.rows.length,1);
  assert.equal(result.rows[0].follow_up_status,route==='cold'?'nurture':'awaiting_approval');
  assert.equal(result.sent,0); assert.equal(result.response.route,route); cases++;
  assert.equal(result.crmWrites,1);
  assert(result.visited.includes('Upsert CRM Lead'));
  assert(result.visited.includes('Intake Result') && result.visited.includes('Intake Response'));
  assert.equal(result.resultInput.lead_id,ID); // Flat Sheets output, not {crm: ...}.
  assert.equal(result.resultInput.crm,undefined);
  assert.equal(result.response.result,'crm_upserted');
}
for (const status of ['sent','sending','not_sent','awaiting_approval']) {
  const original={...row(status), approval_status:status==='not_sent'?'rejected':'approved',
    approval_decision:status==='not_sent'?'reject':'approve', approved_at:'2026-01-02T00:00:00Z',
    follow_up_sent_at:status==='sent'?'2026-01-03T00:00:00Z':'', notes:'Preserve reviewer context'};
  const result=run(A,{created:false,rows:[original]});
  assert(!result.error);
  assert.equal(result.crmWrites,0, 'Existing lead must perform no CRM writes');
  assert(!result.visited.includes('Upsert CRM Lead'));
  assert(result.visited.includes('Intake Result') && result.visited.includes('Intake Response'));
  assert.equal(result.resultInput.exists,true);
  assert.equal(result.resultInput.crm,undefined); // Existing shape intentionally has no crm.
  for (const field of ['approval_status','approval_decision','approved_at','follow_up_status','follow_up_sent_at']) {
    assert.equal(result.rows[0][field],original[field], `Existing ${field} must not reset`);
  }
  assert.deepEqual(result.rows,[original]); assert.equal(result.response.result,'crm_reused');
  assert.equal(result.response.approval_status,original.approval_status);
  assert.equal(result.response.follow_up_status,original.follow_up_status);
  assert.equal(result.response.lead_id,ID); cases++;
}
// A duplicate backend lead with no CRM row still takes the new-CRM branch.
const missingCrm=run(A,{created:false});
assert(!missingCrm.error); assert.equal(missingCrm.crmWrites,1);
assert.equal(missingCrm.response.result,'crm_upserted'); cases++;
for (const route of ['warm','hot']) {
  const result=run(B,{route,rows:[row('awaiting_approval')]});
  assert(!result.error); assert.equal(result.sent,1); assert.equal(result.rows[0].follow_up_status,'sent');
  assert(result.rows[0].follow_up_sent_at); assert(result.visited.indexOf('Mark Sent')>result.visited.indexOf('Send Approved Gmail')); cases++;
}
for (const status of ['sent','sending']) {
  const result=run(B,{rows:[row(status)]}); assert.equal(result.sent,0); assert(!result.visited.includes('Mark Sending')); cases++;
}
for (const decision of ['approve','reject']) {
  const result=run(B,{route:'cold',decision,rows:[row('nurture')]}); assert.equal(result.sent,0); cases++;
}
const rejected=run(B,{decision:'reject',rows:[row('awaiting_approval')]});
assert.equal(rejected.sent,0); assert.equal(rejected.rows[0].approval_status,'rejected'); cases++;
for (const decision of ['yes','maybe','APPROVE']) {assert.equal(run(B,{decision}).sent,0); cases++;}
for (const rows of [[],[row('awaiting_approval'),row('awaiting_approval')]]) {
  const result=run(B,{rows}); assert.equal(result.sent,0); assert(!result.visited.includes('Mark Sending')); cases++;
}
const invalid=run(B,{email:'invalid',rows:[row('awaiting_approval')]}); assert.equal(invalid.sent,0); cases++;
for (const fail of ['Fetch Stored Lead','Find Approval CRM','Mark Sending','Send Approved Gmail']) {
  const result=run(B,{rows:[row('awaiting_approval')],fail}); assert(result.error); assert.equal(result.sent,0);
  assert.notEqual(result.rows[0].follow_up_status,'sent'); cases++;
}
const uncertain=run(B,{rows:[row('awaiting_approval')],fail:'Mark Sent'});
assert.equal(uncertain.sent,1); assert.equal(uncertain.rows[0].follow_up_status,'sending');
assert.equal(run(B,{rows:uncertain.rows}).sent,0); cases++;
console.log(`PASS: two workflow graphs and ${cases} offline scenarios; zero network or live-service calls.`);
