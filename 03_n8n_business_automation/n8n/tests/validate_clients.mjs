import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {loadConfig,validateConfig,runtimeConfig} from '../../scripts/client_config.mjs';
import {buildClient} from '../../scripts/build_client_workflow.mjs';
import {buildCore} from '../../scripts/build_core.mjs';
import {buildErrorHandler} from '../../scripts/build_error_handler.mjs';
import {run,regressionCases} from './validate_workflows.mjs';
import {validateErrorHandler} from './validate_error_handler.mjs';

const read=p=>JSON.parse(readFileSync(new URL(p,import.meta.url),'utf8'));
const example=loadConfig(),baseline=buildCore(),handler=buildErrorHandler();
const fixture=read('../../demo/contracts.json');
let cases=0;
const check=fn=>{fn();cases++;};
const copy=()=>structuredClone(example);
for(const mutate of [
  c=>c.client_id='../escape',c=>c.business_name='',c=>c.features.email_enabled='true',
  c=>c.routing.support='https://invalid',c=>c.routing.support='none',c=>c.email.ack_subject='',
  c=>{c.features.operator_notifications_enabled=true;c.notifications.operator_recipient='invalid';},
  c=>c.config_version='2',c=>c.ai.model='',c=>delete c.ai.model,c=>c.priority.complaint='low',
  c=>c.priority.default='urgent',c=>c.email.ack_body='Unsupported promise',
  c=>c.email.ack_subject='{{request.message}}',c=>c.business_name='Injected\nHeader',
  c=>c.metadata.extra={access_token:'synthetic'},c=>c.ai.key='synthetic',
  c=>c.notifications.operator_recipient='operator'+'@'+'private.invalid',c=>c.client_id='__proto__',
  c=>c.email.response_version='',c=>c.features.unknown=true,
  c=>c.email.ack_body='<b>HTML</b>'+c.email.ack_body,
  c=>c.ai.model='a'.repeat(50),
])check(()=>{const c=copy();mutate(c);assert.throws(()=>validateConfig(c));});
for(const suspect of ['sk-','Bearer ','AIza','refresh_token','access_token','client_secret','private_key','password','BEGIN PRIVATE KEY','oauth'])check(()=>{
  const c=copy();c.business_name='Example '+suspect+'synthetic';
  assert.throws(()=>validateConfig(c),e=>!e.message.includes(c.business_name)&&e.message.includes('suspected secret'));
});

