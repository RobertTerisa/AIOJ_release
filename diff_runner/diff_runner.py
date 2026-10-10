#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用对拍器（Differential Runner）。

设计目标：
- 对拍器本身不写死任何题目文件；
- 用户代码、题解代码、题目 Markdown、测试用例/生成器全部通过参数传入；
- 结果统一输出为 Markdown 评测记录。

基本用法：
    python diff_runner/diff_runner.py ^
        --name UVA10364 ^
        --problem-md UVA10364/UVA10364.md ^
        --user UVA10364/UVA10364.cpp ^
        --correct UVA10364/UVA10364_correct.cpp ^
        --cases diff_runner/sample_cases.json ^
        --out-dir evaluation_records ^
        --timeout 10

也可以使用 JSON 配置文件：
    python diff_runner/diff_runner.py --config diff_runner/sample_config.json

测试用例来源三选一：
    --in-dir <包含 .in 文件的目录>
    --cases <json文件>
    --generator <python文件>

使用 --in-dir 或 --generator 时，对拍器会自动把用例保存到：
    test_data/<题目名>/cases.json

cases JSON 支持两种格式：
    1. ["完整输入字符串1", "完整输入字符串2"]
    2. [{"name": "样例1", "input": "完整输入字符串1"}, ...]

generator Python 文件：
    必须定义 generate_cases(seed=None)，
    返回 list[str] 或 list[dict]。
