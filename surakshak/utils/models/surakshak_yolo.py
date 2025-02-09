import cv2
import numpy as np
import logging
from ultralytics import YOLO
from django.conf import settings
from surakshak.utils.logs import MyHandler

logger = logging.getLogger("inference")
logger.addHandler(MyHandler())

# Path to your exported OpenVINO model (.xml); the .bin must be in the same folder
MODEL_PATH = settings.BASE_DIR / "surakshak/utils/models/yolo11s_openvino_model"


class YOLO11sOpenVINO:
    """
    YOLOv8-based custom model (yolo11s) + OpenVINO inference class, using the Ultralytics library.
    Incorporates optional boundary checks for 'person' detections.
    """

    def __init__(self, openvino_model, input_image, confidence_thres, iou_thres,
                 x1_ratio=None, x2_ratio=None, y1_ratio=None, y2_ratio=None):
        """
        Args:
            openvino_model (str or Path): Path to the OpenVINO .xml file.
            input_image (numpy.ndarray): BGR image array (as read by OpenCV).
            confidence_thres (float): Minimum confidence score threshold.
            iou_thres (float): IoU threshold for NMS.
            x1_ratio, x2_ratio, y1_ratio, y2_ratio (float | None):
                Optional boundary coordinates in [0,1] range indicating the 'allowed' or
                'restricted' region. If None, the boundary is not used.
        """
        self.model_path = str(openvino_model)
        self.img = input_image  # BGR image
        self.conf_thres = confidence_thres
        self.iou_thres = iou_thres

        # Optional bounding region (None means not defined)
        self.x1_ratio = x1_ratio
        self.x2_ratio = x2_ratio
        self.y1_ratio = y1_ratio
        self.y2_ratio = y2_ratio

        # Load the Ultralytics YOLO model (OpenVINO format).
        self.model = YOLO(self.model_path)

        # The model has a .names attribute containing class names.
        self.class_names = self.model.names

        # Generate random colors for each class (optional for drawing).
        self.color_palette = np.random.uniform(0, 255, size=(len(self.class_names), 3))

    def draw_detection(self, image, box, score, class_id):
        """
        Draws a bounding box and label on the image.
        box is [x1, y1, x2, y2] in pixel coordinates.
        """
        x1, y1, x2, y2 = map(int, box)
        color = self.color_palette[class_id]

        # Draw bounding box
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)

        # Create a label
        label_text = f"{self.class_names[class_id]}: {score:.2f}"
        (text_w, text_h), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)

        # Position label above the box
        label_y = max(y1 - 10, text_h + 10)

        # Draw filled rectangle for the label background
        cv2.rectangle(
            image,
            (x1, label_y - text_h),
            (x1 + text_w, label_y),
            color,
            cv2.FILLED
        )
        # Put the label text
        cv2.putText(image, label_text, (x1, label_y - 3),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

    def is_within_boundary(self, coords_ratio):
        """
        Checks whether the given detection's center is within the (x1, y1, x2, y2) ratio boundary,
        if the boundary is defined. If boundary coords are None, returns True (meaning no boundary).
        """
        # If any boundary coordinate is None, treat it as "no boundary defined"
        if any(
            b is None
            for b in [self.x1_ratio, self.x2_ratio, self.y1_ratio, self.y2_ratio]
        ):
            # No boundary is defined; return True => detection "counts" globally
            return True

        # Otherwise, check if center is inside the boundary
        human_center_x = (coords_ratio["x1"] + coords_ratio["x2"]) / 2
        human_center_y = (coords_ratio["y1"] + coords_ratio["y2"]) / 2

        within_x = self.x1_ratio <= human_center_x <= self.x2_ratio
        within_y = self.y1_ratio <= human_center_y <= self.y2_ratio

        if within_x and within_y:
            logger.debug(
                f"Human center at ({human_center_x:.2f}, {human_center_y:.2f}) "
                f"is within boundary [{self.x1_ratio}, {self.x2_ratio}, {self.y1_ratio}, {self.y2_ratio}]."
            )
            return True
        else:
            logger.debug(
                f"Human center at ({human_center_x:.2f}, {human_center_y:.2f}) "
                f"is OUTSIDE boundary [{self.x1_ratio}, {self.x2_ratio}, {self.y1_ratio}, {self.y2_ratio}]."
            )
            return False

    def infer(self):
        """
        Perform inference with the Ultralytics YOLO model (OpenVINO backend) and return:
          1) Annotated image
          2) List of detections (dictionaries)
          3) A Boolean "lockdown_needed" indicating if at least one person is within boundary
        """
        # The Ultralytics `predict()` call handles preprocessing, resizing, etc. automatically.
        results = self.model.predict(
            source=self.img,       # Numpy array or file path
            conf=self.conf_thres,  # Minimum confidence threshold
            iou=self.iou_thres,    # IoU threshold for NMS
            verbose=False
        )

        # For single-image inference, we can take the first result
        result = results[0]

        # result.boxes has all detections
        detections = []

        # Create a copy of the original image for annotation
        annotated_image = self.img.copy()
        img_h, img_w = annotated_image.shape[:2]

        # Flag to track if any person is within boundary
        lockdown_needed = False

        for box_data in result.boxes:
            # box_data.xyxy -> shape [1, 4]. Flatten it
            xyxy = box_data.xyxy[0].cpu().numpy()  # [x1, y1, x2, y2]
            conf = float(box_data.conf[0].cpu().numpy())
            class_id = int(box_data.cls[0].cpu().numpy())

            # Only focus on the 'person' class, assuming class 0 is 'person'
            if class_id != 0:
                continue

            x1, y1, x2, y2 = xyxy

            coords = {
                "x1": int(x1),
                "y1": int(y1),
                "x2": int(x2),
                "y2": int(y2),
            }
            coords_ratio = {
                "x1": x1 / img_w,
                "y1": y1 / img_h,
                "x2": x2 / img_w,
                "y2": y2 / img_h,
            }

            # Check boundary
            inside_boundary = self.is_within_boundary(coords_ratio)

            # Only draw bounding boxes (and label) if inside boundary
            if inside_boundary:
                logger.critical("Detected person within boundary -> Lockdown initiated.")
                lockdown_needed = True
                self.draw_detection(annotated_image, xyxy, conf, class_id)

            # Build the detection dictionary (you can skip adding if not inside boundary
            # if you only want to log/report those within the boundary)
            detections.append(
                {
                    "object": self.class_names[class_id],
                    "confidence": conf,
                    "coords": coords,
                    "coords_ratio": coords_ratio,
                    "inside_boundary": inside_boundary,
                }
            )

        # If no boundary was defined or no one was inside boundary, log info
        if not detections:
            logger.info("No persons detected in the frame.")
        elif not lockdown_needed:
            if any(b is not None for b in [self.x1_ratio, self.x2_ratio, self.y1_ratio, self.y2_ratio]):
                logger.info("No persons detected inside the specified boundary. System is safe.")
            else:
                logger.info("Boundary is not defined. Persons detected, but no boundary rules to enforce.")

        return annotated_image, detections, lockdown_needed


def infer_yolo11s(
    img,
    model_path=MODEL_PATH,
    conf_thres=0.25,
    iou_thres=0.7,
    # Optional boundary in ratio form [0..1]
    x1_ratio=None,
    x2_ratio=None,
    y1_ratio=None,
    y2_ratio=None
):
    """
    Runs inference with yolo11s OpenVINO model on the given image.

    Args:
        img (numpy.ndarray): BGR image array (e.g., from cv2.imread).
        model_path (str or Path): Path to the .xml file of the yolo11s OpenVINO model.
        conf_thres (float): Confidence threshold.
        iou_thres (float): IoU threshold.
        x1_ratio, x2_ratio, y1_ratio, y2_ratio (float | None):
            Optional bounding box in ratio [0..1] coordinates defining a 'restricted' region.

    Returns:
        (output_image, outputs, lockdown_needed):
            output_image -> annotated image (np.ndarray)
            outputs -> list of dictionaries with detected objects
            lockdown_needed -> bool indicating if at least one person is inside boundary
    """
    detection = YOLO11sOpenVINO(
        openvino_model=model_path,
        input_image=img,
        confidence_thres=conf_thres,
        iou_thres=iou_thres,
        x1_ratio=x1_ratio,
        x2_ratio=x2_ratio,
        y1_ratio=y1_ratio,
        y2_ratio=y2_ratio
    )
    output_image, outputs, lockdown_needed = detection.infer()
    return output_image, outputs, lockdown_needed
