import cv2

for i in range(6):  # Test first 5 indices
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        print(f"Camera {i} is available.")
        cap.release()
    else:
        print(f"Camera {i} is not available.")