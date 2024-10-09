# Event Attendance Tracking System with QR and Barcode Scanning

This project is a Flask-based web application designed for event attendance tracking. It authenticates attendees upon entry by scanning QR codes and optionally attaching barcodes. The system uses a camera feed for real-time scanning and stores attendance records in a PostgreSQL database.

## Features

- Real-time QR code scanning for attendee authentication
- Option to manually enter and attach a barcode to each attendee
- Attendance tracking with a visual interface for event organizers
- Controls to reset the camera feed and manage attendance records

## Technologies Used

- Flask for the web framework
- Flask-SQLAlchemy for database interaction
- OpenCV for capturing and processing video from a camera
- Pyzbar for decoding QR codes and barcodes
- PostgreSQL as the database backend

## Requirements

To run this project, the following Python packages are required. You can install them using the provided `requirements.txt` file:

```bash
pip install -r requirements.txt
```
## Requirements List
- Flask
- Flask-SQLAlchemy
- OpenCV
- Requests
- Pyzbar
- Psycopg2 (for PostgreSQL connection)

## Setup and Installation
1. Clone the repository:
```bash
git clone https://github.com/<USERNAME>/<REPO>.git
cd <REPO>
```
2. Set up the environment: It is recommended to use a virtual environment to isolate dependencies.
```bash
python -m venv venv
source venv/bin/activate   # On Windows use `venv\Scripts\activate`
```
3. Install dependencies:
```bash
pip install -r requirements.txt
```
4. Configure Database: Update the database connection details in main.py to match your PostgreSQL setup.
5. Run the application:
```bash
python main.py
```

## Usage
- Open the app in a browser at ```bash http://127.0.0.1:5000. ```
- As attendees arrive, scan their QR code using the camera feed to authenticate them.
- If necessary, enter a barcode manually to attach it to an attendee.
- Use the following controls for attendance management:
- Reset to Scan QR Code: Clears the current session and resets the camera feed.
- Next QR Code: Prepares the application for scanning the next attendee's QR code.
- Flush Database: Clears all attendance records from the database.

## Contributing
- Fork the repository.
- Create a new branch: ```bash git checkout -b my-feature-branch. ```
- Commit your changes: ```bash git commit -m 'Add some feature'. ```
- Push to the branch: ```bash git push origin my-feature-branch. ```
- Submit a pull request.
