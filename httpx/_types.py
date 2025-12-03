"""Lightweight type placeholders for the bundled httpx shim.

These aliases exist only to satisfy starlette.testclient's runtime imports.
"""

from typing import Any

URLTypes = Any
RequestContent = Any
RequestFiles = Any
QueryParamTypes = Any
HeaderTypes = Any
CookieTypes = Any
AuthTypes = Any
TimeoutTypes = Any
