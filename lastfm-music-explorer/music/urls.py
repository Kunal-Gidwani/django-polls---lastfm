from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("top-artists/", views.top_artists, name="top-artists"),
    path("top-tracks/", views.top_tracks, name="top-tracks"),
    path("search/artists/", views.search_artists, name="search-artists"),
    path("search/albums/", views.search_albums, name="search-albums"),
    path("search/tracks/", views.search_tracks, name="search-tracks"),
    path("genre-artists/", views.genre_artists, name="genre-artists"),
]
