import secrets

from nanolink.domain.short_codes import SHORT_CODE_ALPHABET, SHORT_CODE_LENGTH, is_reserved_short_code


class SecretsShortCodeGenerator:
    def next_code(self) -> str:
        while True:
            candidate = "".join(secrets.choice(SHORT_CODE_ALPHABET) for _ in range(SHORT_CODE_LENGTH))
            if not is_reserved_short_code(candidate):
                return candidate
