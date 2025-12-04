"""Minimal httpx-compatible shim for offline testing.

This is not a full implementation of httpx. It only provides the pieces used
by `starlette.testclient` so that FastAPI's TestClient can operate without
network-installed dependencies. The behavior is intentionally small-scope and
focused on the synchronous client path.
"""

from __future__ import annotations

import json
import io
from dataclasses import dataclass
from http.cookies import SimpleCookie
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Tuple
from urllib.parse import urlencode, urljoin, urlparse

from . import _client


class Headers:
    def __init__(self, headers: Optional[Mapping[str, str]] = None):
        self._store: List[Tuple[str, str]] = []
        if headers:
            for key, value in headers.items():
                self._store.append((key, str(value)))

    def multi_items(self) -> List[Tuple[str, str]]:
        return list(self._store)

    def add(self, key: str, value: str) -> None:
        self._store.append((key, value))

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        key_lower = key.lower()
        for k, v in reversed(self._store):
            if k.lower() == key_lower:
                return v
        return default

    def __getitem__(self, key: str) -> str:
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __contains__(self, key: object) -> bool:
        try:
            return self.get(str(key)) is not None
        except Exception:
            return False

    def __iter__(self):  # pragma: no cover - simple iterator
        return (k for k, _ in self._store)

    def items(self) -> Iterable[Tuple[str, str]]:
        return self._store


@dataclass
class URL:
    raw_url: str

    def __post_init__(self) -> None:
        parsed = urlparse(self.raw_url)
        self.scheme = parsed.scheme or "http"
        self.host = parsed.hostname or ""
        self.port = parsed.port
        self.path = parsed.path or "/"
        self.query = parsed.query.encode()
        self.netloc = parsed.netloc.encode()
        self.raw_path = (parsed.path or "/").encode()

    def __str__(self) -> str:  # pragma: no cover - simple helper
        return self.raw_url


class Request:
    def __init__(
        self,
        method: str,
        url: URL,
        headers: Optional[Mapping[str, str]] = None,
        content: Optional[bytes] = None,
    ) -> None:
        self.method = method.upper()
        self.url = url
        self.headers = Headers(headers)
        self._content = content or b""

    def read(self) -> bytes:
        return self._content


class ByteStream:
    def __init__(self, data: bytes):
        self.data = data

    def read(self) -> bytes:
        return self.data


class Response:
    def __init__(
        self,
        status_code: int = 200,
        headers: Optional[Iterable[Tuple[bytes, bytes]]] = None,
        stream: Optional[io.BytesIO | ByteStream] = None,
        content: Optional[bytes] = None,
        request: Optional[Request] = None,
    ) -> None:
        self.status_code = status_code
        raw_headers = headers or []
        header_map: Dict[str, str] = {}
        for key, value in raw_headers:
            key_str = key.decode() if isinstance(key, (bytes, bytearray)) else str(key)
            val_str = value.decode() if isinstance(value, (bytes, bytearray)) else str(value)
            header_map[key_str.lower()] = val_str
        self.headers = header_map
        self.request = request
        if content is not None:
            self._content = content
        elif stream is not None:
            self._content = stream.read()
        else:
            self._content = b""

    @property
    def text(self) -> str:
        return self._content.decode("utf-8")

    def json(self) -> Any:
        return json.loads(self._content.decode())

    def read(self) -> bytes:
        return self._content


class BaseTransport:
    def handle_request(self, request: Request) -> Response:  # pragma: no cover - interface
        raise NotImplementedError


