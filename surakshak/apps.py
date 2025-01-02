from django.apps import AppConfig
from surakshak.utils.camera_manager import CameraManager
from surakshak.utils.inference_engine import InferenceEngine
import threading
import os
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class SurakshakConfig(AppConfig):
    name = "surakshak"

    def ready(self):
        # Prevent multiple initializations in multi-worker setups
        import sys

        if os.environ.get("RUN_MAIN") != "true":
            return
        if "runserver" not in sys.argv and "test" not in sys.argv:
            return

        # Define your RTSP streams here
        from .models import Camera

        cameras = Camera.objects.all()
        streams = []
        for camera in cameras:
            stream = {"name": camera.name, "url": camera.rtsp_url}
            streams.append(stream)

        def initialize_cameras():
            for stream in streams:
                CameraManager.add_camera(stream["name"], stream["url"])
                # each camera is running in a separate thread
            print("All camera fetchers started.")

        def start_inference_engine():
            # print('Starting inference engine')
            InferenceEngine.start()
            # inference for each camera will be in a separate thread

        # initialize_cameras()
        if getattr(settings, "INFERENCE_ENGINE", False):
            logger.info("Starting inference engine")
            start_inference_engine()
