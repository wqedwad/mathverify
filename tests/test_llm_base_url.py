"""The Anthropic client's endpoint never comes from the host's ANTHROPIC_BASE_URL.

Measured in the Claude Code cloud (bulut_tani.md, section 2): the session environment defines
ANTHROPIC_BASE_URL for Claude Code itself and defines neither ANTHROPIC_API_KEY nor
ANTHROPIC_AUTH_TOKEN. The pinned SDK reads ANTHROPIC_BASE_URL whenever `base_url` is omitted, so
without an explicit endpoint the project's F3 calls (with the key from .env) would go to the
platform's endpoint. These tests build clients only and inspect `base_url`; no request is sent,
and every socket connect is blocked so an accidental request fails loudly instead of spending.
"""
from __future__ import annotations

import socket

import pytest

anthropic = pytest.importorskip("anthropic")

from mathverify.llm.anthropic_client import (  # noqa: E402
    AnthropicClient, BASE_URL_ENV, DEFAULT_BASE_URL, resolve_base_url)
from mathverify.llm.cache import LLMCache  # noqa: E402

FAKE_KEY = "sk-ant-test-not-a-real-key"
FAKE_TOKEN = "test-bearer-not-a-real-token"
HOST_URL = "http://example.invalid"

# Every variable the pinned SDK consults for credentials, endpoint or extra headers.
_SDK_ENV = (
    "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL", "ANTHROPIC_CUSTOM_HEADERS",
    "ANTHROPIC_PROFILE", "ANTHROPIC_CONFIG_DIR", "ANTHROPIC_FEDERATION_RULE_ID",
    "ANTHROPIC_ORGANIZATION_ID", "ANTHROPIC_SERVICE_ACCOUNT_ID", "ANTHROPIC_IDENTITY_TOKEN",
    "ANTHROPIC_IDENTITY_TOKEN_FILE", "ANTHROPIC_WORKSPACE_ID", BASE_URL_ENV,
)


def _no_network(*args, **kwargs):
    raise AssertionError("a network connection was attempted in an offline test")


@pytest.fixture(autouse=True)
def _offline_clean_env(monkeypatch):
    for name in _SDK_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(socket.socket, "connect", _no_network)
    monkeypatch.setattr(socket.socket, "connect_ex", _no_network)
    monkeypatch.setattr(socket, "create_connection", _no_network)


def _client(tmp_path) -> AnthropicClient:
    # mode "off": nothing is read from or written to any cache directory
    return AnthropicClient(cache=LLMCache(root=tmp_path / "llm_cache", mode="off"))


def _sdk_default_base_url() -> str:
    """The pinned SDK's own default, read from a bare client with no endpoint override."""
    return str(anthropic.Anthropic(api_key=FAKE_KEY).base_url)


def test_default_constant_equals_the_pinned_sdk_default():
    assert str(anthropic.Anthropic(api_key=FAKE_KEY, base_url=DEFAULT_BASE_URL).base_url) \
        == _sdk_default_base_url()
    assert resolve_base_url() == DEFAULT_BASE_URL == "https://api.anthropic.com"


def test_positive_control_the_sdk_itself_inherits_the_host_variable(monkeypatch):
    # Documents the hazard the client guards against: a bare SDK client follows the variable.
    monkeypatch.setenv("ANTHROPIC_BASE_URL", HOST_URL)
    assert anthropic.Anthropic(api_key=FAKE_KEY).base_url.host == "example.invalid"


def test_key_branch_ignores_the_host_base_url(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_BASE_URL", HOST_URL)
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_KEY)
    sdk = _client(tmp_path)._client
    assert sdk.base_url.scheme == "https"
    assert sdk.base_url.host == "api.anthropic.com"
    assert "example.invalid" not in str(sdk.base_url)
    assert sdk.api_key == FAKE_KEY and sdk.auth_token is None


def test_token_branch_ignores_the_host_base_url_and_keeps_the_auth_token(monkeypatch, tmp_path):
    # No ANTHROPIC_API_KEY: the SDK resolves ANTHROPIC_AUTH_TOKEN itself, as before the fix.
    monkeypatch.setenv("ANTHROPIC_BASE_URL", HOST_URL)
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", FAKE_TOKEN)
    sdk = _client(tmp_path)._client
    assert sdk.base_url.host == "api.anthropic.com"
    assert "example.invalid" not in str(sdk.base_url)
    assert sdk.auth_token == FAKE_TOKEN and sdk.api_key is None
    assert sdk.auth_headers == {"Authorization": f"Bearer {FAKE_TOKEN}"}


@pytest.mark.parametrize("cred", ["ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"])
def test_without_any_base_url_variable_the_endpoint_is_the_sdk_default(monkeypatch, tmp_path, cred):
    # Local Windows behaviour outside Claude Code: nothing set, so nothing may change.
    monkeypatch.setenv(cred, FAKE_KEY)
    assert str(_client(tmp_path)._client.base_url) == _sdk_default_base_url()


@pytest.mark.parametrize("cred", ["ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"])
def test_project_variable_wins_in_both_branches(monkeypatch, tmp_path, cred):
    monkeypatch.setenv(cred, FAKE_KEY)
    monkeypatch.setenv("ANTHROPIC_BASE_URL", HOST_URL)
    monkeypatch.setenv(BASE_URL_ENV, "https://proxy.test.invalid:8443")
    url = _client(tmp_path)._client.base_url
    assert (url.scheme, url.host, url.port) == ("https", "proxy.test.invalid", 8443)


@pytest.mark.parametrize("value", ["", "   "])
def test_empty_project_variable_falls_back_to_the_default(monkeypatch, tmp_path, value):
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_KEY)
    monkeypatch.setenv("ANTHROPIC_BASE_URL", HOST_URL)
    monkeypatch.setenv(BASE_URL_ENV, value)
    assert resolve_base_url() == DEFAULT_BASE_URL
    assert _client(tmp_path)._client.base_url.host == "api.anthropic.com"
