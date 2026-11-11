#!/usr/bin/env python3
"""SL-0.15: executable candidate AST A-run/A-scope/B and dictionary bootstrap.
NOT the official Spiral Language, NOT a cross-model or ICFP experiment.
Run: python3 SL15_雙模式語法與詞典同步成本驗證.py
Requires SL14_語法作用域繼承與語義漂移檢查.py in same directory or
/mnt/data/files/; Python stdlib only.
"""
from __future__ import annotations
import dataclasses, importlib.util, json, pathlib, random, struct, sys, zlib

HERE=pathlib.Path(__file__).resolve().parent
src=next((p for p in (HERE/'SL14_語法作用域繼承與語義漂移檢查.py', HERE/'files'/'SL14_語法作用域繼承與語義漂移檢查.py') if p.exists()),None)
if src is None:raise FileNotFoundError('Need original SL14 codec')
spec=importlib.util.spec_from_file_location('sl14_base',src)
base=importlib.util.module_from_spec(spec);sys.modules[spec.name]=base;spec.loader.exec_module(base)
Word,ListNode,Call,Scope=base.Word,base.ListNode,base.Call,base.Scope
u=base.u

# Run-mode token: 00 + layer(2) + local-index + tail0^k for a single word;
# 01 + layer(2) + count(8) + count local-index/tail0^k words, only inside lists;
# 10 + list count(8); 110 + call argc(8); 111 + scope layer(2).
# Distinct from A-scope's 01 override; frame scheme=3 distinguishes them.
def run_emit(node,d):
    if isinstance(node,Word):
        k,idx=d.loc[node.concept]
        return '00'+u(k,2)+u(idx,d.widths[k])+'0'*k
    if isinstance(node,ListNode):
        if len(node.children)>255:raise ValueError('list too long')
        out=['10'+u(len(node.children),8)];i=0;xs=node.children
        while i<len(xs):
            x=xs[i]
            if isinstance(x,Word):
                k=d.loc[x.concept][0];j=i+1
                while j<len(xs) and isinstance(xs[j],Word) and d.loc[xs[j].concept][0]==k and j-i<255:j+=1
                if j-i>=5: # 12-bit run header vs 4 bits per ordinary word
                    out.append('01'+u(k,2)+u(j-i,8))
                    out.extend(u(d.loc[y.concept][1],d.widths[k])+'0'*k for y in xs[i:j])
                    i=j;continue
            out.append(run_emit(x,d));i+=1
        return ''.join(out)
    if isinstance(node,Call):
        if len(node.args)>255:raise ValueError('call too long')
        return '110'+u(len(node.args),8)+run_emit(node.operator,d)+''.join(run_emit(x,d) for x in node.args)
    if isinstance(node,Scope):
        if node.layer not in d.layers:raise ValueError('bad scope')
        return '111'+u(node.layer,2)+run_emit(node.body,d)
    raise ValueError('unknown AST')

class Reader:
    def __init__(self,bits):self.bits=bits;self.pos=0
    def take(self,n):
        if self.pos+n>len(self.bits):raise ValueError('truncated')
        b=self.bits[self.pos:self.pos+n];self.pos+=n;return b
    def val(self,n):return int(self.take(n),2)

def run_parse(r,d,depth=0,allow_run=False):
    if depth>64:raise ValueError('too deep')
    t=r.take(2)
    if t=='00':
        k=r.val(2)
        if k not in d.layers:raise ValueError('bad word layer')
        idx=r.val(d.widths[k]);tail=r.take(k)
        if tail!='0'*k or idx>=len(d.layers[k]):raise ValueError('bad local code')
        return Word(d.layers[k][idx])
    if t=='01':
        if not allow_run:raise ValueError('run outside list')
        k=r.val(2);count=r.val(8)
        if k not in d.layers or count<5:raise ValueError('invalid run')
        out=[]
        for _ in range(count):
            idx=r.val(d.widths[k]);tail=r.take(k)
            if tail!='0'*k or idx>=len(d.layers[k]):raise ValueError('bad run item')
            out.append(Word(d.layers[k][idx]))
        return out
    if t=='10':
        n=r.val(8);xs=[]
        while len(xs)<n:
            x=run_parse(r,d,depth+1,True)
            if isinstance(x,list):
                if len(xs)+len(x)>n:raise ValueError('run overflows list')
                xs.extend(x)
            else:xs.append(x)
        return ListNode(tuple(xs))
    if r.take(1)=='0':
        n=r.val(8);op=run_parse(r,d,depth+1)
        if not isinstance(op,Word):raise ValueError('call operator not word')
        return Call(op,tuple(run_parse(r,d,depth+1) for _ in range(n)))
    k=r.val(2)
    if k not in d.layers:raise ValueError('bad scope')
    return Scope(k,run_parse(r,d,depth+1))

