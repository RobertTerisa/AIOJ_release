from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class RouterError(Exception): ...
class SpecError(RouterError): ...
class BindError(RouterError): ...
class RetryableError(RouterError): ...
class FatalError(RouterError): ...


@dataclass(frozen=True)
class ProblemSpec:
    path: Path
    raw: dict[str, Any]
    problem_id: str
    kind: str
    constraints: dict[str, Any]
    input_format: dict[str, Any]
    generation: dict[str, Any]
    cutter: dict[str, Any]
    samples: list[dict[str, Any]]

    @property
    def cutter_path(self) -> Path:
        return self.path.parent / self.cutter["path"]


@dataclass
class GroupRecord:
    index: int
    seed: int
    attempt: int
    bound: dict[str, Any]
    content: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "seed": self.seed,
            "attempt": self.attempt,
            "control": {k: v for k, v in self.bound.items()
                        if not k.startswith("_")},
            "content": self.content,
        }


@dataclass
class TestPointRecord:
    test_point_id: str
    problem_id: str
    generator: str
    run_seed: int
    stream: str = "tokens"
    groups: list[GroupRecord] = field(default_factory=list)

    def job_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "test_point_id": self.test_point_id,
            "problem_id": self.problem_id,
            "generator": self.generator,
            "run_seed": self.run_seed,
            "stream": self.stream,
            "groups": [g.to_dict() for g in self.groups],
        }
