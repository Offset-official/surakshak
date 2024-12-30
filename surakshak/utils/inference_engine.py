import logging
import cv2
import imutils
import numpy as np
from surakshak.utils.camera_manager import VideoCamera
import threading 

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
    # Example: If you had a function `my_inference_model(frame)`,
    # you could call it here:
    # result = my_inference_model(frame)
    # logging.info("Model output: %s", result)
    pass

def motion_detector(
    frame_generator,
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
            logger.info(f"Frame {idx}: Motion detected.")
            intrusion_detector(current_frame)
        # else:
        #     logging.info(f"Frame {idx}: No motion detected.")

        # Update previous frame
        prev_frame = gray

    logger.info("Motion detection ended.")

class CameraInferenceEngine:
    def __init__(self, camera):
        self.camera = camera
        self.thread = threading.Thread(target=self.infer_frames, daemon=True, name="Camera IE " + camera.name)
        self.params = []
        self.thread.start()
    
    def infer_frames(self):
        motion_detector(frame_generator(self.camera))

class InferenceEngine:
    camera_inference_engines = []

    @classmethod
    def start(cls):
        # Define your RTSP streams here
        from surakshak.utils.camera_manager import CameraManager
        for camera in list(CameraManager._cameras.values())[:1]:
            camera_inference_engine = CameraInferenceEngine(camera)
            cls.camera_inference_engines.append(camera_inference_engine)
        
    @classmethod
    def infer_frames(cls, frame_generator):
        motion_detector(frame_generator)