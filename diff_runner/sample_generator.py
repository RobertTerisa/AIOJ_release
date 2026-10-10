#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""示例测试用例生成器。

真实题目可以单独写一个这样的文件，对拍器通过 --generator 调用。
生成器需要定义：

    def generate_cases(seed=None):
        return [{"name": "...", "input": "..."}, ...]

返回 list[str] 也可以。
"""

from __future__ import annotations

import random


def generate_cases(seed: int | None = None):
    rng = random.Random(seed)
    cases = []

    # 手写几个基础样例
    cases.append({"name": "基础-全1", "input": "1\n4 1 1 1 1\n"})
    cases.append({"name": "基础-总和非4倍数", "input": "1\n4 1 1 1 2\n"})

    # 随机小数据
    for i in range(1, 11):
        n = rng.randint(4, 9)
        a = [rng.randint(1, 10) for _ in range(n)]
        cases.append(
            {
                "name": f"随机-{i:02d}",
                "input": "1\n" + str(n) + " " + " ".join(map(str, a)) + "\n",
            }
        )

    # 构造一定可以拼成正方形的 yes 数据
    for i in range(1, 4):
        m = rng.randint(2, 3)
        base = [rng.randint(1, 20) for _ in range(m)]
        a = base * 4
        rng.shuffle(a)
        cases.append(
            {
                "name": f"构造yes-{i:02d}",
                "input": "1\n" + str(len(a)) + " " + " ".join(map(str, a)) + "\n",
            }
        )

    return cases