function staticPair(pair,c){
  const {core,handler:eh}=pair;
  // Same static graph, types, retries, expressions and mappings as the fully tested core.
  assert.deepEqual(core.connections,baseline.connections);
  assert.deepEqual(core.settings,baseline.settings);assert.equal(core.active,false);
  assert.equal(core.nodes.length,baseline.nodes.length);
  for(const node of core.nodes){
    const normalized=structuredClone(node),original=baseline.nodes.find(n=>n.name===node.name);
    if(node.name==='Apply Business Rules'){
      assert(node.parameters.jsCode.includes(JSON.stringify(runtimeConfig(c))));
      normalized.parameters.jsCode=normalized.parameters.jsCode.replace(JSON.stringify(runtimeConfig(c)),()=>JSON.stringify(runtimeConfig(example)));
    }
    if(node.name==='Webhook Intake'){assert(node.notes.includes(c.client_id+' - Error Handler'));normalized.parameters.path=original.parameters.path;normalized.notes=original.notes;}
    assert.deepEqual(normalized,original);
  }
  assert.deepEqual(eh.connections,handler.connections);assert.deepEqual(eh.settings,handler.settings);assert.equal(eh.active,false);
  for(const node of eh.nodes){
    const normalized=structuredClone(node),original=handler.nodes.find(n=>n.name===node.name);
    if(node.name==='Prepare Privacy-Safe Error Notification')normalized.parameters.jsCode=normalized.parameters.jsCode.replace(JSON.stringify({notifications_enabled:c.features.operator_notifications_enabled,operator_recipient:c.notifications.operator_recipient}),()=>JSON.stringify({notifications_enabled:false,operator_recipient:'operator@example.com'}));
    assert.deepEqual(normalized,original);
  }
  for(const w of [core,eh]){assert.deepEqual(JSON.parse(JSON.stringify(w)),w);assert(!w.id&&!w.versionId&&!w.meta&&!w.settings.errorWorkflow);for(const n of w.nodes){assert(!n.credentials&&!n.webhookId);if(n.type.endsWith('.googleSheets'))assert.equal(n.parameters.documentId.value,'YOUR_GOOGLE_SHEET_ID');}}
}
for(const name of ['support-demo','sales-demo']){
  const c=loadConfig(new URL(`../../config/client_config.${name}.json`,import.meta.url)),pair=buildClient(c);
  check(()=>{staticPair(pair,c);assert.deepEqual(buildClient(c),pair);
    assert.deepEqual(read(`../generated/business_automation_core.${name}.sanitized.json`),pair.core);
    assert.deepEqual(read(`../generated/business_automation_handler.${name}.sanitized.json`),pair.handler);
  });
  check(()=>{assert.equal(validateErrorHandler(pair.handler),9);});
  for(const request_type of ['sales','support','complaint','billing','general'])check(()=>{
    const r=run({workflow:pair.core,input:{...fixture.input,request_type}});
    assert.equal(r.result.route,c.routing[request_type]);assert.equal(r.sent,0);assert.equal(r.aiCalls,0);
    const ctx=r.history['Apply Business Rules'][0].json.config;
    assert.equal(ctx.business_name,c.business_name);assert.equal(ctx.ai_model,c.ai.model);assert.equal(ctx.email_enabled,c.features.email_enabled);
    assert.equal(r.history['Prepare Business Response'][0].json.subject,c.email.ack_subject);
    assert.equal(r.history['Prepare Business Response'][0].json.body,c.email.ack_body.replaceAll('{{business_name}}',c.business_name));
    assert.equal(r.rows[0].response_version,c.email.response_version);
  });
  const enabled=structuredClone(c);enabled.features.email_enabled=true;enabled.features.acknowledgement_policy=true;
  const workflow=buildClient(enabled).core;
  check(()=>{const r=run({workflow});assert.equal(r.sent,1);assert.equal(r.result.status,'completed');});
  check(()=>{const x=structuredClone(enabled);x.features.acknowledgement_policy=false;const r=run({workflow:buildClient(x).core});assert.equal(r.sent,0);assert.equal(r.result.status,'awaiting_approval');});
  for(const gmail of ['clear_failure','timeout_after_accept','missing'])check(()=>{
    const r=run({workflow,gmail});assert.equal(r.result.status,gmail==='clear_failure'?'failed_safe':'needs_reconciliation');assert.equal(r.result.email_status,gmail==='clear_failure'?'not_sent':'unknown');
    const replay=run({workflow,rows:r.rows});assert.equal(replay.sent,0);assert.equal(replay.writes,0);assert.deepEqual(replay.rows,r.rows);
  });
  for(const fail of ['Log Business Request','Mark Sending','Mark Sent','Mark Send Failed'])check(()=>{
    const r=run({workflow,fail,gmail:fail==='Mark Send Failed'?'clear_failure':'success'});
    assert.equal(r.result.status,fail==='Log Business Request'?'failed':'needs_reconciliation');
    if(fail==='Log Business Request')assert.equal(r.sent,0);
  });
  for(const email_status of ['sent','sending','unknown'])check(()=>{
    const first=run({workflow});const rows=[{...first.rows[0],email_status,status:email_status==='unknown'?'needs_reconciliation':'completed'}];
    const updated=structuredClone(enabled);updated.routing.sales='changed_queue';
    const r=run({workflow:buildClient(updated).core,rows});assert.equal(r.result.status,'duplicate');assert.equal(r.result.route,rows[0].route);assert.equal(r.sent,0);assert.equal(r.writes,0);assert.deepEqual(r.rows,rows);
  });
  check(()=>{const r=run({workflow,input:{...fixture.input,config:{email_enabled:true}}});assert.equal(r.result.status,'rejected');assert.equal(r.sent,0);assert.equal(r.writes,0);});
  for(const request_type of ['billing','complaint'])check(()=>{const r=run({workflow,input:{...fixture.input,request_type}});assert.equal(r.result.status,'awaiting_approval');assert.equal(r.sent,0);});
  check(()=>{const r=run({workflow,input:{...fixture.input,requires_response:false}});assert.equal(r.sent,0);});
  for(const model of ['YOUR_OPENAI_MODEL','test-model'])for(const ai of ['success','network','malformed'])check(()=>{
    const x=structuredClone(c);x.features.ai_enabled=true;x.ai.model=model;
    const r=run({workflow:buildClient(x).core,ai});assert.equal(r.aiCalls,model==='YOUR_OPENAI_MODEL'?0:1);assert.equal(r.sent,0);
    assert.equal(r.rows[0].ai_status,model==='YOUR_OPENAI_MODEL'||ai==='network'?'unavailable':ai==='malformed'?'fallback':'success');
    if(r.aiBody)assert.equal(r.aiBody.model,model);
  });
}
check(()=>{
  const c=copy();c.features.operator_notifications_enabled=true;
  const pair=buildClient(c);staticPair(pair,c);
  const code=pair.handler.nodes.find(n=>n.name==='Prepare Privacy-Safe Error Notification').parameters.jsCode;
  const out=vm.runInNewContext(`(function(){${code}})()`,{$input:{first:()=>({json:{workflow:'safe',failed_node:'safe',execution_mode:'manual',failure_category:'workflow_failure'}})}});
  assert.equal(out[0].json.send,false); // example recipient can never become live-ready.
});
check(()=>{const c=copy();c.priority.default='high';const r=run({workflow:buildClient(c).core});assert.equal(r.result.priority,'high');});
check(()=>{const c=copy();c.business_name="Example ' \\ $& Business";const r=run({workflow:buildClient(c).core});assert(r.history['Prepare Business Response'][0].json.body.includes(c.business_name));});
console.log(`PASS: ${cases} client configuration/generation/regression scenarios. No live calls.`);
console.log(`TESTS_COLLECTED: ${regressionCases+cases}; TESTS_PASSED: ${regressionCases+cases}; TESTS_FAILED: 0`);
