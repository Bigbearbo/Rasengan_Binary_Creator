import json
from pathlib import Path
from datetime import date
P=Path(__file__).parent
src={
  'VM':'fixture://hamster/overview',
  'CODE':'fixture://hamster/snapshot',
  'LANG':'fixture://spiral/design',
  'TEACH':'fixture://spiral/teaching',
  'AGENT':'fixture://publishing/workflow',
  'MEM':'fixture://memory/maintenance',
}
raw=[
('H001','倉鼠世界','版本','2026-11-02 的現存較新程式候選為 hamu_vm_tree_segmented_growth_20261102.zip；只核對了封存檔及隨附報告。','檔案核對','F','VM','2026-11-02','','','最新;程式;分頁樹'),
('H002','倉鼠世界','測試','分頁樹封存報告記載七組 ASan/UBSan 回歸 PASS；10,000 題另以 O2、不含 Sanitizer 執行。本實驗建立記憶時未重跑該 C++ 測試。','報告所述','F','VM','2026-11-02','H001','','測試;分頁樹;驗證'),
('H003','倉鼠世界','決策','正式主線接續版本未由記憶維護回合定案；新產物不能自動取代已採用版本。','待覆核','A','VM','2026-11-02','H001,H002','','正式;接續;最新'),
('H004','倉鼠世界','限制','分頁樹當時仍缺舊連續樹格式遷移、跨 16-bit handle 機制和完整 HP 成本。','來源報告','F','VM','2026-11-02','H001','','遷移;成本;分頁樹'),
('H005','倉鼠世界','界線','受控倉鼠 VM、自由生態、Zero 無語言種子世界及純 01 跨模型教師實驗屬不同研究情境，不能混報成果。','現行研究界線','U','VM','2026-11-02','','','研究;Zero;純01'),
('H006','螺旋語','設計','分層詞長方案 A 與全域等長概念詞方案 B 目前並列競爭；B 尚未取代 A。','未定案','U','LANG','2026-11-02','','','詞典;全域等長;分層'),
('H007','螺旋語','假說','全域等長概念詞可能抑制詞根及組合式語義發展，尚未用真實長期記憶負載證明。','未驗證','A','LANG','2026-11-02','H006','','詞根;全域等長;風險'),
('H008','螺旋語','實驗','2026-11-01 至 02 的 Gemini 純 01 教學受試視窗已遺失，不能繼續假稱受試者在線。','封存','F','TEACH','2026-11-02','','','Gemini;純01;掉線'),
('H009','發布流程示例','工作規則','已取消每十輪正式交接及每二十輪稽核，改由必要時保存原話與更新正式入口。','現行','U','AGENT','2026-11-02','','','交接;十輪;記憶'),
('H010','發布流程示例','出刊','PUB001 私人候選存在，但是否已在 Sites 上架尚未獲真實站上證據；published 空值不能當作未發布證明。','未知','F','AGENT','2026-11-02','','','PUB001;出刊;上架;最新'),
('H011','發布流程示例','授權','PUB006 內容品質自評達標，不代表已取得把私人來源公開的授權。','禁止自動發布','F','AGENT','2026-11-02','','','PUB006;來源;公開'),
('H012','記憶系統','清理','記憶維護 MN-0.1 台帳記載候選刪除零件；舊聊天、原稿、程式 ZIP 不會自動刪除。','現行安全規則','F','MEM','2026-11-02','','','刪除;檔案;清理'),
('H013','記憶系統','來源','原始使用者主張 U、檔案 F、實跑 T、AI 推論 A 與歷史 H 應分開；後寫的摘要不能自動勝過原始證據。','現行安全規則','F','MEM','2026-11-02','','','來源;U;A;證據'),
('H014','螺旋語','研究','語義快照 S 與編碼映射快照 M 分離，是 AI 新提案，不能稱為使用者已定案的字碼或已教會受試者。','未驗證','A','LANG','2026-11-02','H006','','語境;快照;版本'),
]
fields=['識別','領域','種類','命題','狀態','證據類型','來源','時點','依賴','取代','關鍵詞']
facts=[]
for vals in raw:
 d=dict(zip(fields,vals));d['來源']=src[d['來源']];d['依賴']=[x for x in d['依賴'].split(',') if x];d['取代']=[x for x in d['取代'].split(',') if x];d['關鍵詞']=d['關鍵詞'].split(';');facts.append(d)
(P/'共同事實基準.json').write_text(json.dumps({'snapshot':'2026-11-02','items':facts},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
base=['# 一般 Markdown 記憶對照組','', '> 與自然語言螺旋語相同 14 筆來源資料；不是故意降低一般 Markdown 能力。','']
for f in facts:
 base.append(f'## {f["識別"]}｜{f["種類"]}')
 for field in fields[1:]:
  if field=='種類':continue
  v=f[field];base.append(f'{field}：{", ".join(v) if isinstance(v,list) else v}')
 base.append('')
(P/'一般Markdown對照.md').write_text('\n'.join(base)+'\n',encoding='utf8')
spiral=['語法｜自然語言螺旋記憶｜SNL-MEM-0.1','語義快照｜S1｜2026-11-02','映射快照｜自然語詞｜M1','詞典｜主張；狀態；證據類型；來源；時點；依賴；取代；關鍵詞','同義｜狀態｜現況','同義｜命題｜主張','']
for scope in dict.fromkeys(f['領域'] for f in facts):
 spiral.append(f'三層｜研究領域｜{scope}｜語境 S1/M1')
 for f in (x for x in facts if x['領域']==scope):
  spiral.append(f'  二層｜{f["種類"]}｜{f["識別"]}')
  # deliberately use a different surface form (alias) sometimes, to test normalisation
  spiral.append('    一層｜'+('主張' if f['識別'] in ('H001','H006') else '命題')+'｜'+f['命題'])
  spiral.append('    一層｜'+('現況' if f['識別'] in ('H003','H010') else '狀態')+'｜'+f['狀態'])
  for field in ['證據類型','來源','時點']:
   spiral.append('    一層｜'+field+'｜'+f[field])
  for field in ['依賴','取代','關鍵詞']:
   for val in f[field]:spiral.append('    一層｜'+field+'｜'+val)
  spiral.append('')
(P/'自然語言螺旋記憶.snl').write_text('\n'.join(spiral)+'\n',encoding='utf8')
print('created',len(facts),'records')