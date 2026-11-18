# AIOJ 数据生成器使用说明（Readme）

本目录（`generator/`）是 AIOJ 的**数据生成路由层**：把「题目约束 + 生成计划」变成可被对拍器直接读取的 `.in` 测试数据。

一句话概括：

```text
<题号>.generator.json（约束/格式/计划/样例）
        +  C++ 生成器（只追加数据值）
        +  <题号>.cutter.py（把数据流排版成题目要求的输入格式）
        ↓  router.py 调度
test_data/<题号>/*.in  ──>  diff_runner 对拍
```

---

## 1. 数据流与职责

```text
<题号>.generator.json
        │
        ▼
路由层（router.py）
   ├─ 绑定 T / n / m / 数组长度 / 变异数量
   ├─ 按 input_format 顺序把控制 token 写入 .in
   ├─ 循环调用 C++ 生成器，把 content 追加进同一个 .in
   ├─ 构造 job 对象（控制变量 + content 切片 + seed）
   ├─ 调 cutter(problem, job, text) → 最终 .in
   └─ 校验 → 样例回放 → 发布（逐文件替换）→ 写 manifest
        │
        ▼
test_data/<题号>/*.in + evaluation_records/<题号>/*manifest*.json
        │
        ▼
diff_runner：编译题目代码 → 读 .in → 逐组对拍 → 写评测记录
```

| 层 | 负责 | 不负责 |
|---|---|---|
| `<题号>.generator.json` | 约束、输入格式声明、生成计划、样例 | 执行逻辑 |
| 路由层（Python） | 绑定变量、写控制 token、调度生成器、调 cutter、校验、发布 | 不决定数据值 |
| C++ 生成器 | 把数据值追加到 `.in` | 不写控制变量、不排版、不写 JSON |
| `<题号>.cutter.py` | 按 `input_format` 把数据流排版成最终输入 | 不决定数据语义（n/m/长度/边集） |
| 校验器 | `.in` 的结构、图合规、行级结构 | 不判断是否符合题面（只能靠人） |
| 人 | 判断 JSON / cutter 是否与题面一致 | — |

---

## 2. 目录与产物

### 2.1 工具仓库（本仓库）

```text
AIOJ_release/
├── generator/
│   ├── Readme.md          # 本文
│   ├── router.py          # CLI 入口 + 编排
│   ├── models.py          # 数据模型与异常
│   ├── expr.py            # 安全表达式求值
│   ├── bind.py            # 变量约束与绑定
│   ├── registry.py        # 生成器注册表
│   ├── job.py             # job 对象 + 控制 token 写入
│   ├── executor.py        # 调用 C++ 生成器（追加 content）
│   ├── cutter.py          # cutter 加载与调用
│   ├── cutter_runner.py   # cutter 子进程执行器
│   ├── validate.py        # 最终 .in 校验 + 行级校验
│   ├── publish.py         # 发布 + manifest
│   └── cpp/
│       ├── common.h              # 公共参数解析 / 输出打开 / PRNG
│       └── sequence/             # 已实现（源码在库，exe 不入库）
│           ├── seq_random_small.cpp
│           ├── seq_random_large.cpp
│           ├── seq_increasing.cpp
│           ├── seq_decreasing.cpp
│           └── seq_all_equal.cpp
└── diff_runner/
    └── diff_runner.py
```

编译产物（不入库，`.gitignore` 忽略 `*.exe`）：

```text
generator/bin/
├── sequence/   # seq_random_small.exe, seq_increasing.exe, ...
├── graph/      # 预留
└── string/     # 预留
```

> 上表是**当前实际结构**（2026-11-12 核对）。以下为**规划但尚未创建**，不要当成现状：
>
> - `generator/cpp/<其它模式>/`：图论、字符串生成器源码尚未落地；
> - `generator/tests/`：单元测试 / 端到端测试目录尚未创建；
> - `generator/bin/<kind>/`：编译产物目录，`*.exe` 被 `.gitignore` 忽略，需要自行编译生成。
>
> **实际可用以 `generator/registry.py` 的 `GENERATORS` 为准**：目前只有 `seq_random_small` 处于注册状态，`seq_random_large` / `seq_increasing` / `seq_decreasing` / `seq_all_equal` 的源码已存在但注册项仍是注释状态。

### 2.2 题目目录（工作区）

```text
<problems_dirs 之一>/<题号>/
├── <题号>.md                # 题面
├── <题号>.cpp               # 用户代码
├── <题号>_correct.cpp       # 题解（找不到回退 <题号>_solution.cpp）
├── <题号>.generator.json    # schema_version = 2
├── <题号>.cutter.py         # 每题切割脚本
└── IN/                      # 可选：手写 .in；存在时优先于 router
```

### 2.3 产物落点

```text
test_data/<题号>/*.in                                          # 最终测试数据
evaluation_records/<题号>/<题号>_generation_manifest_<ts>.json  # 生成 manifest
evaluation_records/<题号>/<题号>_diff_<ts>_submission_<n>.md    # 对拍记录
```

临时目录 `test_data/<题号>/.tmp_<run_seed>/` 带标记文件 `.router_tmp`：

- 成功发布后清理当前临时目录（清理失败只打印 `[警告]`，不影响退出码）；
- 任一步失败时保留当前临时目录，并在 stderr 打印 `[router error] 临时目录已保留: <路径>`；
- 下次启动只清理**带 `.router_tmp` 标记且不是当前 run_seed** 的历史 `.tmp_*`；无标记的目录一律不碰；
- 当前 run_seed 的 `.tmp_<seed>` 若已存在但缺标记，按路径冲突处理，拒绝删除并返回 `2`。

