from flask import Flask, render_template, Response, request, flash, redirect, url_for
from models import db, Attendee
from config import Config
import cv2
import logging
import numpy as np
import time

# Configure logging first
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- GLOBAL VARIABLES ---
PYZBAR_AVAILABLE = False

# Try to import pyzbar, but don't fail if it's not available
try:
    from pyzbar import pyzbar
    PYZBAR_AVAILABLE = True
    logging.info("pyzbar library loaded successfully")
except ImportError as e:
    PYZBAR_AVAILABLE = False
    logging.warning(f"pyzbar not available: {e}. Using OpenCV only for QR detection.")

# --- APPLICATION SETUP ---
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# --- QR CODE DETECTORS ---
cv_qr_decoder = cv2.QRCodeDetector()

# --- STATE MANAGEMENT ---
STATE_WAITING_FOR_BARCODE = False
STATE_CURRENT_ATTENDEE_ID = None
STATE_FROZEN_FRAME = None
STATE_LAST_QR_TIME = 0
STATE_QR_COOLDOWN = 2.0  # Seconds to wait before detecting new QR
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
            # Additional settings for better QR detection
            try:
                camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
                camera.set(cv2.CAP_PROP_EXPOSURE, -6)
            except:
                pass  # Some cameras don't support these settings
    return camera

def detect_qr_code_opencv(frame):
    """Detect QR codes using OpenCV with multiple preprocessing methods"""
    try:
        # Method 1: Try on original frame
        data, bbox, _ = cv_qr_decoder.detectAndDecode(frame)
        if data and bbox is not None:
            return data, bbox
        
        # Method 2: Convert to grayscale
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        data, bbox, _ = cv_qr_decoder.detectAndDecode(gray_frame)
        if data and bbox is not None:
            return data, bbox
        
        # Method 3: Apply preprocessing
        blurred = cv2.GaussianBlur(gray_frame, (3, 3), 0)
        
        # Try different threshold methods
        threshold_methods = [
            cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2),
            cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, 4),
            cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        ]
        
        for thresh_frame in threshold_methods:
            data, bbox, _ = cv_qr_decoder.detectAndDecode(thresh_frame)
            if data and bbox is not None:
                return data, bbox
                
        # Method 4: Morphological operations
        kernel = np.ones((3, 3), np.uint8)
        morph_frame = cv2.morphologyEx(gray_frame, cv2.MORPH_CLOSE, kernel)
        data, bbox, _ = cv_qr_decoder.detectAndDecode(morph_frame)
        if data and bbox is not None:
            return data, bbox
            
        # Method 5: Contrast and brightness adjustments
        for alpha in [0.7, 1.3, 1.5]:  # contrast
            for beta in [-20, 0, 20, 40]:  # brightness
                adjusted = cv2.convertScaleAbs(gray_frame, alpha=alpha, beta=beta)
                data, bbox, _ = cv_qr_decoder.detectAndDecode(adjusted)
                if data and bbox is not None:
                    return data, bbox
                    
    except Exception as e:
        logging.error(f"Error in OpenCV QR detection: {e}")
        
    return None, None

def detect_qr_code_pyzbar(frame):
    """Detect QR codes using pyzbar library as fallback"""
    global PYZBAR_AVAILABLE
    
    if not PYZBAR_AVAILABLE:
        return None, None
        
    try:
        # Convert to grayscale for pyzbar
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Try pyzbar detection
        qr_codes = pyzbar.decode(gray_frame)
        if qr_codes:
            # Return the first QR code found
            qr_code = qr_codes[0]
            data = qr_code.data.decode('utf-8')
            # Convert pyzbar rect to OpenCV bbox format
            rect = qr_code.rect
            bbox = np.array([[[rect.left, rect.top],
                            [rect.left + rect.width, rect.top],
                            [rect.left + rect.width, rect.top + rect.height],
                            [rect.left, rect.top + rect.height]]], dtype=np.float32)
            return data, bbox
            
        # Try with preprocessing for pyzbar
        blurred = cv2.GaussianBlur(gray_frame, (3, 3), 0)
        qr_codes = pyzbar.decode(blurred)
        if qr_codes:
            qr_code = qr_codes[0]
            data = qr_code.data.decode('utf-8')
            rect = qr_code.rect
            bbox = np.array([[[rect.left, rect.top],
                            [rect.left + rect.width, rect.top],
                            [rect.left + rect.width, rect.top + rect.height],
                            [rect.left, rect.top + rect.height]]], dtype=np.float32)
            return data, bbox
            
    except Exception as e:
        logging.error(f"Error in pyzbar QR detection: {e}")
        
    return None, None

