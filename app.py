from flask import Flask, render_template, Response, request, flash, redirect, url_for
from models import db, Attendee
from config import Config
import cv2
import logging
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- APPLICATION SETUP ---
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# --- OPENCV QR CODE DETECTOR ---
qr_decoder = cv2.QRCodeDetector()

# --- STATE MANAGEMENT ---
STATE_WAITING_FOR_BARCODE = False
STATE_CURRENT_ATTENDEE_ID = None
STATE_FROZEN_FRAME = None
camera = None

def get_camera():
    global camera
    if camera is None:
        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            logging.error("Error: Could not open camera.")
            camera = None
        else:
            # Set camera properties for better performance
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            camera.set(cv2.CAP_PROP_FPS, 30)
    return camera

# --- HELPER FUNCTIONS ---
def detect_qr_code(frame):
    """
    Detects QR codes using multiple methods for better reliability.
    Returns the decoded data and the frame for visualization.
    """
    qr_data = []
    
    try:
        # Method 1: Try on original frame first
        data, bbox, _ = qr_decoder.detectAndDecode(frame)
        if data and bbox is not None:
            logging.info(f"QR Code Detected (original): '{data}'")
            qr_data.append(data)
            return qr_data, frame
        
        # Method 2: Convert to grayscale and try again
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        data, bbox, _ = qr_decoder.detectAndDecode(gray_frame)
        if data and bbox is not None:
            logging.info(f"QR Code Detected (grayscale): '{data}'")
            qr_data.append(data)
            return qr_data, frame
        
        # Method 3: Apply image preprocessing for difficult cases
        # Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray_frame, (5, 5), 0)
        
        # Try multiple threshold methods
        threshold_methods = [
            cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2),
            cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 11, 2),
            cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        ]
        
        for i, thresh_frame in enumerate(threshold_methods):
            data, bbox, _ = qr_decoder.detectAndDecode(thresh_frame)
            if data and bbox is not None:
                logging.info(f"QR Code Detected (threshold method {i+1}): '{data}'")
                qr_data.append(data)
                return qr_data, frame
                
        # Method 4: Try with different contrast/brightness adjustments
        for alpha in [1.2, 0.8]:  # contrast
            for beta in [10, -10, 30, -30]:  # brightness
                adjusted = cv2.convertScaleAbs(gray_frame, alpha=alpha, beta=beta)
                data, bbox, _ = qr_decoder.detectAndDecode(adjusted)
                if data and bbox is not None:
                    logging.info(f"QR Code Detected (adjusted): '{data}'")
                    qr_data.append(data)
                    return qr_data, frame
                    
    except Exception as e:
        logging.error(f"Error in QR code detection: {e}")
        
    return qr_data, frame

def verify_qr_code(qr_data):
    """Verify QR code format and return attendee if valid"""
    if not qr_data:
        logging.warning("Empty QR code data")
        return None
        
    # Handle different QR code formats
    qr_string = str(qr_data).strip()
    logging.info(f"Verifying QR code: '{qr_string}'")
    
    try:
        # Try direct ID conversion first
        if qr_string.isdigit():
            attendee_id = int(qr_string)
        # Try format with colon separator
        elif ':' in qr_string:
            attendee_id = int(qr_string.split(':')[-1].strip())
        # Try other common separators
        elif '-' in qr_string:
            attendee_id = int(qr_string.split('-')[-1].strip())
        else:
            # Try to extract numbers from the string
            import re
            numbers = re.findall(r'\d+', qr_string)
            if numbers:
                attendee_id = int(numbers[-1])  # Take the last number found
            else:
                logging.warning(f"No valid ID found in QR code: '{qr_string}'")
                return None
                
        logging.info(f"Extracted attendee ID: {attendee_id}")
        attendee = Attendee.query.get(attendee_id)
        if attendee:
            logging.info(f"Found attendee: {attendee.first_name} {attendee.last_name}")
        else:
            logging.warning(f"No attendee found with ID: {attendee_id}")
        return attendee
        
    except (ValueError, IndexError) as e:
        logging.warning(f"Invalid QR code format: '{qr_string}'. Error: {e}")
        return None

def process_qr_result(attendee, qr_data):
    """Process the QR scan result and update state accordingly"""
    global STATE_WAITING_FOR_BARCODE, STATE_CURRENT_ATTENDEE_ID
    
    if not attendee:
        return {"status": "Error", "message": "QR Code Not Recognized", "details": f"Data: {qr_data}"}
    
    if attendee.entry:
        return {"status": "Warning", "message": "Already Checked In", "details": f"{attendee.first_name} {attendee.last_name}"}
    
    # Valid attendee, not yet checked in
    STATE_WAITING_FOR_BARCODE = True
    STATE_CURRENT_ATTENDEE_ID = attendee.id
    return {"status": "Success", "message": "QR Verified - Enter Barcode", "details": f"{attendee.first_name} {attendee.last_name}"}

def get_display_info():
    """Get current display information based on state"""
    global STATE_WAITING_FOR_BARCODE, STATE_CURRENT_ATTENDEE_ID
    
    if STATE_WAITING_FOR_BARCODE and STATE_CURRENT_ATTENDEE_ID:
        attendee = Attendee.query.get(STATE_CURRENT_ATTENDEE_ID)
        if attendee:
            return {
                "status": "Success", 
                "message": "Verified - Enter Barcode", 
                "details": f"{attendee.first_name} {attendee.last_name}"
            }
    
    return {"status": "Info", "message": "Please Scan QR Code", "details": ""}

