# Diff Runner 开发日志（整理稿）

> 整理日期：2026-10-11（最近维护：2026-10-31）  
> 整理来源：`develop_log.md`（原文见文末「历史归档」）  
> 当前版本：v0.2（commit `81de335`）  
> 当前分支状态：`main`（截至 `a407415`，与 `origin/main` 同步）  
> 排序规则：现行规格与当前待办不按日期排序；关键决策、部署记录、历史归档索引按新→旧排列。  
> 待办顺延规则：未明确完成、取消或被取代的待办不删除，只更新「最近复核」日期。  
> 本整理稿只做归纳、分类和状态标注，不新增需求；无法判断的内容标注为「待确认」。  


---

## 0. 当前权威规格摘要

| 项目 | 当前有效规格 | 状态 |
|---|---|---|
| 工具与工作区 | 工具本体在 `AIOJ_release`；题目、数据、记录放在工作区；`week_log/` 为仓库内唯一允许放置题目文件（含二进制产物）的例外 | 现行（2026-10-16 修订） |
| 配置文件 | 文件名 `aioj.workspace.json`；可放在程序本体目录；本机私有；不得提交公开仓库；`workspace` 字段指向真实工作区 | 现行 |
| 配置模板 | `template.aioj.workspace.json` 入库，不含本机绝对路径 | 已实施 |
| 题目路径 | 优先 `problems_dirs` 数组；兼容旧的单字符串 `problems_dir` | 已实施 |
| 多题目路径 | 按 `problems_dirs` 顺序查找首个存在的 `<题号>/` | 已实施 |
| 题目文件 | `<题号>.md`、`<题号>.cpp`、`<题号>_correct.cpp`，找不到回退 `<题号>_solution.cpp` | 已实施 |
| 数据来源 | 优先 `<题号>/IN/*.in`；其次配置的 `generators_dir/<题号>_generator.py`；否则报错 | 已实施 |
| 测试数据落点 | `<data_dir>/<题号>/cases.json` | 已实施 |
| 评测记录落点 | `<records_dir>/<题号>/<题号>_diff_<时间戳>_submission_<次数>.md` | 已实施 |
| 配置缺省行为 | 只给 `--name` 时提示复制模板；显式给出全部路径时仍可运行 | 已实施 |
| 仓库卫生 | `.gitignore` 截留私有配置、测试数据、评测记录、讨论记录、`__pycache__`、`*.pyc`、`develop_log.md` | 已实施 |
| 仓库题目文件 | 仓库内除 `week_log/` 外，不得出现以题号命名的文件；`diff_runner/` 内不得出现以题号命名的生成器或产物 | 现行（2026-10-16 修订） |
| 联网与密钥 | 不联网、不调用 API、不写入密钥 | 现行红线 |
| Time Limit | 题面 `AIOJ-META` 的 `TL` 优先；否则用 workspace 默认值；不做动态测定 | 现行 / 待实施 |
| 默认 Time Limit | workspace 默认 `timeout` 已改为 `1s` | 已完成（T-002） |
| Memory Limit | 当前不支持主动 MLE 检测；后续复用 `AIOJ-META` 的 `ML` 字段 | 待实施 |
| `<题号>.meta.json` | 不作为面向用户的常规配置入口 | 现行 |
| 免责声明 | 本地测评结果不代表 OJ 官方结果，最终以实际平台提交为准 | 现行 / 部分待实施 |
| 不支持范围 | 多解、Special Judge、交互题、主动 MLE 检测 | 现行限制 |

---

## 1. 现行规格

### 1.1 工具与工作区分离

- 工具本体位于公开仓库 `AIOJ_release`。
- 题目、生成器、测试数据、评测记录、讨论整理属于工作区内容。
- 工作区由 `aioj.workspace.json` 声明；该文件包含本机绝对路径，必须 gitignore。
- 仓库内除 `week_log/`（每周任务材料目录，含二进制产物）外，不得出现任何以题号命名的文件。

### 1.2 工作区配置

配置文件名固定为 `aioj.workspace.json`。该文件可以放在程序本体目录（例如 `D:/AIOJ_release/aioj.workspace.json`），但必须被 gitignore；其中 `workspace` 字段指向真实工作区。

字段与默认值：

| 字段 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `workspace` | 否 | 配置文件所在目录 | 工作区根，其他相对路径的基准 |
| `problems_dirs` | 建议填 | `workspace` | 题目目录数组，按顺序查找 |
| `problems_dir` | 否 | — | 旧的单路径写法，兼容并归一化为单元素列表 |
| `generators_dir` | 否 | `<workspace>/generators` | 生成器目录 |
| `discussion_dir` | 否 | `<workspace>/discussion_records` | 讨论整理目录 |
| `records_dir` | 否 | `<workspace>/evaluation_records` | 评测记录目录 |
| `data_dir` | 否 | `<workspace>/test_data` | 测试数据目录 |
| `timeout` | 否 | `1` | 默认超时秒数 |
| `compiler` | 否 | `g++` | 默认编译器 |
| `std` | 否 | `c++17` | 默认 C++ 标准 |

路径解析：

- 绝对路径直接使用；
- 相对路径相对 `workspace` 解析；
- 命令行参数优先级高于配置文件；
- 未提供配置文件且只给 `--name` 时，报清晰错误，提示复制 `template.aioj.workspace.json`；
- 显式提供全部文件路径时，仍可保持旧的运行方式；
- 配置缺省时，输出默认基准为当前工作目录 `cwd`（第 19.5 节修订第 18.5 节）。

### 1.3 命令行接口

- 新增 `--workspace-config <文件路径>`：显式指定工作区配置。
- 未提供该参数时，若当前工作目录下存在 `aioj.workspace.json`，自动加载。
- 旧 CLI 参数保持兼容；显式传入的路径优先于配置。
- `--dataset`：把测试数据、评测记录放入 `<题号>/<数据集名>/` 子目录。
- `--cases-out`：显式指定 `cases.json` 输出路径，优先级高于 `--dataset`。

### 1.4 题目文件定位

当只给 `--name <题号>` 且未显式给出文件路径时：

- 按 `problems_dirs` 顺序查找第一个存在的 `<题号>/`；
- 题面：`<题目目录>/<题号>.md`；
- 用户代码：`<题目目录>/<题号>.cpp`；
- 题解：`<题目目录>/<题号>_correct.cpp`，找不到则回退 `<题号>_solution.cpp`；
- 显式 CLI 路径优先于上述推导。

### 1.5 数据来源

- 优先 `<题目目录>/IN/` 中存在 `.in` 文件；
- 否则使用 `<generators_dir>/<题号>_generator.py`；
- 兼容查找 `<题目目录>/<题号>_generator.py`；
- 都没有则清晰报错，说明缺什么，不得编造数据。

### 1.6 产物落点

- 测试数据：`<data_dir>/<题号>/cases.json`；
- 评测记录：`<records_dir>/<题号>/<题号>_diff_<时间戳>_submission_<次数>.md`；
- 讨论整理：`<discussion_dir>/<题号>/BUGLOG.md`，由 Agent 手动整理，工具不自动写；
- 生成器：`<generators_dir>/<题号>_generator.py`；
- 目录不存在时自动创建；
- 工具自身目录不得再出现任何产物。

### 1.7 安全与仓库卫生

- 不联网、不调用任何 API、不写入任何密钥。
- 不修改题目源码 `<题号>.cpp`、`<题号>_solution.cpp`。
- 未经批准不新增功能：Special Judge、MLE、交互题、多解均不在既有范围内。
- 不把 `aioj.workspace.json` 或任何含绝对路径的文件提交到公开仓库。
- `.gitignore` 截留：`aioj.workspace.json`、`test_data/`、`discussion_records/`、`evaluation_records/`、`__pycache__/`、`*.pyc`、`develop_log.md`。
- `develop_log.md` 为本地开发日志，已不再提交。

### 1.8 Time Limit / Memory Limit 规则

- **不做动态测定 Time Limit**：不通过参考题解耗时自动推导 TL。
- 用户可以在题面 Markdown 中使用方案 B：

```markdown
<!-- AIOJ-META
TL: 1.00s
ML: 256MB
-->
```