def detect_qr_code(frame):
    """
    Comprehensive QR code detection using multiple methods
    Returns the decoded data, bbox, and processed frame
    """
    global PYZBAR_AVAILABLE
    
    # Try OpenCV first (faster)
    data, bbox = detect_qr_code_opencv(frame)
    if data and bbox is not None:
        logging.info(f"QR Code detected (OpenCV): '{data}'")
        return data, bbox, frame
    
    # Try pyzbar as fallback if available
    if PYZBAR_AVAILABLE:
        data, bbox = detect_qr_code_pyzbar(frame)
        if data and bbox is not None:
            logging.info(f"QR Code detected (pyzbar): '{data}'")
            return data, bbox, frame
        
    return None, None, frame

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
            parts = qr_string.split(':')
            attendee_id = int(parts[-1].strip())
        # Try other common separators
        elif '-' in qr_string:
            parts = qr_string.split('-')
            attendee_id = int(parts[-1].strip())
        elif '=' in qr_string:
            parts = qr_string.split('=')
            attendee_id = int(parts[-1].strip())
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
    global STATE_WAITING_FOR_BARCODE, STATE_CURRENT_ATTENDEE_ID, STATE_LAST_QR_TIME
    
    # Don't freeze frame here - will be done after drawing info
    STATE_LAST_QR_TIME = time.time()
    
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

def draw_qr_detection_box(frame, bbox):
    """Draw a box around detected QR code"""
    if bbox is not None:
        bbox = bbox.astype(int)
        cv2.polylines(frame, [bbox], True, (0, 255, 0), 3)
    return frame

def generate_frames():
    """Generate video frames with QR code detection"""
    global STATE_FROZEN_FRAME, STATE_WAITING_FOR_BARCODE, STATE_LAST_QR_TIME, PYZBAR_AVAILABLE
    
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
        current_time = time.time()
        should_freeze_frame = False
        
        try:
            # Use frozen frame if we're waiting for barcode (should stay frozen until barcode is processed)
            if STATE_FROZEN_FRAME is not None and STATE_WAITING_FOR_BARCODE:
                # Use the original frozen frame (already has info drawn on it)
                display_frame = STATE_FROZEN_FRAME.copy()
                with app.app_context():
                    current_info = get_display_info()
                    
            # Show frozen frame during cooldown period after error/warning
            elif STATE_FROZEN_FRAME is not None and (current_time - STATE_LAST_QR_TIME) < STATE_QR_COOLDOWN:
                display_frame = STATE_FROZEN_FRAME.copy()
                # Don't redraw info, it's already on the frozen frame
                
            else:
                # Live feed - process new frames
                if not STATE_WAITING_FOR_BARCODE and (current_time - STATE_LAST_QR_TIME) > STATE_QR_COOLDOWN:
                    # Clear any old frozen frame when resuming live feed
                    if STATE_FROZEN_FRAME is not None and not STATE_WAITING_FOR_BARCODE:
                        STATE_FROZEN_FRAME = None
                        
                    # Detect QR codes on live frame
                    qr_data, bbox, processed_frame = detect_qr_code(frame)
                    
                    if qr_data:
                        with app.app_context():
                            attendee = verify_qr_code(qr_data)
                            current_info = process_qr_result(attendee, qr_data)
                            should_freeze_frame = True  # Flag to freeze after drawing info
                            
                            # Draw detection box on the frame
                            if bbox is not None:
                                display_frame = draw_qr_detection_box(display_frame, bbox)
                    else:
                        # No QR detected, show live feed with default message
                        current_info = {"status": "Info", "message": "Please Scan QR Code", "details": ""}
            
            # Only draw information if we're not using a frozen frame that already has info
            if not (STATE_FROZEN_FRAME is not None and not should_freeze_frame):
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
                cv2.rectangle(overlay, (5, 5), (635, 120), (0, 0, 0), -1)
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
                
                # Add frame state indicator
                if STATE_WAITING_FOR_BARCODE:
                    cv2.putText(display_frame, "WAITING FOR BARCODE", (10, 115), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
            
            # Freeze the frame after all information has been drawn
            if should_freeze_frame:
                STATE_FROZEN_FRAME = display_frame.copy()
                logging.info("Frame frozen with QR information displayed")
                       
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
    global STATE_WAITING_FOR_BARCODE, STATE_CURRENT_ATTENDEE_ID, STATE_FROZEN_FRAME, STATE_LAST_QR_TIME
    STATE_WAITING_FOR_BARCODE = False
    STATE_CURRENT_ATTENDEE_ID = None
    STATE_FROZEN_FRAME = None
    STATE_LAST_QR_TIME = 0
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