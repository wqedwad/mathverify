"""The Meta client verifies TLS without Python's strict X.509 profile (27 Sep 2026: the cloud's egress
proxy re-signs with a CA lacking the key-usage extension, and Python 3.13+ refused every call)."""
from __future__ import annotations

import io
import json
import ssl

from mathverify.llm import meta_client
from mathverify.llm.meta_client import MetaClient, tls_context


def test_the_context_still_verifies_the_chain_and_the_host():
    ctx = tls_context()
    assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname
    assert not ctx.verify_flags & getattr(ssl, "VERIFY_X509_STRICT", 0)


def test_every_request_uses_that_context(monkeypatch):
    seen = {}

    class _Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=None, context=None):
        seen["context"] = context
        return _Resp(json.dumps({"choices": []}).encode())

    monkeypatch.setattr(meta_client.urllib.request, "urlopen", fake_urlopen)
    c = MetaClient(model="muse-spark-1.3")
    c._key = "k"
    c._post({"stream": False})
    ctx = seen["context"]
    assert isinstance(ctx, ssl.SSLContext) and ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname
