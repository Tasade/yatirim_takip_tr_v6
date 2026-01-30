from __future__ import annotations

import time
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def build_retry_session(
    retries: int = 3,
    backoff_factor: float = 0.7,
    status_forcelist: tuple[int, ...] = (429, 500, 502, 503, 504),
    timeout_s: int = 10,
) -> requests.Session:
    \"\"\"Requests Session with retry + backoff. Use `request_json` helper.\"\"\"
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        status=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=frozenset(["GET", "POST"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.request_timeout_s = timeout_s  # type: ignore[attr-defined]
    return session

def request_json(session: requests.Session, url: str, **kwargs):
    timeout = kwargs.pop("timeout", getattr(session, "request_timeout_s", 10))
    r = session.get(url, timeout=timeout, **kwargs)
    r.raise_for_status()
    return r.json()
