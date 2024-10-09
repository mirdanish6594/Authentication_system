import cv2
from pyzbar.pyzbar import decode

def test_qr_code_extraction():
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Unable to access the camera")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Unable to capture frame")
            break

        decoded_objects = decode(frame)
        
        if decoded_objects:
            for obj in decoded_objects:
                qr_code_info = obj.data.decode('utf-8')
                print(f"QR Code Data: {qr_code_info}")  # Print the extracted QR code data
        else:
            print("No QR Code detected")

        cv2.imshow('QR Code Scanner', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    test_qr_code_extraction()
