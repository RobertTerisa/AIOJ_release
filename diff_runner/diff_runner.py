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

推荐使用工作区配置，只传题号即可自动定位题目和产物目录：
    python <工具目录>/diff_runner/diff_runner.py --workspace-config aioj.workspace.json --name UVA10364

未配置工作区时，也可以使用旧的 JSON 参数配置文件：
    python diff_runner/diff_runner.py --config diff_runner/sample_config.json

测试用例来源三选一：
    --in-dir <包含 .in 文件的目录>
    --cases <json文件>
    --generator <python文件>

使用 --in-dir 或 --generator 时，对拍器会自动把用例保存到 data_dir/<题目名>/cases.json；
未配置工作区时，data_dir 默认为当前工作目录下的 test_data/。

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


WORKSPACE_CONFIG_NAME = "aioj.workspace.json"

# 用户程序 TLE 熔断阈值：--tle-policy stop 时，收集到 5 组用户 TLE 后停止后续用例。
# 题解 TLE / 参考RE 不受此阈值影响，会立即熔断。
USER_TLE_CIRCUIT_BREAKER_LIMIT = 5


@dataclass
class WorkspaceConfig:
    """aioj.workspace.json 的解析结果。

    所有路径都已转为绝对路径；找不到工作区配置时整个对象为 None，
    此时调用方必须保持旧的显式参数行为。
    """

    config_path: Path
    workspace: Path
    problems_dirs: list[Path]
    generators_dir: Path
    discussion_dir: Path
    records_dir: Path
    data_dir: Path
    timeout: float | None
    compiler: str | None
    std: str | None


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
    for key in ("problem_md", "user", "correct", "cases", "cases_out", "generator", "in_dir", "out_dir", "build_dir"):
        if key in cfg and cfg[key]:
            cfg[key] = resolve_path(cfg[key], base)
    return cfg


def first_present(*values: Any) -> Any:
    """返回第一个非 None 且非空字符串的值；0、False、[] 视为有效值。"""
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and value.strip() == "":
            continue
        return value
    return None


def load_workspace_config(
    explicit_path: Path | None,
    cwd: Path | None = None,
) -> WorkspaceConfig | None:
    """加载并解析 aioj.workspace.json。

    explicit_path 对应 --workspace-config；未提供时只在 cwd 下查找同名配置。
    找不到时返回 None，让调用方回退到旧的显式参数模式。
    """
    cwd = cwd or Path.cwd()
    if explicit_path is not None:
        config_path = resolve_path(explicit_path, cwd)
        if config_path is None:
            raise ValueError("--workspace-config 路径为空")
        if not config_path.exists():
            raise ValueError(f"工作区配置不存在: {config_path}")
    else:
        config_path = (cwd / WORKSPACE_CONFIG_NAME).resolve()
        if not config_path.exists():
            return None

    try:
        cfg = load_json(config_path)
    except json.JSONDecodeError as exc:
        raise ValueError(f"工作区配置 JSON 格式错误: {config_path}\n{exc}") from exc
    if not isinstance(cfg, dict):
        raise ValueError(f"工作区配置必须是 JSON 对象: {config_path}")

    config_dir = config_path.resolve().parent
    workspace = resolve_path(cfg.get("workspace"), config_dir) or config_dir
    workspace = workspace.resolve()

    raw_dirs = first_present(cfg.get("problems_dirs"), cfg.get("problems_dir"))
    if raw_dirs in (None, "", []):
        raw_dirs = [workspace]
    if isinstance(raw_dirs, (str, os.PathLike)):
        raw_dirs = [raw_dirs]
    if not isinstance(raw_dirs, list):
        raise ValueError(f"problems_dirs 必须是数组或字符串: {config_path}")

    problems_dirs: list[Path] = []
    for item in raw_dirs:
        resolved = resolve_path(item, workspace)
        if resolved is None:
            raise ValueError(f"problems_dirs 中不能有空路径: {config_path}")
        problems_dirs.append(resolved)
    if not problems_dirs:
        raise ValueError(f"problems_dirs 不能为空: {config_path}")

    def dir_value(key: str, default_name: str) -> Path:
        value = resolve_path(cfg.get(key), workspace)
        return value or (workspace / default_name)

    return WorkspaceConfig(
        config_path=config_path,
        workspace=workspace,
        problems_dirs=problems_dirs,
        generators_dir=dir_value("generators_dir", "generators"),
        discussion_dir=dir_value("discussion_dir", "discussion_records"),
        records_dir=dir_value("records_dir", "evaluation_records"),
        data_dir=dir_value("data_dir", "test_data"),
        timeout=cfg.get("timeout"),
        compiler=cfg.get("compiler"),
        std=cfg.get("std"),
    )


