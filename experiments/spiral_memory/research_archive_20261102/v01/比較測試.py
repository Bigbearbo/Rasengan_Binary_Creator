#!/usr/bin/env python3
"""SNL-MEM-0.1 vs plain Markdown: identical evidence, deterministic comparison only."""
import argparse
import json
import time
from pathlib import Path
from copy import deepcopy

ROOT=Path(__file__).parent
BASE=ROOT/'一般Markdown對照.md'
SPIRAL=ROOT/'自然語言螺旋記憶.snl'
GOLD=ROOT/'共同事實基準.json'
SINGLE=('命題','狀態','證據類型','來源','時點')
MULTI=('依賴','取代','關鍵詞')
KNOWN=set(SINGLE+MULTI)


def clean(d):
    for field in MULTI:
        d.setdefault(field,[])
    for field in SINGLE:
        if field not in d:raise ValueError('缺少欄位: '+field)
    if not d.get('識別') or not d.get('領域') or not d.get('種類'):
        raise ValueError('缺少穩定識別或分類')
    return d


def parse_markdown(source):
    records=[];cur=None
    for number,line in enumerate(source.splitlines(),1):
        if line.startswith('## '):
            if cur is not None:records.append(clean(cur))
            bits=line[3:].split('｜')
            if len(bits)!=2:raise ValueError(f'MD 行{number} 標題')
            cur={'識別':bits[0].strip(),'種類':bits[1].strip()}
        elif cur is not None and '：' in line:
            key,val=line.split('：',1)
            key=key.strip();val=val.strip()
            if key not in KNOWN|{'領域'}:raise ValueError('MD 未定欄位 '+key)
            if key in cur:raise ValueError('MD 重複欄位 '+key)
            cur[key]=[x.strip() for x in val.split(',') if x.strip()] if key in MULTI else val
    if cur is not None:records.append(clean(cur))
    validate(records)
    return records


def parse_spiral(source):
    records=[];cur=None;context=None;found_header=False;lex={};seen=set()
    for n,raw in enumerate(source.splitlines(),1):
        if not raw:continue
        if raw.startswith('語法｜'):
            if raw!='語法｜自然語言螺旋記憶｜SNL-MEM-0.1':raise ValueError('協議版本不符')
            found_header=True;continue
        if raw.startswith(('語義快照｜','映射快照｜','詞典｜')):continue
        if raw.startswith('同義｜'):
            bits=raw.split('｜')
            if len(bits)!=3 or bits[1] not in KNOWN or bits[2] in KNOWN or (bits[2] in lex and lex[bits[2]]!=bits[1]):
                raise ValueError('同義詞覆寫或未定義 '+raw)
            lex[bits[2]]=bits[1];continue
        if raw.startswith('三層｜'):
            if cur is not None:records.append(clean(cur));cur=None
            bits=raw.split('｜')
            if len(bits)!=4 or bits[1]!='研究領域' or bits[3]!='語境 S1/M1':raise ValueError('三層語境無效')
            context=bits[2];continue
        if raw.startswith('  二層｜'):
            if not context:raise ValueError('二層缺父層')
            if cur is not None:records.append(clean(cur))
            bits=raw.strip().split('｜')
            if len(bits)!=3:raise ValueError('二層標題無效')
            cur={'識別':bits[2],'種類':bits[1],'領域':context}
            continue
        if raw.startswith('    一層｜'):
            if cur is None:raise ValueError('一層缺父層')
            bits=raw.strip().split('｜',2)
            if len(bits)!=3:raise ValueError('一層內容無效')
            key=lex.get(bits[1],bits[1]);val=bits[2]
            if key not in KNOWN:raise ValueError(f'一層未定義概念詞 {key} 行{n}')
            if key in MULTI:cur.setdefault(key,[]).append(val)
            elif key in cur:raise ValueError('一層不可重複的欄位 '+key)
            else:cur[key]=val
            continue
        raise ValueError(f'無法判定語層 行{n}: {raw}')
    if cur is not None:records.append(clean(cur))
    if not found_header:raise ValueError('缺少協議頭')
    validate(records)
    return records


def validate(records):
    ids=[r['識別'] for r in records]
    if len(ids)!=len(set(ids)):raise ValueError('同一詞識別重複')
    idset=set(ids)
    for r in records:
        for x in r['依賴']+r['取代']:
            if x not in idset:raise ValueError(f'未找到依賴：{r["識別"]} -> {x}')
    graph={r['識別']:r['依賴'] for r in records};state={}
    def check(n):
        if state.get(n)==1:raise ValueError('依賴形成循環')
        if state.get(n)==2:return
        state[n]=1
        for m in graph[n]:check(m)
        state[n]=2
    for x in graph:check(x)


def retrieve(records,keyword,scope=None):
    candidates=[]
    for r in records:
        if scope is not None and r['領域']!=scope:continue
        if keyword in r['關鍵詞'] or keyword==r['識別']:
            candidates.append(r['識別'])
    if not candidates:return {'type':'未知','ids':[]}
    if len(candidates)>1:return {'type':'歧義','ids':sorted(candidates)}
    return {'type':'命中','ids':candidates}


