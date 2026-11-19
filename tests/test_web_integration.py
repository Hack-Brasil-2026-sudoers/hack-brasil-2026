"""Real HTTP/TLS integration against a temporary loopback-only test website."""
import json
import socket
import ssl
import threading
from contextlib import ExitStack, contextmanager
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from fastapi.testclient import TestClient

from cybercheck import web
from cybercheck.api import create_app
from cybercheck.config import Settings
from cybercheck.worker import process


HOSTNAME = "local-site.test"
COOKIE_VALUE = "fixture-only-cookie"
BODY = b"<html><body>INTEGRATION_TEST_BODY_NOT_FOR_REPORTS</body></html>"


def create_test_certificate(directory):
    """Generate a temporary CA and a matching server certificate; never commit keys."""
    start = datetime.now(timezone.utc) - timedelta(minutes=1)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "CyberCheck temporary test CA")])
    ca = (x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name)
          .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
          .not_valid_before(start).not_valid_after(start + timedelta(days=1))
          .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
          .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False,
                                      key_encipherment=False, data_encipherment=False, key_agreement=False,
                                      key_cert_sign=True, crl_sign=True, encipher_only=None, decipher_only=None), critical=True)
          .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
          .sign(ca_key, hashes.SHA256()))
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, HOSTNAME)])
    certificate = (x509.CertificateBuilder().subject_name(name).issuer_name(ca_name)
                   .public_key(key.public_key()).serial_number(x509.random_serial_number())
                   .not_valid_before(start).not_valid_after(start + timedelta(days=1))
                   .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
                   .add_extension(x509.SubjectAlternativeName([x509.DNSName(HOSTNAME)]), critical=False)
                   .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
                   .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False,
                                               key_encipherment=True, data_encipherment=False, key_agreement=False,
                                               key_cert_sign=False, crl_sign=False,
                                               encipher_only=None, decipher_only=None), critical=True)
                   .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
                   .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
                   .sign(ca_key, hashes.SHA256()))
    ca_path, cert_path, key_path = (directory / name for name in ("ca.pem", "server.pem", "server.key"))
    ca_path.write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_path.touch(mode=0o600)
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                          serialization.NoEncryption()))
    return ca_path, cert_path, key_path


@contextmanager
def running_server(handler, context=None):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    if context:
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive(), "The integration server must stop after the test"


