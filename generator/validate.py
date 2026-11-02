from __future__ import annotations

from typing import Any

from models import FatalError, ProblemSpec, RetryableError


def items(spec: ProblemSpec) -> list[dict]:
    return spec.input_format["case"]["items"]


def verify_content(spec: ProblemSpec, job: dict[str, Any],
                   text: str) -> None:
    if job.get("stream") == "lines":
        lines = [ln for ln in text.splitlines() if ln.strip()]
        expected = 1 if spec.input_format.get("case_count", {}).get("emit") == "explicit" else 0
        for group in job["groups"]:
            expected += 1
            expected += sum(int(seg["count"]) for seg in group["content"]
                            if seg["type"] == "string_lines")
        if len(lines) != expected:
            raise RetryableError(
                f"数据流行数不符: 期望 {expected}, 实际 {len(lines)}"
            )
        return

    tokens = text.split()
    pos = 0
    if spec.input_format.get("case_count", {}).get("emit") == "explicit":
        t = int(tokens[pos]); pos += 1
        if t != len(job["groups"]):
            raise RetryableError(f"T 不符: {t} != {len(job['groups'])}")
    for group in job["groups"]:
        for item in items(spec):
            if item.get("emit") == "scalar" and item.get("source") == "control":
                name = item["name"]
                val = int(tokens[pos]); pos += 1
                if name in group["control"] and val != int(group["control"][name]):
                    raise RetryableError(f"{name} 与控制值不一致")
        for seg in group["content"]:
            pos += int(seg["count"])
    if pos != len(tokens):
        raise RetryableError(
            f"数据流 token 数不符: 期望 {pos}, 实际 {len(tokens)}"
        )


def find_graph_item(spec: ProblemSpec) -> dict:
    for item in items(spec):
        if item.get("emit") == "graph":
            return item
    raise FatalError("缺少 graph 项")


def read_adjacency(tokens, pos, n, weighted, k_mode):
    adj = []
    for _ in range(n):
        k = int(tokens[pos]); pos += 1
        cnt = k if k_mode == "degree" else k - 1
        if cnt < 0:
            raise FatalError("邻接表 k 非法")
        row = []
        for _ in range(cnt):
            v = int(tokens[pos]); pos += 1
            w = None
            if weighted:
                w = int(tokens[pos]); pos += 1
            row.append((v, w))
        adj.append(row)
    return adj, pos


def parse_graph_cases(spec: ProblemSpec, job: dict[str, Any],
                      text: str) -> list[dict[str, Any]]:
    g = spec.constraints["graph"]
    weighted = bool(g.get("weighted"))
    item = find_graph_item(spec)
    form = item.get("form", "edge_list")
    tokens = text.split()
    pos = 0
    if spec.input_format.get("case_count", {}).get("emit") == "explicit":
        pos += 1

    out = []
    for group in job["groups"]:
        c = group["control"]
        n, m = int(c["n"]), int(c["m"])
        edges = []
        for it in items(spec):
            emit = it.get("emit")
            if emit == "scalar":
                val = int(tokens[pos]); pos += 1
                name = it.get("name")
                if name in c and val != int(c[name]):
                    raise FatalError(f"{name} 与控制值不一致")
            elif emit == "graph":
                if form == "edge_list":
                    for _ in range(m):
                        u = int(tokens[pos]); v = int(tokens[pos + 1])
                        pos += 2
                        w = int(tokens[pos]) if weighted else None
                        if weighted:
                            pos += 1
                        edges.append((u, v, w))
                elif form == "adjacency_list":
                    adj, pos = read_adjacency(
                        tokens, pos, n, weighted,
                        it.get("k_mode", "degree"),
                    )
                    for u, row in enumerate(adj, 1):
                        for v, w in row:
                            if g.get("directed") or u <= v:
                                edges.append((u, v, w))
                else:
                    raise FatalError(f"校验器暂不支持 form: {form}")
        out.append({"n": n, "m": m, "edges": edges})

    if pos != len(tokens):
        raise FatalError(f"最终 .in 有剩余 token: {len(tokens) - pos}")
    return out


