import pyodbc
from flask import current_app

def get_db_connection():
    conn = pyodbc.connect(
        f'DRIVER={current_app.config["DB_DRIVER"]};'
        f'SERVER={current_app.config["DB_SERVER"]};'
        f'DATABASE={current_app.config["DB_DATABASE"]};'
        f'UID={current_app.config["DB_USERNAME"]};'
        f'PWD={current_app.config["DB_PASSWORD"]};'
        'Trusted_Connection=yes;Encrypt=no'
    )
    return conn

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']