# AIOJ 使用说明

**事先声明！本项目的readme.md ， idea，agent.md是由本人我亲自起草，其中题号文件夹是我个人测试用的代码。其余部分则是由ai生成！**


一.项目简介
本项目支持通过LLM阅读题目以生成样例，并将用户代码和正确答案进行对拍进行测评并结合具体样例进行讲题。具体评测受本机影响，不代表OJ结果。


二.项目架构
 - diff_runner:对拍器本体，内部的readme.md 提供了单独使用此对拍器的相关注意事项，AGENT_USAGE.md是面向agent的对拍器使用指南。题目专用生成器现在放在工作区配置的 generators_dir 下，工具仓库本身不放题号文件。
 - discussion_records:用于存放人机交互记录
 - evaluation_records:用于存放对拍记录
 - test_data:用于存放生成器生成的对拍数据
 - AGENTS.md

三.项目使用说明


1. 题目应建立文件夹放在当前目录内，文件夹名字即为题号，在文件夹内应放置3个文件：
   - 题号.cpp:该文件为用户所写的代码
   - 题号_correct.cpp或题号_solution.cpp:该文件为题解代码，用于对拍。
   - 题号.md:题面，用于生成数据。
  

2. 数据来源于以下两处：
   - 用户在题目文件夹中建立IN文件夹并在其中放置包含样例的.in文件
   - 生成器自动生成样例
  

3. 对拍器调用命令
    ```
    python diff_runner\diff_runner.py `
    --name <题号> `
    --problem-md <题号>\<题号>.md `
    --user <题号>\<题号>.cpp `
    --correct <题号>\<题号>_correct.cpp `
    --in-dir <题号>\IN `
    --timeout 10
    ```
    如果题解文件叫 <题号>_solution.cpp，
则把 --correct <题号>\<题号>_correct.cpp
改成 --correct <题号>\<题号>_solution.cpp


4. 生成器模式

    ```
    python diff_runner\diff_runner.py `
    --name <题号> `
    --problem-md <题号>\<题号>.md `
    --user <题号>\<题号>.cpp `
    --correct <题号>\<题号>_correct.cpp `
    --generator <generators_dir>\<题号>_generator.py `
    --seed 123 `
    --timeout 10
    ```


    --in-dir 和 --generator 二选一
5. 测试样例会自动保存至 test_data\<题号>\cases.json
6. 评测记录会自动保存到 evaluation_records\<题号>\<题号>_diff_<时间戳>_submission_<次数>.md

### 三.5 工作区配置（推荐）

从 v2 开始，AIOJ 支持把「工具本体」和「题目内容、评测产物」分开放置。

使用前先复制模板并重命名：

```powershell
copy template.aioj.workspace.json aioj.workspace.json
```

`aioj.workspace.json` 所在的目录就是**工作区根目录**。按需修改其中的路径即可，例如：

```json
{
  "problems_dirs": [
    "D:/ICPC case/Judge",
    "D:/ICPC case/Luogu"
  ],
  "generators_dir": "D:/ICPC case/Judge/generators",
  "discussion_dir": "D:/ICPC case/Judge/discussion_records",
  "records_dir": "D:/ICPC case/Judge/evaluation_records",
  "data_dir": "D:/ICPC case/Judge/test_data",
  "timeout": 10,
  "compiler": "g++",
  "std": "c++17"
}
```

字段说明：

| 字段 | 是否必填 | 默认值 | 说明 |
|---|---|---|---|
| `workspace` | 否 | 配置文件所在目录 | 其他相对路径的基准 |
| `problems_dirs` | 建议填 | 工作区根目录 | 题目文件夹集合，数组，按顺序查找 |
| `problems_dir` | 否 | - | 旧的单路径写法，仍兼容 |
| `generators_dir` | 否 | `<工作区>/generators` | 生成器目录 |
| `discussion_dir` | 否 | `<工作区>/discussion_records` | 讨论整理目录 |
| `records_dir` | 否 | `<工作区>/evaluation_records` | 评测记录目录 |
| `data_dir` | 否 | `<工作区>/test_data` | 测试数据目录 |
| `timeout` | 否 | `10` | 默认超时秒数 |
| `compiler` | 否 | `g++` | C++ 编译器 |
| `std` | 否 | `c++17` | C++ 标准 |

路径解析规则：

- 绝对路径直接使用；
- 相对路径相对于 `workspace` 解析；
- 命令行参数优先于配置文件。

推荐调用方式：

```powershell
python <工具目录>\diff_runner\diff_runner.py `
  --workspace-config aioj.workspace.json `
  --name <题号>
```

如果当前目录就是工作区根目录，可以省略 `--workspace-config`，工具会自动读取当前目录的 `aioj.workspace.json`：

```powershell
python <工具目录>\diff_runner\diff_runner.py --name <题号>
```

题目定位规则：

- 按 `problems_dirs` 顺序查找第一个存在的 `<题号>/`；
- 题面：`<题号>/<题号>.md`；
- 用户代码：`<题号>/<题号>.cpp`；
- 题解：优先 `<题号>_correct.cpp`，找不到则回退 `<题号>_solution.cpp`；
- 数据来源：优先题目文件夹下的 `IN/*.in`，否则使用 `generators_dir/<题号>_generator.py`；
- 散装单文件（`<题号>.cpp` 直接放在平台目录里）暂不支持对拍，需要先整理成 `<题号>/` 结构。

产物默认落点：

- 测试数据：`<data_dir>/<题号>/cases.json`
- 评测记录：`<records_dir>/<题号>/<题号>_diff_<时间戳>_submission_<次数>.md`
- 讨论整理：`<discussion_dir>/<题号>/BUGLOG.md`（由 Agent 手动写入，工具不会自动写）

注意：

- `aioj.workspace.json` 含本机绝对路径，已被 `.gitignore` 忽略，不要提交；
- 找不到工作区配置且只给 `--name` 时，工具会报错并提示复制模板；
- 如果显式提供全部文件路径，旧命令仍然可以运行；
- `discussion_records/` 默认整体被 `.gitignore` 忽略；如果希望把某个 `BUGLOG.md` 提交到仓库，需要手动 `git add -f` 或添加 ignore 例外。

  
四.目前支持情况
- [x] 普通OJ题普通情况 
- [x] 普通OJ题极端情况
- [x] 非交互图论题普通情况
- [x] 非交互图论题极端情况(参见AGENTS.md中的<图论数据生成与极端样例规则>)
- [ ] 多解题目
- [ ] Special Judge外挂
- [ ] MLE检测
  该项目目前只支持非交互、批量输入输出的题目；






五.写在最后
这个项目起先是我在大一的某一天刷题的时候刷到UVA的题目，我自己没法注册账号还用不了Remote Judge，刚好电脑里有Deepseek Harness。我就让大肥鱼给我写个对拍器然后借用题解（我的博客里有提到）自己给自己评测一下，后来我觉得用LLM辅助学习算法很有意思，就让大肥鱼把对拍器的脚本单独整理出来复用，后面又编写Agent把我自己的学习流程和要点固定下来，就变成了现在这个Agent雏形。


