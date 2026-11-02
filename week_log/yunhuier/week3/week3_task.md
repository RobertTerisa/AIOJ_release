
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
| 任务批次 | 第3周(2026.11.1) |
| 仓库地址 | `https://github.com/RobertTerisa/AIOJ_release.git` |
| 分支 | dev/prompts |


---

## 1. 每周任务
 - 使用之前的模板完成序列题目的递增递减 ， 递增要求$An < An+1$ ， 递减要求$An > An+1$ ,数据范围参考随机大。

## 2. 任务提示
- 生成序列时请使用long long以免int溢出，使用种子随机 ， A[i] = A[i-1] + rand(1, 100) , 请确保所有数据在之前规定的随即大的范围。