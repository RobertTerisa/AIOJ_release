#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UVA10364 测试用例生成器。

题目约束：
- 第一行 T；
- 接下来 T 行，每行格式：N a1 a2 ... aN；
- 4 <= N <= 20；
- 1 <= ai <= 10000；
- 所有木棍长度都是整数。

生成器接口：
    def generate_cases(seed=None):
        return [{"name": "...", "input": "..."}, ...]

把本文件传给对拍器：
    --generator diff_runner/generators/UVA10364_generator.py
"""

from __future__ import annotations

import random
from typing import Iterable


def _format_input(tests: Iterable[list[int]]) -> str:
    tests = list(tests)
    lines = [str(len(tests))]
    for a in tests:
        lines.append(str(len(a)) + " " + " ".join(map(str, a)))
    return "\n".join(lines) + "\n"


def _fixed_cases() -> list[dict[str, str]]:
    return [
        {
            "name": "固定-N4全1-yes",
            "input": "1\n4 1 1 1 1\n",
        },
        {
            "name": "固定-总和非4倍数-no",
            "input": "1\n4 1 1 1 2\n",
        },
        {
            "name": "固定-最长棍超边长-no",
            "input": "1\n5 4 1 1 1 1\n",
        },
        {
            "name": "固定-需要选边组合-yes",
            "input": "1\n6 3 6 4 3 6 2\n",
        },
        {
            "name": "固定-总长度可被4整除但不可拼-no",
            "input": "1\n8 8 13 8 8 11 7 13 4\n",
        },
        {
            "name": "固定-T2混合",
            "input": "2\n4 1 1 1 1\n4 1 1 1 2\n",
        },
        {
            "name": "固定-N20全1-yes",
            "input": "1\n20 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1\n",
        },
    ]


def _random_cases(rng: random.Random, count: int, n_min: int, n_max: int) -> list[dict[str, str]]:
    cases = []
    for i in range(1, count + 1):
        n = rng.randint(n_min, n_max)
        a = [rng.randint(1, 10000) for _ in range(n)]
        cases.append(
            {
                "name": f"随机-{n_min}-{n_max}-{i:02d}",
                "input": _format_input([a]),
            }
        )
    return cases


def _constructed_yes_cases(rng: random.Random, count: int) -> list[dict[str, str]]:
    """构造一定能拼成正方形的数据。

    先选一组 m 根木棍，重复 4 份，然后打乱。
    这样天然可以分成 4 组完全相同的边。
    """
    cases = []
    for i in range(1, count + 1):
        m = rng.randint(1, 5)          # m=5 时 N=20
        base = [rng.randint(1, 10000) for _ in range(m)]
        a = base * 4
        rng.shuffle(a)
        cases.append(
            {
                "name": f"构造yes-{i:02d}",
                "input": _format_input([a]),
            }
        )
    return cases


def _hard_no_cases() -> list[dict[str, str]]:
    """构造过的 N=20 困难 no 数据。"""
    return [
        {
            "name": "困难-no-a",
            "input": "1\n20 8 8 6 2 8 6 6 8 1 4 8 7 6 2 2 6 2 8 4 6\n",
        },
        {
            "name": "困难-no-b",
            "input": "1\n20 8 2 4 4 8 2 6 2 2 5 8 2 4 1 8 2 8 2 4 2\n",
        },
        {
            "name": "困难-no-c",
            "input": "1\n20 6 2 4 4 2 6 2 2 6 6 6 1 2 4 6 4 4 4 2 3\n",
        },
    ]


def generate_cases(seed: int | None = None) -> list[dict[str, str]]:
    rng = random.Random(seed)

    cases: list[dict[str, str]] = []
    cases.extend(_fixed_cases())
    cases.extend(_random_cases(rng, count=8, n_min=4, n_max=10))
    cases.extend(_random_cases(rng, count=4, n_min=11, n_max=15))
    cases.extend(_constructed_yes_cases(rng, count=5))
    cases.extend(_hard_no_cases())
    return cases


if __name__ == "__main__":
    import json

    print(json.dumps(generate_cases(seed=1), ensure_ascii=False, indent=2))
