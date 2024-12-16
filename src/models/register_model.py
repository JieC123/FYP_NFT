from config import Config
import pyodbc

class RegisterModel:

    @staticmethod
    def get_next_organiser_id():
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

            # Fetch the current highest OrganiserID
            cursor.execute("SELECT MAX(CAST(SUBSTRING(OrganiserID, 4, LEN(OrganiserID)) AS INT)) FROM Organiser")
            max_id = cursor.fetchone()[0]

            if max_id is None:
                next_id = "ORG00001"
            else:
                next_id = f"ORG{str(max_id + 1).zfill(5)}"

            return next_id

        except pyodbc.Error as e:
            print("Database error: ", e)
            raise

        finally:
            cursor.close()
            connection.close()


    @staticmethod
    def email_exists(email):
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
            cursor.execute("SELECT 1 FROM Organiser WHERE OrganiserEmail = ?", (email,))
            result = cursor.fetchone()
            return result is not None

        except pyodbc.Error as e:
            print("Database error: ", e)
            raise

        finally:
            cursor.close()
            connection.close()


    @staticmethod
    def register_user(full_name, ic_no, email, contact_no, password, profile_image_path):
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

            # Generate the next OrganiserID
            organiser_id = RegisterModel.get_next_organiser_id()

            # Insert new organiser into the database (without DateCreated)
            cursor.execute(
                """
                INSERT INTO [dbo].[Organiser] (
                    OrganiserID, OrganiserName, IC, OrganiserEmail, 
                    OrganiserContactNo, OrganiserProfileImage, EventHistoryCount, Password, AccountStatus
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    organiser_id,
                    full_name,
                    ic_no,
                    email,
                    contact_no,
                    profile_image_path,
                    0,  # EventHistoryCount starts at 0 for new organisers
                    password,  # Ensure password is hashed securely
                    "Active"  # AccountStatus starts as 'Active'
                )
            )

            connection.commit()

        except pyodbc.Error as e:
            print("Database error: ", e)
            raise

        finally:
            cursor.close()
            connection.close()