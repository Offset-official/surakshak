import cv2
import threading
import time
import logging

class VideoCamera:
    def __init__(self, rtsp_url):
        self.rtsp_url = rtsp_url
        self.video = cv2.VideoCapture(self.rtsp_url)
        self.lock = threading.Lock()
        self.frame = None
        self._running = True
        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()

    def update(self):
        while self._running:
            if not self.video.isOpened():
                print(f"Attempting to reconnect to {self.rtsp_url}")
                self.video = cv2.VideoCapture(self.rtsp_url)
                time.sleep(5)  # Wait before retrying

            ret, image = self.video.read()
            if ret:
                with self.lock:
                    self.frame = image
            else:
                print(f"Failed to read frame from {self.rtsp_url}")
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

    @classmethod
    def add_camera(cls, name, rtsp_url):
        if name in cls._cameras:
            print(f"Camera {name} already exists.")
            return
        cls._cameras[name] = VideoCamera(rtsp_url)
        print(f"Camera {name} added and started.")

    @classmethod
    def get_camera(cls, name):
        return cls._cameras.get(name, None)

    @classmethod
    def remove_camera(cls, name):
        camera = cls._cameras.pop(name, None)
        if camera:
            camera.stop()
            print(f"Camera {name} stopped and removed.")

    @classmethod
    def stop_all(cls):
        for name, camera in cls._cameras.items():
            camera.stop()
            print(f"Camera {name} stopped.")
        cls._cameras.clear()
