from django.apps import AppConfig
from surakshak.utils.camera_manager import CameraManager
from surakshak.utils.inference_engine import InferenceEngine
from surakshak.utils.system_config import SystemConfig
from surakshak.utils.logs import MyHandler
import threading
import os
import logging
from django.conf import settings
import datetime
from dotenv import load_dotenv


logger = logging.getLogger(__name__)
logger.addHandler(MyHandler())


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

        initialize_cameras()

        from .models import IncidentType

        if IncidentType.objects.all().count() == 0:
            IncidentType.objects.create(type_name="Trespassing")

        from .models import InferenceSchedule

        if InferenceSchedule.objects.all().count() == 0:
            InferenceSchedule.objects.create(
                start_time="06:00",
                end_time="15:00",
                monday=True,
                tuesday=True,
                wednesday=True,
                thursday=True,
                friday=True,
                saturday=False,
                sunday=False,
            )

        # set intrusion state
        from .models import InferenceSchedule

        time_now = datetime.datetime.now()
        hour_now = time_now.hour
        min_now = time_now.minute
        inactive_schedule = InferenceSchedule.objects.get(pk=1)
        # print(inactive_schedule)
        today_weekday = time_now.weekday()
        mappings = {
            0: "monday",
            1: "tuesday",
            2: "wednesday",
            3: "thursday",
            4: "friday",
            5: "saturday",
            6: "sunday",
        }
        # check if day matches
        if getattr(inactive_schedule, mappings[today_weekday]):

            inactive_schdule_start_time = inactive_schedule.start_time
            inactive_schedule_start_hour = inactive_schdule_start_time.hour
            inactive_schedule_start_min = inactive_schdule_start_time.minute
            inactive_schdule_end_time = inactive_schedule.end_time
            inactive_schdule_end_hour = inactive_schdule_end_time.hour
            inactive_schdule_end_min = inactive_schdule_end_time.minute
            if (
                (inactive_schedule_start_hour, inactive_schedule_start_min)
                < (hour_now, min_now)
                < (inactive_schdule_end_hour, inactive_schdule_end_min)
            ):
                logger.info("Starting system with INACTIVE mode.")

                SystemConfig.set_intrusion("INACTIVE")
                # InferenceEngine.stop() # does nothing, for completeness
            else:
                logger.info("Starting system with ACTIVE mode.")  # school is closed
                SystemConfig.set_intrusion("ACTIVE")
                InferenceEngine.start()

        else:
            logger.info("Starting system with ACTIVE mode.")  # school is closed
            SystemConfig.set_intrusion("ACTIVE")
            InferenceEngine.start()

        # if getattr(settings, "INFERENCE_ENGINE", False):
        #     logger.info("Starting inference engine")
        #     InferenceEngine.start()
        logger.info("Loading environment variables...")
        load_dotenv()
        SystemConfig.start_state_switch(InferenceSchedule)
