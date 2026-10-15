# Diff Runner 使用说明（Agent 版）

本文档给未来的 AI 助手使用。目标：不阅读 `diff_runner.py` 源码，也能正确调用对拍器；
并能根据聊天框中提供的题目要求，写出符合该题目输入格式和约束的数据生成器。

> **v2 更新**：优先使用第九节「工作区配置」。旧章节中的 `diff_runner/generators/`、`test_data/`、`evaluation_records/` 路径是旧版默认；新版推荐用工作区配置的 `generators_dir`、`data_dir`、`records_dir` 定位。

## 一、目录约定

所有命令都在项目根目录下执行，下面全部使用相对路径。

对拍器：

```text
diff_runner\diff_runner.py
```

评测记录输出目录：

```text
evaluation_records\
```

题目讨论、Debug、优化记录目录：

```text
discussion_records\
```

题目专用的数据生成器目录：

```text
<generators_dir>\
```

当前已有示例：

```text
diff_runner\sample_generator.py
diff_runner\sample_config.json
<generators_dir>\UVA10364_generator.py
```

## 二、对拍器原则与参数总表

- 对拍器本身不写死任何题目、用户代码或题解代码。
- 每次运行必须通过参数提供：
  - `--name`：题目名
  - `--problem-md`：题目 Markdown 路径
  - `--user`：用户代码路径
  - `--correct`：题解代码路径
  - 测试数据来源：`--in-dir` 或 `--generator`，二选一
  - `--out-dir`：评测记录输出目录；默认 `evaluation_records\<题目名>\`
- 对拍器会自动：
  1. 编译题解和用户代码；
  2. 逐组运行；
  3. 比较标准输出；
  4. 生成 Markdown 评测记录。

### 2.1 CLI 参数总表

| 参数 | 含义 | 默认值 |
|---|---|---|
| `--config` | JSON 配置文件 | 无 |
| `--name` | 题目名 | 题目 Markdown 文件名 |
| `--problem-md` | 题目 Markdown 文件 | 无 |
| `--user` | 用户代码 `.cpp` | 无 |
| `--correct` | 题解代码 `.cpp` | 无 |
| `--in-dir` | 包含 `.in` 文件的目录 | 无 |
| `--generator` | 数据生成器 Python 文件 | 无 |
| `--out-dir` | 评测记录输出目录 | `evaluation_records\<题目名>\` |
| `--timeout` | 单个测试用例的用户程序超时秒数 | `1` |
| `--compiler` | C++ 编译器 | `g++` |
| `--std` | C++ 标准 | `c++17` |
| `--seed` | 数据生成器随机种子 | 无 |
| `--submission` | 提交次数/记录编号 | 自动递增 |
| `--build-dir` | 编译临时目录 | 系统临时目录 |
| `--keep-build` | 保留编译和运行中间文件 | 否 |

### 2.2 数据来源二选一

`--in-dir` 和 `--generator` 必须二选一。

- 有 `IN` 文件夹：使用 `--in-dir`
- 需要动态生成数据：使用 `--generator`

## 三、用户自有输入方式：--in-dir

只需要 `.in` 文件，不需要 `.out`。对拍器已经内置 `.in` 读取和转换逻辑。

命令：

```powershell
python diff_runner\diff_runner.py `
  --name <题目名> `
  --problem-md <题目.md> `
  --user <用户代码.cpp> `
  --correct <题解代码.cpp> `
  --in-dir <包含 .in 文件的文件夹> `
  --timeout 10
```

对拍器会：

1. 读取 `--in-dir` 目录下所有 `.in` 文件；
2. 转换成对拍器内部使用的中间数据；
3. 自动保存到 `test_data\<题目名>\cases.json`；
4. 使用这些用例运行对拍。

注意：

- 用户只需要提供 `.in` 文件；
- 不需要了解对拍器的内部数据格式；
- 不需要提供 `.out` 文件；
- `.in` 文件内容必须是题目要求的完整标准输入。

## 四、数据生成器方式：--generator

适合随机对拍、构造数据、T > 1 数据、边界数据等。

### 4.1 生成器接口

生成器是一个独立的 Python 文件，必须定义：

```python
def generate_cases(seed=None):
    return [
        {"name": "用例名1", "input": "完整标准输入字符串1"},
        {"name": "用例名2", "input": "完整标准输入字符串2"},
    ]
```

要求：

- 返回 `list[dict]` 或 `list[str]`。
- 每个用例的 `input` 必须是**一次完整运行的标准输入**，包含：
  - `T`
  - 接下来每组数据的完整内容
- 生成的数据必须严格符合题目约束。
- 不要向标准输出打印调试信息；只返回用例列表。
- 使用 `seed` 保证随机数据可复现。

对拍器会自动调用：

```python
cases = generate_cases(seed=seed)
```

如果没有传 `--seed`，则 `seed=None`。

对拍器会把生成器返回的用例自动保存到：

```text
test_data\<题目名>\cases.json
```

### 4.2 调用模板

```powershell
python diff_runner\diff_runner.py `
  --name <题目名> `
  --problem-md <题目.md> `
  --user <用户代码.cpp> `
  --correct <题解代码.cpp> `
  --generator <generators_dir>\<题目名>_generator.py `
  --seed 123 `
  --timeout 10
```

