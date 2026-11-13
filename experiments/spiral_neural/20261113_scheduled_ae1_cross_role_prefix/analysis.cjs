#!/usr/bin/env node
// Read-only cross-role prefix consistency audit of PR #29 archived NN outputs.
// Does NOT execute any NN forward pass or update weights.
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const SOURCE_BLOB='7d87bfc417564c4af08892534d15b1b3af96e104';
const DEFAULT_SOURCE=path.resolve(__dirname,'../20261113_scheduled_suffix_exposure/results.json');
const splits=['train','val','test'], variants=['seen','changed_low','unseen_high'];
const word=v=>v.toString(2).padStart(5,'0')+'0';
const sp=(a,b)=>((a+b)%6===0?'val':(a+b)%6===1?'test':'train');
function assert(x,msg){if(!x)throw Error(msg);}
function check(pred,a,b,c,d,r){
  assert(typeof pred==='string' && /^[01S]+$/.test(pred),'bad prediction alphabet');
  assert([a,b].every(x=>Number.isInteger(x)&&x>=0&&x<6),'bad a/b');
  assert([c,d].every(x=>Number.isInteger(x)&&x>=0&&x<30),'bad c/d');
  assert(r===1||r===2,'bad r');
}
const key=row=>row.slice(0,4).join(':');
function auditRecord(rec, rows, label, split, variant, r) {
  assert(rows.length===(split==='train'?24:6),'wrong row count '+label);
  const ids=new Set();
  let exact=0, stop=0, bits=0;
  for(const row of rows){
    assert(Array.isArray(row)&&row.length===6,'bad prediction tuple '+label);
    const [a,b,c,d,rr,pred]=row;
    check(pred,a,b,c,d,rr);
    assert(rr===r,'wrong r '+label);
    assert(sp(a,b)===split,'split leak '+label);
    if(variant==='unseen_high')assert(c>=15&&d>=15,'high suffix error');
    if(variant==='changed_low'||variant==='seen')assert(c<15&&d<15,'low suffix error');
    assert(!ids.has(key(row)),'duplicate '+label);ids.add(key(row));
    const expect=(r===1?word(a):word(a)+word(b))+'S';
    if(pred===expect)exact++;
    if(pred.endsWith('S')&&pred.length===expect.length)stop++;
    for(let k=0;k<expect.length-1;k++)if(k<pred.length&&pred[k]===expect[k])bits++;
  }
  assert(exact===rec.exact&&stop===rec.stop_position&&bits===rec.bits_correct,'summary mismatch '+label);
  assert(rec.bits_total===rows.length*6*r&&rec.n===rows.length,'totals mismatch '+label);
  return new Map(rows.map(x=>[key(x),x]));
}
function empty(){
 return {n:0,r1_exact:0,r2_exact:0,both_exact:0,r2_prefix_true:0,
         r2_second_true:0,r1_r2_prefix_agree:0,first_only:0,second_only:0,
         both_words_wrong:0,stop_only:0,r2_wrong:0,wrong_second_matches_a:0,
         wrong_second_matches_c:0,wrong_second_matches_d:0,wrong_second_other:0,
         second_info_bit_errors:0,second_terminator_bit_errors:0,examples:[]};
}
function examine(r1,r2,out,where){
  const [a,b,c,d,,pred1]=r1, pred2=r2[5], e1=word(a)+'S',
        e2=word(a)+word(b)+'S';
  const pfirst=pred2.slice(0,6), psecond=pred2.slice(6,12);
  const firstGood=pfirst===word(a), secondGood=psecond===word(b);
  const r1ok=pred1===e1,r2ok=pred2===e2;
  out.n++;if(r1ok)out.r1_exact++;if(r2ok)out.r2_exact++;
  if(r1ok&&r2ok)out.both_exact++;
  if(firstGood)out.r2_prefix_true++;
  if(secondGood)out.r2_second_true++;
  if(pfirst===pred1.slice(0,6))out.r1_r2_prefix_agree++;
  if(!r2ok){
    out.r2_wrong++;
    if(!firstGood&&secondGood)out.first_only++;
    else if(firstGood&&!secondGood)out.second_only++;
    else if(!firstGood&&!secondGood)out.both_words_wrong++;
    else out.stop_only++;
    if(!secondGood){
      if(psecond===word(a))out.wrong_second_matches_a++;
      else if(psecond===word(c))out.wrong_second_matches_c++;
      else if(psecond===word(d))out.wrong_second_matches_d++;
      else out.wrong_second_other++;
    }
    if(out.examples.length<4)out.examples.push({where,raw_q:'01'+'010'+'0100'+[a,b,c,d].map(word).join('')+'111100',
      a,b,c,d,expected_r1:e1,actual_r1:pred1,expected_r2:e2,actual_r2:pred2});
  }
  for(let j=0;j<5;j++)if(psecond[j]!==word(b)[j])out.second_info_bit_errors++;
  if(psecond[5]!==word(b)[5])out.second_terminator_bit_errors++;
}
function analyze(raw) {
  const gitsha=crypto.createHash('sha1').update('blob '+raw.length+'\0').update(raw).digest('hex');
  assert(gitsha===SOURCE_BLOB,'input source Git blob SHA changed: '+gitsha);
  const data=JSON.parse(raw);
  assert(Array.isArray(data.per_model)&&data.per_model.length===4,'four frozen models required');
  assert(data.protocol_sha256==='27cd6874fa08054a58e7cd9d02b2aebee879136eb71d440eaf17a885dec01b2f','protocol mismatch');
  let overall=empty(), groups={}, seenModels=new Set();
  for(const model of data.per_model){
    assert([101,202].includes(model.seed)&&['fixed','varied'].includes(model.mode),'unexpected model');
    const tag=model.seed+'/'+model.mode;assert(!seenModels.has(tag),'duplicate model');seenModels.add(tag);
    for(const split of splits)for(const variant of variants){
      const byR=model.evaluation[split][variant];
      const k=tag+'/'+split+'/'+variant;
      const left=auditRecord(byR['1'],byR['1'].predictions,k+'/r1',split,variant,1);
      const right=auditRecord(byR['2'],byR['2'].predictions,k+'/r2',split,variant,2);
      assert(left.size===right.size,'pair cardinality mismatch');
      const row=empty();
      for(const [pair,first] of left.entries()){
        assert(right.has(pair),'unpaired r1/r2 '+k+'/'+pair);
        examine(first,right.get(pair),row,k+'/'+pair);
        examine(first,right.get(pair),overall,k+'/'+pair);
      }
      groups[k]=row;
    }
  }
  assert(overall.n===432&&overall.r2_wrong===432-overall.r2_exact,'global totals');
  for(const [k,v] of Object.entries(groups))assert(v.n===(k.includes('/train/')?24:6),'group n');
  return {work_id:'AE1-CROSS-ROLE-PREFIX-20261113',source_git_blob:gitsha,
    source_pr:29,source_head:'dcabc3a65a4b9e7a50ab83ff8266b2c233d15000',
    students:4,paired_q:overall.n,total_archived_outputs:864,
    new_optimizer_updates:0,new_nn_forwards:0,overall,groups};
}
function selftest(){
  const x=empty(), a=word(1),b=word(2);
  examine([1,2,3,4,1,a+'S'],[1,2,3,4,2,a+b+'S'],x,'synthetic');
  assert(x.n===1&&x.r2_exact===1&&x.r1_r2_prefix_agree===1,'selftest correct');
  const y=empty();
  examine([1,2,3,4,1,a+'S'],[1,2,3,4,2,a+word(3)+'S'],y,'synthetic-error');
  assert(y.second_only===1&&y.r2_wrong===1&&y.r2_prefix_true===1,'selftest corruption');
  console.log('PASS synthetic correct/error controls');
}
if(require.main===module){
  if(process.argv[2]==='selftest')selftest();
  else{
    const source=process.argv[2]||DEFAULT_SOURCE;
    const result=analyze(fs.readFileSync(source));
    const json=JSON.stringify(result,null,2)+'\n';
    if(process.argv[3])fs.writeFileSync(process.argv[3],json);else process.stdout.write(json);
    console.error('PASS archive-gated 864 outputs / '+result.paired_q+' matched Q pairs, 0 NN forwards');
  }
}
module.exports={analyze,selftest};