- 评测机读到题面 `TL` 标签后，优先使用该 Time Limit；其优先级高于 CLI `--timeout` 和 workspace 默认值。
- 如果题面没有 `TL` 标签，则使用 workspace 配置中的 `timeout`。
- workspace 默认 `timeout` 从 `10s` 改为 `1s`。
- 不联网获取洛谷等平台的 Time Limit。
- 只解析 `AIOJ-META` 注释块内部的 `TL:` / `Time Limit:` / `时间限制:` 行。
- 支持单位 `s`、`ms`、`秒`、`毫秒`，统一换算为秒。
- 不在题面正文中全文裸匹配 `TL:`。
- 找不到 `TL` 标签时，不得编造 Time Limit。
- 不把 `<题号>.meta.json` 作为面向用户的常规配置入口；工具不自动生成、不自动修改该文件。
- MLE 当前未实现；后续复用 `AIOJ-META` 的 `ML` 字段。
- CLI `--timeout` 仅在题面没有 `TL` 标签时作为备用覆盖；该优先级由 T-004 确认。

### 1.9 免责声明

Agent 在输出任何对拍/测评结果时，必须明确声明：

> 本次测评结果为本地对拍结果，不代表 OJ 官方测评结果，最终以实际平台提交结果为准。

要求：

- Agent 在聊天中展示 AC / WA / TLE / MLE / 参考TLE / 参考MLE 等结果时，必须附带该声明；
- `diff_runner` 生成的评测记录 Markdown 也应在“说明”部分加入同义声明；
- 不得把本地 AC 直接表述为“官方 AC”，也不得把本地 TLE 直接表述为“官方 TLE”；
- 如果 TL / ML 来自 workspace 默认值而不是题面 `AIOJ-META`，还应注明这是非官方限制。

---

## 2. 当前待办

> 最后复核日期：2026-10-31  
> 排序规则：先按状态（待确认 → 待实施），再按优先级（高 → 中 → 低）。  
> 未明确完成、取消或被取代的待办不删除，只更新「最近复核」日期。

| ID | 事项 | 状态 | 优先级 | 执行人 | 发起者 | 创建日期 | 最近复核 | 来源 | 备注 |
|---|---|---|---|---|---|---|---|---|---|
| T-001 | 实现题面 `AIOJ-META` 中 `TL` 的解析 | 待实施 | 高 | RobertTerisa | RobertTerisa | 2026-10-11 | 2026-10-12 | 21.3 / 21.4 | 后续复用同一注释块解析 `ML` |
| T-005 | `diff_runner` 生成的评测记录 Markdown 在「说明」部分自动加入免责声明 | 待实施 | 高 | RobertTerisa | RobertTerisa | 2026-10-11 | 2026-10-13 | 21.6 | 曾误标「已完成」（见 §4.5），经代码核对实际未实现；优先级为还原时推断 |
| T-033 | 把检查文件缺漏的功能从 AGENTS.md 转移到对拍器 | 待实施 | 高 | RobertTerisa | RobertTerisa | 2026-10-17 | 2026-10-17 | 本次新增 | 负责人 2026-10-17 提出 |
| T-036 | 制作数据生成器路由，通过json传递参数 | 待实施 | 高 | RobertTerisa | RobertTerisa | 2026-10-22 | 2026-10-22 | 本次新增 | 负责人 2026-10-22 提出 |
| T-014 | 编写自己的通用数据生成器、极端数据生成器。确定 LLM 自行编写数据生成器的边界 | 待实施 | 中 | RobertTerisa | RobertTerisa | 2026-10-11 | 2026-10-12 | 本次新增 | 按负责人要求调整内容 |
| T-030 | 理清对拍器代码，运行逻辑 | 待实施 | 中 | RobertTerisa | RobertTerisa | 2026-10-13 | 2026-10-13 | 本次新增 | 负责人 2026-10-13 提出 |
| T-031 | 加入教学过程泄压阀 | 待实施 | 中 | RobertTerisa | RobertTerisa | 2026-10-16 | 2026-10-16 | 本次新增 | 负责人 2026-10-16 提出 |
| T-032 | 加入对拍前LLM询问数据范围是否有错漏，确认无误后加入题面的标签里 | 待实施 | 中 | RobertTerisa | RobertTerisa | 2026-10-17 | 2026-10-17 | 本次新增 | 负责人 2026-10-17 提出 |
| T-034 | 增加链表（邻接表，有边权，无边权）数据生成器 | 待实施 | 中 | RobertTerisa | RobertTerisa | 2026-10-19 | 2026-10-19 | 本次新增 | 负责人 2026-10-19 提出 |
| T-035 | 增加哈希冲突的序列数据生成器 | 待实施 | 中 | RobertTerisa | RobertTerisa | 2026-10-19 | 2026-10-19 | 本次新增 | 负责人 2026-10-19 提出 |
| T-037 | 增加迁移流程 | 待实施 | 中 | RobertTerisa | RobertTerisa | 2026-10-26 | 2026-10-26 | 本次新增 | 负责人 2026-10-26 提出 |
| T-038 | 编写数据校验器 | 待实施 | 中 | RobertTerisa | RobertTerisa | 2026-10-26 | 2026-10-26 | 本次新增 | 负责人 2026-10-26 提出。校验生成器产出的 `.in` 是否符合 `<题号>.generator.json` 的规格（行数/长度/取值范围/T 组数），不符则判失败并终止评测，防止「生成器不照规格写、路由器无从发现」。与 T-014 相关：数据生成器后续由负责人手写补充，LLM 现写仅为过渡方案 |
| T-039 | 新增对拍器缺失文件报错知会LLM | 待实施 | 中 | RobertTerisa | RobertTerisa | 2026-10-30 | 2026-10-30 | 本次新增 | 负责人 2026-10-30 提出。`diff_runner` 找不到 `<题号>.md` / `<题号>.cpp` / 题解文件时，把缺失项与搜索路径一次性输出到 CLI，供 LLM 读取后补齐文件。验收细节：使用 `[input-missing]` 前缀；stdout 和 stderr 都输出；列出完整搜索路径和缺失项。 |
| T-040 | 新增路由不支持数据生成器知会LLM | 待实施 | 中 | RobertTerisa | RobertTerisa | 2026-10-30 | 2026-10-30 | 本次新增 | 负责人 2026-10-30 提出。路由遇到未注册或未编译的生成器时输出清晰的 `[router error]` 文本（含 generator / available / hint 等字段），`diff_runner` 原样输出到 CLI，供 LLM 据此实现并注册生成器 |
| T-041 | 实现路由错误输出与对拍器错误透传 | 待实施 | 中 | RobertTerisa | RobertTerisa | 2026-10-30 | 2026-10-30 | 本次新增 | 负责人 2026-10-30 提出。覆盖 `[router error]` 文本输出、`diff_runner` 合并 stdout/stderr 并原样透传；与 T-040 相关，实施时可合并 |
| T-042 | 让 diff_runner 只消费 status=ok 的 manifest 且只加载 manifest 列出的 `.in` | 待实施 | 中 | RobertTerisa | RobertTerisa | 2026-10-30 | 2026-10-30 | 本次新增 | 负责人 2026-10-30 提出。`run_external_generator()` 成功后不直接扫目录，而是读取 manifest：`status` 必须为 `ok`，且只加载 `files[].in`；避免 `test_data` 下旧 `.in` 混入，失败时终止评测 |
| T-044 | 补全图论校验语义 | 待实施 | 中 | RobertTerisa | RobertTerisa | 2026-10-30 | 2026-10-30 | 本次新增 | 负责人 2026-10-30 提出。包括：有向简单图重边判定改为 `(u, v)`；明确并实现 `sum(deg)` / 邻接表 `k` 校验；覆盖 `vertex_base = 0` 的邻接表解析；`validate_lines()` 检查多余行。与 T-043 的度数校验项相关，实施时合并 |
| T-045 | 修正 line_sensitive=true 的字符串校验 | 待实施 | 中 | RobertTerisa | RobertTerisa | 2026-10-30 | 2026-10-30 | 本次新增 | 负责人 2026-10-30 提出。包括：`emit="string"` 不按 token 数校验，按整行内容校验；保留空行，不过滤；检查字符串实际长度；循环结束后检查多余行；`verify_content()` 的 lines 分支同步 |
| T-046 | 明确 router 临时目录的生命周期与清理策略 | 待实施 | 中 | RobertTerisa | RobertTerisa | 2026-10-30 | 2026-10-30 | 本次新增 | 负责人 2026-10-30 提出。包括：成功发布后清理当前 `.tmp_*`；失败时保留并打印路径；清理历史 `.tmp_*`；或把临时目录移出 `test_data/<题号>/`；与“`test_data/<题号>/` 只有 `.in`”的验收统一 |
| T-006 | 实现 MLE / 参考 MLE 检测（使用WSL沙箱实现） | 待实施 | 低 | RobertTerisa | RobertTerisa | 2026-10-11 | 2026-10-12 | 20.6 / 21.4 | 后续复用 `AIOJ-META` 的 `ML` 字段 |
| T-043 | 统一 generator_operation.md 的文档表述与参考实现（manifest 位置、生成器错误文案、度数校验、阶段编号） | 待实施 | 低 | RobertTerisa | RobertTerisa | 2026-10-30 | 2026-10-30 | 本次新增 | 负责人 2026-10-30 提出。包括：架构图 manifest 应画在 `evaluation_records`；验收“已注册但未编译”与“生成器不存在”文案对齐；11.3 的 `sum(deg) == 2m` / 邻接表 `k` 校验补 TODO 或等图论阶段；阶段编号 10→12、17→19 重编号 |
| T-047 | 根据 yunhuier 的 week1 日志优化提示词 | 待实施 | 低 | RobertTerisa | RobertTerisa | 2026-10-31 | 2026-10-31 | 本次新增 | 负责人 2026-10-31 提出。参考材料位于 `week_log/yunhuier/week1/`（实际文件为 `week1_task.md`，无 week1 日志文件） |

