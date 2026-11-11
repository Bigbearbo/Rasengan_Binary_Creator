#!/usr/bin/env python3
"""SL-0.18. Synthetic, reproducible comparison of dictionary promotion policies.

Reuses SL17 candidate A/B word lengths and actual zlib JSON delta sizes.
No official Spiral Language encoding, no new student, no natural language equivalence claim.
"""
import sys, random, statistics
from pathlib import Path
sys.path.insert(0, '/mnt/data/sl18_inputs')
from SL17_熱概念提升與跨階擴容驗證 import Lexicon, gamma

EPOCHS=24
RECEIVERS=6
OLD_TOKENS=100
THRESHOLD=100
HISTORY=3


def receiver_online(r,t):
    # One frequent receiver and one infrequent receiver temporarily disappear.
    return not ((r==0 and 8<=t<=15) or (r==3 and 4<=t<=15))


def new_uses(pattern,r,t):
    if pattern=='stable': return 60 if r in (0,1) else 2
    if pattern=='burst': return 80 if t==0 and r in (0,1) else 0
    if pattern=='drift':
        if r==0: return 70 if t<5 else 1
        if r==1: return 2 if t<5 else 70
        return 1
    raise ValueError(pattern)


def workload(n,layers,route,pattern):
    old=Lexicon(n,layers,1); new=Lexicon(n,layers,2,True)
    rng=random.Random(180000+n*7+layers*23+(route=='B')*17+{'stable':0,'burst':1,'drift':2}[pattern]*101)
    # Skewed Zipf-like old-vocabulary use, not uniform or a real-world trace.
    weights=[1/(i+1)**0.9 for i in range(n)]
    old_word={i:1+len(old.word(i,route)) for i in range(n)}
    new_word={i:1+len(new.word(i,route)) for i in range(n)}
    old_pair=1+len(old.word(0,route))+len(old.word(1,route))
    new_direct=1+len(new.word(n,route))
    update_bits=new.delta_bytes(route,old)*8
    periods=[]
    for t in range(EPOCHS):
        row=[]
        for r in range(RECEIVERS):
            if not receiver_online(r,t):
                row.append(None); continue
            ids=rng.choices(range(n),weights=weights,k=OLD_TOKENS)
            k=new_uses(pattern,r,t)
            before=sum(old_word[i] for i in ids)+k*old_pair+len(gamma(old.version))+len(gamma(OLD_TOKENS+k+1))
            after=sum(new_word[i] for i in ids)+k*new_direct+len(gamma(new.version))+len(gamma(OLD_TOKENS+k+1))
            row.append((before,after,k))
        periods.append(row)
    # Cross-check length accounting against actual candidate encoder, incl. framing.
    sample=[0,1,2,3,(0,1)]
    before=old.encode(sample,route)
    after=new.encode([0,1,2,3,n],route)
    assert old.decode(before,route)==sample
    assert new.decode(after,route)==[0,1,2,3,n]
    assert len(before)-len(gamma(old.version))-len(gamma(len(sample)+1))==sum(old_word[i] for i in (0,1,2,3))+old_pair
    assert len(after)-len(gamma(new.version))-len(gamma(len(sample)+1))==sum(new_word[i] for i in (0,1,2,3))+new_direct
    assert new.meaning(n)==old.meaning((0,1))
    # Old receiver can always be sent the composed expression; new word must be rejected.
    try:old.decode(new.encode([n],route),route)
    except ValueError:pass
    else:raise AssertionError('missing-version rejection failed')
    return periods,update_bits,old_pair,new_direct


def baseline(rows):
    return sum(x[0] for row in rows for x in row if x is not None)


def simulate(rows,delta,policy):
    upgraded=[False]*RECEIVERS
    global_activated=False
    cum_hot=0
    hist=[[] for _ in range(RECEIVERS)]
    total=0; upgrades=[]
    for t,row in enumerate(rows):
        active=[r for r,x in enumerate(row) if x is not None]
        if policy=='fixed_global' and not global_activated and cum_hot>=THRESHOLD:
            global_activated=True
        if policy=='forecast_global' and not global_activated and t>0:
            forecast=0
            for r in range(RECEIVERS):
                h=hist[r][-HISTORY:]
                # Unknown future availability approximated from observations.
                freq=sum(x is not None for x in h)/len(h)
                gain=sum((x[0]-x[1]) for x in h if x is not None)/max(1,sum(x is not None for x in h))
                forecast+=freq*gain*(EPOCHS-t)
            if forecast>RECEIVERS*delta:global_activated=True
        for r in active:
            x=row[r]
            if policy in ('fixed_global','forecast_global') and global_activated and not upgraded[r]:
                upgraded[r]=True;total+=delta;upgrades.append((t,r))
            if policy in ('forecast_local','confirmed_local') and not upgraded[r] and t>0:
                h=hist[r][-HISTORY:]
                gain=sum((v[0]-v[1]) for v in h if v is not None)/max(1,sum(v is not None for v in h))
                freq=sum(v is not None for v in h)/len(h)
                confirmed=(policy!='confirmed_local' or (len(h)>=2 and h[-1] is not None and h[-2] is not None and h[-1][0]>h[-1][1] and h[-2][0]>h[-2][1]))
                if confirmed and gain*freq*(EPOCHS-t)>delta:
                    upgraded[r]=True;total+=delta;upgrades.append((t,r))
            total+=x[1] if upgraded[r] else x[0]
        for r in range(RECEIVERS):hist[r].append(row[r])
        cum_hot+=sum(x[2] for x in row if x is not None)
    return total,upgrades


