import ast
from pathlib import Path

import pytest
from scripts.check_house_rules import comment_violations, docstring_violations, length_violations

from nanolink.entrypoints.settings import (
    MissingSetting,
    creator_settings,
    gateway_settings,
    notifier_settings,
)
from tests.support import report_mismatches

GATEWAY_ENVIRONMENT = {
    "PUBLIC_BASE_URL": "https://nanolink.test",
    "DEMO_RESET_TOKEN": "reset",
    "MONGO_HOST": "mongo",
    "MONGO_DATABASE": "nanolink",
    "MONGO_USERNAME": "gateway",
    "MONGO_GATEWAY_PASSWORD": "mongo-secret",
    "NATS_URL": "nats://queue:4222",
    "NATS_USER": "nanolink",
    "NATS_PASSWORD": "nats-secret",
    "VALKEY_HOST": "cache",
    "VALKEY_PASSWORD": "valkey-secret",
    "OIDC_ISSUER": "https://auth.luppol.com/realms/luppol",
    "OIDC_AUDIENCE": "nanolink",
    "OIDC_JWKS_URL": "https://auth.luppol.com/realms/luppol/protocol/openid-connect/certs",
}


def set_environment(monkeypatch: pytest.MonkeyPatch, values: dict[str, str]) -> None:
    for name, value in values.items():
        monkeypatch.setenv(name, value)


def test_gateway_settings_read_every_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    set_environment(monkeypatch, GATEWAY_ENVIRONMENT)
    settings = gateway_settings()
    assert (settings.port, settings.mongo.port, settings.valkey.port) == (8000, 27017, 6379)
    assert settings.mongo.auth_database == "nanolink"
    assert settings.oidc.audience == "nanolink"


def test_each_missing_variable_is_named(monkeypatch: pytest.MonkeyPatch) -> None:
    mismatches = []
    for missing in GATEWAY_ENVIRONMENT:
        with monkeypatch.context() as scoped:
            set_environment(scoped, GATEWAY_ENVIRONMENT)
            scoped.delenv(missing)
            with pytest.raises(MissingSetting) as raised:
                gateway_settings()
            if missing not in str(raised.value):
                mismatches.append(f"{missing} was not named in {raised.value}")
    report_mismatches(mismatches)


def test_notifier_without_smtp_host_disables_mail(monkeypatch: pytest.MonkeyPatch) -> None:
    set_environment(monkeypatch, GATEWAY_ENVIRONMENT)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    assert notifier_settings().smtp is None


def test_creator_uses_its_own_password(monkeypatch: pytest.MonkeyPatch) -> None:
    set_environment(monkeypatch, {**GATEWAY_ENVIRONMENT, "MONGO_USERNAME": "creator"})
    monkeypatch.setenv("MONGO_CREATOR_PASSWORD", "creator-secret")
    assert creator_settings().mongo.password == "creator-secret"


HOUSE_RULE_CASES = [
    ("clean code", "def add(a: int) -> int:\n    return a + 1\n", 0),
    ("a comment", "x = 1\n# explain\n", 1),
    ("an inline comment", "x = 1  # explain\n", 1),
    ("a hash inside a string is fine", "x = '# not a comment'\n", 0),
    ("a docstring", 'def f() -> None:\n    """Explain."""\n', 1),
    ("a 31-line function", "def f() -> None:\n" + "    x = 1\n" * 30, 1),
]


def test_house_rule_checker() -> None:
    mismatches = []
    for case_id, source, expected in HOUSE_RULE_CASES:
        path, tree = Path("case.py"), ast.parse(source)
        found = [
            *comment_violations(path, source),
            *docstring_violations(path, tree),
            *length_violations(path, tree),
        ]
        if len(found) != expected:
            mismatches.append(f"{case_id}: expected {expected} violations, got {found}")
    report_mismatches(mismatches)