# Symmetric control: B also gets a word-run transport packing mode.
# Without this control, A-run's gain could simply be unfair removal of
# repeated AST word tags rather than an advantage of layered dictionaries.
def b_run_emit(node,d):
    if isinstance(node,Word):return '00'+u(d.gloc[node.concept],d.global_width)
    if isinstance(node,ListNode):
        if len(node.children)>255:raise ValueError('list too long')
        out=['10'+u(len(node.children),8)];i=0;xs=node.children
        while i<len(xs):
            if isinstance(xs[i],Word):
                j=i+1
                while j<len(xs) and isinstance(xs[j],Word) and j-i<255:j+=1
                if j-i>=5:
                    out.append('01'+u(j-i,8))
                    out.extend(u(d.gloc[y.concept],d.global_width) for y in xs[i:j])
                    i=j;continue
            out.append(b_run_emit(xs[i],d));i+=1
        return ''.join(out)
    if isinstance(node,Call):
        if len(node.args)>255:raise ValueError('call too long')
        return '110'+u(len(node.args),8)+b_run_emit(node.operator,d)+''.join(b_run_emit(x,d) for x in node.args)
    if isinstance(node,Scope):
        if node.layer not in d.layers:raise ValueError('bad scope')
        return '111'+u(node.layer,2)+b_run_emit(node.body,d)
    raise ValueError('unknown AST')

def b_run_parse(r,d,depth=0,allow_run=False):
    if depth>64:raise ValueError('too deep')
    t=r.take(2)
    if t=='00':
        idx=r.val(d.global_width)
        if idx>=len(d.global_order):raise ValueError('invalid global word')
        return Word(d.global_order[idx])
    if t=='01':
        if not allow_run:raise ValueError('run outside list')
        count=r.val(8)
        if count<5:raise ValueError('invalid B run')
        out=[]
        for _ in range(count):
            idx=r.val(d.global_width)
            if idx>=len(d.global_order):raise ValueError('bad B run word')
            out.append(Word(d.global_order[idx]))
        return out
    if t=='10':
        n=r.val(8);xs=[]
        while len(xs)<n:
            x=b_run_parse(r,d,depth+1,True)
            if isinstance(x,list):
                if len(xs)+len(x)>n:raise ValueError('B run overflows list')
                xs.extend(x)
            else:xs.append(x)
        return ListNode(tuple(xs))
    if r.take(1)=='0':
        n=r.val(8);op=b_run_parse(r,d,depth+1)
        if not isinstance(op,Word):raise ValueError('call operator not word')
        return Call(op,tuple(b_run_parse(r,d,depth+1) for _ in range(n)))
    k=r.val(2)
    if k not in d.layers:raise ValueError('bad scope')
    return Scope(k,b_run_parse(r,d,depth+1))

def encode_b_run(node,d,m):
    if set(d.global_order)!=set(m.meanings):raise ValueError('incomplete manifest')
    p=b_run_emit(node,d)
    return u(base.MAGIC,16)+u(d.ver,8)+u(0,2)+u(d.fp,32)+u(m.fp,32)+u(len(p),24)+u(zlib.crc32(p.encode()),32)+p