---

## 3. 关键决策

> 排序规则：按决策日期新→旧；同日按决策编号新→旧。  
> 状态含义：现行 / 待实施 / 已实施 / 已废弃 / 已被取代 / 待确认。

| 编号 | 日期 | 版本 / commit | 决策 | 状态 | 取代关系 |
|---|---|---|---|---|---|
| D-022-01 | 2026-10-16 | 本次拍板 | 仓库题目存放规则：`week_log/` 为唯一允许放置题目文件的例外（含二进制产物），仓库其余位置不得出现题目文件 | 已确认 | 修订 §0「工具与工作区」、§1.1、§17.3；同步 AGENTS.md / Readme.md / 模板；历史条目不改写 |
| D-021-04 | 2026-10-12 | 现行 | CLI `--timeout` 与题面 `AIOJ-META` 的优先级：题面 `TL` 优先 | 现行 / 待实施 | 完善 D-021-01 |
| D-018-03 | 2026-10-12 | 已确认 | `aioj.workspace.json` 放在程序本体目录下，`workspace` 字段指向真实工作区 | 已确认 | 完善 D-018-01 |
| D-021-03 | 2026-10-11 | 已实施 | Agent 输出测评结果必须附免责声明；后续评测记录也加入同义声明 | 现行 / 部分实施 | 无 |
| D-021-02 | 2026-10-11 | 待实施 | 不把 `<题号>.meta.json` 作为面向用户的常规配置入口 | 现行 | 取代此前“用户可自行配置 meta.json”的讨论 |
| D-021-01 | 2026-10-11 | 部分实施 | 不做动态 Time Limit；题面 `AIOJ-META` 的 `TL` 优先；否则用 workspace 默认值；默认值从 `10s` 改为 `1s`；不联网获取 TL | 现行 / 部分实施 | 修订第 20.6 节“根据每道题调整 Time Limit”的旧设想 |
| D-020-01 | 2026-10-11（v0.2 实施） | v0.2 / `81de335` | 引入 `problems_dirs` 多路径；按顺序取第一个命中；兼容 `problems_dir`；散装单文件暂不支持 | 已实施 | 取代第 17.3、19.1、19.2 节的单路径设定 |
| D-019-01 | 2026-10-11（v0.2 实施） | v0.2 / `81de335` | 题目文件按配置中的绝对路径查找；各类目录写入配置；模板与 `.gitignore` 入库；缺配置时只给 `--name` 报错；缺配置输出默认基准为 `cwd` | 已实施 | 取代第 17、18 节部分内容；后被 D-020 部分修订 |
| D-018-02 | 2026-10-11（v0.2 实施） | v0.2 / `81de335` | 处理 `Judge` 与 `AIOJ_release` 分叉；并入 `--dataset` / `--cases-out` | 已实施 | 无 |
| D-018-01 | 2026-10-11（v0.2 实施） | v0.2 / `81de335` | 配置文件定名 `aioj.workspace.json`；私有配置 gitignore；模板入库；`--workspace-config`；自动加载当前目录配置 | 已实施 | 取代第 16.4 节；后被 D-019、D-020 细化 |
| D-017-01 | 2026-10-11（17.9 勘察） | v0.2 / `81de335` | 不新建工作区，直接使用 `D:/ICPC case/Judge`；题目路径用绝对路径 | 已实施 | 取代第 15.3、16.4 节；后被 D-018、D-019 细化 |
| D-016-01 | 未标注 | 未标注 | 工作区配置草案与 `--workspace` 设想 | 已被取代 | 被 D-017、D-018、D-019 取代 |
| D-015-01 | 未标注 | v0.2 | 工具与内容分离，工作区外置 | 已实施 | 无 |
| D-013-01 | 未标注 | 未标注 | 不联网、不调用 API、不写入密钥 | 现行红线 | 无 |

### 决策说明

- **D-017-01**：保留现有 `D:/ICPC case/Judge` 作为工作区，不强制重建；`problems_dir` 指向 `Judge`，不能直接指向 `D:/ICPC case`，否则会把 `blog`、`Luogu`、`MATIJI` 等误判为题目目录。
- **D-018-01 / D-019-01 / D-020-01**：这三组决策共同构成 v0.2 的工作区配置与自动定位方案，已由 `81de335` 实现。
- **D-021-01 / D-021-04**：动态 TL 被明确否决；题面 `AIOJ-META` 的 `TL` 优先，CLI `--timeout` 仅在题面没有 `TL` 时作为备用覆盖。
- **D-018-03**：`aioj.workspace.json` 可以放在程序本体目录，文件中的 `workspace` 字段指向真实工作区。
- **D-021-02**：用户只被期望在题面顺手补充 `AIOJ-META`，不应要求其逐题维护独立 `meta.json`。
- **D-021-03**：本地对拍结论不能冒充官方 OJ 结论，这是固定输出规范。
- **D-013-01**：属于长期安全红线，不参与日期排序。

---

## 4. 部署 / 实施记录

> 排序规则：按日期新→旧；同日按提交顺序新→旧。

### 4.1 Git 提交记录

| 日期 | commit | 内容 | 状态 |
|---|---|---|---|
| 2026-10-11 | `a407415` | 修复 `.gitignore` | 已部署 |
| 2026-10-11 | `b00b82f` | 不再提交本地开发日志 `develop_log.md`（含本机目录） | 已部署 |
| 2026-10-11 | `81de335` | v0.2 发布：工作区配置、自动定位、产物外置、模板、`.gitignore`、文档更新、移除题号生成器与 pycache | 已部署 |
| 2026-10-11 | `3db59a0` | 更新开发版本的 `AGENTS.md` | 已部署 |
| 2026-10-10 | `ccfc2ab` | 修改 `Readme.md` | 已部署 |
| 2026-10-10 | `51f01bd` | AIOJ-release 初始发布 | 已部署 |

当前 `main` 分支截至 `a407415`，与 `origin/main` 同步。

### 4.2 v0.2 已完成的实现

- `aioj.workspace.json` 工作区配置解析。
- `--workspace-config` 参数；未提供时自动读取当前目录同名配置。
- `problems_dirs` 多路径支持；兼容旧的字符串 `problems_dir`。
- 按 `problems_dirs` 顺序取第一个命中的 `<题号>/`。
- 根据 `<题号>.md`、`<题号>.cpp`、`<题号>_correct.cpp` / `<题号>_solution.cpp` 自动定位题目文件。
- 数据来源自动选择：`IN/*.in` 优先；否则使用生成器。
- 产物落点改为配置中的 `data_dir` / `records_dir`。
- 并入 `--dataset` / `--cases-out`。
- 新增 `template.aioj.workspace.json` 与 `.gitignore`。
- 更新 `Readme.md`、`diff_runner/README.md`、`diff_runner/AGENT_USAGE.md`。
- 移除工具仓库中的题号生成器与 `__pycache__` / `*.pyc` 跟踪。
- 旧命令与旧 `--config` 方式保持兼容。

### 4.3 当前实际使用状态（未入库内容）

- 私有工作区配置当前位于 `D:/AIOJ_release/aioj.workspace.json`，已被 `.gitignore` 忽略。
- 该配置中的 `workspace` 指向 `D:/ICPC case/Judge`；题目、输出目录仍落在真实工作区。
- 真实工作区为 `D:/ICPC case/Judge`，其中已有 `P9228`、`UVA10364` 等完整题目目录。
- 工作区中仍存在一份旧的 `diff_runner` 副本；当前真源以 `AIOJ_release/diff_runner/diff_runner.py` 为准。
- `D:/ICPC case/Judge/.gitignore` 已作为本地保护文件存在；是否在 Judge 仓库提交由负责人决定。

