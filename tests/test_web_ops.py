import httpx
import pytest

from orchestrator.servers.web import ops

_HTML = """
<html>
  <head><style>body { color: red; }</style><script>alert(1)</script></head>
  <body>
    <h1>Title</h1>
    <p>Hello   world.</p>
    <p>Second paragraph.</p>
  </body>
</html>
"""


def test_distill_html_strips_tags_scripts_and_styles():
    text = ops.distill_html(_HTML)

    assert "Title" in text
    assert "Hello   world." in text
    assert "Second paragraph." in text
    assert "alert(1)" not in text
    assert "color: red" not in text


def test_distill_html_truncates_to_max_length():
    huge = "<p>" + ("x" * 50_000) + "</p>"

    text = ops.distill_html(huge)

    assert len(text) == ops._MAX_CONTENT_LENGTH


def _client_returning(html: str, status_code: int = 200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text=html)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_returns_distilled_content():
    client = _client_returning(_HTML)

    text = ops.fetch("https://example.com/page", client=client)

    assert "Title" in text
    assert "<h1>" not in text


def test_fetch_raises_on_http_error():
    client = _client_returning("not found", status_code=404)

    with pytest.raises(ops.FetchError):
        ops.fetch("https://example.com/missing", client=client)


def test_fetch_rejects_url_outside_allowlist():
    client = _client_returning(_HTML)

    with pytest.raises(ops.FetchError):
        ops.fetch("https://not-example.org/page", allowlist=["example.com"], client=client)


def test_fetch_allows_url_matching_allowlist_subdomain():
    client = _client_returning(_HTML)

    text = ops.fetch("https://docs.example.com/page", allowlist=["example.com"], client=client)

    assert "Title" in text
