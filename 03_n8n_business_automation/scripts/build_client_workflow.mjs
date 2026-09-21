import {mkdirSync,writeFileSync} from 'node:fs';
import {isMain,loadConfig,validateConfig} from './client_config.mjs';
import {buildCore} from './build_core.mjs';
import {buildErrorHandler} from './build_error_handler.mjs';

export function buildClient(config){const c=validateConfig(config);return {core:buildCore(c,true),handler:buildErrorHandler(c,true)};}
if(isMain(import.meta.url))try{
  const c=loadConfig(process.argv[2]),pair=buildClient(c);
  const directory=new URL('../n8n/generated/',import.meta.url);mkdirSync(directory,{recursive:true});
  for(const [kind,w] of Object.entries(pair))writeFileSync(new URL(`business_automation_${kind}.${c.client_id}.sanitized.json`,directory),JSON.stringify(w,null,2)+'\n');
  console.log('PASS: inactive sanitized client core and handler generated');
}catch(e){console.error(e.message);process.exitCode=1;}
