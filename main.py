from flask import Flask, render_template, Response, flash, redirect, url_for, request
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.orm import sessionmaker, declarative_base, scoped_session
from sqlalchemy.exc import SQLAlchemyError
import cv2
from pyzbar.pyzbar import decode
from PIL import Image
import logging
import threading

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configure logging
logging.basicConfig(level=logging.INFO)

# Database setup for MySQL
engine = create_engine('mysql+pymysql://techvaganza_a:Geze89828982@14.139.61.137/techvaganza_test')
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

# Declare base for SQLAlchemy models
Base = declarative_base()

# Define the Attendees model
class Attendees(Base):
    __tablename__ = 'attendees'
    
    UID = Column(Integer, primary_key=True)
    FirstName = Column(String(100))
    LastName = Column(String(100))
    Email = Column(String(100))
    InstituteName = Column(String(100))
    ContactNumber = Column(String(15))
    BandID = Column(Integer)

# Create the tables if they don't exist
Base.metadata.create_all(engine)

# Global variables
current_attendee = None
waiting_for_barcode = False
message_to_display = None
frozen_frame = None

# Thread-local storage
thread_local = threading.local()

# QR Code detection
def detect_qr_code(frame):
    image = Image.fromarray(frame)
    decoded_objects = decode(image)
    qr_code_data_list = [obj.data.decode('utf-8') for obj in decoded_objects if obj.type == 'QRCODE']
    return qr_code_data_list

# Barcode detection
def detect_barcode(frame):
    image = Image.fromarray(frame)
    decoded_objects = decode(image)
    barcode_data_list = [obj.data.decode('utf-8') for obj in decoded_objects if obj.type == 'CODE128']
    return barcode_data_list

# Get session
def get_session():
    if not hasattr(thread_local, "session"):
        thread_local.session = Session()
    return thread_local.session

# Verify QR Code
def verify_qr_code(value):
    global current_attendee, waiting_for_barcode, message_to_display, frozen_frame
    try:
        uid = int(value.split(":")[-1].strip())  # Assuming the QR code format is UID: <number>
        session = get_session()
        attendee = session.query(Attendees).filter_by(UID=uid).first()
        if attendee:
            if attendee.BandID:
                message_to_display = "Already Attended"
            else:
                current_attendee = attendee
                waiting_for_barcode = True
                message_to_display = "QR Code Scanned, enter the barcode."
                return attendee
        else:
            message_to_display = "Attendee Not Found"
    except SQLAlchemyError as e:
        logging.error(f"Database Error: {e}")
        message_to_display = f"Database Error: {e}"
    except Exception as e:
        logging.error(f"Error: {e}")
        message_to_display = f"Error: {e}"
    return None

# Attach Barcode Manually
@app.route('/attach_barcode', methods=['POST'])
def attach_barcode():
    barcode_value = request.form.get("barcode")
    return attach_barcode_to_attendee(barcode_value)

# Attach Barcode to Attendee Logic
def attach_barcode_to_attendee(barcode_value):
    global current_attendee, message_to_display, waiting_for_barcode
    if current_attendee:
        try:
            session = get_session()
            attendee = session.query(Attendees).filter_by(UID=current_attendee.UID).first()
            if attendee:
                attendee.BandID = barcode_value
                session.commit()
                message_to_display = "Barcode Linked. Attendance Confirmed."
                flash("Barcode attached successfully. Attendance confirmed.")
                waiting_for_barcode = False
                current_attendee = None
            else:
                message_to_display = "No attendee record found."
                flash("Error: No attendee record found.")
        except SQLAlchemyError as e:
            logging.error(f"Database Error: {e}")
            message_to_display = f"Database Error: {e}"
            flash(f"Database Error: {e}")
        except Exception as e:
            logging.error(f"Error: {e}")
            message_to_display = f"Error: {e}"
            flash(f"Error: {e}")
    else:
        message_to_display = "Scan QR Code first."
        flash("Please scan a QR code first.")
    return redirect(url_for('index'))

# Reset the frozen frame
@app.route('/unfreeze_frame', methods=['POST'])
def unfreeze_frame():
    global frozen_frame, waiting_for_barcode, current_attendee
    frozen_frame = None
    waiting_for_barcode = False
    current_attendee = None
    flash("Reset to Scan QR Code.")
    return redirect(url_for('index'))

# Process the next QR code
@app.route('/next_qr', methods=['POST'])
def next_qr():
    global current_attendee, waiting_for_barcode, message_to_display, frozen_frame
    current_attendee = None
    frozen_frame = None
    waiting_for_barcode = False
    message_to_display = "Scan QR Code"
    flash("Ready for the next QR code.")
    return redirect(url_for('index'))

# Generate frames from camera feed
def gen_frames():
    camera = cv2.VideoCapture(5)

    if not camera.isOpened():
        logging.error("Error: Unable to access the camera.")
        return None

    while True:
        success, frame = camera.read()
        if not success:
            logging.error("Error: Unable to read from camera.")
            break

        frame_bytes = process_frame(frame)

        if frame_bytes:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    camera.release()

# Process frame for video stream
def process_frame(frame):
    global waiting_for_barcode, message_to_display, frozen_frame, current_attendee
    
    if not waiting_for_barcode:
        qr_codes = detect_qr_code(frame)
        if qr_codes:
            for qr_code in qr_codes:
                attendee = verify_qr_code(qr_code)
                if attendee:
                    frozen_frame = display_attendee_info(frame.copy(), attendee)
                    return cv2.imencode('.jpg', frozen_frame)[1].tobytes()
    else:
        barcodes = detect_barcode(frame)
        if barcodes:
            barcode = barcodes[0]
            attach_barcode_to_attendee(barcode)
            frozen_frame = None
            waiting_for_barcode = False

    display_frame = frozen_frame if frozen_frame is not None else frame.copy()

    if waiting_for_barcode:
        cv2.putText(display_frame, "Waiting for barcode scan...", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    if message_to_display:
        cv2.putText(display_frame, message_to_display, (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

    return cv2.imencode('.jpg', display_frame)[1].tobytes()

# Display attendee info on the frame
def display_attendee_info(frame, attendee):
    cv2.putText(frame, f"ID: {attendee.UID}", (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
    cv2.putText(frame, f"Name: {attendee.FirstName} {attendee.LastName}", (10, 180), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
    cv2.putText(frame, f"Email: {attendee.Email}", (10, 210), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
    cv2.putText(frame, f"InstituteName: {attendee.InstituteName}", (10, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
    return frame

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return render_template('entry_status.html', message=message_to_display)

if __name__ == '__main__':
    app.run()

# Cleanup
@app.teardown_appcontext
def shutdown_session(exception=None):
    Session.remove()