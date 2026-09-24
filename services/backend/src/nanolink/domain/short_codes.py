import re
import string

from nanolink.domain.sandbox import DEMO_SEED_CODES

SHORT_CODE_ALPHABET = string.digits + string.ascii_letters
SHORT_CODE_LENGTH = 6
ROUTE_SHORT_CODES = frozenset({"assets", "oauth2", "readyz"})
RESERVED_SHORT_CODES = ROUTE_SHORT_CODES | DEMO_SEED_CODES

_SHORT_CODE_PATTERN = re.compile(f"[0-9A-Za-z]{{{SHORT_CODE_LENGTH}}}")


def is_short_code(candidate: str) -> bool:
    return _SHORT_CODE_PATTERN.fullmatch(candidate) is not None


def is_reserved_short_code(candidate: str) -> bool:
    return candidate in RESERVED_SHORT_CODES
