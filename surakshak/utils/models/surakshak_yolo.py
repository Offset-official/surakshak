import cv2
import numpy as np
import logging
from ultralytics import YOLO
from django.conf import settings
from surakshak.utils.logs import MyHandler

logger = logging.getLogger("inference")
logger.addHandler(MyHandler())

# Path to your exported OpenVINO model (.xml); the .bin must be in the same folder
MODEL_PATH = settings.BASE_DIR / "surakshak/utils/models/yolo11s_openvino_model/yolo11s.xml"


class YOLO11sOpenVINO:
    """
    YOLOv8-based custom model (yolo11s) + OpenVINO inference class, using Ultralytics library.
    """

    def __init__(self, openvino_model, input_image, confidence_thres, iou_thres):
        """
        Args:
            openvino_model (str or Path): Path to the OpenVINO .xml file.
            input_image (numpy.ndarray): BGR image array (as read by OpenCV).
            confidence_thres (float): Minimum confidence score threshold.
            iou_thres (float): IoU threshold for NMS.
        """
        self.model_path = str(openvino_model)
        self.img = input_image  # BGR image
        self.conf_thres = confidence_thres
        self.iou_thres = iou_thres

        # Load the Ultralytics YOLO model (OpenVINO format).
        # This automatically uses the OpenVINO runtime because the file is .xml.
        self.model = YOLO(self.model_path)

        # The model has a .names attribute containing class names (assuming it was trained properly).
        # If you have a custom names list, you could load that here instead.
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

    def infer(self):
        """
        Perform inference with the Ultralytics YOLO model (OpenVINO backend) and return:
          1) Annotated image
          2) List of detections (dictionaries)
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

        for box_data in result.boxes:
            # box_data.xyxy -> shape [1, 4]. Flatten it
            xyxy = box_data.xyxy[0].cpu().numpy()  # [x1, y1, x2, y2]
            conf = float(box_data.conf[0].cpu().numpy())
            class_id = int(box_data.cls[0].cpu().numpy())

            # If you only want certain classes, filter here, e.g.:
            # if class_id != 0:  # Skip if not 'person' (assuming 'person' is class 0)
            #     continue

            x1, y1, x2, y2 = xyxy

            # Build the detection dictionary
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

            detections.append(
                {
                    "object": self.class_names[class_id],
                    "confidence": conf,
                    "coords": coords,
                    "coords_ratio": coords_ratio,
                }
            )

            # Draw the bounding box and label
            self.draw_detection(annotated_image, xyxy, conf, class_id)

        return annotated_image, detections


def infer_yolo11s(img, model_path=MODEL_PATH, conf_thres=0.25, iou_thres=0.7):
    """
    Runs inference with yolo11s OpenVINO model on the given image.

    Args:
        img (numpy.ndarray): BGR image array (e.g., from cv2.imread).
        model_path (str): Path to the .xml file of the yolo11s OpenVINO model.
        conf_thres (float): Confidence threshold.
        iou_thres (float): IoU threshold.

    Returns:
        (output_image, outputs):
            output_image -> annotated image (np.ndarray)
            outputs -> list of dictionaries with detected objects
    """
    detection = YOLO11sOpenVINO(model_path, img, conf_thres, iou_thres)
    output_image, outputs = detection.infer()
    return output_image, outputs
