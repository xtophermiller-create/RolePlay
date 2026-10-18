from __future__ import annotations

import string
from .result import Result, Ok, Err, Severity

PUNCTUATION = string.punctuation.replace('.', '').replace('-', '')
WHITESPACE = string.whitespace.replace(' ', '')


def check_punctuation(
        *,
        value: str | None = None
) -> Result:
    if not isinstance(value, str):
        return Err(meta='value is not a string', severity=Severity.INFO)
    for x in PUNCTUATION:
        if x in value:
            return Err(meta='value has the punctuation', severity=Severity.INFO)
    return Ok()

def check_whitespace(
        *,
        value: str | None = None
) -> Result:
    if not isinstance(value, str):
        return Err(meta='value is not a string', severity=Severity.INFO)
    for x in WHITESPACE:
        if x in value:
            return Err(meta='value has the whitespace', severity=Severity.INFO)
    return Ok()