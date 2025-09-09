from app import app, db
from models import Attendee
import os

# --- DUMMY DATA ---
# This data will be inserted into the database.
attendees_to_add = [
    {'first_name': 'Aisha', 'last_name': 'Khan', 'email': 'aisha.khan@example.com', 'institute': 'NIT Srinagar'},
    {'first_name': 'Vikram', 'last_name': 'Singh', 'email': 'vikram.singh@example.com', 'institute': 'IIT Delhi'},
    {'first_name': 'Priya', 'last_name': 'Sharma', 'email': 'priya.sharma@example.com', 'institute': 'IIT Bombay'},
]

# Ensure the instance folder exists
instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
if not os.path.exists(instance_path):
    os.makedirs(instance_path)

# Use the application context to interact with the database
with app.app_context():
    print("Dropping all tables...")
    db.drop_all()
    print("Creating all tables...")
    db.create_all()

    print("Adding new attendees...")
    for attendee_data in attendees_to_add:
        # Check if attendee already exists by email
        existing_attendee = Attendee.query.filter_by(email=attendee_data['email']).first()
        if not existing_attendee:
            new_attendee = Attendee(
                first_name=attendee_data['first_name'],
                last_name=attendee_data['last_name'],
                email=attendee_data['email'],
                institute=attendee_data['institute']
            )
            db.session.add(new_attendee)
    
    # Commit the changes to the database
    db.session.commit()
    print("Database has been seeded with dummy data!")
    
    # Verify the data
    all_attendees = Attendee.query.all()
    if all_attendees:
        print("\n--- Current Attendees in DB ---")
        for att in all_attendees:
            print(f"ID: {att.id}, Name: {att.first_name} {att.last_name}, Email: {att.email}")
        print("-----------------------------\n")
    else:
        print("No attendees found in the database.")