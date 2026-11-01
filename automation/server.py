"""Loopback-only reference HTTP API. Never expose directly to the internet."""
import hmac
import json
import os
import re
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, HTTPServer

from .core import Rejected, Store, canonical, exact, strict_json
from .providers import AnthropicProvider, OfflineProvider


def secrets_from_environment():
    names = ["INGEST_TOKEN", "REVIEWER_A_TOKEN", "REVIEWER_B_TOKEN", "AUDIT_KEY"]
    secrets = [os.environ.get(n, "") for n in names]
    if any(not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", s) for s in secrets) or len(set(secrets)) != 4:
        raise ValueError("Four distinct, randomly generated >=32-character secrets required")
    return dict(zip(names, secrets))


def make_server(store, secrets, provider, port=8080):
    attempts = deque(maxlen=120)

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"
        server_version = "KAI-Demo"
        sys_version = ""

        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, *_):
            pass  # No request paths, credentials, bodies or provider errors.

        def reply(self, status, value):
            data = canonical(value).encode()
            self.send_response(status)
            for k, v in {"Content-Type": "application/json", "Content-Length": str(len(data)),
                         "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
                         "Content-Security-Policy": "default-src 'none'", "Connection": "close"}.items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(data)

        def dispatch(self):
            try:
                now = time.monotonic()
                while attempts and attempts[0] < now - 60:
                    attempts.popleft()
                if len(attempts) >= 120:
                    raise Rejected("rate_limited", 429)
                attempts.append(now)
                # Refuse browser-origin requests, query strings and Host rebinding.
                if self.headers.get("Origin") or self.headers.get("Host") not in {
                        f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}:
                    raise Rejected("forbidden_origin", 403)
                auths = self.headers.get_all("Authorization", [])
                if len(auths) != 1:
                    raise Rejected("unauthorized", 401)
                token = auths[0]
                if not token.isascii():
                    raise Rejected("unauthorized", 401)
                actor = None
                for env, role in [("INGEST_TOKEN", "ingest"), ("REVIEWER_A_TOKEN", "reviewer_a"),
                                  ("REVIEWER_B_TOKEN", "reviewer_b")]:
                    if hmac.compare_digest(token, "Bearer " + secrets[env]):
                        actor = role
                if actor is None:
                    raise Rejected("unauthorized", 401)
                match = re.fullmatch(r"/v1/jobs/([0-9a-f-]{36})(/decision)?", self.path)
                if self.command == "GET" and match and not match[2]:
                    if actor == "ingest":
                        raise Rejected("forbidden", 403)
                    return self.reply(200, store.get(match[1]))
                if self.command != "POST":
                    raise Rejected("not_found", 404)
                if self.headers.get("Transfer-Encoding"):
                    raise Rejected("unsupported_transfer_encoding", 400)
                lengths = self.headers.get_all("Content-Length", [])
                if len(lengths) != 1 or not re.fullmatch(r"[0-9]{1,5}", lengths[0]):
                    raise Rejected("invalid_content_length", 400)
                length = int(lengths[0])
                if not 1 <= length <= 12288:
                    raise Rejected("payload_too_large", 413)
                if self.headers.get("Content-Type", "").lower() != "application/json":
                    raise Rejected("unsupported_content_type", 415)
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise Rejected("truncated_body", 400)
                body = strict_json(raw)
                if self.path in {"/v1/intakes", "/v1/invoices"}:
                    if actor != "ingest":
                        raise Rejected("forbidden", 403)
                    kind = "intake" if self.path == "/v1/intakes" else "invoice"
                    return self.reply(200, store.ingest(kind, body, provider))
                if match and match[2]:
                    if actor == "ingest":
                        raise Rejected("forbidden", 403)
                    exact(body, {"decision"})
                    return self.reply(200, store.decide(match[1], actor, body["decision"]))
                raise Rejected("not_found", 404)
            except Rejected as e:
                self.reply(e.status, {"error": e.code})
            except (BrokenPipeError, ConnectionResetError, TimeoutError):
                self.close_connection = True
            except Exception:
                self.reply(500, {"error": "internal_error"})

        do_POST = dispatch
        do_GET = dispatch

    # Deliberately single-process / loopback. No pretending this development
    # server is a hardened reverse proxy or multi-tenant deployment.
    return HTTPServer(("127.0.0.1", port), Handler)


def main():
    os.umask(0o077)
    secrets = secrets_from_environment()
    provider_mode = os.environ.get("MODEL_MODE", "offline")
    if provider_mode not in {"offline", "anthropic"}:
        raise ValueError("MODEL_MODE must be offline or anthropic")
    provider = AnthropicProvider() if provider_mode == "anthropic" else OfflineProvider()
    store = Store(os.environ.get("DATABASE_PATH", "var/demo.sqlite"), secrets["AUDIT_KEY"].encode())
    make_server(store, secrets, provider, int(os.environ.get("PORT", "8080"))).serve_forever()


if __name__ == "__main__":
    main()
