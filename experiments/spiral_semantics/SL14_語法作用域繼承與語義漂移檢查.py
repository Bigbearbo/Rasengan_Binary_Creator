#!/usr/bin/env python3
"""SL-0.14 experimental AST codecs; not an official Spiral Language bit format.
Compare context-inherited layer coding (A) vs global-width coding (B), with the
same AST and same framing. Semantic manifest equality is NOT semantic proof.
"""
from dataclasses import dataclass
import hashlib, json, random, zlib

# Reproduce the SL-0.13 test dictionaries locally; no external file required.
@dataclass(frozen=True)
class Dictionary:
    ver:int
    layers:dict
    widths:dict
    global_width:int
    global_order:tuple
    def __post_init__(self):
        assert set(self.layers)=={1,2}
        assert set(self.layers[1]).isdisjoint(self.layers[2])
        assert len(self.layers[1])<=2**self.widths[1]
        assert len(self.layers[2])<=2**self.widths[2]
        assert len(self.global_order)<=2**self.global_width
        assert set(self.global_order)==set(self.layers[1]+self.layers[2])
    @property
    def loc(self):return {w:(k,i) for k in (1,2) for i,w in enumerate(self.layers[k])}
    @property
    def gloc(self):return {w:i for i,w in enumerate(self.global_order)}
    @property
    def fp(self):
        raw=json.dumps([self.ver,self.layers,self.widths,self.global_width,self.global_order],sort_keys=True,ensure_ascii=False).encode()
        return int.from_bytes(hashlib.sha256(raw).digest()[:4],'big')

L1=['數學','加','乘','數值','句號','列表','引用','說話者','問號','定義','呼叫','確認','缺件','函式','普通','命名']
L2=['語言','版本','詞典','作用域','更新','根快照','歷史','巢狀','來源','回答','問題','老師','學生','假想','引用原文','開始','結束','原樣','同義','差分','遞迴','列表型','函式型','可求值','只描述','撤回','重試','錯誤','遺失','說明']
NEW2=['槽位墓碑','世代','引用檢查']
NEW1=['剪切','合併','或','且','非','回音','反回音','計數','比較','重命名','遷移','對照','翻譯','驗證','保存','刪除']
V1=Dictionary(1,{1:L1[:],2:L2[:]},{1:4,2:5},6,tuple(L1+L2))
V2=Dictionary(2,{1:L1[:],2:L2+NEW2},{1:4,2:6},6,tuple(L1+L2+NEW2))
V3=Dictionary(3,{1:L1+NEW1,2:L2+NEW2},{1:5,2:6},7,tuple(L1+L2+NEW2+NEW1))
DICTS=(V1,V2,V3)
MAGIC=0xA714
HEADER=16+8+2+32+32+24+32  # 146 bits, both schemes identical

def u(n,width):
    if n<0 or n>=2**width:raise ValueError('out of range')
    return f'{n:0{width}b}'

def digest32(obj):
    b=json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    return int.from_bytes(hashlib.sha256(b).digest()[:4],'big')

@dataclass(frozen=True)
class Word:
    concept:str
@dataclass(frozen=True)
class ListNode:
    children:tuple
@dataclass(frozen=True)
class Call:
    operator:Word
    args:tuple
@dataclass(frozen=True)
class Scope:
    layer:int
    body:object

@dataclass(frozen=True)
class Manifest:
    meanings:dict
    @property
    def fp(self):return digest32(self.meanings)

def manifest(d,changed=None):
    m={w:f'semantics:stable:{w}' for w in d.global_order}
    if changed:m.update(changed)
    return Manifest(m)

REG={}
for d in DICTS:
    m=manifest(d);REG[(d.ver,d.fp,m.fp)]=(d,m)
DRIFT=manifest(V2,{'加':'semantics:synthetic:modulo-addition'})
REG[(V2.ver,V2.fp,DRIFT.fp)]=(V2,DRIFT)

def emit_ast(node,d,scheme,context=1):
    if isinstance(node,Word):
        if node.concept not in d.loc:raise ValueError('missing concept')
        k,idx=d.loc[node.concept]
        if scheme=='A':
            prefix='00' if k==context else '01'+u(k,2)
            return prefix+u(idx,d.widths[k])+'0'*k
        return '00'+u(d.gloc[node.concept],d.global_width)
    if isinstance(node,ListNode):
        if len(node.children)>255:raise ValueError('list too long')
        return '10'+u(len(node.children),8)+''.join(emit_ast(x,d,scheme,context) for x in node.children)
    if isinstance(node,Call):
        if len(node.args)>255:raise ValueError('call too long')
        return '110'+u(len(node.args),8)+emit_ast(node.operator,d,scheme,context)+''.join(emit_ast(x,d,scheme,context) for x in node.args)
    if isinstance(node,Scope):
        if node.layer not in d.layers:raise ValueError('bad layer')
        return '111'+u(node.layer,2)+emit_ast(node.body,d,scheme,node.layer)
    raise ValueError('invalid AST')

