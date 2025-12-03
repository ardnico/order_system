"""Client defaults used by starlette.testclient.

This module mirrors the public constants httpx exposes without pulling in
external dependencies.
"""


class UseClientDefault:
    """Sentinel for parameters that should use the client's configured default."""

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return "USE_CLIENT_DEFAULT"


USE_CLIENT_DEFAULT = UseClientDefault()
