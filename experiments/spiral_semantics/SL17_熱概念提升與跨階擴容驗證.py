#!/usr/bin/env python3
"""SL-0.17: candidate A/B word encoders, reversible concept promotion, stable bridge IDs.
Not an official SLE grammar and not a cross-model learning experiment.
"""
import json, zlib, math, random
from dataclasses import dataclass


def gamma(n):
    assert n >= 1
    b = format(n, 'b')
    return '0' * (len(b) - 1) + b

class Reader:
    def __init__(self, bits): self.bits, self.i = bits, 0
    def take(self, n):
        if self.i + n > len(self.bits): raise ValueError('truncated')
        out = self.bits[self.i:self.i+n]
        self.i += n
        return out
    def g(self):
        zeros = 0
        while self.take(1) == '0': zeros += 1
        return int('1' + self.take(zeros), 2)
    def done(self):
        if self.i != len(self.bits): raise ValueError('trailing bits')


def width(n):
    return max(1, (n-1).bit_length())

@dataclass(frozen=True)
class Concept:
    sid: int
    name: str
    layer: int
    slot: int
    meaning: tuple

class Lexicon:
    def __init__(self, n, layers, version=1, promote=False):
        self.version, self.layers = version, layers
        self.concepts = []
        counters = [0] * layers
        for i in range(n):
            layer = i % layers + 1
            slot = counters[layer-1]
            counters[layer-1] += 1
            # 'aa' sorts ahead of all original names; sorting names is unsafe for bridge IDs
            self.concepts.append(Concept(i, f'item{i:05d}', layer, slot, ('base', i)))
        if promote:
            layer = 2
            self.concepts.append(Concept(n, 'aa_promoted', layer, counters[layer-1], ('pair', 0, 1)))
        self.by_id = {c.sid: c for c in self.concepts}
        self.by_loc = {(c.layer,c.slot): c for c in self.concepts}
        self.counts = [sum(c.layer == k for c in self.concepts) for k in range(1,layers+1)]
        self.bwidth = width(len(self.concepts))
        self.awidth = {k:width(self.counts[k-1]) for k in range(1,layers+1)}

    def word(self, sid, route):
        c = self.by_id[sid]
        if route == 'A':
            return gamma(c.layer) + format(c.slot, f'0{self.awidth[c.layer]}b')
        if route == 'B':
            return format(sid, f'0{self.bwidth}b')
        raise ValueError(route)

    def read_word(self, reader, route):
        if route == 'A':
            layer = reader.g()
            if layer not in self.awidth: raise ValueError('unknown layer')
            slot = int(reader.take(self.awidth[layer]), 2)
            c = self.by_loc.get((layer, slot))
        else:
            sid = int(reader.take(self.bwidth), 2)
            c = self.by_id.get(sid)
        if c is None: raise ValueError('unknown word')
        return c.sid

    def encode(self, tokens, route):
        bits = gamma(self.version) + gamma(len(tokens)+1)
        for t in tokens:
            if isinstance(t, int):
                bits += '1' + self.word(t,route)
            else:
                assert len(t)==2 and all(x in self.by_id for x in t)
                bits += '0' + ''.join(self.word(x,route) for x in t)
        return bits

    def decode(self, bits, route):
        r = Reader(bits)
        if r.g() != self.version: raise ValueError('wrong version')
        count = r.g() - 1
        out=[]
        for _ in range(count):
            if r.take(1)=='1': out.append(self.read_word(r,route))
            else: out.append((self.read_word(r,route),self.read_word(r,route)))
        r.done()
        return out

    def meaning(self, t):
        if isinstance(t,int): return self.by_id[t].meaning
        return ('pair', t[0], t[1])

    def snapshot_bytes(self, route):
        arr=[]
        for c in self.concepts:
            d={'id':c.sid,'name':c.name,'meaning':c.meaning}
            if route=='A': d.update(layer=c.layer,slot=c.slot)
            arr.append(d)
        raw=json.dumps({'v':self.version,'route':route,'layers':self.layers if route=='A' else None,'entries':arr},separators=(',',':'),ensure_ascii=False).encode()
        return len(zlib.compress(raw,6)) + 12

    def delta_bytes(self, route, base):
        assert len(self.concepts)==len(base.concepts)+1
        c=self.concepts[-1]
        d={'from':base.version,'to':self.version,'route':route,'base_size':len(base.concepts),'id':c.sid,'name':c.name,'meaning':c.meaning}
        if route=='A':d.update(layer=c.layer,slot=c.slot)
        raw=json.dumps(d,separators=(',',':'),ensure_ascii=False).encode()
        return len(zlib.compress(raw,6))+12


