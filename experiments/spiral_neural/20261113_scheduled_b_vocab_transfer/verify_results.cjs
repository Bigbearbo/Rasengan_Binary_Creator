#!/usr/bin/env node
'use strict';
// Metadata + published raw-output audit. Zero NN forward, zero optimizer updates.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const dir=__dirname;
const read=n=>fs.readFileSync(path.join(dir,n));
const gitBlob=b=>crypto.createHash('sha1').update(Buffer.from('blob '+b.length+'\0')).update(b).digest('hex');
const assert=(ok,msg)=>{if(!ok)throw Error('audit fail: '+msg)};
const expected={
  'core.js':'c6fb4968c352ecc1f1a8827d81cee0b99f462b20',
  'raw_cases.jsonl':'62f6d95bad4abf3dc57a6852eb990be9bcabd96d',
  'results_summary.json':'5a035a0cee7967dd1f47e7ba214e9fe5284c77d1'
};
for(const [name,sha] of Object.entries(expected))assert(gitBlob(read(name))===sha,'blob '+name);
const p=JSON.parse(read('protocol.json').toString('utf8'));
const s=JSON.parse(read('results_summary.json').toString('utf8'));
const rows=read('raw_cases.jsonl').toString('utf8').trimEnd().split('\n').map(JSON.parse);
const w=n=>n.toString(2).padStart(5,'0')+'0';
const Q=x=>'01'+'010'+x.r.toString(2).padStart(3,'0')+'0'+[x.a,x.b,x.c,x.d].map(w).join('')+'111100';
const answer=x=>w(x.a)+(x.r===2?w(x.b):'')+'S';
assert(rows.length===1440,'rows count');
assert(new Set(rows.map(x=>[x.seed,x.mode,x.Q].join('|'))).size===1440,'unique model/Q');
for(const x of rows) {
  assert(x.Q===Q(x) && x.Q.length===39,'invalid SLE input');
  assert(x.expected===answer(x),'invalid expected SLE output');
  assert(x.a>=0&&x.a<6&&x.b>=0&&x.b<=29&&x.c>=15&&x.c<=29&&x.d>=15&&x.d<=29,'range');
}
const groups=[['known_b_0_5',x=>x.b<=5],['suffix_role_only_b_6_14',x=>x.b>=6&&x.b<=14],['train_unseen_b_15_29',x=>x.b>=15&&x.b<=29],['train_unseen_b_15_29_no_collision',x=>x.b>=15&&x.b<=29&&!x.collision_with_suffix]];
for(const [group,fn] of groups)for(const r of [1,2]) {
  const xs=rows.filter(x=>x.r===r&&fn(x));
  const v=s.group_statistics[group+'_r'+r];
  assert(xs.length===v.n,'n '+group+r);
  assert(xs.filter(x=>x.actual===x.expected).length===v.exact,'exact '+group+r);
  assert(xs.filter(x=>x.actual.slice(0,6)===w(x.a)).length===v.first_word,'first '+group+r);
  assert(xs.filter(x=>x.actual.endsWith('S')&&x.actual.length===x.expected.length).length===v.stop_at_right_position,'stop '+group+r);
  if(r===2)assert(xs.filter(x=>x.actual.slice(6,12)===w(x.b)).length===v.second_word,'second '+group+r);
}
assert(p.source_blobs['weights_seed101_fixed.json']==='a76bc7608bfe36683e7ed06bd2949483795534d5','frozen checkpoint');
assert(s.archived_outputs_verified===864&&s.new_outputs===1440&&s.new_optimizer_updates===0,'run metadata');
assert(s.total_forward_calls===23040&&s.total_dense_MAC===240353280,'forward/MAC');
console.log('PASS: 1440 model/Q unique legal-bit rows, all 8 group metrics and source-gate metadata match; archived NN replay not rerun by this audit.');
