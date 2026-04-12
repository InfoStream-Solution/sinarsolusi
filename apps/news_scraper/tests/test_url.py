from __future__ import annotations

from src.utils.url import remove_utm_query_params


def test_remove_utm_query_params_strips_tracking_params_and_fragment() -> None:
    url = (
        "https://example.com/news?a=1&utm_source=newsletter&utm_medium=email"
        "&b=2&utm_campaign=spring#section"
    )

    assert remove_utm_query_params(url) == "https://example.com/news?a=1&b=2#section"
