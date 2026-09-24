from dataclasses import dataclass

from nanolink.domain import long_urls
from nanolink.domain.long_urls import long_url_problem
from tests.support import report_mismatches


@dataclass(frozen=True)
class Case:
    id: str
    candidate: str
    expected: str | None


CASES = [
    Case("https with path, query and fragment", "https://example.com/a/b?c=d#e", None),
    Case("http with a port", "http://example.com:8080/", None),
    Case("subdomain and trailing dot", "https://docs.python.org./3/", None),
    Case("internationalised domain", "https://пример.рф/страница", None),
    Case("public IPv4 address", "http://8.8.8.8/dns", None),
    Case("public IPv6 address", "http://[2001:4860:4860::8888]/", None),
    Case("empty", "", long_urls.EMPTY),
    Case("longer than 2048 characters", "https://example.com/" + "a" * 2029, long_urls.TOO_LONG),
    Case("exactly 2048 characters", "https://example.com/" + "a" * 2028, None),
    Case("space inside", "https://exa mple.com/", long_urls.UNPRINTABLE),
    Case("newline at the end", "https://example.com/\n", long_urls.UNPRINTABLE),
    Case("ftp scheme", "ftp://example.com/file", long_urls.UNSUPPORTED_SCHEME),
    Case("javascript scheme", "javascript:alert(1)", long_urls.UNSUPPORTED_SCHEME),
    Case("no scheme", "example.com/path", long_urls.UNSUPPORTED_SCHEME),
    Case("user and password", "https://user:secret@example.com/", long_urls.EMBEDDED_CREDENTIALS),
    Case("port out of range", "https://example.com:99999/", long_urls.INVALID_PORT),
    Case("no host", "https:///path", long_urls.MISSING_HOST),
    Case("broken IPv6 literal", "http://[::1/", long_urls.UNPARSABLE),
    Case("localhost", "http://localhost:8080/", long_urls.NOT_A_PUBLIC_DOMAIN),
    Case("compose service name", "http://mongo:27017/", long_urls.NOT_A_PUBLIC_DOMAIN),
    Case("localhost subdomain", "http://api.localhost/", long_urls.PRIVATE_DOMAIN),
    Case("internal top-level domain", "https://keycloak.internal/admin", long_urls.PRIVATE_DOMAIN),
    Case("home.arpa", "http://router.home.arpa/", long_urls.PRIVATE_DOMAIN),
    Case("private IPv4", "http://192.168.1.1/", long_urls.NON_PUBLIC_ADDRESS),
    Case("loopback IPv4", "http://127.0.0.1:8000/", long_urls.NON_PUBLIC_ADDRESS),
    Case("cloud metadata address", "http://169.254.169.254/latest/meta-data", long_urls.NON_PUBLIC_ADDRESS),
    Case("carrier-grade NAT", "http://100.64.0.1/", long_urls.NON_PUBLIC_ADDRESS),
    Case("docker bridge", "http://172.30.10.3:8080/", long_urls.NON_PUBLIC_ADDRESS),
    Case("unspecified address", "http://0.0.0.0/", long_urls.NON_PUBLIC_ADDRESS),
    Case("loopback IPv6", "http://[::1]/", long_urls.NON_PUBLIC_ADDRESS),
    Case("IPv4-mapped loopback", "http://[::ffff:127.0.0.1]/", long_urls.NON_PUBLIC_ADDRESS),
    Case("decimal IPv4 form", "http://2130706433/", long_urls.UNSUPPORTED_ADDRESS_FORM),
    Case("shortened IPv4 form", "http://127.1/", long_urls.UNSUPPORTED_ADDRESS_FORM),
    Case("hexadecimal IPv4 form", "http://0x7f.0.0.1/", long_urls.UNSUPPORTED_ADDRESS_FORM),
    Case("label with underscore", "https://bad_host.example.com/", long_urls.INVALID_DOMAIN),
    Case("label starting with a hyphen", "https://-bad.example.com/", long_urls.INVALID_DOMAIN),
]


def test_every_long_url_rule_holds() -> None:
    mismatches = [
        f"{case.id}: expected {case.expected!r}, got {actual!r}"
        for case in CASES
        if (actual := long_url_problem(case.candidate)) != case.expected
    ]
    report_mismatches(mismatches)
