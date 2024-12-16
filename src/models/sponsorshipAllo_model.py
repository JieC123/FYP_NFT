import pyodbc
from flask import request, jsonify
from datetime import datetime
from config import Config  # Assuming you have a Config class to hold DB connection details

class SponsorshipAlloModel:
    @staticmethod
    def get_events_for_sponsorship(organiser_id):
        # Build connection string using Config values
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

            # Query to fetch events for the logged-in organiser
            cursor.execute(
                """
                SELECT EventID, EventTitle
                FROM [dbo].[Event]
                WHERE OrganiserID = ?
                ORDER BY EventTitle
                """, (organiser_id,)  # Pass the organiser_id parameter safely
            )

            events = cursor.fetchall()

            # Debugging: Print the raw data fetched from the database
            print("Raw events from DB:", events)  # This should show a list of tuples, e.g., [(Eve00001, 'Event1'), (Eve00002, 'Event2')]

            # Convert the fetched data into a list of dictionaries
            event_list = [{'EventID': str(row.EventID), 'EventTitle': row.EventTitle} for row in events]

            # Debugging: print the transformed event list
            print("Transformed event list:", event_list)  # Check if this is correct

            return event_list

        except pyodbc.Error as e:
            print(f"Database error: {e}")
            return []  # Return an empty list on error

        finally:
            cursor.close()
            connection.close()

   
    @staticmethod
    def get_event_details(event_id):
        # Build connection string using Config values
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

            # Query to fetch the details of a specific event
            cursor.execute(
                """
                SELECT EventID, EventTitle, EventStartDate, EventEndDate
                FROM [dbo].[Event]
                WHERE EventID = ?
                """, (event_id,)
            )

            event = cursor.fetchone()
            if event:
                return {
                    'EventID': str(event.EventID),
                    'EventTitle': event.EventTitle,
                    'EventStartDate': event.EventStartDate,
                    'EventEndDate': event.EventEndDate
                }

            return None

        except pyodbc.Error as e:
            print(f"Database error: {e}")
            return None

        finally:
            cursor.close()
            connection.close()


    @staticmethod
    def get_sponsorships():
        # Building the connection string using Config values
        connection_string = (
            f"DRIVER={Config.DRIVER};"
            f"SERVER={Config.SERVER};"
            f"DATABASE={Config.DATABASE};"
            "Trusted_Connection=yes;"
            "Encrypt=no;"
        )
        
        try:
            # Connect to the database using the connection string
            connection = pyodbc.connect(connection_string)
            cursor = connection.cursor()

            # Execute your SQL query
            cursor.execute("SELECT SponsorshipID, SponsorshipName, Company, Status, AmountContributed FROM [dbo].[Sponsorship]")
            sponsorships = cursor.fetchall()

            # Return the result as a list of dictionaries, formatting the AmountContributed as a currency string
            return [
                {
                    'SponsorshipID': row.SponsorshipID,
                    'SponsorshipName': row.SponsorshipName,
                    'Company': row.Company,
                    'Status': row.Status,
                    'AmountContributed': f"${row.AmountContributed:,.2f}"  # Format as currency
                }
                for row in sponsorships
            ]
        except pyodbc.Error as e:
            print(f"Error fetching sponsorship data: {e}")
            return []
        finally:
            cursor.close()
            connection.close()



    @staticmethod
    def get_unassigned_sponsorships(event_id):
        connection_string = (
            f"DRIVER={Config.DRIVER};"
            f"SERVER={Config.SERVER};"
            f"DATABASE={Config.DATABASE};"
            "Trusted_Connection=yes;"
            "Encrypt=no;"
        )

        try:
            # Establish the connection to the database
            connection = pyodbc.connect(connection_string)
            cursor = connection.cursor()

            # Query to get sponsorships that are NOT assigned to the selected event and are Active
            cursor.execute("""
            SELECT s.SponsorshipID, s.SponsorshipName, s.Company, s.SponsorDetail, 
                s.PaymentSchedule, s.Status, s.AmountContributed
            FROM [dbo].[Sponsorship] s
            LEFT JOIN [dbo].[SponsorshipAssignment] sa
            ON s.SponsorshipID = sa.SponsorshipID
            WHERE (sa.SponsorAssignID IS NULL OR sa.EventID != ?)
            AND s.Status = 'Active'
            """, (event_id,))

            # Fetch all the results
            sponsorships = cursor.fetchall()
            
            # Convert the result to a list of dictionaries
            return [
                {
                    'SponsorshipID': row.SponsorshipID,
                    'SponsorshipName': row.SponsorshipName,
                    'Company': row.Company,
                    'SponsorDetail': row.SponsorDetail,
                    'PaymentSchedule': row.PaymentSchedule,
                    'Status': row.Status,
                    'AmountContributed': row.AmountContributed
                }
                for row in sponsorships
            ]

        except pyodbc.Error as e:
            print(f"Error fetching unassigned sponsorships: {e}")
            return []
        
        finally:
            # Ensure that the cursor and connection are closed
            cursor.close()
            connection.close()




    @staticmethod
    def get_assigned_sponsorships(event_id):
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

            # Query to get sponsorships that are assigned to the selected event
            cursor.execute("""
                SELECT s.SponsorshipID, s.SponsorshipName, s.Company, s.SponsorDetail, 
                    s.PaymentSchedule, s.AmountContributed, sa.DateAssigned
                FROM [dbo].[Sponsorship] s
                JOIN [dbo].[SponsorshipAssignment] sa
                ON s.SponsorshipID = sa.SponsorshipID
                WHERE sa.EventID = ?
            """, (event_id,))

            sponsorships = cursor.fetchall()
            
            # Convert the result to a list of dictionaries
            return [
                {
                    'SponsorshipID': row.SponsorshipID,
                    'SponsorshipName': row.SponsorshipName,
                    'Company': row.Company,
                    'SponsorDetail': row.SponsorDetail,
                    'PaymentSchedule': row.PaymentSchedule,
                    'AmountContributed': row.AmountContributed,
                    'DateAssigned': row.DateAssigned
                }
                for row in sponsorships
            ]

        except pyodbc.Error as e:
            print(f"Error fetching assigned sponsorships: {e}")
            return []
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def assign_sponsorship_to_event(sponsorship_id, event_id):
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

            # Generate SponsorAssignID (e.g., SpA00001, SpA00002)
            cursor.execute("""
                SELECT MAX(CAST(SUBSTRING(SponsorAssignID, 4, 5) AS INT)) AS MaxID
                FROM [dbo].[SponsorshipAssignment]
            """)
            max_id = cursor.fetchone()[0]

            # Increment the ID and format it to the required "SpA0000X" format
            new_id = f"SpA{(max_id + 1):05d}" if max_id is not None else "SpA00001"

            # Get the current timestamp from the user’s system in the format "YYYY-MM-DD HH:MM:SS"
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Insert the new sponsorship assignment into the SponsorshipAssignment table
            cursor.execute("""
                INSERT INTO [dbo].[SponsorshipAssignment] (SponsorAssignID, SponsorshipID, EventID, DateAssigned)
                VALUES (?, ?, ?, ?)
            """, (new_id, sponsorship_id, event_id, current_time))

            connection.commit()
            print(f"Sponsorship {sponsorship_id} successfully assigned to event {event_id}.")

        except pyodbc.Error as e:
            print(f"Error assigning sponsorship: {e}")
            raise e
        finally:
            cursor.close()
            connection.close()


    @staticmethod
    def remove_multiple_sponsorship_assignments(sponsorship_ids, event_id):
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

            # Prepare the query to remove multiple sponsorship assignments
            query = """
                DELETE FROM [dbo].[SponsorshipAssignment]
                WHERE SponsorshipID IN ({})
                AND EventID = ?
            """.format(','.join('?' * len(sponsorship_ids)))  # Prepare placeholders for the IDs

            # Execute the query with the sponsorship IDs and event ID
            cursor.execute(query, sponsorship_ids + [event_id])

            # Commit the transaction
            connection.commit()

            # Check if any rows were affected
            if cursor.rowcount > 0:
                print(f"Successfully removed sponsorship assignments for EventID {event_id}.")
                return True
            else:
                print(f"No sponsorship assignments found for EventID {event_id}.")
                return False

        except pyodbc.Error as e:
            print(f"Error removing sponsorship assignments: {e}")
            return False
        finally:
            cursor.close()
            connection.close()

    