def link_barcode(barcode_value):
    """Link barcode to current attendee and check them in"""
    global STATE_CURRENT_ATTENDEE_ID
    
    if not STATE_CURRENT_ATTENDEE_ID:
        flash("Error: No attendee selected. Please scan QR code first.", "error")
        return
        
    attendee = Attendee.query.get(STATE_CURRENT_ATTENDEE_ID)
    if not attendee:
        flash("Error: Attendee not found.", "error")
        reset_state()
        return

    # Check if barcode already exists
    existing_attendee = Attendee.query.filter_by(band_id=barcode_value).first()
    if existing_attendee:
        flash(f"Error: Barcode already assigned to {existing_attendee.first_name} {existing_attendee.last_name}.", "error")
        reset_state()
        return

    # Link barcode and check in
    attendee.band_id = barcode_value
    attendee.entry = True 
    db.session.commit()
    flash(f"Success! {attendee.first_name} {attendee.last_name} is checked in.", "success")
    logging.info(f"Checked in: {attendee.first_name} {attendee.last_name} with barcode: {barcode_value}")
    reset_state()

def generate_frames():
    """Generate video frames with QR code detection"""
    global STATE_FROZEN_FRAME, STATE_WAITING_FOR_BARCODE, STATE_CURRENT_ATTENDEE_ID
    
    cam = get_camera()
    if not cam:
        logging.error("Camera not available")
        return

    while True:
        success, frame = cam.read()
        if not success:
            logging.error("Failed to read from camera")
            break
            
        display_frame = frame.copy()
        current_info = {"status": "Info", "message": "Please Scan QR Code", "details": ""}
        
        try:
            # Only process new frames if not waiting for barcode
            if not STATE_WAITING_FOR_BARCODE:
                # Detect QR codes
                qr_codes, processed_frame = detect_qr_code(frame)
                
                if qr_codes:
                    with app.app_context():
                        attendee = verify_qr_code(qr_codes[0])
                        current_info = process_qr_result(attendee, qr_codes[0])
                        
                        # If verification successful, freeze the frame
                        if current_info["status"] == "Success":
                            STATE_FROZEN_FRAME = frame.copy()
                            
            else:
                # We're waiting for barcode, show frozen frame with current info
                if STATE_FROZEN_FRAME is not None:
                    display_frame = STATE_FROZEN_FRAME.copy()
                with app.app_context():
                    current_info = get_display_info()
            
            # Draw information on frame
            status_colors = {
                "Info": (255, 200, 0),      # Blue
                "Success": (0, 255, 0),     # Green
                "Error": (0, 0, 255),       # Red
                "Warning": (0, 165, 255)    # Orange
            }
            
            color = status_colors.get(current_info["status"], (255, 255, 255))
            
            # Add semi-transparent background for text
            overlay = display_frame.copy()
            cv2.rectangle(overlay, (5, 5), (635, 100), (0, 0, 0), -1)
            display_frame = cv2.addWeighted(display_frame, 0.7, overlay, 0.3, 0)
            
            # Draw main message
            cv2.putText(display_frame, current_info["message"], (10, 35), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
            
            # Draw details if available
            if current_info.get("details"):
                cv2.putText(display_frame, current_info["details"], (10, 70), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
            # Add status indicator
            status_text = f"Status: {current_info['status']}"
            cv2.putText(display_frame, status_text, (10, 95), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                       
        except Exception as e:
            logging.error(f"Error in generate_frames: {e}")
            cv2.putText(display_frame, "Error processing frame", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # Encode frame
        try:
            _, buffer = cv2.imencode('.jpg', display_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        except Exception as e:
            logging.error(f"Error encoding frame: {e}")
            break

def reset_state():
    """Reset all state variables"""
    global STATE_WAITING_FOR_BARCODE, STATE_CURRENT_ATTENDEE_ID, STATE_FROZEN_FRAME
    STATE_WAITING_FOR_BARCODE = False
    STATE_CURRENT_ATTENDEE_ID = None
    STATE_FROZEN_FRAME = None
    logging.info("State reset")

# --- FLASK ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    present_attendees = Attendee.query.filter_by(entry=True).order_by(Attendee.first_name).all()
    absent_attendees = Attendee.query.filter_by(entry=False).order_by(Attendee.first_name).all()
    return render_template('dashboard.html', present_attendees=present_attendees, absent_attendees=absent_attendees)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/attach_barcode_manual', methods=['POST'])
def attach_barcode_manual():
    if not STATE_WAITING_FOR_BARCODE:
        flash("Please scan a QR code first.", "error")
        return redirect(url_for('index'))
        
    barcode_value = request.form.get("barcode", "").strip()
    if not barcode_value:
        flash("Barcode cannot be empty.", "error")
        return redirect(url_for('index'))
        
    link_barcode(barcode_value)
    return redirect(url_for('index'))

@app.route('/reset', methods=['POST'])
def reset():
    reset_state()
    flash("System reset. Ready for next QR code.", "info")
    return redirect(url_for('index'))

@app.route('/test_camera')
def test_camera():
    """Test route to check camera availability"""
    cam = get_camera()
    if cam and cam.isOpened():
        return {"status": "success", "message": "Camera is working"}
    else:
        return {"status": "error", "message": "Camera not available"}, 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, threaded=True)