---

## 3. 快速开始

1. **写 spec**：读 `<题号>.md`，起草 `<题号>.generator.json`（约束 + 输入格式 + 生成计划 + 样例）。
2. **写 cutter**：同目录写 `<题号>.cutter.py`，实现 `cut(problem, job, text) -> str`。
3. **确认样例**：把题面样例填进 spec 的 `samples[]`（`job` / `text` / `input` / `confirmed`），与人对齐后再生成大规模数据。
4. **跑对拍**：

```powershell
python <工具目录>/diff_runner/diff_runner.py `
  --workspace-config aioj.workspace.json `
  --name <题号>
```

没有 `IN/` 时，对拍器会自动用本目录的 `router.py` + `<题号>.generator.json` 生成数据。

也可以单独跑路由：

```powershell
python <工具目录>/generator/router.py `
  --spec <题目目录>/<题号>.generator.json `
  --output-dir <工作区>/test_data/<题号> `
  --seed 123 `
  --manifest <工作区>/evaluation_records/<题号>/manifest.json
```

---

## 4. `<题号>.generator.json`（v2）

### 4.1 完整示例（序列题）

```json
{
  "schema_version": 2,
  "problem_id": "P1234",
  "kind": "sequence",
  "meta": {
    "source": "Luogu",
    "time_limit_ms": 1000,
    "constraints_source": "P1234.md",
    "confirmed_by_human": true
  },
  "constraints": {
    "variables": { "n": { "min": 1, "max": 100000 } },
    "arrays": [
      { "name": "A", "length": "n", "min": 1, "max": 1000000000 }
    ]
  },
  "input_format": {
    "summary": "第一行 T；每组第一行 n；随后一行 n 个整数",
    "line_sensitive": false,
    "encoding": "utf-8",
    "case_count": { "emit": "explicit", "name": "T" },
    "case": {
      "items": [
        { "emit": "scalar", "name": "n", "source": "control" },
        { "emit": "array",  "name": "A", "source": "content" }
      ]
    }
  },
  "generation": {
    "multi_case": { "T": { "min": 1, "max": 5 } },
    "cases": [
      { "generator": "seq_random_small", "repeat": 5, "scale": "small" },
      { "generator": "seq_random_small", "repeat": 2, "scale": "max",
        "bind": { "n": 100000 } }
    ]
  },
  "cutter": {
    "path": "P1234.cutter.py",
    "entry": "cut",
    "timeout_s": 30,
    "max_output_bytes": 104857600
  },
  "samples": [
    {
      "name": "sample1",
      "job": {
        "schema_version": 1,
        "test_point_id": "P1234__sample",
        "problem_id": "P1234",
        "generator": "sample",
        "run_seed": 0,
        "stream": "tokens",
        "groups": [
          { "index": 1, "seed": 0, "attempt": 1,
            "control": { "n": 3 },
            "content": [ { "name": "A", "type": "int_array", "count": 3 } ] }
        ]
      },
      "text": "1\n3 5 6 7\n",
      "input": "1\n3 5 6 7\n",
      "confirmed": true
    }
  ]
}
```

### 4.2 顶层字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `schema_version` | 是 | 固定 `2`；`1` 会报错并提示迁移 |
| `problem_id` | 是 | 题号 |
| `kind` | 是 | `sequence` / `graph` / `string`（**当前只有 `sequence` 有可用生成器**） |
| `meta.constraints_source` | 是 | 约束来源（通常是 `<题号>.md`） |
| `meta.confirmed_by_human` | 是 | 人是否已确认格式与约束 |
| `constraints` | 是 | 数据语义与校验规则 |
| `input_format` | 是 | 严格输入格式声明 |
| `generation` | 是 | 生成计划 |
| `cutter` | 是 | 每题切割脚本 |
| `samples` | 是 | 样例回放数据 |

> 未列出的字段会被 `load_spec()` 拒绝（不静默忽略）。

### 4.3 `constraints`（序列）

```json
"constraints": {
  "variables": { "n": { "min": 1, "max": 100000 } },
  "arrays": [
    { "name": "A", "length": "n", "min": 1, "max": 1000000000 }
  ]
}
```

| 字段 | 说明 |
|---|---|
| `variables.<name>` | 变量及其取值范围；`min` / `max` 支持整数或表达式 |
| `arrays[].name` | 数组名（仅用于 job 的 `content` 切片） |
| `arrays[].length` | 长度，整数或表达式（通常是某个变量） |
| `arrays[].min` / `max` | 元素取值范围，整数或表达式 |

### 4.4 `input_format`

| 字段 | 取值 | 说明 |
|---|---|---|
| `summary` | 字符串 | 给人/LLM 看的一句话 |
| `line_sensitive` | bool | 只有 `getline`、含空格字符串之类的题才为 `true` |
| `encoding` | `utf-8` | 固定 |
| `case_count.emit` | `explicit` / `none` | 是否输出 `T` |
| `case.items[].emit` | `scalar` / `array` / `graph` / `string` | 输出单元 |
| `case.items[].source` | `control` / `content` | 来自 job 的控制变量，还是来自数据流 |

`emit = graph` 时还可带 `form`（`edge_list` / `adjacency_list`）、`k_mode`、`self_loop`、`neighbor_order`；`graph` 的语义字段只在 `constraints.graph` 出现一次。

### 4.5 `generation`

