from __future__ import annotations

from typing import NamedTuple

from models import DiagnosticError


class Gen(NamedTuple):
    id: str
    kind: str
    exe: str


# 目前只登记已经实现并编译好的模式
GENERATORS: tuple[Gen, ...] = (
    Gen("seq_random_small", "sequence", "seq_random_small.exe"),

    # 以下完成并编译后再取消注释
     Gen("seq_random_large", "sequence", "seq_random_large.exe"),
     Gen("seq_increasing",   "sequence", "seq_increasing.exe"),
     Gen("seq_decreasing",   "sequence", "seq_decreasing.exe"),
     Gen("seq_all_equal",    "sequence", "seq_all_equal.exe"),
    # Gen("graph_chain",      "graph",    "graph_chain.exe"),
    # Gen("graph_star",       "graph",    "graph_star.exe"),
    # Gen("str_random",       "string",   "str_random.exe"),
    # Gen("str_same_char",    "string",   "str_same_char.exe"),
)


def available_generator_ids() -> str:
    """可用生成器 id 的展示用字符串；一个都没有时给 <none>。

    单独抽成 helper，是为了让“未注册生成器”和“生成器未编译”两类错误
    输出同一份可用列表，避免两处各拼一份、日后改注册表时漏改。
    """
    return ", ".join(g.id for g in GENERATORS) or "<none>"


def get_generator(generator_id: str) -> Gen:
    for g in GENERATORS:
        if g.id == generator_id:
            return g
    raise DiagnosticError(
        "unsupported-generator",
        f"未注册的生成器: {generator_id}",
        generator=generator_id,
        available=available_generator_ids(),
        hint="请改用已注册生成器，或由负责人实现、编译并注册该生成器",
    )


def list_generators() -> tuple[Gen, ...]:
    return GENERATORS