### 4.4 文档整理说明

- 本整理稿已迁移覆盖 `develop_log.md`。
- `tmp.md` 已删除。
- 原文已完整保存在文末「历史归档」中，未删除。

---

### 4.5 待办处理记录（2026-10-12 / 2026-10-16 / 2026-10-17）

- T-002：已完成。workspace 默认 `timeout` 已改为 `1s`。
- T-003：已完成。模板与文档中的默认值说明已更新。
- T-004：已确认。题面 `AIOJ-META` 的 TL 优先。
- T-005：状态还原为「待实施」。经代码核对，`diff_runner` 生成的评测记录 Markdown 尚未加入 §21.6 要求的免责声明；此前「已完成」为误标。（2026-10-13 复核）
- T-009：已确认完成。
- T-010：已确认。`aioj.workspace.json` 放在程序本体下。
- T-011：不需要清理，关闭。
- T-012：不需要，关闭。
- T-029：已完成。搜索题用时过长问题已修复。
- T-013：已完成（2026-10-16）。经文件核对，`AGENTS.md` 已加入「模式 C：日志维护」规则，包含前置动作、维护原则、状态流转、每次维护必须检查的区块、输出格式与禁止事项；已从 §2 当前待办移除。
- T-015：已完成（2026-10-17）。负责人确认完成；已从 §2 当前待办移除。
- T-016：已完成（2026-10-17）。负责人确认完成；已从 §2 当前待办移除。

- T-008：不需要 `.gitignore` 例外，关闭。
- T-006：优先级调整为低。
- T-013：优先级调整为高。
- T-014：内容调整为“编写自己的通用数据生成器、极端数据生成器。确定 LLM 自行编写数据生成器的边界”。
- T-015：内容调整为“根据笔记调整我目前的工作流提示词”，优先级调整为高。
- T-016：内容调整为“在提示词中增加软约束，添加输出内容监控插件，用正则表达式拦截完整代码”，优先级调整为高。
- T-017、T-018、T-019、T-023、T-024、T-025、T-026、T-027、T-028：按负责人要求从当前待办移除。
- T-007：按负责人要求从当前待办移除。

> 以上 2026-10-12 条目由负责人确认；T-013 的完成状态于 2026-10-16 由负责人确认；T-015、T-016 的完成状态于 2026-10-17 由负责人确认；如与代码实际行为不一致，以最终代码验证为准。

### 4.6 待办处理记录（2026-10-30）

- T-039：新增。负责人要求增加“对拍器缺失文件报错知会 LLM”，优先级中，执行人与发起人均为 RobertTerisa。
- T-040：新增。负责人要求增加“路由不支持数据生成器知会 LLM”，优先级中，执行人与发起人均为 RobertTerisa。
- T-041：新增。负责人要求把“路由错误输出与对拍器错误透传”移入待办，优先级中，执行人与发起人均为 RobertTerisa；与 T-040 相关，实施时可合并。
- T-042：新增。负责人要求 `diff_runner` 只消费 `status=ok` 的 manifest，并只加载 manifest 列出的 `.in`，优先级中，执行人与发起人均为 RobertTerisa。
- T-043：新增。负责人要求把 `generator_operation.md` 的表述一致性问题（manifest 位置、生成器错误文案、度数校验、阶段编号）作为低优先级待办，执行人与发起人均为 RobertTerisa。
- T-044：新增。负责人要求补全图论校验语义（有向重边、度数 / 邻接表 k、vertex_base=0、多余行），优先级中，执行人与发起人均为 RobertTerisa；与 T-043 的度数校验项相关。
- T-045：新增。负责人要求修正 `line_sensitive=true` 的字符串校验（整行校验、保留空行、长度检查、多余行检查），优先级中，执行人与发起人均为 RobertTerisa。
- T-046：新增。负责人要求明确 router 临时目录的生命周期与清理策略（成功清理、失败保留并打印路径、清理历史 `.tmp_*` 或移出 `test_data`），优先级中，执行人与发起人均为 RobertTerisa。

### 4.7 待办处理记录（2026-10-31）

- T-047：新增。负责人要求“根据 yunhuier 的 week1 日志优化提示词”，优先级低，执行人与发起人均为 RobertTerisa。

## 5. 历史归档

> 排序说明：本节提供「归档索引（新→旧）」；索引之后保留原 `develop_log.md` 全文，原文按原始顺序存放，未删除任何内容。  
> 本归档仅作历史追溯；如与前面的「现行规格」「关键决策」冲突，以标注为「现行」的内容为准。  
> 归档正文中的旧路径、旧状态、旧待办不自动视为当前有效需求。

### 5.1 归档索引（新 → 旧）

| 日期 | 内容 | 原章节 |
|---|---|---|
| 2026-10-11 | TLE / ML 传递方式决议、meta.json 否决、免责声明 | 第 21.1～21.6 节 |
| 2026-10-11 | 多题目路径补充要求 | 第 20.1～20.6 节 |
| 2026-10-11 | v2 开发要求：绝对路径、目录配置、模板、`.gitignore` | 第 19.1～19.7 节 |
| 2026-10-11 | 工作区配置实施规格 | 第 18.1～18.11 节 |
| 2026-10-11 | 目标拓扑修订与现状勘察 | 第 17.1～17.9 节 |
| 未标注 | 工作区方案细化 | 第 16.1～16.7 节 |
| 未标注 | 工具与内容分离架构决策 | 第 15.1～15.7 节 |
| 未标注 | 早期基础：目标、目录、CLI、输出、生成器、AGENTS、图论、验证、安全、限制 | 第 1～14 节 |

---

### 5.2 原文存档（按原始顺序，未删除）

下面为整理前 `develop_log.md` 的全文，原样保留，供历史追溯。

---

# Diff Runner 开发日志

记录范围：对拍器本体、脚本需求、数据生成器规范、AGENTS.md 规则、目录约定、文档体系、验证流程和安全检查。

说明：本日志只记录工程开发相关内容，不包含任何解题方法、算法思路或解题过程。

---

## 1. 项目目标

最初目标是构建一个本地对拍器：

- 能读取用户代码和题解代码；
- 能编译并运行两组代码；
- 能比较标准输出；
- 能把评测结果保存为 Markdown；
- 能复用，而不是每道题都重写一套脚本。

后续目标扩展为：

- 用户代码、题解代码、题目 Markdown、测试数据源全部参数化；
- 支持固定输入、用户自有 `.in`、自动生成数据；
- 支持自动生成测试数据；
- 支持按题号归档数据、评测记录和讨论记录；
- 将 Agent 工作流写入 `AGENTS.md`。

---

## 2. 目录职责

当前约定：

```text
diff_runner\            对拍器本体和文档
evaluation_records\     自动评测记录
discussion_records\     讨论、Debug、优化记录
test_data\              对拍使用的中间数据
AGENTS.md               Agent 行为规则
```

对拍器内部的生成器目录：

```text
diff_runner\generators\
```

---

## 3. 脚本需求演进

### 3.1 早期脚本

早期使用过若干独立脚本：

- 单测试用例对拍脚本；
- 多测试用例对拍脚本；
- 结果汇总脚本。

它们能完成基本任务，但存在明显问题：

- 路径和文件名容易写死；
- 不同题之间需要复制修改；
- 测试数据、输出、记录混在同一个目录；
- 难以统一的生成器规范；
- 缺少统一的参数表和使用说明。

### 3.2 模块化对拍器

将功能收敛为：

```text
diff_runner\diff_runner.py
```

核心需求：

