from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class PublishError(Exception):
    """发布失败；调用方保留临时目录并写 status=failed。"""


def publish(tmp_dir: Path, target_dir: Path) -> list[Path]:
    """逐文件 os.replace；不做目录级原子替换。"""
    target_dir.mkdir(parents=True, exist_ok=True)
    sources = sorted(tmp_dir.glob("*.in"))
    if not sources:
        raise PublishError(f"没有可发布的 .in: {tmp_dir}")
    moved = []
    for src in sources:
        dst = target_dir / src.name
        try:
            os.replace(src, dst)
        except OSError as exc:
            raise PublishError(
                f"发布失败: {src} -> {dst}: {exc}"
            ) from exc
        moved.append(dst)
    return moved


def write_manifest(path: Path, data: dict[str, Any]) -> None:
    # 直接写字节：Windows 上 write_text 会把 "\n" 翻成 "\r\n"，
    # 导致同一 run_seed 的 manifest 在不同平台上字节不一致。
    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload.encode("utf-8"))
