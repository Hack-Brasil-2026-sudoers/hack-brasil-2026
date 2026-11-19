"""Intentionally insecure/corrected website, only for an isolated container network."""
import argparse
import ssl
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


parser = argparse.ArgumentParser()
parser.add_argument("profile", choices=["vulnerable", "fixed"])
args = parser.parse_args()
fixed = args.profile == "fixed"


class Website(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        body = (b'<!doctype html><html><head><title>CyberCheck isolated laboratory</title></head>'
                b'<body><h1>Controlled test website</h1><a href="/details">Details</a>'
                b'<form action="/login" method="post"><input name="username">'
                b'<input name="password" type="password"><button>Demo only</button></form></body></html>')
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Set-Cookie", "demo=fixture-only-cookie" + ("; Secure; HttpOnly; SameSite=Lax" if fixed else ""))
        if fixed:
            self.send_header("Content-Security-Policy", "default-src 'none'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Strict-Transport-Security", "max-age=31536000")
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ssl.SSLError):
            pass

    # The demo form has no state-changing behavior; its response follows the same header profile.
    do_POST = do_GET


# Bind inside the internal container network only; the runner never publishes host ports.
http = ThreadingHTTPServer(("0.0.0.0", 8080), Website)
https = ThreadingHTTPServer(("0.0.0.0", 8443), Website)
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
if not fixed:
    context.set_ciphers("DEFAULT:@SECLEVEL=0")  # Deliberately weak configuration for the isolated lab.
    context.minimum_version = ssl.TLSVersion.TLSv1
context.load_cert_chain("/site/certificate.pem", "/site/private.key")
https.socket = context.wrap_socket(https.socket, server_side=True)
threading.Thread(target=http.serve_forever, daemon=True).start()
https.serve_forever()
