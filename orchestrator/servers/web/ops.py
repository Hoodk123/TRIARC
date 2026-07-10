"""Web fetch + distilled content (docs/architecture.md #5, docs/features.md #6).

Strips an HTML page down to its visible text so a lookup doesn't flood a small
model's context with markup. Access is allowlist-scoped when an allowlist is
configured, per docs/security.md Face 2 ("web access is allowlist/session-scoped").
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

import httpx

_SKIP_TAGS = {"script", "style", "noscript", "head"}
_MAX_CONTENT_LENGTH = 20_000
_DEFAULT_TIMEOUT_SECONDS = 10.0


class FetchError(RuntimeError):
    pass


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            stripped = data.strip()
            if stripped:
                self._chunks.append(stripped)

    def text(self) -> str:
        return "\n".join(self._chunks)


def distill_html(html: str) -> str:
    """Strip an HTML document down to its visible text."""
    extractor = _TextExtractor()
    extractor.feed(html)
    text = re.sub(r"\n{3,}", "\n\n", extractor.text())
    return text[:_MAX_CONTENT_LENGTH]


def _is_allowed(url: str, allowlist: list[str] | None) -> bool:
    if not allowlist:
        return True
    host = httpx.URL(url).host
    return any(host == domain or host.endswith(f".{domain}") for domain in allowlist)


def fetch(
    url: str,
    *,
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
    allowlist: list[str] | None = None,
    client: httpx.Client | None = None,
) -> str:
    """Fetch URL and return its distilled text content."""
    if not _is_allowed(url, allowlist):
        raise FetchError(f"{url!r} is not in the configured allowlist {allowlist!r}")

    owns_client = client is None
    client = client or httpx.Client(timeout=timeout_seconds, follow_redirects=True)
    try:
        response = client.get(url)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise FetchError(f"failed to fetch {url!r}: {exc}") from exc
    finally:
        if owns_client:
            client.close()

    return distill_html(response.text)
