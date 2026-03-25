"""Configuration management for DocuMint."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class OutputFormat(str, Enum):
    """Supported output formats."""

    SINGLE = "single"
    MULTI = "multi"


class DocuMintConfig(BaseModel):
    """DocuMint configuration for documentation generation."""

    output_dir: Path = Field(
        default=Path("docs/api"),
        description="Directory where generated documentation is written.",
    )
    include_private: bool = Field(
        default=False,
        description="Include private members (single leading underscore).",
    )
    include_dunder: bool = Field(
        default=False,
        description="Include dunder methods (__init__, __repr__, etc.).",
    )
    heading_level: int = Field(
        default=2,
        ge=1,
        le=6,
        description="Base heading level for generated markdown (1-6).",
    )
    project_name: str = Field(
        default="API Reference",
        description="Title used in the generated index page.",
    )
    output_format: OutputFormat = Field(
        default=OutputFormat.MULTI,
        description="Generate single-page or multi-page documentation.",
    )


def load_config(**overrides: object) -> DocuMintConfig:
    """Create a config instance, applying any CLI overrides on top."""
    return DocuMintConfig(**{k: v for k, v in overrides.items() if v is not None})
