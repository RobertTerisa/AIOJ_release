
# 每周任务发布模板

> **用途**：记录下周任务清单。
> **使用方法**：
> 1. 复制到 `week_log/<执行者的目录>/<日期>_第X周任务日志.md`；
> 2. 证据统一放入week_log/Github用户名/week(X)/artifacts；
> 3. 日志中不要粘贴 API Key、token、私钥、`aioj.workspace.json` 原文或完整本机绝对路径。
> 4. 每周任务所需要的材料统一放入week_log/Github用户名/week(X)/materials

---

## 0. 元信息

| 字段 | 内容 |
|---|---|
| 负责人 | qdssl-1023 |
| 任务批次 | 第1周(2026.10.15) |
| 仓库地址 | `https://github.com/RobertTerisa/AIOJ_release.git` |
| 分支 | dev/diff_runner |


---

## 1. 每周任务
 - 阅读diff_runner里的Readme.md和AGENT_USAGE.md , 整理对拍器参数
 - 将materials中的文件放入工作区根目录,在命令行中使用第一种参数调用对拍器对拍UVA10364(见本周materials) ，关注并记录评测记录的位置以及名字。
 - 分别将UVA10364.cpp , UVA10364.md , UVA10364_solution.cpp从移出文件夹，参数指定原路劲，把对拍器返回的参数记录下来
 - 使用第二种工作区json配置的参数，关注能否对拍，将结果记录在开发日志
 - 将materials文件夹放入diff_runner文件夹内，只给 --name UVA10364 , 将运行结果记录下来。