import json, pathlib, tempfile, time
from spiral_core import *
P=pathlib.Path(__file__).parent
base=json.loads((P/'共同事實基準.json').read_text(encoding='utf-8'))['items']
text=(P/'螺旋記憶_語法本體.snl').read_text(encoding='utf-8')
root=parse(text);rows=entries(root)
u=parse((P/'作者原話_概念組合示例.snl').read_text(encoding='utf-8'))
urows=entries(u)
checks={}
def check(name, yes):
    assert yes,name
    checks[name]=True
check('十四筆ID完整',set(rows)=={x['識別'] for x in base})
check('每筆領域／狀態／來源／依賴完整',all(rows[x['識別']]['領域']==x['領域'] and rows[x['識別']]['狀態']==x['狀態'] and rows[x['識別']]['出處']==[x['證據類型'],x['來源']] and rows[x['識別']]['依賴']==x['依賴'] for x in base))
check('作者原則單獨一份U記憶',list(urows)==['U001'] and urows['U001']['出處'][0]=='U')
check('域繼承無逐筆標籤',len([n for n,*_ in walk(root) if n.op=='領域'])==4)
check('概念關係可查詢',{'H006','H007'}<=set(query(root,'全域等長')))
check('查詢可展開依賴後果',{'H006','H007','H014'}<=set(query(root,'全域等長',include_dependents=True)))
check('查詢不存在不捏造',query(root,'虛構完全不存在的記憶XYZ')==[])
check('失效傳播H001',consequences(rows,'H001')==['H002','H003','H004'])
check('失效傳播H006',consequences(rows,'H006')==['H007','H014'])
check('對照有兩個不同語義分支', [c.op for c in urows['U001']['原則'].children[0].children]==['不只是','而是'])
c=contrast(urows['U001']['原則'])
check('不只是A並非否定A',c['前者是否被否定'] is False and c['主要要求']['詞']=='底層螺旋語化')
check('未取代有指向',any(n.op=='未取代' and n.args==['B','A'] for n,*_ in walk(rows['H006']['原則'])))
check('不推出與如果的語義結構',any(n.op=='如果' for n,*_ in walk(rows['H011']['原則'])) and any(n.op=='不推出' for n,*_ in walk(rows['H011']['原則'])))
check('未知上架不當作未上架',any(n.op=='已驗證上架' for n,*_ in walk(rows['H010']['原則'])) and rows['H010']['狀態']=='未知')
check('單句原文非既有字段內容',all('命題｜' not in text for _ in [0]))
# Error paths -- reject rather than guessing
for label,src in {
    '未知算符拒絕':'協議，SNL-MEM-0.2，奇異算符，句號，句號',
    '未關閉拒絕':'協議，SNL-MEM-0.2，語境，今天，句號',
    '錯誤終止拒絕':'協議，SNL-MEM-0.2，句號，句號',
    '不只是不可當否定':'協議，SNL-MEM-0.2，對照，不只是，加標籤，詞，句號，句號，句號，句號',
    '版本不合拒絕':'協議，SNL-MEM-0.3，語境，測試，領域，測試，記憶，X，原則，存在，x，句號，句號，狀態，a，句號，出處，A，a，句號，句號，句號，句號，句號',
}.items():
    try:parse(src)
    except SpiralError:pass
    else:raise AssertionError(label)
    checks[label]=True
# Test indentation irrelevant
macro_root=parse((P/'新詞組合與重用.snl').read_text(encoding='utf-8'))
macro_entries=entries(macro_root)
check('語詞序列可序列化往返',parse(serialize(root)).as_dict()==root.as_dict())
check('新概念詞可序列化往返',parse(serialize(macro_root)).as_dict()==macro_root.as_dict())
merged=merge_snapshot(root,u)
check('只增記憶不覆寫原筆數',len(entries(merged))==15 and len(rows)==14)
check('合併後U來源仍為使用者',entries(merged)['U001']['出處'][0]=='U')
try:merge_snapshot(merged,u)
except SpiralError:checks['重複記憶ID拒絕合併']=True
else:raise AssertionError('重複記憶ID拒絕合併')
check('新詞不改解析器即可擴展',set(macro_entries)=={'U002','U003'} and '底層化原則' not in OPS)
check('重用新詞可展開語義',contrast(macro_entries['U002']['原則'])['主要要求']['詞']=='底層螺旋語化')
check('多處使用同一新詞',any(n.op=='對照' for n,*_ in walk(macro_entries['U003']['原則'])))
for label,src in {
    '未知組合詞拒絕':'協議，SNL-MEM-0.2，用詞，無此詞，句號，句號',
    '自我引用組合詞拒絕':'協議，SNL-MEM-0.2，定義詞，循環，用詞，循環，句號，句號，句號'
}.items():
    try:entries(parse(src))
    except SpiralError:pass
    else:raise AssertionError(label)
    checks[label]=True
check('縮排不改解析',parse(text.replace('    ','' )).as_dict()==root.as_dict())
nested='協議，SNL-MEM-0.2，語境，t，領域，大領域，領域，子領域，領域，小領域，領域，第四層，記憶，N001，原則，存在，x，句號，句號，狀態，a，句號，出處，A，f，句號，句號，句號，句號，句號，句號，句號，句號'
check('多層領域可巢狀繼承',entries(parse(nested))['N001']['領域']=='大領域/子領域/小領域/第四層')
(P/'螺旋記憶_含作者修正快照.snl').write_text(serialize(merged),encoding='utf-8')
# Snapshot size and clock are NOT cross-model LLM performance tests
raw=(P/'螺旋記憶_語法本體.snl').stat().st_size
old=(P/'一般Markdown對照.md').stat().st_size
legacy=(P/'自然語言螺旋記憶_v01.snl').stat().st_size
summary={'版本':'SNL-MEM-0.2','基準筆數':len(rows),'使用者新增案例筆數':len(urows),'機器結構檢查':len(checks),'全部通過':all(checks.values()),'測項':checks,
         'bytes':{'Markdown_v01對照':old,'螺旋語_v01_標籤版':legacy,'螺旋語_v02_組合語法':raw,'作者範例額外':(P/'作者原話_概念組合示例.snl').stat().st_size},
         '限制':'僅為人工轉寫及文法解析；概念關係未做獨立自然語言理解盲測、真實跨版本重編碼或長期效能量測。'}
(P/'測試結果.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k!='測項'},ensure_ascii=False,indent=2))