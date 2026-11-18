from __future__ import annotations

import argparse
import json
import random
import secrets
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bind import bind_case, choose, content_specs, derive_seed, eval_int, norm_range
from cutter import call_cutter
from executor import build_args, generator_path, run_generator
from registry import available_generator_ids, list_generators
from job import read_in_text, write_control_tokens
from models import (DiagnosticError, FatalError, GroupRecord, ProblemSpec,
                    RetryableError, RouterError, SpecError, TestPointRecord)
from publish import PublishError, publish, sha256_text, write_manifest
from validate import validate_in, verify_content

MAX_ATTEMPTS = 3

# router 自己创建的临时目录都带这个标记文件，清理历史目录时只认带标记的，
# 避免误删用户自己放在 <output_dir> 下的 .tmp_* 目录。
ROUTER_TMP_MARKER = ".router_tmp"

_TOP_KEYS = {"schema_version", "problem_id", "kind", "meta",
             "constraints", "input_format", "generation", "cutter", "samples"}
_META_KEYS = {"source", "time_limit_ms", "constraints_source",
              "confirmed_by_human"}
_CONSTRAINTS_KEYS = {"variables", "arrays", "strings", "graph"}
_GRAPH_KEYS = {"n", "m", "directed", "weighted", "simple", "self_loops",
               "connected", "vertex_base", "weight"}
_VARIABLE_KEYS = {"min", "max", "expr"}
_ARRAY_KEYS = {"name", "length", "min", "max"}
_STRINGS_KEYS = {"count", "length", "lengths", "alphabet"}
_INPUT_FORMAT_KEYS = {"summary", "line_sensitive", "encoding",
                      "case_count", "case"}
_CASE_COUNT_KEYS = {"emit", "name"}
_CASE_KEYS = {"items"}
_ITEM_KEYS = {"emit", "name", "source", "length",
              "form", "k_mode", "self_loop", "neighbor_order"}
_ITEM_EMITS = {"scalar", "array", "graph", "string"}
_GENERATION_KEYS = {"multi_case", "cases", "coverage"}
_CASE_RULE_KEYS = {"generator", "repeat", "scale", "bind",
                   "mutation", "name"}
# coverage：把「跑什么」从白名单（cases[]）改成「默认全跑 + 否决清单」。
_COVERAGE_KEYS = {"target_groups", "default_plan", "exclude"}
_PLAN_KEYS = {"scale", "repeat"}
_EXCLUDE_KEYS = {"generator", "reason", "reason_code", "evidence"}
_EVIDENCE_KEYS = {"file", "quote"}
_REASON_CODES = {"impossible_by_semantics", "not_applicable",
                 "redundant", "other"}
_MUTATION_KEYS = {"duplicate", "self_loop"}
_CUTTER_KEYS = {"path", "entry", "timeout_s", "max_output_bytes"}
_SAMPLE_KEYS = {"name", "job", "text", "input", "confirmed"}


def _sanitize(value: object) -> str:
    # 防止字段值里的换行伪造额外的 [router error] 行，让调用方按行解析时出错。
    return str(value).replace(chr(10), " ").replace(chr(13), " ")


def _emit_router_error(exc: RouterError) -> None:
    """把 router 错误渲染成 [router error] 多行文本。

    DiagnosticError 带稳定 code 与结构化字段，按 code= / message= / 字段名=value
    逐行输出，方便调用方按 code 分支处理；其它 RouterError 保持旧的单行文案。
    """
    if isinstance(exc, DiagnosticError):
        print(f"[router error] code={exc.code}", file=sys.stderr)
        print(f"[router error] message={exc}", file=sys.stderr)
        for key, value in exc.fields.items():
            print(f"[router error] {key}={_sanitize(value)}", file=sys.stderr)
    else:
        print(f"[router error] {exc}", file=sys.stderr)


def _require_registered_generators(ids) -> None:
    """已注册才继续；多个未注册 id 聚合成一条错误，别让调用方逐条试。

    --only 与 generation.cases[].generator 共用同一 helper，保证两种入口
    报同一份 code / available，不会各写一套文案。
    """
    known = {g.id for g in list_generators()}
    unknown = sorted({x for x in ids if x not in known})
    if unknown:
        joined = ", ".join(unknown)
        raise DiagnosticError(
            "unsupported-generator",
            f"未注册的生成器: {joined}",
            generator=joined,
            available=available_generator_ids(),
            hint="请改用已注册生成器，或由负责人实现、编译并注册该生成器",
        )


