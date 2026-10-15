## 0.开发须知


 - 1. 本项目使用git进行版本维护，提交时请提交至对应分支(在下文会提及)，不要试图直接提交至main分支！
 - 2. 在没有被分配任务的情况下请不要修改AGENTS.md , develop_log , ChangingLog , template , diff_runner内所有文件。
 - 3. 本项目使用VScode + git + Python进行维护,git版本为2.53.0 Python版本为3.13.13 VScode版本保持最新即可,请确保以上依赖项已安装
 - 4. 请阅读以下指南，明确工作流程。

## 1.初次开发
- 1. 分支所属如下
   yunhuier:dev/prompts
   qdssl-1023:dev/diff_runner
   RobertTerisa:dev/owner
 - 2. 切换到开发目录后,在本目录打开VS code,新建终端,输入以下命令
    ```bash
   git clone https://github.com/RobertTerisa/AIOJ_release.git

   git checkout 你的分支
   git pull origin 你的分支
    ```

## 2.每周开发开始前
   输入以下命令:
   ```bash
   git fetch origin
   git checkout 你的分支
   git merge origin/main

   ```


## 3.开发完成后
输入以下命令:
   ```bash
   git add .
   git commit -m "本周干了什么"
   git push -u origin 你的分支
   ```

然后进入GitHub仓库主页，点main后选择对应分支，再点contribute，再点open pull request , 填写标题，描述，然后点击 Create pull request。