def parse_ast(bits,d,scheme,pos=0,context=1,depth=0):
    if depth>64:raise ValueError('max depth')
    def take(n):
        nonlocal pos
        if pos+n>len(bits):raise ValueError('truncated')
        s=bits[pos:pos+n];pos+=n
        return s
    t=take(2)
    if t in ('00','01'):
        k=context
        if t=='01':
            if scheme=='B':raise ValueError('unnecessary override in B')
            k=int(take(2),2)
            if k not in d.layers:raise ValueError('bad layer escape')
            if k==context:raise ValueError('noncanonical escape')
        if scheme=='A':
            idx=int(take(d.widths[k]),2)
            if take(k)!='0'*k:raise ValueError('bad suffix')
            if idx>=len(d.layers[k]):raise ValueError('invalid local ID')
            return Word(d.layers[k][idx]),pos
        idx=int(take(d.global_width),2)
        if idx>=len(d.global_order):raise ValueError('invalid global ID')
        return Word(d.global_order[idx]),pos
    if t=='10':
        count=int(take(8),2);xs=[]
        for _ in range(count):
            x,pos=parse_ast(bits,d,scheme,pos,context,depth+1);xs.append(x)
        return ListNode(tuple(xs)),pos
    if take(1)=='0': # 110 = call
        count=int(take(8),2)
        op,pos=parse_ast(bits,d,scheme,pos,context,depth+1)
        if not isinstance(op,Word):raise ValueError('call operator must be word')
        xs=[]
        for _ in range(count):
            x,pos=parse_ast(bits,d,scheme,pos,context,depth+1);xs.append(x)
        return Call(op,tuple(xs)),pos
    k=int(take(2),2) # 111 = scope
    if k not in d.layers:raise ValueError('bad scope')
    x,pos=parse_ast(bits,d,scheme,pos,k,depth+1)
    return Scope(k,x),pos

def encode(node,d,m,scheme):
    assert scheme in ('A','B')
    if set(d.global_order)!=set(m.meanings):raise ValueError('manifest incomplete')
    p=emit_ast(node,d,scheme)
    return u(MAGIC,16)+u(d.ver,8)+u(1 if scheme=='A' else 2,2)+u(d.fp,32)+u(m.fp,32)+u(len(p),24)+u(zlib.crc32(p.encode()),32)+p

def decode(frame,registry=REG):
    if len(frame)<HEADER or set(frame)-{'0','1'}:raise ValueError('invalid frame')
    if int(frame[:16],2)!=MAGIC:raise ValueError('magic')
    ver=int(frame[16:24],2);s=int(frame[24:26],2)
    if s not in (1,2):raise ValueError('scheme')
    scheme='A' if s==1 else 'B'
    dfp=int(frame[26:58],2);mfp=int(frame[58:90],2)
    n=int(frame[90:114],2);chk=int(frame[114:146],2);p=frame[146:]
    if n!=len(p) or zlib.crc32(p.encode())!=chk:raise ValueError('frame corrupt')
    if (ver,dfp,mfp) not in registry:raise ValueError('missing exact dictionary or manifest')
    d,m=registry[(ver,dfp,mfp)]
    node,pos=parse_ast(p,d,scheme)
    if pos!=len(p):raise ValueError('trailing bits')
    return node,d,m,scheme

def concepts(node):
    if isinstance(node,Word):return [node.concept]
    if isinstance(node,ListNode):return sum((concepts(x) for x in node.children),[])
    if isinstance(node,Call):return concepts(node.operator)+sum((concepts(x) for x in node.args),[])
    if isinstance(node,Scope):return concepts(node.body)
    raise ValueError('bad node')

def transcode(frame,target_d,target_m,target_scheme):
    node,source_d,source_m,_=decode(frame)
    words=concepts(node)
    for w in words:
        if w not in target_d.loc:raise ValueError('target missing concept '+w)
        if source_m.meanings[w]!=target_m.meanings[w]:raise ValueError('semantic manifest drift '+w)
    new=encode(node,target_d,target_m,target_scheme)
    assert decode(new)[0]==node
    return new,{'source':(source_d.ver,source_d.fp,source_m.fp),
                'target':(target_d.ver,target_d.fp,target_m.fp),
                'checked_unique_concepts':len(set(words)),
                'manifest_compatible':True,'semantic_equivalence_proven':False}

def sample_ast():
    return Scope(2,ListNode((Word('語言'),Word('版本'),Word('老師'),
        Scope(1,ListNode((Word('數學'),Call(Word('加'),(Word('數值'),Word('數值'))),Word('句號')))),
        Word('問號'),Word('回答'))))

def random_ast(rng,d,depth=0,context=1):
    if depth>=4 or rng.random()<.55:
        return Word(rng.choice(d.global_order))
    x=rng.random()
    if x<.4:return ListNode(tuple(random_ast(rng,d,depth+1,context) for _ in range(rng.randrange(0,5))))
    if x<.8:return Call(Word(rng.choice(d.global_order)),tuple(random_ast(rng,d,depth+1,context) for _ in range(rng.randrange(0,4))))
    k=rng.choice([1,2]);return Scope(k,random_ast(rng,d,depth+1,k))

