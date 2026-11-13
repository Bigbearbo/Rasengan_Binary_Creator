#!/usr/bin/env node
// AE1 b-only counterfactual: independent inference from immutable PR29 final weights.
// Run from repository checkout: node experiments/spiral_neural/20261113_scheduled_ae1_b_only/probe.cjs
// Does NOT train a network or call an LLM as an answer oracle.
'use strict';
const fs=require('node:fs'), path=require('node:path'), crypto=require('node:crypto');
const parent=path.resolve(__dirname,'../20261113_scheduled_suffix_exposure');
const here=__dirname;
const frozen=JSON.parse(fs.readFileSync(path.join(here,'preregistered_protocol.json'),'utf8'));
const keypath=frozen.baseline_checkpoint_scope.frozen_file_blob_sha;
const hash=(b,algo='sha256')=>crypto.createHash(algo).update(b).digest('hex');
const gitBlob=(b)=>crypto.createHash('sha1').update(Buffer.from('blob '+b.length+'\0')).update(b).digest('hex');
function readFrozen(name) {
  const p=path.join(parent,name==='results.json'?name:'checkpoints/'+name);
  const bytes=fs.readFileSync(p), found=gitBlob(bytes);
  if(found!==keypath[name])throw Error('Source blob mismatch: '+name+' '+found);
  return JSON.parse(bytes.toString('utf8'));
}
const word=v=>{if(!Number.isInteger(v)||v<0||v>=30)throw Error('invalid word');return v.toString(2).padStart(5,'0')+'0'};
const qbits=(r,a,b,c,d)=>'01'+'010'+r.toString(2).padStart(3,'0')+'0'+[a,b,c,d].map(word).join('')+'111100';
const ans=(r,a,b)=>word(a)+(r===2?word(b):'')+'S';
const partition=(a,b)=>((a+b)%6===0?'val':(a+b)%6===1?'test':'train');
function tensor(meta,name,shape) {
  const t=meta.tensors[name];
  if(!t||t.dtype!=='float32'||JSON.stringify(t.shape)!==JSON.stringify(shape))throw Error('Invalid '+name);
  const buf=Buffer.from(t.little_endian_base64,'base64');
  const count=shape.reduce((a,b)=>a*b,1);
  if(buf.length!==count*4)throw Error('Bad float32 bytes '+name);
  return Array.from({length:count},(_,i)=>buf.readFloatLE(i*4));
}
function model(meta) {
  if(meta.schema!=='AE1-SUFFIX-FINAL-WEIGHTS-v1')throw Error('checkpoint schema mismatch');
  const ordered=['0.weight','0.bias','2.weight','2.bias'], sha=crypto.createHash('sha256');
  for(const k of ordered){sha.update(k);sha.update(Buffer.from(meta.tensors[k].little_endian_base64,'base64'))}
  const got=sha.digest('hex');
  if(got!==meta.final_weights_sha256)throw Error('tensor state SHA mismatch '+got);
  return {w:tensor(meta,'0.weight',[64,160]),b:tensor(meta,'0.bias',[64]),
          v:tensor(meta,'2.weight',[3,64]),d:tensor(meta,'2.bias',[3]),seed:meta.seed,mode:meta.mode,sha:got};
}
let forwards=0;
function next(m,s) {
  if(!s.length||s.length>80||/[^01]/.test(s))throw Error('Bad context '+s);
  const active=Array.from(s,(ch,i)=>2*i+(ch==='1'?1:0)), hidden=new Float64Array(64);
  for(let h=0;h<64;h++){
    let z=m.b[h],off=h*160;
    for(let i=0;i<active.length;i++)z+=m.w[off+active[i]];
    hidden[h]=Math.tanh(z);
  }
  let best=-Infinity,arg=-1;
  for(let k=0;k<3;k++){
    let z=m.d[k],off=k*64;
    for(let h=0;h<64;h++)z+=m.v[off+h]*hidden[h];
    if(z>best){best=z;arg=k}
  }
  forwards++;
  return '01S'[arg];
}
function free(m,q) {
  let output='';
  for(let i=0;i<32;i++) {
    if(q.length+output.length>80)return [output,'overflow'];
    const c=next(m,q+output);output+=c;
    if(c==='S')return [output,'stop'];
  }
  return [output,'cap'];
}
function assert(b,msg){if(!b)throw Error(msg)}
function metrics(arr,r,baseOnly) {
  const xs=arr.filter(x=>x.r===r && (baseOnly===undefined || x.is_base===baseOnly));
  return {
    n:xs.length,exact:xs.filter(x=>x.actual===x.expected).length,
    first_word:xs.filter(x=>x.actual.slice(0,6)===word(x.a)).length,
    second_word:r===2?xs.filter(x=>x.actual.slice(6,12)===word(x.b)).length:null,
    stop:xs.filter(x=>x.actual.length===x.expected.length&&x.actual.endsWith('S')).length,
    no_stop:xs.filter(x=>!x.actual.endsWith('S')).length
  };
}
function main() {
  const archive=readFrozen('results.json'),byModel=[],raw=[];
  for(const [idx,key] of ['weights_seed101_fixed.json','weights_seed101_varied.json','weights_seed202_fixed.json','weights_seed202_varied.json'].entries()) {
    const m=model(readFrozen(key)), historical=archive.per_model.find(x=>x.seed===m.seed&&x.mode===m.mode);
    assert(!!historical && historical.final_weights_sha256===m.sha,'archived model key or state mismatch');
    let gate=0;
    for(const split of ['train','val','test'])for(const variant of ['seen','changed_low','unseen_high'])for(const r of [1,2]){
      for(const [a,b,c,d,rr,expected] of historical.evaluation[split][variant][String(r)].predictions) {
        assert(rr===r&&partition(a,b)===split,'archive partition inconsistency');
        const [actual]=free(m,qbits(r,a,b,c,d));
        if(actual!==expected)throw Error('forward/archive mismatch '+key+'/'+split+'/'+variant+'/'+r+'/'+[a,b,c,d]+': '+actual+' vs '+expected);
        gate++;
      }
    }
    assert(gate===216,'archive gate count for '+key+' was '+gate);
    const rows=[];
    for(let a=0;a<6;a++){
      const b0=((1-a)%6+6)%6;
      assert(partition(a,b0)==='test','test anchor');
      const c=15+(7*a+3*b0)%15,d=15+(5*a+11*b0)%15;
      for(let r of [1,2]){
        const baseline=qbits(r,a,b0,c,d);
        for(let b=0;b<6;b++){
          const q=qbits(r,a,b,c,d),expected=ans(r,a,b);
          assert(q.length===39&&q.slice(0,9)==='01010'+r.toString(2).padStart(3,'0')+'0','question profile');
          const diff=[...q].reduce((v,ch,i)=>v+(ch!==baseline[i]&&!(i>=15&&i<21)?1:0),0);
          assert(diff===0,'Only b slot may change');
          const [actual,why]=free(m,q);
          const x={seed:m.seed,mode:m.mode,a,b,b0,c,d,r,split:partition(a,b),is_base:b===b0,
                   Q:q,expected,actual,stop_cause:why};
          rows.push(x);raw.push(x);
        }
      }
    }
    const r1=rows.filter(x=>x.r===1),r2=rows.filter(x=>x.r===2);
    let invariance=0,secondFollows=0,secondStuck=0,prefixStable=0;
    const changedRows=[],failures=[];
    for(let a=0;a<6;a++) {
      const base1=r1.find(x=>x.a===a&&x.is_base),base2=r2.find(x=>x.a===a&&x.is_base);
      for(let b=0;b<6;b++){
        if(b===base1.b0)continue;
        const x1=r1.find(x=>x.a===a&&x.b===b),x2=r2.find(x=>x.a===a&&x.b===b);
        invariance+=(x1.actual===base1.actual?1:0);
        prefixStable+=(x2.actual.slice(0,6)===base2.actual.slice(0,6)?1:0);
        secondFollows+=(x2.actual.slice(6,12)===word(b)?1:0);
        secondStuck+=(x2.actual.slice(6,12)===word(base2.b0)?1:0);
        changedRows.push({a,b,b0:base1.b0,r1_invariant:x1.actual===base1.actual,
          r2_prefix_same:x2.actual.slice(0,6)===base2.actual.slice(0,6),
          r2_new_second_correct:x2.actual.slice(6,12)===word(b),
          r2_old_second_echo:x2.actual.slice(6,12)===word(base2.b0)});
      }
    }
    const modelRow={seed:m.seed,mode:m.mode,source_file:key,weights_sha256:m.sha,archived_gate_match:gate,
      r1_base:metrics(rows,1,true),r1_changed:metrics(rows,1,false),r2_base:metrics(rows,2,true),r2_changed:metrics(rows,2,false),
      changed_b_count:30,r1_output_invariant:invariance,r2_first_word_output_stable:prefixStable,
      r2_new_second_correct:secondFollows,r2_old_second_repeated:secondStuck,
      by_split:Object.fromEntries(['train','val','test'].map(s=>[s,{
         r1:metrics(rows.filter(x=>x.split===s),1),r2:metrics(rows.filter(x=>x.split===s),2)
      }])),changedRows};
    byModel.push(modelRow);
  }
  assert(raw.length===288 && byModel.length===4,'intervention enumeration');
  const totals=Object.fromEntries(['r1_base','r1_changed','r2_base','r2_changed'].map(key=>{
    const xs=byModel.map(x=>x[key]);
    return[key,Object.fromEntries(Object.keys(xs[0]).map(k=>[k,xs[0][k]===null?null:xs.reduce((sum,x)=>sum+x[k],0)]))];
  }));
  const summary={models:4,archived_outputs_verified:864,new_outputs:288,changed_b_comparisons:240,
    r1_changed_invariant:byModel.reduce((s,x)=>s+x.r1_output_invariant,0),
    r2_new_second_correct:byModel.reduce((s,x)=>s+x.r2_new_second_correct,0),
    r2_old_second_repeated:byModel.reduce((s,x)=>s+x.r2_old_second_repeated,0),
    r2_first_word_stable:byModel.reduce((s,x)=>s+x.r2_first_word_output_stable,0),
    totals,actual_nn_forwards:forwards,dense_mac:forwards*10432,
    new_optimizer_updates:0};
  const report={work_id:frozen.work_id,date:'2026-11-13',
    git_base:frozen.base_commit,blob_sha_gate:keypath,summary,by_model:byModel,
    every_raw_bit_case:raw,conclusion_scope:'post-hoc checkpoint intervention; b values often trained with other suffixes; no new training nor blind split'};
  fs.writeFileSync(path.join(here,'results.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(summary,null,2));
}
main();
