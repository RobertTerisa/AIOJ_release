#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P9228 原神  数据生成器

输入格式（单组，无多测）:
    n m k
    a_1 ... a_n
    b_1 ... b_m
约束: 1<=n,m<=1e6, 0<=a_i,b_i,k<=1e9
"""
from __future__ import annotations

import random

LIM = 10 ** 9


def _case(name, n, m, k, a, b):
    assert len(a) == n and len(b) == m, name
    return {
        "name": name,
        "input": "%d %d %d\n%s\n%s\n" % (
            n, m, k, " ".join(map(str, a)), " ".join(map(str, b))),
    }


def generate_cases(seed=None):
    rng = random.Random(seed)
    cases = []

    # ---------- 1. 题面样例 ----------
    cases.append({"name": "样例1", "input": "6 7 3\n1 1 4 5 1 4\n1 9 1 9 8 1 0\n"})
    cases.append({"name": "样例2", "input": "5 3 5\n1 4 2 8 5\n7 1 4\n"})
    cases.append({"name": "样例3", "input": "1 1 0\n2\n3\n"})

    # ---------- 2. 极小 / 手工边界 ----------
    cases.append(_case("n1m1_k0_zero", 1, 1, 0, [0], [0]))
    cases.append(_case("n1m1_ak_eq", 1, 1, 7, [7], [5]))        # a == k
    cases.append(_case("n1m1_ak_up", 1, 1, 7, [8], [5]))        # a = k+1
    cases.append(_case("n1m1_ak_down", 1, 1, 7, [6], [5]))      # a = k-1
    cases.append(_case("n1m1_bothmax", 1, 1, LIM, [LIM], [LIM]))
    cases.append(_case("n1m1_kbig", 1, 1, LIM, [1], [1]))
    cases.append(_case("n2m1", 2, 1, 3, [10, 1], [4]))
    cases.append(_case("n1m2", 1, 2, 3, [10], [4, 7]))
    cases.append(_case("n3m3_equal", 3, 3, 10, [10, 10, 10], [1, 1, 1]))
    cases.append(_case("all_a_zero", 4, 4, 5, [0, 0, 0, 0], [9, 9, 9, 9]))
    cases.append(_case("all_b_zero", 4, 4, 5, [9, 9, 9, 9], [0, 0, 0, 0]))

    # ---------- 3. 专门踩 k 的边界: a_i = k, k±1 密集 ----------
    for t in range(40):
        n = rng.randint(1, 8)
        m = rng.randint(1, 8)
        k = rng.randint(0, 6)
        vals = [max(0, k + d) for d in (-1, 0, 1)]
        a = [rng.choice(vals) for _ in range(n)]
        b = [rng.choice(vals) for _ in range(m)]
        cases.append(_case("tie_k_%02d" % t, n, m, k, a, b))

    # ---------- 4. 随机小数据（值域小、容易撞边界） ----------
    for t in range(300):
        n = rng.randint(1, 10)
        m = rng.randint(1, 10)
        k = rng.randint(0, 10)
        a = [rng.randint(0, 10) for _ in range(n)]
        b = [rng.randint(0, 10) for _ in range(m)]
        cases.append(_case("small_rand_%03d" % t, n, m, k, a, b))

    # ---------- 5. 随机中等数据（大值域） ----------
    for t in range(60):
        n = rng.randint(1, 200)
        m = rng.randint(1, 200)
        k = rng.choice([0, rng.randint(0, LIM), LIM])
        a = [rng.randint(0, LIM) for _ in range(n)]
        b = [rng.randint(0, LIM) for _ in range(m)]
        cases.append(_case("mid_rand_%03d" % t, n, m, k, a, b))

    # ---------- 6. 特殊性质 ----------
    # k=0
    for t in range(20):
        n = rng.randint(1, 50)
        m = rng.randint(1, 50)
        cases.append(_case("k0_%02d" % t, n, m, 0,
                           [rng.randint(0, LIM) for _ in range(n)],
                           [rng.randint(0, LIM) for _ in range(m)]))
    # k > max(a,b)  (子任务 13~14)
    for t in range(20):
        n = rng.randint(1, 50)
        m = rng.randint(1, 50)
        a = [rng.randint(0, 1000) for _ in range(n)]
        b = [rng.randint(0, 1000) for _ in range(m)]
        k = max(a + b) + rng.randint(1, 1000)
        cases.append(_case("k_gt_max_%02d" % t, n, m, k, a, b))
    # k < min(a,b)  (全部用规则二)
    for t in range(20):
        n = rng.randint(1, 50)
        m = rng.randint(1, 50)
        k = rng.randint(0, 100)
        a = [rng.randint(k + 1, LIM) for _ in range(n)]
        b = [rng.randint(k + 1, LIM) for _ in range(m)]
        cases.append(_case("k_lt_min_%02d" % t, n, m, k, a, b))
    # n == m  (子任务 15~16)
    for t in range(20):
        n = rng.randint(1, 60)
        cases.append(_case("n_eq_m_%02d" % t, n, n, rng.randint(0, LIM),
                           [rng.randint(0, LIM) for _ in range(n)],
                           [rng.randint(0, LIM) for _ in range(n)]))
    # n 与 m 相差 1（配对交错最紧的情况）
    for t in range(20):
        n = rng.randint(2, 60)
        m = n + rng.choice([-1, 1])
        cases.append(_case("diff1_%02d" % t, n, m, rng.randint(0, LIM),
                           [rng.randint(0, LIM) for _ in range(n)],
                           [rng.randint(0, LIM) for _ in range(m)]))

    # ---------- 7. 大规模 ----------
    n = m = 1000000
    cases.append(_case("max_n_eq_m", n, m, rng.randint(0, LIM),
                       [rng.randint(0, LIM) for _ in range(n)],
                       [rng.randint(0, LIM) for _ in range(m)]))
    n, m = 1000000, 1
    cases.append(_case("max_n_m1", n, m, rng.randint(0, LIM),
                       [rng.randint(0, LIM) for _ in range(n)],
                       [rng.randint(0, LIM) for _ in range(m)]))
    n, m = 1, 1000000
    cases.append(_case("n1_max_m", n, m, rng.randint(0, LIM),
                       [rng.randint(0, LIM) for _ in range(n)],
                       [rng.randint(0, LIM) for _ in range(m)]))

    return cases


if __name__ == "__main__":
    cs = generate_cases(seed=123)
    print("用例数:", len(cs))
    for c in cs:
        print("  ", c["name"], "len(input)=", len(c["input"]))
