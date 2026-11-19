"""Conservative, unauthenticated checks for one authorized public website."""
import http.client
import ipaddress
import re
import socket
import ssl
from http.cookies import CookieError, SimpleCookie
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

from .scanners import PRIORITIES, finding
from .store import now


MAX_REDIRECTS = 3
REQUEST_TIMEOUT = 5
TRANSITION_NETWORKS = tuple(ipaddress.ip_network(value) for value in (
    "64:ff9b::/96", "64:ff9b:1::/48", "2002::/16", "2001::/32",
))


class WebError(ValueError):
    """Public error without response bodies, cookies, or raw input URLs."""


def normalize_url(value):
    if not isinstance(value, str) or len(value) > 2048 or re.search(r"[\s\x00-\x1f\x7f\\\\]", value):
        raise WebError("Provide an HTTP(S) URL without whitespace or control characters.")
    try:
        parts = urlsplit(value)
        if (parts.scheme not in ("http", "https") or not parts.hostname
                or parts.username is not None or parts.password is not None
                or parts.query or parts.fragment):
            raise WebError("Use a public HTTP(S) URL without credentials, query parameters, or fragments.")
        expected_port = 443 if parts.scheme == "https" else 80
        if parts.port not in (None, expected_port):
            raise WebError("Only the standard HTTP and HTTPS ports are supported.")
        host = parts.hostname.encode("idna").decode("ascii").lower().rstrip(".")
        if "%" in host:
            raise WebError("Scoped or percent-encoded hostnames are not supported.")
        try:
            host = str(ipaddress.ip_address(host))
        except ValueError:
            if len(host) > 253 or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                                      for label in host.split(".")):
                raise WebError("Invalid website hostname.") from None
        authority = f"[{host}]" if ":" in host else host
        path = quote(parts.path or "/", safe="/%:@!$&'()*+,;=-._~")
        return urlunsplit((parts.scheme, authority, path, "", ""))
    except (ValueError, UnicodeError) as exc:
        if isinstance(exc, WebError):
            raise
        raise WebError("Invalid website URL.") from None


def public_address(host, port):
    try:
        answers = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError:
        raise WebError("Could not resolve the website hostname.") from None
    addresses = []
    for answer in answers:
        address = ipaddress.ip_address(answer[4][0])
        mapped = getattr(address, "ipv4_mapped", None)
        transition = address.version == 6 and any(address in network for network in TRANSITION_NETWORKS)
        if (not address.is_global or address.is_reserved or address.is_multicast or address.is_unspecified
                or (mapped is not None and not mapped.is_global) or transition):
            raise WebError("Private, local, special-use, or mixed public/private destinations are blocked.")
        addresses.append(str(address))
    if not addresses:
        raise WebError("The hostname has no usable public address.")
    return addresses[0]


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host, address):
        self.address = address
        self.tls_context = ssl.create_default_context()
        super().__init__(host, timeout=REQUEST_TIMEOUT, context=self.tls_context)

    def connect(self):
        # Connect to the validated IP, retaining the original hostname for SNI and certificate verification.
        raw = socket.create_connection((self.address, self.port), self.timeout)
        try:
            self.sock = self.tls_context.wrap_socket(raw, server_hostname=self.host)
        except Exception:
            raw.close()
            raise


def request_page(url):
    parts = urlsplit(url)
    secure = parts.scheme == "https"
    address = public_address(parts.hostname, 443 if secure else 80)
    connection = (PinnedHTTPSConnection(parts.hostname, address) if secure else
                  http.client.HTTPConnection(address, 80, timeout=REQUEST_TIMEOUT))
    try:
        connection.request("GET", parts.path, headers={
            "Host": parts.netloc, "User-Agent": "CyberCheck/0.1 (authorized security assessment)",
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.1", "Connection": "close",
        })
        tls = {"certificate_verified": True, "version": connection.sock.version()} if secure else None
        response = connection.getresponse()
        # Do not read response bodies or forward cookies, credentials, or environment proxies.
        return response.status, response.getheaders(), tls
    finally:
        connection.close()


def observation(rule, category, title, url, recommendation, evidence, severity="low"):
    result = finding("cybercheck-web", rule, category, title, None, None, severity, "high",
                     recommendation, {"url": url, **evidence})
    result["priority"] = "review"
    result["priority_reason"] = "Observed response configuration; impact depends on application context. Review required."
    return result


def inspect_headers(url, headers):
    fields = {}
    for name, value in headers:
        fields.setdefault(name.lower(), []).append(value)
    results = []
    secure = urlsplit(url).scheme == "https"
    if not secure:
        results.append(observation("WEB-HTTPS", "web_transport", "Response served over unencrypted HTTP", url,
                                   "Serve this page over HTTPS and redirect HTTP requests to HTTPS.",
                                   {"https": False}, "medium"))
    if secure:
        hsts = fields.get("strict-transport-security", [])
        ages = [re.search(r"(?:^|;)\s*max-age\s*=\s*([0-9]+)\s*(?:;|$)", value, re.I) for value in hsts]
        enabled = len(hsts) == 1 and any(match and match.group(1).strip("0") for match in ages)
        if not enabled:
            results.append(observation("WEB-HSTS", "web_headers", "HSTS is absent or not enabled", url,
                                       "After confirming HTTPS works throughout the site, configure an appropriate HSTS max-age.",
                                       {"header": "Strict-Transport-Security", "enabled": False}))
    content_type = fields.get("content-type", [""])[0].split(";", 1)[0].strip().lower()
    if content_type not in ("text/html", "application/xhtml+xml"):
        return results, False
    for header, rule, title, recommendation in (
        ("content-security-policy", "WEB-CSP", "No enforced Content Security Policy observed",
         "Design and test a Content Security Policy suitable for the page; report-only policies do not enforce it."),
        ("x-content-type-options", "WEB-NOSNIFF", "Content-type sniffing protection is missing or invalid",
         "Send X-Content-Type-Options: nosniff with correct Content-Type values."),
    ):
        values = fields.get(header, [])
        configured = any(value.strip() for value in values)
        if header == "x-content-type-options":
            configured = len(values) == 1 and values[0].strip().lower() == "nosniff"
        if not configured:
            results.append(observation(rule, "web_headers", title, url, recommendation,
                                       {"header": header, "configured": False}))
    return results, True