def affected(records,change):
    if change not in {r['識別'] for r in records}:raise ValueError('變動來源不存在')
    rev={r['識別']:set() for r in records}
    for r in records:
        for dep in r['依賴']:rev[dep].add(r['識別'])
    found=set();queue=[change]
    while queue:
        i=queue.pop()
        for child in rev[i]:
            if child not in found:
                found.add(child);queue.append(child)
    return sorted(found)


def expect_error(fn):
    try:fn()
    except ValueError:return True
    return False


def main():
    golden=json.loads(GOLD.read_text(encoding='utf8'))['items']
    md=parse_markdown(BASE.read_text(encoding='utf8'))
    sl=parse_spiral(SPIRAL.read_text(encoding='utf8'))
    checks=[]
    def check(label,result):checks.append({'項目':label,'結果':'PASS' if result else 'FAIL'})
    check('同一來源內容14筆逐欄一致', sorted(md,key=lambda x:x['識別'])==sorted(sl,key=lambda x:x['識別'])==sorted(golden,key=lambda x:x['識別']))
    check('每筆穩定識別不重複',len({r['識別'] for r in sl})==len(sl))
    check('螺旋語範圍繼承與別名正規化',sl[0]['領域']=='倉鼠世界' and sl[0]['命題']==golden[0]['命題'] and sl[2]['狀態']=='待覆核')
    qs=[('分頁樹','倉鼠世界'),('測試','倉鼠世界'),('正式','倉鼠世界'),('遷移','倉鼠世界'),('Zero','倉鼠世界'),('全域等長','螺旋語'),('詞根','螺旋語'),('Gemini','螺旋語'),('交接','發布流程示例'),('PUB001','發布流程示例'),('PUB006','發布流程示例'),('刪除','記憶系統'),('來源','記憶系統'),('不存在的詞','螺旋語'),('最新',None)]
    for k,s in qs:
        check(f'相同查詢結果 {k}/{s or "跨領域"}',retrieve(md,k,s)==retrieve(sl,k,s))
    check('跨領域/同領域歧義不亂選',retrieve(sl,'最新',None)['type']=='歧義')
    check('不存在的詞答未知',retrieve(sl,'不存在的詞','螺旋語')['type']=='未知')
    check('分頁樹證據失效影響相關結論',affected(md,'H001')==affected(sl,'H001')==['H002','H003','H004'])
    check('詞典競爭前提變更影響相依假說',affected(sl,'H006')==['H007','H014'])
    check('無關來源不誤傷其他專案',not any(x in affected(sl,'H001') for x in ['H009','H010','H012']))
    check('使用者原始檔案未因情境更新改寫',md==parse_markdown(BASE.read_text(encoding='utf8')))
    check('拒絕孤兒一層',expect_error(lambda:parse_spiral('語法｜自然語言螺旋記憶｜SNL-MEM-0.1\n    一層｜命題｜假')))
    check('拒絕新詞未定義直接使用',expect_error(lambda:parse_spiral(SPIRAL.read_text(encoding='utf8').replace('一層｜狀態｜','一層｜魔法標籤｜',1))))
    check('拒絕不合法的依賴識別',expect_error(lambda:validate([dict(x,依賴=['H999']) if x['識別']=='H001' else x for x in sl])))
    check('拒絕循環依賴',expect_error(lambda:validate([dict(x,依賴=['H007']) if x['識別']=='H006' else x for x in sl])))
    check('拒絕相同語義別名衝突',expect_error(lambda:parse_spiral(SPIRAL.read_text(encoding='utf8').replace('同義｜命題｜主張','同義｜命題｜現況'))))
    sizes={'一般Markdown對照.md':BASE.stat().st_size,'自然語言螺旋記憶.snl':SPIRAL.stat().st_size}
    def timed(fn,text):
        t=time.perf_counter()
        for _ in range(300):fn(text)
        return round((time.perf_counter()-t)/300*1000,4)
    times={'Markdown_每次解析毫秒':timed(parse_markdown,BASE.read_text(encoding='utf8')),'螺旋_每次解析毫秒':timed(parse_spiral,SPIRAL.read_text(encoding='utf8'))}
    out={'實驗':'自然語言螺旋記憶 SNL-MEM-0.1 / 一般 Markdown','日期':'2026-11-02','資料數':len(sl),'查詢數':len(qs),'檢查數':len(checks),'通過數':sum(c['結果']=='PASS' for c in checks),'位元組':sizes,'解析時間':times,'檢查':checks,'限制':'完全共享人工整理的 14 筆事實、同一套確定性查詢；只證明規格解析與對照可重現，沒有 LLM 盲測、沒有時間長期測試、沒有證明 SLE 壓縮或理解優勢。'}
    (ROOT/'機器測試結果.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in out.items() if k not in ['檢查']},ensure_ascii=False,indent=2))
    for c in checks:
        if c['結果']!='PASS':print('FAIL',c['項目'])
    if out['通過數']!=out['檢查數']:raise SystemExit(1)

if __name__=='__main__':main()