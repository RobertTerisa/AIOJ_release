# Diff Runner

通用对拍器。对拍器本身不写死任何题目、用户代码或题解代码，全部通过参数传入。

## 目录约定

- `diff_runner/`：对拍器
- `evaluation_records/`：自动生成的评测记录
- `discussion_records/`：题目讨论、Debug 过程整理成的 Markdown

## 基本用法

```powershell
python diff_runner\diff_runner.py `
  --name UVA10364 `
  --problem-md UVA10364\UVA10364.md `
  --user UVA10364\UVA10364.cpp `
  --correct UVA10364\UVA10364_correct.cpp `
  --generator diff_runner\generators\UVA10364_generator.py `
  --seed 123 `
  --timeout 10
```

## 配置文件用法

```powershell
python diff_runner\diff_runner.py --config diff_runner\sample_config.json
```

配置文件中可以写：

```json
{
  "name": "UVA10364",
  "problem_md": "../UVA10364/UVA10364.md",
  "user": "../UVA10364/UVA10364.cpp",
  "correct": "../UVA10364/UVA10364_correct.cpp",
  "generator": "generators/UVA10364_generator.py",
  "out_dir": "../evaluation_records",
  "timeout": 10,
  "compiler": "g++",
  "std": "c++17"
}
```

相对路径按配置文件所在目录解析。

## 测试用例来源

二选一：

```text
--in-dir <包含 .in 文件的目录>
--generator <python文件>
```

`--in-dir` 和 `--generator` 会自动把用例保存到：

```text
test_data\<题目名>\cases.json
```

用户只需要：

- 有 `IN` 文件夹时，在里面放 `.in` 文件；
- 没有 `IN` 时，使用数据生成器。

生成器格式：

```python
def generate_cases(seed=None):
    return [
        {"name": "样例1", "input": "..."},
    ]
```

## 输出

默认评测结果写入：

```text
evaluation_records/<题目名>/<题目名>_diff_<时间戳>_submission_<次数>.md
```

不指定 `--submission` 时，对拍器会自动按当前输出目录里已有的同题记录递增提交次数。

记录中包含：

- 每组输入
- 题解输出
- 用户输出
- 双方耗时
- 状态：AC / WA / TLE / RE 等
- 统计

## 状态说明

- `AC`：输出一致
- `WA`：输出不一致
- `TLE`：用户程序超时
- `RE`：用户程序运行错误
- `参考TLE`：题解程序超时
- `参考RE`：题解程序运行错误

MLE 需要额外的内存监控；当前版本不主动检测 MLE。