| 字段 | 说明 |
|---|---|
| `multi_case.T` | 每个测试点的组数范围，支持 `min` / `max` 或整数 |
| `cases[]` | 一个测试点一条规则；**可省略**（启用 `coverage` 时可只写 `coverage`）。同一生成器允许写多条，一条都不会被删 |
| `cases[].generator` | **注册表里的生成器 id**（不含 `.exe`） |
| `cases[].repeat` | 该规则重复生成几个测试点 |
| `cases[].scale` | `min` / `max` / `small` / `medium` / `random` |
| `cases[].bind` | 覆盖某个变量的取值或范围（如 `"base_m": "n-1"`） |
| `cases[].mutation` | 图论变异（`duplicate` / `self_loop`），序列题不用 |
| `cases[].name` | 用例用途标签（如 `max-scale`）。只做标记：不进 `test_point_id`、不进 `.in` 文件名、不进 `derive_seed()`、不参与唯一性统计；缺省为空串，写进 manifest 的 `files[].name` |
| `coverage` | **可选**。开启后「跑什么」从白名单（`cases[]`）改为「默认全跑 + 否决清单」：候选 = 注册表中 `kind` 相符且 exe 存在的生成器，逐条 include，再按 `exclude[]` 剔除；未出现在 `cases[]` 的候选按 `default_plan` 补规则。不写 `coverage` 时保持旧白名单行为，并打印 `[coverage][legacy] 白名单模式，不保证全覆盖` |
| `coverage.target_groups` | 目标 `.in` 份数。`default_plan.repeat = "auto"` 时**必填**（普通/图论 50，搜索/DFS/BFS/回溯 20）；缺失直接 `[router error] code=invalid-coverage` 退 2，不设缺省值 |
| `coverage.default_plan` | 未出现在 `cases[]` 的候选使用的计划，缺省 `{"scale": "random", "repeat": "auto"}` |
| `coverage.default_plan.scale` | 取值同 `cases[].scale` |
| `coverage.default_plan.repeat` | 正整数或 `"auto"`。`"auto"` 只补差额、均分、余数给前几名，组数不超 `target_groups`（人工条目已凑满时每个候选仍跑 1 次，故可能略超） |
| `coverage.exclude[]` | 否决清单，缺省为空 = 候选全集全部运行 |
| `coverage.exclude[].generator` | 必须是已注册 id：未注册报 `code=unsupported-generator` 退 2；同一 id 重复条目报 `code=invalid-coverage` |
| `coverage.exclude[].reason` | 必填，非空字符串。每次「减法」都必须给理由，进日志与 manifest |
| `coverage.exclude[].reason_code` | 可选，只用于分类：`impossible_by_semantics` / `not_applicable` / `redundant` / `other` |
| `coverage.exclude[].evidence` | 可选 `{file, quote}`。给了 `quote` 就在 `file`（默认 `<题号>.md`）里做子串匹配，**匹配不到只提示、不报错** |

### 4.6 `samples[]`（样例回放）

每条样例必须四件套齐全：

| 字段 | 说明 |
|---|---|
| `job` | 该样例对应的临时 job 对象 |
| `text` | 进入 cutter 之前的原始数据流文本 |
| `input` | 题面样例输入原文（cutter 输出必须与之一致） |
| `confirmed` | 必须为 `true`；缺失或为 `false` 时路由直接报错 |

---

## 5. C++ 生成器参数规格 ★

### 5.1 公共约定

- **每个数据模式一个独立可执行文件**，不用 `--pattern` 之类的开关切换模式；
- 可执行文件放在 `generator/bin/<kind>/<生成器文件名>.exe`；
- 注册表 `GENERATORS` 里写 `Gen(id, kind, exe)`，`exe` 是文件名（含 `.exe`）；
- `<题号>.generator.json` 的 `generation.cases[].generator` 写 **id**（不含 `.exe`）；
- 公共参数：`--seed`、`--out`、`--append`；
- **只追加 content 值**：不写 `T`、不写 `n`/`m`、不写 JSON、不写控制头；
- 输出 UTF-8、空白分隔、**行末 `\n`（LF，不使用 CRLF）**；
- **禁止 `time()` / `random_device()` 等非确定性来源**：同一 `--seed` 必须产出完全相同的字节；
- 退出码 `0` 表示成功，非 `0` 表示失败（错误信息写 stderr）。

### 5.2 序列生成器参数（当前支持）

目前只有一个已实现的模式：`seq_random_small`（小范围随机）。

```powershell
seq_random_small.exe --seed 123 --out case_001.in --append --array 10,1,60
seq_random_small.exe --seed 456 --out case_001.in --append --array 10,1,60 --array 20,1,1000000000
```

| 参数 | 必填 | 取值 | 说明 |
|---|---|---|---|
| `--seed` | 是 | 64 位整数 | 该组的 `sub_seed`。**必须完全决定输出**；相同 seed 必须逐字节一致 |
| `--out` | 是 | 文件路径 | 输出文件；`--append` 时追加，否则截断 |
| `--append` | 否 | 无值标志 | 追加模式。路由**总是**传这个参数，因为控制 token 已经先写进同一个文件 |
| `--array` | 是（至少 1 个，可重复） | `长度,最小值,最大值` | 对应 `constraints.arrays` 里的一个数组，**顺序与 spec 中的 `arrays` 一致** |

`--array` 的三个数字：

| 位置 | 含义 | 合法值 |
|---|---|---|
| 1 | 长度（本组要输出的元素个数） | `>= 0` |
| 2 | 最小值 | `<= 最大值` |
| 3 | 最大值 | `>= 最小值` |

**输出语义**