例如 UVA10364：

```powershell
python diff_runner\diff_runner.py `
  --name UVA10364 `
  --problem-md UVA10364\UVA10364.md `
  --user UVA10364\UVA10364.cpp `
  --correct UVA10364\UVA10364_correct.cpp `
  --generator <generators_dir>\UVA10364_generator.py `
  --seed 123 `
  --timeout 10
```

## 五、任意题目的标准流程

每次在聊天框中拿到一道新题后，按以下步骤操作。

### 5.1 提取题目信息

阅读题目 Markdown，提取：

- 输入格式；
- 输出格式；
- `T` 是否存在，范围是多少；
- 每组的参数范围；
- 数值范围；
- 特殊边界条件；
- 是否需要多测。

### 5.2 选择数据来源

优先检查题目文件夹下是否有 `IN` 文件夹。

- 如果存在 `IN` 文件夹，并且里面有 `.in` 文件：
  - 使用 `--in-dir`；
  - 不需要再写生成器；
  - 对拍器会自动保存 `test_data\<题目名>\cases.json`。
- 如果 `IN` 不存在或里面没有 `.in` 文件：
  - 在 `<generators_dir>\` 下新建 `<题目名>_generator.py`；
  - 实现 `generate_cases(seed=None)`；
  - 对拍器会自动保存 `test_data\<题目名>\cases.json`。

### 5.3 生成器建议包含的数据

- 最小规模边界数据；
- 最大规模边界数据；
- 随机小数据；
- 随机大规模数据；
- 构造 `yes` 数据；
- 构造 `no` 数据；
- 多测 `T > 1` 数据，如果题目支持。

### 5.4 独立检查生成器

```powershell
python "<generators_dir>\<题目名>_generator.py"
```

### 5.5 运行对拍器

使用 `.in` 文件夹：

```powershell
python diff_runner\diff_runner.py --name <题目名> --problem-md <题目.md> --user <用户代码.cpp> --correct <题解代码.cpp> --in-dir <题目文件夹>\IN --timeout 10
```

使用生成器：

```powershell
python diff_runner\diff_runner.py --name <题目名> --problem-md <题目.md> --user <用户代码.cpp> --correct <题解代码.cpp> --generator <generators_dir>\<题目名>_generator.py --seed 123 --timeout 10
```

## 六、通用生成器模板

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import random


def _format_tests(tests):
    """tests 是多个用例的参数列表，按题目输入格式拼接。"""
    lines = [str(len(tests))]
    for item in tests:
        lines.append(" ".join(map(str, item)))   # 按题目真实格式修改这里
    return "\n".join(lines) + "\n"


def generate_cases(seed=None):
    rng = random.Random(seed)
    cases = []

    # 1. 固定边界样例
    cases.append({
        "name": "固定样例1",
        "input": "1\n4 1 1 1 1\n",
    })

    # 2. 随机小数据
    for i in range(1, 11):
        n = rng.randint(4, 10)          # 按题目范围修改
        a = [rng.randint(1, 10000) for _ in range(n)]
        cases.append({
            "name": f"随机小-{i:02d}",
            "input": "1\n" + str(n) + " " + " ".join(map(str, a)) + "\n",
        })

    # 3. 随机较大数据
    for i in range(1, 6):
        n = rng.randint(11, 20)         # 按题目范围修改
        a = [rng.randint(1, 10000) for _ in range(n)]
        cases.append({
            "name": f"随机大-{i:02d}",
            "input": "1\n" + str(n) + " " + " ".join(map(str, a)) + "\n",
        })

    # 4. 多测 T > 1
    t = 3
    lines = [str(t)]
    for _ in range(t):
        n = rng.randint(4, 10)
        a = [rng.randint(1, 10000) for _ in range(n)]
        lines.append(str(n) + " " + " ".join(map(str, a)))
    cases.append({
        "name": "多测-T3",
        "input": "\n".join(lines) + "\n",
    })

    return cases
```

注意：模板必须根据题目实际输入格式修改，不能直接套用。

## 七、配置文件方式

也可以把参数写入 JSON 配置文件，避免每次写长命令。

示例：

```json
{
  "name": "UVA10364",
  "problem_md": "../UVA10364/UVA10364.md",
  "user": "../UVA10364/UVA10364.cpp",
  "correct": "../UVA10364/UVA10364_correct.cpp",
  "generator": "generators/UVA10364_generator.py",
  "out_dir": "../evaluation_records/UVA10364",
  "timeout": 10,
  "compiler": "g++",
  "std": "c++17"
}
```

调用：

