#!/usr/bin/env python3
# SL-0.13: experimental bitstream prototypes, NOT finalized Spiral Language wire syntax.
from dataclasses import dataclass
import hashlib, json, random, zlib
from collections import Counter

MAGIC=0xA75C
HEADER_BITS=16+8+32+16+32

def u(n,w):
    if not 0 <= n < 2**w: raise ValueError(f'out of range: {n}/{w}')
    return f'{n:0{w}b}'

def crc(bits): return zlib.crc32(bits.encode('ascii'))

@dataclass(frozen=True)
class D:
    ver:int
    layers:dict
    widths:dict
    global_width:int
    def __post_init__(self):
        assert set(self.layers)=={1,2}
        assert len(self.layers[1])==len(set(self.layers[1]))
        assert len(self.layers[2])==len(set(self.layers[2]))
        assert not set(self.layers[1]) & set(self.layers[2])
        assert all(len(self.layers[k])<=2**self.widths[k] for k in (1,2))
        assert sum(map(len,self.layers.values()))<=2**self.global_width
    @property
    def all(self): return self.layers[1]+self.layers[2]
    @property
    def loc(self): return {v:(k,i) for k in (1,2) for i,v in enumerate(self.layers[k])}
    @property
    def global_loc(self): return {v:i for i,v in enumerate(self.all)}
    @property
    def fp(self):
        raw=json.dumps([self.ver,self.layers,self.widths,self.global_width],sort_keys=True,ensure_ascii=False).encode()
        return int.from_bytes(hashlib.sha256(raw).digest()[:4],'big')

# Stable global indexes: append new tokens at end, not by re-concatenating layer arrays.
# D.global_order provides that order, and dictionary fingerprint includes it.
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
        assert len(self.layers[1])<=2**self.widths[1] and len(self.layers[2])<=2**self.widths[2]
        assert len(self.global_order)<=2**self.global_width
        assert set(self.global_order)==set(self.layers[1]+self.layers[2])
    @property
    def loc(self): return {v:(k,i) for k in (1,2) for i,v in enumerate(self.layers[k])}
    @property
    def gloc(self): return {v:i for i,v in enumerate(self.global_order)}
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
REG={d.ver:d for d in (V1,V2,V3)}

def encode(words,d,scheme):
    for w in words:
        if w not in d.loc: raise ValueError('unknown concept: '+w)
    if scheme=='A':
        # 2-bit layer + 8-bit run length are framing metadata, not spiral words.
        payload='';i=0
        while i<len(words):
            k=d.loc[words[i]][0]; j=i+1
            while j<len(words) and j-i<255 and d.loc[words[j]][0]==k:j+=1
            payload+=u(k,2)+u(j-i,8)
            payload+=''.join(u(d.loc[w][1],d.widths[k])+'0'*k for w in words[i:j])
            i=j
    elif scheme=='B':
        payload=''.join(u(d.gloc[w],d.global_width) for w in words)
    else: raise ValueError('bad scheme')
    return u(MAGIC,16)+u(d.ver,8)+u(d.fp,32)+u(len(words),16)+u(crc(payload),32)+payload

def decode(bits,scheme,registry=REG):
    if len(bits)<HEADER_BITS or set(bits)-set('01'):raise ValueError('invalid frame')
    if int(bits[:16],2)!=MAGIC:raise ValueError('bad magic')
    ver=int(bits[16:24],2)
    if ver not in registry:raise ValueError('missing dictionary')
    d=registry[ver]
    if int(bits[24:56],2)!=d.fp:raise ValueError('dictionary fingerprint mismatch')
    count=int(bits[56:72],2); chk=int(bits[72:104],2); p=bits[104:]
    if crc(p)!=chk:raise ValueError('checksum mismatch')
    words=[];pos=0
    if scheme=='A':
        while len(words)<count:
            if pos+10>len(p):raise ValueError('truncated run')
            k=int(p[pos:pos+2],2); n=int(p[pos+2:pos+10],2);pos+=10
            if k not in d.layers or n==0 or n>count-len(words):raise ValueError('bad run')
            w=d.widths[k]+k
            if pos+n*w>len(p):raise ValueError('truncated token')
            for _ in range(n):
                tok=p[pos:pos+w];pos+=w
                if not tok.endswith('0'*k):raise ValueError('bad suffix')
                idx=int(tok[:d.widths[k]],2)
                if idx>=len(d.layers[k]):raise ValueError('unknown token')
                words.append(d.layers[k][idx])
    elif scheme=='B':
        w=d.global_width
        if len(p)!=count*w:raise ValueError('invalid fixed-length payload')
        for i in range(count):
            idx=int(p[i*w:(i+1)*w],2)
            if idx>=len(d.global_order):raise ValueError('unknown token')
            words.append(d.global_order[idx])
        pos=len(p)
    else:raise ValueError('bad scheme')
    if pos!=len(p):raise ValueError('trailing bits')
    return words,d