def encode_run(node,d,m):
    if set(d.global_order)!=set(m.meanings):raise ValueError('incomplete manifest')
    p=run_emit(node,d)
    return u(base.MAGIC,16)+u(d.ver,8)+u(3,2)+u(d.fp,32)+u(m.fp,32)+u(len(p),24)+u(zlib.crc32(p.encode()),32)+p

def decode_any(frame,registry=None):
    if registry is None:registry=base.REG
    if len(frame)<base.HEADER or set(frame)-{'0','1'}:raise ValueError('invalid frame')
    scheme=int(frame[24:26],2)
    if scheme in (1,2):return base.decode(frame,registry)
    if scheme not in (0,3):raise ValueError('invalid scheme')
    if int(frame[:16],2)!=base.MAGIC:raise ValueError('magic')
    ver=int(frame[16:24],2);dfp=int(frame[26:58],2);mfp=int(frame[58:90],2)
    n=int(frame[90:114],2);chk=int(frame[114:146],2);p=frame[146:]
    if n!=len(p) or zlib.crc32(p.encode())!=chk:raise ValueError('frame corrupt')
    if (ver,dfp,mfp) not in registry:raise ValueError('missing dictionary/manifest')
    d,m=registry[(ver,dfp,mfp)]
    r=Reader(p);node=run_parse(r,d) if scheme==3 else b_run_parse(r,d)
    if r.pos!=len(p):raise ValueError('trailing bits')
    return node,d,m,'A-run' if scheme==3 else 'B-run'

def all_frames(ast,d,m):
    return {'A-scope':base.encode(ast,d,m,'A'),
            'A-run':encode_run(ast,d,m),
            'B':base.encode(ast,d,m,'B'),
            'B-run':encode_b_run(ast,d,m)}

def canonical(obj):return json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf-8')

def pack(obj):
    # Fixed bootstrap framing: ASCII magic + byte length + zlib + CRC32;
    # unlike the SLE data frame, it does NOT require an SLE dictionary to read.
    b=zlib.compress(canonical(obj),level=6)
    return b'SL15'+struct.pack('>I',len(b))+b+struct.pack('>I',zlib.crc32(b))

def unpack(buf):
    if len(buf)<12 or buf[:4]!=b'SL15':raise ValueError('bootstrap magic')
    n=struct.unpack('>I',buf[4:8])[0]
    if n>10_000_000 or len(buf)!=n+12:raise ValueError('bootstrap length')
    b=buf[8:8+n]
    if zlib.crc32(b)!=struct.unpack('>I',buf[-4:])[0]:raise ValueError('bootstrap checksum')
    return json.loads(zlib.decompress(b).decode('utf-8'))

def snapshot(d,m):
    return {'kind':'snapshot','version':d.ver,'layers':{str(k):list(v) for k,v in d.layers.items()},
            'widths':{str(k):v for k,v in d.widths.items()},'global_width':d.global_width,
            'global_order':list(d.global_order),'meanings':m.meanings,'dict_fp':d.fp,'meaning_fp':m.fp}

def from_snapshot(s):
    if s['kind']!='snapshot':raise ValueError('not snapshot')
    d=base.Dictionary(s['version'],{int(k):v for k,v in s['layers'].items()},
        {int(k):v for k,v in s['widths'].items()},s['global_width'],tuple(s['global_order']))
    m=base.Manifest(s['meanings'])
    if d.fp!=s['dict_fp'] or m.fp!=s['meaning_fp']:raise ValueError('fingerprint mismatch')
    return d,m

def delta(old_d,old_m,new_d,new_m):
    # This delta format only permits append-only dictionaries; removal/reorder
    # must fall back to a full snapshot (do not silently remap old code indices).
    for k in (1,2):
        if new_d.layers[k][:len(old_d.layers[k])]!=old_d.layers[k]:raise ValueError('not append-only')
    if new_d.global_order[:len(old_d.global_order)]!=old_d.global_order:raise ValueError('global reorder')
    if any(old_m.meanings[k]!=new_m.meanings.get(k) for k in old_m.meanings):
        # semantic changes are allowed but explicitly transmitted below
        pass
    return {'kind':'delta','from':old_d.ver,'from_dict_fp':old_d.fp,'from_meaning_fp':old_m.fp,
        'to':new_d.ver,'to_dict_fp':new_d.fp,'to_meaning_fp':new_m.fp,
        'layer_append':{str(k):new_d.layers[k][len(old_d.layers[k]):] for k in (1,2)},
        'global_append':list(new_d.global_order[len(old_d.global_order):]),
        'widths':{str(k):v for k,v in new_d.widths.items()},'global_width':new_d.global_width,
        'meaning_changes':{k:v for k,v in new_m.meanings.items() if old_m.meanings.get(k)!=v}}

