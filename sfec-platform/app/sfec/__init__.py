from ..config import settings
from .base import SfecClient


def get_sfec_client() -> SfecClient:
    if settings.sfec_mode == "http":
        from .http import HttpSfecClient
        return HttpSfecClient()
    from .mock import MockSfecClient
    return MockSfecClient()