- 每个 `--array` 输出**一行**，恰好「长度」个整数，元素取值落在闭区间 `[最小值, 最大值]`；
- 多个 `--array` 按出现顺序**各占一行**；
- 行内元素以单个空格分隔；行末有换行；
- 整份输出末尾必须有换行（保证与路由写入的控制 token 拼在一起后仍是合法 token 流）；
- 数值范围按 64 位整数处理（例如 `1000000000` 这类大值没问题）。

**示例**

```text
输入参数：--seed 123 --out a.in --append --array 5,1,9 --array 3,10,20
a.in 内容（示意）：
3 6 9 7 2
12 20 13
```

**退出码与错误**

| 情况 | 退出码 | 表现 |
|---|---|---|
| 正常 | `0` | 追加写入完成 |
| 缺 `--seed` / `--out` / `--array` | 非 `0` | stderr 说明缺少什么 |
| `--array` 格式错（不是三段整数） | 非 `0` | stderr 指出原始参数 |
| `最小值 > 最大值` | 非 `0` | stderr 说明区间非法 |
| 出现未识别参数 | 非 `0` | stderr 指出参数名 |
| 打不开输出文件 | 非 `0` | stderr 说明路径 |

路由侧遇到非 `0` 会报 `生成器失败: <exe> (exit=N)`，并附上 **stderr 或 stdout 其中一路**（优先 stderr，取不到才用 stdout）的尾部，最多 2000 字符；评测在**编译前**终止。

### 5.3 参数是怎么算出来的（spec → argv）

| 参数 | 来源 |
|---|---|
| `--seed` | `sub_seed = H(run_seed, generator, ordinal, group_index, attempt)`，由路由派生；`ordinal` 是规则序号（`repeat` 的每次展开各占一个） |
| `--out` | 当前测试点的临时 `.in` 路径 |
| `--append` | 路由固定传入 |
| `--array` | 每个 `constraints.arrays[]` 一项，取值为 `绑定出的 length, min, max` |

也就是说：**生成器不需要知道题号、不需要知道 `T`、不需要知道第几组**——它只按 `--array` 描述生成一组值即可。

### 5.4 手写生成器检查清单

- [ ] 只写 content 值，不写 `T` / `n` / `m` / 任何控制变量；
- [ ] 不写 JSON、不写注释行、不写额外空行之外的格式；
- [ ] 行末用 `\n`（Windows 上请用二进制方式打开文件，避免被转成 `\r\n`）；
- [ ] 同一 `--seed` 两次运行输出逐字节一致；
- [ ] 不使用 `time()` / `random_device()` / 环境变量等外部随机；
- [ ] 参数非法时返回非 `0`，并把原因写到 stderr；
- [ ] 处理大值（`10^9`）与边界（长度 0 / 最小=最大）；
- [ ] 编译产物放到 `generator/bin/<kind>/`，并在 `registry.py` 登记。

### 5.5 注册新生成器

1. 把 `.cpp` 放到 `generator/cpp/<kind>/`，`#include "../common.h"`；
2. 编译到 `generator/bin/<kind>/<名字>.exe`：

```powershell
g++ -O2 -std=c++17 -Wall -Wextra -o generator/bin/sequence/seq_increasing.exe generator/cpp/sequence/seq_increasing.cpp
```

3. 在 `generator/registry.py` 的 `GENERATORS` 里加一行（**未编译完成前保持注释**）：

```python
Gen("seq_increasing", "sequence", "seq_increasing.exe"),
```

4. 用 `python generator/router.py --list-generators` 确认状态变成 `ready`（`missing` 表示 exe 还没编译或路径不对）。

### 5.6 `cpp/common.h` 提供什么

`common.h` 是公共头，只处理与模式无关的部分：

| 符号 | 作用 |
|---|---|
| `using i64 = long long` | 统一 64 位整数 |
| `struct Args { seed; out; append; rest; }` | 公共参数解析结果；`rest` 按顺序保留未识别参数 |
| `parse_common(argc, argv)` | 解析 `--seed` / `--out` / `--append`，其余进 `rest` |
| `open_out(args)` | 以追加/截断方式打开输出文件（**二进制模式，避免 CRLF**） |
| `make_rng(seed)` | 由 seed 构造 `mt19937_64`（确定性） |

模式自己的参数（如 `--array`）从 `Args::rest` 里取，例如按 `--array` + 参数值成对扫描。

### 5.7 暂未支持：图论 / 字符串生成器

`constraints.graph`、`constraints.strings` 与对应的绑定逻辑、校验逻辑已经在代码里就位，但**生成器尚未实现、也未注册**，因此目前：

- `<题号>.generator.json` 的 `kind` 只能真正跑通 `sequence`；
- 设计预留的参数（仅记录，**当前没有可用 exe**）：
  - 图论：`--n` `--base-m` `--dup` `--loop` `--directed` `--weighted` `--vertex-base` `--simple` `--connected` `--weight-min` `--weight-max`；
  - 字符串：`--count` `--lengths` `--alphabet`。

---

## 6. cutter 接口

```python
def cut(problem: dict, job: dict, text: str) -> str: ...
```

| 项 | 说明 |
|---|---|
| `problem` | 题目 JSON（即 `<题号>.generator.json` 的内容） |
| `job` | 该测试点的临时 job 对象（控制变量 + content 切片 + seed） |
| `text` | 进入 cutter 之前的数据流文本 |
| 返回值 | 最终 `.in` 的完整文本（必须是 `str`） |

约束与边界：

- 纯函数、确定性：同样输入必须产出同样输出；
- 不读网络、不写文件、不依赖当前时间；
- 只允许标准库；
- 在**子进程**中运行，带超时（`cutter.timeout_s`）与输出大小上限（`cutter.max_output_bytes`）；
- 必须通过样例回放（见 §11）。

职责边界：