def _check_unknown(obj, allowed, where):
    if not isinstance(obj, dict):
        raise DiagnosticError(
            "invalid-schema",
            f"{where} 必须是 JSON 对象",
            where=where,
            expected="object",
            actual=type(obj).__name__,
        )
    unknown = sorted(set(obj) - allowed)
    if unknown:
        raise DiagnosticError(
            "unknown-field",
            f"{where} 含未知字段",
            where=where,
            unknown=", ".join(unknown),
            allowed=", ".join(sorted(allowed)),
        )


def _expect_list(value, where):
    """数组类型守卫：`cases` / `exclude` 写成对象或标量时，别让 enumerate() 抛裸 TypeError。"""
    if not isinstance(value, list):
        raise DiagnosticError(
            "invalid-coverage",
            f"{where} 必须是 JSON 数组",
            where=where,
            expected="array",
            actual=type(value).__name__,
        )
    return value


def _check_plan(plan, where):
    if plan is None:
        return
    _check_unknown(plan, _PLAN_KEYS, where)
    rep = plan.get("repeat", "auto")
    if rep != "auto" and (isinstance(rep, bool) or not isinstance(rep, int)
                          or rep < 1):
        raise DiagnosticError(
            "invalid-coverage",
            f"{where}.repeat 必须是正整数或 \"auto\"（当前 {rep!r}）",
            where=f"{where}.repeat",
            expected='正整数或 "auto"',
            actual=rep,
        )


