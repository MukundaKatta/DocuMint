"""CLI interface for DocuMint — powered by Typer."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from documint import __version__
from documint.config import DocuMintConfig, OutputFormat, load_config
from documint.core import CodeAnalyzer, DocGenerator

app = typer.Typer(
    name="documint",
    help="Auto-generate markdown documentation from Python codebases.",
    add_completion=False,
)
console = Console()


def _collect_py_files(path: Path) -> list[Path]:
    """Return a sorted list of .py files from *path* (file or directory)."""
    if path.is_file():
        return [path]
    return sorted(path.rglob("*.py"))


@app.command()
def generate(
    source: Path = typer.Argument(..., help="Python file or directory to document."),
    output: Path = typer.Option(
        Path("docs/api"), "-o", "--output", help="Output directory for Markdown files."
    ),
    include_private: bool = typer.Option(False, "--private", help="Include private members."),
    include_dunder: bool = typer.Option(False, "--dunder", help="Include dunder methods."),
    project_name: str = typer.Option("API Reference", "--project", help="Project title for index."),
    single: bool = typer.Option(False, "--single", help="Generate single-page documentation."),
) -> None:
    """Generate Markdown documentation for Python source files."""
    output_format = OutputFormat.SINGLE if single else OutputFormat.MULTI
    config = load_config(
        output_dir=output,
        include_private=include_private,
        include_dunder=include_dunder,
        project_name=project_name,
        output_format=output_format,
    )
    analyzer = CodeAnalyzer(config)
    generator = DocGenerator(config)

    files = _collect_py_files(source)

    if not files:
        console.print("[red]No Python files found.[/red]")
        raise typer.Exit(code=1)

    console.print(f"[bold cyan]DocuMint[/bold cyan] v{__version__}")
    console.print(f"Found [bold]{len(files)}[/bold] Python file(s)\n")

    modules = []
    for py_file in files:
        console.print(f"  Analyzing [green]{py_file}[/green]")
        modules.append(analyzer.analyze_file(py_file))

    written = generator.write(modules)
    console.print(
        f"\n[bold green]Wrote {len(written)} file(s)[/bold green] to {config.output_dir}/"
    )


@app.command()
def analyze(
    source: Path = typer.Argument(..., help="Python file or directory to analyze."),
    include_private: bool = typer.Option(False, "--private", help="Include private members."),
    include_dunder: bool = typer.Option(False, "--dunder", help="Include dunder methods."),
) -> None:
    """Analyze Python source and display a summary (no files written)."""
    config = load_config(include_private=include_private, include_dunder=include_dunder)
    analyzer = CodeAnalyzer(config)
    files = _collect_py_files(source)

    if not files:
        console.print("[red]No Python files found.[/red]")
        raise typer.Exit(code=1)

    console.print(f"[bold cyan]DocuMint[/bold cyan] v{__version__}  — analysis mode\n")

    table = Table(title="Module Summary")
    table.add_column("File", style="green")
    table.add_column("Classes", justify="right")
    table.add_column("Functions", justify="right")
    table.add_column("Has Docstring", justify="center")

    for py_file in files:
        info = analyzer.analyze_file(py_file)
        table.add_row(
            str(py_file),
            str(len(info.classes)),
            str(len(info.functions)),
            "yes" if info.docstring else "no",
        )

    console.print(table)


@app.command()
def version() -> None:
    """Show the DocuMint version."""
    console.print(f"DocuMint v{__version__}")


if __name__ == "__main__":
    app()
