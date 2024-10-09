import os

class Config:
    # PostgreSQL database URI for authentication_data
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI', 'mysql+pymysql://mirdanish:Password123%40%23%24@localhost:3306/authentication_data')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
