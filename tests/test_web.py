import json
import socket
import ssl
import sys

import pytest

from cybercheck import web
from cybercheck.__main__ import main


URL = "https://example.test/"
SAFE_HEADERS = [
    ("Content-Type", "text/html; charset=utf-8"),
    ("Strict-Transport-Security", "max-age=31536000; includeSubDomains"),
    ("Content-Security-Policy", "default-src 'self'"),
    ("X-Content-Type-Options", "nosniff"),
    ("Set-Cookie", "session=synthetic-secret; Secure; HttpOnly; SameSite=Lax"),
]


def test_authorization_required_before_network(monkeypatch):
    monkeypatch.setattr(web, "request_page", lambda *args: pytest.fail("Unauthorized network request"))
    with pytest.raises(web.WebError, match="authorization"):
        web.analyze_web(URL)


@pytest.mark.parametrize("url", [
    "file:///etc/passwd", "ftp://example.test/", "https://user@example.test/",
    "https://example.test:8443/", "https://example.test/?token=secret", "https://example.test/#secret",
    "https://example.test/\r\nHeader:value", "https://example.test\\@localhost/", "not-a-url",
    "https://[2606:4700:4700::1111%25eth0]/",
])
def test_reject_invalid_or_sensitive_urls(url):
    with pytest.raises(web.WebError):
        web.normalize_url(url)


@pytest.mark.parametrize("addresses", [
    ["127.0.0.1"], ["10.0.0.1"], ["169.254.169.254"], ["::1"], ["fc00::1"],
    ["::ffff:127.0.0.1"], ["224.0.0.1"], ["64:ff9b::7f00:1"], ["4000::1"],
    ["8.8.8.8", "192.168.1.1"],
])
def test_public_resolution_rejects_private_and_mixed_answers(monkeypatch, addresses):
    monkeypatch.setattr(web.socket, "getaddrinfo", lambda *a, **k: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443)) for address in addresses
    ])
    with pytest.raises(web.WebError, match="blocked"):
        web.public_address("example.test", 443)


def test_https_connection_pins_ip_and_verifies_original_hostname(monkeypatch):
    calls = []
    class RawSocket:
        def close(self):
            calls.append("closed")
    raw = RawSocket()
    class Context:
        def wrap_socket(self, value, *, server_hostname):
            assert value is raw
            calls.append(server_hostname)
            return "verified-socket"
    monkeypatch.setattr(web.socket, "create_connection", lambda address, timeout: calls.append(address) or raw)
    connection = web.PinnedHTTPSConnection("example.test", "8.8.8.8")
    assert connection.tls_context.check_hostname
    assert connection.tls_context.verify_mode == ssl.CERT_REQUIRED
    connection.tls_context = Context()
    connection.connect()
    assert calls == [("8.8.8.8", 443), "example.test"]
    assert connection.sock == "verified-socket"


def test_request_does_not_read_body_or_send_credentials(monkeypatch):
    calls = []
    monkeypatch.setattr(web, "public_address", lambda *args: "8.8.8.8")
    class Response:
        status = 200
        def getheaders(self):
            return SAFE_HEADERS
        def read(self, *args):
            pytest.fail("Must not read the body")
    class Connection:
        sock = type("TLS", (), {"version": lambda self: "TLSv1.3"})()
        def request(self, method, path, *, headers):
            assert method == "GET" and path == "/"
            assert headers["Host"] == "example.test"
            assert not {"Authorization", "Cookie", "Proxy-Authorization"} & headers.keys()
        def getresponse(self):
            return Response()
        def close(self):
            calls.append("closed")
    monkeypatch.setattr(web, "PinnedHTTPSConnection", lambda host, address: Connection())
    status, _, tls = web.request_page(URL)
    assert status == 200 and tls == {"certificate_verified": True, "version": "TLSv1.3"}
    assert calls == ["closed"]


def test_secure_response_does_not_claim_site_is_secure(monkeypatch):
    monkeypatch.setattr(web, "request_page", lambda url: (200, SAFE_HEADERS, {"certificate_verified": True}))
    result = web.analyze_web(URL, authorization_confirmed=True)
    assert result["status"] == "completed"
    assert result["findings"] == []
    assert result["started_at"].endswith("+00:00") and result["finished_at"]
    assert "score" not in result
    assert "synthetic-secret" not in json.dumps(result)


def test_header_and_cookie_evidence_is_redacted(monkeypatch):
    headers = [("Content-Type", "text/html"), ("Set-Cookie", "token=synthetic-secret")]
    monkeypatch.setattr(web, "request_page", lambda url: (200, headers, {"certificate_verified": True}))
    result = web.analyze_web(URL, authorization_confirmed=True)
    assert {f["rule_id"] for f in result["findings"]} == {"WEB-HSTS", "WEB-CSP", "WEB-NOSNIFF", "WEB-COOKIE"}
    assert all(f["status"] == "potential" and f["priority"] == "review" for f in result["findings"])
    assert "synthetic-secret" not in json.dumps(result)
    assert all(f["recommendation"] for f in result["findings"])


