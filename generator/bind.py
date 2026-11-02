from __future__ import annotations

import hashlib
import random
from typing import Any

from expr import names_in, safe_eval
from models import BindError, ProblemSpec


def eval_int(expr: Any, env: dict[str, Any]) -> int:
    return safe_eval(expr, env)


def norm_range(value: Any) -> tuple[Any, Any]:
    if isinstance(value, bool):
        raise BindError("范围不能是布尔值")
    if isinstance(value, int):
        return value, value
    if isinstance(value, dict):
        if "expr" in value:
            return value["expr"], value["expr"]
        if "min" not in value or "max" not in value:
            raise BindError(f"范围缺少 min/max: {value!r}")
        return value["min"], value["max"]
    raise BindError(f"无法识别的范围: {value!r}")


def choose(lo: int, hi: int, scale: str, rng: random.Random) -> int:
    if lo > hi:
        raise BindError(f"范围不可行: [{lo}, {hi}]")
    if lo == hi:
        return lo
    if scale == "min":
        return lo
    if scale == "max":
        return hi
    if scale == "small":
        hi = min(hi, lo + max(0, (hi - lo) // 10))
    elif scale == "medium":
        hi = min(hi, lo + max(0, (hi - lo) // 2))
    return rng.randint(lo, hi)


def derive_seed(run_seed: int, generator: str, group_index: int,
                attempt: int) -> int:
    text = f"{run_seed}|{generator}|{group_index}|{attempt}"
    # 仅用于派生 sub_seed，不参与任何完整性校验。
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "little") & ((1 << 63) - 1)


def bind_vars(specs: dict[str, Any], scale: str,
              rng: random.Random) -> dict[str, int]:
    env: dict[str, int] = {}
    pending = dict(specs)
    while pending:
        progressed = False
        for name in list(pending):
            lo_expr, hi_expr = norm_range(pending[name])
            deps = names_in(lo_expr) | names_in(hi_expr)
            if not deps <= set(env):
                continue
            lo = eval_int(lo_expr, env)
            hi = eval_int(hi_expr, env)
            env[name] = choose(lo, hi, scale, rng)
            del pending[name]
            progressed = True
        if not progressed:
            raise BindError(f"变量依赖无法解析: {sorted(pending)}")
    return env


def bind_sequence(spec: ProblemSpec, rule: dict[str, Any],
                  rng: random.Random) -> dict[str, Any]:
    specs = dict(spec.constraints.get("variables", {}))
    specs.update(rule.get("bind", {}))
    env = bind_vars(specs, rule.get("scale", "random"), rng)
    arrays = []
    for arr in spec.constraints.get("arrays", []):
        length = eval_int(arr["length"], env)
        lo = eval_int(arr.get("min", 0), env)
        hi = eval_int(arr.get("max", 10**9), env)
        if lo > hi:
            raise BindError(f"数组 {arr['name']} 元素范围不可行")
        arrays.append({"name": arr["name"], "length": length,
                       "min": lo, "max": hi})
    env["_arrays"] = arrays
    return env


def _graph_capacity(g: dict[str, Any], n: int) -> int:
    if g.get("simple"):
        return n * (n - 1) if g.get("directed") else n * (n - 1) // 2
    _, hi_expr = norm_range(g["m"])
    return eval_int(hi_expr, {"n": n})


def bind_graph(spec: ProblemSpec, rule: dict[str, Any],
               rng: random.Random) -> dict[str, Any]:
    g = spec.constraints["graph"]
    scale = rule.get("scale", "random")
    env: dict[str, int] = {}

    n_lo, n_hi = norm_range(g["n"])
    env["n"] = choose(eval_int(n_lo, env), eval_int(n_hi, env), scale, rng)
    n = env["n"]

    mutation = rule.get("mutation", {})
    dup = eval_int(mutation.get("duplicate", 0), env)
    loop = eval_int(mutation.get("self_loop", 0), env)
    if g.get("simple") and (dup or loop):
        raise BindError("simple=true 时不允许启用重边/自环变异")
    if g.get("self_loops") is False and loop:
        raise BindError("题面禁止自环，不能生成自环变异")

    override = rule.get("bind", {})
    if "base_m" in override:
        base_m = eval_int(override["base_m"], env)
        m = base_m + dup + loop
    else:
        m_lo, m_hi = norm_range(g["m"])
        lo = eval_int(m_lo, env)
        hi = min(eval_int(m_hi, env), _graph_capacity(g, n))
        if g.get("connected"):
            lo = max(lo, n - 1 if n > 0 else 0)
        m = choose(max(lo, 0), hi, scale, rng)
        base_m = m - dup - loop

    if base_m < 0:
        raise BindError(f"base_m 为负: m={m}, dup={dup}, loop={loop}")
    m_lo, m_hi = norm_range(g["m"])
    if not (eval_int(m_lo, env) <= m <= eval_int(m_hi, env)):
        raise BindError(f"m={m} 超出题面范围")

    env.update({"m": m, "base_m": base_m, "dup": dup, "loop": loop})
    return env


def bind_string(spec: ProblemSpec, rule: dict[str, Any],
                rng: random.Random) -> dict[str, Any]:
    specs = dict(spec.constraints.get("variables", {}))
    specs.update(rule.get("bind", {}))
    env = bind_vars(specs, rule.get("scale", "random"), rng)
    s = spec.constraints["strings"]
    count = eval_int(s["count"], env)
    if "lengths" in s:
        lengths = [eval_int(x, env) for x in s["lengths"]]
        if len(lengths) != count:
            raise BindError("lengths 数量与 count 不一致")
    else:
        lengths = [eval_int(s["length"], env)] * count
    env["_strings"] = {"count": count, "lengths": lengths,
                       "alphabet": s.get("alphabet", "ab")}
    return env


def bind_case(spec: ProblemSpec, rule: dict[str, Any],
              group_index: int, seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    if spec.kind == "sequence":
        return bind_sequence(spec, rule, rng)
    if spec.kind == "graph":
        return bind_graph(spec, rule, rng)
    if spec.kind == "string":
        return bind_string(spec, rule, rng)
    raise BindError(f"未知题型: {spec.kind}")


def content_specs(spec: ProblemSpec,
                  bound: dict[str, Any]) -> list[dict[str, Any]]:
    if spec.kind == "sequence":
        return [
            {"name": a["name"], "type": "int_array", "count": a["length"]}
            for a in bound["_arrays"]
        ]
    if spec.kind == "graph":
        g = spec.constraints["graph"]
        width = 3 if g.get("weighted") else 2
        total = bound["base_m"] + bound["dup"] + bound["loop"]
        return [{"name": "G", "type": "int_array",
                 "count": total * width, "width": width}]
    if spec.kind == "string":
        return [{"name": "S", "type": "string_lines",
                 "count": bound["_strings"]["count"]}]
    raise BindError(f"未知题型: {spec.kind}")
