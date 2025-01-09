from django.urls import path, include
from django.conf import settings as django_settings
from django.conf.urls.static import static


from .views import (
    homepage,
    stream_page,
    video_feed,
    notify_page,
    logs_page,
    settings_page,
    toggle_status,
    notify_api,
    timings_page,
    heartbeat,
    resolve,
    respondents_page,
    add_respondent,
    settings_page,
    incidents,
    camera_adjust,
    single_stream_page,
    camera_page,
    incidents_mapping_page,
    assign_respondent,
    login_page,
    login
)

urlpatterns = [
    path("", login_page , name="login_page"),
    path("auth/", login , name="login"),
    path("home/", homepage, name="homepage"),
    path("streams/", stream_page, name="stream_page"),
    path("notify/", notify_page, name="notify_page"),
    path("logs/", logs_page, name="logs_page"),
    path("settings/", settings_page, name="settings"),
    path("video_feed/<str:camera_name>/", video_feed, name="video_feed"),
    path("toggle-status/", toggle_status, name="toggle_status"),
    path("__reload__/", include("django_browser_reload.urls")),
    path("notify_api/", notify_api, name="notify_api"),
    path("settings/timings", timings_page, name="timings"),
    path("heartbeat", heartbeat, name="heartbeat"),
    path("resolve/<str:incident_id>", resolve, name="resolve"),
    path("settings/respondents/", respondents_page, name="respondents_page"),
    path("settings/add_respondent/", add_respondent, name="add_respondent"),
    path("incidents", incidents, name="incidents"),
    path("camera_adjust", camera_adjust, name="camera_adjust"),
    path('stream/<str:camera_name>/', single_stream_page, name='single_stream_page'),
    path('settings/camera_page', camera_page, name='camera_page'),
    path('settings/incidents_mapping', incidents_mapping_page, name='incidents_mapping_page'),
    path('settings/assign_respondent/', assign_respondent, name='assign_respondent')
    
] + static(django_settings.MEDIA_URL, document_root=django_settings.MEDIA_ROOT)
