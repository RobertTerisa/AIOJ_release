# AIOJ 使用说明

**事先声明！本项目的readme.md ， idea，agent.md是由本人我亲自起草，其余部分则是由ai生成！**


一.项目简介
本项目支持通过LLM阅读题目以生成样例，并将用户代码和正确答案进行对拍进行测评并结合具体样例进行讲题。具体评测受本机影响，不代表OJ结果。


二.项目架构
 - diff_runner:对拍器本体，内部的readme.md 提供了单独使用此对拍器的相关注意事项，AGENT_USAGE.md是面向agent的对拍器使用指南。diff_runner/generators 为生成器本体所在处。
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
    --generator diff_runner\generators\<题号>_generator.py `
    --seed 123 `
    --timeout 10
    ```


    --in-dir 和 --generator 二选一
5. 测试样例会自动保存至 test_data\<题号>\cases.json
6. 评测记录会自动保存到 evaluation_records\<题号>\<题号>_diff_<时间戳>_submission_<次数>.md
  
四.目前支持情况
- [x] 普通OJ题普通情况 
- [x] 普通OJ题极端情况
- [x] 非交互图论题普通情况
- [x] 非交互图论题极端情况(参见AGENTS.md中的<图论数据生成与极端样例规则>)
- [ ] 多解题目
- [ ] Special Judge外挂
- [ ] MLE检测
  该项目目前只支持非交互、批量输入输出的题目；
暂不支持交互题、多解题目和 Special Judge。

五.写在最后
这个项目起先是我在大一的某一天刷题的时候刷到UVA的题目，我自己没法注册账号还用不了Remote Judge，刚好电脑里有Deepseek Harness。我就让大肥鱼给我写个对拍器然后借用题解（我的博客里有提到）自己给自己评测一下，后来我觉得用LLM辅助学习算法很有意思，就让大肥鱼把对拍器的脚本单独整理出来复用，后面又编写Agent把我自己的学习流程和要点固定下来，就变成了现在这个Agent雏形。