# Actual ICFP 2020 Modulation for a minimal (version, stable_id) bridge record.
@dataclass(frozen=True)
class Pair:
    first: object
    rest: object

class Nil: pass
NIL=Nil()

def modulation(x):
    if x is NIL: return '00'
    if isinstance(x,Pair): return '11'+modulation(x.first)+modulation(x.rest)
    if type(x) is int:
        n=(abs(x).bit_length()+3)//4
        return ('01' if x>=0 else '10')+'1'*n+'0'+(format(abs(x),f'0{4*n}b') if n else '')
    raise TypeError(type(x))

def demodulation(bits):
    r=Reader(bits)
    def read(depth=0):
        if depth>32:raise ValueError('nesting')
        tag=r.take(2)
        if tag=='00':return NIL
        if tag=='11':return Pair(read(depth+1),read(depth+1))
        if tag not in ('01','10'):raise ValueError('bad tag')
        n=0
        while r.take(1)=='1':
            n+=1
            if n>128:raise ValueError('integer too large')
        v=int(r.take(n*4),2) if n else 0
        if (tag=='10' and v==0) or (n and v < 1<<(4*(n-1))):raise ValueError('noncanonical')
        return v if tag=='01' else -v
    x=read();r.done();return x

def bridge_packet(version,stable_id):
    return modulation(Pair(version,Pair(stable_id,NIL)))

def bridge_resolve(bits,registry):
    data=demodulation(bits)
    if not isinstance(data,Pair) or not isinstance(data.rest,Pair) or data.rest.rest is not NIL:
        raise ValueError('bad bridge packet')
    version,sid=data.first,data.rest.first
    if version not in registry or sid not in registry[version].by_id:
        raise ValueError('unknown version or concept')
    return registry[version].by_id[sid].meaning


def experiment(n,layers,route,hot=100,other=1000):
    old=Lexicon(n,layers,1)
    new=Lexicon(n,layers,2,True)
    # Deterministic and evenly spread existing traffic, excluding roots only if appropriate.
    rng=random.Random(170000+n*10+layers)
    other_ids=[rng.randrange(n) for _ in range(other)]
    before=[(0,1)]*hot+other_ids
    after=[n]*hot+other_ids
    old_bits=len(old.encode(before,route))
    new_bits=len(new.encode(after,route))
    delta=new.delta_bytes(route,old)
    # First use of promotion: all receivers need the delta; marginal cost must include it.
    saving=old_bits-new_bits
    total=saving-delta*8
    # Stable semantic ID of pre-existing words cannot change after adding a lexicographically earlier name.
    assert all(old.by_id[i].meaning==new.by_id[i].meaning for i in range(n))
    assert new.meaning(n)==old.meaning((0,1))
    assert old.decode(old.encode(before,route),route)==before
    assert new.decode(new.encode(after,route),route)==after
    assert old.decode(old.encode(before,route),route)==before  # rollback/replay
    try:
        old.decode(new.encode(after,route),route)
    except ValueError:
        pass
    else:
        raise AssertionError('new frame must be rejected by old version')
    # Dynamic gamma layer prefix, including 4th/8th layers, without fixed 2-bit assumption.
    last_layer=layers
    last_sid=next(c.sid for c in old.concepts if c.layer==last_layer)
    assert old.decode(old.encode([last_sid],route),route)==[last_sid]
    return dict(n=n,layers=layers,route=route,hot=hot,other=other,old_width=old.bwidth if route=='B' else old.awidth[2],new_width=new.bwidth if route=='B' else new.awidth[2],old_bits=old_bits,new_bits=new_bits,payload_saving=saving,delta_bytes=delta,net_saving=total,full_old_bytes=old.snapshot_bytes(route),full_new_bytes=new.snapshot_bytes(route))


