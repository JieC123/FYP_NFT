import pyodbc
from flask import request, jsonify
from datetime import datetime
from config import Config
import random
import math


class BoothAlloModel:

    @staticmethod
    def get_events_for_booth(organiser_id):
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

            cursor.execute(
                """
                SELECT EventID, EventTitle
                FROM [dbo].[Event]
                WHERE OrganiserID = ?
                ORDER BY EventTitle
                """, (organiser_id,)
            )

            events = cursor.fetchall()

            event_list = [{'EventID': str(row.EventID), 'EventTitle': row.EventTitle} for row in events]

            return event_list

        except pyodbc.Error as e:
            print(f"Database error: {e}")
            return []

        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def get_event_details(event_id):
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

            cursor.execute(
                """
                SELECT EventTitle, EventStartDate, EventEndDate
                FROM [dbo].[Event]
                WHERE EventID = ?
                """, (event_id,)
            )

            event_details = cursor.fetchone()

            return {
                'EventTitle': event_details.EventTitle,
                'EventStartDate': event_details.EventStartDate,
                'EventEndDate': event_details.EventEndDate
            }

        except pyodbc.Error as e:
            print(f"Database error: {e}")
            return None

        finally:
            cursor.close()
            connection.close()

    
    @staticmethod
    def get_unassigned_booths(event_id):
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

            # Updated query to fetch only necessary attributes for unassigned exhibitors
            cursor.execute(
                """
                SELECT e.ExhibitorID, e.ExhibitorName, e.Company, e.BoothCategory, 
                    e.BoothSize, e.BoothRentalFees, e.Status
                FROM [dbo].[ExhibitorAndBooth] e
                LEFT JOIN [dbo].[ExhibitorAndBoothAssignment] a
                ON e.ExhibitorID = a.ExhibitorID AND a.EventID = ?
                WHERE e.Status = 'Active' AND a.ExhibitorID IS NULL
                """, (event_id,)
            )

            booths = cursor.fetchall()

            # Construct a list of dictionaries from the query result
            booth_list = [{
                'ExhibitorID': row.ExhibitorID,
                'ExhibitorName': row.ExhibitorName,
                'Company': row.Company,
                'BoothCategory': row.BoothCategory,
                'BoothSize': row.BoothSize,
                'BoothRentalFees': row.BoothRentalFees,
                'Status': row.Status
            } for row in booths]

            return booth_list

        except pyodbc.Error as e:
            print(f"Database error: {e}")
            return []  # Return an empty list on error

        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def get_assigned_booths(event_id):
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

            # Updated query to fetch the necessary details from both tables
            cursor.execute(
                """
                SELECT 
                    e.ExhibitorID, 
                    e.ExhibitorName, 
                    e.Company, 
                    e.BoothCategory, 
                    e.BoothSize, 
                    e.BoothRentalFees,
                    a.RentalStartDate,
                    a.RentalEndDate,
                    a.TotalRentalDays,
                    a.DateAssigned
                FROM [dbo].[ExhibitorAndBooth] e
                INNER JOIN [dbo].[ExhibitorAndBoothAssignment] a 
                    ON e.ExhibitorID = a.ExhibitorID
                    AND a.EventID = ?
                WHERE a.EventID = ? AND e.Status = 'Active'
                """, (event_id, event_id)
            )

            booths = cursor.fetchall()

            # Construct a list of dictionaries with the relevant data
            booth_list = [{
                'ExhibitorID': row.ExhibitorID,
                'ExhibitorName': row.ExhibitorName,
                'Company': row.Company,
                'BoothCategory': row.BoothCategory,
                'BoothSize': row.BoothSize,
                'BoothRentalFees': row.BoothRentalFees,
                'RentalStartDate': row.RentalStartDate,
                'RentalEndDate': row.RentalEndDate,
                'TotalRentalDays': row.TotalRentalDays,
                'DateAssigned': row.DateAssigned
            } for row in booths]

            return booth_list

        except pyodbc.Error as e:
            print(f"Database error: {e}")
            return []

        finally:
            cursor.close()
            connection.close()


    
    @staticmethod
    def assign_booth_to_event(exhibitor_id, event_id, rental_start_date, rental_end_date, rental_days):
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

            # Calculate rental days with the new logic
            if isinstance(rental_start_date, str):
                rental_start_date = datetime.strptime(rental_start_date, '%Y-%m-%d')
            if isinstance(rental_end_date, str):
                rental_end_date = datetime.strptime(rental_end_date, '%Y-%m-%d')

            # Calculate the time difference in hours
            time_diff = rental_end_date - rental_start_date
            hours_diff = time_diff.total_seconds() / 3600  # Convert to hours

            # Calculate rental days:
            # If less than 24 hours, count as 1 day
            # If more than 24 hours, round up to next day
            if hours_diff <= 24:
                rental_days = 1
            else:
                rental_days = math.ceil(hours_diff / 24)

            # Find the smallest available ExhibitorAssignID
            cursor.execute("""
                SELECT TOP 1 new_id
                FROM (
                    SELECT 
                        'ExhA' + RIGHT('00000' + CAST(ROW_NUMBER() OVER (ORDER BY ExhibitorAssignID) AS VARCHAR), 5) AS new_id
                    FROM [dbo].[ExhibitorAndBoothAssignment]
                    WHERE ExhibitorAssignID LIKE 'ExhA%'
                ) AS ids
                WHERE new_id NOT IN (SELECT ExhibitorAssignID FROM [dbo].[ExhibitorAndBoothAssignment])
            """)
            result = cursor.fetchone()

            # Generate the new ID
            if result:
                new_id = result[0]
            else:
                cursor.execute("""
                    SELECT MAX(CAST(SUBSTRING(ExhibitorAssignID, 5, 5) AS INT)) AS MaxID
                    FROM [dbo].[ExhibitorAndBoothAssignment]
                    WHERE ExhibitorAssignID LIKE 'ExhA%' 
                """)
                max_id = cursor.fetchone()[0]
                new_id = f"ExhA{(max_id + 1):05d}" if max_id is not None else "ExhA00001"

            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
                INSERT INTO [dbo].[ExhibitorAndBoothAssignment] 
                (ExhibitorAssignID, ExhibitorID, EventID, RentalStartDate, RentalEndDate, TotalRentalDays, DateAssigned)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (new_id, exhibitor_id, event_id, rental_start_date, rental_end_date, rental_days, current_time))

            connection.commit()
            print(f"Booth {exhibitor_id} assigned to event {event_id} with ID {new_id} for {rental_days} days.")

        except pyodbc.Error as e:
            print(f"Database error while assigning booth: {e}")
            raise e
        finally:
            cursor.close()
            connection.close()


    @staticmethod
    def remove_multiple_booth_assignments(booth_ids, event_id):
        connection_string = (
            f"DRIVER={Config.DRIVER};"
            f"SERVER={Config.SERVER};"
            f"DATABASE={Config.DATABASE};"
            "Trusted_Connection=yes;"
            "Encrypt=no;"
        )

        try:
            connection = pyodbc.connect(connection_string)
            cursor = connection.cursor()

            # Prepare the query to remove booth assignments based on ExhibitorID
            query = """
                DELETE FROM [dbo].[ExhibitorAndBoothAssignment]
                WHERE ExhibitorID IN ({})  -- Correctly using ExhibitorID
                AND EventID = ?  -- Match the EventID
            """.format(','.join('?' * len(booth_ids)))  # Prepare placeholders for the booth IDs

            # Execute the query with the booth IDs and event ID
            cursor.execute(query, booth_ids + [event_id])

            # Commit the transaction
            connection.commit()

            # Check if any rows were affected
            if cursor.rowcount > 0:
                print(f"Successfully removed booth assignments for EventID {event_id}.")
                return True
            else:
                print(f"No booth assignments found for EventID {event_id}.")
                return False

        except pyodbc.Error as e:
            print(f"Error removing booth assignments: {e}")
            return False
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def get_booths_for_event(event_id):
        connection_string = (
            f"DRIVER={Config.DRIVER};"
            f"SERVER={Config.SERVER};"
            f"DATABASE={Config.DATABASE};"
            "Trusted_Connection=yes;"
            "Encrypt=no;"
        )

        try:
            # Establish connection to the database
            connection = pyodbc.connect(connection_string)
            cursor = connection.cursor()

            # Generate random latitude and longitude values between 200 and 300
            random_latitude = random.uniform(200, 300)  # Random latitude between 200 and 300
            random_longitude = random.uniform(200, 300)  # Random longitude between 200 and 300

            # Prepare the SQL query to fetch booths and exhibitor assignments for the selected event
            query = """
                SELECT eb.ExhibitorID, eb.ExhibitorName, eb.ExhibitorEmail, eb.ExhibitorContactInfo, 
                    eb.Company, eb.Status, eb.BoothCategory, eb.BoothSize, eb.BoothRentalFees,
                    eba.ExhibitorAssignID, eba.RentalStartDate, eba.RentalEndDate, eba.TotalRentalDays, eba.DateAssigned
                FROM ExhibitorAndBoothAssignment eba
                JOIN ExhibitorAndBooth eb ON eba.ExhibitorID = eb.ExhibitorID
                WHERE eba.EventID = ?
            """

            # Execute the query with the event_id as parameter
            cursor.execute(query, (event_id,))

            # Fetch all the results
            booths = cursor.fetchall()

            # Process booth data and return it
            booth_data = []
            for booth in booths:
                booth_data.append({
                    'id': booth.ExhibitorAssignID,
                    'lat': random_latitude,  # Use the random latitude
                    'lon': random_longitude,  # Use the random longitude
                    'name': booth.ExhibitorName,
                    'email': booth.ExhibitorEmail,
                    'contact_info': booth.ExhibitorContactInfo,
                    'company': booth.Company,
                    'status': booth.Status,
                    'booth_category': booth.BoothCategory,
                    'booth_size': booth.BoothSize,
                    'rental_fees': booth.BoothRentalFees,
                    'rental_start': booth.RentalStartDate,
                    'rental_end': booth.RentalEndDate,
                    'total_rental_days': booth.TotalRentalDays
                })

            return booth_data

        except pyodbc.Error as e:
            print(f"Error fetching booths for event {event_id}: {e}")
            return []

        finally:
            # Ensure cursor and connection are properly closed
            cursor.close()
            connection.close()