def must_fail(fn,label):
    try:fn()
    except ValueError:return
    raise AssertionError('must reject '+label)

def main():
    rng=random.Random(20261102)
    total=0
    for d in DICTS:
        m=manifest(d)
        for _ in range(1000):
            ast=random_ast(rng,d)
            for s in ('A','B'):
                frame=encode(ast,d,m,s)
                decoded,dd,mm,ss=decode(frame)
                assert (decoded,dd.ver,mm.fp,ss)==(ast,d.ver,m.fp,s)
                total+=1
    sample=sample_ast()
    for source in DICTS:
        for target in DICTS:
            for a in ('A','B'):
                for b in ('A','B'):
                    src=encode(sample,source,manifest(source),a)
                    dst,receipt=transcode(src,target,manifest(target),b)
                    assert decode(dst)[0]==sample and receipt['manifest_compatible']
                    total+=1
    # Same ID/name and mapping, but changed semantic manifest => explicitly reject.
    src=encode(ListNode((Word('數學'),Word('加'))),V1,manifest(V1),'A')
    must_fail(lambda:transcode(src,V2,DRIFT,'B'),'semantic drift')
    # A compatible subset may still migrate even if unused concepts drift.
    safe=encode(ListNode((Word('數學'),Word('乘'))),V1,manifest(V1),'A')
    assert transcode(safe,V2,DRIFT,'B')[1]['manifest_compatible']
    # A drift frame cannot be decoded with a registry that knows only the normal v2 manifest.
    drift_frame=encode(sample,V2,DRIFT,'B')
    standard_registry={k:v for k,v in REG.items() if k!=(V2.ver,V2.fp,DRIFT.fp)}
    must_fail(lambda:decode(drift_frame,standard_registry),'missing manifest')
    must_fail(lambda:decode(src[:-1]),'truncated frame')
    corrupt=src[:150]+('1' if src[150]=='0' else '0')+src[151:]
    must_fail(lambda:decode(corrupt),'bit flip')
    must_fail(lambda:decode(src+'0'),'trailing bits')
    # Decoder rejects invalid scope layer, even with valid frame checksum.
    bad_scope=Scope(2,Word('老師'))
    payload=emit_ast(bad_scope,V1,'A')
    bad_payload=payload[:3]+'11'+payload[5:]
    must_fail(lambda:parse_ast(bad_payload,V1,'A'),'bad layer')
    # Actual word encoding cost across identical semantic ASTs.
    rows=[]
    for d in DICTS:
        m=manifest(d)
        for label,words in [
            ('flat_90_10', [Word(rng.choice(d.layers[1] if rng.random()<.9 else d.layers[2])) for _ in range(1000)]),
            ('flat_50_50', [Word(rng.choice(d.layers[1] if rng.random()<.5 else d.layers[2])) for _ in range(1000)]),
            ('flat_alternating', [Word(rng.choice(d.layers[1] if i%2==0 else d.layers[2])) for i in range(1000)])]:
            ast=ListNode(tuple(ListNode(tuple(words[i:i+200])) for i in range(0,len(words),200)))
            a=encode(ast,d,m,'A');b=encode(ast,d,m,'B')
            assert decode(a)[0]==decode(b)[0]==ast
            rows.append((d.ver,label,len(a),len(b),len(a)-len(b)))
        for label,n1,n2 in [('scoped_90_10',900,100),('scoped_50_50',500,500)]:
            # list length is capped at 255; use chunked lists with same semantics.
            def chunked(k,n):
                xs=[Word(rng.choice(d.layers[k])) for _ in range(n)]
                return Scope(k,ListNode(tuple(ListNode(tuple(xs[i:i+200])) for i in range(0,n,200))))
            ast=ListNode((chunked(1,n1),chunked(2,n2)))
            a=encode(ast,d,m,'A');b=encode(ast,d,m,'B')
            assert decode(a)[0]==decode(b)[0]==ast
            rows.append((d.ver,label,len(a),len(b),len(a)-len(b)))
    print('AST_ROUNDTRIPS_AND_TRANSCODES_PASS',total)
    print('DRIFT_REJECT_AND_COMPATIBLE_SUBSET_PASS')
    print('MISSING_MANIFEST_TRUNCATION_CORRUPTION_SCOPE_REJECTION_PASS')
    print('HEADER_BITS',HEADER)
    print('version workload A_bits B_bits A_minus_B')
    for row in rows:print(*row)
    print('SAMPLE_AST',sample)
    print('SAMPLE_A_BITS',len(encode(sample,V1,manifest(V1),'A')))
    print('SAMPLE_B_BITS',len(encode(sample,V1,manifest(V1),'B')))
if __name__=='__main__':main()