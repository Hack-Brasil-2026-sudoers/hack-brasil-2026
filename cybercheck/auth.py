"""GitHub OAuth with browser-bound PKCE and encrypted, expiring server-side sessions."""
import base64
import hashlib
import hmac
import secrets
import time
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet, InvalidToken

from .github import GitHub, GitHubError


SESSION_COOKIE = "cybercheck_session"
STATE_COOKIE = "cybercheck_oauth_state"


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class Auth:
    def __init__(self, settings, store, transport=None):
        self.settings, self.store, self.transport = settings, store, transport
        self.enabled = bool(settings.github_client_id)
        self.cipher = Fernet(settings.session_key.encode()) if self.enabled else None
        if self.enabled:
            with store.connect() as db:
                db.execute("""CREATE TABLE IF NOT EXISTS oauth_states (
                    hash TEXT PRIMARY KEY, verifier TEXT NOT NULL, expires_at INTEGER NOT NULL
                )""")
                db.execute("""CREATE TABLE IF NOT EXISTS user_sessions (
                    hash TEXT PRIMARY KEY, owner TEXT NOT NULL, user_id INTEGER NOT NULL,
                    login TEXT NOT NULL, token TEXT NOT NULL, expires_at INTEGER NOT NULL
                )""")
                db.execute("CREATE INDEX IF NOT EXISTS sessions_by_owner ON user_sessions(owner, expires_at)")

    def begin(self):
        state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(64)
        now = int(time.time())
        with self.store.connect() as db:
            db.execute("DELETE FROM oauth_states WHERE expires_at<=?", (now,))
            db.execute("DELETE FROM user_sessions WHERE expires_at<=?", (now,))
            db.execute("INSERT INTO oauth_states VALUES(?,?,?)",
                       (digest(state), self.cipher.encrypt(verifier.encode()).decode(), now + 600))
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        query = urlencode({"client_id": self.settings.github_client_id,
                           "redirect_uri": self.settings.public_url + "/auth/github/callback",
                           "state": state, "code_challenge": challenge, "code_challenge_method": "S256",
                           "scope": "offline_access"})
        return state, "https://github.com/login/oauth/authorize?" + query

    def complete(self, code, state, browser_state):
        if not state or not browser_state or not secrets.compare_digest(digest(state), digest(browser_state)):
            raise GitHubError("The login request is invalid or expired. Start again.")
        now = int(time.time())
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM oauth_states WHERE hash=? AND expires_at>?",
                             (digest(state), now)).fetchone()
            db.execute("DELETE FROM oauth_states WHERE hash=?", (digest(state),))
        if not row or not code:
            raise GitHubError("The login request is invalid or expired. Start again.")
        try:
            verifier = self.cipher.decrypt(row["verifier"].encode()).decode()
            with httpx.Client(timeout=30, trust_env=False, transport=self.transport) as client:
                response = client.post("https://github.com/login/oauth/access_token",
                                       headers={"Accept": "application/json"}, data={
                                           "client_id": self.settings.github_client_id,
                                           "client_secret": self.settings.github_client_secret,
                                           "code": code, "code_verifier": verifier,
                                           "redirect_uri": self.settings.public_url + "/auth/github/callback",
                                       })
            if response.status_code != 200:
                raise GitHubError("GitHub could not complete login. Start again.")
            data = GitHub.payload(response)
            token, expires = data.get("access_token"), data.get("expires_in")
            if (not isinstance(token, str) or not token or not token.isascii()
                    or any(char.isspace() or ord(char) < 32 for char in token)
                    or type(expires) is not int or expires <= 0 or data.get("token_type") != "bearer"):
                raise GitHubError("GitHub did not return an expiring user token. Check the App settings and sign in again.")
            user = GitHub(self.settings, self.transport, user_token=token).profile()
        except (httpx.HTTPError, InvalidToken, UnicodeError) as exc:
            raise GitHubError("GitHub login failed. Start again.") from exc
        session = secrets.token_urlsafe(32)
        lifetime = min(expires, 28800)
        with self.store.connect() as db:
            db.execute("INSERT INTO user_sessions VALUES(?,?,?,?,?,?)", (
                digest(session), f"github:{user['id']}", user["id"], user["login"],
                self.cipher.encrypt(token.encode()).decode(), int(time.time()) + lifetime,
            ))
        # Refresh tokens are deliberately discarded; expiration requires a new login.
        return session, lifetime

    def current(self, session):
        if not self.enabled or not session:
            return None
        with self.store.connect() as db:
            row = db.execute("SELECT * FROM user_sessions WHERE hash=? AND expires_at>?",
                             (digest(session), int(time.time()))).fetchone()
        if not row:
            return None
        return self.decode(row)

    def decode(self, row):
        try:
            token = self.cipher.decrypt(row["token"].encode()).decode()
        except (InvalidToken, UnicodeError) as exc:
            raise GitHubError("The saved GitHub session is unavailable. Sign in again.") from exc
        return {"owner": row["owner"], "id": row["user_id"], "login": row["login"], "token": token,
                "csrf_token": hmac.new(self.settings.session_key.encode(), row["hash"].encode(), "sha256").hexdigest()}

    def token_for_owner(self, owner):
        if not self.enabled:
            raise GitHubError("GitHub user login is no longer configured. Sign in again.")
        with self.store.connect() as db:
            row = db.execute("SELECT * FROM user_sessions WHERE owner=? AND expires_at>? "
                             "ORDER BY expires_at DESC LIMIT 1", (owner, int(time.time()))).fetchone()
        if not row:
            raise GitHubError("The user's GitHub session expired or was signed out. Sign in and request a new analysis.")
        return self.decode(row)["token"]

    def logout(self, session):
        if session:
            with self.store.connect() as db:
                db.execute("DELETE FROM user_sessions WHERE hash=?", (digest(session),))