def check_graph(g: dict[str, Any], case: dict[str, Any]) -> None:
    n, m, edges = case["n"], case["m"], case["edges"]
    base = int(g.get("vertex_base", 1))
    lo, hi = base, base + n - 1
    seen = set()
    for u, v, w in edges:
        if not (lo <= u <= hi and lo <= v <= hi):
            raise FatalError(f"边端点越界: {u} {v}")
        if u == v and not g.get("self_loops"):
            raise FatalError(f"出现自环: {u}")
        # TODO: directed=true 时重边判定要用 (u, v)，不能用 (min, max)
        key = (min(u, v), max(u, v))
        if g.get("simple"):
            if key in seen:
                raise FatalError(f"出现重边: {u} {v}")
            seen.add(key)
        if g.get("weighted") and w is not None:
            wr = g.get("weight", {})
            if not (wr.get("min", -10**18) <= w <= wr.get("max", 10**18)):
                raise FatalError(f"边权越界: {w}")
    if len(edges) != m:
        raise FatalError(f"m 与实际边数不一致: {m} != {len(edges)}")
    if g.get("connected") and n > 1:
        parent = list(range(n + 1))
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        for u, v, _ in edges:
            a, b = find(u - base + 1), find(v - base + 1)
            if a != b:
                parent[a] = b
        if len({find(i) for i in range(1, n + 1)}) != 1:
            raise FatalError("图不连通")


def validate_final_structure(spec: ProblemSpec, job: dict[str, Any],
                             text: str) -> None:
    """最终 .in 的通用 token 结构校验（sequence / string）。"""
    tokens = text.split()
    pos = 0
    if spec.input_format.get("case_count", {}).get("emit") == "explicit":
        if not tokens:
            raise FatalError("缺少 T")
        t = int(tokens[pos]); pos += 1
        if t != len(job["groups"]):
            raise FatalError(f"T 不符: {t} != {len(job['groups'])}")

    for group in job["groups"]:
        control = group["control"]
        for item in spec.input_format["case"]["items"]:
            emit = item.get("emit")
            if emit == "scalar":
                if pos >= len(tokens):
                    raise FatalError("缺少控制 token")
                val = int(tokens[pos]); pos += 1
                name = item.get("name")
                if name in control and val != int(control[name]):
                    raise FatalError(f"{name} 与控制值不一致")
            elif emit in ("array", "string"):
                name = item.get("name")
                seg = next((s for s in group["content"]
                            if s["name"] == name), None)
                if seg is None:
                    raise FatalError(f"缺少 content: {name}")
                pos += int(seg["count"])
            elif emit == "graph":
                continue
            else:
                raise FatalError(f"未知 item: {emit}")

    if pos != len(tokens):
        raise FatalError(f"最终 .in 有剩余 token: {len(tokens) - pos}")


def validate_in(spec: ProblemSpec, job: dict[str, Any], text: str) -> None:
    if not text.strip():
        raise FatalError(".in 为空")
    if spec.kind == "graph":
        for case in parse_graph_cases(spec, job, text):
            check_graph(spec.constraints["graph"], case)
    elif not spec.input_format.get("line_sensitive"):
        validate_final_structure(spec, job, text)
    if spec.input_format.get("line_sensitive"):
        validate_lines(spec, job, text)


def validate_lines(spec: ProblemSpec, job: dict[str, Any], text: str) -> None:
    lines = [ln for ln in text.splitlines() if ln != ""]
    idx = 0
    if spec.input_format.get("case_count", {}).get("emit") == "explicit":
        idx += 1
    for group in job["groups"]:
        for item in items(spec):
            emit = item.get("emit")
            if emit == "graph":
                if item.get("form") != "edge_list":
                    raise FatalError("line_sensitive 暂不支持该 graph form")
                width = 3 if spec.constraints["graph"].get("weighted") else 2
                for _ in range(int(group["control"]["m"])):
                    if len(lines[idx].split()) != width:
                        raise FatalError(f"第 {idx + 1} 行 token 数不符")
                    idx += 1
                continue
            if idx >= len(lines):
                raise FatalError("行数不足")
            expect = 1
            if emit == "array":
                seg = next((s for s in group["content"]
                            if s["name"] == item.get("name")), None)
                expect = int(seg["count"]) if seg else 0
            if len(lines[idx].split()) != expect:
                raise FatalError(f"第 {idx + 1} 行 token 数不符")
            idx += 1
