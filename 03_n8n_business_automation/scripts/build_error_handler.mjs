// No provider calls. Generate a disabled-by-default sanitized notification workflow.
import {writeFileSync} from 'node:fs';
import {isMain,loadConfig,validateConfig} from './client_config.mjs';
import {buildCore} from './build_core.mjs';
export function buildErrorHandler(client=loadConfig(),clientNamed=false){
client=validateConfig(client);const core=buildCore(client,clientNamed);
const nodes=[],connections={};
function add(name,type,version,parameters,extra={}){
  nodes.push({name,type:`n8n-nodes-base.${type}`,typeVersion:version,parameters,id:`error-template-${nodes.length+1}`,position:[nodes.length*260,0],onError:'stopWorkflow',...extra});
}
function code(name,fn){add(name,'code',2,{mode:'runOnceForAllItems',jsCode:`return (${fn.toString()})();`});}
function edge(from,to,port=0){connections[from]??={main:[]};while(connections[from].main.length<=port)connections[from].main.push([]);connections[from].main[port].push({node:to,type:'main',index:0});}
add('Error Trigger','errorTrigger',1,{});
code('Normalize Error Context',function(){
  const event=$input.first().json||{};
  const allowedNodes=ALLOWED_NODE_NAMES;
  const node=event.execution?.lastNodeExecuted;
  const failed_node=allowedNodes.includes(node)?node:'Unknown stage';
  const mode=event.execution?.mode;
  const execution_mode=['manual','webhook','trigger','retry','error','integrated'].includes(mode)?mode:'unknown';
  // Deliberately omit raw error objects, names, IDs and URLs from the notification.
  const failure_category=failed_node==='AI Classify Request'?'ai_failure':
    ['Find Existing Request','Log Business Request','Mark Sending','Mark Sent','Mark Send Failed','Mark Unknown'].includes(failed_node)?'storage_failure':
    failed_node==='Send Business Email'?'delivery_review_required':'workflow_failure';
  return [{json:{workflow:'MB05 Business Automation - Core Workflow',failed_node,execution_mode,failure_category}}];
});
nodes.at(-1).parameters.jsCode=nodes.at(-1).parameters.jsCode.replace('ALLOWED_NODE_NAMES',JSON.stringify(core.nodes.map(n=>n.name)));
code('Prepare Privacy-Safe Error Notification',function(){
  const config=TRUSTED_NOTIFICATION_CONFIG;
  const c=$input.first().json;
  const send=config.notifications_enabled===true&&!/@example\.com$/i.test(config.operator_recipient)&&/^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$/.test(config.operator_recipient);
  const summary='Business automation workflow execution failed. Review the execution details in n8n.';
  return [{json:{send,recipient:config.operator_recipient,subject:'Business automation execution requires review',message:`${summary}\nWorkflow: ${c.workflow}\nStage: ${c.failed_node}\nMode: ${c.execution_mode}\nCategory: ${c.failure_category}`}}];
});
add('Notify Operator?', 'if',2.2,{conditions:{options:{caseSensitive:true,leftValue:'',typeValidation:'strict',version:2},conditions:[{id:'notify',leftValue:'={{ $json.send }}',rightValue:'',operator:{type:'boolean',operation:'true',singleValue:true}}],combinator:'and'},options:{}},{alwaysOutputData:false});
add('Send Error Notification','gmail',2.1,{resource:'message',operation:'send',sendTo:'={{ $json.recipient }}',subject:'={{ $json.subject }}',emailType:'text',message:'={{ $json.message }}',options:{appendAttribution:false}},{retryOnFail:false,alwaysOutputData:true,onError:'continueErrorOutput'});
code('Notification Disabled',function(){return [{json:{notification_status:'disabled'}}];});
code('Notification Outcome',function(){
  const r=$input.first().json;
  return [{json:{notification_status:r.notification_status==='disabled'?'disabled':!r.error&&typeof r.id==='string'&&/^[A-Za-z0-9_-]{1,200}$/.test(r.id)?'accepted':'unconfirmed'}}];
});
edge('Error Trigger','Normalize Error Context');edge('Normalize Error Context','Prepare Privacy-Safe Error Notification');edge('Prepare Privacy-Safe Error Notification','Notify Operator?');
edge('Notify Operator?','Send Error Notification');edge('Notify Operator?','Notification Disabled',1);edge('Send Error Notification','Notification Outcome');edge('Send Error Notification','Notification Outcome',1);
edge('Notification Disabled','Notification Outcome');
const workflow={name:'MB05 Business Automation — Error Handler',active:false,nodes,connections,settings:{executionOrder:'v1',saveDataErrorExecution:'none',saveDataSuccessExecution:'none',saveManualExecutions:false,saveExecutionProgress:false},pinData:{},tags:[]};
nodes.find(n=>n.name==='Prepare Privacy-Safe Error Notification').parameters.jsCode=nodes.find(n=>n.name==='Prepare Privacy-Safe Error Notification').parameters.jsCode.replace('TRUSTED_NOTIFICATION_CONFIG',()=>JSON.stringify({notifications_enabled:client.features.operator_notifications_enabled,operator_recipient:client.notifications.operator_recipient}));
if(clientNamed)workflow.name='MB05 Business Automation - '+client.client_id+' - Error Handler';
return workflow;
}
if(isMain(import.meta.url)){writeFileSync(new URL('../n8n/workflow_error_handler/business_automation_error_handler.sanitized.json',import.meta.url),JSON.stringify(buildErrorHandler(),null,2)+'\n');console.log('Generated canonical handler.');}
