#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UVA10364 数据生成器（普通 180 组 + 极端/边界 20 组）。

题目输入格式：
    第一行 T；
    接下来 T 行，每行 N a1 a2 ... aN。
约束：
    4 <= N <= 20
    1 <= ai <= 10000

生成器接口：
    def generate_cases(seed=None) -> list[dict]
        [{"name": "...", "input": "完整标准输入字符串"}, ...]
"""

from __future__ import annotations

import random
from typing import Iterable


def _format_input(tests: Iterable[list[int]]) -> str:
    """按题目输入格式拼接一次完整运行所需的标准输入。"""
    tests = list(tests)
    lines = [str(len(tests))]
    for a in tests:
        lines.append(str(len(a)) + " " + " ".join(map(str, a)))
    return "\n".join(lines) + "\n"


def _case(name: str, tests: list[list[int]]) -> dict[str, str]:
    return {"name": name, "input": _format_input(tests)}


# ---------------------------------------------------------------------------
# 普通样例：180 组
# ---------------------------------------------------------------------------

def _ordinary_fixed_cases() -> list[dict[str, str]]:
    return [
        _case("普通-固定-N4全1-yes", [[1, 1, 1, 1]]),
        _case("普通-固定-总和非4倍数-no", [[1, 1, 1, 2]]),
        _case("普通-固定-最长棍超边长-no", [[4, 1, 1, 1, 1]]),
        _case("普通-固定-需要选边组合-yes", [[3, 6, 4, 3, 6, 2]]),
        _case("普通-固定-总和可4整除但不可拼-no", [[8, 8, 13, 8, 8, 11, 7, 13, 4]]),
        _case("普通-固定-N20全1-yes", [[1] * 20]),
        _case("普通-固定-N20全2-yes", [[2] * 20]),
    ]


def _ordinary_random_cases(rng: random.Random, count: int) -> list[dict[str, str]]:
    """普通随机数据：长度范围大，覆盖随机的格式与早期 no。"""
    cases: list[dict[str, str]] = []
    for i in range(1, count + 1):
        n = rng.randint(4, 20)
        a = [rng.randint(1, 10000) for _ in range(n)]
        cases.append(_case(f"普通-随机-{i:03d}", [a]))
    return cases


def _ordinary_small_sum4_cases(rng: random.Random, count: int) -> list[dict[str, str]]:
    """小长度且总和调整为 4 的倍数，容易把搜索逼到深层。"""
    cases: list[dict[str, str]] = []
    for i in range(1, count + 1):
        n = rng.randint(4, 15)
        a = [rng.randint(1, 12) for _ in range(n)]
        # 只调整最后一个元素，确保仍然合法且总和是 4 的倍数。
        a[-1] += (-sum(a)) % 4
        cases.append(_case(f"普通-小数据4倍数-{i:03d}", [a]))
    return cases


def _ordinary_constructed_yes_cases(rng: random.Random, count: int) -> list[dict[str, str]]:
    """先选 m 根，重复 4 份并打乱，保证一定有解。"""
    cases: list[dict[str, str]] = []
    for i in range(1, count + 1):
        m = (i - 1) % 5 + 1          # N = 4, 8, 12, 16, 20
        if i % 2 == 0:
            base = [rng.randint(1, 30) for _ in range(m)]
        else:
            base = [rng.randint(1, 10000) for _ in range(m)]
        a = base * 4
        rng.shuffle(a)
        cases.append(_case(f"普通-构造yes-{i:03d}", [a]))
    return cases


def _ordinary_constructed_no_cases(rng: random.Random, count: int) -> list[dict[str, str]]:
    """保证无解的简单构造：总和是 4 的倍数，但有一根超过边长。"""
    cases: list[dict[str, str]] = []
    for i in range(1, count + 1):
        # 边长 target，四根为 [target+d, target, target, target-d]。
        # 总和 = 4*target，且 target+d > target。
        target = rng.randint(100, 9000)
        d = rng.randint(1, min(500, 10000 - target))
        a = [target + d, target, target, target - d]
        rng.shuffle(a)
        cases.append(_case(f"普通-构造no-{i:03d}", [a]))
    return cases


def _ordinary_multi_cases(rng: random.Random, count: int) -> list[dict[str, str]]:
    """T > 1 的多测样例。"""
    cases: list[dict[str, str]] = []
    for i in range(1, count + 1):
        t = rng.randint(2, 4)
        tests: list[list[int]] = []
        for _ in range(t):
            n = rng.randint(4, 12)
            a = [rng.randint(1, 100) for _ in range(n)]
            tests.append(a)
        cases.append(_case(f"普通-多测-{i:03d}", tests))
    return cases


def _ordinary_cases(rng: random.Random) -> list[dict[str, str]]:
    cases: list[dict[str, str]] = []
    cases.extend(_ordinary_fixed_cases())                 # 7
    cases.extend(_ordinary_random_cases(rng, 60))         # 60
    cases.extend(_ordinary_small_sum4_cases(rng, 40))     # 40
    cases.extend(_ordinary_constructed_yes_cases(rng, 50))# 50
    cases.extend(_ordinary_constructed_no_cases(rng, 10)) # 10
    cases.extend(_ordinary_multi_cases(rng, 13))          # 13
    assert len(cases) == 180, len(cases)
    return cases


# ---------------------------------------------------------------------------
# 极端 / 边界样例：20 组
# ---------------------------------------------------------------------------

def _extreme_cases(rng: random.Random) -> list[dict[str, str]]:
    hard_a = [8, 8, 6, 2, 8, 6, 6, 8, 1, 4, 8, 7, 6, 2, 2, 6, 2, 8, 4, 6]
    hard_b = [8, 2, 4, 4, 8, 2, 6, 2, 2, 5, 8, 2, 4, 1, 8, 2, 8, 2, 4, 2]
    hard_c = [6, 2, 4, 4, 2, 6, 2, 2, 6, 6, 6, 1, 2, 4, 6, 4, 4, 4, 2, 3]

    cases: list[dict[str, str]] = [
        _case("极端-N4全1-yes", [[1, 1, 1, 1]]),
        _case("极端-N4全10000-yes", [[10000, 10000, 10000, 10000]]),
        _case("极端-N20全1-yes", [[1] * 20]),
        _case("极端-N20全10000-yes", [[10000] * 20]),
        _case("极端-N20全9999-yes", [[9999] * 20]),
        _case("极端-N20全2-yes", [[2] * 20]),
        _case("极端-总和非4倍数-no", [[10000, 9999, 9998, 9997]]),
        _case("极端-最长棍超边长-no", [[10000, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]]),
        _case("极端-大值构造yes", [[10000, 9999, 9998, 9997, 9996] * 4]),
        _case("极端-小值构造yes", [[1, 2, 3, 4, 5] * 4]),
        _case("极端-困难no-a", [hard_a]),
        _case("极端-困难no-b", [hard_b]),
        _case("极端-困难no-c", [hard_c]),
        _case("极端-困难no-a放大1000", [[v * 1000 for v in hard_a]]),
        _case("极端-困难no-b放大1000", [[v * 1000 for v in hard_b]]),
        _case("极端-困难no-c放大1000", [[v * 1000 for v in hard_c]]),
        _case("极端-T2-yes和no", [[10000] * 20, hard_c]),
        _case("极端-T3混合", [[1] * 20, [10000, 9999, 9998, 9997], [10000, 9999, 9998, 9997, 9996] * 4]),
        _case("极端-N20单根过大-no", [[10000] + [499] * 19]),
    ]
    # 最后一组：总和严格为 4 的倍数，长度尽量极端。
    a = [rng.randint(9000, 10000) for _ in range(20)]
    a[-1] += (-sum(a)) % 4
    cases.append(_case("极端-N20随机4倍数", [a]))

    assert len(cases) == 20, len(cases)
    return cases


def generate_cases(seed: int | None = None) -> list[dict[str, str]]:
    rng = random.Random(seed)
    cases = _ordinary_cases(rng)   # 180
    cases.extend(_extreme_cases(rng))  # 20
    assert len(cases) == 200, len(cases)
    return cases


if __name__ == "__main__":
    import json

    print(json.dumps(generate_cases(seed=1), ensure_ascii=False, indent=2))
