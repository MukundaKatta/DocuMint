"""CLI entry point: python -m documint."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from documint.config import DocuMintConfig, OutputFormat
from documint.core import CodeAnalyzer, DocGenerator

app = typer.Typer(
    name="documint",
    help="Auto-generate beautiful documentation from Python codebases.",
    add_completion=False,
)
console = Console()


@app.command()
def generate(
    source: str = typer.Argument(..., help="Path to a Python file or directory."),
    output: str = typer.Option("docs/api", "--output", "-o", help="Output directory."),
    format: str = typer.Option("multi", "--format", "-f", help="Output format: single or multi."),
    include_private: bool = typer.Option(False, "--private", help="Include private members."),
    include_dunder: bool = typer.Option(False, "--dunder", help="Include dunder methods."),
    project_name: str = typer.Option("API Reference", "--name", "-n", help="Project name."),
) -> None:
    """Generate Markdown documentation from Python source files."""
    fmt = OutputFormat.SINGLE if format == "single" else OutputFormat.MULTI
    config = DocuMintConfig(
        output_dir=Path(output),
        include_private=include_private,
        include_dunder=include_dunder,
        project_name=project_name,
        output_format=fmt,
    )

    analyzer = CodeAnalyzer(config)
    source_path = Path(source)

    if source_path.is_file():
        modules = [analyzer.analyze_file(source_path)]
    elif source_path.is_dir():
        modules = analyzer.analyze_directory(source_path)
    else:
        console.print(f"[red]Error:[/red] {source} is not a valid file or directory.")
        raise typer.Exit(code=1)

    if not modules:
        console.print("[yellow]No Python modules found.[/yellow]")
        raise typer.Exit(code=0)

    generator = DocGenerator(config)
    written = generator.write(modules)

    console.print(f"\n[green]Generated {len(written)} documentation file(s):[/green]")
    for p in written:
        console.print(f"  {p}")


@app.command()
def analyze(
    source: str = typer.Argument(..., help="Path to a Python file or directory."),
    include_private: bool = typer.Option(False, "--private", help="Include private members."),
    include_dunder: bool = typer.Option(False, "--dunder", help="Include dunder methods."),
) -> None:
    """Analyze Python source and display a summary table (no file output)."""
    config = DocuMintConfig(
        include_private=include_private,
        include_dunder=include_dunder,
    )
    analyzer = CodeAnalyzer(config)
    source_path = Path(source)

    if source_path.is_file():
        modules = [analyzer.analyze_file(source_path)]
    elif source_path.is_dir():
        modules = analyzer.analyze_directory(source_path)
    else:
        console.print(f"[red]Error:[/red] {source} is not a valid file or directory.")
        raise typer.Exit(code=1)

    table = Table(title="DocuMint Analysis Summary")
    table.add_column("Module", style="cyan")
    table.add_column("Classes", justify="right")
    table.add_column("Functions", justify="right")
    table.add_column("Imports", justify="right")

    for mod in modules:
        table.add_row(
            mod.name,
            str(len(mod.classes)),
            str(len(mod.functions)),
            str(len(mod.imports)),
        )

    console.print(table)


def main() -> None:
    """Entry point for ``python -m documint``."""
    app()


if __name__ == "__main__":
    main()
