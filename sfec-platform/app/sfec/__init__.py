from ..config import settings
from .base import SfecClient


def get_sfec_client() -> SfecClient:
    if settings.sfec_mode == "mock":
        from .mock import MockSfecClient
        return MockSfecClient()
    from .http import BASE_URLS, HttpSfecClient
    if settings.sfec_mode not in BASE_URLS:
        raise ValueError(f"SFEC_MODE invalide : {settings.sfec_mode} (mock, sandbox ou production)")
    return HttpSfecClient(BASE_URLS[settings.sfec_mode], settings.sfec_api_key, settings.sfec_timeout)
