"""Verify an isolated Docker stack, without external card APIs or existing user data.

Requires previously built tcg-api, tcg-scraping and tcg-migrate images and Docker Compose >= 2.24.4.
The temporary project's volume is removed in finally; the real tcg project is untouched.
"""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def main():
    project = f"tcg-smoke-{uuid4().hex[:10]}"
    with tempfile.TemporaryDirectory(prefix="tcg-docker-smoke-") as directory:
        temporary = Path(directory)
        data = temporary / "data"
        (data / "images").mkdir(parents=True)
        (data / "jobs" / "admin").mkdir(parents=True)
        variables = {
            "POSTGRES_USER": "tcg",
            "POSTGRES_DB": "tcg",
            "POSTGRES_PASSWORD": uuid4().hex,
            "POSTGRES_PORT": "5432",
            "TCG_DATA_DIR": str(data),
            "TCG_UID": str(os.getuid()),
            "TCG_GID": str(os.getgid()),
        }
        env_file = temporary / ".env"
        env_file.write_text("\n".join(f"{key}={value}" for key, value in variables.items()))
        override = temporary / "compose.yaml"
        override.write_text(
            'services:\n  postgres:\n    ports: !override ["127.0.0.1::5432"]\n'
            '  api:\n    ports: !override ["127.0.0.1::8000"]\n'
        )
        compose = [
            "docker",
            "compose",
            "--env-file",
            str(env_file),
            "-p",
            project,
            "-f",
            str(ROOT / "compose.yaml"),
            "-f",
            str(override),
        ]

        def run(*arguments, input=None):
            result = subprocess.run(
                compose + list(arguments),
                cwd=ROOT,
                env=os.environ | variables,
                input=input,
                text=True,
                capture_output=True,
            )
            if result.returncode:
                raise RuntimeError(result.stdout + result.stderr)
            return result.stdout.strip()

        try:
            print(f"Starting isolated project {project}…", flush=True)
            run("up", "--no-build", "-d", "--wait", "--wait-timeout", "120")
            origin = "http://" + run("port", "api", "8000")
            for service, forbidden in {
                "api": ["scrapy", "twisted", "playwright", "PIL", "filelock", "tcg_scraping"],
                "worker": ["fastapi", "uvicorn", "tcg_api"],
            }.items():
                run(
                    "exec",
                    "-T",
                    service,
                    "python",
                    "-c",
                    "from importlib.util import find_spec; "
                    f"assert all(find_spec(name) is None for name in {forbidden!r})",
                )
            run(
                "run",
                "--rm",
                "--no-deps",
                "migrate",
                "python",
                "-c",
                "from importlib.util import find_spec; "
                "assert all(find_spec(name) is None for name in "
                "['fastapi', 'uvicorn', 'scrapy', 'playwright', 'tcg_api', 'tcg_scraping'])",
            )
            print("Runtime dependency isolation verified.", flush=True)

            def request(path, body=None):
                payload = json.dumps(body).encode() if body is not None else None
                with urlopen(
                    Request(
                        origin + path,
                        data=payload,
                        headers={"Content-Type": "application/json", "X-TCG-Admin": "1"},
                    ),
                    timeout=5,
                ) as response:
                    return response.read()

            fixture = (ROOT / "tests/fixtures/tcgdex_charizard.json").read_text()
            seed = f"""
import json
import os
from pathlib import Path
from PIL import Image
from tcg_scraping.sources.tcgdex.normalize import normalize_card, normalize_set
from tcg_persistence.catalog import Repository
from tcg_persistence.configuration import database_url
raw = json.loads({fixture!r})
raw['pricing'] = {{'usd': 50}}
card = normalize_card(raw, language='fr', source_url='https://api.tcgdex.net/v2/fr/cards/base1-4')
path = Path(os.environ['TCG_IMAGES_DIR']) / 'pokemon/fr/base1/4-base1.webp'
path.parent.mkdir(parents=True, exist_ok=True)
Image.new('RGB', (8, 8), 'orange').save(path, 'WEBP')
repository = Repository(database_url())
images = [{{'path': 'pokemon/fr/base1/4-base1.webp'}}]
repository.save(card.model_dump(mode='json') | {{'images': images}})
repository.save_set(normalize_set({{
    'id':'base1','name':'Set de Base','serie':{{'id':'base','name':'Base'}}
}},language='fr'))
repository.close()
"""
            run("exec", "-T", "worker", "python", "-", input=seed)
            assert json.loads(request("/api/health")) == {"status": "ok"}
            assert json.loads(request("/api/overview"))["total"] == 1
            detail = json.loads(
                request(
                    "/api/cards/detail?game=pokemon&source=tcgdex&source_id=base1-4&language=fr"
                )
            )
            assert detail["set_name"] == "Set de Base"
            assert detail["set_info"]["block"] == {"id": "base", "name": "Base"}
            assert json.loads(request("/api/blocks"))[0]["source_id"] == "base"
            assert (
                json.loads(request("/api/cards?block_id=base&game=pokemon&source=tcgdex"))["total"]
                == 1
            )
            assert json.loads(request("/api/cards?block_id=missing"))["total"] == 0
            assert "pricing" not in detail["raw"]
            assert detail["faces"][0]["statistics"]["hp"] == 120
            assert b'<div id="root">' in request("/cards/pokemon/tcgdex/fr/base1-4")
            image = request(detail["image_urls"][0])
            assert image[:4] == b"RIFF" and image[8:12] == b"WEBP"
            # Exercise grouped SQL and translated search on PostgreSQL, using
            # only a synthetic localized version of the existing fixture.
            run(
                "exec",
                "-T",
                "worker",
                "python",
                "-",
                input=seed.replace("language='fr'", "language='es'")
                .replace("'Set de Base'", "'Base ES'")
                .replace("'name':'Base'", "'name':'Serie ES'")
                .replace("pokemon/fr/", "pokemon/es/"),
            )
            grouped = json.loads(
                request("/api/card-groups?q=Base%20ES&language=fr&display_language=es&page_size=1")
            )
            assert grouped["total"] == 1
            assert grouped["items"][0]["language"] == "fr"
            assert {v["language"] for v in grouped["items"][0]["versions"]} == {"fr", "es"}
            assert json.loads(request("/api/card-groups?page=2&page_size=1"))["items"] == []
            assert json.loads(request("/api/card-groups?q=Serie%20ES"))["total"] == 1
            assert json.loads(request("/api/cards"))["total"] == 2
            print("Grouped pagination and translated search verified on PostgreSQL.", flush=True)
            for _ in range(2):
                job = json.loads(
                    request(
                        "/api/jobs",
                        {
                            "spider": "tcgdex",
                            "languages": ["fr"],
                            "card_ids": ["base1-4"],
                            "limit": 1,
                            "force": False,
                        },
                    )
                )
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    state = json.loads(request(f"/api/jobs/{job['id']}"))
                    if state["status"] not in {"queued", "running"}:
                        break
                    time.sleep(0.25)
                assert state["status"] == "succeeded", request(
                    f"/api/jobs/{job['id']}/logs"
                ).decode()
                assert state["stats"]["cards/skipped_existing"] == 1
                assert request(f"/api/jobs/{job['id']}/logs")
            print("API, deep link, WebP, worker and duplicate filtering verified.", flush=True)
            run(
                "exec",
                "-T",
                "worker",
                "python",
                "-",
                input="""
import asyncio
from playwright.async_api import async_playwright
async def check():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        print('Chromium starts:', browser.version)
        await browser.close()
asyncio.run(check())
""",
            )
            run("restart", "api", "worker")
            # Docker may reassign an ephemeral published port on restart.
            origin = "http://" + run("port", "api", "8000")
            deadline = time.monotonic() + 30
            while True:
                try:
                    assert json.loads(request("/api/health"))["status"] == "ok"
                    break
                except (URLError, ConnectionError) as _error:
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(0.25)
            assert json.loads(request("/api/overview"))["total"] == 2
            assert len(json.loads(request("/api/jobs"))) == 2
            assert request(detail["image_urls"][0]) == image
            print("Chromium and persistence after restart verified.", flush=True)
        except Exception:
            print(run("logs", "--tail", "50"), flush=True)
            raise
        finally:
            run("down", "--volumes", "--remove-orphans")
            print(f"Removed isolated project {project}.", flush=True)


if __name__ == "__main__":
    main()
