#!/usr/bin/env python3
"""螺旋語增量解析器 prototype v0.1

用途：依已知 (n, k, offset) 切詞、維護上下文詞樹、提示未知語義。
不負責：從任意位元串自動發現階層／階數、猜測新詞語義、執行算符。

示範配置是「數學、算符、參數1、參數2」，不是完整螺旋語規範。
配置保存在 state JSON 的 profiles，可增添不同版本、欄位長度與層數。
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


DEFAULT_PROFILE = {
    "fields": [
        {"role": "category", "n": 1, "k": 1},
        {"role": "operator", "n": 3, "k": 1},
        {"role": "arg1", "n": 3, "k": 1},
        {"role": "arg2", "n": 3, "k": 1},
    ],
    # 這是教材情境中的共識詞典，而非聲稱「數學」在所有版本皆為 00。
    "category_meanings": {"00": "數學"},
}


def initial_state() -> dict[str, Any]:
    return {
        "format_version": 1,
        "profiles": {"math_demo_v1": DEFAULT_PROFILE},
        "tree": {},
    }


def tokenize(bits: str, n: int, k: int, offset: int) -> dict[str, Any]:
    """對應論文 Tokenize(S,k,n,offset)。不推測 n、k、offset。"""
    if n <= 0 or k <= 0 or offset < 0:
        raise ValueError("n、k 必須大於 0；offset 不可小於 0")
    end = offset + n + k
    if end > len(bits):
        raise ValueError(f"位元不足：位置 {offset} 需要 {n+k} 位")
    word = bits[offset:end]
    if any(bit not in "01" for bit in word):
        raise ValueError(f"非二進位詞碼：{word!r}")
    if word[n:] != "0" * k:
        raise ValueError(f"尾碼不合法：{word!r}；預期末尾 {k} 個 0")
    return {
        "offset": offset,
        "end": end,
        "word": word,
        "information": word[:n],
        "value": int(word[:n], 2),
        "n": n,
        "k": k,
    }


class SpiralParser:
    def __init__(self, state_path: str | Path):
        self.path = Path(state_path)
        self.state = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else initial_state()

    def save(self) -> None:
        """先寫暫存檔再替換，避免中途寫壞語法樹。"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_name(self.path.name + ".tmp")
        temp.write_text(json.dumps(self.state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temp, self.path)

    def parse(self, bits: str, profile_name: str = "math_demo_v1") -> dict[str, Any]:
        # 任一詞不合法、詞長不合、類別不匹配：整則不更新記憶。
        profile = self.state["profiles"].get(profile_name)
        if profile is None:
            raise ValueError(f"未知配置 {profile_name!r}；先在 state JSON 增加 profiles")
        if not bits or any(bit not in "01" for bit in bits):
            raise ValueError("輸入必須是非空的純 0/1 位元串（不能帶逗號或空白）")

        tokens = []
        offset = 0
        for field in profile["fields"]:
            item = tokenize(bits, int(field["n"]), int(field["k"]), offset)
            item["role"] = field["role"]
            tokens.append(item)
            offset = item["end"]
        if offset != len(bits):
            raise ValueError(f"訊息剩餘 {len(bits) - offset} 位；此配置不接受未定義欄位")

        categories = [item for item in tokens if item["role"] == "category"]
        operators = [item for item in tokens if item["role"] == "operator"]
        if len(categories) != 1 or len(operators) != 1:
            raise ValueError("此原型配置恰好需要一個 category 與一個 operator 欄位")
        cat, op = categories[0], operators[0]
        cat_name = profile["category_meanings"].get(cat["word"])
        if cat_name is None:
            raise ValueError(f"未知類別詞 {cat['word']}；無法安全套用 {profile_name} 的數學欄位規則")

        branch = self.state["tree"].setdefault(profile_name, {}).setdefault(cat["word"], {})
        operator_tree = branch.setdefault("operators", {})
        node = operator_tree.get(op["word"])
        is_new = node is None
        if is_new:
            node = {"status": "unknown", "meaning": None, "seen": 0}
            operator_tree[op["word"]] = node
        node["seen"] += 1
        args = [t["value"] for t in tokens if t["role"].startswith("arg")]
        node["last_args"] = args
        tree_path = f"{profile_name}/{cat_name}/算符/{op['value']}"
        if node["status"] == "unknown":
            hint = f"{tree_path}：{'新增' if is_new else '再次出現'}未知算符；參數={args}。需由 AI 根據後續證據推測語義。"
        else:
            hint = f"{tree_path}：已確認語義 {node['meaning']}；參數={args}。"
        self.save()
        return {
            "profile": profile_name,
            "tokens": tokens,
            "path": tree_path,
            "new_node": is_new,
            "hint": hint,
        }

    def define(self, operator_word: str, meaning: str, profile_name: str = "math_demo_v1", category_word: str = "00") -> None:
        """僅外部教師或已驗證流程才應確認語義。"""
        node = self.state["tree"].get(profile_name, {}).get(category_word, {}).get("operators", {}).get(operator_word)
        if node is None:
            raise ValueError("尚無該詞節點；請先解析含有該算符的合法訊息")
        if not meaning.strip():
            raise ValueError("語義不可為空")
        node["status"] = "confirmed"
        node["meaning"] = meaning.strip()
        self.save()


def main() -> None:
    cli = argparse.ArgumentParser(description="螺旋語增量解析器（結構解析＋語法樹＋提示）")
    cli.add_argument("--state", default="spiral_tree.json", help="語法樹／配置 JSON 檔案")
    cli.add_argument("--profile", default="math_demo_v1", help="解析配置名稱")
    sub = cli.add_subparsers(dest="command", required=True)
    sub.add_parser("tree", help="檢視目前配置與語法樹")
    parser = sub.add_parser("parse", help="解析純 0/1 訊息並更新語法樹")
    parser.add_argument("bits")
    setter = sub.add_parser("define", help="人工確認某個已看過的算符語義")
    setter.add_argument("operator_word", help="完整算符詞碼，包含尾碼 0")
    setter.add_argument("meaning")
    args = cli.parse_args()
    engine = SpiralParser(args.state)
    try:
        if args.command == "parse":
            result = engine.parse(args.bits, args.profile)
        elif args.command == "define":
            engine.define(args.operator_word, args.meaning, args.profile)
            result = {"confirmed": args.operator_word, "meaning": args.meaning}
        else:
            result = engine.state
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except ValueError as exc:
        cli.error(str(exc))


if __name__ == "__main__":
    main()