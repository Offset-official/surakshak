from django.shortcuts import render
import threading
import time
import cv2


class VideoCamera:
    def __init__(self, rtsp_url):
        self.rtsp_url = rtsp_url
        self.video = cv2.VideoCapture(self.rtsp_url)
        self.lock = threading.Lock()
        self._running = True

    def __del__(self):
        self.video.release()

    def stop(self):
        self._running = False

    def get_frame(self):
        with self.lock:
            if not self.video.isOpened():
                self.video = cv2.VideoCapture(self.rtsp_url)

            success, image = self.video.read()
            if not success:
                return None

            # Convert to jpg format
            ret, jpeg = cv2.imencode(".jpg", image)
            return jpeg.tobytes()


def gen(camera):
    while camera._running:
        frame = camera.get_frame()
        if frame is not None:
            yield (
                b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n\r\n"
            )
        else:
            time.sleep(0.1)  # Sleep briefly if frame capture failed