- cutter **决定**：token 顺序、换行、`T` 的位置、邻接表派生、下标偏移；
- cutter **不决定**：`n`、`m`、数组长度、边集内容——这些来自 `job.groups[].control` 与 `.in` 的 content。

---

## 7. `.in`、job 对象与写入顺序

### 7.1 `.in` 里只有测试数据

- 一个测试点一个 `.in`；
- 只有题目要求的 token，不写 JSON、不写控制头、不写 seed；
- 控制变量（`T`、`n`、长度）本身就是题目输入的一部分，按 `input_format` 顺序作为普通 token 写入；
- 最终 `.in` 可以直接交给题解/用户程序读取。

### 7.2 job 对象（临时，不持久化到 `test_data`）

```json
{
  "schema_version": 1,
  "test_point_id": "P1234__seq_random_small__001",
  "problem_id": "P1234",
  "generator": "seq_random_small",
  "run_seed": 20260101,
  "stream": "tokens",
  "groups": [
    {
      "index": 1,
      "seed": 3847291,
      "attempt": 1,
      "control": { "n": 5 },
      "content": [ { "name": "A", "type": "int_array", "count": 5 } ]
    }
  ]
}
```

| 字段 | 说明 |
|---|---|
| `stream` | `tokens` 或 `lines`（字符串题按行） |
| `groups[].seed` | 该组派生的 `sub_seed` |
| `groups[].attempt` | 第几次尝试成功 |
| `groups[].control` | 该组控制变量 |
| `groups[].content` | 该组 content 切片（名字 / 类型 / 数量 / 宽度） |

### 7.3 写入顺序

```text
1. 路由写 T（如果 case_count.emit = explicit）
2. 对每组 g：
     a. 路由按 input_format 顺序写该组控制 token
     b. 调生成器 --append，追加该组 content
3. 全部组写完 → 得到「原始数据流」
4. cutter 排版 → 最终 .in
```

> 约束：当前实现假设**一个 group 内控制 token 位于 content 之前**。若题目是「控制—内容—控制—内容」结构，需要 cutter 重排（见 §6）。

---

## 8. 多组样例（T）

- `T` 是**文件级**参数：一个 `.in` 里有 `T` 组；
- 路由先绑定全部组的控制变量，再按组循环写文件；
- 最终 token 顺序：`T → 第 1 组 → 第 2 组 → …`；
- 一个测试点一个 `.in`；测试点个数由 `generation.cases[].repeat` 控制；
- 总组数 = 所有测试点的 `T` 之和。

---

## 9. 变量绑定与 scale

- `constraints.variables` 提供基础范围，`generation.cases[].bind` 提供该用例的覆盖或固定值；
- `min` / `max` 支持整数与表达式；表达式只允许四则运算、`//`、`%`、`min`、`max`、`isqrt`，不做属性访问、不允许导入、不允许未绑定变量；
- 绑定顺序：解析依赖 → 拓扑排序 → 逐个 `choose(lo, hi, scale)`；
- `lo > hi` 一律报 `BindError`。

| `scale` | 行为 |
|---|---|
| `min` | 取 `lo` |
| `max` | 取 `hi` |
| `small` | `[lo, lo + (hi - lo) // 10]` |
| `medium` | `[lo, lo + (hi - lo) // 2]` |
| `random` | `[lo, hi]` |

图论额外规则（生成器尚未实现，绑定逻辑已就位）：`simple` 时 `hi` 收到容量上限、`connected` 时 `lo` 抬到 `n-1`、变异数量不能使 `base_m < 0`。

---

## 10. 校验与重试

两道检查点：

| 检查点 | 内容 | 失败处理 |
|---|---|---|
| 数据流级 | `content[].count` 与实际 token 数一致、控制 token 与控制值一致、`T` 与组数一致 | 内容性错误**可重试**（最多 3 次），失败 attempt 只打 `[retry]` 日志，不写入 job / manifest |
| 最终 `.in` 级 | 通用 token 结构、图合规、行级结构 | 一律 fatal，不重试 |

最终 `.in` 的检查包括：

- 控制 token 必须与 job 一致；
- content token 数必须与 `job.groups[].content` 一致；
- 不能有剩余 token；
- `line_sensitive = true` 时再叠加行级检查（每行 token 数）。

---

## 11. 样例回放

- `samples[]` 保存题面样例输入 + 固定的 `job` + `text`；
- 路由调用 cutter，比较 cutter 输出与 `samples[].input`；
- `line_sensitive = false` 按 token 比较，`true` 按行比较；
- 不一致：打印失败并**终止，不发布**；
- 缺 `job` / `text` / `input` 或 `confirmed != true`：直接报错，不跳过。

> 样例回放只证明「同一份数据，cutter 的输出和题面样例输入一致」。**程序输出是否正确由对拍器负责**，不在数据生成器里判断。

---

## 12. seed 策略

- `run_seed` 一个测试点批次一个，由对拍器生成（也可用 `--seed` 显式覆盖）；
- 每组 `sub_seed = H(run_seed, generator, ordinal, group_index, attempt)`，`ordinal` 是规则序号（`repeat` 的每次展开各占一个）；
- 生成器只接收 `sub_seed`；
- `run_seed` 写入 manifest 与评测记录；
- 成功组的 `sub_seed` / `attempt` 写入 job 对象；失败 attempt 只打日志；
- 最终 `.in` 落盘保留，WA 时可直接复现。

`ordinal` 进哈希解决的是「同一 `generator` 的多条规则 / 多次 `repeat` 拿到同一个种子」：现在它们是不同的 `sub_seed`，绑定出的数值也各自独立。

