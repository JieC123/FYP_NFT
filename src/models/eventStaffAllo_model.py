import pyodbc
from datetime import datetime
import math
from config import Config

class StaffAlloModel:

    @staticmethod
    def get_events_for_staff(organiser_id):
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
    def get_unassigned_staff(event_id):
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

            # Fetch event details to get event's start and end date
            cursor.execute("""
                SELECT EventStartDate, EventEndDate
                FROM [EventDB].[dbo].[Event]
                WHERE EventID = ?
            """, (event_id,))
            event_details = cursor.fetchone()

            if not event_details:
                return []  # Event not found or invalid event ID

            event_start_date = event_details.EventStartDate
            event_end_date = event_details.EventEndDate

            # Query to fetch unassigned staff and their job periods, filtering by event period
            cursor.execute(
                """
                SELECT es.EventStaffID, es.EventStaffName, es.Role, es.JobStartPeriod, es.JobEndPeriod,
                    es.Salary, es.OneTimeFees, es.Status
                FROM [EventDB].[dbo].[EventStaff] es
                LEFT JOIN [EventDB].[dbo].[EventStaffAssignment] esa
                ON es.EventStaffID = esa.EventStaffID AND esa.EventID = ?
                WHERE es.Status = 'Active'
                AND esa.EventStaffID IS NULL
                AND es.JobStartPeriod <= ?  -- Staff job start period must be before or on event start date
                AND es.JobEndPeriod >= ?    -- Staff job end period must be after or on event end date
                """, (event_id, event_start_date, event_end_date)
            )

            staff = cursor.fetchall()

            staff_list = [{'EventStaffID': str(row.EventStaffID),
                        'EventStaffName': row.EventStaffName,
                        'Role': row.Role,
                        'JobStartPeriod': row.JobStartPeriod,
                        'JobEndPeriod': row.JobEndPeriod,
                        'Salary': row.Salary,
                        'OneTimeFees': row.OneTimeFees,
                        'Status': row.Status} for row in staff]

            return staff_list

        except pyodbc.Error as e:
            print(f"Database error: {e}")
            return []

        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def get_assigned_staff(event_id):
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

            
            query = """
                SELECT 
                    es.EventStaffID,
                    es.EventStaffName,
                    es.Role,
                    es.JobStartPeriod,
                    es.JobEndPeriod,
                    es.Salary,
                    es.OneTimeFees,
                    esa.HoursWorked,
                    esa.DateAssigned
                FROM [EventDB].[dbo].[EventStaff] es
                JOIN [EventDB].[dbo].[EventStaffAssignment] esa
                    ON es.EventStaffID = esa.EventStaffID
                WHERE esa.EventID = ?
            """

            cursor.execute(query, (event_id,))
            staff = cursor.fetchall()

            # Create a list of dictionaries with the required fields
            staff_list = [{
                'StaffID': str(row.EventStaffID),
                'StaffName': row.EventStaffName,
                'Role': row.Role,
                'JobStartPeriod': row.JobStartPeriod,
                'JobEndPeriod': row.JobEndPeriod,
                'Salary': row.Salary,
                'OneTimeFees': row.OneTimeFees,
                'HoursWorked': row.HoursWorked,
                'DateAssigned': row.DateAssigned
            } for row in staff]

            return staff_list

        except pyodbc.Error as e:
            print(f"Database error: {e}")
            return []

        finally:
            cursor.close()
            connection.close()


    @staticmethod
    def assign_staff_to_event(staff_id, event_id, job_start_period, job_end_period, event_start_date, event_end_date):
        # Validate the event's start and end period against the staff's job period
        if not (job_start_period <= event_start_date and job_end_period >= event_end_date):
            return False

        # Check if the staff member has already been assigned to an event in the same period
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

            # Fetch the event details for all previously assigned events for the staff
            cursor.execute("""
                SELECT E.EventStartDate, E.EventEndDate
                FROM [dbo].[Event] E
                JOIN [dbo].[EventStaffAssignment] ESA ON E.EventID = ESA.EventID
                WHERE ESA.EventStaffID = ? AND ESA.EventID != ? -- Exclude the new event if already assigned
            """, (staff_id, event_id))

            existing_assignments = cursor.fetchall()

            # Check if the new event overlaps with any of the previous assignments
            for assignment in existing_assignments:
                assigned_event_start_date = assignment[0]
                assigned_event_end_date = assignment[1]

                # If the new event overlaps with an existing assignment
                if not (event_end_date <= assigned_event_start_date or event_start_date >= assigned_event_end_date):
                    
                    return False  # Return False to indicate that assignment can't be done

            # Calculate hours worked (event_end_date - event_start_date)
            hours_worked = (event_end_date - event_start_date).total_seconds() / 3600.0  # hours worked as float

            # Fetch the maximum numeric ID (without the 'StfA' prefix)
            cursor.execute("""
                SELECT MAX(CAST(SUBSTRING(EventStaffAssignID, 4, 5) AS INT)) AS MaxID
                FROM [dbo].[EventStaffAssignment]
                WHERE EventStaffAssignID LIKE 'StfA%' AND TRY_CAST(SUBSTRING(EventStaffAssignID, 4, 5) AS INT) IS NOT NULL
            """)
            max_id_result = cursor.fetchone()

            # Handle the next ID to assign
            if max_id_result and max_id_result[0] is not None:
                max_id = max_id_result[0] + 1
            else:
                max_id = 1  # Start from 'StfA00001' if no records exist

            # Check if the generated ID already exists (in case there were gaps)
            while True:
                new_staff_assign_id = f"StfA{max_id:05d}"
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM [dbo].[EventStaffAssignment] 
                    WHERE EventStaffAssignID = ?
                """, (new_staff_assign_id,))
                exists = cursor.fetchone()[0]
                if exists == 0:  # ID doesn't exist, it's safe to use
                    break
                max_id += 1

            # Get the current timestamp
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Insert the new staff assignment into the database
            cursor.execute("""
                INSERT INTO [dbo].[EventStaffAssignment] 
                (EventStaffAssignID, EventStaffID, EventID, HoursWorked, DateAssigned)
                VALUES (?, ?, ?, ?, ?)
            """, (new_staff_assign_id, staff_id, event_id, hours_worked, current_time))

            connection.commit()

            return True  # Staff assigned successfully

        except pyodbc.Error as e:
            print(f"Database error while assigning staff: {e}")
            raise e
        finally:
            cursor.close()
            connection.close()






    @staticmethod
    def remove_multiple_staff_assignments(selected_staff_ids, event_id):
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

            # Prepare the query to remove multiple staff assignments
            query = """
                DELETE FROM [dbo].[EventStaffAssignment]
                WHERE EventStaffID IN ({})
                AND EventID = ?
            """.format(','.join('?' * len(selected_staff_ids)))  # Prepare placeholders for the IDs

            # Execute the query with the selected staff IDs and event ID
            cursor.execute(query, selected_staff_ids + [event_id])

            # Commit the transaction
            connection.commit()

            # Check if any rows were affected
            if cursor.rowcount > 0:
                print(f"Successfully removed staff assignments for EventID {event_id}.")
                return True
            else:
                print(f"No staff assignments found for EventID {event_id}.")
                return False

        except pyodbc.Error as e:
            print(f"Error removing staff assignments: {e}")
            return False
        finally:
            cursor.close()
            connection.close()
