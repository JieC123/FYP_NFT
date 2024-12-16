# src/models/profile_model.py
from config import Config
import pyodbc

class ProfileModel:
    @staticmethod
    def get_profile_by_id(organiser_id):
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

            # Retrieve profile information by organiser ID
            cursor.execute(
                """
                SELECT OrganiserID, OrganiserName, IC, OrganiserEmail, OrganiserContactNo, 
                    OrganiserProfileImage, AccountStatus
                FROM Organiser
                WHERE OrganiserID = ?
                """,
                (organiser_id,)
            )
            profile_data = cursor.fetchone()

            # Fetch dynamic EventHistoryCount based on organiser ID
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM Event
                WHERE OrganiserID = ?
                """,
                (organiser_id,)
            )
            event_count_data = cursor.fetchone()
            event_history_count = event_count_data[0] if event_count_data else 0  # Accessing the count correctly

            if profile_data:
                profile = {
                    "id": profile_data[0],
                    "name": profile_data[1],
                    "ic": profile_data[2],
                    "email": profile_data[3],
                    "contact_no": profile_data[4],
                    "profile_image": profile_data[5],
                    "event_history_count": event_history_count,
                    "account_status": profile_data[6]
                }
                return profile
            else:
                return None

        except pyodbc.Error as e:
            print("Database error: ", e)
            raise

        finally:
            cursor.close()
            connection.close()



    @staticmethod
    def update_profile(organiser_id, name, contact_no, ic_no, password=None, profile_image=None):
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

            update_query = """
                UPDATE [dbo].[Organiser]
                SET OrganiserName = ?, OrganiserContactNo = ?, IC = ?
            """
            params = [name, contact_no, ic_no]

            if password:
                update_query += ", Password = ?"
                params.append(password)

            if profile_image:
                update_query += ", OrganiserProfileImage = ?"
                params.append(profile_image)

            update_query += " WHERE OrganiserID = ?"
            params.append(organiser_id)

            cursor.execute(update_query, tuple(params))
            connection.commit()

        except pyodbc.Error as e:
            print("Database error: ", e)
            raise

        finally:
            cursor.close()
            connection.close()

