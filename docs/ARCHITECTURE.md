# Architecture

## Overview

DocuMint is a Python CLI tool that generates Markdown documentation from Python source code using Abstract Syntax Tree (AST) analysis. It never imports or executes the target code — everything is done via static analysis.

## Components

### CLI Layer (`cli.py`)

Built with [Typer](https://typer.tiangolo.com/), the CLI provides two main commands:

- **`generate`** — Analyze source files and write Markdown documentation to disk.
- **`analyze`** — Display a summary table of extracted information without writing files.

Rich is used for terminal formatting (tables, colors, progress).

### Core Engine (`core.py`)

Two main classes:

**`CodeAnalyzer`** — parses Python files and extracts structured metadata:

| Method | Purpose |
|---|---|
| `analyze_file(filepath)` | Parse a `.py` file and return a `ModuleInfo` |
| `analyze_directory(directory)` | Recursively analyze all `.py` files in a directory |
| `_extract_class(node)` | Extract class metadata from an AST `ClassDef` node |
| `_extract_function(node)` | Extract function metadata from an AST `FunctionDef` node |
| `_extract_import(node)` | Extract import strings from `Import`/`ImportFrom` nodes |

**`DocGenerator`** — produces Markdown from analyzed metadata:

| Method | Purpose |
|---|---|
| `generate(modules)` | Generate docs and return `{filename: content}` mapping |
| `write(modules)` | Generate and write docs to the configured output directory |
| `_render_module(mod, hl)` | Render full markdown for a single module |
| `_render_class(cls, hl)` | Render markdown for a single class |
| `_render_function(fn, hl)` | Render markdown for a single function |
| `_build_class_hierarchy(classes)` | Build a text-based class hierarchy tree |

### Configuration (`config.py`)

Uses [Pydantic](https://docs.pydantic.dev/) `BaseModel` to define configuration with validation. Supports:

- `output_dir` — where generated docs are written
- `include_private` / `include_dunder` — visibility filters
- `heading_level` — base Markdown heading level
- `project_name` — title for the index page
- `output_format` — `SINGLE` (one page) or `MULTI` (one file per module)

### Utilities (`utils.py`)

Low-level helpers that the core engine depends on:

- **AST helpers** — `parse_file`, `get_annotation_str`, `get_decorator_names`, `format_signature`
- **Markdown helpers** — `markdown_heading`, `markdown_code_block`, `markdown_table`
- **Name classification** — `is_private()`, `is_dunder()`

## Data Flow

```
Python files (.py)
       |
       v
  AST Parsing (parse_file -> ast.parse)
       |
       v
  CodeAnalyzer (classes, functions, imports, docstrings, signatures)
       |
       v
  Data Models (ModuleInfo, ClassInfo, FunctionInfo)
       |
       v
  DocGenerator (module docs, index, class hierarchy)
       |
       v
  File Export (docs/api/*.md)
```

## Design Decisions

1. **No code execution** — Only `ast.parse` is used, so broken or incomplete code can still be documented as long as it parses.
2. **Dataclass models** — Lightweight `@dataclass` types for analysis results, keeping the boundary between config and data clear.
3. **Configurable filtering** — Private and dunder members are excluded by default but can be opted in via config.
4. **Single-pass analysis** — Each file is parsed once; classes and functions are extracted in a single walk of top-level children.
5. **Output modes** — SINGLE mode combines everything into one file; MULTI mode produces one file per module plus an index.
