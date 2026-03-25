"""Tests for the DocuMint core engine."""

from __future__ import annotations

import textwrap
from pathlib import Path

from documint.core import CodeAnalyzer, DocGenerator
from documint.config import DocuMintConfig, OutputFormat
from documint.utils import is_private, is_dunder, markdown_table


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_CODE = textwrap.dedent("""\
    \"\"\"Sample module docstring.\"\"\"

    import os
    from pathlib import Path


    class Animal:
        \"\"\"A base animal class.\"\"\"

        def __init__(self, name: str) -> None:
            self.name = name

        def speak(self) -> str:
            \"\"\"Return the sound the animal makes.\"\"\"
            return ""


    class Dog(Animal):
        \"\"\"A dog that barks.\"\"\"

        def speak(self) -> str:
            \"\"\"Return bark.\"\"\"
            return "Woof!"


    def greet(name: str, greeting: str = "Hello") -> str:
        \"\"\"Greet someone by name.\"\"\"
        return f"{greeting}, {name}!"


    async def fetch_data(url: str, *, timeout: int = 30) -> dict:
        \"\"\"Fetch data from a URL asynchronously.\"\"\"
        return {}
""")


def _write_sample(tmp_path: Path) -> Path:
    """Write sample code to a temp .py file and return the path."""
    p = tmp_path / "sample.py"
    p.write_text(SAMPLE_CODE, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Test: CodeAnalyzer
# ---------------------------------------------------------------------------

class TestCodeAnalyzer:

    def test_module_docstring_extracted(self, tmp_path: Path) -> None:
        filepath = _write_sample(tmp_path)
        module = CodeAnalyzer().analyze_file(filepath)
        assert module.docstring == "Sample module docstring."

    def test_classes_extracted(self, tmp_path: Path) -> None:
        filepath = _write_sample(tmp_path)
        cfg = DocuMintConfig(include_dunder=True)
        module = CodeAnalyzer(cfg).analyze_file(filepath)
        names = [c.name for c in module.classes]
        assert "Animal" in names
        assert "Dog" in names

    def test_functions_extracted(self, tmp_path: Path) -> None:
        filepath = _write_sample(tmp_path)
        module = CodeAnalyzer().analyze_file(filepath)
        names = [f.name for f in module.functions]
        assert "greet" in names
        assert "fetch_data" in names

    def test_async_detected(self, tmp_path: Path) -> None:
        filepath = _write_sample(tmp_path)
        module = CodeAnalyzer().analyze_file(filepath)
        fetch = next(f for f in module.functions if f.name == "fetch_data")
        assert fetch.is_async is True
        assert "async def" in fetch.signature

    def test_class_bases(self, tmp_path: Path) -> None:
        filepath = _write_sample(tmp_path)
        cfg = DocuMintConfig(include_dunder=True)
        module = CodeAnalyzer(cfg).analyze_file(filepath)
        dog = next(c for c in module.classes if c.name == "Dog")
        assert "Animal" in dog.bases

    def test_imports_extracted(self, tmp_path: Path) -> None:
        filepath = _write_sample(tmp_path)
        module = CodeAnalyzer().analyze_file(filepath)
        assert "os" in module.imports
        assert "pathlib" in module.imports

    def test_private_excluded_by_default(self, tmp_path: Path) -> None:
        code = "def public(): ...\ndef _private(): ...\n"
        p = tmp_path / "priv.py"
        p.write_text(code)
        module = CodeAnalyzer().analyze_file(p)
        names = [f.name for f in module.functions]
        assert "public" in names
        assert "_private" not in names

    def test_private_included_when_configured(self, tmp_path: Path) -> None:
        code = "def public(): ...\ndef _private(): ...\n"
        p = tmp_path / "priv.py"
        p.write_text(code)
        cfg = DocuMintConfig(include_private=True)
        module = CodeAnalyzer(cfg).analyze_file(p)
        names = [f.name for f in module.functions]
        assert "_private" in names


# ---------------------------------------------------------------------------
# Test: DocGenerator
# ---------------------------------------------------------------------------

class TestDocGenerator:

    def test_single_page_output(self, tmp_path: Path) -> None:
        filepath = _write_sample(tmp_path)
        cfg = DocuMintConfig(output_format=OutputFormat.SINGLE, include_dunder=True)
        module = CodeAnalyzer(cfg).analyze_file(filepath)
        pages = DocGenerator(cfg).generate([module])
        assert "index.md" in pages
        assert "Animal" in pages["index.md"]

    def test_multi_page_output(self, tmp_path: Path) -> None:
        filepath = _write_sample(tmp_path)
        cfg = DocuMintConfig(output_format=OutputFormat.MULTI, include_dunder=True)
        module = CodeAnalyzer(cfg).analyze_file(filepath)
        pages = DocGenerator(cfg).generate([module])
        assert "index.md" in pages
        assert "sample.md" in pages

    def test_write_creates_files(self, tmp_path: Path) -> None:
        filepath = _write_sample(tmp_path)
        out_dir = tmp_path / "output"
        cfg = DocuMintConfig(
            output_dir=out_dir,
            output_format=OutputFormat.MULTI,
            include_dunder=True,
        )
        module = CodeAnalyzer(cfg).analyze_file(filepath)
        written = DocGenerator(cfg).write([module])
        assert len(written) >= 2
        for p in written:
            assert p.exists()


# ---------------------------------------------------------------------------
# Test: Utility functions
# ---------------------------------------------------------------------------

class TestUtils:

    def test_is_private(self) -> None:
        assert is_private("_helper") is True
        assert is_private("public") is False
        assert is_private("__dunder__") is False

    def test_is_dunder(self) -> None:
        assert is_dunder("__init__") is True
        assert is_dunder("_private") is False

    def test_markdown_table(self) -> None:
        result = markdown_table(["A", "B"], [["1", "2"], ["3", "4"]])
        assert "| A | B |" in result
        assert "| 1 | 2 |" in result
        assert "---" in result