@pytest.fixture
def local_site(tmp_path):
    requests = []
    ca_path, cert_path, key_path = create_test_certificate(tmp_path)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_path, key_path)

    class Website(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            requests.append({"path": self.path, "host": self.headers.get("Host"),
                             "cookie": self.headers.get("Cookie"), "authorization": self.headers.get("Authorization")})
            if self.path in ("/upgrade", "/redirect", "/external"):
                destination = {"/upgrade": f"https://{HOSTNAME}/fixed", "/redirect": "/fixed",
                               "/external": "https://out-of-scope.example/"}[self.path]
                self.send_response(302)
                self.send_header("Location", destination)
                self.send_header("Set-Cookie", f"demo={COOKIE_VALUE}; Secure; HttpOnly; SameSite=Lax")
            else:
                self.send_response(403 if self.path == "/forbidden" else 200)
                self.send_header("Content-Type", "application/json" if self.path == "/api" else "text/html")
                if self.path in ("/fixed", "/api"):
                    self.send_header("Strict-Transport-Security", "max-age=31536000")
                    self.send_header("Content-Security-Policy", "default-src 'self'")
                    self.send_header("X-Content-Type-Options", "nosniff")
                    self.send_header("Set-Cookie", f"demo={COOKIE_VALUE}; Secure; HttpOnly; SameSite=Lax")
                else:
                    self.send_header("Set-Cookie", f"demo={COOKIE_VALUE}")
            self.send_header("Content-Length", str(len(BODY)))
            self.end_headers()
            try:
                self.wfile.write(BODY)
            except (BrokenPipeError, ConnectionResetError):
                pass  # The scanner intentionally closes without consuming the body.

    with ExitStack() as stack:
        http = stack.enter_context(running_server(Website))
        https = stack.enter_context(running_server(Website, context))
        yield {"ports": {80: http.server_port, 443: https.server_port}, "ca": ca_path, "requests": requests}


@pytest.fixture
def authorized_local_site(local_site, monkeypatch):
    """Only the test redirects validated connections to ephemeral loopback ports."""
    original_connect = socket.create_connection
    connections = []

    def resolve(host, port):
        assert host == HOSTNAME and port in local_site["ports"], "Unexpected integration target"
        return "127.0.0.1"

    def connect(address, timeout=web.REQUEST_TIMEOUT, source_address=None, **kwargs):
        host, port = address
        assert host == "127.0.0.1" and port in local_site["ports"], "Unexpected outbound connection"
        connections.append(port)
        return original_connect((host, local_site["ports"][port]), timeout, source_address, **kwargs)

    monkeypatch.setattr(web, "public_address", resolve)
    monkeypatch.setattr(socket, "create_connection", connect)
    monkeypatch.setenv("SSL_CERT_FILE", str(local_site["ca"]))
    return {**local_site, "connections": connections}


def rules(report):
    return {item["rule_id"] for item in report["findings"]}


@pytest.mark.parametrize("scheme", ["http", "https"])
def test_real_site_reports_insecure_headers_and_cookies(authorized_local_site, scheme):
    report = web.analyze_web(f"{scheme}://{HOSTNAME}/vulnerable", authorization_confirmed=True)
    expected = {"WEB-CSP", "WEB-NOSNIFF", "WEB-COOKIE", "WEB-HSTS" if scheme == "https" else "WEB-HTTPS"}
    assert report["status"] == "completed" and rules(report) == expected
    assert all(item["evidence"]["url"].endswith("/vulnerable") and item["recommendation"]
               for item in report["findings"])
    assert COOKIE_VALUE not in json.dumps(report) and BODY.decode() not in json.dumps(report)
    assert authorized_local_site["requests"][0]["host"] == HOSTNAME


def test_real_https_fixed_page_removes_findings_and_verifies_certificate(authorized_local_site):
    vulnerable = web.analyze_web(f"https://{HOSTNAME}/vulnerable", authorization_confirmed=True)
    fixed = web.analyze_web(f"https://{HOSTNAME}/fixed", authorization_confirmed=True)
    assert rules(vulnerable) == {"WEB-HSTS", "WEB-CSP", "WEB-NOSNIFF", "WEB-COOKIE"}
    assert fixed["status"] == "completed" and fixed["findings"] == []
    assert fixed["requests"][0]["tls"]["certificate_verified"] is True
    assert fixed["requests"][0]["tls"]["version"] in {"TLSv1.2", "TLSv1.3"}
    assert COOKIE_VALUE not in json.dumps(fixed)
    print(json.dumps({"insecure": vulnerable, "corrected": fixed}, indent=2))


def test_fixed_headers_over_real_http_do_not_hide_plaintext_transport(authorized_local_site):
    report = web.analyze_web(f"http://{HOSTNAME}/fixed", authorization_confirmed=True)
    assert rules(report) == {"WEB-HTTPS"}
    assert report["requests"][0]["tls"] is None


@pytest.mark.parametrize("scheme,path,ports", [("http", "/upgrade", [80, 443]),
                                              ("https", "/redirect", [443, 443])])
def test_real_redirect_does_not_forward_cookies(authorized_local_site, scheme, path, ports):
    report = web.analyze_web(f"{scheme}://{HOSTNAME}{path}", authorization_confirmed=True)
    assert report["status"] == "completed" and report["findings"] == []
    assert authorized_local_site["connections"] == ports
    assert [item["path"] for item in authorized_local_site["requests"]] == [path, "/fixed"]
    assert all(item["cookie"] is None and item["authorization"] is None
               for item in authorized_local_site["requests"])


def test_real_cross_host_redirect_is_not_requested(authorized_local_site):
    report = web.analyze_web(f"https://{HOSTNAME}/external", authorization_confirmed=True)
    assert report["status"] == "partial" and "hostname" in report["checks"][-1]["error"]
    assert authorized_local_site["connections"] == [443]
    assert [item["path"] for item in authorized_local_site["requests"]] == ["/external"]


def test_real_untrusted_certificate_fails_without_http_fallback(authorized_local_site, monkeypatch):
    monkeypatch.delenv("SSL_CERT_FILE")
    report = web.analyze_web(f"https://{HOSTNAME}/fixed", authorization_confirmed=True)
    assert report["status"] == "failed" and rules(report) == {"WEB-TLS-CERT"}
    assert authorized_local_site["connections"] == [443]
    assert authorized_local_site["requests"] == []


def test_real_trusted_certificate_with_wrong_hostname_is_rejected(authorized_local_site, monkeypatch):
    def resolve(host, port):
        assert host == "wrong-name.test" and port == 443
        return "127.0.0.1"
    monkeypatch.setattr(web, "public_address", resolve)
    report = web.analyze_web("https://wrong-name.test/fixed", authorization_confirmed=True)
    assert report["status"] == "failed" and rules(report) == {"WEB-TLS-CERT"}
    assert authorized_local_site["requests"] == []


@pytest.mark.parametrize("path", ["/api", "/forbidden"])
def test_real_non_html_or_denied_page_has_incomplete_coverage(authorized_local_site, path):
    report = web.analyze_web(f"https://{HOSTNAME}{path}", authorization_confirmed=True)
    assert report["status"] == "partial"
    assert not rules(report) & {"WEB-CSP", "WEB-NOSNIFF"}


def test_local_addresses_remain_blocked_without_test_override(local_site):
    report = web.analyze_web("http://127.0.0.1/vulnerable", authorization_confirmed=True)
    assert report["status"] == "failed" and "blocked" in report["checks"][-1]["error"]
    assert local_site["requests"] == []


@pytest.mark.parametrize("path,expected_status", [("/vulnerable", "completed"), ("/fixed", "completed"),
                                                  ("/api", "partial"), ("/external", "partial")])
def test_web_api_worker_history_and_deletion_over_real_tls(authorized_local_site, tmp_path, path, expected_status):
    settings = Settings(api_token="test-operator-" + "x" * 40, data_dir=tmp_path / "api-data")
    headers = {"Authorization": f"Bearer {settings.api_token}"}
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/web-analyses", headers=headers, json={
            "target_url": f"https://{HOSTNAME}{path}", "authorization_confirmed": True,
        })
        assert response.status_code == 202
        assert authorized_local_site["requests"] == []
        store = client.app.state.store
        job = store.claim()
        assert job["status"] == "running"
        assert client.delete(response.headers["location"], headers=headers).status_code == 409
        process(job, store, None, settings)
        report = client.get(response.headers["location"], headers=headers).json()
        analysis = report["analysis"]
        assert analysis["status"] == expected_status
        assert analysis["kind"] == "web" and analysis["commit_sha"] is None
        assert analysis["requests"][0]["tls"]["certificate_verified"] is True
        assert analysis["limitations"] and analysis["finished_at"]
        if path == "/vulnerable":
            assert "web_cookies" in report["groups"] and "web_headers" in report["groups"]
        if path == "/fixed":
            assert analysis["findings"] == []
        serialized = json.dumps(report)
        assert COOKIE_VALUE not in serialized and BODY.decode() not in serialized
        assert all(request["authorization"] is None for request in authorized_local_site["requests"])
        assert client.get("/api/analyses", headers=headers).json()["analyses"] == [analysis]
        assert client.delete(response.headers["location"], headers=headers).status_code == 204
        assert store.list() == []
