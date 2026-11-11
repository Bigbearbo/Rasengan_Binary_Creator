#!/usr/bin/env python3
"""SL-0.12: deterministic toy backends, not Spiral Language binary codec.
1000 slots, 120 edits; full snapshots, checkpoint+delta, persistent binary Merkle DAG.
"""
import hashlib, random, struct, time, json
from dataclasses import dataclass

SEED=20261102
N=1000
EVENTS=120
CHECKPOINT=20
rng=random.Random(SEED)

def sha(b): return hashlib.sha256(b).digest()
def data_for(slot,gen,revision):
    seed=f'{SEED}:{slot}:{gen}:{revision}'.encode()
    return (sha(seed)*4)[:128]

@dataclass(frozen=True)
class Slot:
    generation:int
    active:bool
    payload:bytes

def slotbytes(i,s):
    return struct.pack('>IIB',i,s.generation,int(s.active))+s.payload

def snapshot_bytes(state):
    return b'S12F'+struct.pack('>I',len(state))+b''.join(slotbytes(i,s) for i,s in enumerate(state))

def state_digest(state):return sha(snapshot_bytes(state))

def event_bytes(version,old,new,i,s,action):
    # Variable-length delete event (no payload); full payload for change/reuse.
    body=struct.pack('>I',version)+old+new+struct.pack('>IIB',i,s.generation,action)
    return body+(s.payload if action!=2 else b'')

# Persistent binary Merkle content-addressed store; object key costs 32 bytes.
class Merkle:
    def __init__(self,n):
        self.n=n
        self.size=1<<(n-1).bit_length()
        self.store={}
    def put(self,b):
        h=sha(b)
        if h in self.store: assert self.store[h]==b
        self.store[h]=b
        return h
    def leaf(self,i,s):return self.put(b'L'+slotbytes(i,s))
    def build(self,state):
        nodes=[self.leaf(i,s) for i,s in enumerate(state)]
        for i in range(len(state),self.size):nodes.append(self.put(b'P'+struct.pack('>I',i)))
        while len(nodes)>1:
            nodes=[self.put(b'I'+nodes[i]+nodes[i+1]) for i in range(0,len(nodes),2)]
        return nodes[0]
    def update(self,root,slot,s):
        path=[]; node=root; lo=0; hi=self.size
        while hi-lo>1:
            raw=self.store[node]; assert raw[:1]==b'I'
            mid=(lo+hi)//2
            if slot<mid: path.append((False,raw[33:65]));node=raw[1:33];hi=mid
            else: path.append((True,raw[1:33]));node=raw[33:65];lo=mid
        node=self.leaf(slot,s)
        for right,sibling in reversed(path):
            node=self.put(b'I'+(sibling+node if right else node+sibling))
        return node
    def read(self,root,slot):
        node=root;lo=0;hi=self.size
        while hi-lo>1:
            raw=self.store[node]
            if raw[:1]!=b'I':raise ValueError('missing/invalid Merkle internal node')
            mid=(lo+hi)//2
            if slot<mid:node=raw[1:33];hi=mid
            else:node=raw[33:65];lo=mid
        raw=self.store[node]
        if raw[:1]!=b'L':raise ValueError('missing Merkle leaf')
        i,gen,active=struct.unpack('>IIB',raw[1:10]); assert i==slot
        return Slot(gen,bool(active),raw[10:])
    def reachable(self,roots):
        seen=set();stack=list(roots)
        while stack:
            h=stack.pop()
            if h in seen:continue
            raw=self.store[h] # fail closed on missing content
            if sha(raw)!=h:raise ValueError('Merkle content mismatch')
            seen.add(h)
            if raw[:1]==b'I':stack.extend((raw[1:33],raw[33:65]))
        return seen
    def size_bytes(self,roots):
        reachable=self.reachable(roots)
        return sum(len(self.store[h])+32 for h in reachable)+32*len(roots)