class Client:
    def __init__(
        self,
        *,
        app: Any = None,
        base_url: str = "http://testserver",
        headers: Optional[Dict[str, str]] = None,
        transport: Optional[BaseTransport] = None,
        follow_redirects: bool = True,
        cookies: Optional[Mapping[str, str]] = None,
    ) -> None:
        self.app = app
        self.base_url = base_url.rstrip("/")
        self._transport = transport
        self.follow_redirects = follow_redirects
        self._default_headers = Headers(headers or {})
        self._cookies: MutableMapping[str, str] = dict(cookies or {})

    # Expose client default sentinel for compatibility
    _client = _client

    def _merge_url(self, url: Any) -> str:
        return self._prepare_url(url)

    def _prepare_url(self, url: Any, params: Optional[Mapping[str, Any]] = None) -> str:
        joined = urljoin(self.base_url + "/", str(url))
        if params:
            query = urlencode(params, doseq=True)
            separator = "&" if urlparse(joined).query else "?"
            joined = f"{joined}{separator}{query}"
        return joined

    def _prepare_headers(self, extra: Optional[Mapping[str, str]]) -> Headers:
        headers = Headers({k: v for k, v in self._default_headers.items()})
        if extra:
            for key, value in extra.items():
                headers.add(key, str(value))
        if self._cookies and headers.get("cookie") is None:
            cookie_value = "; ".join(f"{k}={v}" for k, v in self._cookies.items())
            headers.add("cookie", cookie_value)
        return headers

    def _update_cookies_from_response(self, response: Response) -> None:
        if "set-cookie" not in response.headers:
            return
        cookie = SimpleCookie()
        cookie.load(response.headers["set-cookie"])
        for key, morsel in cookie.items():
            self._cookies[key] = morsel.value

    def request(
        self,
        method: str,
        url: Any,
        *,
        content: Any = None,
        data: Optional[Mapping[str, Any]] = None,
        files: Any = None,
        json: Any = None,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        cookies: Any = None,
        auth: Any = None,
        follow_redirects: bool | None = None,
        timeout: Any = None,
        extensions: Any = None,
    ) -> Response:
        if cookies:
            self._cookies.update({k: str(v) for k, v in cookies.items()})
        final_url = self._prepare_url(url, params)
        body: Optional[bytes] = None
        if json is not None:
            body = json.dumps(json).encode()
            headers = {**(headers or {}), "content-type": "application/json"}
        elif data is not None:
            body = urlencode(data, doseq=True).encode()
            headers = {**(headers or {}), "content-type": "application/x-www-form-urlencoded"}
        elif isinstance(content, (bytes, bytearray)):
            body = bytes(content)
        elif content is None:
            body = b""
        else:
            body = str(content).encode()

        req_headers = self._prepare_headers(headers)
        request = Request(method, URL(final_url), headers={k: v for k, v in req_headers.items()}, content=body)

        if self._transport is None:
            raise RuntimeError("No transport configured for httpx shim")
        response = self._transport.handle_request(request)
        self._update_cookies_from_response(response)

        should_follow = self.follow_redirects if follow_redirects is None else follow_redirects
        redirects_remaining = 5
        while should_follow and response.status_code in {301, 302, 303, 307, 308} and redirects_remaining > 0:
            location = response.headers.get("location")
            if not location:
                break
            redirects_remaining -= 1
            next_method = "GET" if response.status_code == 303 else method
            response = self.request(next_method, location, headers=headers, follow_redirects=False)
        return response

    def get(self, url: Any, **kwargs: Any) -> Response:
        return self.request("GET", url, **kwargs)

    def options(self, url: Any, **kwargs: Any) -> Response:
        return self.request("OPTIONS", url, **kwargs)

    def head(self, url: Any, **kwargs: Any) -> Response:
        return self.request("HEAD", url, **kwargs)

    def post(self, url: Any, **kwargs: Any) -> Response:
        return self.request("POST", url, **kwargs)

    def put(self, url: Any, **kwargs: Any) -> Response:
        return self.request("PUT", url, **kwargs)

    def patch(self, url: Any, **kwargs: Any) -> Response:
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: Any, **kwargs: Any) -> Response:
        return self.request("DELETE", url, **kwargs)


# Convenience re-exports
USE_CLIENT_DEFAULT = _client.USE_CLIENT_DEFAULT

__all__ = [
    "BaseTransport",
    "ByteStream",
    "Client",
    "Headers",
    "Request",
    "Response",
    "URL",
    "USE_CLIENT_DEFAULT",
]