def test_http_upgrade_is_followed_without_forwarding_cookies(monkeypatch):
    calls = []
    def request(url):
        calls.append(url)
        if url.startswith("http:"):
            return 301, [("Location", URL), ("Set-Cookie", "token=do-not-forward")], None
        return 200, SAFE_HEADERS, {"certificate_verified": True}
    monkeypatch.setattr(web, "request_page", request)
    result = web.analyze_web("http://example.test/", authorization_confirmed=True)
    assert result["status"] == "completed"
    assert calls == ["http://example.test/", URL]
    assert "WEB-HTTPS" not in {f["rule_id"] for f in result["findings"]}
    assert "do-not-forward" not in json.dumps(result)


@pytest.mark.parametrize("location", ["https://127.0.0.1/", "https://other.test/", "http://example.test/"])
def test_redirect_cannot_escape_authorized_hostname_or_downgrade(monkeypatch, location):
    calls = []
    monkeypatch.setattr(web, "request_page", lambda url: calls.append(url) or (302, [("Location", location)], None))
    result = web.analyze_web(URL, authorization_confirmed=True)
    assert calls == [URL]
    assert result["status"] == "partial"
    assert result["checks"][-1]["status"] == "failed"


def test_redirect_limit(monkeypatch):
    calls = []
    def request(url):
        calls.append(url)
        return 302, [("Location", f"/page-{len(calls)}")], None
    monkeypatch.setattr(web, "request_page", request)
    result = web.analyze_web(URL, authorization_confirmed=True)
    assert len(calls) == web.MAX_REDIRECTS + 1
    assert result["status"] == "partial"
    assert "limit" in result["checks"][-1]["error"]


@pytest.mark.parametrize("error", [ssl.SSLCertVerificationError("private certificate detail"),
                                  socket.timeout("private network detail")])
def test_request_failures_do_not_leak_raw_exceptions(monkeypatch, error):
    def request(url):
        raise error
    monkeypatch.setattr(web, "request_page", request)
    result = web.analyze_web(URL, authorization_confirmed=True)
    assert result["status"] == "failed"
    assert result["finished_at"]
    assert "private" not in json.dumps(result)
    if isinstance(error, ssl.SSLCertVerificationError):
        assert result["findings"][0]["rule_id"] == "WEB-TLS-CERT"


def test_non_html_and_unsuccessful_responses_are_partial(monkeypatch):
    monkeypatch.setattr(web, "request_page", lambda url: (200, [("Content-Type", "application/json")], None))
    result = web.analyze_web(URL, authorization_confirmed=True)
    assert result["status"] == "partial"
    assert not {f["rule_id"] for f in result["findings"]} & {"WEB-CSP", "WEB-NOSNIFF"}
    monkeypatch.setattr(web, "request_page", lambda url: (403, [], None))
    assert web.analyze_web(URL, authorization_confirmed=True)["status"] == "partial"


def test_hsts_disabled_and_report_only_csp_are_not_counted_as_protection():
    findings, _ = web.inspect_headers(URL, [("Content-Type", "text/html"),
        ("Strict-Transport-Security", "max-age=0"), ("Content-Security-Policy-Report-Only", "default-src 'none'")])
    assert {f["rule_id"] for f in findings} >= {"WEB-HSTS", "WEB-CSP"}


def test_duplicate_security_headers_and_malformed_cookies_require_review():
    headers = SAFE_HEADERS + [("Strict-Transport-Security", "max-age=0"),
                              ("X-Content-Type-Options", "invalid")]
    findings, _ = web.inspect_headers(URL, headers)
    assert {f["rule_id"] for f in findings} == {"WEB-HSTS", "WEB-NOSNIFF"}
    _, valid = web.inspect_cookies(URL, [("Set-Cookie", "invalid-cookie")])
    assert not valid


def test_dns_rebinding_to_private_address_is_blocked_on_next_request(monkeypatch):
    resolutions = []
    connections = []
    def resolve(*args, **kwargs):
        address = "8.8.8.8" if not resolutions else "127.0.0.1"
        resolutions.append(address)
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443))]
    class Connection:
        sock = type("TLS", (), {"version": lambda self: "TLSv1.3"})()
        def __init__(self, host, address):
            connections.append(address)
        def request(self, *args, **kwargs):
            pass
        def getresponse(self):
            return type("Response", (), {"status": 302, "getheaders": lambda self: [("Location", "/next")]})()
        def close(self):
            pass
    monkeypatch.setattr(web.socket, "getaddrinfo", resolve)
    monkeypatch.setattr(web, "PinnedHTTPSConnection", Connection)
    result = web.analyze_web(URL, authorization_confirmed=True)
    assert result["status"] == "partial"
    assert resolutions == ["8.8.8.8", "127.0.0.1"] and connections == ["8.8.8.8"]
    assert "blocked" in result["checks"][-1]["error"]


def test_web_cli_does_not_load_github_or_dotenv(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["cybercheck", "web", URL, "--authorization-confirmed"])
    monkeypatch.setattr("cybercheck.__main__.load_dotenv", lambda: pytest.fail("Must not load credentials"))
    monkeypatch.setattr(web, "request_page", lambda url: (200, SAFE_HEADERS, {"certificate_verified": True}))
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    assert json.loads(capsys.readouterr().out)["kind"] == "web"
