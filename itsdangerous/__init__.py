"""Minimal subset of itsdangerous for session signing.

Provides TimestampSigner and BadSignature used by Starlette's SessionMiddleware.
This implementation uses HMAC-SHA256 and supports optional expiration checks.
"""

from __future__ import annotations

import base64
import hmac
import time
from hashlib import sha256
from typing import Optional

from .exc import BadSignature


class TimestampSigner:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key.encode()

    def _signature(self, value: bytes) -> bytes:
        return hmac.new(self.secret_key, value, sha256).hexdigest().encode()

    def sign(self, value: bytes) -> bytes:
        timestamp = str(int(time.time())).encode()
        sig = self._signature(value)
        payload = b".".join([value, timestamp, sig])
        return base64.b64encode(payload)

    def unsign(self, signed_value: bytes, max_age: Optional[int] = None) -> bytes:
        try:
            decoded = base64.b64decode(signed_value)
            value, timestamp, sig = decoded.rsplit(b".", 2)
        except Exception as exc:  # pragma: no cover - defensive
            raise BadSignature("Malformed signed value") from exc

        if not hmac.compare_digest(sig, self._signature(value)):
            raise BadSignature("Signature mismatch")

        if max_age is not None:
            try:
                ts_int = int(timestamp.decode())
            except ValueError as exc:  # pragma: no cover - defensive
                raise BadSignature("Invalid timestamp") from exc
            if time.time() - ts_int > max_age:
                raise BadSignature("Signature expired")
        return value


__all__ = ["TimestampSigner", "BadSignature"]
