import logging
import cv2
import imutils
import numpy as np
from surakshak.utils.camera_manager import VideoCamera
import threading
from surakshak.utils.models.surakshak_yolo import infer_yolo11s
import uuid
import time
import surakshak.utils.system_config as system_config
import surakshak.utils.coordinator_thread as coordinator_thread
from django.core.files.base import ContentFile
from surakshak.utils.logs import MyHandler
import io

logger = logging.getLogger("inference")
logger.addHandler(MyHandler())
lockdown_lock = threading.Lock()


def frame_generator(camera: VideoCamera):
    """Generator that yields frames from a VideoCamera object.

    :param camera: A VideoCamera instance.
    """
    while True:
        frame = camera.get_frame()
        if frame is not None:
            yield cv2.imdecode(np.frombuffer(frame, np.uint8), -1)
        else:
            yield None


def intrusion_detector(frame, camera_name):
    """
    Detects human intrusions in a given frame from a specific camera using the modified YOLO script,
    which already checks boundary coordinates and returns whether lockdown is needed.

    Args:
        frame (numpy.ndarray): The video frame to process (BGR format).
        camera_name (str): The name of the camera from which the frame is captured.
    """
    logger.info("Running YOLO on suspicious frame...")

    # Retrieve the camera instance from the database
    from surakshak.models import Camera

    camera = Camera.objects.filter(name=camera_name).first()

    if not camera:
        logger.error(f"No camera found with name '{camera_name}'.")
        return  # Early exit if camera is not found

    # Convert camera coordinates (if defined) from percentages to ratios in [0..1]
    # If any coordinate is missing, we'll pass None to the inference so it treats it as "no boundary defined."
    if all(
        [
            camera.x1 is not None,
            camera.x2 is not None,
            camera.y1 is not None,
            camera.y2 is not None,
        ]
    ):
        x1_ratio = camera.x1 / 100.0
        x2_ratio = camera.x2 / 100.0
        y1_ratio = camera.y1 / 100.0
        y2_ratio = camera.y2 / 100.0
        logger.debug(
            f"Using camera boundary ratios: x1={x1_ratio}, x2={x2_ratio}, "
            f"y1={y1_ratio}, y2={y2_ratio}"
        )
    else:
        logger.debug(
            "Camera boundary not fully defined. Any detected person triggers lockdown."
        )
        x1_ratio = None
        x2_ratio = None
        y1_ratio = None
        y2_ratio = None

    # Now call the modified YOLO inference, which returns:
    #   (annotated_image, outputs, lockdown_needed)
    # The boundary check is handled inside the YOLO function.
    output_image, outputs, lockdown_needed = infer_yolo11s(
        img=frame,  # or use default if already set in the function
        conf_thres=0.25,
        iou_thres=0.7,
        x1_ratio=x1_ratio,
        x2_ratio=x2_ratio,
        y1_ratio=y1_ratio,
        y2_ratio=y2_ratio,
    )

    # If lockdown is needed, proceed to initiate it
    if lockdown_needed:
        with lockdown_lock:
            # Check if the system is already in lockdown to prevent redundant actions
            if not system_config.SystemConfig.lockdown:
                logger.info(
                    "Lockdown needed. System is not in lockdown. Proceeding to initiate lockdown."
                )

                # Encode the output image to JPEG format
                ret, encoded_image = cv2.imencode(".jpg", output_image)
                if not ret:
                    logger.error("Failed to encode the image for lockdown.")
                    return  # Early exit if encoding fails

                # Create a ContentFile for the image
                image_content = ContentFile(
                    encoded_image.tobytes(), name=f"{uuid.uuid4()}.jpg"
                )

                # Initiate the lockdown process in a separate thread
                logger.debug("Starting CoordinatorThread to handle lockdown.")
                coordinator_thread.CoordinatorThread(
                    system_config.enter_lockdown, camera_name, image_content
                )
            else:
                logger.info("System is already in lockdown. No action taken.")
    else:
        logger.debug("Lockdown not required based on YOLO detections and boundaries.")


