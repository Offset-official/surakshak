from django.urls import path, include
from .views import homepage, stream_page, video_feed

urlpatterns = [
    path("", homepage, name="homepage"),
    path("stream/", stream_page, name="stream_page"),
    path("video_feed/<int:feed_number>/", video_feed, name="video_feed"),
    path("__reload__/", include("django_browser_reload.urls")),
]
