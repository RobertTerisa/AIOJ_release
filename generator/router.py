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
from registry import list_generators
from job import read_in_text, write_control_tokens
from models import (FatalError, GroupRecord, ProblemSpec, RetryableError,
                    RouterError, SpecError, TestPointRecord)
from publish import PublishError, publish, sha256_text, write_manifest
from validate import validate_in, verify_content

MAX_ATTEMPTS = 3

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
_GENERATION_KEYS = {"multi_case", "cases"}
_CASE_RULE_KEYS = {"generator", "repeat", "scale", "bind", "mutation"}
_MUTATION_KEYS = {"duplicate", "self_loop"}
_CUTTER_KEYS = {"path", "entry", "timeout_s", "max_output_bytes"}
_SAMPLE_KEYS = {"name", "job", "text", "input", "confirmed"}


def _check_unknown(obj, allowed, where):
    if not isinstance(obj, dict):
        raise SpecError(f"{where} 必须是 JSON 对象")
    unknown = sorted(set(obj) - allowed)
    if unknown:
        raise SpecError(f"{where} 含未知字段: {unknown}")


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
    for i, rule in enumerate(gen.get("cases", [])):
        _check_unknown(rule, _CASE_RULE_KEYS, f"generation.cases[{i}]")
        if "mutation" in rule:
            _check_unknown(rule["mutation"], _MUTATION_KEYS,
                           f"generation.cases[{i}].mutation")

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
    rng = random.Random(derive_seed(run_seed, "T", ordinal, 1))
    lo_expr, hi_expr = norm_range(mc)
    return choose(eval_int(lo_expr, {}), eval_int(hi_expr, {}),
                  rule.get("scale", "random"), rng)


def build_groups(spec: ProblemSpec, rule: dict, run_seed: int,
                 T: int, attempt: int) -> list[GroupRecord]:
    groups = []
    for i in range(1, T + 1):
        seed = derive_seed(run_seed, rule["generator"], i, attempt)
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
        raise SpecError(f"生成器不存在: {exe}")
    T = bind_T(spec, rule, run_seed, ordinal)
    test_point_id = f"{spec.problem_id}__{rule['generator']}__{ordinal:03d}"
    last_error = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            groups = build_groups(spec, rule, run_seed, T, attempt)
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
    try:
        spec = load_spec(args.spec)

        known = {g.id for g in list_generators()}
        unknown = [x for x in args.only if x not in known]
        if unknown:
            print(f"[router error] --only 含未注册生成器: {', '.join(unknown)}",
                  file=sys.stderr)
            print(f"[router error] 可用: {', '.join(sorted(known))}",
                  file=sys.stderr)
            return 2

        for rule in spec.generation["cases"]:
            if rule["generator"] not in known:
                print(f"[router error] problem.json 引用了未注册生成器: "
                      f"{rule['generator']}", file=sys.stderr)
                return 2

        selected = [
            r for r in spec.generation["cases"]
            if not args.only or r["generator"] in args.only
        ]
        if not selected:
            print("[router error] --only 没有匹配到任何 generation.cases",
                  file=sys.stderr)
            return 2

        run_seed = args.seed if args.seed is not None else secrets.randbelow(2**31)
        root = args.generator_root or (Path(__file__).parent / "bin")

        args.output_dir.mkdir(parents=True, exist_ok=True)
        tmp_dir = args.output_dir / f".tmp_{run_seed}"
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        tmp_dir.mkdir(parents=True)
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
                })
                print(f"[gen] {final.name}")

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
            print(f"[router error] 临时目录已保留: {tmp_dir}", file=sys.stderr)
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

        shutil.rmtree(tmp_dir, ignore_errors=True)
        print(f"[done] {len(moved)} 个 .in -> {args.output_dir}")
        return 0
    except RouterError as exc:
        print(f"[router error] {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"[router error] 系统错误: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
