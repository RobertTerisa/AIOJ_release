from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
from typing import Any, Iterable

from data_class import TestCase


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
