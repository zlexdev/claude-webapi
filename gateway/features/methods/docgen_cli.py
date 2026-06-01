"""CLI: regenerate gateway/METHODS.md from the live method registry.

    python -m gateway.features.methods.docgen_cli
"""

from __future__ import annotations

from pathlib import Path

from gateway.features.methods.registry import MethodRegistry
from gateway.features.methods.services.docgen_service import MethodDocGenerator
from gateway.shared.logging import configure_logging, get_logger


def main() -> None:
    configure_logging()
    markdown = MethodDocGenerator(MethodRegistry()).as_markdown()
    out_path = Path(__file__).resolve().parents[2] / "METHODS.md"
    out_path.write_text(markdown, encoding="utf-8")
    get_logger("methods.docgen").info("wrote %s", out_path)


if __name__ == "__main__":
    main()
