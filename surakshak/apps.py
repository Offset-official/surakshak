from django.apps import AppConfig
from surakshak.utils.camera_manager import CameraManager
import threading
import os 
import logging 


logger = logging.getLogger(__name__)
class SurakshakConfig(AppConfig):
    name = 'surakshak'
    def ready(self):
        # Prevent multiple initializations in multi-worker setups
        import sys
        if os.environ.get('RUN_MAIN') != 'true':
            return
        if 'runserver' not in sys.argv and 'test' not in sys.argv:
            return

        # Define your RTSP streams here
        from .models import Camera
        cameras = Camera.objects.all()
        streams = []
        for camera in cameras:
            stream = {
                'name': camera.name,
                'url': camera.rtsp_url
            }
            streams.append(stream)

        # Start a separate thread to manage camera initialization
        def initialize_cameras():
            for stream in streams:
                CameraManager.add_camera(stream['name'], stream['url'])

            print('All camera fetchers started.')

        # Start the initialization in a separate thread to avoid blocking
        init_thread = threading.Thread(target=initialize_cameras, daemon=True)
        init_thread.start()
