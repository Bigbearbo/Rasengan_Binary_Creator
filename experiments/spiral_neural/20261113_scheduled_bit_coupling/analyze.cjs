'use strict';
const fs=require('fs');
const assert=require('assert');
const analyze=function analyze(raw,sha) {
  const assert=(ok,msg)=>{if(!ok)throw Error(msg)};
  assert(sha==="62f6d95bad4abf3dc57a6852eb990be9bcabd96d","source blob mismatch");
  const rows=raw.trim().split("\n").map(x=>JSON.parse(x));
  const word=v=>v.toString(2).padStart(5,"0")+"0";
  const q=(r,a,b,c,d)=>"01"+"010"+r.toString(2).padStart(3,"0")+"0"+[a,b,c,d].map(word).join("")+"111100";
  const expected=(r,a,b)=>word(a)+(r===2?word(b):"")+"S";
  const group=b=>b<=5?"known_0_5":b<=14?"suffix_only_6_14":"unseen_15_29";
  const seen=new Set(),byContext=new Map(),totals={known_0_5:[0,0],suffix_only_6_14:[0,0],unseen_15_29:[0,0]};
  let invalidSuffixZero=0;let wrongStop=0;
  for(const x of rows) {
    assert([101,202].includes(x.seed)&&["fixed","varied"].includes(x.mode)&&Number.isInteger(x.a)&&x.a>=0&&x.a<=5&&Number.isInteger(x.b)&&x.b>=0&&x.b<=29&&[1,2].includes(x.r),"invalid index");
    assert(x.Q===q(x.r,x.a,x.b,x.c,x.d)&&x.Q.length===39,"Q profile invalid");
    assert(x.expected===expected(x.r,x.a,x.b),"answer invalid");
    assert(x.actual.length===x.expected.length&&/^[01]+S$/.test(x.actual),"output length/stop invalid");
    const k=[x.seed,x.mode,x.a,x.b,x.r].join("|");
    assert(!seen.has(k),"duplicate row "+k);seen.add(k);
    const ctx=[x.seed,x.mode,x.a].join("|");
    if(!byContext.has(ctx))byContext.set(ctx,{seed:x.seed,mode:x.mode,a:x.a,rows:{1:new Map(),2:new Map()}});
    byContext.get(ctx).rows[x.r].set(x.b,x);
    const g=group(x.b);totals[g][x.r-1]+=(x.actual===x.expected);
    if(x.r===2&&x.actual[11]!=="0")invalidSuffixZero++;
  }
  assert(rows.length===1440&&seen.size===1440&&byContext.size===24,"missing rows");
  assert(JSON.stringify(totals)==='{"known_0_5":[143,115],"suffix_only_6_14":[136,1],"unseen_15_29":[224,0]}',"published exact counts mismatch");
  const ranges={known_0_5:[0,5],suffix_only_6_14:[6,14],unseen_15_29:[15,29]};
  const result={};
  const modelResult={};
  for(const [name,[min,max]] of Object.entries(ranges)) {
    const edgeByBit=Array.from({length:5},(_,bit)=>({bit,aligned:0,reversed:0,unchanged:0,invalid:0,r1_first_word_changed:0,r2_first_word_changed:0,total:0}));
    const counts={n:0,info_bits_correct:0,info_bits_total:0,majority_baseline_correct:0,target_ones:Array(5).fill(0),actual_ones:Array(5).fill(0),structural_zero_correct:0};
    for(const x of rows)if(x.r===2&&x.b>=min&&x.b<=max){
      counts.n++;counts.structural_zero_correct+=x.actual[11]==="0";
      for(let j=0;j<5;j++){const t=x.expected[6+j],p=x.actual[6+j];counts.info_bits_total++;counts.info_bits_correct+=(t===p);counts.target_ones[j]+=(t==="1");counts.actual_ones[j]+=(p==="1")}
    }
    counts.majority_baseline_correct=counts.target_ones.reduce((sum,n)=>sum+Math.max(n,counts.n-n),0);
    counts.info_bit_accuracy=counts.info_bits_correct/counts.info_bits_total;
    counts.majority_bit_accuracy=counts.majority_baseline_correct/counts.info_bits_total;
    for(const ctx of byContext.values()) {
      const mk=ctx.seed+"-"+ctx.mode,local=[];
      for(let bit=0;bit<5;bit++){
        const e=edgeByBit[bit];
        for(let b=min;b<=max;b++){
          if((b&(1<<bit))!==0)continue;
          let other=b|(1<<bit);
          if(other>max||other<min)continue;
          const low=ctx.rows[2].get(b),hi=ctx.rows[2].get(other);
          const lowCtrl=ctx.rows[1].get(b),highCtrl=ctx.rows[1].get(other);
          assert(low&&hi&&lowCtrl&&highCtrl,"missing edge");
          const p=6+(4-bit),L=low.actual[p],H=hi.actual[p];
          e.total++;
          let kind;
          if(!"01".includes(L)||!"01".includes(H)){e.invalid++;kind="invalid"}
          else if(L==="0"&&H==="1"){e.aligned++;kind="aligned"}
          else if(L==="1"&&H==="0"){e.reversed++;kind="reversed"}
          else{e.unchanged++;kind="unchanged"}
          if(lowCtrl.actual.slice(0,6)!==highCtrl.actual.slice(0,6))e.r1_first_word_changed++;
          if(low.actual.slice(0,6)!==hi.actual.slice(0,6))e.r2_first_word_changed++;
          local.push({bit,low:b,high:other,kind,low_pred:L,high_pred:H});
        }
      }
      if(!modelResult[mk])modelResult[mk]={seed:ctx.seed,mode:ctx.mode,groups:{}};
      const tally={aligned:local.filter(x=>x.kind==="aligned").length,reversed:local.filter(x=>x.kind==="reversed").length,unchanged:local.filter(x=>x.kind==="unchanged").length,invalid:local.filter(x=>x.kind==="invalid").length,n:local.length};
      tally.signed=tally.aligned-tally.reversed;
      modelResult[mk].groups[name]=(modelResult[mk].groups[name]||[]).concat([{a:ctx.a,...tally}]);
    }
    const totalEdges=edgeByBit.reduce((s,x)=>s+x.total,0);
    const aligned=edgeByBit.reduce((s,x)=>s+x.aligned,0),reversed=edgeByBit.reduce((s,x)=>s+x.reversed,0),unchanged=edgeByBit.reduce((s,x)=>s+x.unchanged,0);
    result[name]={rows:counts,edges:{total:totalEdges,aligned,reversed,unchanged,signed:aligned-reversed,r1_first_word_changed:edgeByBit.reduce((s,x)=>s+x.r1_first_word_changed,0),r2_first_word_changed:edgeByBit.reduce((s,x)=>s+x.r2_first_word_changed,0),by_input_bit:edgeByBit}};
  }
  let seeds={};
  for(const m of Object.values(modelResult))for(const [group,xs] of Object.entries(m.groups)){
    const k=m.seed+"-"+group;
    if(!seeds[k])seeds[k]={seed:m.seed,group,aligned:0,reversed:0,unchanged:0,signed:0,n:0};
    for(const x of xs){for(const s of ["aligned","reversed","unchanged","signed","n"])seeds[k][s]+=x[s]}
  }
  const sign24=Object.fromEntries(Object.keys(ranges).map(name=>{
    const vals=Object.values(modelResult).flatMap(m=>m.groups[name]).map(x=>x.signed);
    return [name,{positive:vals.filter(v=>v>0).length,zero:vals.filter(v=>v===0).length,negative:vals.filter(v=>v<0).length,total:vals.length}];
  }));
  return {source_commit:"23963d32f0ef75c5890cfdd5bc9d320621754f32",source_raw_blob:sha,rows:rows.length,contexts:byContext.size,reference_exact:totals,all_stop_correct:true,invalid_second_word_terminal_0:invalidSuffixZero,metrics:result,per_model:modelResult,per_seed:seeds,context_signs:sign24,training_updates:0,forward_calls:0,MAC:0};
};
if(require.main===module){const path=process.argv[2]||require('path').join(__dirname,'../20261113_scheduled_b_vocab_transfer/raw_cases.jsonl');const raw=fs.readFileSync(path,'utf8');const crypto=require('crypto');const expectedBlob='62f6d95bad4abf3dc57a6852eb990be9bcabd96d';const actualBlob=crypto.createHash('sha1').update('blob '+Buffer.byteLength(raw,'utf8')+'\0','utf8').update(raw,'utf8').digest('hex');if(actualBlob!==expectedBlob)throw Error('git blob SHA mismatch: '+actualBlob);const result=analyze(raw,actualBlob);process.stdout.write(JSON.stringify(result,null,2)+'\n');}
module.exports=analyze;
