# -*- coding: utf-8 -*-
from collections import OrderedDict
import numpy as np
import argparse
import dlib
import cv2
import os

# Argument parsing
ap = argparse.ArgumentParser()
ap.add_argument("-p", "--shape-predictor", required=True, help="path to facial landmark predictor")
ap.add_argument("-i", "--image", required=True, help="path to input image")
args = vars(ap.parse_args())

# Define mapping for 68 facial landmarks
FACIAL_LANDMARKS_68_IDXS = OrderedDict([
    ("mouth", (48, 68)),
    ("right_eyebrow", (17, 22)),
    ("left_eyebrow", (22, 27)),
    ("right_eye", (36, 42)),
    ("left_eye", (42, 48)),
    ("nose", (27, 36)),
    ("jaw", (0, 17))
])

def shape_to_np(shape, dtype="int"):
    # Convert dlib shape object to a NumPy array
    coords = np.zeros((shape.num_parts, 2), dtype=dtype)
    for i in range(0, shape.num_parts):
        coords[i] = (shape.part(i).x, shape.part(i).y)
    return coords

def visualize_facial_landmarks(image, shape, colors=None, alpha=0.75):
    # Create overlay and output copies for color masking
    overlay = image.copy()
    output = image.copy()
    
    if colors is None:
        colors = [(19, 199, 109), (79, 76, 240), (230, 159, 23),
                  (168, 100, 168), (158, 163, 32),
                  (163, 38, 32), (180, 42, 220)]

    # Loop over the facial landmark regions individually
    for (i, name) in enumerate(FACIAL_LANDMARKS_68_IDXS.keys()):
        (j, k) = FACIAL_LANDMARKS_68_IDXS[name]
        pts = shape[j:k]
        
        # If the region is the jaw, draw lines
        if name == "jaw":
            for l in range(1, len(pts)):
                ptA = tuple(pts[l - 1])
                ptB = tuple(pts[l])
                cv2.line(overlay, ptA, ptB, colors[i], 2)
        # Otherwise, compute the convex hull and fill the contour
        else:
            hull = cv2.convexHull(pts)
            cv2.drawContours(overlay, [hull], -1, colors[i], -1)

    # Apply the transparent overlay onto the image
    cv2.addWeighted(overlay, alpha, output, 1 - alpha, 0, output)
    return output

# 1. Load Dlib face detector and shape predictor
print("[INFO] Loading dlib detectors...")
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(args["shape_predictor"])

# 2. Read and preprocess the image
image = cv2.imread(args["image"])
if image is None:
    print("[ERROR] Could not read image.")
    exit()

# Maintain aspect ratio and resize
(h, w) = image.shape[:2]
image = cv2.resize(image, (500, int(h * (500 / w))), interpolation=cv2.INTER_AREA)
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# --- Critical Fix: Memory rearrangement for M3 Mac ---
# Force image memory to C-contiguous layout to prevent dlib "Unsupported image type" errors
gray_fixed = np.array(gray, copy=True, order='C')

# 3. Detect faces using Dlib
print("[INFO] Detecting faces...")
rects = detector(gray_fixed, 1)
print(f"[INFO] Found {len(rects)} face(s)")

# Initialize final output as a copy of the resized original image
final_output = image.copy()

# 4. Loop over the detected faces
for (i, rect) in enumerate(rects):
    # Predict facial landmarks
    shape_obj = predictor(gray_fixed, rect)
    shape = shape_to_np(shape_obj)

    # Draw color masks for each face
    print(f"[INFO] Processing face {i+1}...")
    
    # Update final_output cumulatively with each detected face
    final_output = visualize_facial_landmarks(final_output, shape)

# 5. Display and save the final result
cv2.imshow("Multi-face Landmark Detection", final_output)

# Create output directory and save result
if not os.path.exists("output"):
    os.makedirs("output")
save_path = f"output/multi_face_result.jpg"
cv2.imwrite(save_path, final_output)
print(f"[INFO] Final result saved to: {save_path}")

print("[INFO] Done. Press any key to exit.")
cv2.waitKey(0)
cv2.destroyAllWindows()