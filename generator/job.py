from __future__ import annotations

from pathlib import Path
from typing import Any, TextIO

from models import ProblemSpec


def write_control_tokens(handle: TextIO, spec: ProblemSpec,
                         bound: dict[str, Any]) -> None:
    """按 input_format 顺序把该组控制 token 写入 .in。"""
    tokens = []
    for item in spec.input_format["case"]["items"]:
        if item.get("emit") == "scalar" and item.get("source") == "control":
            name = item["name"]
            if name in bound:
                tokens.append(str(bound[name]))
    if tokens:
        handle.write(" ".join(tokens) + "\n")


def read_in_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")
