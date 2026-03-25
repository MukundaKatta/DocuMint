"""Main DocuMint engine -- CodeAnalyzer and DocGenerator."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from documint.config import DocuMintConfig, OutputFormat
from documint.utils import (
    format_signature,
    get_annotation_str,
    get_decorator_names,
    is_dunder,
    is_private,
    markdown_code_block,
    markdown_heading,
    markdown_table,
    parse_file,
)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class FunctionInfo:
    """Extracted metadata for a single function or method."""

    name: str
    signature: str
    docstring: Optional[str] = None
    decorators: list[str] = field(default_factory=list)
    return_type: str = ""
    is_async: bool = False
    lineno: int = 0


@dataclass
class ClassInfo:
    """Extracted metadata for a class definition."""

    name: str
    docstring: Optional[str] = None
    bases: list[str] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)
    methods: list[FunctionInfo] = field(default_factory=list)
    lineno: int = 0


@dataclass
class ModuleInfo:
    """Extracted metadata for an entire Python module."""

    name: str
    filepath: str
    docstring: Optional[str] = None
    classes: list[ClassInfo] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# CodeAnalyzer
# ---------------------------------------------------------------------------

class CodeAnalyzer:
    """Parse Python source files using the AST and extract structured metadata.

    Supports extraction of classes, functions, decorators, docstrings,
    type annotations, and import statements.
    """

    def __init__(self, config: Optional[DocuMintConfig] = None) -> None:
        self.config = config or DocuMintConfig()

    def analyze_file(self, filepath: str | Path) -> ModuleInfo:
        """Analyze a single Python file and return a ModuleInfo."""
        filepath = Path(filepath)
        tree = parse_file(filepath)
        module_name = filepath.stem

        module = ModuleInfo(
            name=module_name,
            filepath=str(filepath),
            docstring=ast.get_docstring(tree),
        )

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                cls = self._extract_class(node)
                if cls:
                    module.classes.append(cls)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fn = self._extract_function(node)
                if fn:
                    module.functions.append(fn)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                module.imports.extend(self._extract_import(node))

        return module

    def analyze_directory(self, directory: str | Path) -> list[ModuleInfo]:
        """Recursively analyze all .py files in a directory."""
        directory = Path(directory)
        modules: list[ModuleInfo] = []
        for py_file in sorted(directory.rglob("*.py")):
            if py_file.name.startswith("__"):
                continue
            try:
                modules.append(self.analyze_file(py_file))
            except SyntaxError:
                continue
        return modules

    def _should_include(self, name: str) -> bool:
        """Decide whether a name should be included based on config."""
        if is_dunder(name):
            return self.config.include_dunder
        if is_private(name):
            return self.config.include_private
        return True

    def _extract_class(self, node: ast.ClassDef) -> Optional[ClassInfo]:
        """Extract class metadata from an AST ClassDef node."""
        if not self._should_include(node.name):
            return None
        bases = [ast.unparse(b) for b in node.bases]
        methods: list[FunctionInfo] = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fn = self._extract_function(item)
                if fn:
                    methods.append(fn)
        return ClassInfo(
            name=node.name,
            docstring=ast.get_docstring(node),
            bases=bases,
            decorators=get_decorator_names(node),
            methods=methods,
            lineno=node.lineno,
        )

    def _extract_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> Optional[FunctionInfo]:
        """Extract function metadata from an AST FunctionDef node."""
        if not self._should_include(node.name):
            return None
        return FunctionInfo(
            name=node.name,
            signature=format_signature(node),
            docstring=ast.get_docstring(node),
            decorators=get_decorator_names(node),
            return_type=get_annotation_str(node.returns),
            is_async=isinstance(node, ast.AsyncFunctionDef),
            lineno=node.lineno,
        )

    @staticmethod
    def _extract_import(node: ast.Import | ast.ImportFrom) -> list[str]:
        """Extract import strings from Import / ImportFrom nodes."""
        results: list[str] = []
        if isinstance(node, ast.Import):
            for alias in node.names:
                results.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            results.append(node.module)
        return results


# ---------------------------------------------------------------------------
# DocGenerator
# ---------------------------------------------------------------------------

class DocGenerator:
    """Generate Markdown documentation from analyzed module metadata."""

    def __init__(self, config: Optional[DocuMintConfig] = None) -> None:
        self.config = config or DocuMintConfig()

    def generate(self, modules: list[ModuleInfo]) -> dict[str, str]:
        """Generate documentation and return a mapping of filename to content.

        In SINGLE mode a single index.md is produced.
        In MULTI mode each module gets its own file plus an index.md.
        """
        if self.config.output_format == OutputFormat.SINGLE:
            return self._generate_single(modules)
        return self._generate_multi(modules)

    def write(self, modules: list[ModuleInfo]) -> list[Path]:
        """Generate docs and write them to the configured output directory."""
        pages = self.generate(modules)
        out_dir = self.config.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []
        for filename, content in pages.items():
            path = out_dir / filename
            path.write_text(content, encoding="utf-8")
            written.append(path)
        return written

    def _generate_single(self, modules: list[ModuleInfo]) -> dict[str, str]:
        """Produce a single index.md containing all modules."""
        hl = self.config.heading_level
        parts: list[str] = [markdown_heading(self.config.project_name, max(1, hl - 1)), ""]

        for mod in modules:
            parts.append(self._render_module(mod, hl))
            parts.append("")

        return {"index.md": "\n".join(parts)}

    def _generate_multi(self, modules: list[ModuleInfo]) -> dict[str, str]:
        """Produce one file per module plus an index."""
        hl = self.config.heading_level
        pages: dict[str, str] = {}

        index_rows: list[list[str]] = []
        for mod in modules:
            fname = f"{mod.name}.md"
            pages[fname] = self._render_module(mod, hl)
            desc = (mod.docstring or "").split("\n")[0][:80]
            index_rows.append([f"[{mod.name}]({fname})", desc])

        index_parts = [
            markdown_heading(self.config.project_name, max(1, hl - 1)),
            "",
            markdown_table(["Module", "Description"], index_rows),
            "",
        ]
        pages["index.md"] = "\n".join(index_parts)
        return pages

    def _render_module(self, mod: ModuleInfo, hl: int) -> str:
        """Render full markdown for a single module."""
        parts: list[str] = [markdown_heading(f"Module `{mod.name}`", hl)]
        if mod.docstring:
            parts.append(f"\n{mod.docstring}\n")

        # Dependency graph (imports)
        if mod.imports:
            parts.append(markdown_heading("Dependencies", hl + 1))
            for imp in mod.imports:
                parts.append(f"- `{imp}`")
            parts.append("")

        # Functions table and details
        if mod.functions:
            parts.append(markdown_heading("Functions", hl + 1))
            rows = [
                [
                    f"`{fn.name}`",
                    fn.return_type or "-",
                    (fn.docstring or "-").split("\n")[0],
                ]
                for fn in mod.functions
            ]
            parts.append(markdown_table(["Function", "Returns", "Description"], rows))
            parts.append("")
            for fn in mod.functions:
                parts.append(self._render_function(fn, hl + 2))

        # Classes
        if mod.classes:
            parts.append(markdown_heading("Classes", hl + 1))
            for cls in mod.classes:
                parts.append(self._render_class(cls, hl + 2))

        # Class hierarchy diagram
        hierarchy = self._build_class_hierarchy(mod.classes)
        if hierarchy:
            parts.append(markdown_heading("Class Hierarchy", hl + 1))
            parts.append(markdown_code_block(hierarchy, ""))
            parts.append("")

        return "\n".join(parts)

    def _render_function(self, fn: FunctionInfo, hl: int) -> str:
        """Render markdown for a single function."""
        parts: list[str] = [markdown_heading(f"`{fn.name}`", hl)]
        if fn.decorators:
            parts.append(
                "**Decorators:** " + ", ".join(f"`@{d}`" for d in fn.decorators)
            )
        parts.append(markdown_code_block(fn.signature))
        if fn.docstring:
            parts.append(fn.docstring)
        parts.append("")
        return "\n".join(parts)

    def _render_class(self, cls: ClassInfo, hl: int) -> str:
        """Render markdown for a single class."""
        title = f"`{cls.name}`"
        if cls.bases:
            title += "(" + ", ".join(f"`{b}`" for b in cls.bases) + ")"
        parts: list[str] = [markdown_heading(title, hl)]
        if cls.decorators:
            parts.append(
                "**Decorators:** " + ", ".join(f"`@{d}`" for d in cls.decorators)
            )
        if cls.docstring:
            parts.append(f"\n{cls.docstring}\n")
        if cls.methods:
            rows = [
                [
                    f"`{m.name}`",
                    m.return_type or "-",
                    (m.docstring or "-").split("\n")[0],
                ]
                for m in cls.methods
            ]
            parts.append(markdown_heading("Methods", hl + 1))
            parts.append(markdown_table(["Method", "Returns", "Description"], rows))
            parts.append("")
            for m in cls.methods:
                parts.append(self._render_function(m, hl + 2))
        return "\n".join(parts)

    @staticmethod
    def _build_class_hierarchy(classes: list[ClassInfo]) -> str:
        """Build a text-based class hierarchy tree."""
        if not classes:
            return ""
        lines: list[str] = []
        for cls in classes:
            if cls.bases:
                for base in cls.bases:
                    lines.append(f"{base}")
                    lines.append(f"  └── {cls.name}")
            else:
                lines.append(cls.name)
            for method in cls.methods:
                prefix = "async " if method.is_async else ""
                lines.append(f"      ├── {prefix}{method.name}()")
        return "\n".join(lines)
