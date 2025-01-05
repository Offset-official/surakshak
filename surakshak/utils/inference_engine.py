import logging
import cv2
import imutils
import numpy as np
from surakshak.utils.camera_manager import VideoCamera
import threading 
from surakshak.utils.models.surakshak_yolo import infer_yolo
from django.conf import settings
import uuid
import time 

logger = logging.getLogger("inference")

def frame_generator(camera: VideoCamera):
    """
    Generator that yields frames from a VideoCamera object.
    
    :param camera: A VideoCamera instance.
    """
    while True:
        frame = camera.get_frame()
        if frame is not None:
            yield cv2.imdecode(np.frombuffer(frame, np.uint8), -1)
        else:
            yield None

def intrusion_detector(frame):
    """
    Placeholder for your custom model or processing routine.
    This function will be called whenever motion is detected.
    """
    logger.info("Running yolo on suspicious frame...")
    output_image, outputs = infer_yolo(frame)
    human_detected = False
    for output in outputs:
        if output["object"] == "person":
            human_detected = True
            break
    if human_detected:
        logger.critical("Human detected! Entering Intrusion Mode.")
        output_image_name = str(uuid.uuid4()) + ".jpg"
        cv2.imwrite(settings.MEDIA_ROOT / output_image_name, output_image)

        # save image somewhere
        # start recording 5s clip of incident
        # create incident in database with image reference and intrusion details
        # ask all cameras to stop inference for some time
        # system should enter a lockdown mode
        # once lockdown mode is over, return to normal operation
    

def motion_detector(
    frame_generator,
    camera_name,
    MIN_SIZE_FOR_MOVEMENT=2000
):
    """
    Detect motion by comparing consecutive frames from a generator.
    If motion is detected, run another model.
    
    :param frame_generator: An iterable (generator) that yields frames (numpy arrays).
    :param MIN_SIZE_FOR_MOVEMENT: Minimum contour area to consider valid movement.
    """

    prev_frame = None  # Will store the previous frame

    for idx, current_frame in enumerate(frame_generator):
        # If the generator yields None or fails to read a frame, skip
        if current_frame is None:
            logger.warning(f"Received an empty frame at index {idx}.")
            continue

        # Convert current frame to grayscale and blur to reduce noise
        gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        # If there's no previous frame yet, set it and move on
        if prev_frame is None:
            prev_frame = gray
            continue

        # Compare previous and current frames to detect motion
        frame_delta = cv2.absdiff(prev_frame, gray)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)

        # Find contours in the thresholded image
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Flag to track if motion is detected in this frame
        motion_detected = False

        for c in contours:
            if cv2.contourArea(c) > MIN_SIZE_FOR_MOVEMENT:
                motion_detected = True
                break  # No need to check other contours once movement is found

        # If motion is detected, call another model (inference, etc.)
        if motion_detected:
            # logger.info(f"Frame {idx}: Motion detected. Camera {camera_name}")
            # should we also save all instances where motion was detected?
            intrusion_detector(current_frame)
        prev_frame = gray

    logger.info("Motion detection ended.")

class CameraInferenceEngine:
    def __init__(self, camera, name):
        self.camera = camera
        self.name = name
        self.thread = threading.Thread(target=self.infer_frames, daemon=True, name="Camera IE " + camera.name)
        self.params = []
        self.thread.start()
    
    def infer_frames(self):
        time.sleep(5)
        motion_detector(frame_generator(self.camera), self.name)

class InferenceEngine:
    camera_inference_engines = []

    @classmethod
    def start(cls):
        from surakshak.utils.camera_manager import CameraManager
        for items in list(CameraManager._cameras.items()):
            name, camera = items
            camera_inference_engine = CameraInferenceEngine(camera, name)
            cls.camera_inference_engines.append(camera_inference_engine)
        