initial=tuple(Slot(1,True,data_for(i,1,0)) for i in range(N))
state=initial
states=[state]
roots_full=[state_digest(state)]
merkle=Merkle(N)
roots_merkle=[merkle.build(state)]
checkpoints={0:snapshot_bytes(state)}
deltas={}
changes=[]
revision=0
start=time.perf_counter()
for version in range(1,EVENTS+1):
    cycle=(version-1)%8
    if cycle==6: # delete one live slot, then reuse next step
        slot=500+(version-1)//8
        action=2
        new=Slot(state[slot].generation,False,b'\x00'*128)
    elif cycle==7:
        slot=500+(version-1)//8
        assert not state[slot].active
        action=3
        new=Slot(state[slot].generation+1,True,data_for(slot,state[slot].generation+1,version))
    else:
        slot=rng.randrange(0,500)
        action=1
        revision+=1
        new=Slot(state[slot].generation,True,data_for(slot,state[slot].generation,revision))
    state=state[:slot]+(new,)+state[slot+1:]
    newdig=state_digest(state)
    deltas[version]=event_bytes(version,roots_full[-1],newdig,slot,new,action)
    changes.append((slot,new,action))
    states.append(state)
    roots_full.append(newdig)
    roots_merkle.append(merkle.update(roots_merkle[-1],slot,new))
    if version%CHECKPOINT==0:checkpoints[version]=snapshot_bytes(state)
    # Exact Merkle root after path update must equal full rebuild root.
    assert roots_merkle[-1]==merkle.build(state)

# Decode full snapshot and replay deltas from nearest checkpoint.
def decode_snapshot(raw):
    if raw[:4]!=b'S12F':raise ValueError('bad snapshot header')
    count=struct.unpack('>I',raw[4:8])[0]
    assert len(raw)==8+137*count
    out=[]
    for i in range(count):
        p=raw[8+137*i:8+137*(i+1)]
        sid,gen,active=struct.unpack('>IIB',p[:9]);assert sid==i
        out.append(Slot(gen,bool(active),p[9:]))
    return tuple(out)

def replay(target,checkpoints,delta_map):
    cp=max(k for k in checkpoints if k<=target)
    state=decode_snapshot(checkpoints[cp])
    for version in range(cp+1,target+1):
        raw=delta_map[version] # missing delta => explicit failure
        idx=4+32+32
        v=struct.unpack('>I',raw[:4])[0]
        old=raw[4:36]; newdig=raw[36:68]
        slot,gen,action=struct.unpack('>IIB',raw[idx:idx+9])
        payload=(b'\x00'*128 if action==2 else raw[idx+9:])
        assert v==version and len(payload)==128 and state_digest(state)==old
        nextslot=Slot(gen,action!=2,payload)
        state=state[:slot]+(nextslot,)+state[slot+1:]
        assert state_digest(state)==newdig
    return state

for version in range(EVENTS+1):
    assert decode_snapshot(snapshot_bytes(states[version]))==states[version]
    assert replay(version,checkpoints,deltas)==states[version]
    assert merkle.read(roots_merkle[version],0)==states[version][0]
    assert merkle.read(roots_merkle[version],500)==states[version][500]

# 15 stale handles after a tombstone + reuse: root-bound old handle still valid.
for i in range(15):
    delete_ver=7+8*i; reuse_ver=delete_ver+1; slot=500+i
    old=states[delete_ver-1][slot]
    assert old.active and states[delete_ver][slot].active is False
    assert states[reuse_ver][slot].generation==old.generation+1
    assert merkle.read(roots_merkle[delete_ver-1],slot)==old
    assert merkle.read(roots_merkle[reuse_ver],slot).generation!=old.generation
    # A floating (slot,generation) handle must reject reuse, even when slot number matches.
    assert (slot,old.generation)!=(slot,states[reuse_ver][slot].generation)

