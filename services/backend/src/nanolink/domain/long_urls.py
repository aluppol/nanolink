import ipaddress
import re
from urllib.parse import SplitResult, urlsplit

MAX_LONG_URL_LENGTH = 2048
ALLOWED_SCHEMES = frozenset({"http", "https"})
PRIVATE_TOP_LEVEL_DOMAINS = frozenset(
    {
        "localhost",
        "local",
        "internal",
        "intranet",
        "lan",
        "home",
        "corp",
        "arpa",
        "test",
        "invalid",
        "example",
    }
)

EMPTY = "the URL is empty"
TOO_LONG = f"the URL is longer than {MAX_LONG_URL_LENGTH} characters"
UNPRINTABLE = "the URL contains spaces or control characters"
UNPARSABLE = "the URL cannot be parsed"
UNSUPPORTED_SCHEME = "only http and https URLs can be shortened"
EMBEDDED_CREDENTIALS = "URLs with a user name or password in them are not allowed"
INVALID_PORT = "the URL has an invalid port"
MISSING_HOST = "the URL has no host"
NON_PUBLIC_ADDRESS = "the URL points to a private or reserved network address"
UNSUPPORTED_ADDRESS_FORM = "the host is a numeric address written in an unsupported form"
NOT_A_PUBLIC_DOMAIN = "the host must be a public domain name"
PRIVATE_DOMAIN = "the host belongs to a private or reserved domain"
INVALID_DOMAIN = "the host is not a valid domain name"

_NUMERIC_LABEL = re.compile(r"0x[0-9a-f]*|[0-9]+", re.IGNORECASE)
_DNS_LABEL = re.compile(r"(?!-)[a-z0-9-]{1,63}(?<!-)", re.IGNORECASE)


def long_url_problem(candidate: str) -> str | None:
    text_problem = _text_problem(candidate)
    if text_problem is not None:
        return text_problem
    try:
        parts = urlsplit(candidate)
    except ValueError:
        return UNPARSABLE
    return _parts_problem(parts)


def _text_problem(candidate: str) -> str | None:
    if not candidate:
        return EMPTY
    if len(candidate) > MAX_LONG_URL_LENGTH:
        return TOO_LONG
    if any(character.isspace() or not character.isprintable() for character in candidate):
        return UNPRINTABLE
    return None


def _parts_problem(parts: SplitResult) -> str | None:
    if parts.scheme not in ALLOWED_SCHEMES:
        return UNSUPPORTED_SCHEME
    if "@" in parts.netloc:
        return EMBEDDED_CREDENTIALS
    try:
        host = parts.hostname
        _ = parts.port
    except ValueError:
        return INVALID_PORT
    if not host:
        return MISSING_HOST
    return host_problem(host)


def host_problem(host: str) -> str | None:
    if ":" in host:
        return _address_problem(host)
    labels = host.removesuffix(".").split(".")
    if _NUMERIC_LABEL.fullmatch(labels[-1]):
        return _address_problem(host)
    return _domain_problem(labels)


def _address_problem(host: str) -> str | None:
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return UNSUPPORTED_ADDRESS_FORM
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    return None if address.is_global else NON_PUBLIC_ADDRESS


def _domain_problem(labels: list[str]) -> str | None:
    if len(labels) < 2:
        return NOT_A_PUBLIC_DOMAIN
    if labels[-1].lower() in PRIVATE_TOP_LEVEL_DOMAINS:
        return PRIVATE_DOMAIN
    try:
        ascii_labels = [label.encode("idna").decode("ascii") for label in labels]
    except UnicodeError:
        return INVALID_DOMAIN
    if all(_DNS_LABEL.fullmatch(label) for label in ascii_labels):
        return None
    return INVALID_DOMAIN
