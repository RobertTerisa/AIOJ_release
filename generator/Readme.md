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
│   ├── cpp/
│   │   ├── common.h       # 公共参数解析 / 输出打开 / PRNG
│   │   └── <模式>/<生成器>.cpp
│   └── tests/             # 单元测试与端到端测试
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

> 目录里列的是规划结构；**实际可用以 `generator/registry.py` 的 `GENERATORS` 为准**。

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

临时文件（`test_data/<题号>/.tmp_<run_seed>/`）在发布成功后会被清理；发布失败时保留，便于人工恢复。

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
| `cases[]` | 一个测试点一条规则 |
| `cases[].generator` | **注册表里的生成器 id**（不含 `.exe`） |
| `cases[].repeat` | 该规则重复生成几个测试点 |
| `cases[].scale` | `min` / `max` / `small` / `medium` / `random` |
| `cases[].bind` | 覆盖某个变量的取值或范围（如 `"base_m": "n-1"`） |
| `cases[].mutation` | 图论变异（`duplicate` / `self_loop`），序列题不用 |

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

路由侧遇到非 `0` 会报 `生成器失败: <exe> (exit=N)` 并附上 stderr / stdout 尾部，评测在**编译前**终止。

### 5.3 参数是怎么算出来的（spec → argv）

| 参数 | 来源 |
|---|---|
| `--seed` | `sub_seed = H(run_seed, generator, group_index, attempt)`，由路由派生 |
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
- 每组 `sub_seed = H(run_seed, generator, group_index, attempt)`；
- 生成器只接收 `sub_seed`；
- `run_seed` 写入 manifest 与评测记录；
- 成功组的 `sub_seed` / `attempt` 写入 job 对象；失败 attempt 只打日志；
- 最终 `.in` 落盘保留，WA 时可直接复现。

⚠️ 已知行为：`sub_seed` 只由 `(run_seed, generator, group_index, attempt)` 决定，**不含规则序号**。所以同一条规则 `repeat > 1` 时会得到多个完全相同的 `.in`；需要不同数据时，请写成多条 `bind` 不同的规则（各自 `repeat = 1`）。

---

## 13. 发布与 manifest

1. 全部 `.in` 先生成到 `test_data/<题号>/.tmp_<run_seed>/`；
2. 全部校验通过（含样例回放）；
3. 写 manifest，`status = "ready"`；
4. 逐文件 `os.replace` 到 `test_data/<题号>/`；
5. 全部成功 → `status = "ok"`，清理临时目录；
6. 中途失败 → `status = "failed"`，**保留临时目录**并打印路径，返回非 0。

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

> 已知限制：MVP 不做目录级原子替换，也不删除 `test_data/<题号>/` 里上一轮的旧 `.in`，对拍器会把它们一起读入。

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

退出码：`0` 成功；`2` 参数 / 规格 / 生成失败（打印 `[router error] ...`）；`1` 发布失败。

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
- router 模式**不写 `cases.json`**，只读 `<data_dir>/<题号>/*.in`；
- 评测记录的元信息会带上「数据来源 / 生成入口 / run_seed / manifest 路径」。

---

## 16. 报错与排查

| 输出 | 含义 | 处理 |
|---|---|---|
| `[data-source] ...` | 本次选中的数据来源 | 先确认选对没有；选错就显式传数据源参数 |
| `[数据生成失败]` + `entry:` / `exit_code:` / 双流尾部 | 生成入口失败 | 按尾部信息修 spec / cutter / 生成器；此时不会编译用户程序 |
| `[router error] ...` | 路由内部错误（spec 非法、生成器未注册或未编译、`--only` 无匹配、发布失败） | 按提示修 spec 或注册生成器 |
| `[retry] ...` | 数据流级校验失败后的重试日志 | 多为生成器输出 token 数与 `content[].count` 不符 |
| 未注册的生成器: xxx；可用: ... | `generation.cases[].generator` 写了没注册的 id | 先在 `registry.py` 登记，或改成已注册 id |
| 生成器不存在: `.../bin/<kind>/xxx.exe` | 已注册但 exe 没编译 / 放错位置 | 编译到 `generator/bin/<kind>/` |
| 样例回放失败 | cutter 输出与 `samples[].input` 不一致 | 题面样例抄错、cutter 排版错，或 `line_sensitive` 设错 |
| 样例未经确认 | `confirmed` 不是 `true` | 与人对齐后改 `true` |

---

## 17. 当前支持状态与已知限制

**已实现**

- 路由全链路：spec 校验 → 绑定 → 写控制 token → 调生成器 → cutter → 校验 → 样例回放 → 发布 → manifest；
- 序列题型（`kind = sequence`）的绑定、校验、行级校验；
- 图论 / 字符串的绑定与校验逻辑（生成器尚未实现，暂不可端到端跑通）；
- `diff_runner` 粘合：`--generator-exe` 等 4 个新参数、数据来源优先级、不写 `cases.json`。

**已知限制**

- `GENERATORS` 目前只有 `seq_random_small`，且仓库内不保存 exe（`*.exe` 被忽略），需要自行编译后才会是 `ready`；
- 图论 / 字符串生成器未实现（`graph_chain`、`str_random` 等在注册表里是注释状态）；
- `publish` 不清理上一轮的旧 `.in`；
- 生成期失败（spec 非法、生成器失败、样例回放失败）不会写 manifest，只能靠退出码判断；
- `replay_samples` 在临时目录创建之后执行，回放失败会留下 `.tmp_<run_seed>/`；
- `--only` 无匹配、`--generator-exe` 未注册等提示文案与旧版文档存在差异。

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
