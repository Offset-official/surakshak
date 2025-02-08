import argparse
import cv2
import numpy as np
import onnxruntime as ort
import logging
import time

# Optional: Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("inference")

class YOLOv8:
    """YOLOv8 object detection model class for handling inference and visualization."""

    def __init__(self, onnx_model, confidence_thres=0.5, iou_thres=0.5, providers=["CPUExecutionProvider"]):
        """
        Initializes an instance of the YOLOv8 class.

        Args:
            onnx_model (str): Path to the ONNX model.
            confidence_thres (float): Confidence threshold for filtering detections.
            iou_thres (float): IoU (Intersection over Union) threshold for non-maximum suppression.
            providers (List[str]): Execution providers for ONNXRuntime.
        """
        self.onnx_model = onnx_model
        self.confidence_thres = confidence_thres
        self.iou_thres = iou_thres

        # Load the class names from the COCO dataset (80 classes)
        self.classes = [
            "person", "bicycle", "car", "motorcycle", "airplane", "bus",
            "train", "truck", "boat", "traffic light", "fire hydrant",
            "stop sign", "parking meter", "bench", "bird", "cat", "dog",
            "horse", "sheep", "cow", "elephant", "bear", "zebra",
            "giraffe", "backpack", "umbrella", "handbag", "tie",
            "suitcase", "frisbee", "skis", "snowboard", "sports ball",
            "kite", "baseball bat", "baseball glove", "skateboard",
            "surfboard", "tennis racket", "bottle", "wine glass", "cup",
            "fork", "knife", "spoon", "bowl", "banana", "apple",
            "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza",
            "donut", "cake", "chair", "couch", "potted plant", "bed",
            "dining table", "toilet", "tv", "laptop", "mouse", "remote",
            "keyboard", "cell phone", "microwave", "oven", "toaster",
            "sink", "refrigerator", "book", "clock", "vase", "scissors",
            "teddy bear", "hair drier", "toothbrush"
        ]

        # Generate a color palette for the classes
        self.color_palette = np.random.uniform(0, 255, size=(len(self.classes), 3))

        # Create an ONNX Runtime session
        logger.info(f"Loading ONNX model from: {onnx_model}")
        self.session = ort.InferenceSession(self.onnx_model, providers=providers)

        # Retrieve model input information
        self.model_inputs = self.session.get_inputs()
        input_shape = self.model_inputs[0].shape
        # Shape is [batch, channel, height, width], e.g. [1, 3, 640, 640]
        self.input_height = input_shape[2]
        self.input_width = input_shape[3]

    def draw_detections(self, img, box, score, class_id):
        """
        Draws bounding boxes and labels on the input image based on the detected objects.

        Args:
            img (numpy.ndarray): The input image to draw detections on.
            box (list[int]): Detected bounding box [x, y, width, height].
            score (float): Corresponding detection score.
            class_id (int): Class ID for the detected object.
        """
        x1, y1, w, h = box
        color = self.color_palette[class_id]
        cv2.rectangle(img, (int(x1), int(y1)), (int(x1 + w), int(y1 + h)), color, 2)

        label = f"{self.classes[class_id]}: {score:.2f}"
        (label_width, label_height), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        label_x = x1
        # Make sure the text is above (or below) the box
        label_y = y1 - 10 if y1 - 10 > label_height else y1 + label_height + 10

        # Draw a filled rectangle for the label background
        cv2.rectangle(
            img,
            (label_x, label_y - label_height),
            (label_x + label_width, label_y),
            color,
            cv2.FILLED
        )

        # Put label text
        cv2.putText(
            img,
            label,
            (label_x, label_y - 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 0),
            1,
            cv2.LINE_AA
        )

    def preprocess(self, frame):
        """
        Preprocess the input frame for inference.
        
        Args:
            frame (numpy.ndarray): BGR image from OpenCV.

        Returns:
            numpy.ndarray: Preprocessed image as float32.
        """
        self.img_height, self.img_width_orig = frame.shape[:2]
        # Convert BGR to RGB
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # Resize
        img = cv2.resize(img, (self.input_width, self.input_height))
        # Normalize
        img = img.astype(np.float32) / 255.0
        # HWC to CHW
        img = np.transpose(img, (2, 0, 1))
        # Add batch dimension
        img = np.expand_dims(img, axis=0)
        return img

    def postprocess(self, frame, output):
        """
        Postprocess the model's output to extract bounding boxes, scores, and class IDs.
        
        Args:
            frame (numpy.ndarray): Original BGR frame.
            output (List[numpy.ndarray]): Model outputs.

        Returns:
            numpy.ndarray: The frame with detections drawn.
            List[dict]: A list of detections.
        """
        # Output shape: [1, 84, N] -> after np.squeeze -> [84, N]
        # Then we transpose -> [N, 84]
        out = np.transpose(np.squeeze(output[0]))
        rows = out.shape[0]

        boxes = []
        scores = []
        class_ids = []

        # Scale factors to map back to original image size
        x_factor = self.img_width_orig / self.input_width
        y_factor = self.img_height / self.input_height

        for i in range(rows):
            class_scores = out[i][4:]
            max_score = np.amax(class_scores)
            if max_score >= self.confidence_thres:
                class_id = np.argmax(class_scores)
                x, y, w, h = out[i][0], out[i][1], out[i][2], out[i][3]

                # Convert center x,y,w,h to top-left x,y and box width,height
                left = int((x - w / 2) * x_factor)
                top = int((y - h / 2) * y_factor)
                width = int(w * x_factor)
                height = int(h * y_factor)

                boxes.append([left, top, width, height])
                scores.append(float(max_score))
                class_ids.append(class_id)

        # Perform NMS
        indices = cv2.dnn.NMSBoxes(boxes, scores, self.confidence_thres, self.iou_thres)
        detections = []
        if len(indices) > 0:
            for i in indices.flatten():
                box = boxes[i]
                score = scores[i]
                class_id = class_ids[i]
                self.draw_detections(frame, box, score, class_id)

                x1, y1, w, h = box
                detection_info = {
                    "object": self.classes[class_id],
                    "confidence": score,
                    "coords": {
                        "x1": x1,
                        "y1": y1,
                        "x2": x1 + w,
                        "y2": y1 + h
                    }
                }
                detections.append(detection_info)

        return frame, detections

    def infer(self, frame):
        """
        Runs inference on a single frame.

        Args:
            frame (numpy.ndarray): BGR image from OpenCV.

        Returns:
            (numpy.ndarray, List[dict]): A tuple of (annotated_frame, detections).
        """
        img_data = self.preprocess(frame)
        # Run the model
        output = self.session.run(None, {self.model_inputs[0].name: img_data})
        # Postprocess
        annotated_frame, detections = self.postprocess(frame, output)
        return annotated_frame, detections


