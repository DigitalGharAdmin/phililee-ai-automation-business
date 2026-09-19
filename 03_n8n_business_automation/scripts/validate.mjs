// Build 1 contract and publication checks only. No provider/runtime integration.
import assert from 'node:assert/strict';
import {readFileSync, existsSync} from 'node:fs';
import {execFileSync, spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

const root=fileURLToPath(new URL('../',import.meta.url));
const read=p=>readFileSync(path.join(root,p),'utf8');
const uuid=v=>typeof v==='string' && /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/.test(v);
const types=['sales','support','complaint','billing','general'];
const priorities=['low','normal','high'];
const routes={sales:'sales_queue',support:'support_queue',complaint:'review_queue',billing:'review_queue',general:'general_queue'};
const inputKeys=['request_id','customer_name','email','company','request_type','message','source','priority_hint','requires_response'];
export function input(raw) {
  assert(raw && typeof raw==='object' && !Array.isArray(raw));
  assert(Object.keys(raw).every(k=>inputKeys.includes(k)));
  const x={company:null,request_type:'general',priority_hint:'normal',requires_response:false,...raw};
  for(const [k,v] of Object.entries(x)) if(typeof v==='string') x[k]=v.trim();
  if(x.company==='') x.company=null;
  assert(uuid(x.request_id));
  for(const [k,min,max] of [['customer_name',2,120],['message',10,4000]])
    assert(typeof x[k]==='string' && x[k].length>=min && x[k].length<=max);
  assert(x.company===null || (typeof x.company==='string' && x.company.length>=1 && x.company.length<=200));
  assert(typeof x.email==='string' && x.email.length<=254 && /^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$/.test(x.email));
  x.email=x.email.toLowerCase();
  assert(types.includes(x.request_type)); assert(priorities.includes(x.priority_hint));
  assert(['form','webhook','email_import'].includes(x.source));
  assert.equal(typeof x.requires_response,'boolean');
  return x;
}
const summaries={rejected:'invalid_input',conflict:'id_conflict',logged:'recorded',awaiting_approval:'approval_required',completed:'acknowledgement_sent',duplicate:'existing_request',failed:'operation_failed',needs_reconciliation:'reconciliation_required'};
export function output(x) {
  assert(x && typeof x==='object' && !Array.isArray(x));
  assert.deepEqual(Object.keys(x).sort(),['request_id','accepted','classification','priority','route','action','status','logged','email_status','result_summary'].sort());
  assert(x.request_id===null || uuid(x.request_id));
  assert.equal(typeof x.accepted,'boolean'); assert.equal(typeof x.logged,'boolean');
  assert(x.classification===null || types.includes(x.classification));
  assert(x.priority===null || priorities.includes(x.priority));
  assert(['none',...Object.values(routes)].includes(x.route));
  assert(['none','log_only','request_approval','acknowledge','reuse'].includes(x.action));
  assert(['not_requested','disabled','pending_approval','sending','sent','failed','unknown'].includes(x.email_status));
  assert(Object.hasOwn(summaries,x.status)); assert.equal(x.result_summary,summaries[x.status]);
  assert.equal(x.accepted,!['rejected','conflict'].includes(x.status));
  if(!x.accepted) {
    assert.equal(x.classification,null); assert.equal(x.priority,null); assert.equal(x.route,'none');
    assert.equal(x.action,'none'); assert.equal(x.logged,false); assert.equal(x.email_status,'not_requested');
  } else {
    assert(uuid(x.request_id)); assert(types.includes(x.classification)); assert(priorities.includes(x.priority));
    assert.equal(x.route,routes[x.classification]);
  }
  if(['logged','awaiting_approval','completed','duplicate','needs_reconciliation'].includes(x.status)) assert(x.logged);
  if(x.status==='logged') {assert.equal(x.action,'log_only'); assert(['not_requested','disabled'].includes(x.email_status));}
  if(x.status==='awaiting_approval') {assert.equal(x.action,'request_approval');assert.equal(x.email_status,'pending_approval');}
  if(x.status==='completed') {assert.equal(x.action,'acknowledge');assert.equal(x.email_status,'sent');}
  if(x.status==='duplicate') assert.equal(x.action,'reuse');
  if(x.status==='needs_reconciliation') assert.equal(x.email_status,'unknown');
}
const fixture=JSON.parse(read('demo/contracts.json'));
input(fixture.input); output(fixture.output);
let cases=2;
for(const patch of [{request_id:'bad'},{email:'bad'},{customer_name:' '},{message:'short'},{requires_response:'true'},{request_type:'refund'},{priority_hint:'urgent'},{source:'unknown'},{extra:1},{company:123}]) {
  assert.throws(()=>input({...fixture.input,...patch})); cases++;
}
const minimal={...fixture.input,email:'  CUSTOMER@EXAMPLE.COM  ',company:'  '};
delete minimal.request_type; delete minimal.priority_hint; delete minimal.requires_response;
const normalized=input(minimal); assert.equal(normalized.email,'customer@example.com');
assert.equal(normalized.company,null); assert.equal(normalized.requires_response,false); cases++;
for(const patch of [{accepted:false},{logged:false},{status:'completed',result_summary:'acknowledgement_sent'},{email_status:'sent'},{result_summary:'private arbitrary text'},{extra:true}]) {
  assert.throws(()=>output({...fixture.output,...patch})); cases++;
}
for(const file of ['README.md','.env.example','.gitignore','docs/ARCHITECTURE.md','docs/BUSINESS_RULES.md','docs/DATA_CONTRACT.md','docs/BUILD_1_SCOPE.md','n8n/README.md','n8n/workflow_core/README.md','n8n/workflow_error_handler/README.md','demo/README.md']) assert(existsSync(path.join(root,file)),file);
for(const name of ['.env','.env.local','local.db','n8n/raw_exports/private.json','credentials/local.json'])
  assert.equal(spawnSync('git',['check-ignore','-q','--',name],{cwd:root}).status,0,`Missing ignore: ${name}`);
assert.notEqual(spawnSync('git',['check-ignore','-q','--no-index','--','.env.example'],{cwd:root}).status,0);
const files=execFileSync('git',['ls-files','--cached','--others','--exclude-standard','-z','--','.'],{cwd:root,encoding:'utf8'}).split('\0').filter(Boolean);
const issues=[];
for(const file of new Set(files)) {
  const content=read(file);
  if(/(?:^|\/)\.env(?:$|\.)/.test(file) && !file.endsWith('.env.example')) issues.push([file,'environment file']);
  if(/\.(?:db|sqlite\w*)(?:-|$)|raw_exports\/|credentials\//i.test(file)) issues.push([file,'private artifact']);
  if(/sk-[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{30,}|ya29\.[A-Za-z0-9_-]+|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY|Bearer\s+[A-Za-z0-9_.-]{20,}/.test(content)) issues.push([file,'secret pattern']);
  if(/["']?(?:access_token|refresh_token|client_secret|password|OPENAI_API_KEY)["']?\s*[:=]\s*["'][A-Za-z0-9_./+=-]{16,}["']/i.test(content)) issues.push([file,'secret assignment']);
  for(const match of content.matchAll(/[\w.+-]+@([\w.-]+\.[A-Za-z]{2,})/g)) if(match[1].toLowerCase()!=='example.com') issues.push([file,'nonexample email']);
  if(file.endsWith('.json')) {
    const data=JSON.parse(content);
    if(data.nodes && (!file.endsWith('.sanitized.json') || data.nodes.some(n=>n.credentials || n.webhookId))) issues.push([file,'unsafe workflow export']);
    if(data.nodes) {
      if(data.id||data.versionId||data.meta||data.settings?.errorWorkflow)issues.push([file,'account-specific workflow metadata']);
      for(const node of data.nodes) {
        if(!/^(?:error-)?template-\d+$/.test(node.id||''))issues.push([file,'non-template node identifier']);
        if(node.type.endsWith('.googleSheets')&&node.parameters.documentId?.value!=='YOUR_GOOGLE_SHEET_ID')issues.push([file,'non-placeholder document identifier']);
      }
    }
  }
}
for(const [file,category] of issues) process.stderr.write(`${file}: ${category}\n`);
assert.equal(issues.length,0,'Publication scan failed (values withheld)');
console.log(`PASS: ${cases} contract checks; docs, ignore safety, secret and privacy scans. No live calls.`);

export const contractCases=cases;
