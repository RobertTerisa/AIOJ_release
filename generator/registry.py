from __future__ import annotations

from typing import NamedTuple

from models import SpecError


class Gen(NamedTuple):
    id: str
    kind: str
    exe: str


# 目前只登记已经实现并编译好的模式
GENERATORS: tuple[Gen, ...] = (
    Gen("seq_random_small", "sequence", "seq_random_small.exe"),

    # 以下完成并编译后再取消注释
    # Gen("seq_random_large", "sequence", "seq_random_large.exe"),
    # Gen("seq_increasing",   "sequence", "seq_increasing.exe"),
    # Gen("seq_decreasing",   "sequence", "seq_decreasing.exe"),
    # Gen("seq_all_equal",    "sequence", "seq_all_equal.exe"),
    # Gen("graph_chain",      "graph",    "graph_chain.exe"),
    # Gen("graph_star",       "graph",    "graph_star.exe"),
    # Gen("str_random",       "string",   "str_random.exe"),
    # Gen("str_same_char",    "string",   "str_same_char.exe"),
)


def get_generator(generator_id: str) -> Gen:
    for g in GENERATORS:
        if g.id == generator_id:
            return g
    known = ", ".join(g.id for g in GENERATORS)
    raise SpecError(f"未注册的生成器: {generator_id}；可用: {known}")


def list_generators() -> tuple[Gen, ...]:
    return GENERATORS
