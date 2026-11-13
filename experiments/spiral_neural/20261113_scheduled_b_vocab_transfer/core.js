'use strict';
// Pure-JS, dependency-free AE1 neural inference. Inject load(name)->{sha,content}.
// Entry returns all raw Q/target/predictions; no student receives an oracle.
// Matches the archived PR29 PyTorch [160,64,3] tanh network forward semantics.
function runAE1BTransfer(load, spec) {
  const fail=(m)=>{throw Error(m)};
  const assert=(b,m)=>{if(!b)fail(m)};
  const base='experiments/spiral_neural/20261113_scheduled_suffix_exposure/';
  const expected=spec.source_blobs;
  function read(name) {
    const v=load((name==='results.json'?base:base+'checkpoints/')+name);
    assert(v && v.sha===expected[name], 'frozen source Git blob failed '+name+' '+(v&&v.sha));
    return JSON.parse(v.content);
  }
  function b64(str) {
    const alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
    const out=[];
    assert(str.length%4===0,'base64 length');
    for(let i=0;i<str.length;i+=4) {
      const a=alphabet.indexOf(str[i]),b=alphabet.indexOf(str[i+1]);
      const c=str[i+2]==='='?0:alphabet.indexOf(str[i+2]);
      const d=str[i+3]==='='?0:alphabet.indexOf(str[i+3]);
      assert(a>=0&&b>=0&&c>=0&&d>=0,'base64 alphabet');
      const n=(a<<18)|(b<<12)|(c<<6)|d;
      out.push((n>>16)&255);
      if(str[i+2]!=='=')out.push((n>>8)&255);
      if(str[i+3]!=='=')out.push(n&255);
    }
    return Uint8Array.from(out);
  }
  function floats(obj,k,shape) {
    const t=obj.tensors[k];
    assert(t&&t.dtype==='float32'&&JSON.stringify(t.shape)===JSON.stringify(shape),'bad tensor '+k);
    const bytes=b64(t.little_endian_base64),n=shape.reduce((x,y)=>x*y,1);
    assert(bytes.length===n*4,'bad tensor size '+k);
    const dv=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);
    const out=new Float64Array(n);
    for(let i=0;i<n;i++)out[i]=dv.getFloat32(i*4,true);
    return out;
  }
  function loadModel(meta) {
    assert(meta.schema==='AE1-SUFFIX-FINAL-WEIGHTS-v1'&&meta.updates===1600,'model meta schema/updates');
    return {seed:meta.seed,mode:meta.mode,sha:meta.final_weights_sha256,
      w:floats(meta,'0.weight',[64,160]),b:floats(meta,'0.bias',[64]),
      v:floats(meta,'2.weight',[3,64]),d:floats(meta,'2.bias',[3])};
  }
  function word(n) {assert(Number.isInteger(n)&&n>=0&&n<30,'illegal data ID '+n);return n.toString(2).padStart(5,'0')+'0'}
  function Q(r,a,b,c,d) {return '01'+'010'+r.toString(2).padStart(3,'0')+'0'+[a,b,c,d].map(word).join('')+'111100'}
  function A(r,a,b) {return word(a)+(r===2?word(b):'')+'S'}
  function split(a,b) {if(b>=6)return 'answer_role_unseen';const residue=(a+b)%6;return residue===0?'val':residue===1?'test':'train'}
  function group(b) {return b<6?'known_b_0_5':b<15?'suffix_role_only_b_6_14':'train_unseen_b_15_29'}
  assert(Q(2,0,1,18,26)===spec.test_design.example.Q_r2_a0_b1_c18_d26,'example Q fixture');
  assert(Q(2,0,6,18,26)===spec.test_design.example.Q_r2_a0_b6_c18_d26,'example new Q fixture');
  assert(A(2,0,6)===spec.test_design.example.A_r2_a0_b6,'example target fixture');
  let totalForward=0;
  function next(m,s) {
    assert(s.length>=1&&s.length<=80&&/^[01]+$/.test(s),'context malformed/overlong');
    const act=[];
    for(let i=0;i<s.length;i++)act.push(i*2+(s[i]==='1'?1:0));
    const hid=new Float64Array(64);
    for(let h=0;h<64;h++){
      let z=m.b[h],off=h*160;
      for(let j=0;j<act.length;j++)z+=m.w[off+act[j]];
      hid[h]=Math.tanh(z);
    }
    let ix=-1,best=-Infinity;
    for(let k=0;k<3;k++){
      let z=m.d[k],off=k*64;
      for(let h=0;h<64;h++)z+=m.v[off+h]*hid[h];
      if(z>best){best=z;ix=k}
    }
    totalForward++;
    return '01S'[ix];
  }
  function generate(m,q) {
    let out='';
    for(let j=0;j<32;j++){
      if(q.length+out.length>80)return {actual:out,cause:'overflow'};
      out+=next(m,q+out);
      if(out.endsWith('S'))return {actual:out,cause:'stop'};
    }
    return {actual:out,cause:'cap'};
  }
  const archival=read('results.json');
  const filenames=['weights_seed101_fixed.json','weights_seed101_varied.json','weights_seed202_fixed.json','weights_seed202_varied.json'];
  const models=filenames.map(name=>{const m=loadModel(read(name));m.filename=name;return m});
  const replay=[];
  // All 864 archived outputs form an unconditional gate before ANY fresh probe.
  for(const m of models){
    const prior=archival.per_model.find(x=>x.seed===m.seed&&x.mode===m.mode);
    assert(prior&&prior.final_weights_sha256===m.sha,'state/archived SHA conflict '+m.filename);
    let matches=0;
    for(const p of ['train','val','test'])for(const suffix of ['seen','changed_low','unseen_high'])for(const r of [1,2]) {
      const rows=prior.evaluation[p][suffix][String(r)].predictions;
      for(const [a,b,c,d,rr,old] of rows) {
        assert(rr===r&&split(a,b)===p,'archive metadata mismatch');
        const prediction=generate(m,Q(r,a,b,c,d)).actual;
        assert(prediction===old,'archival forward mismatch '+[m.seed,m.mode,a,b,c,d,r]);
        matches++;
      }
    }
    assert(matches===216,'archive count '+matches);
    replay.push({seed:m.seed,mode:m.mode,weights_sha256:m.sha,matched:matches});
  }
  const gateForward=totalForward;
  assert(replay.reduce((x,v)=>x+v.matched,0)===864,'archive total gate');

  const records=[];
  for(const m of models)for(let a=0;a<6;a++){
    const b0=(1-a+6)%6;
    assert(split(a,b0)==='test','test anchor invalid');
    const c=15+(7*a+3*b0)%15,d=15+(5*a+11*b0)%15;
    for(const r of [1,2]){
      const original=Q(r,a,b0,c,d);
      for(let b=0;b<30;b++){
        const q=Q(r,a,b,c,d),expectedAnswer=A(r,a,b);
        assert(q.length===39&&q.slice(0,15)===original.slice(0,15)&&q.slice(21)===original.slice(21),'not b-only changed');
        assert(q.slice(15,21)===word(b),'b bit offset wrong');
        const got=generate(m,q);
        records.push({seed:m.seed,mode:m.mode,a,b,b0,c,d,r,group:group(b),
          pair_split:split(a,b),collision_with_suffix:b===c||b===d,
          Q:q,expected:expectedAnswer,actual:got.actual,cause:got.cause});
      }
    }
  }
  assert(records.length===1440,'wrong probe count');
  const count=arr=>({
    n:arr.length,exact:arr.filter(x=>x.actual===x.expected).length,
    first_word:arr.filter(x=>x.actual.slice(0,6)===word(x.a)).length,
    second_word:arr.filter(x=>x.r===2&&x.actual.slice(6,12)===word(x.b)).length,
    stop_at_right_position:arr.filter(x=>x.actual.endsWith('S')&&x.actual.length===x.expected.length).length,
    no_stop:arr.filter(x=>!x.actual.endsWith('S')).length,
    cap:arr.filter(x=>x.cause==='cap').length,overflow:arr.filter(x=>x.cause==='overflow').length
  });
  const strata={};
  for(const g of ['known_b_0_5','suffix_role_only_b_6_14','train_unseen_b_15_29','train_unseen_b_15_29_no_collision'])
    for(const r of [1,2]) {
      const xs=records.filter(x=>x.r===r&&(g.endsWith('no_collision')?
        x.group==='train_unseen_b_15_29'&&!x.collision_with_suffix:x.group===g));
      strata[g+'_r'+r]=count(xs);
    }
  const byModel=models.map(m=>({seed:m.seed,mode:m.mode,byGroup:Object.fromEntries(
    Object.keys(strata).map(key=>{
      const r=Number(key.slice(-1)),g=key.slice(0,-3);
      const xs=records.filter(x=>x.seed===m.seed&&x.mode===m.mode&&x.r===r&&
        (g==='train_unseen_b_15_29_no_collision'?x.group==='train_unseen_b_15_29'&&!x.collision_with_suffix:x.group===g));
      return [key,count(xs)];
    })
  )}));
  const heldoutKnown={};
  for(const s of ['train','val','test'])heldoutKnown[s]=count(records.filter(x=>x.r===2&&x.pair_split===s));
  const r1_invariance=records.filter(x=>x.r===1).reduce((sum,x)=>{
    const base=records.find(y=>y.seed===x.seed&&y.mode===x.mode&&y.a===x.a&&y.r===1&&y.b===x.b0);
    return sum+(x.actual===base.actual?1:0);
  },0);
  const examples=Object.fromEntries(['known_b_0_5','suffix_role_only_b_6_14','train_unseen_b_15_29'].map(g=>
    [g,records.filter(x=>x.group===g&&x.r===2&&x.actual!==x.expected).slice(0,8)]));
  const summary={work_id:spec.work_id,source_ref:spec.base_ref,source_file_sha:expected,
    model_architecture:"160 input -> 64 tanh -> 3 logits",parameters_per_model:10499,models:4,
    archived_outputs_verified:864,archival_forward_calls:gateForward,new_outputs:records.length,
    new_forward_calls:totalForward-gateForward,total_forward_calls:totalForward,
    new_dense_MAC:(totalForward-gateForward)*10432,total_dense_MAC:totalForward*10432,
    new_optimizer_updates:0,group_statistics:strata,known_b_pair_split_r2:heldoutKnown,
    r1_invariance_count:r1_invariance,r1_invariance_total:records.filter(x=>x.r===1).length,
    by_model:byModel,failure_examples:examples,
    scope_note:"Pretrained PR29 frozen nets; group b=6..14 may be seen as suffix, b=15..29 never trained; a,c,d fixed. The anchor c,d are high and group15..29 can collide, so noncollision is also reported; not a blind test or proof of SLE superiority.",
    nvidia_calls:0,codex_local_calls:0};
  return {summary,records};
}
if(typeof module!=='undefined'&&module.exports) module.exports=runAE1BTransfer;
