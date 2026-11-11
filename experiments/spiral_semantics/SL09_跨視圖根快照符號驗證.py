"""SL-0.9 symbolic semantic snapshot checks. Not an SLE bit decoder."""
from dataclasses import dataclass
import hashlib, json, random

@dataclass(frozen=True)
class Node:
    name: str
    revision: int
    deps: tuple  # (logical-name, node-id) pairs
    body: str

def digest(x):
    return hashlib.sha256(json.dumps(x, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]

def store_node(store, node):
    ident = digest((node.name, node.revision, node.deps, node.body))
    store[ident] = node
    return ident

def closure(root, store, enforce_single=True):
    """Root maps logical name to pinned immutable node-id; detect conflicting binds."""
    seen=set(); stack=list(root.values()); bound={}
    while stack:
        ident=stack.pop()
        if ident in seen: continue
        if ident not in store: raise LookupError('missing pinned definition: '+ident)
        n=store[ident]
        if enforce_single and n.name in bound and bound[n.name]!=ident:
            raise ValueError('conflicting revisions: '+n.name)
        bound[n.name]=ident
        seen.add(ident)
        for label, dep in n.deps:
            if dep not in store: raise LookupError('missing pinned dependency: '+dep)
            if store[dep].name != label: raise ValueError('dependency label mismatch')
            stack.append(dep)
    for label, ident in root.items():
        if store[ident].name != label: raise ValueError('root label mismatch')
    return seen

rng=random.Random(20261102)
store={}; names=[f'C{i}' for i in range(12)]
# Stable DAG: every C_i depends on zero or more earlier concepts.
edges={name: tuple(rng.sample(names[:i], k=rng.randrange(min(3,i)+1))) for i,name in enumerate(names)}
roots=[]; root={}; rev={n:0 for n in names}
for n in names:
    root[n]=store_node(store, Node(n,0,tuple((d,root[d]) for d in edges[n]),f'v0:{n}'))
roots.append(root.copy())
for t in range(200):
    target=rng.choice(names); rev[target]+=1
    # Rebuild target and all transitive dependents, each with immutable pinned deps.
    affected={target}
    for n in names:
        if any(d in affected for d in edges[n]): affected.add(n)
    nxt=root.copy()
    for n in names:
        if n in affected:
            if n!=target: rev[n]+=1
            nxt[n]=store_node(store,Node(n,rev[n],tuple((d,nxt[d]) for d in edges[n]),f'v{rev[n]}:{n}'))
    root=nxt; roots.append(root.copy())
    assert len(closure(root,store))==12

# Mixed-epoch references must be rejected if they collide on a logical concept.
a=roots[0]; b=roots[-1]
# Choose a node that depends on C0 from any snapshot, if none force a minimal example.
j1=store_node(store,Node('JOIN',1,tuple(),'OR'))
j2=store_node(store,Node('JOIN',2,tuple(),'XOR'))
f1=store_node(store,Node('F',1,(('JOIN',j1),),'F(x)=JOIN(x,1)'))
g2=store_node(store,Node('G',2,(('JOIN',j2),),'G(x)=JOIN(x,1)'))
assert len(closure({'F':f1,'JOIN':j1},store))==2
try:
    closure({'F':f1,'G':g2},store)
    raise AssertionError('mixed snapshot was silently accepted')
except ValueError as e:
    assert 'conflicting revisions' in str(e)
# A deliberate side-by-side comparison is expressible by explicit namespaces.
old=store_node(store,Node('history/JOIN',1,tuple(),'OR'))
new=store_node(store,Node('current/JOIN',2,tuple(),'XOR'))
assert len(closure({'history/JOIN':old,'current/JOIN':new},store))==2
# Missing pinned old definitions must not silently fall back to new ones.
partial=store.copy(); del partial[j1]
try:
    closure({'F':f1},partial)
    raise AssertionError('missing old JOIN was silently substituted')
except LookupError: pass
# Keep two historical roots + latest; GC must retain transitive closure of all pinned roots.
pinned=[roots[0],roots[75],roots[-1],{'F':f1,'JOIN':j1}]
retained=set().union(*(closure(r,store) for r in pinned))
gc={k:v for k,v in store.items() if k in retained}
for r in pinned: assert closure(r,gc)==closure(r,store)
# An unpinned old root may fail after GC; this is expected, not a bug.
unpinned=[r for r in roots if any(v not in gc for v in r.values())]
assert unpinned
# Mapping snapshot is a separate artifact: changing fixed-width N doesn't change node identity.
M7={'N':7,'JOIN':'1010100'}; M8={'N':8,'JOIN':'01010100'}
assert digest(M7)!=digest(M8) and j1 in store
assert len(M7['JOIN'])==M7['N'] and len(M8['JOIN'])==M8['N']
print(json.dumps({'randomized_updates':200,'valid_snapshots':len(roots),'concepts_per_snapshot':12,'stored_immutable_nodes':len(store),'retained_nodes':len(gc),'garbage_collectable_nodes':len(store)-len(gc),'unpinned_old_roots_lost':len(unpinned),'tests':['snapshot_closure','mixed_epoch_reject','explicit_namespace_compare','missing_dependency_fail','pinned_gc_replay','S_M_separation'],'status':'PASS','scope':'symbolic, no real SLE/ICFP parser or bit cost'},ensure_ascii=False,indent=2))