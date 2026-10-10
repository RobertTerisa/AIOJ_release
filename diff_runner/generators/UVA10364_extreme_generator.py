#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UVA10364 极端样例生成器。

题目约束：
- 第一行 T；
- 接下来每组：N a1 a2 ... aN；
- 4 <= N <= 20；
- 1 <= ai <= 10000。

使用：
    --generator diff_runner/generators/UVA10364_extreme_generator.py
"""

from __future__ import annotations

import random
from typing import Iterable


def _format_tests(tests: Iterable[list[int]]) -> str:
    tests = list(tests)
    lines = [str(len(tests))]
    for a in tests:
        lines.append(str(len(a)) + " " + " ".join(map(str, a)))
    return "\n".join(lines) + "\n"


def _scaled(values: list[int], factor: int) -> list[int]:
    return [v * factor for v in values]


def _fixed_extreme_cases() -> list[dict[str, str]]:
    cases: list[dict[str, str]] = []

    # 边界 N 和最大长度
    cases.append({
        "name": "极端-N4-全10000-yes",
        "input": _format_tests([[10000, 10000, 10000, 10000]]),
    })
    cases.append({
        "name": "极端-N20-全10000-yes",
        "input": _format_tests([[10000] * 20]),
    })
    cases.append({
        "name": "极端-N20-全9999-yes",
        "input": _format_tests([[9999] * 20]),
    })

    # 最小长度和最大 N
    cases.append({
        "name": "极端-N20-全1-yes",
        "input": _format_tests([[1] * 20]),
    })

    # N=19，总和 20，target=5
    cases.append({
        "name": "极端-N19-混合yes",
        "input": _format_tests([[2] + [1] * 18]),
    })

    # 大数值构造 yes：选 5 根大木棍，重复 4 份
    base = [10000, 9999, 9998, 9997, 9996]
    cases.append({
        "name": "极端-N20-大值构造yes",
        "input": _format_tests([base * 4]),
    })

    # 之前构造过的困难 no，数据整体放大，仍然合法且仍然是 no
    hard_a = [8, 8, 6, 2, 8, 6, 6, 8, 1, 4, 8, 7, 6, 2, 2, 6, 2, 8, 4, 6]
    hard_b = [8, 2, 4, 4, 8, 2, 6, 2, 2, 5, 8, 2, 4, 1, 8, 2, 8, 2, 4, 2]
    hard_c = [6, 2, 4, 4, 2, 6, 2, 2, 6, 6, 6, 1, 2, 4, 6, 4, 4, 4, 2, 3]

    for name, a in [
        ("极端-困难no-a-放大1000", hard_a),
        ("极端-困难no-b-放大1000", hard_b),
        ("极端-困难no-c-放大1000", hard_c),
    ]:
        values = _scaled(a, 1000)
        cases.append({"name": name, "input": _format_tests([values])})

    # T=2 多测：第一组 yes，第二组 no
    cases.append({
        "name": "极端-T2-yes和no",
        "input": _format_tests([[10000] * 20, _scaled(hard_a, 1000)]),
    })

    return cases


def _random_extreme_cases(rng: random.Random, count: int) -> list[dict[str, str]]:
    cases: list[dict[str, str]] = []
    for i in range(1, count + 1):
        # 随机构造 yes：m 根木棍重复 4 份，N=4m 在 4~20 之间
        m = rng.randint(1, 5)
        base = [rng.randint(9000, 10000) for _ in range(m)]
        a = base * 4
        rng.shuffle(a)
        cases.append({
            "name": f"极端-随机yes-{i:02d}",
            "input": _format_tests([a]),
        })
    return cases


def generate_cases(seed: int | None = None) -> list[dict[str, str]]:
    rng = random.Random(seed)
    cases = _fixed_extreme_cases()
    cases.extend(_random_extreme_cases(rng, count=3))
    return cases


if __name__ == "__main__":
    import json

    print(json.dumps(generate_cases(seed=1), ensure_ascii=False, indent=2))
