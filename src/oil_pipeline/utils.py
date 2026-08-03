"""Low-level EBCDIC / packed-decimal decoding helpers for the RRC production tape format."""

RECORD_LENGTH = 102  # bytes; PDF100.ebc fixed physical record length (pda001.pdf)
ENCODING = "cp037"  # assumed IBM EBCDIC code page 037 (US/Canada) — validated in notebooks/01_explore_rrc_production.ipynb

_NEGATIVE_SIGN_NIBBLES = {0xD, 0xB}


def decode_text(field: bytes, encoding: str = ENCODING) -> str:
    """Decode an EBCDIC text/digit field to a Python str."""
    return field.decode(encoding)


def unpack_comp3(field: bytes) -> int:
    """Unpack an IBM COMP-3 (packed decimal) field into a signed int.

    Each byte holds two BCD digits, except the last byte, whose low nibble
    is the sign (C/F = positive, D/B = negative) rather than a digit.
    """
    digits = []
    for byte in field[:-1]:
        digits.append((byte >> 4) & 0xF)
        digits.append(byte & 0xF)
    digits.append((field[-1] >> 4) & 0xF)
    sign_nibble = field[-1] & 0xF

    value = int("".join(str(d) for d in digits))
    return -value if sign_nibble in _NEGATIVE_SIGN_NIBBLES else value
