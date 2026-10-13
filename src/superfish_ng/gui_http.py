# SPDX-License-Identifier: Apache-2.0
"""Authenticated loopback HTTP envelopes, replies and fixed static assets."""
import hmac
import json
import mimetypes
import subprocess
from http.server import BaseHTTPRequestHandler
from .json_codec import parse_json

_REQUEST_BYTES = 4 * 1024 * 1024
_CHECKPOINT_REQUEST_BYTES = 64 * 1024 * 1024
_CHECKPOINT_ACTIONS = frozenset(('hphi-replay-tune', 'hphi-resume-tune', 'hphi-tune-trial'))
_CURVED_PLANAR_CHECKPOINT_BYTES = 128 * 1024 * 1024
_CURVED_PLANAR_CHECKPOINT_ACTIONS = frozenset(('planar-curved-replay-tune', 'planar-curved-resume-tune', 'planar-curved-tune-trial'))

def read_api_request(stream, content_length, *, action_hint=None):
    """Read a bounded authenticated API envelope, preserving strict JSON parsing."""
    size = int(content_length)
    large_curve = action_hint in _CURVED_PLANAR_CHECKPOINT_ACTIONS
    limit = _CURVED_PLANAR_CHECKPOINT_BYTES if large_curve else _CHECKPOINT_REQUEST_BYTES
    if not 0 < size <= limit:
        raise ValueError(f"request must be between 1 byte and {limit // (1024 * 1024)} MiB")
    raw = stream.read(size)
    if len(raw) != size:
        raise ValueError("request body is shorter than Content-Length")
    data = parse_json(raw)
    if not isinstance(data, dict):
        raise ValueError("request must be an object")
    if large_curve and data.get('action') != action_hint:
        raise ValueError('curved checkpoint action header differs from the strict request action')
    if size > _REQUEST_BYTES and (not isinstance(data.get("action"), str) or data['action'] not in _CHECKPOINT_ACTIONS | _CURVED_PLANAR_CHECKPOINT_ACTIONS):
        raise ValueError("request exceeds 4 MiB; only dedicated checkpoint replay, resume and trial import allow larger bodies")
    return data


ASSET_PATHS = {
    '/': 'index.html',
    '/app.js': 'app.js',
    '/curved-mesh-canvas.js': 'curved-mesh-canvas.js',
    '/curved-deformation-workflow.js': 'curved-deformation-workflow.js',
    '/style.css': 'style.css',
    '/planar.html': 'planar.html',
    '/planar.js': 'planar.js',
    '/planar-curved.html': 'planar-curved.html',
    '/planar-curved.js': 'planar-curved.js',
    '/hphi.html': 'hphi.html',
    '/hphi.js': 'hphi.js',
    '/magnetic.html': 'magnetic.html',
    '/static-study.html': 'static-study.html',
    '/static-study.js': 'static-study.js',
    '/static.html': 'static.html',
    '/static.js': 'static.js',
    '/magnetic.js': 'magnetic.js',
}


def make_handler(token, assets, operation_dispatch, read_request):
    """Build the local transport around explicit application callbacks."""
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(
            self, data, status=200, content_type="application/json; charset=utf-8"
        ):
            if not isinstance(data, bytes):
                data = json.dumps(data, ensure_ascii=False, allow_nan=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'",
            )
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def valid_host(self):
            return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

        def do_GET(self):
            if not self.valid_host():
                return self.reply({'error': 'invalid host'}, 403)
            from urllib.parse import urlsplit
            name = ASSET_PATHS.get(urlsplit(self.path).path)
            if name is None:
                return self.reply({"error": "not found"}, 404)
            self.reply(
                (assets / name).read_bytes(),
                content_type=mimetypes.guess_type(name)[0] + "; charset=utf-8",
            )

        def do_POST(self):
            origin = f"http://127.0.0.1:{self.server.server_port}"
            if (
                not self.valid_host()
                or self.headers.get("Origin", origin) != origin
                or not hmac.compare_digest(self.headers.get("X-NG-Token", ""), token)
            ):
                return self.reply(
                    {"error": "local session required; reopen the launch URL"}, 403
                )
            if self.path != "/api":
                return self.reply({"error": "not found"}, 404)
            try:
                data = read_request(self.rfile, self.headers.get("Content-Length", "0"),
                                        action_hint=self.headers.get('X-NG-Action'))
                response = operation_dispatch(data)
                return self.reply(response.data, content_type=response.content_type)
            except (
                ValueError,
                KeyError,
                TypeError,
                OSError,
                RuntimeError,
                subprocess.TimeoutExpired,
            ) as exc:
                self.reply({"error": str(exc)}, 400)


    return Handler
