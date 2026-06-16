import re

REDACTION = "[REDACTED]"

_PREFIX_PATTERNS = [
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s]+"),
    re.compile(r"(?i)(password\s*[:=]\s*)[^\s&]+"),
    re.compile(r"(?i)(passwd\s*[:=]\s*)[^\s&]+"),
    re.compile(r"(?i)(token\s*[:=]\s*)[^\s&]+"),
    re.compile(r"(?i)(secret\s*[:=]\s*)[^\s&]+"),
    re.compile(r"(?i)(cookie\s*[:=]\s*)[^\r\n]+"),
]

_FULL_PATTERNS = [
    re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE),
    re.compile(r"(https?://[^\s?]+\?[^\s]*(?:token|secret|auth|key)=[^\s]+)", re.IGNORECASE),
]


def redact_text(value: str) -> str:
    redacted = value
    for pattern in _PREFIX_PATTERNS:
        redacted = pattern.sub(lambda match: f"{match.group(1)}{REDACTION}", redacted)
    for pattern in _FULL_PATTERNS:
        redacted = pattern.sub(REDACTION, redacted)
    return redacted


def redact_lines(lines: list[str]) -> list[str]:
    return [redact_text(line) for line in lines]
