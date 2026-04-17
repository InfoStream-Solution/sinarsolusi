from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse


def remove_utm_query_params(url: str) -> str:
    """Return `url` without UTM-style tracking query parameters."""

    parsed = urlparse(url)
    query_items = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.startswith("utm_")
    ]
    query = urlencode(query_items, doseq=True)
    return parsed._replace(query=query).geturl()