def find_problem_dir(name: str, workspace: WorkspaceConfig) -> Path:
    """按 problems_dirs 顺序查找第一个存在的 <题号>/ 文件夹。"""
    for base in workspace.problems_dirs:
        candidate = base / name
        if candidate.is_dir():
            return candidate
    searched = "\n".join(f"  - {base / name}" for base in workspace.problems_dirs)
    raise ValueError(f"未找到题目文件夹 {name}/，已按顺序查找:\n{searched}")


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
    dataset: str | None = None,
    stopped_reason: str | None = None,
    skipped_cases: list[TestCase] | None = None,
) -> None:
    skipped_cases = skipped_cases or []
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
    if dataset:
        lines.append(f"- 数据集：{dataset}")
    lines.append(f"- 题目 Markdown：`{display_path(problem_md)}`" if problem_md else "- 题目 Markdown：未提供")
    lines.append(f"- 用户代码：`{display_path(user_src)}`")
    lines.append(f"- 题解代码：`{display_path(correct_src)}`")
    lines.append(f"- 编译命令：`{compiler} -O2 -std={std}`")
    lines.append(f"- 单例超时：{timeout:g} 秒")
    if stopped_reason:
        lines.append("- 对拍中止：是")
        lines.append(f"- 熔断原因：{stopped_reason}")
        lines.append(f"- 已执行：{len(rows)} / {len(cases)}")
        lines.append(f"- 未执行：{len(skipped_cases)} 组")
        if skipped_cases:
            skipped_names = ", ".join(c.name for c in skipped_cases[:20])
            if len(skipped_cases) > 20:
                skipped_names += f" 等 {len(skipped_cases)} 组"
            lines.append(f"- 未执行用例：{skipped_names}")
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
        user_time = (
            f"{row['user_time']:.3f}s"
            if row.get("user_time") is not None
            else "-"
        )
        user_out = row.get("user_out")
        if user_out is None:
            user_out = "（未运行）"
        lines.append(
            "| {name} | {input} | {correct_out} | {correct_time:.3f}s | {user_out} | {user_time} | **{status}** | {note} |".format(
                name=md_cell(str(row["name"])),
                input=md_cell(row["input"]),
                correct_out=md_cell(row["correct_out"]),
                correct_time=row["correct_time"],
                user_out=md_cell(str(user_out)),
                user_time=user_time,
                status=row["status"],
                note=md_cell(row.get("note", "")),
            )
        )
    lines.append("")
    lines.append("## 说明")
    lines.append("")
    lines.append("- 表格中的 `<br>` 表示换行。")
    lines.append("- 本记录由 diff_runner 自动生成。")
    lines.append("- 评测记录仅代表本机结果，不反映实际OJ评测结果。")
    if stopped_reason:
        lines.append("- 本次对拍因 TLE 熔断提前结束，未执行用例未参与统计。")
    lines.append("- MLE 需要额外内存监控；当前版本不主动检测 MLE。")
    lines.append("")

    record_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="通用 UVA/OJ 对拍器")
    parser.add_argument("--config", type=Path, help="旧的 JSON 参数配置文件")
    parser.add_argument("--workspace-config", type=Path, help="工作区配置文件 aioj.workspace.json；缺省时尝试读取当前目录同名文件")
    parser.add_argument("--name", help="题目名，默认取题目 Markdown 文件名")
    parser.add_argument("--problem-md", type=Path, help="题目 Markdown 文件（独立于对拍器）")
    parser.add_argument("--user", type=Path, help="用户代码 .cpp")
    parser.add_argument("--correct", type=Path, help="题解代码 .cpp")
    parser.add_argument("--cases", type=Path, help="测试用例 JSON 文件")
    parser.add_argument("--generator", type=Path, help="测试用例生成器 Python 文件")
    parser.add_argument("--in-dir", type=Path, help="包含 .in 文件的目录；对拍器会自动转换为 cases JSON")
    parser.add_argument("--dataset", help="数据集名；用于区分同一道题的多套数据")
    parser.add_argument("--cases-out", type=Path, help="显式指定 cases.json 输出路径；优先级高于 --dataset")
    parser.add_argument("--out-dir", type=Path, help="评测记录输出目录；默认 evaluation_records/<题目名>")
    parser.add_argument("--timeout", type=float, help="每个测试用例的用户程序超时时间（秒）")
    parser.add_argument(
        "--tle-policy",
        choices=("continue", "stop"),
        default="stop",
        help="TLE 熔断策略：stop=默认，命中题解 TLE/参考RE 立即停止，用户 TLE 收集 5 组后停止；continue=保持旧行为，跑完全部用例",
    )
    parser.add_argument("--compiler", help="C++ 编译器，默认 g++")
    parser.add_argument("--std", help="C++ 标准，默认 c++17")
    parser.add_argument("--seed", type=int, help="随机生成器 seed")
    parser.add_argument("--submission", type=int, help="提交次数/记录编号；不传则自动按已有记录递增")
    parser.add_argument("--build-dir", type=Path, help="编译临时目录")
    parser.add_argument("--keep-build", action="store_true", help="保留编译和运行中间文件")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cwd = Path.cwd()

    try:
        workspace = load_workspace_config(args.workspace_config, cwd)
    except (ValueError, TypeError, OSError) as exc:
        print(f"[错误] {exc}", file=sys.stderr)
        return 1

    try:
        cfg: dict[str, Any] = load_config(args.config) if args.config else {}
    except Exception as exc:  # noqa: BLE001 - 友好展示旧配置错误
        print(f"[错误] 旧配置文件读取失败: {exc}", file=sys.stderr)
        return 1

    def pick(cli_value: Any, key: str, default: Any = None) -> Any:
        if cli_value is not None:
            return cli_value
        return first_present(cfg.get(key), default)

    def pick_path(cli_value: Path | None, key: str) -> Path | None:
        if cli_value is not None:
            return resolve_path(cli_value, cwd)
        value = cfg.get(key)
        if value is None or str(value).strip() == "":
            return None
        return value

    problem_md = pick_path(args.problem_md, "problem_md")
    user_src = pick_path(args.user, "user")
    correct_src = pick_path(args.correct, "correct")
    cases_path = pick_path(args.cases, "cases")
    generator_path = pick_path(args.generator, "generator")
    in_dir = pick_path(args.in_dir, "in_dir")
    out_dir_arg = pick_path(args.out_dir, "out_dir")
    cases_out_arg = pick_path(args.cases_out, "cases_out")
    build_dir_arg = pick_path(args.build_dir, "build_dir")

    name_value = first_present(args.name, cfg.get("name"))
    if name_value is None and problem_md is not None:
        name_value = problem_md.stem
    name = str(name_value) if name_value is not None else "diff"

    if workspace is None and any(p is None for p in (user_src, correct_src)):
        print(
            "[错误] 未找到工作区配置 aioj.workspace.json，无法自动定位题目文件。\n"
            "请先把 template.aioj.workspace.json 复制为当前目录的 aioj.workspace.json，"
            "或显式提供 --problem-md / --user / --correct。",
            file=sys.stderr,
        )
        return 1

    problem_dir: Path | None = None
    if workspace is not None and any(p is None for p in (problem_md, user_src, correct_src)):
        try:
            problem_dir = find_problem_dir(name, workspace)
        except ValueError as exc:
            print(f"[错误] {exc}", file=sys.stderr)
            return 1
        if problem_md is None:
            problem_md = problem_dir / f"{name}.md"
        if user_src is None:
            user_src = problem_dir / f"{name}.cpp"
        if correct_src is None:
            correct_candidate = problem_dir / f"{name}_correct.cpp"
            solution_candidate = problem_dir / f"{name}_solution.cpp"
            correct_src = correct_candidate if correct_candidate.exists() else solution_candidate

    if problem_dir is None:
        if problem_md is not None:
            problem_dir = problem_md.parent
        elif user_src is not None:
            problem_dir = user_src.parent

    if problem_md is not None and not problem_md.exists():
        print(f"[错误] 题目 Markdown 不存在: {problem_md}", file=sys.stderr)
        return 1
    if user_src is None or not user_src.exists():
        print(f"[错误] 用户代码不存在: {user_src}", file=sys.stderr)
        return 1
    if correct_src is None or not correct_src.exists():
        print(f"[错误] 题解代码不存在: {correct_src}", file=sys.stderr)
        return 1

    dataset_raw = first_present(args.dataset, cfg.get("dataset"))
    dataset = safe_name(str(dataset_raw)) if dataset_raw not in (None, "") else None
    seed = pick(args.seed, "seed", None)
    timeout_value = first_present(args.timeout, cfg.get("timeout"), workspace.timeout if workspace else None, 10.0)
    compiler_value = first_present(args.compiler, cfg.get("compiler"), workspace.compiler if workspace else None, "g++")
    std_value = first_present(args.std, cfg.get("std"), workspace.std if workspace else None, "c++17")
    submission = pick(args.submission, "submission", None)

    try:
        timeout = float(timeout_value)
    except (TypeError, ValueError):
        print(f"[错误] --timeout 必须是数字: {timeout_value}", file=sys.stderr)
        return 1
    compiler = str(compiler_value)
    std = str(std_value)

    sources = [p for p in (cases_path, generator_path, in_dir) if p is not None]
    if len(sources) > 1:
        print("[错误] 必须且只能指定 --cases、--generator、--in-dir 之一", file=sys.stderr)
        return 1

    if not sources and workspace is not None:
        # 优先题目文件夹里的 IN/，其次工作区生成器目录，最后题目文件夹内的旧式生成器。
        if problem_dir is not None:
            in_candidate = problem_dir / "IN"
            if in_candidate.is_dir() and any(in_candidate.glob("*.in")):
                in_dir = in_candidate
        if in_dir is None:
            candidates: list[Path] = []
            if name:
                candidates.append(workspace.generators_dir / f"{name}_generator.py")
                if problem_dir is not None:
                    candidates.append(problem_dir / f"{name}_generator.py")
            for candidate in candidates:
                if candidate.exists():
                    generator_path = candidate
                    break
        sources = [p for p in (cases_path, generator_path, in_dir) if p is not None]

    if len(sources) != 1:
        if workspace is None:
            print(
                "[错误] 未找到工作区配置 aioj.workspace.json，且没有可用的数据来源。\n"
                "请先把 template.aioj.workspace.json 复制为当前目录的 aioj.workspace.json，"
                "或用 --cases / --in-dir / --generator 显式指定数据。",
                file=sys.stderr,
            )
        else:
            print(
                "[错误] 未找到数据来源。请提供 --in-dir / --generator / --cases，"
                "或确认题目文件夹下有 IN/*.in 或配置的 generators_dir 下有生成器。",
                file=sys.stderr,
            )
        return 1

    if out_dir_arg is not None:
        out_dir = out_dir_arg
    else:
        records_root = workspace.records_dir if workspace is not None else (cwd / "evaluation_records")
        out_dir = records_root / safe_name(name)
        if dataset:
            out_dir = out_dir / dataset

    if cases_out_arg is not None:
        cases_json_path = cases_out_arg
    else:
        data_root = workspace.data_dir if workspace is not None else (cwd / "test_data")
        cases_json_path = data_root / safe_name(name)
        if dataset:
            cases_json_path = cases_json_path / dataset
        cases_json_path = cases_json_path / "cases.json"

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
        cases_json_path.parent.mkdir(parents=True, exist_ok=True)
        cases_data = [{"name": c.name, "input": c.input} for c in cases]
        cases_json_path.write_text(
            json.dumps(cases_data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"[cases] 已保存: {display_path(cases_json_path)}")
    elif cases_out_arg is not None:
        print("[警告] --cases-out 只在 --in-dir 或 --generator 模式下生效，当前 --cases 模式已忽略", file=sys.stderr)

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

    tle_policy = args.tle_policy
    print(f"[3/3] 运行 {len(cases)} 组数据，用户程序超时 {timeout:g}s")
    rows: list[dict[str, Any]] = []
    stopped_reason: str | None = None
    skipped_cases: list[TestCase] = []
    user_tle_count = 0

    for i, case in enumerate(cases, 1):
        correct_res = run_program(correct_exe, case.input, timeout, build_dir, f"correct_{i:03d}")

        user_res: RunResult | None = None
        should_stop = False

        if tle_policy == "stop" and correct_res.status == "timeout":
            status, note = "参考TLE", "题解程序超时；TLE 熔断，用户程序未运行"
            should_stop = True
        elif tle_policy == "stop" and correct_res.exit_code not in (None, 0):
            status, note = "参考RE", f"题解程序返回码 {correct_res.exit_code}；TLE 熔断，用户程序未运行"
            should_stop = True
        else:
            user_res = run_program(user_exe, case.input, timeout, build_dir, f"user_{i:03d}")
            status, note = verdict_for(correct_res, user_res)

        rows.append(
            {
                "name": case.name,
                "input": case.input,
                "correct_out": correct_res.stdout,
                "correct_time": correct_res.elapsed,
                "user_out": user_res.stdout if user_res is not None else "（未运行）",
                "user_time": user_res.elapsed if user_res is not None else None,
                "status": status,
                "note": note,
            }
        )
        mark = "AC" if status == "AC" else status
        print(f"  {i:03d}/{len(cases):03d} {case.name}: {mark}")

        if tle_policy == "stop" and should_stop:
            stopped_reason = f"{status}（第 {i} 组：{case.name}）"
            skipped_cases = cases[i:]
            print(f"[熔断] {stopped_reason}，跳过剩余 {len(skipped_cases)} 组")
            break

        if tle_policy == "stop" and user_res is not None and user_res.status == "timeout":
            user_tle_count += 1
            if user_tle_count >= USER_TLE_CIRCUIT_BREAKER_LIMIT:
                stopped_reason = (
                    f"用户TLE达到 {USER_TLE_CIRCUIT_BREAKER_LIMIT} 组"
                    f"（第 {i} 组：{case.name}）"
                )
                skipped_cases = cases[i:]
                print(f"[熔断] {stopped_reason}，跳过剩余 {len(skipped_cases)} 组")
                break

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
        dataset=dataset,
        stopped_reason=stopped_reason,
        skipped_cases=skipped_cases,
    )

    total = len(rows)
    ac = sum(1 for r in rows if r["status"] == "AC")
    print()
    if stopped_reason:
        print(f"完成: {ac}/{total} AC（TLE 熔断，已跳过 {len(skipped_cases)} 组）")
    else:
        print(f"完成: {ac}/{total} AC")
    print(f"记录: {display_path(record_path)}")

    if not keep_build:
        shutil.rmtree(build_dir, ignore_errors=True)
    return 0 if ac == total else 2



if __name__ == "__main__":
    sys.exit(main())
