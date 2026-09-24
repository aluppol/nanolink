import os
from dataclasses import dataclass

from nanolink.adapters.email.senders import SmtpSettings
from nanolink.adapters.mongo.connection import MongoSettings
from nanolink.adapters.nats.connection import NatsSettings
from nanolink.adapters.valkey.connection import ValkeySettings

DEFAULT_HTTP_PORT = "8000"


class MissingSetting(SystemExit):
    def __init__(self, name: str) -> None:
        super().__init__(f"missing required environment variable {name}")


def required(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise MissingSetting(name)
    return value


def optional(name: str, default: str) -> str:
    return os.environ.get(name) or default


@dataclass(frozen=True, slots=True)
class OidcSettings:
    issuer: str
    audience: str
    jwks_url: str


@dataclass(frozen=True, slots=True)
class GatewaySettings:
    port: int
    public_base_url: str
    demo_reset_token: str
    mongo: MongoSettings
    nats: NatsSettings
    valkey: ValkeySettings
    oidc: OidcSettings


@dataclass(frozen=True, slots=True)
class CreatorSettings:
    batch_size: int
    batch_wait_seconds: float
    heartbeat_file: str
    mongo: MongoSettings
    nats: NatsSettings


@dataclass(frozen=True, slots=True)
class NotifierSettings:
    port: int
    public_base_url: str
    smtp: SmtpSettings | None
    nats: NatsSettings
    oidc: OidcSettings


@dataclass(frozen=True, slots=True)
class MigrateSettings:
    root_mongo: MongoSettings
    user_passwords: dict[str, str]
    nats: NatsSettings


def log_level() -> str:
    return optional("LOG_LEVEL", "info").upper()


def app_mongo(password_variable: str, app_name: str) -> MongoSettings:
    database = required("MONGO_DATABASE")
    return MongoSettings(
        host=required("MONGO_HOST"),
        port=int(optional("MONGO_PORT", "27017")),
        database=database,
        username=required("MONGO_USERNAME"),
        password=required(password_variable),
        auth_database=database,
        app_name=app_name,
    )


def nats_settings(client_name: str) -> NatsSettings:
    return NatsSettings(
        url=required("NATS_URL"),
        user=required("NATS_USER"),
        password=required("NATS_PASSWORD"),
        client_name=client_name,
    )


def valkey_settings() -> ValkeySettings:
    return ValkeySettings(
        host=required("VALKEY_HOST"),
        port=int(optional("VALKEY_PORT", "6379")),
        password=required("VALKEY_PASSWORD"),
    )


def oidc_settings() -> OidcSettings:
    return OidcSettings(
        issuer=required("OIDC_ISSUER"),
        audience=required("OIDC_AUDIENCE"),
        jwks_url=required("OIDC_JWKS_URL"),
    )


def gateway_settings() -> GatewaySettings:
    return GatewaySettings(
        port=int(optional("PORT", DEFAULT_HTTP_PORT)),
        public_base_url=required("PUBLIC_BASE_URL"),
        demo_reset_token=required("DEMO_RESET_TOKEN"),
        mongo=app_mongo("MONGO_GATEWAY_PASSWORD", "nanolink-gateway"),
        nats=nats_settings("nanolink-gateway"),
        valkey=valkey_settings(),
        oidc=oidc_settings(),
    )


def creator_settings() -> CreatorSettings:
    return CreatorSettings(
        batch_size=int(optional("CREATOR_BATCH_SIZE", "100")),
        batch_wait_seconds=float(optional("CREATOR_BATCH_WAIT_SECONDS", "1.0")),
        heartbeat_file=optional("HEARTBEAT_FILE", "/tmp/creator-heartbeat"),
        mongo=app_mongo("MONGO_CREATOR_PASSWORD", "nanolink-creator"),
        nats=nats_settings("nanolink-creator"),
    )


def notifier_settings() -> NotifierSettings:
    return NotifierSettings(
        port=int(optional("PORT", DEFAULT_HTTP_PORT)),
        public_base_url=required("PUBLIC_BASE_URL"),
        smtp=smtp_settings(),
        nats=nats_settings("nanolink-notifier"),
        oidc=oidc_settings(),
    )


def smtp_settings() -> SmtpSettings | None:
    host = os.environ.get("SMTP_HOST", "")
    if not host:
        return None
    return SmtpSettings(
        host=host,
        port=int(optional("SMTP_PORT", "587")),
        username=os.environ.get("SMTP_USERNAME", ""),
        password=os.environ.get("SMTP_PASSWORD", ""),
        sender=required("SMTP_FROM"),
    )


def migrate_settings() -> MigrateSettings:
    root = MongoSettings(
        host=required("MONGO_HOST"),
        port=int(optional("MONGO_PORT", "27017")),
        database=required("MONGO_DATABASE"),
        username=required("MONGO_INITDB_ROOT_USERNAME"),
        password=required("MONGO_INITDB_ROOT_PASSWORD"),
        auth_database="admin",
        app_name="nanolink-migrate",
    )
    passwords = {
        "gateway": required("MONGO_GATEWAY_PASSWORD"),
        "creator": required("MONGO_CREATOR_PASSWORD"),
        "redirect": required("MONGO_REDIRECT_PASSWORD"),
    }
    return MigrateSettings(root_mongo=root, user_passwords=passwords, nats=nats_settings("nanolink-migrate"))
