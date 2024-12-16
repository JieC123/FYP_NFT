import os
from datetime import timedelta

class Config:
    SECRET_KEY = 'your_secret_key_here'
    
    # Database settings
    DB_SERVER = r'LAPTOP-VB12GW\SQLEXPRESS01'
    DB_DATABASE = 'EventDB'
    DB_USERNAME = 'user'
    DB_PASSWORD = 'db1234'
    DB_DRIVER = '{ODBC Driver 18 for SQL Server}'
    
    # Upload settings
    UPLOAD_FOLDER = 'src/image'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # IPFS settings
    IPFS_API_ENDPOINT = '/ip4/127.0.0.1/tcp/5001'
    IPFS_GATEWAY = 'http://localhost:8080/ipfs'
    
    # Mail settings
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'angjc-pm21@student.tarc.edu.my'
    MAIL_PASSWORD = 'wmch bmfb butz uwyl'
    MAIL_DEFAULT_SENDER = 'angjc-pm21@student.tarc.edu.my'