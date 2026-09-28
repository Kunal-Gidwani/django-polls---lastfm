import requests
from django.conf import settings

LASTFM_BASE_URL = "https://ws.audioscrobbler.com/2.0/"


class LastFMError(Exception):
    def __init__(self, message: str, code: int = 0):
        super().__init__(message)
        self.code = code


def call_lastfm(method: str, **params) -> dict:
    api_key = getattr(settings, "LASTFM_API_KEY", "")
    if not api_key:
        raise LastFMError("LASTFM_API_KEY is not configured.", code=0)

    query = {
        "method": method,
        "api_key": api_key,
        "format": "json",
    }
    query.update({k: v for k, v in params.items() if v is not None})

    response = requests.get(LASTFM_BASE_URL, params=query, timeout=10)
    response.raise_for_status()

    data = response.json()

    if "error" in data:
        raise LastFMError(data.get("message", "Last.fm error"), code=data["error"])

    return data
