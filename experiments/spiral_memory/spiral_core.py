"""Natural-language Spiral Memory v0.2: lexical concepts + compositional operators + explicit scope.
This is an experimental human-readable grammar, not a bitstream SLE codec.
"""
import dataclasses, json, re
from pathlib import Path

# (direct atom count, min child expressions, max child expressions, semantic role)
OPS = {
    '協議': (1,1,None,'protocol'), '語境': (1,1,None,'context'),
    '定義詞': (1,1,1,'concept-definition'), '用詞': (1,0,0,'concept-application'),
    '領域': (1,1,None,'domain'), '記憶': (1,1,None,'memory'),
    '原則': (0,1,None,'meaning'), '觀察': (0,1,None,'meaning'),
    '並行': (0,2,None,'and'), '並存': (0,2,None,'coexist'),
    '對照': (0,2,2,'contrast'), '不只是': (0,1,1,'insufficient-alone'),
    '而是': (0,1,1,'main-claim'), '可能': (0,1,1,'hypothesis'),
    '未證實': (0,1,1,'unverified'), '報告稱': (0,1,1,'reported'),
    '禁止': (0,1,1,'prohibition'), '尚未': (0,1,1,'not-yet'),
    '條件': (0,1,1,'condition'), '則': (0,1,1,'consequence'),
    '如果': (0,2,2,'conditional'), '不推出': (0,1,1,'non-implication'),
    '未取代': (2,0,0,'non-supersession'), '不等於': (2,0,0,'distinction'),
    '存在': (1,0,0,'exists'), '只核對': (1,0,0,'scope-check'),
    '已有測試報告': (2,0,0,'reported-test'),
    '本輪未重跑': (1,0,0,'not-retested'),
    '待決': (1,0,0,'undecided'), '自動取代': (2,0,0,'automatic-promotion'),
    '缺少': (1,0,0,'missing'), '不同研究': (1,0,0,'separate-research'),
    '混報成果': (1,0,0,'conflation'), '方案': (1,0,0,'option'),
    '抑制': (2,0,0,'possible-effect'), '真正長期實測': (1,0,0,'real-long-run-test'),
    '受試視窗在線': (1,0,0,'participant-online'),
    '已遺失': (1,0,0,'lost'), '取消': (1,0,0,'canceled'),
    '改用': (1,0,0,'replacement-practice'),
    '已上架': (1,0,0,'published'), '已驗證上架': (1,0,0,'publication-verified'), '聲稱在線': (1,0,0,'claim-online'), '私人候選': (1,0,0,'private-candidate'),
    '空台帳證明未上架': (1,0,0,'invalid-evidence'),
    '內容品質達標': (1,0,0,'quality-pass'), '取得公開授權': (1,0,0,'publication-permission'),
    '禁止自動刪除': (1,0,0,'no-auto-delete'), '數量': (2,0,0,'count'),
    '分開': (1,0,0,'separate-category'), '摘要凌駕原證': (1,0,0,'source-inversion'),
    '屬於提案': (2,0,0,'proposal-attribution'), '使用者已定案': (1,0,0,'user-accepted'),
    '已教會受試者': (1,0,0,'taught-to-participant'),
    '加標籤': (1,0,0,'tag-only'), '底層螺旋語化': (1,0,0,'structural-language-change'),
    '狀態': (1,0,0,'status'), '出處': (2,0,0,'provenance'),
    '依賴': (1,0,0,'dependency'), '取代': (1,0,0,'supersedes'),
}

class SpiralError(ValueError): pass
@dataclasses.dataclass
class Node:
    op: str
    args: list
    children: list = dataclasses.field(default_factory=list)
    def as_dict(self):
        return {'詞':self.op,'參數':self.args,'子句':[x.as_dict() for x in self.children]}

def tokens(source):
    """Fullwidth comma and newline delimit tokens except inside 「...」. End scope is word 句號."""
    out=[]; buf=[]; inside=False
    for no,line in enumerate(source.splitlines(),1):
        if line.lstrip().startswith('#'):continue
        for c in line+'\n':
            if c=='「' and not inside:inside=True;buf.append(c)
            elif c=='」' and inside:inside=False;buf.append(c)
            elif c in '，\n。' and not inside:
                x=''.join(buf).strip()
                if x:out.append(x)
                buf=[]
            else:buf.append(c)
    if inside:raise SpiralError('unclosed quote 「')
    if ''.join(buf).strip():out.append(''.join(buf).strip())
    return out

def parse(source):
    stream=tokens(source)
    vocab=OPS.copy(); roots=[]; stack=[]; i=0
    while i<len(stream):
        w=stream[i];i+=1
        if w=='句號':
            if not stack:raise SpiralError('orphan 句號')
            n=stack.pop()
            lo,mi,ma,_=vocab[n.op];k=len(n.children)
            if k<mi or (ma is not None and k>ma):
                raise SpiralError(f'{n.op} children={k}, expected {mi}..{ma}')
            if n.op=='對照' and [x.op for x in n.children]!=['不只是','而是']:
                raise SpiralError('對照 requires 不只是 then 而是')
            if n.op=='如果' and [x.op for x in n.children]!=['條件','則']:
                raise SpiralError('如果 requires 條件 then 則')
            continue
        if w not in vocab:raise SpiralError('undefined concept/operator: '+w)
        ar=vocab[w][0]
        if i+ar>len(stream):raise SpiralError('missing arguments '+w)
        args=stream[i:i+ar];i+=ar
        if '句號' in args:raise SpiralError('missing atom before 句號: '+w)
        args=[a[1:-1] if a.startswith('「') and a.endswith('」') else a for a in args]
        n=Node(w,args)
        if stack:stack[-1].children.append(n)
        else:roots.append(n)
        stack.append(n)
    if stack:raise SpiralError('unclosed expressions: '+','.join(n.op for n in stack))
    if len(roots)!=1 or roots[0].op!='協議':raise SpiralError('expect single 協議 root')
    if roots[0].args!=['SNL-MEM-0.2']:raise SpiralError('unsupported grammar version; use versioned decoder')
    return roots[0]

