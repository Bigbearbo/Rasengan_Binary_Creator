#!/usr/bin/env python3
"""Read-only query facade for SNL-MEM-0.1 and equal-fact Markdown baseline."""
import argparse
from pathlib import Path
from 比較測試 import parse_spiral,parse_markdown,retrieve,affected,SPIRAL,BASE

p=argparse.ArgumentParser(description='自然語言螺旋記憶實驗；僅限精確詞條查找，不是 LLM 語義問答')
p.add_argument('--格式',choices=['螺旋語','Markdown'],default='螺旋語')
p.add_argument('--詞',help='查詢詞典登記的精確關鍵詞，例如 PUB001；可輸出多筆歧義')
p.add_argument('--領域',help='縮小研究領域，例如 倉鼠世界、螺旋語、發布流程示例、記憶系統')
p.add_argument('--ID',help='直接取記憶識別，例如 H006')
p.add_argument('--後果',help='若某記憶失效，哪些記憶需要重新覆核；只是依賴提示')
a=p.parse_args()
if not (a.詞 or a.ID or a.後果):p.error('請提供 --詞、--ID 或 --後果')
records=parse_spiral(SPIRAL.read_text(encoding='utf8')) if a.格式=='螺旋語' else parse_markdown(BASE.read_text(encoding='utf8'))
byid={r['識別']:r for r in records}
if a.後果:
 print(f'假設 {a.後果} 的前提發生變更，應重新覆核：')
 for ident in affected(records,a.後果):print('  '+ident+'｜'+byid[ident]['命題'])
if a.ID:
 if a.ID not in byid:print('未知識別；不猜測。')
 else:
  r=byid[a.ID]
  for key in ['識別','領域','種類','命題','狀態','證據類型','來源','時點','依賴','取代','關鍵詞']:
   print(f'{key}：{r.get(key)}')
if a.詞:
 x=retrieve(records,a.詞,a.領域)
 print(f'查詢：{a.詞}｜領域：{a.領域 or "不限"}｜結果：{x["type"]}')
 for ident in x['ids']:
  r=byid[ident]
  print(f'{ident} {r["命題"]} [{r["狀態"]}]')
  print('  來源：'+r['來源']+'；記錄時點：'+r['時點'])