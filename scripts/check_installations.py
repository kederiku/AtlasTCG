"""Run each package's tests in a non-editable, independently installed environment.

Only test runners are added to production dependencies. The shared development
environment and the user's database/files are never used or changed.
"""

import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    (
        "tcg-core",
        "packages/core/tests",
        "test",
        ["sqlalchemy", "fastapi", "scrapy", "tcg_api", "tcg_scraping", "tcg_persistence"],
    ),
    (
        "tcg-persistence",
        "packages/persistence/tests",
        "test",
        ["fastapi", "uvicorn", "scrapy", "playwright", "tcg_api", "tcg_scraping"],
    ),
    (
        "tcg-api",
        "apps/api/tests",
        "api-test",
        ["scrapy", "twisted", "playwright", "PIL", "filelock", "tcg_scraping"],
    ),
    ("tcg-scraping", "apps/scraping/tests", "test", ["fastapi", "uvicorn", "tcg_api"]),
]


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="tcg-installations-") as directory:
        base = Path(directory)
        # No personal connection settings reach the test subprocesses.
        environment = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("TCG_", "POSTGRES_"))
            and key not in {"PYTHONPATH", "VIRTUAL_ENV", "SCRAPY_SETTINGS_MODULE"}
        }
        for package, tests, group, forbidden in CASES:
            target = base / package
            env = environment | {"UV_PROJECT_ENVIRONMENT": str(target)}
            subprocess.run(
                [
                    "uv",
                    "sync",
                    "--locked",
                    "--package",
                    package,
                    "--no-dev",
                    "--group",
                    group,
                    "--no-editable",
                    # Local wheel caches may only watch pyproject.toml. Always
                    # rebuild workspace packages so these checks exercise the
                    # current sources, including their local dependencies.
                    *[
                        argument
                        for local_package, *_ in CASES
                        for argument in ("--reinstall-package", local_package)
                    ],
                ],
                cwd=ROOT,
                env=env,
                check=True,
            )
            python = str(target / "bin" / "python")
            subprocess.run(
                [
                    python,
                    "-c",
                    (
                        "from importlib.util import find_spec; from pathlib import Path; "
                        f"assert all(find_spec(name) is None for name in {forbidden!r}); "
                        f"location = Path(find_spec({package.replace('-', '_')!r}).origin); "
                        f"assert location.is_relative_to({str(target)!r})"
                    ),
                ],
                cwd=base,
                env=env,
                check=True,
            )
            subprocess.run([python, "-m", "pytest", "-q", tests], cwd=ROOT, env=env, check=True)
            print(f"Verified isolated installation: {package}", flush=True)


if __name__ == "__main__":
    main()
