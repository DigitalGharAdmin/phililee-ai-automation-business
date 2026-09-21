import {readFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';

export const isMain=url=>Boolean(process.argv[1])&&pathToFileURL(process.argv[1]).href===url;
const fail=(path,category)=>{throw new Error(`${path}: ${category}`);};
export function validateConfig(c){
  const object=(v,path,keys,optional=[])=>{
    if(!v||typeof v!=='object'||Array.isArray(v))fail(path,'object required');
    if(Object.keys(v).some(k=>!keys.includes(k))||keys.some(k=>!optional.includes(k)&&!Object.hasOwn(v,k)))fail(path,'unknown or missing fields');
  };
  function scan(v,path='config'){
    if(typeof v==='string'){
      if(/sk-|Bearer\s|AIza|refresh_token|access_token|client_secret|private_key|password|BEGIN.*PRIVATE KEY|oauth/i.test(v))fail(path,'suspected secret');
      if(/[A-Za-z0-9_+/=-]{40,}/.test(v))fail(path,'opaque token-like value');
      if(/[\u0000-\u001f\u007f-\u009f]/.test(v))fail(path,'control characters');
    }else if(v&&typeof v==='object')for(const [k,x] of Object.entries(v)){
      if(/secret|token|password|credential|oauth|private_key/i.test(k))fail(path,'forbidden field category');
      scan(x,path+'.'+(/^[a-z_]+$/.test(k)?k:'unknown_field'));
    }
  }
  scan(c);
  object(c,'config',['config_version','client_id','business_name','features','ai','routing','priority','email','notifications','metadata'],['metadata']);
  const str=(v,p,max,pattern)=>{if(typeof v!=='string'||!v.trim()||v!==v.trim()||v.length>max||(pattern&&!pattern.test(v)))fail(p,'invalid string');};
  if(c.config_version!=='1')fail('config_version','unsupported version');
  str(c.client_id,'client_id',50,/^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$/);
  str(c.business_name,'business_name',100);
  const flags=['email_enabled','acknowledgement_policy','ai_enabled','operator_notifications_enabled'];
  object(c.features,'features',flags);
  for(const key of flags)if(typeof c.features[key]!=='boolean')fail('features.'+key,'boolean required');
  object(c.ai,'ai',['model']);str(c.ai.model,'ai.model',80,/^[A-Za-z0-9][A-Za-z0-9._-]*$/);
  object(c.routing,'routing',['sales','support','complaint','billing','general']);
  for(const [key,v] of Object.entries(c.routing)){str(v,'routing.'+key,64,/^[a-z][a-z0-9_-]*$/);if(v==='none')fail('routing.'+key,'reserved route');}
  object(c.priority,'priority',['complaint','high_hint','default','general_low_hint']);
  for(const [key,v] of Object.entries(c.priority))if(!['low','normal','high'].includes(v))fail('priority.'+key,'invalid priority');
  if(c.priority.complaint!=='high'||c.priority.high_hint!=='high'||c.priority.general_low_hint!=='low')fail('priority','fixed safety policy');
  object(c.email,'email',['ack_subject','ack_body','response_version']);
  str(c.email.ack_subject,'email.ack_subject',160);str(c.email.ack_body,'email.ack_body',2000);
  str(c.email.ack_subject.replaceAll('{{business_name}}',()=>c.business_name),'email.ack_subject',160);
  str(c.email.ack_body.replaceAll('{{business_name}}',()=>c.business_name),'email.ack_body',2000);
  str(c.email.response_version,'email.response_version',64,/^[a-zA-Z0-9][a-zA-Z0-9._-]*$/);
  for(const [key,v] of Object.entries(c.email))if(/[<>]|\{\{|\}\}/.test(v.replaceAll('{{business_name}}','')))fail('email.'+key,'unsupported template or HTML');
  if(!c.email.ack_body.includes('This acknowledgement does not confirm any purchase, refund or service commitment.'))fail('email.ack_body','required neutral disclaimer missing');
  object(c.notifications,'notifications',['operator_recipient']);
  str(c.notifications.operator_recipient,'notifications.operator_recipient',254,/^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$/);
  if(c.metadata!==undefined){object(c.metadata,'metadata',['environment']);str(c.metadata.environment,'metadata.environment',32,/^[a-z][a-z0-9-]*$/);}
  // Published/build inputs are sanitized. Real recipients are bound privately in n8n.
  for(const [path,v] of [['business_name',c.business_name],...Object.entries(c.email).map(([k,v])=>['email.'+k,v]),['notifications.operator_recipient',c.notifications.operator_recipient]]){
    for(const m of v.matchAll(/[\w.+-]+@([\w.-]+\.[A-Za-z]{2,})/g))if(m[1].toLowerCase()!=='example.com')fail(path,'private email');
  }
  if(/\{\{|\}\}|[<>]/.test(c.business_name))fail('business_name','unsafe template');
  return structuredClone(c);
}
export function loadConfig(path=new URL('../config/client_config.example.json',import.meta.url)){
  let c;try{c=JSON.parse(readFileSync(path,'utf8'));}catch{fail('config','unreadable or invalid JSON');}
  return validateConfig(c);
}
export function runtimeConfig(c){c=validateConfig(c);return {client_id:c.client_id,business_name:c.business_name,...c.features,ai_model:c.ai.model,routing:c.routing,priority:c.priority,email:{...c.email,ack_subject:c.email.ack_subject.replaceAll('{{business_name}}',()=>c.business_name),ack_body:c.email.ack_body.replaceAll('{{business_name}}',()=>c.business_name)}};}
if(isMain(import.meta.url))try{loadConfig(process.argv[2]);console.log('PASS: client configuration');}catch(e){console.error(e.message);process.exitCode=1;}
