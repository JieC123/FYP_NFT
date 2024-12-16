import pyodbc
import random
import bcrypt
from config import Config  # Make sure config.py has DB configurations

class ResetPasswordModel:
    @staticmethod
    def generate_verification_code():
        return random.randint(100000, 999999)  # Generates a 6-digit code

    @staticmethod
    def get_user_by_email(email):
        connection_string = (
            f"DRIVER={Config.DRIVER};"
            f"SERVER={Config.SERVER};"
            f"DATABASE={Config.DATABASE};"
            'Trusted_Connection=yes;'
            'Encrypt=no;'
        )

        try:
            connection = pyodbc.connect(connection_string)
            cursor = connection.cursor()
            # Query to fetch user details
            cursor.execute(
                'SELECT OrganiserID, OrganiserEmail FROM Organiser WHERE OrganiserEmail = ?',
                (email,)
            )
            organiser = cursor.fetchone()  # Fetch the first matching user

            if organiser:
                return {
                    "OrganiserID": organiser[0],
                    "OrganiserEmail": organiser[1],
                }
            else:
                return None

        except pyodbc.Error as e:
            print("Database error: ", e)
            raise

        finally:
            cursor.close()
            connection.close()



    @staticmethod
    def update_user_password(email, new_password):
        connection_string = (
            f"DRIVER={Config.DRIVER};"
            f"SERVER={Config.SERVER};"
            f"DATABASE={Config.DATABASE};"
            'Trusted_Connection=yes;'
            'Encrypt=no;'
        )

        try:
            connection = pyodbc.connect(connection_string)
            cursor = connection.cursor()

            # Encrypt the password with bcrypt
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())

            # Update password in the database
            cursor.execute(
                'UPDATE Organiser SET Password = ? WHERE OrganiserEmail = ?',
                (hashed_password, email)
            )
            connection.commit()  # Commit changes to the database

        except pyodbc.Error as e:
            print("Database error: ", e)
            raise

        finally:
            cursor.close()
            connection.close()
