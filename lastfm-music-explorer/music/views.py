import math
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from django.http import JsonResponse
from django.shortcuts import render

from .lastfm import LastFMError, call_lastfm

CHART_PAGE_SIZE = 20
SEARCH_PAGE_SIZE = 20
SEARCH_MIN_LENGTH = 4
GENRE_PAGE_SIZE = 10
GENRE_COUNTRY_SCAN_LIMIT = 60


def index(request):
    return render(request, "music/index.html")


def _parse_page(request) -> int:
    try:
        page = int(request.GET.get("page", 1))
        return max(page, 1)
    except (ValueError, TypeError):
        return 1


def _error(msg: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"error": msg}, status=status)


def _lastfm_error_response(exc: Exception) -> JsonResponse:
    if isinstance(exc, LastFMError):
        return JsonResponse({"error": str(exc), "code": exc.code}, status=502)
    if isinstance(exc, requests.RequestException):
        return JsonResponse({"error": "Could not reach Last.fm. Try again later."}, status=502)
    return JsonResponse({"error": "Unexpected error."}, status=500)


def top_artists(request):
    country = request.GET.get("country", "").strip()
    if not country:
        return _error("'country' query parameter is required.")

    page = _parse_page(request)

    try:
        data = call_lastfm(
            "geo.getTopArtists",
            country=country,
            limit=CHART_PAGE_SIZE,
            page=page,
        )
    except Exception as exc:
        return _lastfm_error_response(exc)

    attrs = data.get("topartists", {}).get("@attr", {})
    artists = data.get("topartists", {}).get("artist", [])

    return JsonResponse({
        "country": attrs.get("country", country),
        "page": int(attrs.get("page", page)),
        "per_page": CHART_PAGE_SIZE,
        "total_pages": int(attrs.get("totalPages", 1)),
        "total": int(attrs.get("total", 0)),
        "artists": [
            {
                "rank": int(a.get("@attr", {}).get("rank", i + 1)),
                "name": a.get("name"),
                "listeners": int(a.get("listeners", 0)),
                "url": a.get("url"),
            }
            for i, a in enumerate(artists)
        ],
    })


def top_tracks(request):
    country = request.GET.get("country", "").strip()
    if not country:
        return _error("'country' query parameter is required.")

    page = _parse_page(request)

    try:
        data = call_lastfm(
            "geo.getTopTracks",
            country=country,
            limit=CHART_PAGE_SIZE,
            page=page,
        )
    except Exception as exc:
        return _lastfm_error_response(exc)

    attrs = data.get("tracks", {}).get("@attr", {})
    tracks = data.get("tracks", {}).get("track", [])

    return JsonResponse({
        "country": attrs.get("country", country),
        "page": int(attrs.get("page", page)),
        "per_page": CHART_PAGE_SIZE,
        "total_pages": int(attrs.get("totalPages", 1)),
        "total": int(attrs.get("total", 0)),
        "tracks": [
            {
                "rank": int(t.get("@attr", {}).get("rank", i + 1)),
                "name": t.get("name"),
                "artist": t.get("artist", {}).get("name") if isinstance(t.get("artist"), dict) else t.get("artist"),
                "listeners": int(t.get("listeners", 0)),
                "url": t.get("url"),
            }
            for i, t in enumerate(tracks)
        ],
    })


def _search_view(request, lastfm_method: str, param_name: str, result_key: str, items_key: str):
    q = request.GET.get("q", "").strip()
    if not q:
        return _error("'q' query parameter is required.")
    if len(q) < SEARCH_MIN_LENGTH:
        return _error(f"'q' must be at least {SEARCH_MIN_LENGTH} characters.")

    page = _parse_page(request)

    try:
        data = call_lastfm(
            lastfm_method,
            **{param_name: q},
            limit=SEARCH_PAGE_SIZE,
            page=page,
        )
    except Exception as exc:
        return _lastfm_error_response(exc)

    results = data.get(result_key, {})
    opensearch_total = results.get("opensearch:totalResults", 0)
    items_container = results.get(items_key, {})

    item_key = list(items_container.keys())[0] if items_container else None
    items = items_container.get(item_key, []) if item_key else []
    if isinstance(items, dict):
        items = [items]

    cleaned = []
    for item in items:
        entry = {
            "name": item.get("name"),
            "url": item.get("url"),
        }
        if "listeners" in item:
            entry["listeners"] = item.get("listeners")
        if "artist" in item:
            artist = item.get("artist")
            entry["artist"] = artist.get("name") if isinstance(artist, dict) else artist
        cleaned.append(entry)

    return JsonResponse({
        "query": q,
        "page": page,
        "per_page": SEARCH_PAGE_SIZE,
        "total": int(opensearch_total),
        "results": cleaned,
    })