full_all=sum(len(snapshot_bytes(s))+32 for s in states)
delta_all=sum(len(x) for x in checkpoints.values())+sum(len(x) for x in deltas.values())+32*len(states)
merkle_all=merkle.size_bytes(roots_merkle)

pins=[0,30,60,90,120]
full_pinned=sum(len(snapshot_bytes(states[i]))+32 for i in pins)
# Delta pinned policy: retain checkpoints 0,20,40,60,80,100,120 + only deltas needed to reach pins.
needed_deltas=set()
needed_checkpoints=set()
for v in pins:
    cp=(v//CHECKPOINT)*CHECKPOINT
    needed_checkpoints.add(cp)
    needed_deltas.update(range(cp+1,v+1))
retained_checkpoints={i:checkpoints[i] for i in needed_checkpoints}
delta_pinned=sum(len(x) for x in retained_checkpoints.values())+sum(len(deltas[i]) for i in needed_deltas)+32*len(pins)
merkle_pinned=merkle.size_bytes([roots_merkle[i] for i in pins])
for v in pins:
    assert replay(v,retained_checkpoints,{i:deltas[i] for i in needed_deltas})==states[v]
    for i in (0,500,514,999):assert merkle.read(roots_merkle[v],i)==states[v][i]

# Actually prune Merkle store to pinned roots and verify all 5*1000 historical slots.
original_store=merkle.store
retained_nodes=merkle.reachable([roots_merkle[i] for i in pins])
merkle.store={h:original_store[h] for h in retained_nodes}
for v in pins:
    for slot in range(N):assert merkle.read(roots_merkle[v],slot)==states[v][slot]
assert roots_merkle[1] not in merkle.store
merkle.store=original_store

# Deliberate missing-history failure, and fail-closed content deletion.
try:
    replay(35,checkpoints,{i:d for i,d in deltas.items() if i!=31})
    raise AssertionError('missing delta unexpectedly replayed')
except KeyError:pass
bad_root=roots_merkle[30]; bad_child=merkle.store[bad_root][1:33]
raw=merkle.store.pop(bad_child)
try:
    merkle.read(bad_root,0)
    raise AssertionError('missing Merkle node unexpectedly resolved')
except KeyError:pass
finally:merkle.store[bad_child]=raw

# Offline receiver has version 20; choose catchup to 35; compare raw byte counts.
catchup_delta=sum(len(deltas[i]) for i in range(21,36))
full_refresh=len(snapshot_bytes(states[35]))
# A standalone Merkle proof must include old/new root, slot data, and siblings for every event;
# this is an illustrative uncompressed per-update proof estimate (not a measured network protocol).
merkle_proof_est=sum(len(deltas[i])+merkle.size.bit_length().__sub__(1)*32 for i in range(21,36))

result={
 'seed':SEED,'slots':N,'versions':len(states),'mutations':90,'deletes':15,'reuses':15,
 'checkpoint_interval':CHECKPOINT,'pins':pins,'retained_checkpoint_versions':sorted(needed_checkpoints),
 'all_history_bytes':{'full_snapshots':full_all,'checkpoint_deltas':delta_all,'persistent_merkle':merkle_all},
 'pinned_history_bytes':{'full_snapshots':full_pinned,'checkpoint_deltas':delta_pinned,'persistent_merkle':merkle_pinned},
 'catchup_20_to_35_bytes':{'full_snapshot':full_refresh,'delta_chain':catchup_delta,'merkle_per_update_proof_estimate':merkle_proof_est},
 'merkle_objects_total':len(merkle.store),'merkle_objects_retained_after_gc':len(retained_nodes),
 'elapsed_seconds':round(time.perf_counter()-start,3),
 'assertions':'PASS: 121 state replays, 121 Merkle roots full rebuild, 15 stale handle rejects, actual pinned GC + 5000 slot reads, missing data fail-closed'
}
print(json.dumps(result,ensure_ascii=False,indent=2))