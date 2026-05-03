"""
Judge code generation: 8-char alphanumeric (7 random + 1 checksum), Luhn-mod-32.

Charset excludes 0/O and 1/I/L to avoid ambiguous characters.
"""

import secrets

CHARSET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
CHARSET_LEN = len(CHARSET)
_INDEX = {c: i for i, c in enumerate(CHARSET)}


def _luhn_mod_n_checksum(payload: str) -> str:
    factor = 2
    total = 0
    for ch in reversed(payload):
        addend = factor * _INDEX[ch]
        addend = (addend // CHARSET_LEN) + (addend % CHARSET_LEN)
        total += addend
        factor = 1 if factor == 2 else 2
    remainder = total % CHARSET_LEN
    check_index = (CHARSET_LEN - remainder) % CHARSET_LEN
    return CHARSET[check_index]


def generate_judge_code() -> str:
    """
    Generate a 8-char alphanumeric (7-random, 1 checksum) judge code.
    """
    payload = "".join(secrets.choice(CHARSET) for _ in range(7))
    return payload + _luhn_mod_n_checksum(payload)


def is_valid_judge_code(code: str) -> bool:
    """
    Validate the 8-char alphanumeric judge code.
    """
    code = code.upper().replace("-", "")
    if len(code) != 8:
        return False
    if any(c not in _INDEX for c in code):
        return False
    return _luhn_mod_n_checksum(code[:7]) == code[7]