def tests():
    for n in (64,256,1024):
        for layers in (4,8):
            for route in ('A','B'):
                old=Lexicon(n,layers,1); new=Lexicon(n,layers,2,True)
                assert old.bwidth+1==new.bwidth
                assert old.awidth[2]+1==new.awidth[2]
                assert old.awidth[1]==new.awidth[1]
                assert len({c.sid for c in new.concepts})==n+1
                assert len({(c.layer,c.slot) for c in new.concepts})==n+1
                assert sorted(new.concepts,key=lambda c:c.name)[0].sid==n
                # Full vocabulary roundtrip in each version, including 4th/8th layer.
                for lex in (old,new):
                    seq=list(lex.by_id)
                    for j in range(0,len(seq),47):
                        part=seq[j:j+47]+[(0,1)]
                        bits=lex.encode(part,route)
                        assert lex.decode(bits,route)==part
                        assert lex.decode(bits,route)==part
                        for corrupt in (bits[:-1],bits+'1'):
                            try: lex.decode(corrupt,route)
                            except ValueError: pass
                            else: raise AssertionError('bad frame accepted')
                for hot in (10,100,500,2000):
                    experiment(n,layers,route,hot,1000)
    # A bridge that sorts by names changes almost every ID on promotion; stable ID doesn't.
    n=64
    old=Lexicon(n,4,1);new=Lexicon(n,4,2,True)
    sorted_old={c.sid:i for i,c in enumerate(sorted(old.concepts,key=lambda c:c.name))}
    sorted_new={c.sid:i for i,c in enumerate(sorted(new.concepts,key=lambda c:c.name))}
    changed=sum(sorted_old[i]!=sorted_new[i] for i in range(n))
    assert changed==n
    # Malicious-looking new alias cannot change the meaning of an existing ID.
    assert new.by_id[0].meaning==old.by_id[0].meaning
    registry={1:old,2:new}
    for sid in range(n):
        assert bridge_resolve(bridge_packet(1,sid),registry)==bridge_resolve(bridge_packet(2,sid),registry)
    assert bridge_resolve(bridge_packet(2,n),registry)==old.meaning((0,1))
    try:bridge_resolve(bridge_packet(1,n),registry)
    except ValueError:pass
    else:raise AssertionError('new concept decoded in old dictionary')
    for v in (1,2):
        assert demodulation(modulation(Pair(v,Pair(1,NIL))))==Pair(v,Pair(1,NIL))
    return changed

if __name__=='__main__':
    changed=tests()
    print('PASS: 3 boundaries × 2 layer counts × 2 routes × 2 versions, all vocabulary roundtrips, corrupt-frame rejects, 48 workload runs, rollback and stable IDs.')
    print('name-sorted bridge IDs shifted:',changed,'/64; monotonic stable IDs shifted: 0/64')
    print('base 64/256/1024, 4/8 layers, hot=100 and 1000 other references:')
    for n in (64,256,1024):
        for layers in (4,8):
            for route in ('A','B'):
                d=experiment(n,layers,route)
                print(n,layers,route,'width',d['old_width'],'->',d['new_width'],'payload',d['payload_saving'],'delta',d['delta_bytes'],'net',d['net_saving'])
    print('Promotion crossover hot count (1000 other references, including delta):')
    for n in (64,256,1024):
        for layers in (4,8):
            for route in ('A','B'):
                best=next((h for h in range(1,2001) if experiment(n,layers,route,h,1000)['net_saving']>0),None)
                print(n,layers,route,best)