def oracle(rows,delta,local=True):
    """Ex post lower bound with full future knowledge and one irreversible upgrade."""
    if local:
        total=0;choices=[]
        for r in range(RECEIVERS):
            candidates=[]
            for cutoff in range(len(rows)+1):
                cost=0;paid=False
                for t,row in enumerate(rows):
                    x=row[r]
                    if x is None:continue
                    if t>=cutoff:
                        if not paid:cost+=delta;paid=True
                        cost+=x[1]
                    else:cost+=x[0]
                candidates.append(cost)
            best=min(range(len(candidates)),key=candidates.__getitem__)
            total+=candidates[best];choices.append(best)
        return total,choices
    costs=[]
    for cutoff in range(len(rows)+1):
        paid=[False]*RECEIVERS;cost=0
        for t,row in enumerate(rows):
            for r,x in enumerate(row):
                if x is None:continue
                if t>=cutoff:
                    if not paid[r]:cost+=delta;paid[r]=True
                    cost+=x[1]
                else:cost+=x[0]
        costs.append(cost)
    best=min(range(len(costs)),key=costs.__getitem__)
    return costs[best],best


def run():
    results=[]
    for n in (64,256,1024):
      for layers in (4,8):
       for route in ('A','B'):
        for pattern in ('stable','burst','drift'):
            rows,delta,old_pair,new_direct=workload(n,layers,route,pattern)
            base=baseline(rows)
            policy={k:simulate(rows,delta,k) for k in ('fixed_global','forecast_global','forecast_local','confirmed_local')}
            local_oracle,local_choices=oracle(rows,delta,True)
            global_oracle,global_choice=oracle(rows,delta,False)
            assert local_oracle<=global_oracle<=base
            assert all(local_oracle<=v[0] for v in policy.values())
            results.append(dict(n=n,layers=layers,route=route,pattern=pattern,base=base,delta=delta,
                pair_bits=old_pair,direct_bits=new_direct,
                fixed=policy['fixed_global'][0],global_predict=policy['forecast_global'][0],
                local_predict=policy['forecast_local'][0],confirmed_local=policy['confirmed_local'][0],
                fixed_up=policy['fixed_global'][1],global_up=policy['forecast_global'][1],local_up=policy['forecast_local'][1],confirmed_up=policy['confirmed_local'][1],
                oracle_global=global_oracle,oracle_local=local_oracle,oracle_global_at=global_choice,oracle_local_at=local_choices))
    assert len(results)==36
    print('PASS 36 scenarios: A/B × 4/8 layers × 64/256/1024 vocab × stable/burst/drift; actual candidate 01 roundtrips, old-version rejection, 6 receivers, offline windows, oracle lower bounds.')
    print('Costs below are total bits (candidate token payload + per-epoch version/count prefix + per-receiver zlib6 JSON delta; no network frame/CPU/retransmission). Lower is better.')
    for n in (64,256,1024):
      for layers in (4,8):
       for route in ('A','B'):
        for pattern in ('stable','burst','drift'):
          d=next(x for x in results if x['n']==n and x['layers']==layers and x['route']==route and x['pattern']==pattern)
          print(f"{n:4} {layers} {route} {pattern:6} | no={d['base']:6} fixed={d['fixed']:6} globalPred={d['global_predict']:6} localPred={d['local_predict']:6} confirmed={d['confirmed_local']:6} oracleGlobal={d['oracle_global']:6} oracleLocal={d['oracle_local']:6} | sync={d['delta']} | upgraded={len(d['fixed_up'])}/{len(d['global_up'])}/{len(d['local_up'])}/{len(d['confirmed_up'])}")
    print('SUMMARIES: total policy savings vs no promotion across all scenarios')
    for name in ('fixed','global_predict','local_predict','confirmed_local','oracle_global','oracle_local'):
      print(name, sum(x['base']-x[name] for x in results))
    print('DETAILED 64/4/B stable:',next(x for x in results if x['n']==64 and x['layers']==4 and x['route']=='B' and x['pattern']=='stable'))
    print('DETAILED 64/4/A burst:',next(x for x in results if x['n']==64 and x['layers']==4 and x['route']=='A' and x['pattern']=='burst'))
    return results

if __name__=='__main__':run()