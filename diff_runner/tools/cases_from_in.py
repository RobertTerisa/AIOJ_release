#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把常见的 .in 测试数据转换成 diff_runner 的 cases JSON。

注意：
- 只需要 .in 文件；
- 不需要 .out 文件；
- 对拍器会用题解代码现场生成参考答案。

基本用法：
    python diff_runner/tools/cases_from_in.py --in-dir testcases --out cases.json

生成的 JSON 格式：
    [
      {"name": "1", "input": "..."},
      {"name": "2", "input": "..."}
    ]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="把 .in 文件转成 diff_runner cases JSON，不需要 .out")
    parser.add_argument("--in-dir", type=Path, required=True, help="存放 .in 文件的目录")
    parser.add_argument("--out", type=Path, required=True, help="输出的 cases.json")
    parser.add_argument("--pattern", default="*.in", help=".in 文件匹配模式，默认 *.in")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.in_dir.exists():
        print(f"[错误] 目录不存在: {args.in_dir}")
        return 1

    in_files = sorted(args.in_dir.glob(args.pattern))
    if not in_files:
        print(f"[错误] 在 {args.in_dir} 下没有找到匹配 {args.pattern} 的文件")
        return 1

    cases = []
    for in_path in in_files:
        cases.append(
            {
                "name": in_path.stem,
                "input": in_path.read_text(encoding="utf-8"),
            }
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"已生成: {args.out}")
    print(f"用例数量: {len(cases)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
