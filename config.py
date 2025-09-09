import os

# Get the absolute path of the directory where this file is located
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-hard-to-guess-secret-key'
    
    # Configure the database to use SQLite
    # The database file will be stored in an 'instance' folder
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'attendees.db')
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False