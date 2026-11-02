
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
| 负责人 | yunhuier |
| 任务批次 | 第4周(2026.11.1(提前布置)) |
| 仓库地址 | `https://github.com/RobertTerisa/AIOJ_release.git` |
| 分支 | dev/prompts |


---

## 1. 每周任务
- 读取数据生成器(./generator)里的Readme.md , 明确序列数据生成器需要获取的参数，将之前定下的常量改为通过外部CLI传递参数。