#!/usr/bin/env python3
"""SL-0.10: symbolic recursion groups, immutable roots and replay policy.
No SLE bit encoding, network, or ICFP interpreter is implemented.
"""
import hashlib, json
from dataclasses import dataclass

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()

class SemanticError(Exception):
    pass

@dataclass(frozen=True)
class Group:
    rev: int
    template: str = 'mutual_parity'
    def spec(self):
        # All intra-group references use stable local names, not recursive hashes.
        return {'members': ['even', 'odd', 'revision'],
                'defs': {'even': 'n==0 ? rev%2==0 : odd(n-1)',
                         'odd': 'n==0 ? rev%2==1 : even(n-1)',
                         'revision': 'rev'},
                'rev': self.rev, 'template': self.template}
    @property
    def id(self): return digest(self.spec())

def validate_group(group):
    if group.template != 'mutual_parity':
        raise SemanticError('unsupported / non-decreasing recursive group')
    if group.rev < 0:
        raise SemanticError('invalid revision')
    if len(group.spec()['members']) != len(set(group.spec()['members'])):
        raise SemanticError('duplicate member')
    return group.id

def eval_group(group, fn, n, fuel=100):
    if fn == 'revision': return group.rev
    if fn not in ('even','odd') or not isinstance(n,int) or n < 0:
        raise SemanticError('unknown function or invalid argument')
    if fuel <= 0: raise SemanticError('fuel exhausted')
    if n == 0: return (group.rev % 2 == 0) if fn == 'even' else (group.rev % 2 == 1)
    return eval_group(group, 'odd' if fn == 'even' else 'even', n-1, fuel-1)

@dataclass(frozen=True)
class Root:
    group_id: str
    mapping_id: str
    def id(self): return digest({'S':self.group_id,'M':self.mapping_id})

def replay(root, groups, mappings, n):
    # No implicit fallback to latest root or mapping.
    if root.mapping_id not in mappings: raise SemanticError('missing original M')
    if root.group_id not in groups: raise SemanticError('missing original S')
    return eval_group(groups[root.group_id], 'even', n)

# Tests: stable identity of mutually recursive SCC without circular hashing.
groups = {g.id:g for g in (Group(i) for i in range(61))}
assert len(groups) == 61
assert Group(3).id == Group(3).id
for i in range(61):
    g = Group(i)
    validate_group(g)
    for n in range(41):
        assert eval_group(g,'even',n) == ((i+n)%2==0)
        assert eval_group(g,'odd',n) == ((i+n)%2==1)
assert eval_group(Group(7),'revision',0) == 7
for bad in (Group(1,'aliases_only'), Group(2,'non_decreasing')):
    try: validate_group(bad); raise AssertionError('bad group accepted')
    except SemanticError: pass
try: eval_group(Group(0),'even',20,fuel=5); raise AssertionError('fuel check failed')
except SemanticError: pass

# A has local-layer mapping upgrades; B has global word-length upgrades.
# These are symbolic mapping identifiers only, not bitstream simulations.
roots = {}
mappings = {}
for route in ('A','B'):
    roots[route] = []
    for i in range(61):
        epoch = min(i // 20, 2)
        spec = ({'route':'A','changed_layer':1,'epoch':epoch}
                if route=='A' else {'route':'B','global_N':7+epoch})
        mid = digest(spec)
        mappings[mid] = spec
        roots[route].append(Root(Group(i).id,mid))

for route in roots:
    for i,r in enumerate(roots[route]):
        assert replay(r,groups,mappings,37) == ((i+37)%2==0)
        assert len({r.id() for r in roots[route]}) == 61

# A missing old S or M is a hard error, even when the latest versions exist.
for route in roots:
    old = roots[route][2]
    for gstore,mstore in (({k:v for k,v in groups.items() if k!=old.group_id},mappings),
                         (groups,{k:v for k,v in mappings.items() if k!=old.mapping_id})):
        try: replay(old,gstore,mstore,7); raise AssertionError('missing dependency accepted')
        except SemanticError: pass

# An invalid update must not mutate the active immutable root.
active = roots['A'][60]
try:
    validate_group(Group(61,'aliases_only'))
    active = Root(Group(61).id,active.mapping_id)
except SemanticError:
    pass
assert active == roots['A'][60]

pinned = {2,17,39,60}  # four hamsters with explicit historical replay promises
policies = {
    'all': set(range(61)),
    'pinned_only': pinned,
    'checkpoint_10_plus_pinned': set(range(0,61,10)) | pinned,
}
summary = {}
for route in roots:
    summary[route] = {}
    for name,indices in policies.items():
        kept_roots = [roots[route][i] for i in sorted(indices)]
        kept_groups = {r.group_id:groups[r.group_id] for r in kept_roots}
        kept_mappings = {r.mapping_id:mappings[r.mapping_id] for r in kept_roots}
        success = 0
        for i,r in enumerate(roots[route]):
            try:
                if i not in indices: raise SemanticError('root not retained')
                replay(r,kept_groups,kept_mappings,9)
                success += 1
            except SemanticError: pass
        assert success == len(indices)
        # Offline, a root alone is insufficient when an immutable dependency is evicted.
        evicted = {k:v for k,v in kept_groups.items() if v.rev%7 != 0}
        offline_success = 0
        for i in sorted(indices):
            try: replay(roots[route][i],evicted,kept_mappings,9); offline_success+=1
            except SemanticError: pass
        summary[route][name] = {
            'replayable_history_roots':success,'total_history_roots':61,
            'kept_semantic_groups':len(kept_groups),
            'kept_mapping_snapshots':len(kept_mappings),
            'offline_replay_after_example_eviction':offline_success,
        }

print(json.dumps({'status':'PASS','tested_groups':61,'recursion_cases':61*41*2,
                  'mapping_routes':['A','B'],'policy_summary':summary},ensure_ascii=False,indent=2))