def serialize(root):
    # Structural serialization with explicit closing words; indentation is non-semantic.
    lines=[]
    def emit(n,depth):
        def quote(a):
            if any(x in a for x in ('，','。','\n')) or a=='句號':
                if '「' in a or '」' in a:raise SpiralError('quoted literal requires escaping grammar')
                return '「'+a+'」'
            return a
        lines.append('  '*depth+'，'.join([n.op]+[quote(x) for x in n.args]))
        for c in n.children:emit(c,depth+1)
        lines.append('  '*depth+'句號')
    emit(root,0)
    return '\n'.join(lines)+'\n'

def merge_snapshot(old,new):
    if old.op!='協議' or new.op!='協議' or old.args!=new.args:
        raise SpiralError('incompatible snapshots; must explicitly migrate vocab')
    import copy
    merged=copy.deepcopy(old)
    merged.children.extend(copy.deepcopy(new.children))
    entries(merged)  # refuse duplicate IDs, missing dependencies or invalid macro references
    return merged

def walk(n, domains=(), context=()):
    if n.op=='領域':domains=domains+tuple(n.args)
    if n.op=='語境':context=context+tuple(n.args)
    yield (n,domains,context)
    for c in n.children:yield from walk(c,domains,context)

def definitions(root):
    # A concept can mean a composition of earlier known words, rather than a new opcode.
    definitions={}
    for n,_,_ in walk(root):
        if n.op=='定義詞':
            name=n.args[0]
            if name in definitions or name in OPS:raise SpiralError('duplicate or reserved concept: '+name)
            definitions[name]=n.children[0]
    def check(n, visited=()):
        if n.op=='用詞':
            name=n.args[0]
            if name not in definitions:raise SpiralError('undefined composite concept '+name)
            if name in visited:raise SpiralError('circular concept expansion: '+name)
            check(definitions[name],visited+(name,))
        for ch in n.children:check(ch,visited)
    check(root)
    return definitions

def expand(n, defs):
    # Return a fresh tree, never replace archived bytes in the source document.
    if n.op=='用詞':
        if n.args[0] not in defs:raise SpiralError('undefined composite concept '+n.args[0])
        return expand(defs[n.args[0]],defs)
    return Node(n.op,n.args[:],[expand(c,defs) for c in n.children])

def entries(root):
    result={}
    defs=definitions(root)
    for n,domains,contexts in walk(root):
        if n.op=='記憶':
            key=n.args[0]
            if key in result:raise SpiralError('duplicate stable ID '+key)
            sources=[c.args for c in n.children if c.op=='出處']
            statuses=[c.args[0] for c in n.children if c.op=='狀態']
            propositions=[c for c in n.children if c.op in ('原則','觀察')]
            if len(propositions)!=1 or len(sources)!=1 or len(statuses)!=1 or not domains:
                raise SpiralError('memory needs inherited 領域, one meaning, 出處, 狀態: '+key)
            result[key]={'ID':key,'領域':'/'.join(domains),'語境':'/'.join(contexts),
                         '原則':expand(propositions[0],defs), '狀態':statuses[0], '出處':sources[0],
                         '依賴':[c.args[0] for c in n.children if c.op=='依賴']}
    for key,v in result.items():
        for dep in v['依賴']:
            if dep not in result:raise SpiralError('missing dependency '+key+' -> '+dep)
    def visit(x,chain):
        if x in chain:raise SpiralError('dependency cycle '+str(chain+(x,)))
        for d in result[x]['依賴']:visit(d,chain+(x,))
    for key in result:visit(key,())
    return result

def semantic_tokens(n):
    yield n.op
    yield from n.args
    for c in n.children:yield from semantic_tokens(c)

def consequences(data,rootid):
    pending=[rootid];seen=set()
    while pending:
        k=pending.pop(0)
        for id,v in data.items():
            if k in v['依賴'] and id not in seen and id!=rootid:
                seen.add(id);pending.append(id)
    return sorted(seen)

def contrast(n):
    # means A not sufficient alone, not !A.
    for sub in [x for x in walk(n)]:
        x=sub[0]
        if x.op=='對照':
            return {'不是僅有':x.children[0].children[0].as_dict(),
                    '主要要求':x.children[1].children[0].as_dict(),
                    '前者是否被否定':False}
    return None

def query(root, word, domain=None, include_dependents=False):
    ds=entries(root);hits=[]
    for k,rec in ds.items():
        text=' '.join(semantic_tokens(rec['原則']))
        if word in text and (not domain or domain in rec['領域']):hits.append(k)
    if include_dependents:
        downstream=set(hits)
        for h in hits:downstream.update(consequences(ds,h))
        return sorted(downstream)
    return hits

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('file');p.add_argument('--查',default=None);p.add_argument('--依賴後果',default=None)
    args=p.parse_args();root=parse(Path(args.file).read_text(encoding='utf-8'));data=entries(root)
    if args.查:print(json.dumps(query(root,args.查),ensure_ascii=False))
    elif args.依賴後果:print(json.dumps(consequences(data,args.依賴後果),ensure_ascii=False))
    else:print(json.dumps({'筆數':len(data),'領域':sorted({v['領域'] for v in data.values()})},ensure_ascii=False))