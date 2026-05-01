"""Execute sandboxed LLM Plotly code with static import checks."""

from __future__ import annotations

import argparse
import ast
import builtins
import importlib.util
import json
import site
import sys
import traceback
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import CodeType
from typing import Any


@dataclass(frozen=True)
class StaticViolation:
    """Represents a single AST policy violation discovered before execution."""

    node_type: str
    name: str
    lineno: int


@lru_cache(maxsize=1)
def _load_policy() -> dict[str, Any]:
    init_path = Path(__file__).with_name("__init__.py")
    spec = importlib.util.spec_from_file_location("plotly_sandbox_policy", init_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load sandbox policy constants.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {
        "allowed_thirdparty": tuple(module.ALLOWED_THIRDPARTY_PACKAGES),
        "allowed_stdlib": frozenset(module.ALLOWED_STDLIB_MODULES),
        "disallowed_builtin_calls": frozenset(module.DISALLOWED_BUILTIN_CALLS),
        "disallowed_dunder_attrs": frozenset(module.DISALLOWED_DUNDER_ATTRS),
    }


def _top_level_name(name: str | None) -> str:
    if not name:
        return ""
    return name.split(".", 1)[0]


def collect_static_violations(tree: ast.AST) -> list[StaticViolation]:
    """Collect all allow-list violations from the parsed LLM code AST."""
    policy = _load_policy()
    allowed_roots = set(policy["allowed_thirdparty"]) | set(policy["allowed_stdlib"])
    violations: list[StaticViolation] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = _top_level_name(alias.name)
                if root not in allowed_roots:
                    violations.append(
                        StaticViolation("Import", root or alias.name, node.lineno)
                    )
        elif isinstance(node, ast.ImportFrom):
            root = _top_level_name(node.module)
            if node.level != 0 or root not in allowed_roots:
                violations.append(
                    StaticViolation("ImportFrom", root or ".", node.lineno)
                )
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in policy["disallowed_builtin_calls"]:
                violations.append(
                    StaticViolation("Call", node.func.id, node.lineno)
                )
        elif isinstance(node, ast.Attribute):
            if node.attr in policy["disallowed_dunder_attrs"]:
                violations.append(
                    StaticViolation("Attribute", node.attr, node.lineno)
                )

    return violations


def emit_static_violations(violations: list[StaticViolation]) -> None:
    """Write policy violations as JSON Lines to stderr."""
    for violation in violations:
        sys.stderr.write(
            json.dumps(
                {
                    "node_type": violation.node_type,
                    "name": violation.name,
                    "lineno": violation.lineno,
                },
                ensure_ascii=False,
            )
        )
        sys.stderr.write("\n")


def _requester_filename() -> str | None:
    runner_path = str(Path(__file__).resolve()).replace("\\", "/")
    frame = sys._getframe(2)
    while frame is not None:
        filename = frame.f_code.co_filename
        normalized = filename.replace("\\", "/")
        if normalized == runner_path:
            frame = frame.f_back
            continue
        if filename == "<llm>":
            return filename
        if filename.startswith("<frozen importlib"):
            frame = frame.f_back
            continue
        if "importlib" in normalized:
            frame = frame.f_back
            continue
        return filename
    return None


def _build_sandbox_builtins() -> dict[str, Any]:
    policy = _load_policy()
    allowed_roots = set(policy["allowed_thirdparty"]) | set(policy["allowed_stdlib"])
    original_import = builtins.__import__

    def guarded_import(
        name: str,
        globals: dict[str, Any] | None = None,
        locals: dict[str, Any] | None = None,
        fromlist: tuple[str, ...] | list[str] = (),
        level: int = 0,
    ) -> Any:
        requester = _requester_filename()
        root = _top_level_name(name)
        if requester == "<llm>" and (level != 0 or root not in allowed_roots):
            raise ImportError(f"import '{root or name}' is not allowed in sandbox")
        return original_import(name, globals, locals, fromlist, level)

    sandbox_builtins = builtins.__dict__.copy()
    sandbox_builtins["__import__"] = guarded_import
    return sandbox_builtins


def _enable_site_packages() -> None:
    """Re-enable venv site-packages inside the isolated -I -S runner process."""
    site.main()


def execute_code(
    code: str,
    *,
    enforce_static_checks: bool = True,
) -> int:
    """Execute LLM code and return the runner exit code."""
    try:
        tree = ast.parse(code, filename="<llm>")
    except SyntaxError:
        traceback.print_exc(file=sys.stderr)
        return 2

    if enforce_static_checks:
        violations = collect_static_violations(tree)
        if violations:
            emit_static_violations(violations)
            return 3

    try:
        _enable_site_packages()
        compiled = compile(tree if enforce_static_checks else code, "<llm>", "exec")
        if isinstance(compiled, CodeType):
            code_object = compiled
        else:
            code_object = compile(code, "<llm>", "exec")
        sandbox_globals = {
            "__name__": "__main__",
            "__builtins__": _build_sandbox_builtins(),
        }
        exec(code_object, sandbox_globals)
        return 0
    except Exception:
        traceback.print_exc(file=sys.stderr)
        return 2


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-path", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    code = Path(args.code_path).read_text(encoding="utf-8")
    return execute_code(code)


if __name__ == "__main__":
    raise SystemExit(main())