- 用户代码、题解代码、题目 Markdown 均通过参数传入；
- 测试数据来源通过参数选择；
- 结果统一输出到 `evaluation_records\<题号>\`；
- 中间数据统一输出到 `test_data\<题号>\`；
- 使用相对路径调用；
- 支持配置文件。

---

## 4. 对拍器 CLI 需求

最终 CLI 参数包括：

| 参数 | 用途 |
|---|---|
| `--config` | 读取 JSON 配置文件 |
| `--name` | 题目名 |
| `--problem-md` | 题目 Markdown |
| `--user` | 用户代码 |
| `--correct` | 题解代码 |
| `--in-dir` | 用户自有 `.in` 目录 |
| `--cases` | 内部/高级 cases 模式 |
| `--generator` | 数据生成器 |
| `--out-dir` | 评测记录输出目录 |
| `--timeout` | 单例超时秒数 |
| `--compiler` | C++ 编译器 |
| `--std` | C++ 标准 |
| `--seed` | 生成器随机种子 |
| `--submission` | 提交次数/记录编号 |
| `--build-dir` | 编译临时目录 |
| `--keep-build` | 保留编译和运行中间文件 |

面向用户的常规数据来源后来收敛为：

```text
--in-dir
--generator
```

二者必须二选一。

---

## 5. 输出规则

### 5.1 测试数据

使用 `--in-dir` 或 `--generator` 时，对拍器自动保存：

```text
test_data\<题号>\cases.json
```

### 5.2 评测记录

默认输出：

```text
evaluation_records\<题号>\<题号>_diff_<时间戳>_submission_<次数>.md
```

提交次数规则：

- 不指定 `--submission` 时自动递增；
- 指定 `--submission N` 时使用指定编号；
- 更换输出目录后，编号按新目录重新计算。

---

## 6. 数据生成器规范

生成器统一放在：

```text
diff_runner\generators\<题号>_generator.py
```

生成器必须实现：

```python
def generate_cases(seed=None):
    ...
    return cases
