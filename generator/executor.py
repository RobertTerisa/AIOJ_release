from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from models import FatalError, ProblemSpec
from registry import get_generator


def generator_path(root: Path, spec: ProblemSpec,
                   rule: dict[str, Any]) -> Path:
    entry = get_generator(rule["generator"])
    if entry.kind != spec.kind:
        raise FatalError(
            f"生成器 {entry.id} 属于 {entry.kind}，但题目是 {spec.kind}"
        )
    return root / entry.kind / entry.exe


def build_args(spec: ProblemSpec, rule: dict[str, Any],
               bound: dict[str, Any], seed: int,
               out_path: Path) -> list[str]:
    args = ["--seed", str(seed),
            "--out", str(out_path), "--append"]

    if spec.kind == "sequence":
        for arr in bound["_arrays"]:
            args += ["--array",
                     f'{arr["length"]},{arr["min"]},{arr["max"]}']
        return args

    if spec.kind == "graph":
        g = spec.constraints["graph"]
        args += [
            "--n", str(bound["n"]),
            "--base-m", str(bound["base_m"]),
            "--dup", str(bound["dup"]),
            "--loop", str(bound["loop"]),
            "--directed", "1" if g.get("directed") else "0",
            "--weighted", "1" if g.get("weighted") else "0",
            "--vertex-base", str(int(g.get("vertex_base", 1))),
            "--simple", "1" if g.get("simple") else "0",
            "--connected", "1" if g.get("connected") else "0",
        ]
        if g.get("weighted"):
            w = g.get("weight", {"min": 1, "max": 10**9})
            args += ["--weight-min", str(w["min"]),
                     "--weight-max", str(w["max"])]
        return args

    if spec.kind == "string":
        s = bound["_strings"]
        args += [
            "--count", str(s["count"]),
            "--lengths", ",".join(map(str, s["lengths"])),
            "--alphabet", s["alphabet"],
        ]
        return args

    raise FatalError(f"未知题型: {spec.kind}")


def run_generator(exe: Path, args: list[str],
                  timeout: float) -> None:
    try:
        proc = subprocess.run(
            [str(exe), *args],
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise FatalError(f"生成器超时: {exe}") from exc
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "无输出").strip()[-2000:]
        raise FatalError(
            f"生成器失败: {exe} (exit={proc.returncode})\n{detail}"
        )