> 种子不同不保证数据不同：可行域小（判断题、`n<=10`、`bind` 写死、形态生成器只由 `n` 决定）时，种子不同而数据相同是必然的。这正是唯一性只告警、不阻塞的原因。

唯一性可见性：

- 发布前 router 打印 `[verify] N 份数据 / M 份互不相同`；`M < N` 时打印 `[warn] 存在 N-M 份重复数据，已放行（不阻塞发布）`，并用 `[warn] 重复: a.in == b.in …` 逐组列出；
- 只告警：不改退出码、不阻塞发布、**不写 manifest**；可行域小于组数的题出现重复属正常；
- 通道：`[verify]` 走 stdout，`[warn]` 走 stderr（两者都不是错误）；
- 这两行只**直接运行 `generator/router.py`** 时可见；经 `diff_runner` 运行时被丢弃（成功路径不转述 router 输出，见 T-050）。

---

## 13. 发布与 manifest

1. 全部 `.in` 先生成到 `test_data/<题号>/.tmp_<run_seed>/`；
2. 全部校验通过（含样例回放）；
3. 写 manifest，`status = "ready"`；
4. 逐文件 `os.replace` 到 `test_data/<题号>/`；
5. 全部成功 → `status = "ok"`，清理临时目录；
6. 中途失败 → `status = "failed"`，**保留临时目录**并打印路径，返回非 0。

临时目录的生命周期：

- 创建时写入标记文件 `.tmp_<run_seed>/.router_tmp`，用于区分“router 建的目录”和用户自己的目录；
- 成功发布后清理当前目录；清理失败打印 `[警告] 临时目录清理失败（数据已发布）: …`，退出码仍为 `0`；
- 生成 / 样例回放 / 发布任一步失败时保留当前目录，并在 stderr 打印 `[router error] 临时目录已保留: <路径>`（同一轮只打印一次）；
- 启动时自动清理历史 `.tmp_*`，但**只删带 `.router_tmp` 标记且非当前 run_seed 的目录**；`symlink`/junction 与无标记目录一律不碰（清理失败只打印 `[警告] 历史临时目录清理失败: …`）；
- 同一 `--seed` 重跑：带标记的旧目录先删后建；缺标记则判定为路径冲突，打印 `[router error] 临时目录路径已存在且缺少标记，拒绝删除: <路径>` 并返回 `2`。

manifest 示例：

```json
{
  "schema_version": 2,
  "problem_id": "P1234",
  "run_seed": 20260101,
  "status": "ok",
  "files": [
    { "in": "P1234__seq_random_small__001.in", "sha256": "……", "groups": 3 }
  ]
}
```

| `status` | 含义 |
|---|---|
| `ready` | 已生成并校验，尚未发布完成 |
| `ok` | 全部发布成功 |
| `failed` | 发布失败，临时目录保留 |

字段口径：**既有字段不变，新增两个可选字段**——`files[].name`（用例用途标签，来自 `generation.cases[].name`，缺省 `""`）与顶层 `coverage`（覆盖率账本）。`schema_version` 仍然为 `2`；唯一性只体现在日志，**不进 manifest**。

| 字段 | 谁写 | 是否必填 | 对拍器是否读 |
|---|---|---|---|
| `schema_version` / `problem_id` / `run_seed` / `status` / `files[].in` / `files[].sha256` | 既有 | 是 | 读（`load_cases_from_manifest()` 强校验） |
| `files[].groups` | 既有 | 是 | 不读 |
| `files[].name` | 新增 | 否（缺省 `""`） | 不读 |
| `coverage` | 新增（仅 coverage 模式写；legacy 模式不写） | 否 | 不读 |

coverage 模式下的 manifest 追加段（`schema_version` 仍为 2）：

```json
"coverage": {
  "mode": "exhaustive",
  "target_groups": 50,
  "effective_repeat": null,
  "planned_repeats": { "seq_random_large": 17, "seq_increasing": 16, "seq_decreasing": 16 },
  "manual_rules": 1,
  "planned_rules": 3,
  "groups": 50,
  "candidates": ["seq_random_small", "seq_random_large", "seq_increasing",
                 "seq_decreasing", "seq_all_equal"],
  "covered": ["seq_decreasing", "seq_increasing", "seq_random_large", "seq_random_small"],
  "excluded": [{ "generator": "seq_all_equal", "reason": "题面要求元素两两不同",
                 "reason_code": "impossible_by_semantics" }],
  "skipped": []
}
```

- 各候选 `repeat` 不同时 `effective_repeat` 为 `null`，靠 `planned_repeats` 复现这一轮为什么是 N 组；
- 账本两行汇总（`[coverage] 候选 … = 覆盖 … + 否决 … + 跳过 …` / `[coverage] 规则 … = 人工 … + 默认计划 …`）走 **stdout**；`[coverage][exclude]` / `[skip]` / `[plan]` / `[skipped]` / `[evidence][warn]` 走 **stderr**。

> 已知限制：MVP 不做目录级原子替换，也不删除 `test_data/<题号>/` 里上一轮的旧 `.in`。
> 旧 `.in` 仍保留，但 **router 模式下对拍器不再目录扫描**：只加载本次 manifest `files[].in` 列出的文件，旧文件自然不参与评测。
> 非 `router.py` 的外部入口（如 `xxx_router.py`、原生 exe）没有 manifest，仍按目录扫描，可能把旧 `.in` 一起读入；此时对拍器会打印 `[警告]`。

---

## 14. router 命令行

```powershell
python generator/router.py --spec <题号>.generator.json --output-dir <目录> [选项]
```

