"""Bounded, read-only HTTP discovery for preparing TCGdex collections."""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

from tcg_core.collections.discovery import ChoiceKind, DiscoveryUnavailable, LocalizedChoice


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class TCGdexDiscovery:
    def __init__(self, *, timeout: float = 5, max_bytes: int = 2 * 1024 * 1024):
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="tcgdex-options")

    def close(self):
        self.executor.shutdown(wait=True, cancel_futures=True)

    def choices(
        self, kind: ChoiceKind, languages: list[str], block_id: str | None
    ) -> list[LocalizedChoice]:
        futures = [
            self.executor.submit(self.localized_choices, kind, language, block_id)
            for language in languages
        ]
        result = []
        try:
            for future in as_completed(futures, timeout=30):
                result.extend(future.result())
        except (OSError, ValueError, TimeoutError) as error:
            raise DiscoveryUnavailable("TCGdex choices are temporarily unavailable") from error
        finally:
            for future in futures:
                future.cancel()
        return result

    def localized_choices(self, kind, language, block_id):
        resource = "series" if kind == "block" or block_id is not None else "sets"
        url = f"https://api.tcgdex.net/v2/{quote(language, safe='')}/{resource}"
        if block_id is not None:
            url += f"/{quote(block_id, safe='')}"
        request = Request(url, headers={"Accept": "application/json", "User-Agent": "TCG-Admin"})
        try:
            with build_opener(NoRedirect()).open(request, timeout=self.timeout) as response:
                body = response.read(self.max_bytes + 1)
        except HTTPError as error:
            if error.code == 404:
                return []
            raise
        if len(body) > self.max_bytes:
            raise ValueError("TCGdex discovery response exceeds size limit")
        data = json.loads(body)
        if block_id is not None:
            if not isinstance(data, dict) or data.get("id") != block_id:
                raise ValueError("TCGdex returned a different block")
            data = data.get("sets")
        if not isinstance(data, list):
            raise ValueError("TCGdex choices must be a list")
        choices = []
        for item in data:
            if not isinstance(item, dict):
                raise ValueError("TCGdex choice must be an object")
            choices.append(
                LocalizedChoice(id=item.get("id"), name=item.get("name"), language=language)
            )
        return choices
