# 🎫 Event Attendance Tracking System

A Flask-based web application for real-time event attendance tracking using QR code authentication and barcode linking. Originally developed for a college tech fest to manage 5000+ attendees, this system provides seamless check-in management with live camera feed integration.

## ✨ Features

* **Real-time QR Code Detection** - Advanced scanning using OpenCV and pyzbar with visual feedback.
* **Barcode Integration** - Manual barcode entry and linking to verified attendees.
* **Live Camera Feed** - Continuous video streaming with intelligent frame freezing.
* **Attendance Dashboard** - Real-time view of present and absent attendees.
* **Duplicate Prevention** - Prevents duplicate barcode assignments and double check-ins.
* **System Controls** - Reset functionality and comprehensive error handling.

## 🛠️ Technologies Used

* **Flask** - Web framework
* **Flask-SQLAlchemy** - Database ORM
* **OpenCV** - Computer vision and camera handling
* **pyzbar** - Enhanced QR/barcode decoding (optional)
* **PostgreSQL** - Database backend
* **NumPy** - Image processing operations

## 📋 Requirements
```
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
opencv-python==4.8.1.78
pyzbar==0.1.9
psycopg2-binary==2.9.7
numpy==1.24.3
```
## 🚀 Installation & Setup

### 1. Clone the Repository

```
git clone https://github.com/mirdanish6594/Authentication_system.git
cd Authentication_system
```

### 2. Create Virtual Environment
```
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```
### 3. Install Dependencies
```
pip install -r requirements.txt

# For enhanced QR detection (optional):
# macOS: brew install zbar
# Ubuntu: sudo apt-get install libzbar0
```
### 4. Database Setup

Configure your database in `config.py`:
```
class Config:
    SECRET_KEY = 'your-secret-key-here'
    SQLALCHEMY_DATABASE_URI = 'postgresql://username:password@localhost/attendance_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
```
### 5. Initialize Database
```
python
>>> from app import app, db
>>> with app.app_context():
...     db.create_all()
>>> exit()
```
## 🎯 Usage

### Starting the Application

python app.py

Navigate to `http://127.0.0.1:5000`

### QR Code Scanning Process

1.  **Prepare QR Codes** - Ensure QR codes contain attendee ID in supported formats:
    * Direct ID: `123`
    * With prefix: `ID:123`, `ATTENDEE-123`, `USER=123`
2.  **Scan Process**:
    * Position QR code within camera view.
    * System detects and freezes the frame with attendee information.
    * Enter the barcode manually in the input field.
    * Click "Attach Barcode" to complete check-in.
3.  **System Controls**:
    * **Reset** - Clear the current session.
    * **Dashboard** - View attendance status.
    * **Test Camera** - Check camera connectivity.

## 📊 API Endpoints

| Endpoint                 | Method | Purpose                       |
| ------------------------ | ------ | ----------------------------- |
| `/`                      | `GET`  | Main scanning interface       |
| `/dashboard`             | `GET`  | Attendance overview           |
| `/video_feed`            | `GET`  | Camera stream                 |
| `/attach_barcode_manual` | `POST` | Link barcode to attendee      |
| `/reset`                 | `POST` | Reset system state            |

## 🔧 Database Model
```
class Attendee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    entry = db.Column(db.Boolean, default=False)
    band_id = db.Column(db.String(50), unique=True, nullable=True)
```
## 🐛 Troubleshooting

### Camera Issues

# Test camera access
```
python -c "import cv2; cap = cv2.VideoCapture(0); print('Camera OK' if cap.isOpened() else 'Camera Failed')"
```
### QR Code Detection Issues

* Ensure good lighting conditions.
* Clean the camera lens.
* Try different QR code sizes.
* Check that the QR code format contains a numeric ID.

### pyzbar Installation (Optional Enhancement)

# macOS
```brew install zbar```

# Ubuntu
sudo apt-get install libzbar0

## 🚀 Production Deployment

### Using Gunicorn
```
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```
### Environment Variables
```
export SECRET_KEY="your-production-secret-key"
export DATABASE_URL="postgresql://user:pass@host:port/dbname"
```
## 🤝 Contributing

1.  Fork the repository.
2.  Create a feature branch: `git checkout -b feature/your-feature`
3.  Commit changes: `git commit -m 'Add some feature'`
4.  Push to the branch: `git push origin feature/your-feature`
5.  Submit a pull request.

## 📄 License

This project is licensed under the MIT License.

## 🏆 Real-World Usage

This system was successfully deployed for a college tech fest managing **5000+ attendees** with:

* Real-time check-in processing
* Zero downtime during peak hours
* Efficient QR code Scanning
* Comprehensive attendance tracking

Built for seamless event management 🎉