def search_artists(request):
    return _search_view(
        request,
        lastfm_method="artist.search",
        param_name="artist",
        result_key="results",
        items_key="artistmatches",
    )


def search_albums(request):
    return _search_view(
        request,
        lastfm_method="album.search",
        param_name="album",
        result_key="results",
        items_key="albummatches",
    )


def search_tracks(request):
    return _search_view(
        request,
        lastfm_method="track.search",
        param_name="track",
        result_key="results",
        items_key="trackmatches",
    )


def _artist_matches_genre(artist: dict, genre_lower: str) -> bool:
    artist_name = artist.get("name", "")
    if not artist_name:
        return False
    try:
        tag_data = call_lastfm("artist.getTopTags", artist=artist_name)
    except Exception:
        return False

    tags = tag_data.get("toptags", {}).get("tag", [])
    if isinstance(tags, dict):
        tags = [tags]
    tag_names = [t.get("name", "").lower() for t in tags]
    return any(genre_lower in name for name in tag_names)


def genre_artists(request):
    genre = request.GET.get("genre", "").strip()
    if not genre:
        return _error("'genre' query parameter is required.")

    country = request.GET.get("country", "").strip()
    page = _parse_page(request)

    if not country:
        try:
            data = call_lastfm(
                "tag.getTopArtists",
                tag=genre,
                limit=GENRE_PAGE_SIZE,
                page=page,
            )
        except Exception as exc:
            return _lastfm_error_response(exc)

        attrs = data.get("topartists", {}).get("@attr", {})
        artists = data.get("topartists", {}).get("artist", [])

        return JsonResponse({
            "genre": genre,
            "country": None,
            "page": int(attrs.get("page", page)),
            "per_page": GENRE_PAGE_SIZE,
            "total_pages": int(attrs.get("totalPages", 1)),
            "total": int(attrs.get("total", 0)),
            "artists": [
                {
                    "rank": int(a.get("@attr", {}).get("rank", i + 1)),
                    "name": a.get("name"),
                    "url": a.get("url"),
                }
                for i, a in enumerate(artists)
            ],
        })

    try:
        chunk = call_lastfm(
            "geo.getTopArtists",
            country=country,
            limit=GENRE_COUNTRY_SCAN_LIMIT,
            page=1,
        )
    except Exception as exc:
        return _lastfm_error_response(exc)

    all_country_artists = chunk.get("topartists", {}).get("artist", [])
    if isinstance(all_country_artists, dict):
        all_country_artists = [all_country_artists]

    genre_lower = genre.lower()
    matched = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {
            pool.submit(_artist_matches_genre, artist, genre_lower): artist
            for artist in all_country_artists
        }
        for future in as_completed(futures):
            artist = futures[future]
            try:
                if future.result():
                    matched.append(artist)
            except Exception:
                continue

    matched_names = {a.get("name") for a in matched}
    matched = [a for a in all_country_artists if a.get("name") in matched_names]

    total_matched = len(matched)
    start = (page - 1) * GENRE_PAGE_SIZE
    end = start + GENRE_PAGE_SIZE
    page_slice = matched[start:end]
    total_pages = math.ceil(total_matched / GENRE_PAGE_SIZE) if total_matched else 1

    return JsonResponse({
        "genre": genre,
        "country": country,
        "page": page,
        "per_page": GENRE_PAGE_SIZE,
        "total_pages": total_pages,
        "total": total_matched,
        "artists": [
            {
                "rank": int(a.get("@attr", {}).get("rank", i + start + 1)),
                "name": a.get("name"),
                "listeners": int(a.get("listeners", 0)),
                "url": a.get("url"),
            }
            for i, a in enumerate(page_slice)
        ],
    })