def motion_detector(
    frame_generator, camera_name, stop_event, MIN_SIZE_FOR_MOVEMENT=2000
):
    """Detect motion by comparing consecutive frames from a generator.
    If motion is detected, run another model.

    :param frame_generator: An iterable (generator) that yields frames (numpy arrays).
    :param MIN_SIZE_FOR_MOVEMENT: Minimum contour area to consider valid movement.
    """
    prev_frame = None  # Will store the previous frame

    for idx, current_frame in enumerate(frame_generator):
        if stop_event.is_set():
            break
        # If the generator yields None or fails to read a frame, skip
        if current_frame is None:
            # logger.warning(f"Received an empty frame at index {idx}.")
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
        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        # Flag to track if motion is detected in this frame
        motion_detected = False

        for c in contours:
            if cv2.contourArea(c) > MIN_SIZE_FOR_MOVEMENT:
                motion_detected = True
                break  # No need to check other contours once movement is found

        # If motion is detected, call another model (inference, etc.)
        if motion_detected:
            intrusion_detector(current_frame, camera_name)
        prev_frame = gray

    logger.info("Motion detection ended.")


class CameraInferenceEngine:
    def __init__(self, camera, name):
        self.camera = camera
        self.name = name
        self.thread = None  # We'll create the thread later when we start inference
        self.stop_event = threading.Event()  # Event to signal stopping the thread
        self.is_running = False  # State to track if inference is running

    def infer_frames(self):
        """This function runs the motion detector and initiates the inference loop."""
        time.sleep(5)  # Give time for the camera to stabilize
        motion_detector(frame_generator(self.camera), self.name, self.stop_event)

    def start(self):
        """Start the inference thread if not already running."""
        if not self.is_running:
            self.stop_event.clear()  # Reset the stop event
            self.thread = threading.Thread(
                target=self.infer_frames,
                daemon=True,
                name="Camera IE " + self.camera.name,
            )
            self.thread.start()
            self.is_running = True
            # logger.info(f"Inference started for camera: {self.name}")
        # logger.warning(f"Inference already running for camera: {self.name}")

    def stop(self):
        """Stop the inference thread if running."""
        if self.is_running:
            self.stop_event.set()  # Signal the thread to stop
            self.thread.join()  # Wait for the thread to finish
            self.is_running = False
            # logger.info(f"Inference stopped for camera: {self.name}")

    def toggle(self):
        """Toggle between starting and stopping the inference."""
        if self.is_running:
            self.stop()
        else:
            self.start()


class InferenceEngine:
    camera_inference_engines = []
    first_init = True

    @classmethod
    def start(cls):
        from surakshak.utils.camera_manager import CameraManager

        if cls.first_init:
            # Initialize the camera inference engines for all cameras
            for items in list(CameraManager._cameras.items()):
                name, camera = items
                camera_inference_engine = CameraInferenceEngine(camera, name)
                cls.camera_inference_engines.append(camera_inference_engine)
            cls.first_init = False

        for engine in cls.camera_inference_engines:
            engine.start()
        logger.info("All inference engines started.")

    @classmethod
    def stop(cls):
        """Stop all camera inference engines if they are running."""
        # logger.info("Stopping all inference engines...")
        for engine in cls.camera_inference_engines:
            engine.stop()
        logger.info("All inference engines stopped.")

    @classmethod
    def toggle(cls, camera_name=None):
        """Toggle the inference for a specific camera or for all cameras."""
        if camera_name:
            # Find the camera inference engine by name and toggle it
            engine = next(
                (e for e in cls.camera_inference_engines if e.name == camera_name), None
            )
            if engine:
                engine.toggle()
                # logger.info(f"Toggled inference for camera: {camera_name}")
            else:
                logger.warning(f"Camera {camera_name} not found.")
        else:
            # Toggle all cameras
            for engine in cls.camera_inference_engines:
                engine.toggle()
            logger.info("Toggled inference for all cameras.")