def apply_delta(old_d,old_m,change):
    if change['kind']!='delta' or (old_d.ver,old_d.fp,old_m.fp)!=(change['from'],change['from_dict_fp'],change['from_meaning_fp']):
        raise ValueError('missing or wrong delta base')
    layers={k:old_d.layers[k]+change['layer_append'][str(k)] for k in (1,2)}
    d=base.Dictionary(change['to'],layers,{int(k):v for k,v in change['widths'].items()},
        change['global_width'],tuple(old_d.global_order+tuple(change['global_append'])))
    meanings=dict(old_m.meanings);meanings.update(change['meaning_changes']);m=base.Manifest(meanings)
    if d.fp!=change['to_dict_fp'] or m.fp!=change['to_meaning_fp']:raise ValueError('delta target mismatch')
    return d,m

def must_fail(f):
    try:f()
    except (ValueError,KeyError,zlib.error,UnicodeDecodeError):return
    raise AssertionError('expected failure')

def workload(d,kind,rng):
    def words(k,n):return tuple(Word(rng.choice(d.layers[k])) for _ in range(n))
    def chunks(xs):return ListNode(tuple(ListNode(xs[i:i+200]) for i in range(0,len(xs),200)))
    if kind=='flat_90_10':
        return chunks(tuple(Word(rng.choice(d.layers[1] if rng.random()<.9 else d.layers[2])) for _ in range(1000)))
    if kind=='flat_alternating':
        return chunks(tuple(Word(rng.choice(d.layers[1 if i%2==0 else 2])) for i in range(1000)))
    if kind=='scoped_90_10':
        return ListNode((Scope(1,chunks(words(1,900))),Scope(2,chunks(words(2,100)))))
    if kind=='scoped_50_50':
        return ListNode((Scope(1,chunks(words(1,500))),Scope(2,chunks(words(2,500)))))
    if kind=='nested_mixed':
        return ListNode(tuple(Scope(2,Call(Word('回答'),(Scope(1,ListNode((Word('數學'),Word('加'),Word('數值')))),Word('問號')))) for _ in range(200)))
    raise ValueError('bad workload')