| 参数 | 说明 |
|---|---|
| `--spec` / `--params` | `<题号>.generator.json` 路径（两个名字等价） |
| `--output-dir` | `.in` 输出目录（通常是 `test_data/<题号>`） |
| `--seed` | 指定 `run_seed`；不传则随机生成 |
| `--generator-root` | 生成器根目录；默认 `generator/bin`，期望 `<root>/<kind>/<exe>` |
| `--only` | 只跑指定 id 的生成器规则；未知 id 在生成前报错 |
| `--timeout` | 单个生成器调用超时秒数（默认 60） |
| `--manifest` | manifest 输出路径 |
| `--list-generators` | 只打印注册表（可单独运行，不需要 `--spec` / `--output-dir`） |

退出码：

| 退出码 | 覆盖范围 |
|---|---|
| `0` | `--list-generators` 正常输出；或生成 + 校验 + 发布 + manifest 全部成功 |
| `1` | 发布失败（`PublishError`，manifest 写为 `status=failed`，临时目录保留） |
| `2` | 其余失败：缺 `--spec` / `--output-dir`、spec 非法（`DiagnosticError` 各 `code`）、绑定失败、生成器未注册 / 未编译、生成失败、样例回放失败、重试耗尽、cutter 失败、`--only` 无匹配、临时目录路径冲突、当前临时目录清理失败、manifest 写入失败（数据已发布）、系统 `OSError` |

补充说明：

- `2` 是"参数 / 规格 / 生成失败"的总汇，**不区分轻重**；要区分具体原因请看 `[router error] code=` 行或文本；
- 成功发布后清理临时目录失败只打印 `[警告]`，**不改变退出码**（仍为 `0`）；
- 本轮未新增任何数字退出码。

`[router error]` 的两种形态：

- **结构化多行**（`DiagnosticError`）：首行 `code=<稳定错误码>`，随后 `message=<说明>`、若干 `字段名=值`、末尾 `hint=<下一步该做什么>`；
- **单行**（其它 `RouterError`，如规格 JSON 解析失败）：沿用旧文案 `[router error] <说明>`。

结构化错误码见第 16 节。退出码不因错误码变化：仍是上述三个数字，未新增。

---

## 15. 与 diff_runner 的衔接

`diff_runner` 新增了 4 个参数：`--generator-exe`、`--generator-params`、`--generator-timeout`（默认 600）、`--no-cases-json`。

数据来源优先级（只在**没有显式指定**数据来源时生效）：

```text
显式 CLI（--cases / --in-dir / --generator / --generator-exe）
  > <题目目录>/IN/*.in
  > 工具目录/generator/router.py + <题目目录>/<题号>.generator.json
  > <题目目录>/<题号>_generator.exe
  > <generators_dir>/<题号>_generator.py
```

规则：

- **显式 CLI 覆盖 IN**；默认行为仍是「有 IN 优先」；
- 默认 router 只有 `router.py` 与 `<题号>.generator.json` **同时存在**才启用；
- router 一旦启用但报错 → **直接停止，不静默回退**；
- 选中的数据源会打印 `[data-source] ...`；
- router 模式**不写 `cases.json`**；入口是 `router.py` 时只读本次 manifest `files[].in`（`status` 必须为 `ok`、`run_seed` 必须一致），不是目录扫描；
- 入口是其它外部生成器时仍目录扫描 `<data_dir>/<题号>/*.in` 并打印 `[警告]`；
- manifest 缺失 / `status` 非 `ok` / `run_seed` 不匹配 / `files[].in` 非法或不存在 / `sha256` 不符 → 一律按 `[数据生成失败]` 终止，不回退目录扫描；
- 评测记录的元信息会带上「数据来源 / 生成入口 / run_seed / manifest 路径」。

---

## 16. 报错与排查

| 输出 | 含义 | 处理 |
|---|---|---|
| `[data-source] ...` | 本次选中的数据来源 | 先确认选对没有；选错就显式传数据源参数 |
| `[数据生成失败]` + `entry:` / `exit_code:` + `--- router output (tail) ---` | 生成入口失败。tail 是 stdout 与 stderr **合并**后的首尾片段，首部最多 500 字符、总长最多 2000 字符，不是完整输出 | 按尾部信息修 spec / cutter / 生成器；此时不会编译用户程序；要完整日志请直接跑 router |
| `[router error] ...` | 路由内部错误（spec 非法、生成器未注册或未编译、`--only` 无匹配、发布失败） | 按提示修 spec 或注册生成器 |
| `[retry] ...` | 数据流级校验失败后的重试日志 | 多为生成器输出 token 数与 `content[].count` 不符 |
| `[router error] code=unsupported-generator` | `--only` 或 `generation.cases[].generator` 写了没注册的 id（多个会聚合成一条） | 先在 `registry.py` 登记并编译，或改成已注册 id；`available=` 给出当前可用列表 |
| `[router error] code=generator-not-built` | 已注册但 exe 没编译 / 放错位置（预检在建目录、样例回放之前） | 按 `expected=` 编译到 `generator/bin/<kind>/`，或检查 `--generator-root` |
| 样例回放失败 | cutter 输出与 `samples[].input` 不一致 | 题面样例抄错、cutter 排版错，或 `line_sensitive` 设错 |
| 样例未经确认 | `confirmed` 不是 `true` | 与人对齐后改 `true` |
| `[router error] 临时目录已保留: <路径>` | 本轮失败，当前 `.tmp_<run_seed>/` 被保留（含中间 `.in` 与 `.router_tmp`） | 排查完后可手动删除；不要把它当成已发布数据 |
| `[router error] 临时目录路径已存在且缺少标记，拒绝删除: <路径>` | 当前 `--seed` 的临时目录已存在，但不是 router 建的（缺 `.router_tmp`） | 换 `--seed`，或确认后手动清理该目录 |
| `[router error] 当前临时目录清理失败: <路径>` | 同 seed 重建前删除带标记的旧目录失败（如被占用） | 关闭占用进程后重试 |
| `[警告] 历史临时目录清理失败: <路径>` | 启动清理历史 `.tmp_*` 失败，或该目录是 symlink / junction | 不影响本轮生成；需要时手动清理 |

