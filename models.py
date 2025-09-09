from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Attendee(db.Model):
    """
    Represents an attendee in the database.
    """
    __tablename__ = 'attendees'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    institute = db.Column(db.String(150), nullable=False)
    band_id = db.Column(db.String(50), nullable=True, unique=True)
    # <-- NEW FEATURE: Add an 'entry' column to track attendance
    entry = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f'<Attendee {self.first_name} {self.last_name}>'