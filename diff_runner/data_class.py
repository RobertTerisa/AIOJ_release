from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path


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
