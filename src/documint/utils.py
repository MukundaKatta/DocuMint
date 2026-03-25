"""AST helpers, markdown formatting, and signature extraction utilities."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

def parse_file(filepath: str | Path) -> ast.Module:
    """Parse a Python file and return the AST module node."""
    source = Path(filepath).read_text(encoding="utf-8")
    return ast.parse(source, filename=str(filepath))


def get_annotation_str(node: Optional[ast.expr]) -> str:
    """Convert an AST annotation node to a human-readable string."""
    if node is None:
        return ""
    return ast.unparse(node)


def get_decorator_names(node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Return a list of decorator names for a class or function node."""
    names: list[str] = []
    for dec in node.decorator_list:
        names.append(ast.unparse(dec))
    return names


def format_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Build a human-readable function signature string from an AST node.

    Includes parameter names, annotations, defaults, and return type.
    """
    parts: list[str] = []
    args = node.args

    # Compute default offsets: defaults align to the *end* of the positional args
    num_positional = len(args.args)
    num_defaults = len(args.defaults)
    default_offset = num_positional - num_defaults

    for idx, arg in enumerate(args.args):
        param = arg.arg
        if arg.annotation:
            param += f": {ast.unparse(arg.annotation)}"
        default_idx = idx - default_offset
        if default_idx >= 0:
            default_val = ast.unparse(args.defaults[default_idx])
            param += f" = {default_val}"
        parts.append(param)

    # *args
    if args.vararg:
        p = f"*{args.vararg.arg}"
        if args.vararg.annotation:
            p += f": {ast.unparse(args.vararg.annotation)}"
        parts.append(p)

    # keyword-only args
    for idx, arg in enumerate(args.kwonlyargs):
        param = arg.arg
        if arg.annotation:
            param += f": {ast.unparse(arg.annotation)}"
        if idx < len(args.kw_defaults) and args.kw_defaults[idx] is not None:
            param += f" = {ast.unparse(args.kw_defaults[idx])}"
        parts.append(param)

    # **kwargs
    if args.kwarg:
        p = f"**{args.kwarg.arg}"
        if args.kwarg.annotation:
            p += f": {ast.unparse(args.kwarg.annotation)}"
        parts.append(p)

    sig = ", ".join(parts)
    ret = ""
    if node.returns:
        ret = f" -> {ast.unparse(node.returns)}"

    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    return f"{prefix} {node.name}({sig}){ret}"


def is_private(name: str) -> bool:
    """Return True if *name* starts with an underscore but is not a dunder."""
    return name.startswith("_") and not name.startswith("__")


def is_dunder(name: str) -> bool:
    """Return True if *name* is a dunder (double-underscore) name."""
    return name.startswith("__") and name.endswith("__") and len(name) > 4


# ---------------------------------------------------------------------------
# Markdown formatting helpers
# ---------------------------------------------------------------------------

def markdown_heading(text: str, level: int = 2) -> str:
    """Return a markdown heading string."""
    return f"{'#' * level} {text}"


def markdown_code_block(code: str, lang: str = "python") -> str:
    """Wrap *code* in a fenced markdown code block."""
    return f"```{lang}\n{code}\n```"


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    """Build a markdown table from headers and row data."""
    if not headers:
        return ""
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def indent_block(text: str, spaces: int = 4) -> str:
    """Indent every line of *text* by *spaces* spaces."""
    prefix = " " * spaces
    return "\n".join(prefix + line for line in text.splitlines())