```powershell
python diff_runner\diff_runner.py --config diff_runner\sample_config.json
```

相对路径按配置文件所在目录解析。

配置文件支持以下键：

| 配置键 | 对应 CLI 参数 | 说明 |
|---|---|---|
| `name` | `--name` | 题目名 |
| `problem_md` | `--problem-md` | 题目 Markdown |
| `user` | `--user` | 用户代码 |
| `correct` | `--correct` | 题解代码 |
| `in_dir` | `--in-dir` | `.in` 文件夹 |
| `generator` | `--generator` | 数据生成器 |
| `out_dir` | `--out-dir` | 评测记录输出目录 |
| `timeout` | `--timeout` | 超时秒数 |
| `compiler` | `--compiler` | C++ 编译器 |
| `std` | `--std` | C++ 标准 |
| `seed` | `--seed` | 随机种子 |
| `submission` | `--submission` | 提交次数/记录编号 |
| `build_dir` | `--build-dir` | 编译临时目录 |

注意：

- `in_dir`、`generator` 也必须在配置中二选一。
- 命令行参数优先于配置文件。

## 八、评测记录与目录写入行为

每次运行自动生成评测记录，文件名会自动附带提交次数。

如果显式指定：

```powershell
--out-dir evaluation_records\<题目名>
```

则记录写入指定目录。

如果没有指定 `--out-dir`，默认输出目录就是：

```text
evaluation_records\<题目名>\
```

记录写入：

```text
evaluation_records\<题目名>\<题目名>_diff_<时间戳>_submission_<次数>.md
```

提交次数规则：

- 不指定 `--submission` 时，对拍器会统计当前输出目录里已有的同题记录，自动取下一个编号；
- 指定 `--submission N` 时，直接使用 `N`；
- 如果输出目录换了，编号会按新目录里的已有记录重新计算。

记录包含：

- 元信息；
- 统计表；
- 每组输入；
- 题解输出；
- 用户输出；
- 双方耗时；
- 状态；
- 备注。

### 8.1 三类目录的写入责任

| 内容 | 目录 | 谁来写 | 是否自动 |
|---|---|---|---|
| 测试数据 `cases.json` | `test_data\<题目名>\cases.json` | 对拍器 | `--in-dir` 或 `--generator` 时自动写 |
| 评测记录 | `evaluation_records\<题目名>\` | 对拍器 | 默认自动写；可用 `--out-dir` 覆盖 |
| 讨论、Debug、优化记录 | `discussion_records\<题目名>\` | Agent 手动整理 | 对拍器不会写 |

注意：

- 对拍器只负责测试数据和评测记录；
- 聊天记录、讨论过程、Debug 过程不会由对拍器自动保存；
- Agent 需要自己把讨论内容整理成 Markdown，写入 `discussion_records\<题目名>\`；
- 当前版本不主动检测 MLE；如果需要内存限制，需要额外扩展。

状态含义：

| 状态 | 含义 |
|---|---|
| AC | 输出一致 |
| WA | 输出不一致 |
| TLE | 用户程序超时 |
| RE | 用户程序运行错误 |
| 参考TLE | 题解程序超时 |
| 参考RE | 题解程序运行错误 |

## 九、工作区配置（v2，推荐）

现在优先使用工作区配置，不再把题目和产物都放在工具目录。

1. 工作区根目录放 `aioj.workspace.json`；模板为 `template.aioj.workspace.json`。
2. 配置字段：
   - `problems_dirs`：题目目录数组，按顺序查找第一个存在的 `<题号>/`；
   - `generators_dir`：生成器目录；
   - `data_dir`：`cases.json` 输出目录；
   - `records_dir`：评测记录输出目录；
   - `discussion_dir`：讨论整理目录；
   - `timeout`、`compiler`、`std`：默认编译/运行参数。
3. 推荐命令：

```powershell
python <工具目录>\diff_runner\diff_runner.py `
  --workspace-config <工作区>\aioj.workspace.json `
  --name <题号>
```

如果当前目录就是工作区根目录，可省略 `--workspace-config`。

4. 自动定位规则：
   - 题面：`<problems_dirs 命中的题目目录>/<题号>.md`
   - 用户代码：`<题号>.cpp`
   - 题解：`<题号>_correct.cpp`，找不到回退 `<题号>_solution.cpp`
   - 数据：优先 `<题号>/IN/*.in`；否则 `<generators_dir>/<题号>_generator.py`
5. 产物：
   - `<data_dir>/<题号>/cases.json`
   - `<records_dir>/<题号>/<题号>_diff_<时间戳>_submission_<次数>.md`
6. 新增可选参数：
   - `--dataset <名称>`：把测试数据和记录放进 `<题号>/<名称>/` 子目录；
   - `--cases-out <路径>`：显式指定 `cases.json` 输出路径，优先级高于 `--dataset`。
7. 旧命令（显式传 `--problem-md/--user/--correct/--in-dir/--generator`）仍然兼容。
