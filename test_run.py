from vision_analyzer import VisionAnalyzer
import numpy as np
import cv2
import base64

analyzer = VisionAnalyzer(model_path="yolo11n.pt")

# Create a blank test image as base64
mock_img = np.zeros((640, 640, 3), dtype=np.uint8)
_, buffer = cv2.imencode(".jpg", mock_img)
mock_b64 = base64.b64encode(buffer).decode("utf-8")

# Call with explicit keyword argument
result = analyzer.analyze(image_b64=mock_b64)
print("Vision Module Output:", result)