```

返回值可以是：

```text
list[dict]
list[str]
```

每个用例的 `input` 必须是一次完整运行的标准输入。

生成器要求：

- 严格符合题目输入格式和约束；
- 使用 seed 保证可复现；
- 不向标准输出打印调试信息；
- 生成数据由对拍器自动保存到 `test_data\<题号>\cases.json`。

---

## 7. 用户自有输入规范

用户只需要在题目文件夹下建立：

```text
<题号>\IN\
```

并在其中放置 `.in` 文件。

对拍器通过：

```text
--in-dir <题号>\IN
```

自动读取并转换。

要求：

- 不需要用户编写 JSON；
- 不需要用户提供 `.out`；
- `.in` 内容必须是完整标准输入。

---

## 8. 文档体系

当前文档分工：

| 文件 | 面向对象 | 作用 |
|---|---|---|
| `diff_runner\README.md` | 人 | 对拍器简介、基本用法、参数、输出 |
| `diff_runner\AGENT_USAGE.md` | Agent | 详细操作流程、参数总表、生成器规范、目录责任 |
| `AGENTS.md` | Agent | 文件发现、数据来源选择、非 AC 讲解、讨论记录、实验限制 |
| 根目录 `Readme.md` | 人 | 项目总览、架构、快速使用、支持范围 |

统一原则：

```text
所有命令使用相对路径。
```

---

## 9. AGENTS.md 规则演进

### 9.1 文件发现

题目文件夹中必须存在：

```text
<题号>.cpp
<题号>.md
<题号>_correct.cpp 或 <题号>_solution.cpp
```

缺少必选文件时，停止并报告，不得编造。

### 9.2 可选输入

可选目录：

```text
<题号>\IN\
```

有 `.in` 时优先使用；没有时使用生成器。

### 9.3 数据来源

- 有 `IN`：使用 `--in-dir`；
- 无 `IN`：使用 `--generator`；
- 对拍器自动保存 `test_data\<题号>\cases.json`。

### 9.4 非 AC 讲解

对非 AC 记录进行讲解：

- WA：结合具体结果分析；
- TLE：分析用户代码的时间复杂度；
- RE：分析造成 RE 的原因；
- 参考 TLE / 参考 RE：同样需要讲解题解程序的问题；
- 当前不主动检测 MLE。

### 9.5 讨论记录

如果用户要求整理讨论，保存为：

```text
discussion_records\<题号>\BUGLOG.md
```

### 9.6 实验限制

未经明确批准，禁止修改：

```text
<题号>.cpp
<题号>_solution.cpp
```

Agent 只负责生成测试脚本、生成数据、运行对拍和整理记录。

### 9.7 数据规模

默认：

```text
200 份样例
180 份普通样例
20 份极端/边界样例
```

用户要求更高强度时：

```text
100 份边界或极端样例
```

---

## 10. 图论数据生成规则

`AGENTS.md` 增加了图论极端样例规则，要求覆盖：

- 链式结构；
- 菊花图 / 星型图；
- 网格图；
- 不连通图；
- 重边与自环；
- `N=1, M=0`；
- `N=0`（题目允许时）。

生成逻辑约束：

- 先生成随机生成树，再额外加边；
- 如果生成逻辑与题目特殊约束冲突，优先遵守题目约束。

---

## 11. 辅助工具

已提供：

```text
diff_runner\tools\cases_from_in.py
```

用途：

```text
把 .in 文件转换为内部 cases 格式。
```

普通用户不需要使用它，因为 `--in-dir` 已内置转换逻辑。

---

## 12. 验证记录

对拍器进行过端到端验证：

- 配置方式可以编译、运行、比较并生成记录；
- 生成器模式可以自动保存 cases 数据；
- 提交次数可以自动递增；
- 评测记录可以正常写入 `evaluation_records\<题号>\`；
- 文档中的相对路径命令可以运行。

---

## 13. 安全检查

已经检查 `diff_runner` 及工作区文本文件，未发现：

- API key；
- token；
- 密码；
- 私钥；
- 凭据文件；
- `.env` 文件；
- 硬编码的账号信息。

对拍器本身：

- 不访问网络；
- 不调用 LLM API；
- 只做本地编译、运行、比较和记录。

---

## 14. 当前限制与待办

当前不支持：

- 多解题目；
- Special Judge；
- 交互题；
- 主动 MLE 检测。

待改进：

- 进一步统一 `test_data` 目录命名；
- 考虑增加 `--dataset` 或 `--cases-out` 来区分同一道题的多套数据；
- 清理早期手动测试遗留文件；
- 避免在面向用户的文档中暴露内部 JSON 细节。

---

## 15. 架构决策：工具与内容分离（工作区外置，待实施）

> 状态：**方向已定，尚未实施**。本节记录讨论结论，供下一步开发使用。

### 15.1 现状问题

- 引擎 `diff_runner` 同时存在于两个仓库（`Judge` 与 `AIOJ_release`），两份代码已分叉。
- `AIOJ_release` 作为对外发布仓库，仍混有题目专属生成器（`diff_runner/generators/*.py`）。
- 产物（`test_data`、`evaluation_records`）默认写在「工具自身所在目录」，导致工具仓库越跑越脏；已有约 76MB 产物被 git 跟踪。
- 没有 `.gitignore`，`__pycache__` 等中间文件也被跟踪。

### 15.2 硬前提

引擎必须支持「产物写到指定工作区」，即引入 `--workspace`（或等价的工作区配置）。
否则外置工具跑题目时，`cases.json` 与评测记录会写回工具仓库本身，分离方案不成立。

### 15.3 目标拓扑

- `AIOJ_release/`（公开，工具唯一真源）
  - `AGENTS.md`：教练规则（对外模板，不可替换）
  - `Readme.md`、`.gitignore`
  - `diff_runner/`：引擎与文档，不含任何以题号命名的文件；周任务题目材料（含二进制产物）统一放入 `week_log/`
- `AIOJ_workspace/`（私有，新建的做题仓库）
  - `AGENTS.md`：教练规则（真正的工作区规则）
  - `aioj.workspace.json`：工作区配置，声明各目录
  - `problems/<题号>/`：题面、用户代码、题解代码
  - `_local/`：生成器、测试数据、评测记录、聊天整理（gitignore）
  - `discussion_records/`：整理后的 BUGLOG（是否入库待定）

### 15.4 四点计划的可行性

| 编号 | 计划 | 可行性 | 关键条件 |
|---|---|---|---|
| 1 | 新配置文件，把题目放到仓库外 | 可行 | 需要 `--workspace` 或工作区配置；现有 `--config` 只支持单题 |
| 2 | 生成器单独文件夹并 gitignore | 可行 | 引擎无需改动；`--generator` 本就接受任意路径 |
| 3 | 测试数据、聊天记录、评测记录同理 | 可行 | 需要 `--workspace` 与 `--cases-out`，否则写回工具仓库 |
| 4 | 单独开仓库存放做题代码版本迭代 | 可行且推荐 | 即上图的 `AIOJ_workspace` |

### 15.5 实施步骤

1. 引擎（在 `AIOJ_release` 内）：新增 `--workspace`，把 `test_data`、`evaluation_records` 默认挂到工作区下；保留 `--out-dir`、`--cases-out` 覆盖；移植 `Judge` 中的 `--dataset`、`--cases-out` 增量。
2. 清理 `AIOJ_release`：删除 `diff_runner/generators/`，新增 `.gitignore`，取消跟踪 `__pycache__`。
3. 新建 `AIOJ_workspace`：按 15.3 建目录，放入教练版 `AGENTS.md`、工作区配置、题目文件夹与生成器。
4. 联调：在工作区内使用外置工具跑一次，确认产物全部落在工作区，工具仓库 `git status` 干净。
5. 收敛旧仓库：处理 `Judge`（`AIOJ_local`）中的重复引擎与 76MB 产物。

### 15.6 风险与注意

- 生成器与记录一旦 gitignore，clone 到新机器不会带过来；需接受「可重新生成」，或选择部分入库。
- 教练版 `AGENTS.md` 属于「工作区」，应随做题仓库走；不能用开发规则顶替它。
- 开发规则（不许乱加功能、改完必须回归测试等）不占 `AGENTS.md` 主内容，可放本日志或作为文末小节。
- 顺序不可颠倒：先有 `--workspace`，再删 `Judge` 中的引擎副本。

### 15.7 待办（下一个迭代）

- [ ] 实现 `--workspace`（引擎）。
- [ ] 移植 `--dataset` / `--cases-out` 到 `AIOJ_release`。
- [ ] `AIOJ_release` 新增 `.gitignore`、移除生成器。
- [ ] 新建 `AIOJ_workspace` 并完成一次端到端联调。

---

## 16. 工作区方案细化：配置、搬家与 --workspace 的职责边界

> 补充第 15 节。状态：**设计已定，待实施**。

### 16.1 三件事必须分清

| 工作 | 由谁完成 | 频率 |
|---|---|---|
| 把题目、生成器等数据搬进个人仓库 | 手动搬一次 | 一次性 |
| 写一份「地址簿」，声明数据在哪、产出存哪 | 配置文件 | 一次性 |
| 让引擎真的按地址簿读写，而不是写回工具自身目录 | `--workspace`（需开发） | 引擎改一次 |

结论：配置文件本身不会搬运数据，也不能改变引擎的写入位置。

### 16.2 一句话原则

**config 是纸，`--workspace` 是腿。只有纸，引擎不会走路。**

### 16.3 现有 --config 的局限

- 现有 `--config` 是「一道题一份配置」，题目多时非常啰嗦。
- 即使配置里写了外部路径，产出（`cases.json`、评测记录）仍会写回工具自身目录，因为 `project_root()` 写死为工具上级目录。

### 16.4 工作区配置草案（待实现）

拟新增一份工作区级配置，例如置于个人仓库根目录：`aioj.workspace.json`

```json
{
  "workspace": ".",
  "problems_dir": "problems",
  "data_dir": "_local/test_data",
  "records_dir": "_local/evaluation_records",
  "timeout": 10,
  "compiler": "g++",
  "std": "c++17"
}
```

约定：

- `problems_dir`：题目目录，按 `problems/<题号>/<题号>.cpp` 等命名规则存放。
- `data_dir`：测试数据 `cases.json` 的存放位置。
- `records_dir`：评测记录的输出位置。
- 生成器既可放在 `problems/<题号>/` 内，也可放在单独的 `_local/generators/`。

### 16.5 目标调用方式

```
python D:/AIOJ_release/diff_runner/diff_runner.py --workspace D:/AIOJ_workspace --name UVA10364
```

引擎按工作区约定自动定位题面、用户代码、题解代码与生成器，并把全部产出写入 `_local/`。

### 16.6 安全注意

- `aioj.workspace.json` 属于个人仓库，**不得提交到公开的 `AIOJ_release`**，否则会暴露本机私有路径。
- 教练版 `AGENTS.md` 随工作区（个人仓库）走；`AIOJ_release` 里保留一份作为对外模板。

### 16.7 开工清单（在 Release 版开始前）

- [ ] 在 `AIOJ_release` 中实现 `--workspace`。
- [ ] 移植 `--dataset` / `--cases-out`。
- [ ] 新增 `.gitignore`，移除 `diff_runner/generators/` 与 `__pycache__`。
- [ ] 新建 `AIOJ_workspace`，放入工作区配置与教练版 `AGENTS.md`。
- [ ] 端到端联调：确认工具仓库 `git status` 干净。

---

## 17. 目标拓扑修订：题目用绝对路径，其余可默认可覆盖

> 本节修订第 15.3 节与第 16.4 节；如有冲突，**以本节为准**。
> 背景：负责人现有题目全部位于 `D:/ICPC case` 相关目录，**不希望重建新工作区**。

### 17.1 修订原则

1. 不强制新建工作区，直接指向现有目录。
2. 题目所在路径由用户填写**绝对路径**，最灵活，跨盘、跨目录均可。
3. 生成器、聊天记录、评测记录、测试数据都有**默认位置**，同时**允许用户覆盖**。

### 17.2 修订后拓扑

```
D:/ICPC case/Judge/                ← 现有目录，直接当工作区用，不重建
├── aioj.workspace.json            ← 新增：地址簿（建议 gitignore）
├── P9228/  UVA10364/ ...          ← 题目，原地不动
├── generators/                    ← 生成器（默认位置）
├── discussion_records/            ← 聊天 / 讨论整理（默认位置）
├── evaluation_records/            ← 评测记录（默认位置）
└── test_data/                     ← 测试数据（默认位置）

D:/AIOJ_release/                   ← 工具（公开，唯一真源；`week_log/` 为周任务题目材料（含二进制产物）唯一例外，其余位置不含题目）
└── diff_runner/diff_runner.py
```

### 17.3 配置项设计

| 配置键 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `workspace` | 否 | 配置文件所在目录 | 工作区根，下列默认值的基准 |
| `problems_dir` | 建议填 | 缺省时取 `workspace` | **题目所在目录，支持绝对路径** |
| `generators_dir` | 否 | `<workspace>/generators` | 生成器存放位置 |
| `discussion_dir` | 否 | `<workspace>/discussion_records` | 聊天 / 讨论整理存放位置 |
| `records_dir` | 否 | `<workspace>/evaluation_records` | 评测记录输出位置 |
| `data_dir` | 否 | `<workspace>/test_data` | 测试数据 `cases.json` 输出位置 |
| `timeout` | 否 | `10` | 默认超时秒数 |
| `compiler` | 否 | `g++` | 默认编译器 |
| `std` | 否 | `c++17` | 默认语言标准 |

### 17.4 示例配置

`D:/ICPC case/Judge/aioj.workspace.json`：

```json
{
  "problems_dir": "D:/ICPC case/Judge",
  "generators_dir": "D:/ICPC case/Judge/generators",
  "discussion_dir": "D:/ICPC case/Judge/discussion_records",
  "records_dir": "D:/ICPC case/Judge/evaluation_records",
  "data_dir": "D:/ICPC case/Judge/test_data",
  "timeout": 10,
  "compiler": "g++",
  "std": "c++17"
}
```

只需 `problems_dir` 一项也能运行；其余不写，自动落到默认位置。

### 17.5 调用方式

```
python D:/AIOJ_release/diff_runner/diff_runner.py --workspace-config "D:/ICPC case/Judge/aioj.workspace.json" --name UVA10364
```

命令行参数优先级高于配置文件。

### 17.6 规则

- `problems_dir` 支持绝对路径；相对路径按配置文件所在目录解析。
- 默认位置都挂在 `workspace` 之下；用户修改 `workspace` 或对应键，默认位置随之改变。
- 不提供配置文件时，保持旧行为（相对工具上级目录），保证向后兼容。
- `aioj.workspace.json` 属于个人数据，应加入 `.gitignore`，不得提交到公开的 `AIOJ_release`。

### 17.7 连带影响

- `diff_runner/generators/` 中的生成器迁出到工作区 `generators/`（默认位置）。
- `AGENT_USAGE.md`、`AGENTS.md` 中生成器路径约定同步更新。
- 引擎新增 `--workspace-config`，并可提供单项覆盖参数（如 `--problems-dir`）。

### 17.8 待办（更新）

- [ ] 实现工作区配置读取与默认路径推导。
- [ ] 实现 `--workspace-config`（及单项覆盖参数）。
- [ ] 让产出（`data_dir` / `records_dir`）遵循配置，不再写回工具目录。
- [ ] 迁移现有生成器到工作区 `generators/`。
- [ ] `AIOJ_release` 新增 `.gitignore`，移除生成器与 `__pycache__`。

### 17.9 现状勘察（2026-10-11）

对 `D:/ICPC case` 实测，题目存放形态**并不统一**：

| 目录 | 形态 | 是否适用 AIOJ |
|---|---|---|
| `Judge/P9228/`、`Judge/UVA10364/` | 完整题目文件夹（题面 + 用户代码 + 题解） | 适用 |
| `Luogu/*.cpp` | 散装单文件，只有一份代码，无题面、无题解 | 不适用 |
| `MATIJI/BD202401.cpp` | 散装单文件 | 不适用 |
| `blog/` | 题解博客与文档 | 不适用 |

结论：

- `problems_dir` 应指向 `D:/ICPC case/Judge`，**不能**指向 `D:/ICPC case`，否则 `blog`、`Luogu`、`MATIJI` 会被误判为题目文件夹。
- 散装 `.cpp` 目录（`Luogu`、`MATIJI`）暂不纳入工作区；若日后需要，需另开「散装模式」，或在迁移时补成 `<题号>/` 结构。
- 待负责人确认：`Luogu` / `MATIJI` 中的散装代码是否需要 AIOJ 支持。

---

## 18. 实施规格：工作区配置（交接给新对话的 AI）

> 本节是**自包含的实施说明书**。新对话中的 AI 只读本节即可开工，无需之前的聊天记录。
> 如与第 15 / 16 / 17 节冲突，以本节为准。

### 18.1 任务一句话

给 `diff_runner` 增加「工作区配置」能力：由一份 JSON 声明题目目录与各类输出目录，使工具可脱离自身安装目录运行，并把全部产物写到指定位置。

### 18.2 背景与现状（必读）

- 工具真源：`D:/AIOJ_release/diff_runner/diff_runner.py`（对应公开仓库 AIOJ_release）。
- 工作区（现有，不重建）：`D:/ICPC case/Judge/`，内含题目文件夹 `<题号>/`（如 P9228、UVA10364）。
- 当前问题：`project_root()` 写死为「工具所在目录的上一级」，产出（`test_data/`、`evaluation_records/`）永远写回工具目录。
- 另有一份副本 `D:/ICPC case/Judge/diff_runner/diff_runner.py`，含未验收的 `--dataset` / `--cases-out` 增量，已与 release 版分叉。**开工前必须先处理这个分叉。**

### 18.3 已拍板，不要再改

1. 配置文件名：`aioj.workspace.json`（不要用 `config.json`，避免与已有 `--config` 混淆）。
2. 位置：工作区根目录，例如 `D:/ICPC case/Judge/aioj.workspace.json`。
3. 该文件含本机绝对路径，**必须 gitignore，不得提交到公开仓库**。
4. 路径一律使用正斜杠 `/`；反斜杠写法在 JSON 中需转义成两个连续反斜杠，易错，不推荐但应兼容。

### 18.4 配置字段与默认值

| 字段 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `workspace` | 否 | 配置文件所在目录 | 工作区根，下列默认值的基准 |
| `problems_dir` | 建议填 | 取 `workspace` | 题目文件夹集合所在目录，支持绝对路径 |
| `generators_dir` | 否 | `<workspace>/generators` | 生成器存放位置 |
| `discussion_dir` | 否 | `<workspace>/discussion_records` | 聊天 / 讨论整理存放位置 |
| `records_dir` | 否 | `<workspace>/evaluation_records` | 评测记录输出位置 |
| `data_dir` | 否 | `<workspace>/test_data` | 测试数据 `cases.json` 输出位置 |
| `timeout` | 否 | `10` | 默认超时秒数 |
| `compiler` | 否 | `g++` | 默认编译器 |
| `std` | 否 | `c++17` | 默认语言标准 |

示例配置：

```json
{
  "problems_dir": "D:/ICPC case/Judge",
  "generators_dir": "D:/ICPC case/Judge/generators",
  "discussion_dir": "D:/ICPC case/Judge/discussion_records",
  "records_dir": "D:/ICPC case/Judge/evaluation_records",
  "data_dir": "D:/ICPC case/Judge/test_data",
  "timeout": 10,
  "compiler": "g++",
  "std": "c++17"
}
```

只写 `problems_dir` 也能运行，其余字段走默认值。

### 18.5 路径解析规则

- 配置文件中的路径：绝对路径直接使用；相对路径相对 `workspace` 解析。
- `workspace` 缺省时取配置文件所在目录。
- 命令行参数优先级高于配置文件。
- 不传配置文件、且未找到默认配置时，保持旧行为（工具上级目录），确保向后兼容。

### 18.6 命令行接口

- 新增 `--workspace-config <文件路径>`：显式指定工作区配置。
- 若未提供该参数，但当前工作目录下存在 `aioj.workspace.json`，则自动加载。
- 其余命令行参数保持不变，且可覆盖配置项。

目标效果：

```
python D:/AIOJ_release/diff_runner/diff_runner.py --workspace-config "D:/ICPC case/Judge/aioj.workspace.json" --name UVA10364
```

### 18.7 命名约定（据配置自动定位题目文件）

当用户只给 `--name <题号>`、未显式给出各文件路径时，按以下规则推导：

- 题面：`<problems_dir>/<题号>/<题号>.md`
- 用户代码：`<problems_dir>/<题号>/<题号>.cpp`
- 题解代码：`<problems_dir>/<题号>/<题号>_correct.cpp`，找不到则回退 `<题号>_solution.cpp`
- 数据来源（与 AGENTS.md 一致）：
  - 若 `<problems_dir>/<题号>/IN/` 内存在 `.in` 文件，走 `--in-dir` 行为；
  - 否则若 `<generators_dir>/<题号>_generator.py` 存在，走生成器；
  - 否则若 `<problems_dir>/<题号>/<题号>_generator.py` 存在，走生成器；
  - 都没有则报错，并清晰说明缺了什么，不得编造。
- 显式传入的 CLI 路径优先于上述约定。

### 18.8 产物落点

- 测试数据：`<data_dir>/<题号>/cases.json`
- 评测记录：`<records_dir>/<题号>/<题号>_diff_<时间戳>_submission_<次数>.md`
- 目录不存在时自动创建；工具自身目录不得再出现任何产物。

### 18.9 验收标准

验收标准已统一收敛到 `AGENTS.md` 第 9 节（唯一权威）。
修改引擎后，请直接对照 `AGENTS.md` 第 9 节的验收清单逐条自测；
本节不再重复维护，避免两处不同步。

### 18.10 红线

- 不联网、不调用任何 API、不写入任何密钥。
- 不破坏现有命令行参数与输出格式。
- 不修改题目源码（`<题号>.cpp`、`<题号>_solution.cpp`）。
- 未经批准不新增功能（Special Judge、MLE、交互题、多解均不在本次范围）。
- 不把 `aioj.workspace.json` 或任何含绝对路径的文件提交到公开仓库。

### 18.11 开工前第一步

处理 `Judge` 与 `AIOJ_release` 两份 `diff_runner.py` 的分叉：决定 `--dataset` / `--cases-out` 增量是并入 release 版还是丢弃，然后统一为一份真源。

---

## 19. 开发要求（最新，v2）

> 本节为负责人新下达的开发要求，细化并部分修订第 17、18 节。如与前面章节冲突，**以本节为准**。

### 19.1 要求一：题目文件按配置中的绝对路径查找

- **取消**「在当前工作区内搜索 `<题号>/` 文件夹」的旧逻辑。
- 题目文件根据 `aioj.workspace.json` 中的 `problems_dir`（**绝对路径**）定位：
  - 题面：`<problems_dir>/<题号>/<题号>.md`
  - 用户代码：`<problems_dir>/<题号>/<题号>.cpp`
  - 题解代码：`<problems_dir>/<题号>/<题号>_correct.cpp`，找不到则回退 `<题号>_solution.cpp`
- 命令行显式传入的路径仍然优先。

### 19.2 要求二：各类目录写入配置，可自由修改

以下目录以**绝对路径**存放在 `aioj.workspace.json` 中，默认位置为「本工作区」内：

| 用途 | 配置字段 | 默认位置 |
|---|---|---|
| 测试数据 | `data_dir` | `<工作区>/test_data` |
| 聊天记录整理 | `discussion_dir` | `<工作区>/discussion_records` |
| 评测记录 | `records_dir` | `<工作区>/evaluation_records` |
| 生成器 | `generators_dir` | `<工作区>/generators` |

- 用户可自行修改任意一项。
- **`Readme.md` 必须展示如何修改这些路径**（给出示例配置）。

「本工作区」的定义：**存放 `aioj.workspace.json` 的目录**。

### 19.3 要求三：仓库放模板，本机放私有配置

| 文件 | 是否入库 | 用途 |
|---|---|---|
| `template.aioj.workspace.json` | 是 | 上传 GitHub 的模板 |
| `aioj.workspace.json` | 否 | 本机私用，含绝对路径 |

- **`Readme.md` 必须写明**：使用前先把 `template.aioj.workspace.json` **复制并重命名为** `aioj.workspace.json`，再按需修改其中的路径。

### 19.4 要求四：新增 `.gitignore`

截留以下内容，保证「本地能用、仓库干净」：

- `aioj.workspace.json`（含本机绝对路径）
- `test_data/`
- `discussion_records/`
- `evaluation_records/`
- `__pycache__/`
- `*.pyc`

### 19.5 实施细节（据以上要求推导）

1. 配置文件缺省时：若用户只给 `--name`，报清晰错误，提示「请先复制 `template.aioj.workspace.json` 为 `aioj.workspace.json`」；若用户显式给出全部文件路径，仍可运行。
2. 配置缺失时的输出默认基准：当前工作目录（cwd）。**此点修订第 18.5 节。**
3. `template.aioj.workspace.json` 中不得包含任何本机绝对路径，只放相对形式或占位说明。

### 19.6 备注 / 待确认

- `discussion_records/` 若整体 gitignore，则整理后的 BUGLOG 也不会入库。若希望保留精华笔记，需在 `.gitignore` 中开例外（例如 `!discussion_records/**/BUGLOG.md`）。**待负责人确认。**
- `template.aioj.workspace.json` 的字段说明是否也在 `Readme.md` 中完整列出？**待确认。**

### 19.7 待办

- [ ] 引擎：题目路径改为读 `problems_dir`。
- [ ] 引擎：输出目录改为读配置，默认落在工作区。
- [ ] 引擎：`--workspace-config`，并在缺省时给出清晰报错。
- [ ] 仓库：新增 `template.aioj.workspace.json`。
- [ ] 仓库：新增 `.gitignore`。
- [ ] 文档：`Readme.md` 补充「重命名模板」与「修改路径」两节。

---

## 20. 开发要求补充：多题目路径

> 补充并修订第 17.3、19.1、19.2 节中 `problems_dir` 的单路径设定。如冲突，**以本节为准**。

### 20.1 背景

负责人按平台分文件夹存放题目，例如：

```
D:/ICPC case/
├── Judge/      完整题目文件夹（<题号>/ 结构）
├── Luogu/      散装单文件（<题号>.cpp，无题面、无题解）
└── MATIJI/     散装单文件
```

题目可能位于任意平台文件夹内，因此配置需支持多个路径。

### 20.2 多路径配置

```json
{
  "problems_dirs": [
    "D:/ICPC case/Judge",
    "D:/ICPC case/Luogu",
    "D:/ICPC case/MATIJI"
  ]
}
```

- 优先使用数组键 `problems_dirs`。
- 兼容旧的单路径字符串 `problems_dir`，内部归一化为单元素列表。
- 每个路径均支持绝对路径。

### 20.3 匹配规则（负责人决定：暂不特殊处理重名）

- 按 `problems_dirs` 中的**顺序**依次查找 `<题号>/`。
- **取第一个命中的路径**，立即使用，不再继续查找。
- 暂时**不做**「多个平台同一题号」的冲突检测（负责人日常主要在洛谷，实际不会触发）。
- 若日后需要，可再补「多命中报错 / 让用户选择」。

### 20.4 散装单文件处理策略（路线 A）

负责人选择【路线 A】：

- 散装单文件（`<题号>.cpp` 直接躺在平台文件夹里）**暂不支持对拍**，因为 AIOJ 需要题解作为参照。
- 以后逐步「装修」为 `<题号>/` 结构：

```
Luogu/B3621/
├── B3621.md            题面
├── B3621.cpp           用户代码
└── B3621_correct.cpp   题解
```

- 装修完某平台的某个题目后，再将该平台文件夹加入 `problems_dirs`。
- 未装修的散装文件，AIOJ 暂不处理。

### 20.5 输出目录不需要多路径

- `data_dir`、`discussion_dir`、`records_dir`、`generators_dir` 仍各自只有一个路径（见第 19.2 节）。
- 题目来源可以多个，产出目录只需一个。

### 20.6 待办

- [ ] 引擎：`problems_dirs` 支持数组，并兼容字符串 `problems_dir`。
- [ ] 引擎：按顺序取第一个命中。
- [ ] `template.aioj.workspace.json` 使用数组写法展示。
- [ ] `Readme.md` 说明多路径与散装文件的限制。
- [ ] 长期：逐步装修各平台文件夹中的散装代码。
- [ ] 引入超出限制内存(MLE) ， 参考MLE
- [ ] 引入根据每道题调整Time Limit

---

## 21. TLE 检测方案决议（2026-10-11）

> 本节记录负责人对 Time Limit 传递方式的决定。如与第 14、20.6 节冲突，以本节为准。

### 21.1 决议

- **不做动态测定 Time Limit**：不通过参考题解耗时自动推导 TL。
- 用户可以通过在题目 Markdown 文件里使用【方案 B：AIOJ 专用 HTML 注释】补充题面没有的 Time Limit。
- 注释格式示例：

```markdown
<!-- AIOJ-META
TL: 1.00s
ML: 256MB
-->
```

- 当前主要使用 `TL` 标签；`ML` 为后续 MLE 功能预留。
- 评测机读到题面 `TL` 标签后，优先使用该 Time Limit。
- 如果题面没有 `TL` 标签，则使用 workspace 配置中的 `timeout`。
- workspace 默认 `timeout` 从 `10s` 改为 `1s`。
- 不联网获取洛谷等平台的 Time Limit；题面没有就使用默认值，或由用户手动补充 `AIOJ-META`。

### 21.2 优先级（负责人本次明确部分）

1. 题面 `AIOJ-META` 中的 `TL`
2. workspace 配置中的 `timeout`
3. 默认值 `1s`

说明：负责人本次只明确“题面 `TL` 优先于 workspace 默认值”。  
现有的 CLI `--timeout` 是否仍保留最高优先级，属于向后兼容细节，实施前需再与负责人确认。

### 21.3 实现要点

- 只解析 HTML 注释块 `AIOJ-META` 内部的 `TL:` / `Time Limit:` / `时间限制:` 行。
- 支持单位 `s`、`ms`、`秒`、`毫秒`，统一换算为秒。
- 不在题面正文中全文裸匹配 `TL:`，避免把正文误认成元数据。
- 找不到 `TL` 标签时，不得编造 Time Limit。
- 评测记录里建议写明本次 TL 来源，例如：
  - `problem-html-meta`
  - `workspace-default`
- 评测记录继续保留“单例超时”字段。

### 21.4 后续相关待办

- [ ] 实现题面 `AIOJ-META` 解析。
- [ ] 将 workspace 默认 `timeout` 从 `10` 改为 `1`。
- [ ] 更新 `template.aioj.workspace.json` 与 `Readme.md` / `AGENT_USAGE.md` 中的默认值说明。
- [ ] 后续 MLE 复用同一 `AIOJ-META` 注释块，增加 `ML` 字段。

### 21.5 不采用：用户手工维护 `<题号>.meta.json`

负责人明确：用户不太可能为每道题单独维护一份 `meta.json`，能顺手在题面里写 `AIOJ-META` 的 TL/ML 已经很好了。因此：

- 不把 `<题号>.meta.json` 作为面向用户的常规配置入口；
- 用户只需在题面里写 `AIOJ-META` 的 TL/ML；
- 如果题面没有 `TL`，则使用 workspace 默认 TL；
- 工具不自动生成、不自动修改 `<题号>.meta.json`；
- 未来如果出现本地元数据文件，只能作为可选的内部缓存或导入产物，不能反过来要求用户手工维护。

> 说明：此前讨论中出现的“用户可以自己配置 `<题号>.meta.json`”方案，从开发日志中移除，不作为用户侧需求。

### 21.6 Agent 输出免责声明

负责人要求：以后 Agent 在输出任何对拍/测评结果时，必须明确声明：

> 本次测评结果为本地对拍结果，不代表 OJ 官方测评结果，最终以实际平台提交结果为准。

实现要求：

- Agent 在聊天中展示 AC / WA / TLE / MLE / 参考TLE / 参考MLE 等结果时，必须附带该免责声明；
- 后续 `diff_runner` 生成的评测记录 Markdown 也应在“说明”部分自动加入同义声明；
- 不得把本地 AC 直接表述为“官方 AC”，也不得把本地 TLE 直接表述为“官方 TLE”；
- 如果本次 TL / ML 来自 workspace 默认值而不是题面 `AIOJ-META`，还应同时注明“该限制为非官方限制”；
- 该声明应作为以后的固定输出规范，不能因为结果看起来很好或很差而省略。
