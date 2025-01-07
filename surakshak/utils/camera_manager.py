import cv2
import threading
import time
import logging
import os 
from surakshak.utils.logs import MyHandler

logger = logging.getLogger("camera")
logger.addHandler(MyHandler())

class VideoCamera:
    def __init__(self, rtsp_url, name):
        self.rtsp_url = rtsp_url
        self.video = cv2.VideoCapture(self.rtsp_url)
        self.lock = threading.Lock()
        self.name = name
        self.frame = None
        self._running = True
        self.thread = threading.Thread(target=self.update, daemon=True, name=name)
        self.thread.start()

    def update(self): # updates as frames arrive
        while self._running:
            if not self.video.isOpened():
                logger.info(f"Attempting to reconnect to {self.rtsp_url}")
                self.video = cv2.VideoCapture(self.rtsp_url)
                time.sleep(5)  # Wait before retrying

            ret, image = self.video.read() # this will wait till next frame
            if ret:
                with self.lock:
                    self.frame = image
                time.sleep(0.1) # limits to 10 FPS
            else:
                logger.info(f"Failed to read frame from {self.rtsp_url}")
                self.video.release()
                time.sleep(5)  # Wait before retrying

    def get_frame(self):
        with self.lock:
            if self.frame is None:
                return None
            ret, jpeg = cv2.imencode('.jpg', self.frame)
            if ret:
                return jpeg.tobytes()
            return None

    def stop(self):
        self._running = False
        self.thread.join()
        self.video.release()


class CameraManager:
    _cameras = {}
    os.environ['OPENCV_FFMPEG_LOGLEVEL'] = "0"
    @classmethod
    def add_camera(cls, name, rtsp_url):
        if name in cls._cameras:
            logger.info(f"Camera {name} already exists.")
            return
        cls._cameras[name] = VideoCamera(rtsp_url, name)
        logger.info(f"Camera {name} added and started.")

    @classmethod
    def get_camera(cls, name):
        return cls._cameras.get(name, None)

    @classmethod
    def remove_camera(cls, name):
        camera = cls._cameras.pop(name, None)
        if camera:
            camera.stop()
            logger.info(f"Camera {name} stopped and removed.")

    @classmethod
    def stop_all(cls):
        for name, camera in cls._cameras.items():
            camera.stop()
            logger.info(f"Camera {name} stopped.")
        cls._cameras.clear()
