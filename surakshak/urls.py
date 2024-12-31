from django.urls import path, include
from .views import *

urlpatterns = [
    path("", homepage, name="homepage"),
    path("stream/", stream_page, name="stream_page"),
    path("video_feed/<str:camera_name>/", video_feed, name="video_feed"),
    path("__reload__/", include("django_browser_reload.urls")),
    path("settings/respondents/", respondents_page, name="respondents_page"),
]