### 16.1 router 结构化错误码

全部由 `DiagnosticError` 抛出，输出形如：

```text
[router error] code=unsupported-generator
[router error] message=未注册的生成器: graph_chain
[router error] generator=graph_chain
[router error] available=seq_random_small
[router error] hint=请改用已注册生成器，或由负责人实现、编译并注册该生成器
```

| code | 触发条件 | 附带字段 |
|---|---|---|
| `unsupported-generator` | `--only`、`generation.cases[].generator` 或 `coverage.exclude[].generator` 引用了未注册 id | `generator`、`available`、`hint` |
| `invalid-coverage` | coverage 的语义错误**统一归这一个码**，具体位置由 `where` 区分：`target_groups` 非正整数、`repeat` 非正整数且非 `"auto"`、`repeat:"auto"` 但缺 `target_groups`、`cases` / `exclude` 不是数组、`exclude[].generator` 缺失或非字符串、`exclude[].generator` 重复、`reason` 为空、`reason_code` 不在枚举内、`evidence` 不是对象 | `where`、`expected`、`actual` |
| `generator-not-built` | 已注册但 `<generator-root>/<kind>/<exe>` 不存在（预检即失败，不会建目录） | `generator`、`expected`、`available`、`hint` |
| `unknown-field` | spec 任意层出现白名单外字段 | `where`、`unknown`、`allowed` |
| `unknown-bind-key` | `generation.cases[].bind` 覆盖了未声明的键（图题只允许 `base_m`，其余只允许 `constraints.variables` 里已声明的变量） | `where`、`unknown`、`allowed` |
| `invalid-schema` | 某层应为 JSON 对象却给了别的类型（如 `constraints` 写成数组、`bind` 写成数组） | `where`、`expected`、`actual` |

说明：字段值里的换行会被压成空格，保证一条错误只占固定行数、不会伪造额外的 `[router error]` 行。

---

## 17. 当前支持状态与已知限制

**已实现**

- 路由全链路：spec 校验 → 绑定 → 写控制 token → 调生成器 → cutter → 校验 → 样例回放 → 发布 → manifest；
- 序列题型（`kind = sequence`）的绑定、校验、行级校验；
- 图论 / 字符串的绑定逻辑（`bind_graph` / `bind_string`）与**部分**校验已存在；完整校验仍缺，见下方已知限制；
- `diff_runner` 粘合：`--generator-exe` 等 4 个新参数、数据来源优先级、不写 `cases.json`。

**已知限制**

- `GENERATORS` 目前只有 `seq_random_small`，且仓库内不保存 exe（`*.exe` 被忽略），需要自行编译后才会是 `ready`；
- 图论 / 字符串生成器未实现（`graph_chain`、`str_random` 等在注册表里是注释状态）；
- `publish` 不清理上一轮的旧 `.in`；router 模式靠 manifest 隔离旧 `.in`（只加载本次 manifest 列出的文件），非 router 入口仍按目录扫描；
- 重复数据**只告警不阻塞**：`[verify]` / `[warn]` 不改退出码、不写 manifest；这两行经对拍器运行时不可见（T-050）；
- `coverage` 的候选集只由「注册表 + `<generator-root>/<kind>/<exe>` 是否存在」决定，注册表自描述（`tier` / `precondition` / `postcondition`）未实现；
- 生成期失败（spec 非法、生成器失败、样例回放失败）不会写 manifest（`status=ready` 要等生成完成后才写），此时只能靠 `[router error]` 文本与退出码判断；
- `replay_samples` 在临时目录创建之后执行，回放失败会留下 `.tmp_<run_seed>/`（带 `.router_tmp` 标记，并会打印保留路径）；
- **图论 / 字符串校验未完成（待 T-044）**：`validate.py` 中 `directed=true` 的重边判定仍用 `(min, max)` 而非 `(u, v)`；没有 `sum(deg) == 2m` 校验；邻接表 `k_mode` 只检查 `cnt < 0`，未完整校验 `k` 与该行内容；`vertex_base = 0` 的邻接表解析与"多余行"检查也尚未补齐。图论 / 字符串生成器本身也还没实现，因此这条链路目前无法端到端跑通。

---

## 18. 扩展一个新生成器（步骤）

1. 明确模式语义（随机 / 单调 / 极值 / 图形态……），确定它在 `generation.cases[].generator` 里的 id；
2. 在 `generator/cpp/<kind>/` 下新建 `.cpp`，`#include "../common.h"`，只从 `Args::rest` 里解析自己的参数；
3. 遵守 §5.1 的全部约定（只写 content、LF、确定性、退出码）；
4. 编译到 `generator/bin/<kind>/<id>.exe`；
5. 在 `registry.py` 的 `GENERATORS` 里登记（未编译时保持注释）；
6. `python generator/router.py --list-generators` 确认 `ready`；
7. 用一个真实题目跑 `diff_runner` 验证：`[data-source]`、`.in` 结构、样例回放、AC 结果；
8. 补一条端到端测试（参考 `generator/tests/test_e2e.py` 的桩生成器写法）。
