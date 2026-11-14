"""Check the 40 closed populations and optional seed-zero reference replay."""
import csv
import io
import sys
from collections import defaultdict
from pathlib import Path


def read_csv(path, prefix):
    lines = Path(path).read_text().splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(prefix))
    data = [lines[start]]
    for line in lines[start + 1:]:
        if not line or not line[0].isdigit():
            break
        data.append(line)
    return [{k: int(v) for k, v in row.items()}
            for row in csv.DictReader(io.StringIO("\n".join(data)))]


rows = read_csv(sys.argv[1], "seed,reward,")
if len(rows) != 480:
    raise ValueError("Expected 480 censuses")
groups = defaultdict(list)
for row in rows:
    if row["seed"] not in range(5) or row["reward"] not in (0, 12000):
        raise ValueError("Unexpected schedule or reward")
    if row["balance"] != 200000 + row["rewarded"] - row["spent"]:
        raise ValueError("Resource conservation")
    if row["living"] != 4 + row["births"] - row["retired"] or not 0 <= row["living"] <= 8:
        raise ValueError("Population conservation")
    if sum(row[k] for k in ("off", "on", "after_failure", "reserve")) != row["living"]:
        raise ValueError("Policy count")
    if row["rewarded"] != row["reward"] * row["correct_answers"]:
        raise ValueError("Actual answer reward")
    if not 0 <= row["confirmed"] <= row["correct_answers"] or not 0 <= row["route_answers"] <= row["correct_answers"]:
        raise ValueError("Answer/confirmation accounting")
    key = tuple(row[k] for k in ("seed", "reward", "breeding", "reverse"))
    groups[key].append(row)
if len(groups) != 40:
    raise ValueError("Expected forty scenarios")
for series in groups.values():
    if [r["round"] for r in series] != list(range(1, 13)):
        raise ValueError("Missing or unordered rounds")
    for before, after in zip(series, series[1:]):
        for field in ("correct_answers", "confirmed", "route_answers", "spent", "rewarded", "births", "retired"):
            if after[field] < before[field]:
                raise ValueError("Cumulative field decreased: " + field)
if len(sys.argv) > 2:
    reference = read_csv(sys.argv[2], "schedule,reward,")
    expected = {tuple(r[k] for k in ("reward", "breeding", "reverse", "round")): r
                for r in reference if r["schedule"] == 1}
    for row in rows:
        if row["seed"]:
            continue
        key = tuple(row[k] for k in ("reward", "breeding", "reverse", "round"))
        if {k: v for k, v in row.items() if k != "seed"} != {
            k: v for k, v in expected[key].items() if k != "schedule"
        }:
            raise ValueError("Seed zero does not replay matched-catalogue comparison")

print("# 相同十二題的五種順序\n")
print("全部順序保留同一份四片段表、十二題多重集合、前八題二階／後四題三階，以及資源和繁殖規則。種子0是原課程；種子1至4只在各階段內重排。下面列出原始順序與反轉創始政策順序的最終結果。\n")
print("| 種子 | 獎勵 | 繁殖 | 反轉 | 存活 | 出生 | 正答 | 確認 | 路由正答 | 餘額 |")
print("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
for key, series in sorted(groups.items()):
    row = series[-1]
    print("| " + " | ".join(map(str, (*key, row["living"], row["births"],
        row["correct_answers"], row["confirmed"], row["route_answers"], row["balance"]))) + " |")
print("\n題目內容完全相同，只能支持本設定下的順序敏感性。資料值與題型的配對也由同一題保留，沒有測試任意新題或跨階降回。")
