#!/usr/bin/env python3
"""SL-0.11: symbolic SCC / immutable group root / Merkle indexed slots.
Not a Spiral Language bitstream, ICFP implementation, or measured network benchmark.
"""
import hashlib, json, math

def h(data): return hashlib.sha256(data).digest()
def encode(x): return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
def leaf_hash(v): return h(b'L' + encode(v))
def parent_hash(a,b): return h(b'I' + a + b)
def root_hash(n, inner): return h(b'G' + n.to_bytes(8,'big') + inner)

def build(leaves):
    n=len(leaves)
    p=1 << (n-1).bit_length()
    layer=[leaf_hash(x) for x in leaves]+[h(b'PAD'+i.to_bytes(8,'big')) for i in range(n,p)]
    levels=[layer]
    while len(layer)>1:
        layer=[parent_hash(layer[i],layer[i+1]) for i in range(0,len(layer),2)]
        levels.append(layer)
    return levels,root_hash(n,levels[-1][0])

def update(levels,old_n,index,new_leaf):
    out=[row.copy() for row in levels]
    out[0][index]=leaf_hash(new_leaf)
    k=index
    for height in range(1,len(out)):
        k//=2
        out[height][k]=parent_hash(out[height-1][2*k],out[height-1][2*k+1])
    return out,root_hash(old_n,out[-1][0])

def verify(expected,leaves):
    _,actual=build(leaves)
    if expected!=actual: raise ValueError('root mismatch / mixed version')
    return True

def eval_root(expected_root, leaves, start):
    # Minimal symbolic ring: member 0 is the base case; all others forward.
    verify(expected_root,leaves)
    pos=start
    for _ in range(len(leaves)+1):
        if pos==0: return 0 if leaves[0]['body']=='v1' else 1
        pos=leaves[pos]['ref']
    raise ValueError('fuel exhausted / unresolved cycle')

def edges(n,kind):
    if kind=='ring': return {i:[(i+1)%n] for i in range(n)}
    if kind=='chain': return {i:([i-1] if i else []) for i in range(n)}
    if kind=='disjoint_10_cycles':
        return {i:[i+1 if i+1<n and (i+1)//10==i//10 else (i//10)*10] for i in range(n)}
    raise ValueError(kind)

def components(graph):
    # Iterative Kosaraju: no Python recursion-limit dependency for 1000+ members.
    seen=set(); order=[]
    for start in graph:
        if start in seen: continue
        seen.add(start); stack=[(start,iter(graph[start]))]
        while stack:
            v,it=stack[-1]
            try:
                w=next(it)
                if w not in seen:
                    seen.add(w); stack.append((w,iter(graph[w])))
            except StopIteration:
                order.append(v);stack.pop()
    reverse={i:[] for i in graph}
    for i,targets in graph.items():
        for j in targets: reverse[j].append(i)
    seen=set(); comps=[]
    for start in reversed(order):
        if start in seen: continue
        stack=[start];seen.add(start);c=[]
        while stack:
            v=stack.pop();c.append(v)
            for w in reverse[v]:
                if w not in seen: seen.add(w);stack.append(w)
        comps.append(c)
    return comps

def reverse_affected(graph,changed):
    rev={i:[] for i in graph}
    for i,ds in graph.items():
        for j in ds: rev[j].append(i)
    seen={changed};todo=[changed]
    while todo:
        for w in rev[todo.pop()]:
            if w not in seen: seen.add(w);todo.append(w)
    return len(seen)

summary=[]
for n in (1,10,100,1000):
    graph=edges(n,'ring')
    leaves=[{'slot':i,'ref':graph[i][0],'body':'v1','data':'x'*100} for i in range(n)]
    levels,r0=build(leaves)
    assert verify(r0,leaves)
    new_leaves=[x.copy() for x in leaves]
    new_leaves[0]['body']='v2'
    next_levels,r1=update(levels,n,0,new_leaves[0])
    assert r0!=r1 and next_levels!=levels
    assert r1==build(new_leaves)[1]
    assert verify(r0,leaves) and verify(r1,new_leaves)
    assert eval_root(r0,leaves,n-1)==0 and eval_root(r1,new_leaves,n-1)==1
    # Other update positions must preserve old snapshots and match a full rebuild.
    for j in sorted({0, n//2, n-1}):
        variant=[v.copy() for v in leaves]
        variant[j]['body']='alternate'
        path_tree, path_root=update(levels,n,j,variant[j])
        assert path_root==build(variant)[1]
        assert levels[-1][0]==build(leaves)[0][-1][0]
    try: verify(r0,new_leaves); raise AssertionError('mixed group was accepted')
    except ValueError: pass
    try: verify(r1,leaves); raise AssertionError('stale group was accepted')
    except ValueError: pass
    # Symbolic A/B mapping upgrades are independent from semantic group root.
    for mapping in ({'A_layer':2,'epoch':0},{'A_layer':2,'epoch':1},
                    {'B_N':7},{'B_N':8}):
        assert verify(r0,leaves) and encode(mapping)
    depth=len(levels)-1
    idx_bytes=(n-1).bit_length()//8 + (1 if (n-1).bit_length()%8 else 0)
    summary.append({'members':n,'scc_ring_count':len(components(graph)),
                    'merkle_depth':depth,
                    'full_republish_bytes_assumed':128*n+32,
                    'cached_delta_bytes_both_assumed':128+64+idx_bytes,
                    'full_rehash_input_bytes_assumed':128*n,
                    'merkle_changed_path_hash_input_bytes_assumed':128+64*depth,
                    'merkle_cached_digest_bytes_upper_bound':32*(2*(1<<((n-1).bit_length()))-1),
                    'chain_scc_count':len(components(edges(n,'chain'))),
                    'chain_change_first_reverse_affected':reverse_affected(edges(n,'chain'),0),
                    'chain_change_last_reverse_affected':reverse_affected(edges(n,'chain'),n-1),
                    'ten_cycle_scc_count':len(components(edges(n,'disjoint_10_cycles'))),
                    'ten_cycle_change_first_reverse_affected':reverse_affected(edges(n,'disjoint_10_cycles'),0)})

print(json.dumps({'status':'PASS','scope':'symbolic only','cases':summary},ensure_ascii=False,indent=2))