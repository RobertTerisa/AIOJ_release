from __future__ import annotations

import ast
import math
from typing import Any


_ALLOWED = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
    ast.Name, ast.Load, ast.Call,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv,
    ast.Mod, ast.USub, ast.UAdd,
)
_FUNCS = {"min": min, "max": max, "isqrt": math.isqrt}


def _check(node: ast.AST) -> None:
    if not isinstance(node, _ALLOWED):
        raise ValueError(f"表达式不允许的语法: {type(node).__name__}")
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCS:
            raise ValueError("表达式只允许 min / max / isqrt")
        if node.keywords:
            raise ValueError("表达式函数不支持关键字参数")


def safe_eval(expr: Any, env: dict[str, Any]) -> int:
    if isinstance(expr, bool):
        raise ValueError("表达式不接受布尔值")
    if isinstance(expr, int):
        return expr
    tree = ast.parse(str(expr), mode="eval")
    for node in ast.walk(tree):
        _check(node)
        if isinstance(node, ast.Name) and node.id not in env and node.id not in _FUNCS:
            raise ValueError(f"表达式引用了未绑定变量: {node.id}")
    value = eval(compile(tree, "<expr>", "eval"),
                 {"__builtins__": {}}, {**env, **_FUNCS})
    if not isinstance(value, int):
        raise ValueError(f"表达式结果不是整数: {expr} -> {value!r}")
    return value


def names_in(expr: Any) -> set[str]:
    if isinstance(expr, int):
        return set()
    tree = ast.parse(str(expr), mode="eval")
    return {
        node.id for node in ast.walk(tree)
        if isinstance(node, ast.Name) and node.id not in _FUNCS
    }
