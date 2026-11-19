
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
| 任务批次 | 第5周(2026.11.18) |
| 仓库地址 | `https://github.com/RobertTerisa/AIOJ_release.git` |
| 分支 | dev/prompts |


---

## 1. 每周任务
 - 编写CLI化(同week4要求)的数据生成器，要求传入 N , i_min , i_max后按照如下方法构造长度为N的序列
   - 1.定义区间1为[i_max - (i_max - i_min)*3/10 , i_max] , 区间2为[i_min , i_min + (i_max-i_min)*3/10]
   - 2.先布尔随机，0表示从区间1取，1表示从区间2取，
   - 3.接着根据上一步的布尔随机值从1和2中取随机数
   - 4.如果区间范围不够静默退化成随机。