"""Keep the dependency boundaries executable as the project grows."""

import ast
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "src" / "banking"


@pytest.mark.parametrize(
    ("layer", "allowed_layers"),
    [
        ("domain", {"domain"}),
        ("utils", {"domain", "utils"}),
        ("business", {"domain", "utils", "business"}),
        ("repository", {"domain", "repository"}),
        ("api", {"api", "domain", "bootstrap"}),
    ],
)
def test_layer_import_boundaries(layer, allowed_layers):
    for path in (SOURCE / layer).rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            modules = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
            for module in modules:
                if module.startswith("banking."):
                    assert module.split(".")[1] in allowed_layers, (path, module)
                if layer in {"domain", "business", "repository", "utils"}:
                    assert module.split(".")[0] not in {"fastapi", "pydantic", "starlette"}