def main():
    parser = argparse.ArgumentParser(description="Real-time YOLOv8 ONNX Inference on a Video")
    parser.add_argument("--model_path", type=str, default="yolov8n.onnx", help="Path to the YOLOv8 ONNX model.")
    parser.add_argument("--video_path", type=str, default="video.mp4", help="Path to the input video.")
    parser.add_argument("--conf_thres", type=float, default=0.5, help="Confidence threshold.")
    parser.add_argument("--iou_thres", type=float, default=0.5, help="IoU threshold.")
    args = parser.parse_args()

    # Initialize the detector
    detector = YOLOv8(
        onnx_model=args.model_path,
        confidence_thres=args.conf_thres,
        iou_thres=args.iou_thres,
        providers=["CPUExecutionProvider"]  # or e.g. ["CUDAExecutionProvider"] if you have GPU
    )

    cap = cv2.VideoCapture(args.video_path)
    if not cap.isOpened():
        logger.error(f"Unable to open video file: {args.video_path}")
        return

    # Read frames in a loop
    while True:
        ret, frame = cap.read()
        if not ret:
            logger.info("End of video stream or cannot read the video.")
            break

        start_time = time.time()

        # Inference
        annotated_frame, detections = detector.infer(frame)

        # Calculate FPS
        end_time = time.time()
        fps = 1 / (end_time - start_time + 1e-8)

        # Display FPS on the frame
        cv2.putText(
            annotated_frame,
            f"FPS: {fps:.2f}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )

        # Show the frame
        cv2.imshow("YOLOv8 Inference", annotated_frame)

        # Press 'q' to exit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
