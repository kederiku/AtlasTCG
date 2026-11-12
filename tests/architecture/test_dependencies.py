"""Executable dependency rules for the four independently installed packages."""

import ast
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BOUNDARIES = [
    ("packages/core", {"pydantic"}, {"pydantic"}),
    (
        "packages/persistence",
        {"tcg_core", "sqlalchemy", "alembic", "psycopg"},
        {"tcg-core", "sqlalchemy", "alembic", "psycopg"},
    ),
    (
        "apps/api",
        {
            "tcg_core",
            "tcg_persistence",
            "fastapi",
            "starlette",
            "uvicorn",
            "pydantic",
        },
        {"tcg-core", "tcg-persistence", "fastapi", "uvicorn", "pydantic", "starlette"},
    ),
    (
        "apps/scraping",
        {
            "tcg_core",
            "tcg_persistence",
            "scrapy",
            "twisted",
            "PIL",
            "playwright",
            "scrapy_playwright",
            "filelock",
        },
        {
            "tcg-core",
            "tcg-persistence",
            "scrapy",
            "scrapy-playwright",
            "twisted",
            "playwright",
            "pillow",
            "filelock",
        },
    ),
]


@pytest.mark.parametrize(("project", "allowed_imports", "allowed_dependencies"), BOUNDARIES)
def test_package_respects_its_dependency_boundary(project, allowed_imports, allowed_dependencies):
    root = ROOT / project
    config = tomllib.loads((root / "pyproject.toml").read_text())
    own_package = config["project"]["name"].replace("-", "_")
    allowed = sys.stdlib_module_names | allowed_imports | {own_package}
    violations = []
    for path in (root / "src").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                names = [node.module]
            for name in names:
                if name.split(".")[0] not in allowed:
                    violations.append(f"{path.relative_to(ROOT)}:{node.lineno}: {name}")
                if project == "packages/core" and name.split(".")[0] in {
                    "subprocess",
                    "sqlite3",
                    "http",
                    "socket",
                }:
                    violations.append(
                        f"{path.relative_to(ROOT)}:{node.lineno}: external I/O {name}"
                    )
    assert not violations, "\n".join(violations)
    from packaging.requirements import Requirement

    dependencies = {Requirement(value).name for value in config["project"]["dependencies"]}
    assert dependencies <= allowed_dependencies
