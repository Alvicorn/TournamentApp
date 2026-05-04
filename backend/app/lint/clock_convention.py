"""Static check enforcing the Postgres-clock convention.

Rules (see ``docs/engineering/correctness.md#timer-authority``):

1. No ``datetime.utcnow`` or ``datetime.now`` calls in ``app/`` (except this
   file's own helper text and ``app/models/base.py`` where the soft-delete
   fallback documents the exception).
2. Every ``DateTime`` mapped column must carry ``server_default=func.now()``
   (or be explicitly nullable, e.g. ``deleted_at``).

Invoked via ``python -m app.lint.clock_convention`` and from CI. Returns
non-zero exit code on violation.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "app"

ALLOWED_DATETIME_FILES = {
    Path("models/base.py"),  # soft-delete Python fallback documents the exception
    Path("auth/judge.py"),  # JWT iat/exp use Python time intentionally (not a DB clock)
    Path("lint/clock_convention.py"),
}


def _is_datetime_now_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr in {"utcnow", "now"}:
        value = func.value
        if isinstance(value, ast.Name) and value.id == "datetime":
            return True
        if isinstance(value, ast.Attribute) and value.attr == "datetime":
            return True
    return False


def _check_datetime_calls(path: Path) -> list[str]:
    rel = path.relative_to(ROOT)
    if rel in ALLOWED_DATETIME_FILES:
        return []
    tree = ast.parse(path.read_text(encoding="utf-8"))
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _is_datetime_now_call(node):
            violations.append(
                f"{rel}:{node.lineno} uses Python clock; use Postgres func.now() instead"
            )
    return violations


def _check_datetime_columns(path: Path) -> list[str]:
    """For ``mapped_column(DateTime(timezone=True), ...)`` calls, require either
    ``server_default=`` or ``nullable=True``.
    """
    rel = path.relative_to(ROOT)
    tree = ast.parse(path.read_text(encoding="utf-8"))
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_mapped_column = isinstance(func, ast.Name) and func.id == "mapped_column"
        if not is_mapped_column:
            continue
        # Look for DateTime(...) as first positional arg
        first = node.args[0] if node.args else None
        is_datetime = (
            isinstance(first, ast.Call)
            and isinstance(first.func, ast.Name)
            and first.func.id == "DateTime"
        )
        if not is_datetime:
            continue
        kwargs = {kw.arg: kw.value for kw in node.keywords}
        if "server_default" in kwargs:
            continue
        nullable_node = kwargs.get("nullable")
        if isinstance(nullable_node, ast.Constant) and nullable_node.value is True:
            continue
        violations.append(f"{rel}:{node.lineno} DateTime column missing server_default=func.now()")
    return violations


def run() -> int:
    violations: list[str] = []
    for path in ROOT.rglob("*.py"):
        violations.extend(_check_datetime_calls(path))
        violations.extend(_check_datetime_columns(path))
    if violations:
        print("Clock-convention violations:")
        for v in violations:
            print(f"  {v}")
        return 1
    print("Clock convention OK")
    return 0


if __name__ == "__main__":
    sys.exit(run())
