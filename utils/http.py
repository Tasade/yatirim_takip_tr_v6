from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@dataclass
class _SessionWithTimeout(requests.Session):
    request_timeout_s: int = 10


def build_retry_session(
    timeout_s: int = 10,
    total_retries: int = 3,
    backoff_factor: float = 0.8,
    status_forcelist: Optional[tuple[int, ...]] = (429, 500, 502, 503, 504),
) -> requests.Session:
    s = _SessionWithTimeout()
    s.request_timeout_s = timeout_s

    retry = Retry(
        total=total_retries,
        connect=total_retries,
        read=total_retries,
        status=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=frozenset(["GET", "POST"]),
        raise_on_status=False,
        respect_retry_after_header=True,
    )

    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
    s.mount("http://", adapter)
    s.mount("https://", adapter)

    s.headers.update(
        {
            "User-Agent": "YatirimTakipTR/6",
            "Accept": "application/json,text/plain,*/*",
        }
    )
    return s