def main():
    rng=random.Random(20261102)
    count=0
    for d in base.DICTS:
        m=base.manifest(d)
        for _ in range(500):
            ast=base.random_ast(rng,d)
            for name,frame in all_frames(ast,d,m).items():
                got,dd,mm,mode=decode_any(frame)
                assert (got,dd.fp,mm.fp)==(ast,d.fp,m.fp)
                count+=1
    print('AST_FOUR_MODES_ROUNDTRIP_PASS',count)
    print('version workload A_scope_bits A_run_bits A_adaptive_bits B_bits B_run_bits B_adaptive_bits best')
    for d in base.DICTS:
        m=base.manifest(d)
        for kind in ('flat_90_10','flat_alternating','scoped_90_10','scoped_50_50','nested_mixed'):
            ast=workload(d,kind,rng);frames=all_frames(ast,d,m)
            assert all(decode_any(x)[0]==ast for x in frames.values())
            lens={k:len(v) for k,v in frames.items()}
            adaptive=min(lens['A-scope'],lens['A-run'])
            badaptive=min(lens['B'],lens['B-run'])
            print(d.ver,kind,lens['A-scope'],lens['A-run'],adaptive,lens['B'],lens['B-run'],badaptive,min(lens,key=lens.get))
    print('BOOTSTRAP_SYNC_BYTES (zlib6 UTF8 JSON, includes 12-byte bootstrap envelope)')
    snapshots=[pack(snapshot(d,base.manifest(d))) for d in base.DICTS]
    changes=[pack(delta(a,base.manifest(a),b,base.manifest(b))) for a,b in zip(base.DICTS,base.DICTS[1:])]
    for i,x in enumerate(snapshots):
        d,m=from_snapshot(unpack(x));assert (d.fp,m.fp)==(base.DICTS[i].fp,base.manifest(base.DICTS[i]).fp)
        print('snapshot_v',i+1,len(x))
    for i,x in enumerate(changes):
        a=base.DICTS[i];b=base.DICTS[i+1]
        d,m=apply_delta(a,base.manifest(a),unpack(x))
        assert (d.fp,m.fp)==(b.fp,base.manifest(b).fp)
        print('delta_v',i+1,'to',i+2,len(x))
    v1=base.DICTS[0];d,m=v1,base.manifest(v1)
    for x in changes:d,m=apply_delta(d,m,unpack(x))
    assert (d.fp,m.fp)==(base.V3.fp,base.manifest(base.V3).fp)
    direct=pack(delta(base.V1,base.manifest(base.V1),base.V3,base.manifest(base.V3)))
    direct_d,direct_m=apply_delta(base.V1,base.manifest(base.V1),unpack(direct))
    assert (direct_d.fp,direct_m.fp)==(base.V3.fp,base.manifest(base.V3).fp)
    print('offline_v1_to_v3_delta_chain_bytes',sum(map(len,changes)),'direct_delta_bytes',len(direct),'full_v3_bytes',len(snapshots[-1]))
    print('new_peer_v3_full_bytes',len(snapshots[-1]))
    print('cached_peer_v3_frame_only_bytes', (len(encode_run(base.sample_ast(),base.V3,base.manifest(base.V3)))+7)//8)
    # Receiver capability negotiation: never send an unknown transport view.
    example=workload(base.V3,'flat_alternating',random.Random(123))
    offered=all_frames(example,base.V3,base.manifest(base.V3))
    legacy={'A-scope','B'}; modern={'A-scope','A-run','B','B-run'}
    assert min((len(offered[k]),k) for k in legacy)[1]=='B'
    assert min((len(offered[k]),k) for k in modern)[1]=='B-run'
    print('CAPABILITY_NEGOTIATION_FALLBACK_PASS')
    # If receiver has only v1 and receives a v3 frame, refuse; cannot guess meaning.
    v3_frame=encode_run(base.sample_ast(),base.V3,base.manifest(base.V3))
    only_v1={(v1.ver,v1.fp,base.manifest(v1).fp):(v1,base.manifest(v1))}
    must_fail(lambda:decode_any(v3_frame,only_v1))
    must_fail(lambda:apply_delta(base.V1,base.manifest(base.V1),unpack(changes[1])))
    must_fail(lambda:unpack(snapshots[0][:-1]+bytes([snapshots[0][-1]^1])))
    must_fail(lambda:unpack(snapshots[0][:-1]))
    must_fail(lambda:decode_any(v3_frame[:-1]))
    # same ID/name but changed declared meaning: no silent semantic migration.
    drift=base.DRIFT
    changed=delta(base.V1,base.manifest(base.V1),base.V2,drift)
    dv,dm=apply_delta(base.V1,base.manifest(base.V1),changed)
    assert dm.fp==drift.fp and dv.fp==base.V2.fp
    old_frame=base.encode(ListNode((Word('加'),)),base.V1,base.manifest(base.V1),'A')
    old_ast,_,old_m,_=decode_any(old_frame)
    must_fail(lambda: _check_used_meanings(old_ast,old_m,dm))
    print('OFFLINE_RECOVERY_AND_DRIFT_REJECTION_PASS')
    print('IMPORTANT: bootstrap uses independent fixed byte framing; not a self-hosted SLE dictionary')

def _check_used_meanings(ast,src,dst):
    for c in base.concepts(ast):
        if src.meanings[c]!=dst.meanings.get(c):raise ValueError('semantic drift '+c)

if __name__=='__main__':main()