def transcode(bits,src_scheme,dst_scheme,target):
    words,source=decode(bits,src_scheme)
    if any(w not in target.loc for w in words):raise ValueError('target missing concept')
    new=encode(words,target,dst_scheme)
    assert decode(new,dst_scheme)[0]==words
    # A high-level, explicit migration receipt (not a new native wire word).
    return new,{'source_version':source.ver,'target_version':target.ver,'source_fp':f'{source.fp:08x}',
        'target_fp':f'{target.fp:08x}','concept_count':len(words),
        'semantic_digest':hashlib.sha256(json.dumps(words,ensure_ascii=False).encode()).hexdigest(),
        'lossless':True}

def generate(d,pattern,rng):
    a=d.layers[1];b=d.layers[2]
    if pattern=='long_runs':return [rng.choice(a) for _ in range(900)]+[rng.choice(b) for _ in range(100)]
    if pattern=='alternating':return [rng.choice(a if i%2==0 else b) for i in range(1000)]
    if pattern=='random_90_10':return [rng.choice(a if rng.random()<0.9 else b) for _ in range(1000)]
    raise ValueError(pattern)

def expect_fail(fn,what):
    try:fn()
    except ValueError:return
    raise AssertionError('should reject: '+what)

def main():
    rng=random.Random(20261102)
    assert (V1.widths,V1.global_width)==({1:4,2:5},6)
    assert (V2.widths,V2.global_width)==({1:4,2:6},6)
    assert (V3.widths,V3.global_width)==({1:5,2:6},7)
    assert [len(d.global_order) for d in REG.values()]==[46,49,65]
    sample=['語言','版本','說話者','老師','數學','加','列表','引用','句號','問號','說明']
    for d in REG.values():
        for scheme in ('A','B'):
            assert decode(encode(sample,d,scheme),scheme)[0]==sample
    tests=0
    for d in REG.values():
        for _ in range(1000):
            words=[rng.choice(d.global_order) for _ in range(rng.randrange(0,101))]
            for scheme in ('A','B'):
                bits=encode(words,d,scheme)
                assert decode(bits,scheme)[0]==words
                tests+=1
    for src in REG.values():
        for dst in REG.values():
            for a,b in [('A','B'),('B','A'),('A','A'),('B','B')]:
                shared=[w for w in src.global_order if w in dst.loc]
                words=[rng.choice(shared) for _ in range(150)]
                new,receipt=transcode(encode(words,src,a),a,b,dst)
                assert decode(new,b)[0]==words and receipt['lossless']
                tests+=1
    # Reject unsupported semantic migration, wrong registry, changed fingerprint, corruption, and truncated payload.
    expect_fail(lambda:transcode(encode(['槽位墓碑'],V2,'A'),'A','B',V1),'missing target concept')
    bits=encode(sample,V2,'A')
    expect_fail(lambda:decode(bits,'A',{1:V1,3:V3}),'missing dictionary')
    expect_fail(lambda:decode(bits,'A',{2:V1}),'wrong dictionary fingerprint')
    corrupt=bits[:115]+('1' if bits[115]=='0' else '0')+bits[116:]
    expect_fail(lambda:decode(corrupt,'A'),'corruption')
    expect_fail(lambda:decode(bits[:-1],'A'),'truncation')
    # Old frames remain readable after upgrading registry.
    old=encode(sample,V1,'B'); assert decode(old,'B',REG)[0]==sample
    # Dictionary width, version and concept count must be included in the actual frame.
    rows=[]
    for d in REG.values():
        for pattern in ('long_runs','random_90_10','alternating'):
            words=generate(d,pattern,rng)
            aa=encode(words,d,'A');bb=encode(words,d,'B')
            assert decode(aa,'A')[0]==decode(bb,'B')[0]==words
            rows.append((d.ver,pattern,len(aa),len(bb),len(aa)-len(bb)))
    print('ROUNDTRIPS_AND_MIGRATIONS_PASS',tests)
    print('ERROR_REJECTION_PASS 5; OLD_FRAME_REPLAY_PASS')
    print('HEADER_BITS',HEADER_BITS)
    print('v pattern A_bits B_bits A_minus_B')
    for row in rows:print(*row)
    print('SAMPLE',sample)
    print('SAMPLE_V1_A',encode(sample,V1,'A'))
    print('SAMPLE_V1_B',encode(sample,V1,'B'))
if __name__=='__main__':main()