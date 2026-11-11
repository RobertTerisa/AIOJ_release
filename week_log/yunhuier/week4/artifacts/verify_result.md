# 第 4 周验收记录（本机实测）

> 说明：以下数据为本机实测，仅代表本机环境，不代表 OJ 或 CI 环境。
> 环境：Windows 11 / g++ 8.1.0 / `-O2 -std=c++17 -Wall -Wextra` / Python 3.13.9
> 验收脚本：`artifacts/test_week4.py`（26 项，全部 PASS）

## 1. 编译

```
g++ -O2 -std=c++17 -Wall -Wextra -o generator/bin/sequence/seq_increasing.exe generator/cpp/sequence/seq_increasing.cpp
g++ -O2 -std=c++17 -Wall -Wextra -o generator/bin/sequence/seq_decreasing.exe generator/cpp/sequence/seq_decreasing.cpp
```

两个文件均**零警告**编译通过，产物各 150,179 B。

## 2. 参数与行为

| 参数 | 必填 | 说明 |
|---|---|---|
| `--seed` | 是 | 同一 seed 逐字节一致 |
| `--out` | 是 | 输出文件路径 |
| `--append` | 否 | 由路由传入；追加写 content，不写控制头 |
| `--array 长度,最小值,最大值` | 至少一个 | 可重复；每个输出一行，数值按 64 位处理 |

## 3. 检查项（26 项全 PASS）

| # | 检查项 | 结果 | 实测值 |
|---|---|---|---|
| 1 | 递增：退出码 0 | PASS | — |
| 2 | 递增：元素个数 == 长度 | PASS | 5 |
| 3 | 递增：严格单调 | PASS | `[2, 5, 7, 8, 9]` |
| 4 | 递增：落在 [min, max] | PASS | `[2, 5, 7, 8, 9]` ⊂ [1, 9] |
| 5 | 输出无 CR 字节（纯 LF） | PASS | 0 个 `\r` |
| 6 | 长度 0：输出一个空行 | PASS | `b'\n'` |
| 7 | 长度 1 且 min=max | PASS | `[7]` |
| 8 | 大值（上界 1e9）正常 | PASS | `518519100 … 518519345` |
| 9 | 满规模 1e6：个数正确 | PASS | 1,000,000 |
| 10 | 满规模 `--array 1000000,1,1000000` | PASS | 只能取 `1..1000000` 紧排列（区间恰好够用） |
| 11 | 多 `--array`：输出两行 | PASS | 2 行 |
| 12 | 递减：两行都严格递减且各在区间内 | PASS | `[76, 5, 4]` / `[290, 277, 272, 212]` |
| 13 | `--append`：追加成两行 | PASS | 2 行 |
| 14–15 | 同 seed 两次运行逐字节一致 | PASS | 两个 exe 各验一次 |
| 16 | 不同 seed 输出不同 | PASS | — |
| 17 | 1e6 元素耗时 < 1 s | PASS | 最快 137 ms |
| 18–19 | 1e6 元素严格单调 | PASS | 递增 148 ms / 递减 156 ms |
| 20–26 | 7 类错误输入均非 0 退出且写 stderr | PASS | 见下表 |

## 4. 错误码实测

| 场景 | 退出码 | stderr |
|---|---|---|
| 缺少 `--seed` | 1 | `[seq_increasing] 缺少 --seed` |
| 缺少 `--array` | 1 | `[seq_increasing] 至少需要一个 --array` |
| 缺少 `--out` | 1 | `[seq_increasing] 缺少 --out` |
| `--array` 格式错（`3,1`） | 1 | `[seq_increasing] --array 格式错误，应为 长度,最小值,最大值：3,1` |
| 最小值 > 最大值 | 1 | `[seq_increasing] --array 区间非法（最小值 > 最大值）：3,9,1` |
| 未识别参数 `--foo` | 1 | `[seq_increasing] 未识别参数: --foo` |
| 区间容纳不下（`5,1,3`） | 1 | `[seq_increasing] 区间容纳不下严格递增序列：需要跨度至少 4，实际只有 2` |

## 5. 路由识别验证（临时登记后已回滚）

`registry.py` 属框架作者文件，本次**未提交任何修改**。为确认 exe 能被路由识别，本地临时取消两行注释后执行：

```
python generator/router.py --list-generators
seq_random_small	sequence	missing	seq_random_small.exe
seq_increasing	sequence	ready	seq_increasing.exe
seq_decreasing	sequence	ready	seq_decreasing.exe
```

验证完毕立即还原，`git status --short` 只剩新增的源码目录：

```
?? generator/cpp/sequence/
```