def parse_args():
    p = argparse.ArgumentParser(description="AIOJ 数据生成路由")
    p.add_argument("--spec", "--params", dest="spec", type=Path, default=None)
    p.add_argument("--output-dir", type=Path, default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--generator-root", type=Path, default=None)
    p.add_argument("--only", action="append", default=[])
    p.add_argument("--timeout", type=float, default=60.0)
    p.add_argument("--manifest", type=Path, default=None)
    p.add_argument("--list-generators", action="store_true")
    return p.parse_args()


def load_spec(path: Path) -> ProblemSpec:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SpecError(f"无法读取规格: {path}: {exc}") from exc
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SpecError(f"规格 JSON 解析失败: {path}: {exc}") from exc
    if raw.get("schema_version") != 2:
        raise SpecError(
            f"只支持 schema_version=2（当前 {raw.get('schema_version')!r}）；"
            "v1 已废弃，请迁移到 v2"
        )
    for key in ("problem_id", "kind", "constraints", "input_format",
                "generation", "cutter", "samples"):
        if key not in raw:
            raise SpecError(f"规格缺少字段: {key}")
    if raw["kind"] not in ("sequence", "graph", "string"):
        raise SpecError(f"不支持的 kind: {raw['kind']}")

    _check_unknown(raw, _TOP_KEYS, "顶层")
    _check_unknown(raw.get("meta", {}), _META_KEYS, "meta")

    constraints = raw["constraints"]
    _check_unknown(constraints, _CONSTRAINTS_KEYS, "constraints")
    if "graph" in constraints:
        _check_unknown(constraints["graph"], _GRAPH_KEYS, "constraints.graph")
    for name, var in constraints.get("variables", {}).items():
        if isinstance(var, dict):
            _check_unknown(var, _VARIABLE_KEYS, f"constraints.variables.{name}")
    for i, arr in enumerate(constraints.get("arrays", [])):
        _check_unknown(arr, _ARRAY_KEYS, f"constraints.arrays[{i}]")
    if "strings" in constraints:
        _check_unknown(constraints["strings"], _STRINGS_KEYS, "constraints.strings")

    fmt = raw["input_format"]
    _check_unknown(fmt, _INPUT_FORMAT_KEYS, "input_format")
    if "case_count" in fmt:
        _check_unknown(fmt["case_count"], _CASE_COUNT_KEYS,
                       "input_format.case_count")
    case = fmt.get("case", {})
    _check_unknown(case, _CASE_KEYS, "input_format.case")
    for i, item in enumerate(case.get("items", [])):
        _check_unknown(item, _ITEM_KEYS, f"input_format.case.items[{i}]")
        if item.get("emit") not in _ITEM_EMITS:
            raise SpecError(
                f"input_format.case.items[{i}].emit 不支持: "
                f"{item.get('emit')!r}"
            )

    gen = raw["generation"]
    _check_unknown(gen, _GENERATION_KEYS, "generation")
    # cases 现在可省略（coverage 模式下由默认计划补齐）；但类型写错也不能冒 traceback。
    cases_raw = gen.get("cases")
    if cases_raw is None:
        cases_raw = []
    _expect_list(cases_raw, "generation.cases")
    # bind 是“覆盖已声明变量”的入口，不是新变量声明处：图题只允许覆盖 base_m
    # （dup/loop 走 mutation，n/m 由 constraints 决定），其余题型只允许覆盖
    # constraints.variables 里已经声明过的变量。
    allowed_bind = (
        {"base_m"} if raw["kind"] == "graph"
        else set(constraints.get("variables", {}))
    )
    for i, rule in enumerate(cases_raw):
        _check_unknown(rule, _CASE_RULE_KEYS, f"generation.cases[{i}]")
        if "mutation" in rule:
            _check_unknown(rule["mutation"], _MUTATION_KEYS,
                           f"generation.cases[{i}].mutation")
        bind = rule.get("bind", {})
        if not isinstance(bind, dict):
            raise DiagnosticError(
                "invalid-schema",
                f"generation.cases[{i}].bind 必须是 JSON 对象",
                where=f"generation.cases[{i}].bind",
                expected="object",
                actual=type(bind).__name__,
            )
        unknown_bind = sorted(set(bind) - allowed_bind)
        if unknown_bind:
            raise DiagnosticError(
                "unknown-bind-key",
                f"generation.cases[{i}].bind 含未声明的键",
                where=f"generation.cases[{i}].bind",
                unknown=", ".join(unknown_bind),
                allowed=", ".join(sorted(allowed_bind)) or "<none>",
            )

    coverage = gen.get("coverage")
    if coverage is not None:
        _check_unknown(coverage, _COVERAGE_KEYS, "generation.coverage")
        _check_plan(coverage.get("default_plan"),
                    "generation.coverage.default_plan")

        target = coverage.get("target_groups")
        if target is not None and (isinstance(target, bool)
                                   or not isinstance(target, int) or target < 1):
            raise DiagnosticError(
                "invalid-coverage",
                f"generation.coverage.target_groups 必须是正整数（当前 {target!r}）",
                where="generation.coverage.target_groups",
                expected="正整数",
                actual=target,
            )
        # repeat:"auto" 必须能算出目标组数：在 load_spec 阶段就快速失败，
        # 不要拖到 expand_coverage 才报（那时目录可能已经建好了）。
        plan = coverage.get("default_plan") or {}
        if plan.get("repeat", "auto") == "auto" and target is None:
            raise DiagnosticError(
                "invalid-coverage",
                'coverage.default_plan.repeat 为 "auto" 但未声明 target_groups',
                where="generation.coverage.target_groups",
                expected="正整数（普通/图论 50，搜索/DFS/BFS/回溯 20）",
                actual="<缺失>",
            )

        registered = {g.id for g in list_generators()}
        seen: set[str] = set()
        exclude = coverage.get("exclude")
        if exclude is None:
            exclude = []
        _expect_list(exclude, "generation.coverage.exclude")
        for i, entry in enumerate(exclude):
            where = f"generation.coverage.exclude[{i}]"
            _check_unknown(entry, _EXCLUDE_KEYS, where)

            gid = entry.get("generator")
            if not isinstance(gid, str) or not gid:
                raise DiagnosticError(
                    "invalid-coverage",
                    f"{where}.generator 缺失或不是字符串",
                    where=f"{where}.generator",
                    expected="已注册的生成器 id",
                    actual=gid,
                )
            if gid not in registered:
                # 与 T-040 的 unsupported-generator 完全同构：共用同一份 available 列表。
                raise DiagnosticError(
                    "unsupported-generator",
                    f"{where} 引用了未注册的生成器: {gid}",
                    generator=gid,
                    available=available_generator_ids(),
                    hint="请改用已注册生成器，或由负责人实现、编译并注册该生成器",
                )
            if not str(entry.get("reason") or "").strip():
                raise DiagnosticError(
                    "invalid-coverage",
                    f"{where}.reason 不能为空（每次减法都必须给理由）",
                    where=f"{where}.reason",
                    expected="非空字符串",
                    actual=entry.get("reason"),
                )
            if gid in seen:
                raise DiagnosticError(
                    "invalid-coverage",
                    f"{where}.generator 重复: {gid}",
                    where=f"{where}.generator",
                    expected="每个生成器最多一条否决条目",
                    actual=gid,
                )
            seen.add(gid)

            reason_code = entry.get("reason_code")
            if reason_code is not None and reason_code not in _REASON_CODES:
                raise DiagnosticError(
                    "invalid-coverage",
                    f"{where}.reason_code 不支持: {reason_code!r}",
                    where=f"{where}.reason_code",
                    expected=", ".join(sorted(_REASON_CODES)),
                    actual=reason_code,
                )
            if entry.get("evidence") is not None:
                # coverage 语义错误统一走 invalid-coverage；这里不能用 _check_unknown，
                # 它按 invalid-schema 报，会让调用方的 code= 分支表多认一个码。
                if not isinstance(entry["evidence"], dict):
                    raise DiagnosticError(
                        "invalid-coverage",
                        f"{where}.evidence 必须是 JSON 对象",
                        where=f"{where}.evidence",
                        expected="object",
                        actual=type(entry["evidence"]).__name__,
                    )
                _check_unknown(entry["evidence"], _EVIDENCE_KEYS,
                               where + ".evidence")

    _check_unknown(raw["cutter"], _CUTTER_KEYS, "cutter")
    for i, sample in enumerate(raw["samples"]):
        _check_unknown(sample, _SAMPLE_KEYS, f"samples[{i}]")

    return ProblemSpec(
        path=path.resolve(), raw=raw,
        problem_id=raw["problem_id"], kind=raw["kind"],
        constraints=raw["constraints"], input_format=raw["input_format"],
        generation=raw["generation"], cutter=raw["cutter"],
        samples=raw["samples"],
    )


def bind_T(spec: ProblemSpec, rule: dict, run_seed: int, ordinal: int) -> int:
    mc = spec.generation.get("multi_case", {}).get("T")
    if mc is None:
        return 1
    rng = random.Random(derive_seed(run_seed, "T", ordinal, 0, 1))
    lo_expr, hi_expr = norm_range(mc)
    return choose(eval_int(lo_expr, {}), eval_int(hi_expr, {}),
                  rule.get("scale", "random"), rng)


def build_groups(spec: ProblemSpec, rule: dict, run_seed: int,
                 T: int, attempt: int, ordinal: int) -> list[GroupRecord]:
    groups = []
    for i in range(1, T + 1):
        seed = derive_seed(run_seed, rule["generator"], ordinal, i, attempt)
        bound = bind_case(spec, rule, i, seed)
        groups.append(GroupRecord(
            index=i, seed=seed, attempt=attempt, bound=bound,
            content=content_specs(spec, bound),
        ))
    return groups


def generate_test_point(spec: ProblemSpec, rule: dict, run_seed: int,
                        ordinal: int, root: Path, tmp_dir: Path,
                        timeout: float) -> tuple[Path, int]:
    exe = generator_path(root, spec, rule)
    if not exe.exists():
        raise DiagnosticError(
            "generator-not-built",
            f"生成器不存在: {exe}",
            generator=rule["generator"],
            expected=str(exe),
            available=available_generator_ids(),
            hint="请把生成器编译到 generator/<kind>/ 下，或检查 --generator-root",
        )
    T = bind_T(spec, rule, run_seed, ordinal)
    test_point_id = f"{spec.problem_id}__{rule['generator']}__{ordinal:03d}"
    last_error = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            groups = build_groups(spec, rule, run_seed, T, attempt, ordinal)
            record = TestPointRecord(
                test_point_id=test_point_id, problem_id=spec.problem_id,
                generator=rule["generator"], run_seed=run_seed,
                stream="lines" if spec.kind == "string" else "tokens",
                groups=groups,
            )
            in_path = tmp_dir / f"{test_point_id}.in"
            with in_path.open("w", encoding="utf-8", newline="\n") as f:
                if spec.input_format["case_count"].get("emit") == "explicit":
                    f.write(f"{T}\n")
            for group in groups:
                with in_path.open("a", encoding="utf-8", newline="\n") as f:
                    write_control_tokens(f, spec, group.bound)
                run_generator(
                    exe,
                    build_args(spec, rule, group.bound, group.seed, in_path),
                    timeout,
                )
            raw = read_in_text(in_path)
            verify_content(spec, record.job_dict(), raw)
            out = call_cutter(spec, record.job_dict(), raw,
                              float(spec.cutter.get("timeout_s", 30)))
            validate_in(spec, record.job_dict(), out)
            in_path.write_bytes(out.encode("utf-8"))
            return in_path, len(groups)
        except RetryableError as exc:
            last_error = exc
            # 失败 attempt 只打日志，不写入 job 对象 / manifest
            print(f"[retry] {rule['generator']} attempt={attempt}: {exc}",
                  file=sys.stderr)

    raise FatalError(f"{rule['generator']} 重试耗尽: {last_error}")


def replay_samples(spec: ProblemSpec, timeout: float) -> None:
    """只做格式检查：cutter 输出是否等于题面样例输入。
    程序输出检查由 diff_runner 负责，这里不比较 sample["output"]。
    """
    if not spec.samples:
        raise FatalError("samples 为空，无法做样例回放")

    for sample in spec.samples:
        name = sample.get("name", "sample")
        for key in ("job", "text", "input"):
            if key not in sample:
                raise FatalError(f"样例缺少 {key}: {name}")
        if not sample.get("confirmed"):
            raise FatalError(f"样例未经确认: {name}")

        out = call_cutter(spec, sample["job"], sample["text"], timeout)
        expected = sample["input"]
        if spec.input_format.get("line_sensitive"):
            ok = out.splitlines() == expected.splitlines()
        else:
            ok = out.split() == expected.split()
        if not ok:
            raise FatalError(f"样例回放失败: {name}")


def cleanup_stale_tmp(output_dir: Path, current_seed: int) -> None:
    """清理本题目录下历史 router 临时目录，保留当前 run_seed。

    只碰“目录 + 带 .router_tmp 标记 + 非当前 seed”的 .tmp_*：
    symlink 不跟随、无标记的目录视为用户数据、当前 seed 交给调用方重建。
    """
    for child in output_dir.glob(".tmp_*"):
        if child.is_symlink() or not child.is_dir():
            continue
        if child.name == f".tmp_{current_seed}":
            continue
        if not (child / ROUTER_TMP_MARKER).is_file():
            continue
        try:
            shutil.rmtree(child)
        except OSError as exc:
            print(f"[警告] 历史临时目录清理失败: {child}: {exc}",
                  file=sys.stderr)


def _dup_groups(files: list[dict]) -> list[list[str]]:
    """按 sha256 归并文件名，按首次出现顺序只返回重复的组（每组一行）。"""
    by_hash: dict[str, list[str]] = {}
    for f in files:
        by_hash.setdefault(f["sha256"], []).append(f["in"])
    return [names for names in by_hash.values() if len(names) > 1]


def _verify_evidence(spec: ProblemSpec, entry: dict) -> None:
    """只检查理由引用的原文确实在题面里，不判断理由是否正确。
    匹配不到只提示，不阻塞发布。"""
    ev = entry.get("evidence") or {}
    quote = " ".join(str(ev.get("quote") or "").split())
    if not quote:
        return
    path = spec.path.parent / ev.get("file", f"{spec.problem_id}.md")
    try:
        text = " ".join(path.read_text(encoding="utf-8").split())
    except OSError as exc:
        print(f"[coverage][evidence][warn] {entry['generator']}: 证据文件读不到: "
              f"{path.name}（{exc}）", file=sys.stderr)
        return
    if quote not in text:
        print(f"[coverage][evidence][warn] {entry['generator']}: 否决理由引用的原文"
              f"在 {path.name} 中找不到: {quote!r}", file=sys.stderr)


def expand_coverage(spec: ProblemSpec, root: Path, only: list[str]
                    ) -> dict | None:
    """coverage 模式：人工 cases 原样保留 + 只给「没被提到」的候选补默认计划。
    返回 None 表示 spec 未启用 coverage，调用方继续走旧的白名单逻辑。"""
    cov = spec.generation.get("coverage")
    if cov is None:
        print("[coverage][legacy] 白名单模式，不保证全覆盖")
        return None

    candidates = [g.id for g in list_generators()
                  if g.kind == spec.kind
                  and (root / g.kind / g.exe).exists()]
    excluded: list[dict] = []
    skipped: list[str] = []
    for entry in cov.get("exclude", []):
        gid = entry["generator"]
        if gid in candidates:
            excluded.append({"generator": gid, "reason": entry["reason"],
                             "reason_code": entry.get("reason_code", "")})
            _verify_evidence(spec, entry)
            print(f"[coverage][exclude] {gid}: {entry['reason']}", file=sys.stderr)
        else:
            # 不阻碍人写全清单：kind 不符或未编译只记一笔，不报错。
            skipped.append(gid)
            print(f"[coverage][skip] {gid}: 不在候选集（kind 不符或生成器未编译）",
                  file=sys.stderr)

    cases = list(spec.generation.get("cases", []))
    manual: list[dict] = []
    for rule in cases:
        gid = rule["generator"]
        if gid in {e["generator"] for e in excluded}:
            print(f"[coverage][warn] 人工条目被判否决不执行: {gid}"
                  f"（name={rule.get('name', '')}）", file=sys.stderr)
            continue
        if only and gid not in only:
            continue
        manual.append(rule)
    if only:
        print("[coverage][skipped] --only 生效，覆盖率统计不完整", file=sys.stderr)

    present = {r["generator"] for r in cases}
    excluded_ids = {e["generator"] for e in excluded}
    missing = [gid for gid in candidates
               if gid not in present and gid not in excluded_ids
               and (not only or gid in only)]

    plan = dict(cov.get("default_plan", {"scale": "random", "repeat": "auto"}))
    auto = plan.get("repeat", "auto") == "auto"
    target = cov.get("target_groups")
    if auto and target is None:
        # 防御性兜底：load_spec() 已快速失败过；这里再拦一次，避免以后有人
        # 单独调用 expand_coverage() 时绕过校验。错误类型与码必须与 load_spec 一致。
        raise DiagnosticError(
            "invalid-coverage",
            'coverage.default_plan.repeat 为 "auto" 但未声明 target_groups',
            where="generation.coverage.target_groups",
            expected="正整数（普通/图论 50，搜索/DFS/BFS/回溯 20）",
            actual="<缺失>",
        )

    planned: list[dict] = []
    if missing:
        if auto:
            # 只补差额，均分且不超目标：余数给前几名，避免 ceil 造成多一组。
            have = sum(int(r.get("repeat", 1)) for r in manual)
            gap = max(0, int(target) - have)
            base, rem = divmod(gap, len(missing))
            repeats = [max(1, base + (1 if i < rem else 0))
                       for i in range(len(missing))]
        else:
            repeats = [max(1, int(plan["repeat"]))] * len(missing)
        base_plan = {k: v for k, v in plan.items() if k != "repeat"}
        for gid, rep in zip(missing, repeats):
            planned.append(dict(base_plan, generator=gid, repeat=rep))
        for rule in planned:
            print(f"[coverage][plan] {rule['generator']}: repeat={rule['repeat']}",
                  file=sys.stderr)

    return {
        "rules": manual + planned,
        "manual": manual,
        "planned": planned,
        "candidates": candidates,
        "excluded": excluded,
        "skipped": skipped,
        "target_groups": target,
        "auto": auto,
        "plan": plan,
    }


def _report_coverage(cov: dict, groups_actual: int,
                     manifest: dict) -> None:
    """打印两行账本并写进 manifest：不落盘就无法复现「这轮为什么是 N 组」。"""
    rules = cov["rules"]
    covered = sorted({r["generator"] for r in rules})
    print(f"[coverage] 候选 {len(cov['candidates'])} = 覆盖 {len(covered)}"
          f" + 否决 {len(cov['excluded'])} + 跳过 {len(cov['skipped'])}")
    planned = cov["planned"]
    if cov["auto"] and planned:
        reps = [r["repeat"] for r in planned]
        detail = (f"{reps[0]}/候选" if len(set(reps)) == 1
                  else "/".join(str(x) for x in reps))
        auto_note = f"repeat: auto -> {detail}"
    elif cov["auto"]:
        auto_note = "repeat: auto -> 无可补候选"
    else:
        auto_note = f"repeat: {cov['plan'].get('repeat')}"
    target = cov["target_groups"]
    target_txt = "未声明" if target is None else f"{target} 组"
    print(f"[coverage] 规则 {len(rules)} 条 = 人工 {len(cov['manual'])}"
          f" + 默认计划 {len(planned)}；目标 {target_txt}，"
          f"实际 {groups_actual} 组（{auto_note}）")
    if target is not None and groups_actual < target:
        print(f"[coverage][warn] 实际 {groups_actual} 组 < 目标 {target} 组："
              f"人工样例不足，且没有可补的候选生成器")
    manifest["coverage"] = {
        "mode": "exhaustive",
        "target_groups": target,
        "effective_repeat": (planned[0]["repeat"]
                             if planned and len({p["repeat"] for p in planned}) == 1
                             else None),
        "planned_repeats": {p["generator"]: p["repeat"] for p in planned},
        "manual_rules": len(cov["manual"]),
        "planned_rules": len(planned),
        "groups": groups_actual,
        "candidates": cov["candidates"],
        "covered": covered,
        "excluded": cov["excluded"],
        "skipped": cov["skipped"],
    }


def main() -> int:
    args = parse_args()
    if args.list_generators:
        root = args.generator_root or (Path(__file__).parent / "bin")
        for g in list_generators():
            exe = root / g.kind / g.exe
            status = "ready" if exe.exists() else "missing"
            print(f"{g.id}	{g.kind}	{status}	{g.exe}")
        return 0
    if args.spec is None:
        print("[router error] 缺少 --spec", file=sys.stderr)
        return 2
    if args.output_dir is None:
        print("[router error] 缺少 --output-dir", file=sys.stderr)
        return 2

    # 失败时要把“临时目录还留着”告诉调用方，否则只能靠猜路径；
    # 用标志位去重，保证同一条信息只打印一次。
    tmp_dir: Path | None = None
    tmp_kept_reported = False

    def report_tmp_kept() -> None:
        nonlocal tmp_kept_reported
        if tmp_kept_reported or tmp_dir is None or not tmp_dir.exists():
            return
        tmp_kept_reported = True
        print(f"[router error] 临时目录已保留: {tmp_dir}", file=sys.stderr)

    try:
        spec = load_spec(args.spec)

        # root 必须早于 expand_coverage()：候选集由「注册表 + 已编译 exe」决定。
        root = args.generator_root or (Path(__file__).parent / "bin")

        _require_registered_generators(args.only)
        _require_registered_generators(
            [rule["generator"] for rule in spec.generation.get("cases", [])]
        )

        coverage = expand_coverage(spec, root, args.only)
        selected = coverage["rules"] if coverage is not None else [
            r for r in spec.generation.get("cases", [])
            if not args.only or r["generator"] in args.only
        ]
        if not selected:
            print("[router error] --only 没有匹配到任何 generation.cases",
                  file=sys.stderr)
            return 2

        run_seed = args.seed if args.seed is not None else secrets.randbelow(2**31)

        # 生成器预检必须在建目录、跑样例回放之前：否则 exe 缺失会被
        # “samples 为空 / cutter 报错”遮住，还会留下无意义的临时目录。
        for rule in selected:
            exe = generator_path(root, spec, rule)
            if not exe.exists():
                raise DiagnosticError(
                    "generator-not-built",
                    f"生成器不存在: {exe}",
                    generator=rule["generator"],
                    expected=str(exe),
                    available=available_generator_ids(),
                    hint="请把生成器编译到 generator/<kind>/ 下，或检查 --generator-root",
                )

        args.output_dir.mkdir(parents=True, exist_ok=True)
        # 先清历史（只认带标记的），再处理当前 seed 目录。
        cleanup_stale_tmp(args.output_dir, run_seed)

        tmp_dir = args.output_dir / f".tmp_{run_seed}"
        if tmp_dir.exists():
            # 无标记说明不是 router 建的，可能是用户数据；拒绝删除而不是覆盖。
            if not (tmp_dir / ROUTER_TMP_MARKER).is_file():
                print(f"[router error] 临时目录路径已存在且缺少标记，拒绝删除: {tmp_dir}",
                      file=sys.stderr)
                return 2
            try:
                shutil.rmtree(tmp_dir)
            except OSError as exc:
                print(f"[router error] 当前临时目录清理失败: {tmp_dir}: {exc}",
                      file=sys.stderr)
                return 2
        tmp_dir.mkdir(parents=True)
        (tmp_dir / ROUTER_TMP_MARKER).write_text("router tmp", encoding="utf-8")
        replay_samples(spec, float(spec.cutter.get("timeout_s", 30)))

        manifest = {
            "schema_version": 2,
            "problem_id": spec.problem_id,
            "run_seed": run_seed,
            "status": "ready",
            "files": [],
        }

        ordinal = 0
        for rule in selected:
            for _ in range(int(rule.get("repeat", 1))):
                ordinal += 1
                final, group_count = generate_test_point(
                    spec, rule, run_seed, ordinal, root, tmp_dir, args.timeout
                )
                text = final.read_text(encoding="utf-8")
                manifest["files"].append({
                    "in": final.name,
                    "sha256": sha256_text(text),
                    "groups": group_count,
                    # 用例用途标签：区分「故意重复的极端样例」和「凑数复制」。
                    "name": rule.get("name", ""),
                })
                print(f"[gen] {final.name}")

        if coverage is not None:
            _report_coverage(coverage, len(manifest["files"]), manifest)

        # 发布前统计唯一性：只告警，不阻塞。
        # 可行域小于组数的题（判断题、n<=10、合法输入稀疏）不可能全部互不相同。
        sha_list = [f["sha256"] for f in manifest["files"]]
        uniq = len(set(sha_list))
        dup = len(sha_list) - uniq
        print(f"[verify] {len(sha_list)} 份数据 / {uniq} 份互不相同")
        if dup:
            print(f"[warn] 存在 {dup} 份重复数据，已放行（不阻塞发布）",
                  file=sys.stderr)
            for names in _dup_groups(manifest["files"]):
                print(f"[warn] 重复: {' == '.join(names)}", file=sys.stderr)

        if args.manifest:
            write_manifest(args.manifest, manifest)  # status = ready

        try:
            moved = publish(tmp_dir, args.output_dir)
        except PublishError as exc:
            manifest["status"] = "failed"
            if args.manifest:
                try:
                    write_manifest(args.manifest, manifest)
                except OSError as write_exc:
                    print(f"[router error] failed manifest 写入失败: {write_exc}",
                          file=sys.stderr)
            print(f"[router error] {exc}", file=sys.stderr)
            report_tmp_kept()
            return 1

        manifest["status"] = "ok"
        if args.manifest:
            try:
                write_manifest(args.manifest, manifest)
            except OSError as exc:
                print(f"[router error] manifest 写入失败: {exc}", file=sys.stderr)
                print(f"[router error] 数据已发布，临时目录保留: {tmp_dir}",
                      file=sys.stderr)
                return 2

        # 清理失败不影响已发布数据，但不能静默忽略：调用方需要知道残留目录。
        try:
            shutil.rmtree(tmp_dir)
        except OSError as exc:
            print(f"[警告] 临时目录清理失败（数据已发布）: {tmp_dir}: {exc}",
                  file=sys.stderr)
        print(f"[done] {len(moved)} 个 .in -> {args.output_dir}")
        return 0
    except RouterError as exc:
        _emit_router_error(exc)
        report_tmp_kept()
        return 2
    except OSError as exc:
        print(f"[router error] 系统错误: {exc}", file=sys.stderr)
        report_tmp_kept()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
