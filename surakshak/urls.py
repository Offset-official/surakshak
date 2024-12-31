from django.urls import path, include
from .views import *

urlpatterns = [
    path("", homepage, name="homepage"),
    path("stream/", stream_page, name="stream_page"),
    path("video_feed/<str:camera_name>/", video_feed, name="video_feed"),
    path("__reload__/", include("django_browser_reload.urls")),
    path("settings/respondents/", respondents_page, name="respondents_page"),
    path("settings/respondents/add/", respondent_reg_page, name="respondent_reg_page"),
    path("settings/respondents/add/add_respondent/", add_respondent, name="add_respondent"),
]
