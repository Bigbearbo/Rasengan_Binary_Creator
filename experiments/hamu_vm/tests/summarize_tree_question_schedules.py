"""Check every census and pair fixed/varied schedules under one catalogue."""
import csv
import io
import sys
from collections import defaultdict
from pathlib import Path

lines = Path(sys.argv[1]).read_text().splitlines()
start = next(i for i, line in enumerate(lines) if line.startswith("schedule,reward,"))
data = [lines[start]]
for line in lines[start + 1:]:
    if not line or not line[0].isdigit():
        break
    data.append(line)
rows = [{k: int(v) for k, v in row.items()} for row in csv.DictReader(io.StringIO("\n".join(data)))]
if len(rows) != 192:
    raise ValueError("Expected 192 censuses")
groups = defaultdict(list)
for row in rows:
    if row["schedule"] not in (0, 1) or row["reward"] not in (0, 12000):
        raise ValueError("Unexpected schedule or reward")
    if row["balance"] != 200000 + row["rewarded"] - row["spent"]:
        raise ValueError("Resource conservation")
    if row["living"] != 4 + row["births"] - row["retired"] or not 0 <= row["living"] <= 8:
        raise ValueError("Population conservation")
    if sum(row[k] for k in ("off", "on", "after_failure", "reserve")) != row["living"]:
        raise ValueError("Policy census")
    if row["rewarded"] != row["reward"] * row["correct_answers"]:
        raise ValueError("Actual answer credit")
    if not 0 <= row["confirmed"] <= row["correct_answers"]:
        raise ValueError("Confirmation accounting")
    if not 0 <= row["route_answers"] <= row["correct_answers"]:
        raise ValueError("Route accounting")
    groups[(row["schedule"], row["reward"], row["breeding"], row["reverse"])].append(row)
if len(groups) != 16:
    raise ValueError("Expected sixteen controls")
for series in groups.values():
    if [r["round"] for r in series] != list(range(1, 13)):
        raise ValueError("Missing or unordered round")
    for before, after in zip(series, series[1:]):
        for key in ("correct_answers", "confirmed", "route_answers", "spent", "rewarded", "births", "retired"):
            if after[key] < before[key]:
                raise ValueError("Cumulative field decreased: " + key)

print("# 同片段表：固定題與變動題序（十二輪）\n")
print("兩組都使用 ZERO／XOR1／COPY／FLIP 四個有效片段、四名相同政策創始個體、相同費率與繁殖規則。固定題為二階 op1／資料5／ZERO；變動題依十二題課程交錯三個二階詞，第九輪起升到三階。先嘗試已綁樹路由，無法路由才進學習，避免完成學習者被錯算為閒置。\n")
print("| 題序 | 獎勵 | 繁殖 | 反轉 | 存活 | 出生 | 退場 | 正答 | 確認 | 路由正答 | 餘額 | 已消耗 |")
print("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
for key, series in sorted(groups.items()):
    row = series[-1]
    print("| " + " | ".join(map(str, (*key, row["living"], row["births"], row["retired"],
        row["correct_answers"], row["confirmed"], row["route_answers"],
        row["balance"], row["spent"]))) + " |")
print("\n這是同一候選表、同一生命週期規則下的題序控制；題義數量與難度仍隨題序一起改變，不能據此推出一般題庫難度排名。固定題重複也讓已確認路由頻繁被使用，與多種新詞的學習成本不同。")
