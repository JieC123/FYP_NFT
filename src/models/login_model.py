# src/models/login_model.py

from config import Config
import pyodbc

class LoginModel:
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
                'SELECT OrganiserID, OrganiserName, IC, OrganiserEmail, OrganiserContactNo, OrganiserProfileImage, EventHistoryCount, Password, AccountStatus FROM Organiser WHERE OrganiserEmail = ?',
                (email,)
            )
            organiser = cursor.fetchone()  # Fetch the first matching user

            if organiser:
                return {
                    "OrganiserID": organiser[0],
                    "OrganiserName": organiser[1],
                    "IC": organiser[2],
                    "OrganiserEmail": organiser[3],
                    "OrganiserContactNo": organiser[4],
                    "OrganiserProfileImage": organiser[5],
                    "EventHistoryCount": organiser[6],
                    "Password": organiser[7],
                    "AccountStatus": organiser[8]
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
    def get_user_by_id(organiser_id):
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

            # Query to fetch organiser's name by OrganiserID
            cursor.execute(
                '''SELECT OrganiserName FROM Organiser WHERE OrganiserID = ?''',
                (organiser_id,)
            )
            organiser = cursor.fetchone()  # Fetch the organiser by ID

            if organiser:
                return organiser[0]  # Return the OrganiserName
            else:
                return None

        except pyodbc.Error as e:
            print("Database error: ", e)
            raise

        finally:
            cursor.close()
            connection.close()