"""

from __future__ import annotations

import argparse
import importlib.util
import inspect
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable

# Windows 控制台/管道下显式使用 UTF-8，避免中文乱码。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


@dataclass
class TestCase:
    name: str
    input: str


@dataclass
class RunResult:
    status: str          # done / timeout
    exit_code: int | None
    stdout: str
    stderr: str
    elapsed: float
    input_path: Path
    stdout_path: Path
    stderr_path: Path


def project_root() -> Path:
    """diff_runner/ 的上一级目录。"""
    return Path(__file__).resolve().parent.parent


def display_path(path: Path) -> str:
    """显示路径时优先使用相对路径，保证记录可迁移。"""
    try:
        resolved = path.resolve()
    except OSError:
        return str(path)

    for base in (project_root(), Path.cwd()):
        try:
            return str(resolved.relative_to(base))
        except ValueError:
            continue
    return str(resolved)


def safe_name(name: str) -> str:
    """把题目名转成适合做文件名的字符串。"""
    name = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", name, flags=re.UNICODE)
    return name.strip("._") or "diff"


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()


def md_cell(text: str) -> str:
    """转义 Markdown 表格单元格。"""
    text = normalize_text(text)
    text = text.replace("|", "\\|")
    text = text.replace("\n", "<br>")
    return text


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> Any:
    return json.loads(read_text(path))


def resolve_path(value: str | os.PathLike[str] | None, base: Path) -> Path | None:
    if value is None or str(value).strip() == "":
        return None
    p = Path(value)
    if not p.is_absolute():
        p = (base / p).resolve()
    return p


def load_config(config_path: Path) -> dict[str, Any]:
    cfg = load_json(config_path)
    if not isinstance(cfg, dict):
        raise ValueError(f"配置文件必须是 JSON 对象: {config_path}")
    base = config_path.resolve().parent
    for key in ("problem_md", "user", "correct", "cases", "generator", "in_dir", "out_dir", "build_dir"):
        if key in cfg and cfg[key]:
            cfg[key] = resolve_path(cfg[key], base)
    return cfg


def load_cases_from_json(path: Path) -> list[TestCase]:
    data = load_json(path)
    if isinstance(data, dict):
        data = data.get("cases", [])
    if not isinstance(data, list):
        raise ValueError(f"cases JSON 必须是数组或包含 cases 数组的对象: {path}")
    return normalize_case_list(data, path)


def normalize_case_list(raw: Iterable[Any], source: Path | None = None) -> list[TestCase]:
    cases: list[TestCase] = []
    for i, item in enumerate(raw, 1):
        if isinstance(item, str):
            cases.append(TestCase(name=f"case_{i:03d}", input=item))
        elif isinstance(item, dict):
            if "input" not in item:
                raise ValueError(f"{source or '生成器'} 的第 {i} 个用例缺少 input 字段")
            cases.append(TestCase(name=str(item.get("name", f"case_{i:03d}")), input=str(item["input"])))
        else:
            raise ValueError(f"{source or '生成器'} 的第 {i} 个用例格式不支持")
    return cases


def load_cases_from_in_dir(path: Path, pattern: str = "*.in") -> list[TestCase]:
    """从目录中的 .in 文件读取测试用例。"""
    if not path.exists():
        raise ValueError(f".in 目录不存在: {path}")
    files = sorted(path.glob(pattern))
    if not files:
        raise ValueError(f".in 目录中没有匹配 {pattern} 的文件: {path}")
    cases: list[TestCase] = []
    for file in files:
        cases.append(TestCase(name=file.stem, input=file.read_text(encoding="utf-8")))
    return cases


def load_cases_from_generator(path: Path, seed: int | None) -> list[TestCase]:
    spec = importlib.util.spec_from_file_location("diff_runner_generator", str(path))
    if spec is None or spec.loader is None:
        raise ValueError(f"无法加载生成器: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    func = getattr(module, "generate_cases", None)
    if not callable(func):
        raise ValueError(f"生成器必须定义 generate_cases(seed=None): {path}")

    sig = inspect.signature(func)
    if "seed" in sig.parameters:
        raw = func(seed=seed)
    else:
        raw = func()
    if isinstance(raw, dict):
        raw = raw.get("cases", [])
    return normalize_case_list(raw, path)


def compile_source(
    src: Path,
    exe: Path,
    compiler: str,
    std: str,
    build_dir: Path,
    tag: str,
) -> tuple[bool, str]:
    out_path = build_dir / f"compile_{tag}.out"
    err_path = build_dir / f"compile_{tag}.err"
    cmd = [compiler, "-O2", f"-std={std}", "-o", str(exe), str(src)]
    with out_path.open("w", encoding="utf-8") as out, err_path.open("w", encoding="utf-8") as err:
        try:
            proc = subprocess.run(cmd, stdout=out, stderr=err, timeout=120)
        except subprocess.TimeoutExpired:
            return False, f"编译超时: {src}"
    if proc.returncode != 0:
        return False, f"编译失败: {src}\n{read_text(err_path)}"
    return True, ""


def run_program(
    exe: Path,
    input_text: str,
    timeout: float,
    run_dir: Path,
    tag: str,
) -> RunResult:
    input_path = run_dir / f"{tag}.in"
    out_path = run_dir / f"{tag}.out"
    err_path = run_dir / f"{tag}.err"
    input_path.write_text(input_text, encoding="utf-8")

    t0 = time.perf_counter()
    try:
        with (
            input_path.open("r", encoding="utf-8") as fi,
            out_path.open("w", encoding="utf-8") as fo,
            err_path.open("w", encoding="utf-8") as fe,
        ):
            proc = subprocess.run([str(exe)], stdin=fi, stdout=fo, stderr=fe, timeout=timeout)
        elapsed = time.perf_counter() - t0
        return RunResult(
            status="done",
            exit_code=proc.returncode,
            stdout=read_text(out_path),
            stderr=read_text(err_path),
            elapsed=elapsed,
            input_path=input_path,
            stdout_path=out_path,
            stderr_path=err_path,
        )
    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - t0
        return RunResult(
            status="timeout",
            exit_code=None,
            stdout=read_text(out_path),
            stderr=read_text(err_path),
            elapsed=elapsed,
            input_path=input_path,
            stdout_path=out_path,
            stderr_path=err_path,
        )


def verdict_for(correct: RunResult, user: RunResult) -> tuple[str, str]:
    """返回 (记录状态, 备注)。"""
    if correct.status == "timeout":
        return "参考TLE", "题解程序超时"
    if correct.exit_code not in (None, 0):
        return "参考RE", f"题解程序返回码 {correct.exit_code}"

    if user.status == "timeout":
        return "TLE", "我的程序超时"
    if user.exit_code not in (None, 0):
        return "RE", f"我的程序返回码 {user.exit_code}"

    if normalize_text(correct.stdout) == normalize_text(user.stdout):
        return "AC", ""
    return "WA", "输出不一致"


def write_record(
    record_path: Path,
    name: str,
    problem_md: Path | None,
    user_src: Path,
    correct_src: Path,
    cases: list[TestCase],
    rows: list[dict[str, Any]],
    timeout: float,
    compiler: str,
    std: str,
    submission: int,
) -> None:
    counts = {k: 0 for k in ("AC", "WA", "TLE", "RE", "参考TLE", "参考RE")}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1

    lines: list[str] = []
    lines.append(f"# {name} 对拍评测记录")
    lines.append("")
    lines.append("## 元信息")
    lines.append("")
    lines.append(f"- 时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- 提交次数：第 {submission} 次")
    lines.append(f"- 题目 Markdown：`{display_path(problem_md)}`" if problem_md else "- 题目 Markdown：未提供")
    lines.append(f"- 用户代码：`{display_path(user_src)}`")
    lines.append(f"- 题解代码：`{display_path(correct_src)}`")
    lines.append(f"- 编译命令：`{compiler} -O2 -std={std}`")
    lines.append(f"- 单例超时：{timeout:g} 秒")
    lines.append("")
    lines.append("## 统计")
    lines.append("")
    lines.append("| 状态 | 数量 |")
    lines.append("|---|---:|")
    for key in ("AC", "WA", "TLE", "RE", "参考TLE", "参考RE"):
        if counts.get(key):
            lines.append(f"| {key} | {counts[key]} |")
    lines.append("")
    lines.append("## 评测结果")
    lines.append("")
    lines.append("| 样例 | 具体输入 | 题解输出 | 题解耗时 | 我的输出 | 我的耗时 | 状态 | 备注 |")
    lines.append("|---|---|---:|---:|---:|---:|---|---|")
    for row in rows:
        lines.append(
            "| {name} | {input} | {correct_out} | {correct_time:.3f}s | {user_out} | {user_time:.3f}s | **{status}** | {note} |".format(
                name=md_cell(str(row["name"])),
                input=md_cell(row["input"]),
                correct_out=md_cell(row["correct_out"]),
                correct_time=row["correct_time"],
                user_out=md_cell(row["user_out"]),
                user_time=row["user_time"],
                status=row["status"],
                note=md_cell(row.get("note", "")),
            )
        )
    lines.append("")
    lines.append("## 说明")
    lines.append("")
    lines.append("- 表格中的 `<br>` 表示换行。")
    lines.append("- 本记录由 diff_runner 自动生成。")
    lines.append("- MLE 需要额外内存监控；当前版本不主动检测 MLE。")
    lines.append("")

    record_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="通用 UVA/OJ 对拍器")
    parser.add_argument("--config", type=Path, help="JSON 配置文件")
    parser.add_argument("--name", help="题目名，默认取题目 Markdown 文件名")
    parser.add_argument("--problem-md", type=Path, help="题目 Markdown 文件（独立于对拍器）")
    parser.add_argument("--user", type=Path, help="用户代码 .cpp")
    parser.add_argument("--correct", type=Path, help="题解代码 .cpp")
    parser.add_argument("--cases", type=Path, help="测试用例 JSON 文件")
    parser.add_argument("--generator", type=Path, help="测试用例生成器 Python 文件")
    parser.add_argument("--in-dir", type=Path, help="包含 .in 文件的目录；对拍器会自动转换为 cases JSON")
    parser.add_argument("--out-dir", type=Path, help="评测记录输出目录；默认 evaluation_records/<题目名>")
    parser.add_argument("--timeout", type=float, help="每个测试用例的用户程序超时时间（秒）")
    parser.add_argument("--compiler", help="C++ 编译器，默认 g++")
    parser.add_argument("--std", help="C++ 标准，默认 c++17")
    parser.add_argument("--seed", type=int, help="随机生成器 seed")
    parser.add_argument("--submission", type=int, help="提交次数/记录编号；不传则自动按已有记录递增")
    parser.add_argument("--build-dir", type=Path, help="编译临时目录")
    parser.add_argument("--keep-build", action="store_true", help="保留编译和运行中间文件")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cfg: dict[str, Any] = load_config(args.config) if args.config else {}

    root = project_root()

    def pick(cli_value: Any, key: str, default: Any = None) -> Any:
        if cli_value is not None:
            return cli_value
        return cfg.get(key, default)

    problem_md = resolve_path(pick(args.problem_md, "problem_md"), Path.cwd())
    user_src = resolve_path(pick(args.user, "user"), Path.cwd())
    correct_src = resolve_path(pick(args.correct, "correct"), Path.cwd())
    cases_path = resolve_path(pick(args.cases, "cases"), Path.cwd())
    generator_path = resolve_path(pick(args.generator, "generator"), Path.cwd())
    in_dir = resolve_path(pick(args.in_dir, "in_dir"), Path.cwd())
    timeout = float(pick(args.timeout, "timeout", 10.0))
    compiler = str(pick(args.compiler, "compiler", "g++"))
    std = str(pick(args.std, "std", "c++17"))
    seed = pick(args.seed, "seed", None)
    submission = pick(args.submission, "submission", None)
    build_dir_arg = resolve_path(pick(args.build_dir, "build_dir"), Path.cwd())

    if user_src is None or not user_src.exists():
        print(f"[错误] 用户代码不存在: {user_src}", file=sys.stderr)
        return 1
    if correct_src is None or not correct_src.exists():
        print(f"[错误] 题解代码不存在: {correct_src}", file=sys.stderr)
        return 1
    if problem_md is not None and not problem_md.exists():
        print(f"[错误] 题目 Markdown 不存在: {problem_md}", file=sys.stderr)
        return 1

    sources = [p for p in (cases_path, generator_path, in_dir) if p is not None]
    if len(sources) != 1:
        print("[错误] 必须且只能指定 --cases、--generator、--in-dir 之一", file=sys.stderr)
        return 1

    name = str(pick(args.name, "name", problem_md.stem if problem_md else "diff"))
    out_dir = resolve_path(pick(args.out_dir, "out_dir"), Path.cwd()) or (root / "evaluation_records" / safe_name(name))

    try:
        if cases_path is not None:
            if not cases_path.exists():
                raise ValueError(f"cases JSON 不存在: {cases_path}")
            cases = load_cases_from_json(cases_path)
            save_cases_json = False
        elif generator_path is not None:
            if not generator_path.exists():
                raise ValueError(f"generator 不存在: {generator_path}")
            cases = load_cases_from_generator(generator_path, seed)
            save_cases_json = True
        else:
            cases = load_cases_from_in_dir(in_dir)  # type: ignore[arg-type]
            save_cases_json = True
    except Exception as exc:  # noqa: BLE001 - 把错误友好地展示给调用方
        print(f"[错误] {exc}", file=sys.stderr)
        return 1

    if not cases:
        print("[错误] 没有加载到任何测试用例", file=sys.stderr)
        return 1

    if save_cases_json:
        cases_json_path = root / "test_data" / safe_name(name) / "cases.json"
        cases_json_path.parent.mkdir(parents=True, exist_ok=True)
        cases_data = [{"name": c.name, "input": c.input} for c in cases]
        cases_json_path.write_text(
            json.dumps(cases_data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"[cases] 已保存: {display_path(cases_json_path)}")

    out_dir.mkdir(parents=True, exist_ok=True)

    if build_dir_arg is not None:
        build_dir = build_dir_arg
        build_dir.mkdir(parents=True, exist_ok=True)
        keep_build = bool(args.keep_build)
    else:
        build_dir = Path(tempfile.mkdtemp(prefix="diff_runner_"))
        keep_build = bool(args.keep_build)

    exe_suffix = ".exe" if os.name == "nt" else ""
    correct_exe = build_dir / f"correct{exe_suffix}"
    user_exe = build_dir / f"user{exe_suffix}"

    print(f"[1/3] 编译题解: {display_path(correct_src)}")
    ok, msg = compile_source(correct_src, correct_exe, compiler, std, build_dir, "correct")
    if not ok:
        print(msg, file=sys.stderr)
        if not keep_build:
            shutil.rmtree(build_dir, ignore_errors=True)
        return 1

    print(f"[2/3] 编译用户代码: {display_path(user_src)}")
    ok, msg = compile_source(user_src, user_exe, compiler, std, build_dir, "user")
    if not ok:
        print(msg, file=sys.stderr)
        if not keep_build:
            shutil.rmtree(build_dir, ignore_errors=True)
        return 1

    print(f"[3/3] 运行 {len(cases)} 组数据，用户程序超时 {timeout:g}s")
    rows: list[dict[str, Any]] = []
    for i, case in enumerate(cases, 1):
        correct_res = run_program(correct_exe, case.input, timeout, build_dir, f"correct_{i:03d}")
        user_res = run_program(user_exe, case.input, timeout, build_dir, f"user_{i:03d}")
        status, note = verdict_for(correct_res, user_res)
        rows.append(
            {
                "name": case.name,
                "input": case.input,
                "correct_out": correct_res.stdout,
                "correct_time": correct_res.elapsed,
                "user_out": user_res.stdout,
                "user_time": user_res.elapsed,
                "status": status,
                "note": note,
            }
        )
        mark = "AC" if status == "AC" else status
        print(f"  {i:03d}/{len(cases):03d} {case.name}: {mark}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = safe_name(name)

    if submission is None:
        existing = sorted(out_dir.glob(f"{base_name}_diff_*.md"))
        submission = len(existing) + 1
    else:
        try:
            submission = int(submission)
        except (TypeError, ValueError):
            print(f"[错误] --submission 必须是整数: {submission}", file=sys.stderr)
            return 1

    record_path = out_dir / f"{base_name}_diff_{timestamp}_submission_{submission}.md"
    write_record(
        record_path=record_path,
        name=name,
        problem_md=problem_md,
        user_src=user_src,
        correct_src=correct_src,
        cases=cases,
        rows=rows,
        timeout=timeout,
        compiler=compiler,
        std=std,
        submission=submission,
    )

    total = len(rows)
    ac = sum(1 for r in rows if r["status"] == "AC")
    print()
    print(f"完成: {ac}/{total} AC")
    print(f"记录: {display_path(record_path)}")

    if not keep_build:
        shutil.rmtree(build_dir, ignore_errors=True)
    return 0 if ac == total else 2


if __name__ == "__main__":
    sys.exit(main())
