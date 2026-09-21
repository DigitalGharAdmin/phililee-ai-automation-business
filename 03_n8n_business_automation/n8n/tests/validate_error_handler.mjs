import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

export function validateErrorHandler(){
  const wf=JSON.parse(readFileSync(new URL('../workflow_error_handler/business_automation_error_handler.sanitized.json',import.meta.url),'utf8'));
  const nodes=new Map(wf.nodes.map(n=>[n.name,n]));
  assert.equal(wf.active,false);assert(!wf.settings.errorWorkflow);
  assert.equal(wf.settings.saveDataErrorExecution,'none');assert.equal(wf.settings.saveManualExecutions,false);
  assert.equal(nodes.get('Error Trigger').type,'n8n-nodes-base.errorTrigger');
  assert.equal(nodes.get('Send Error Notification').retryOnFail,false);
  assert.equal(nodes.get('Notify Operator?').alwaysOutputData,false);
  assert.equal(wf.connections['Notify Operator?'].main[1][0].node,'Notification Disabled');
  const expected=[['Error Trigger','Normalize Error Context'],['Normalize Error Context','Prepare Privacy-Safe Error Notification'],['Prepare Privacy-Safe Error Notification','Notify Operator?'],['Notify Operator?','Send Error Notification'],['Notify Operator?','Notification Disabled'],['Send Error Notification','Notification Outcome'],['Send Error Notification','Notification Outcome'],['Notification Disabled','Notification Outcome']];
  assert.deepEqual(Object.entries(wf.connections).flatMap(([from,p])=>p.main.flatMap(l=>l.map(e=>[from,e.node]))),expected);
  for(const n of wf.nodes){assert(!n.credentials&&!n.webhookId);if(n.type.endsWith('.code'))assert(!/\brequire\s*\(|\bimport\s*\(/.test(n.parameters.jsCode));}
  assert.equal(nodes.get('Send Error Notification').parameters.message,'={{ $json.message }}');
  const prepare=nodes.get('Prepare Privacy-Safe Error Notification').parameters.jsCode;
  assert(prepare.includes('notifications_enabled:false'));assert(prepare.includes("operator_recipient:'operator@example.com'"));
  const coreReadme=readFileSync(new URL('../workflow_core/README.md',import.meta.url),'utf8');
  assert(coreReadme.includes('Settings > Error Workflow')&&coreReadme.includes('MB05 Business Automation'));

  function run(event,{enable=false,replaceRecipient=true,outcome='success'}={}){
    let name='Error Trigger',items=[{json:event}],sends=0,prepared,normalized;const visited=[];
    for(let i=0;name&&i<12;i++){
      const n=nodes.get(name);visited.push(name);let port=0;
      const context={$input:{first:()=>items[0]},$json:items[0].json};
      const expr=v=>v.startsWith('={{')?vm.runInNewContext('('+v.slice(3,-2)+')',context,{timeout:1000}):v;
      if(n.type.endsWith('.code')){
        let code=n.parameters.jsCode;
        if(enable&&name==='Prepare Privacy-Safe Error Notification'){
          code=code.replace('notifications_enabled:false','notifications_enabled:true');
          if(replaceRecipient)code=code.replaceAll('operator@example.com','reviewer@example.com').replace("config.operator_recipient!=='reviewer@example.com'","config.operator_recipient!=='operator@example.com'");
        }
        items=vm.runInNewContext(`(function(){${code}})()`,context,{timeout:1000});
        if(name==='Normalize Error Context')normalized=JSON.parse(JSON.stringify(items[0].json));
        if(name==='Prepare Privacy-Safe Error Notification')prepared=JSON.parse(JSON.stringify(items[0].json));
      }else if(n.type.endsWith('.if'))port=expr(n.parameters.conditions.conditions[0].leftValue)?0:1;
      else if(n.type.endsWith('.gmail')){
        assert.equal(expr(n.parameters.sendTo),'reviewer@example.com');
        assert(!expr(n.parameters.message).includes('PRIVATE_MARKER'));
        sends++;port=outcome==='failure'?1:0;
        items=[{json:outcome==='failure'?{error:{message:'PRIVATE_MARKER'}}:outcome==='empty'?{}:{id:'synthetic-accepted'}}];
      }
      name=wf.connections[name]?.main[port]?.[0]?.node;
    }
    assert(!JSON.stringify(normalized).includes('PRIVATE_MARKER'));
    assert(!JSON.stringify(prepared).includes('PRIVATE_MARKER'));
    assert(!JSON.stringify(items).includes('PRIVATE_MARKER'));
    assert.deepEqual(Object.keys(normalized).sort(),['execution_mode','failed_node','failure_category','workflow']);
    assert(visited.includes('Notification Outcome'));
    return {sends,normalized,prepared,result:JSON.parse(JSON.stringify(items[0].json))};
  }
  const hostile={workflow:{name:'PRIVATE_MARKER'},execution:{lastNodeExecuted:'PRIVATE_MARKER',mode:'PRIVATE_MARKER',url:'PRIVATE_MARKER',id:'PRIVATE_MARKER',retryOf:'PRIVATE_MARKER',error:{message:'PRIVATE_MARKER',stack:'PRIVATE_MARKER'}},body:{email:'private@example.com',message:'PRIVATE_MARKER'},credentials:{value:'PRIVATE_MARKER'},config:{notifications_enabled:true}};
  let cases=0;
  for(const event of [{},hostile,{execution:{lastNodeExecuted:'Mark Sent',mode:'webhook'}},{trigger:{error:{message:'PRIVATE_MARKER'}}}]){
    const r=run(event);assert.equal(r.sends,0);assert.equal(r.result.notification_status,'disabled');cases++;
  }
  for(const outcome of ['success','failure','empty']){const r=run(hostile,{enable:true,outcome});assert.equal(r.sends,1);assert.equal(r.result.notification_status,outcome==='success'?'accepted':'unconfirmed');cases++;}
  const placeholder=run(hostile,{enable:true,replaceRecipient:false});assert.equal(placeholder.sends,0);cases++;
  const mapped=run({execution:{lastNodeExecuted:'Mark Sent',mode:'webhook'}});assert.equal(mapped.normalized.failure_category,'storage_failure');cases++;
  return cases;
}
