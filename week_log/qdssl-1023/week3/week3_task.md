
# 每周任务发布模板

> **用途**：记录下周任务清单。
> **使用方法**：
> 1. 复制到 `week_log/<执行者的目录>/<日期>_第X周任务日志.md`；
> 2. 证据统一放入week_log/Github用户名/week(X)/artifacts；
> 3. 日志中不要粘贴 API Key、token、私钥、`aioj.workspace.json` 原文或完整本机绝对路径。
> 4. 每周任务所需要的材料（含二进制产物）统一放入week_log/Github用户名/week(X)/materials；仓库内不得放置题目文件

---

## 0. 元信息

| 字段 | 内容 |
|---|---|
| 负责人 | qdssl-1023 |
| 任务批次 | 第3周(2026.11.1) |
| 仓库地址 | `https://github.com/RobertTerisa/AIOJ_release.git` |
| 分支 | dev/diff_runner |


---

## 1. 每周任务
 - 实现对题目.md里面 <!-- AIOJ-META TL: ML:-->标签的解析，解析出Time Limit ，并使解析出的time limit为第一优先级。该标签并非强制要求，应该为可选项。
 - 新建UVA10364.md ,里面写上 < !-- AIOJ-META TL:0.001s --> 再复制UVA10364.cpp , 更名为UVA10364_solution.cpp , 用workspace的方式运行对拍器。观察改动能否让题解tle。然后移除该标签使markdown为空文件，运行对拍器观察能否正常根据workspace的time limit(1.00s)对拍。上述完成即算测试通过。
 - 任务完成情况写入任务日志。