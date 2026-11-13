#!/usr/bin/env node
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const here=__dirname,root=path.resolve(here,'../../..');
const spec=JSON.parse(fs.readFileSync(path.join(here,'protocol.json'),'utf8'));
const run=require(path.join(here,'core.js'));
const gitBlob=bytes=>crypto.createHash('sha1').update(Buffer.from('blob '+bytes.length+'\0')).update(bytes).digest('hex');
const load=(repoPath)=>{
  const full=path.join(root,repoPath);
  const data=fs.readFileSync(full);
  return {sha:gitBlob(data),content:data.toString('utf8')};
};
const result=run(load,spec);
fs.writeFileSync(path.join(here,'results_summary.json'),JSON.stringify(result.summary,null,2)+'\n');
fs.writeFileSync(path.join(here,'raw_cases.jsonl'),result.records.map(x=>JSON.stringify(x)).join('\n')+'\n');
console.log(JSON.stringify({gate:result.summary.archived_outputs_verified,probes:result.summary.new_outputs,
  forwards:result.summary.total_forward_calls,mac:result.summary.total_dense_MAC,
  groups:result.summary.group_statistics},null,2));
