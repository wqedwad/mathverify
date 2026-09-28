"""The Meta client streams, and a non-streaming client retries a gateway failure as a stream (K4,
28 Sep 2026: 61 of 179 items ended with HTTP 502 "upstream request failed" from the cloud's egress
proxy, which cuts a non-streaming call at ~31 s; only 504/524/408 switched to streaming)."""
from __future__ import annotations

import io
import urllib.error

import pytest

from mathverify.llm import meta_client
from mathverify.llm.base import LLMError
from mathverify.llm.cache import LLMCache
from mathverify.llm.meta_client import MetaClient

_LAST = {"id": "chatcmpl-1", "model": "muse-spark-1.3", "choices": [{"delta": {}, "finish_reason": "stop", "index": 0}],
         "usage": {"prompt_tokens": 1000, "completion_tokens": 2000}}


def _client(tmp_path, monkeypatch, fail_codes, stream=False):
    """A client whose transport fails with `fail_codes` in turn, then streams one answer."""
    calls, sleeps = [], []
    codes = list(fail_codes)

    def fake_post(body):
        calls.append(bool(body.get("stream")))
        if codes:
            raise urllib.error.HTTPError(meta_client._URL, codes.pop(0), "gw", {},
                                         io.BytesIO(b"upstream request failed"))
        if body.get("stream"):
            return dict(_LAST), '{"ok": 1}'
        return {**_LAST, "choices": [{"message": {"content": '{"ok": 1}'}, "finish_reason": "stop"}]}, ""

    c = MetaClient(model="muse-spark-1.3", cache=LLMCache(tmp_path, mode="auto"), max_retries=2, stream=stream)
    c._key = "k"
    monkeypatch.setattr(c, "_post", fake_post)
    monkeypatch.setattr(meta_client.time, "sleep", lambda s: sleeps.append(s))
    return c, calls, sleeps


def test_the_client_streams_from_the_first_attempt(tmp_path, monkeypatch):
    assert MetaClient(model="muse-spark-1.3", cache=LLMCache(tmp_path)).stream is True
    c, calls, sleeps = _client(tmp_path, monkeypatch, [], stream=True)
    r = c.complete("sys", "user", schema={"type": "object"}, effort="xhigh")
    assert calls == [True] and sleeps == [] and r.parsed == {"ok": 1} and r.meta["streamed"] is True
    assert r.cost_usd > 0


def test_a_cached_answer_does_not_depend_on_the_mode(tmp_path, monkeypatch):
    c, calls, _ = _client(tmp_path, monkeypatch, [], stream=False)
    first = c.complete("sys", "user", schema={"type": "object"}, effort="xhigh")
    c2, calls2, _ = _client(tmp_path, monkeypatch, [], stream=True)
    again = c2.complete("sys", "user", schema={"type": "object"}, effort="xhigh")
    assert calls == [False] and calls2 == [] and again.cached and again.parsed == first.parsed


@pytest.mark.parametrize("code", [502, 504, 524, 408])
def test_a_gateway_failure_is_retried_at_once_as_a_stream(tmp_path, monkeypatch, code):
    c, calls, sleeps = _client(tmp_path, monkeypatch, [code])
    r = c.complete("sys", "user", schema={"type": "object"}, effort="xhigh")
    assert calls == [False, True] and sleeps == []
    assert r.parsed == {"ok": 1} and r.meta["streamed"] is True
    # the stream's last event carries usage: the call is paid for and counts against the cap
    assert r.input_tokens == 1000 and r.output_tokens == 2000 and r.cost_usd > 0


def test_a_502_while_already_streaming_waits_and_stays_a_stream(tmp_path, monkeypatch):
    c, calls, sleeps = _client(tmp_path, monkeypatch, [502, 502])
    r = c.complete("sys", "user", schema={"type": "object"}, effort="xhigh")
    assert calls == [False, True, True] and len(sleeps) == 1
    assert r.meta["streamed"] is True


@pytest.mark.parametrize("code", [500, 503, 429])
def test_other_server_errors_are_retried_as_they_were(tmp_path, monkeypatch, code):
    c, calls, sleeps = _client(tmp_path, monkeypatch, [code])
    r = c.complete("sys", "user", schema={"type": "object"}, effort="xhigh")
    assert calls == [False, False] and len(sleeps) == 1
    assert r.meta["streamed"] is False


def test_retries_run_out_with_an_error(tmp_path, monkeypatch):
    c, calls, _ = _client(tmp_path, monkeypatch, [502, 502, 502])
    with pytest.raises(LLMError, match="HTTP 502"):
        c.complete("sys", "user", schema={"type": "object"}, effort="xhigh")
    assert calls == [False, True, True]
