from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


def load_cutter(path: Path, entry: str):
    spec = importlib.util.spec_from_file_location("aioj_cutter", str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 cutter: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    func = getattr(module, entry, None)
    if not callable(func):
        raise RuntimeError(f"cutter 缺少入口 {entry}: {path}")
    return func


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cutter", type=Path, required=True)
    parser.add_argument("--entry", default="cut")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    data = json.loads(args.input.read_text(encoding="utf-8"))
    func = load_cutter(args.cutter, args.entry)
    text = func(data["problem"], data["job"], data["text"])
    if not isinstance(text, str):
        raise RuntimeError("cutter 必须返回 str")
    # 直接写字节：避免 Windows 上 write_text 把 "\n" 翻成 "\r\n"，
    # 否则 call_cutter 读回的文本与 cutter 返回值不一致（样例回放会假失败）。
    args.output.write_bytes(text.encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