def inspect_cookies(url, headers):
    results = []
    valid = True
    for index, value in enumerate(v for name, v in headers if name.lower() == "set-cookie"):
        cookie = SimpleCookie()
        try:
            cookie.load(value)
        except (ValueError, CookieError):
            valid = False
            continue
        if not cookie:
            valid = False
            continue
        for morsel in cookie.values():
            missing = [name for name in ("secure", "httponly", "samesite") if not morsel[name]]
            if morsel["samesite"] and morsel["samesite"].lower() not in ("lax", "strict", "none"):
                missing.append("valid_samesite")
            if missing:
                results.append(observation(
                    "WEB-COOKIE", "web_cookies", "Cookie protection attributes require review", url,
                    "For sensitive cookies, use Secure, HttpOnly where JavaScript access is unnecessary, "
                    "and a SameSite policy compatible with the application. Cookie purpose was not assessed.",
                    {"cookie_index": index + 1, "missing_attributes": missing},
                ))
    return results, valid


def analyze_web(url, *, authorization_confirmed=False):
    if not authorization_confirmed:
        raise WebError("Confirm ownership or written authorization before analyzing a website.")
    initial = normalize_url(url)
    report = {"kind": "web", "target_url": initial, "started_at": now(), "finished_at": None,
              "status": "failed", "requests": [], "findings": [], "checks": [],
              "limitations": ["Unauthenticated GET requests only; no crawling, payload injection, or form submission.",
                              "Only the supplied hostname is authorized; cross-host redirects are not followed.",
                              "No response bodies, raw cookies, or credentials are retained.",
                              "TLS covers the negotiated connection, not all supported protocols or cipher suites.",
                              "Header checks inspect response configuration, not CSP policy quality or browser behavior.",
                              "Missing headers do not prove exploitability; no security score is assigned."]}
    current = initial
    seen = set()
    try:
        for _ in range(MAX_REDIRECTS + 1):
            if current in seen:
                raise WebError("Redirect loop detected; analysis incomplete.")
            seen.add(current)
            status, headers, tls = request_page(current)
            report["requests"].append({"url": current, "status_code": status, "tls": tls})
            cookies, valid_cookies = inspect_cookies(current, headers)
            report["findings"].extend(cookies)
            report["checks"].append({"check": "cookies", "url": current,
                                     "status": "completed" if valid_cookies else "partial"})
            if status in (301, 302, 303, 307, 308):
                locations = [v for k, v in headers if k.lower() == "location"]
                if len(locations) != 1:
                    raise WebError("Redirect has no single usable destination; analysis incomplete.")
                destination = normalize_url(urljoin(current, locations[0]))
                if urlsplit(destination).hostname != urlsplit(initial).hostname:
                    raise WebError("Redirect leaves the authorized hostname; destination was not requested.")
                if urlsplit(current).scheme == "https" and urlsplit(destination).scheme != "https":
                    raise WebError("HTTPS downgrade redirect blocked; destination was not requested.")
                current = destination
                continue
            if not 200 <= status < 300:
                raise WebError("The page returned a non-success status; configuration analysis is incomplete.")
            findings, html = inspect_headers(current, headers)
            report["findings"].extend(findings)
            report["checks"].extend([
                {"check": "transport", "status": "completed"},
                {"check": "headers", "status": "completed" if html else "partial",
                 "note": None if html else "HTML-specific checks were not applied to this content type."},
            ])
            report["status"] = "partial" if any(c["status"] == "partial" for c in report["checks"]) else "completed"
            break
        else:
            raise WebError("Redirect limit exceeded; analysis incomplete.")
    except ssl.SSLCertVerificationError:
        report["status"] = "partial" if report["requests"] else "failed"
        report["findings"].append(observation(
            "WEB-TLS-CERT", "web_transport", "TLS certificate verification failed", current,
            "Check the certificate's validity, hostname, and trust chain. Verification was not bypassed.",
            {"certificate_verified": False}, "medium"))
        report["checks"].append({"check": "request", "status": "failed", "error": "TLS certificate verification failed."})
    except (WebError, OSError, http.client.HTTPException) as exc:
        message = str(exc) if isinstance(exc, WebError) else "Network, TLS, or HTTP response failure; analysis incomplete."
        report["status"] = "partial" if report["requests"] else "failed"
        report["checks"].append({"check": "request", "status": "failed", "error": message})
    report["finished_at"] = now()
    report["findings"].sort(key=lambda item: (PRIORITIES[item["priority"]], item["rule_id"]))
    return report
