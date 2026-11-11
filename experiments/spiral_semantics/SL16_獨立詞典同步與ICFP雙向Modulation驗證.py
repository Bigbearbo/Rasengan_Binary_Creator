#!/usr/bin/env python3
"""SL-0.16 experimental reproducible study, not official SLE/MLP.
A-only/B-only dictionary sync; synthetic compositional vocabulary; real ICFP-2020
Modulation of ints/cons/nil used as a DATA interchange envelope.
Requires SL14_語法作用域繼承與語義漂移檢查.py and
SL15_雙模式語法與詞典同步成本驗證.py in same directory.
Python 3 stdlib only. Not an ICFP evaluator or a cross-model learning test.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib, importlib.util, json, pathlib, random, sys

HERE=pathlib.Path(__file__).resolve().parent

def import_sibling(filename, modname):
    path=HERE/filename
    if not path.exists():
        path=HERE/'sl16_inputs'/filename
    if not path.exists():
        raise FileNotFoundError(filename)
    spec=importlib.util.spec_from_file_location(modname,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[modname]=module
    spec.loader.exec_module(module)
    return module

base=import_sibling('SL14_語法作用域繼承與語義漂移檢查.py','sl16_base')
sl15=import_sibling('SL15_雙模式語法與詞典同步成本驗證.py','sl16_sl15')
Word,ListNode,Call,Scope=base.Word,base.ListNode,base.Call,base.Scope

def canonical(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
def fp(x):return int.from_bytes(hashlib.sha256(canonical(x)).digest()[:4],'big')

def snapshot(d,m,scheme):
    common={'kind':'snapshot','scheme':scheme,'version':d.ver,'meanings':m.meanings}
    if scheme=='A':
        common.update(layers={str(k):list(v) for k,v in d.layers.items()},widths={str(k):v for k,v in d.widths.items()})
    elif scheme=='B':
        common.update(global_order=list(d.global_order),global_width=d.global_width,
                      allowed_layers=sorted(d.layers))
    else:raise ValueError('unknown route')
    common['route_fp']=fp(common)
    return common

def validate_snapshot(s):
    if s.get('kind')!='snapshot' or s.get('scheme') not in ('A','B'):raise ValueError('bad route')
    old=s.copy();digest=old.pop('route_fp',None)
    if fp(old)!=digest:raise ValueError('snapshot fingerprint')
    if s['scheme']=='A':
        layers={int(k):tuple(v) for k,v in s['layers'].items()}
        widths={int(k):v for k,v in s['widths'].items()}
        if set(layers)!=set(widths) or any(len(v)>2**widths[k] for k,v in layers.items()):raise ValueError('invalid A widths')
        names=[w for xs in layers.values() for w in xs]
    else:
        names=s['global_order']
        if len(names)>2**s['global_width']:raise ValueError('invalid B width')
        if len(set(s['allowed_layers']))!=len(s['allowed_layers']):raise ValueError('duplicate layer')
    if len(set(names))!=len(names) or set(names)!=set(s['meanings']):raise ValueError('incomplete dictionary/meaning map')
    return s

class Route:
    def __init__(self,s):
        self.s=validate_snapshot(s)
        self.scheme=s['scheme'];self.version=s['version'];self.meanings=s['meanings'];self.route_fp=s['route_fp']
        if self.scheme=='A':
            self.layers={int(k):tuple(v) for k,v in s['layers'].items()}
            self.widths={int(k):v for k,v in s['widths'].items()}
            self.loc={w:(k,i) for k,xs in self.layers.items() for i,w in enumerate(xs)}
            self.names=set(self.loc)
        else:
            self.global_order=tuple(s['global_order']);self.global_width=s['global_width']
            self.gloc={w:i for i,w in enumerate(self.global_order)}
            self.loc={w:(0,i) for i,w in enumerate(self.global_order)}  # SL14 membership check only, not an A layer map
            # Only the set of valid scopes is needed for B, NOT A's word/layer mapping.
            self.layers={k:() for k in s['allowed_layers']}
            self.names=set(self.global_order)
    def emit(self,ast):return base.emit_ast(ast,self,'A' if self.scheme=='A' else 'B')
    def parse(self,bits):
        x,end=base.parse_ast(bits,self,'A' if self.scheme=='A' else 'B')
        if end!=len(bits):raise ValueError('trailing data')
        return x

def delta(s0,s1):
    validate_snapshot(s0);validate_snapshot(s1)
    if s0['scheme']!=s1['scheme'] or s0['version']>=s1['version']:raise ValueError('bad upgrade')
    scheme=s0['scheme'];res={'kind':'delta','scheme':scheme,'from_version':s0['version'],
          'from_fp':s0['route_fp'],'to_version':s1['version'],'to_fp':s1['route_fp'],
          'meaning_changes':{k:v for k,v in s1['meanings'].items() if s0['meanings'].get(k)!=v}}
    if scheme=='A':
        if set(s0['layers'])!=set(s1['layers']):raise ValueError('layer set changed')
        res['append']={k:s1['layers'][k][len(s0['layers'][k]):] for k in s0['layers']}
        if any(s1['layers'][k][:len(s0['layers'][k])]!=s0['layers'][k] for k in s0['layers']):raise ValueError('nonappend A')
        res['widths']=s1['widths']
    else:
        if s1['global_order'][:len(s0['global_order'])]!=s0['global_order']:raise ValueError('nonappend B')
        res['append']=s1['global_order'][len(s0['global_order']):]
        res['global_width']=s1['global_width'];res['allowed_layers']=s1['allowed_layers']
    return res

def apply_delta(s,c):
    validate_snapshot(s)
    if c['kind']!='delta' or c['scheme']!=s['scheme'] or (c['from_version'],c['from_fp'])!=(s['version'],s['route_fp']):
        raise ValueError('wrong base')
    n={k:v for k,v in s.items() if k!='route_fp'}
    n['version']=c['to_version'];n['meanings']={**s['meanings'],**c['meaning_changes']}
    if s['scheme']=='A':
        n['layers']={k:s['layers'][k]+c['append'][k] for k in s['layers']}
        n['widths']=c['widths']
    else:
        n['global_order']=s['global_order']+c['append'];n['global_width']=c['global_width']
        n['allowed_layers']=c['allowed_layers']
    n['route_fp']=fp(n)
    validate_snapshot(n)
    if n['route_fp']!=c['to_fp']:raise ValueError('wrong target fingerprint')
    return n

@dataclass(frozen=True)
class Pair:
    first:object
    rest:object
class _Nil:pass
NIL=_Nil()

def plist(xs):
    ans=NIL
    for x in reversed(xs):ans=Pair(x,ans)
    return ans

def as_list(x,max_count=100000):
    out=[]
    while isinstance(x,Pair):
        if len(out)>=max_count:raise ValueError('list too long')
        out.append(x.first);x=x.rest
    if x is not NIL:raise ValueError('improper list')
    return out

def mod(x):
    if x is NIL:return '00'
    if isinstance(x,Pair):return '11'+mod(x.first)+mod(x.rest)
    if type(x) is int:
        n=(abs(x).bit_length()+3)//4
        if n>128:raise ValueError('integer too wide')
        return ('01' if x>=0 else '10')+'1'*n+'0'+(format(abs(x),f'0{4*n}b') if n else '')
    raise TypeError(type(x))

class Bits:
    def __init__(self,b):
        if set(b)-{'0','1'}:raise ValueError('nonbinary')
        self.b=b;self.i=0
    def take(self,n):
        if n<0 or self.i+n>len(self.b):raise ValueError('truncated')
        s=self.b[self.i:self.i+n];self.i+=n;return s

def dem_inner(r,depth=0):
    if depth>256:raise ValueError('nesting limit')
    tag=r.take(2)
    if tag=='00':return NIL
    if tag=='11':return Pair(dem_inner(r,depth+1),dem_inner(r,depth+1))
    n=0
    while r.take(1)=='1':
        n+=1
        if n>128:raise ValueError('integer length limit')
    magnitude=int(r.take(n*4),2) if n else 0
    if (n==0 and tag=='10') or (n>0 and magnitude<1<<(4*(n-1))):
        raise ValueError('noncanonical integer')
    return magnitude if tag=='01' else -magnitude

def dem(bits):
    r=Bits(bits);x=dem_inner(r)
    if r.i!=len(bits):raise ValueError('trailing bits')
    return x

def bridge_names(route):return tuple(sorted(route.names))
def bridge_fp(route):return fp({'names':bridge_names(route),'meanings':route.meanings})

def to_icfp_ast(ast,lookup):
    if isinstance(ast,Word):return plist([0,lookup[ast.concept]])
    if isinstance(ast,ListNode):return plist([1,plist([to_icfp_ast(x,lookup) for x in ast.children])])
    if isinstance(ast,Call):return plist([2,lookup[ast.operator.concept],plist([to_icfp_ast(x,lookup) for x in ast.args])])
    if isinstance(ast,Scope):return plist([3,ast.layer,to_icfp_ast(ast.body,lookup)])
    raise ValueError('bad AST')

def from_icfp_ast(data,names,allowed_layers,depth=0):
    if depth>64:raise ValueError('AST too deep')
    items=as_list(data)
    if not items or type(items[0]) is not int:raise ValueError('missing node tag')
    tag=items[0]
    def name(idx):
        if type(idx) is not int or not 0<=idx<len(names):raise ValueError('unknown word id')
        return Word(names[idx])
    if tag==0 and len(items)==2:return name(items[1])
    if tag==1 and len(items)==2:
        return ListNode(tuple(from_icfp_ast(x,names,allowed_layers,depth+1) for x in as_list(items[1])))
    if tag==2 and len(items)==3:
        return Call(name(items[1]),tuple(from_icfp_ast(x,names,allowed_layers,depth+1) for x in as_list(items[2])))
    if tag==3 and len(items)==3 and type(items[1]) is int and items[1] in allowed_layers:
        return Scope(items[1],from_icfp_ast(items[2],names,allowed_layers,depth+1))
    raise ValueError('bad node shape/tag/scope')

def to_icfp_packet(ast,route):
    names=bridge_names(route);lookup={n:i for i,n in enumerate(names)}
    return mod(plist([route.version,bridge_fp(route),to_icfp_ast(ast,lookup)]))

def from_icfp_packet(bits,registry):
    items=as_list(dem(bits))
    if len(items)!=3 or type(items[0]) is not int or type(items[1]) is not int:raise ValueError('bad packet')
    ver,signature,data=items
    if (ver,signature) not in registry:raise ValueError('missing exact bridge dictionary')
    route=registry[(ver,signature)]
    return from_icfp_ast(data,bridge_names(route),set(route.layers))

def must_fail(f):
    try:f()
    except (ValueError,KeyError,RecursionError):return
    raise AssertionError('expected rejection')

def compound_test(synonyms=1):
    # Artificial semantics, NOT natural-language learning. Each direct synonym
    # maps to the same ordered pair; composition is explicitly interpreted.
    roots=[f'根{i}' for i in range(16)]
    op='組合';l1=[op]+roots
    l2=[f'複合{i}_{alias}' for i in range(256) for alias in range(synonyms)]
    meaning={op:'operator:ordered-pair',**{w:f'root:{i}' for i,w in enumerate(roots)}}
    meaning.update({w:f'pair:{i//16}:{i%16}' for i in range(256) for w in [f'複合{i}_{a}' for a in range(synonyms)]})
    # For compositional variant, only roots and operator are needed.
    def snap(scheme,direct):
        a=l1;b=l2 if direct else []
        names=a+b
        obj={'kind':'snapshot','scheme':scheme,'version':1,
             'meanings':{k:meaning[k] for k in names}}
        if scheme=='A':obj.update(layers={'1':a,'2':b},widths={'1':max(1,(len(a)-1).bit_length()),
                    '2':max(1,(len(b)-1).bit_length())})
        else:obj.update(global_order=names,global_width=max(1,(len(names)-1).bit_length()),allowed_layers=[1,2])
        obj['route_fp']=fp(obj)
        return Route(obj),len(sl15.pack(obj))
    def meaning_value(node):
        if isinstance(node,Word):
            desc=meaning[node.concept]
            if desc.startswith('pair:'):
                _,a,b=desc.split(':');return (int(a),int(b))
            if desc.startswith('root:'):return int(desc.split(':')[1])
        if isinstance(node,Call) and node.operator.concept==op and len(node.args)==2:
            return tuple(meaning_value(x) for x in node.args)
        raise ValueError('not a synthetic compound')
    result={}
    for scheme in ('A','B'):
        rd,ds=snap(scheme,True);rc,cs=snap(scheme,False)
        direct_bits=0;composed_bits=0
        for i in range(256):
            direct=Word(f'複合{i}_{i%synonyms}')
            comp=Call(Word(op),(Word(roots[i//16]),Word(roots[i%16])))
            assert rd.parse(rd.emit(direct))==direct
            assert rc.parse(rc.emit(comp))==comp
            assert rd.meanings[direct.concept]==f'pair:{i//16}:{i%16}'
            assert meaning_value(direct)==meaning_value(comp)==(i//16,i%16)
            assert (comp.operator.concept,comp.args[0].concept,comp.args[1].concept)==(op,roots[i//16],roots[i%16])
            direct_bits+=len(rd.emit(direct));composed_bits+=len(rc.emit(comp))
        crossover=next(reps for reps in range(1,100) if 8*ds+reps*direct_bits < 8*cs+reps*composed_bits)
        result[scheme]={'synonyms':synonyms,'direct_sync_bytes':ds,'compose_sync_bytes':cs,'crossover':crossover,
                        'direct_256_bits':direct_bits,'compose_256_bits':composed_bits,
                        'totals':{reps:(8*ds+reps*direct_bits,8*cs+reps*composed_bits) for reps in (1,10,100)}}
    return result

def main():
    print('ICFP_KNOWN_VECTORS')
    vectors=[(NIL,'00'),(0,'010'),(1,'01100001'),(-1,'10100001'),(16,'0111000010000'),
             (Pair(1,2),'110110000101100010')]
    for obj,bits in vectors:
        assert mod(obj)==bits and dem(bits)==obj
        print(type(obj).__name__,bits)
    rng=random.Random(20261102)
    for _ in range(2000):
        n=rng.randrange(-(2**63),2**63)
        assert dem(mod(n))==n
    print('ICFP_INT_RANDOM_ROUNDTRIP_PASS',2000)
    must_fail(lambda:dem('100'))  # negative zero
    must_fail(lambda:dem('0110')) # truncated integer
    must_fail(lambda:dem('0101')) # trailing bits
    must_fail(lambda:dem('011100000001')) # noncanonical 8-bit integer value 1

    A=[];B=[];sizes={};delta_sizes={}
    for d in base.DICTS:
        m=base.manifest(d)
        for scheme,out in [('A',A),('B',B)]:
            blob=sl15.pack(snapshot(d,m,scheme))
            s=validate_snapshot(sl15.unpack(blob))
            out.append(Route(s))
            sizes[(scheme,d.ver)]=len(blob)
    for scheme,routes in [('A',A),('B',B)]:
        for a,b in zip(routes,routes[1:]):
            c=delta(a.s,b.s)
            blob=sl15.pack(c)
            rebuilt=apply_delta(a.s,sl15.unpack(blob))
            assert rebuilt==b.s
            delta_sizes[(scheme,a.version,b.version)]=len(blob)
        c=delta(routes[0].s,routes[-1].s)
        blob=sl15.pack(c)
        assert apply_delta(routes[0].s,sl15.unpack(blob))==routes[-1].s
        delta_sizes[(scheme,1,3)]=len(blob)
        must_fail(lambda:apply_delta(routes[1].s,c))
        damaged=bytearray(blob);damaged[-1]^=1
        must_fail(lambda:sl15.unpack(bytes(damaged)))
        # No other route's mapping is stored: independent snapshots are sufficient.
        if scheme=='A':assert 'global_order' not in routes[-1].s
        else:assert 'layers' not in routes[-1].s
    print('SINGLE_ROUTE_SYNC_BYTES')
    for scheme in ('A','B'):
        print(scheme,'snapshots',[sizes[(scheme,v)] for v in (1,2,3)],
              'deltas_1to2_2to3_direct1to3',[delta_sizes[(scheme,*p)] for p in ((1,2),(2,3),(1,3))])
    print('LEGACY_DUAL_ROUTE_SNAPSHOT_V3_BYTES',len(sl15.pack(sl15.snapshot(base.V3,base.manifest(base.V3)))))

    # Interchange uses canonical lexical ordering within a version-bound bridge;
    # adding names can renumber bridge IDs. Fingerprint+version prevent guessing.
    reg={};regA={}
    for a,b in zip(A,B):
        assert bridge_names(a)==bridge_names(b) and bridge_fp(a)==bridge_fp(b)
        reg[(a.version,bridge_fp(a))]=b
        regA[(a.version,bridge_fp(a))]=a
    count=0
    for d,a,b in zip(base.DICTS,A,B):
        for _ in range(400):
            ast=base.random_ast(rng,d)
            ia=to_icfp_packet(ast,a)
            ib=to_icfp_packet(ast,b)
            assert ia==ib
            assert from_icfp_packet(ia,reg)==ast
            assert from_icfp_packet(ib,regA)==ast
            assert a.parse(a.emit(ast))==ast
            assert b.parse(b.emit(ast))==ast
            count+=1
    print('CROSS_ROUTE_ICFP_AST_ROUNDTRIP_PASS',count,'route_payload_roundtrips',count*2)
    sample=base.sample_ast()
    ia=to_icfp_packet(sample,A[2]);assert from_icfp_packet(ia,reg)==sample
    print('SAMPLE_V3_PAYLOAD_BITS','A',len(A[2].emit(sample)),'B',len(B[2].emit(sample)),'ICFP_VERSIONED_DATA',len(ia))
    must_fail(lambda:from_icfp_packet(ia,{(A[0].version,bridge_fp(A[0])):A[0]}))
    must_fail(lambda:from_icfp_packet(ia[:-1],reg))
    must_fail(lambda:from_icfp_packet(ia+'0',reg))
    changed=dict(B[2].s);changed['meanings']={**changed['meanings'],'加':'semantics:synthetic:modulo-addition'}
    changed.pop('route_fp');changed['route_fp']=fp(changed)
    changed_route=Route(changed)
    assert bridge_fp(changed_route)!=bridge_fp(B[2])
    must_fail(lambda:from_icfp_packet(ia,{(changed_route.version,bridge_fp(changed_route)):changed_route}))
    # Malformed AST tag and out-of-range word ID are rejected even with a valid ICFP structure.
    must_fail(lambda:from_icfp_packet(mod(plist([3,bridge_fp(B[2]),plist([99])])),reg))
    must_fail(lambda:from_icfp_packet(mod(plist([3,bridge_fp(B[2]),plist([0,999999])])),reg))
    print('ICFP_AND_ROUTE_ERROR_REJECTION_PASS')

    print('SYNTHETIC_COMPOSITION_VS_DIRECT (sync bytes, 256 concepts payload bits per pass)')
    for synonyms in (1,2):
        for scheme,data in compound_test(synonyms).items():
            print('synonyms',synonyms,'scheme',scheme,'sync_direct',data['direct_sync_bytes'],
                  'sync_compose',data['compose_sync_bytes'],'bits_direct',data['direct_256_bits'],
                  'bits_compose',data['compose_256_bits'],'crossover_passes',data['crossover'],'totals_bits_1_10_100',data['totals'])
    print('LIMITS: ICFP Modulation is real, but AST tags/lexical ID bridge are experimental; no ICFP evaluator, no official SLE, no new student B, no measured CPU')

if __name__=='__main__':main()