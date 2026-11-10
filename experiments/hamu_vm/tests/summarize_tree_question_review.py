"""Check equal pre-intervention history and every 16-round ledger."""
import csv
import io
import sys
from collections import defaultdict
from pathlib import Path

lines=Path(sys.argv[1]).read_text().splitlines()
data=[lines[0]]+[s for s in lines[1:] if s and s[0].isdigit()]
rows=[{k:int(v) for k,v in row.items()} for row in csv.DictReader(io.StringIO("\n".join(data)))]
if len(rows)!=256:raise ValueError("256 censuses required")
groups=defaultdict(list)
for row in rows:
    if row['balance']!=200000+row['rewarded']-row['spent']:raise ValueError("resource ledger")
    if row['living']!=4+row['births']-row['retired'] or not 0<=row['living']<=8:raise ValueError("population")
    if row['rewarded']!=row['reward']*row['correct_answers']:raise ValueError("answer credit")
    groups[(row['review'],row['reward'],row['breeding'],row['reverse'])].append(row)
if len(groups)!=16:raise ValueError("sixteen cases")
for key,series in groups.items():
    if [r['round'] for r in series]!=list(range(1,17)):raise ValueError("rounds")
    if key[0]==0:
        for r in series[8:12]:
            if r['correct_answers']!=series[7]['correct_answers']:raise ValueError("delay answers")
for reward in (0,12000):
 for breeding in (0,1):
  for reverse in (0,1):
   a=groups[(0,reward,breeding,reverse)];b=groups[(1,reward,breeding,reverse)]
   if a[:8]!=[{**r,'review':0} for r in b[:8]]:raise ValueError("first eight rounds differ")
   if reward==12000 and b[-1]['correct_answers']<=a[-1]['correct_answers']:
       raise ValueError("review did not unlock answers")
print('# 雙槽阻塞的複習介入：十六輪\n')
print('兩組前八輪皆為種子3的同一題序；第9至12輪對照組只付維持費而不出題，介入組依次重出既有二階題；第13至16輪兩組皆收到相同三階題。片段表、政策、獎勵和出生規則相同。\n')
print('| 複習 | 正答獎勵 | 繁殖 | 反轉 | 存活 | 出生 | 正答 | 確認 | 路由正答 | 餘額 |')
print('| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |')
for key,series in sorted(groups.items()):
 r=series[-1];print('| '+' | '.join(map(str,(*key,r['living'],r['births'],r['correct_answers'],r['confirmed'],r['route_answers'],r['balance'])))+' |')
print('\n複習題同時增加可答機會及成本；這是教學排程介入，不代表客體已自主決定保留或清除待學槽。')
