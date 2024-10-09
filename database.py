from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)

# Attendees model (matches the updated attendees table)
class Attendees(db.Model):
    __tablename__ = 'attendees'
    
    attendee_id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    contact_number = db.Column(db.String(15), nullable=False)
    band_id = db.Column(db.String(50), nullable=True, default=None)
    entry = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Attendees {self.first_name} {self.last_name}, ID: {self.id}>'
    
class Attendance(db.Model):
    __tablename__ = 'attendance'
    
    attendee_id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    contact_number = db.Column(db.String(15), nullable=False)
    band_id = db.Column(db.String(50), nullable=True, default=None)
    entry = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Attendance {self.first_name} {self.last_name}, ID: {self.id}>'

# Create the database and tables if they don't already exist
with app.app_context():
    db.create_all()
