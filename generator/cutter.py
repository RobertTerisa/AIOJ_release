from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from models import FatalError, ProblemSpec


def call_cutter(spec: ProblemSpec, job: dict[str, Any], text: str,
                timeout: float) -> str:
    runner = Path(__file__).resolve().parent / "cutter_runner.py"
    limit = int(spec.cutter.get("max_output_bytes", 100 * 1024 * 1024))

    with tempfile.TemporaryDirectory(prefix="aioj_cut_") as td:
        input_path = Path(td) / "input.json"
        output_path = Path(td) / "output.txt"
        input_path.write_text(json.dumps({
            "problem": spec.raw,
            "job": job,
            "text": text,
        }, ensure_ascii=False), encoding="utf-8")

        cmd = [
            sys.executable, str(runner),
            "--cutter", str(spec.cutter_path),
            "--entry", spec.cutter.get("entry", "cut"),
            "--input", str(input_path),
            "--output", str(output_path),
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True,
                                  text=True, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise FatalError(f"cutter 超时: {spec.cutter_path}") from exc
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "无输出").strip()[-4000:]
            raise FatalError(
                f"cutter 失败: {spec.cutter_path}\n{detail}"
            )
        data = output_path.read_bytes()
        if len(data) > limit:
            raise FatalError(
                f"cutter 输出超过上限: {len(data)} > {limit}"
            )
        return data.decode("utf-8")
