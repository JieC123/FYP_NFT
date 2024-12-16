from config import Config
import pyodbc
from datetime import datetime
from math import ceil

class ParticipantModel:


    @staticmethod
    def get_all_participants(event_ids=None):
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
                    p.ParticipantID,
                    p.RegistrationDate as ParticipantRegistrationDate,
                    u.UserName,
                    u.UserEmail,
                    u.UserContactInfo,
                    e.EventTitle
                FROM [dbo].[Participants] p
                JOIN [dbo].[TicketingUser] u ON p.UserID = u.UserID
                JOIN [dbo].[Event] e ON p.EventID = e.EventID
            """
            
            # Add event filter if specified
            if event_ids:
                placeholders = ','.join('?' * len(event_ids))
                query += f" WHERE p.EventID IN ({placeholders})"
                cursor.execute(query, event_ids)
            else:
                cursor.execute(query)

            participants = cursor.fetchall()

            participant_list = [
                {
                    "ParticipantID": row.ParticipantID,
                    "ParticipantName": row.UserName,
                    "ParticipantEmail": row.UserEmail,
                    "ParticipantContactInfo": row.UserContactInfo,
                    "RegistrationDate": row.ParticipantRegistrationDate,
                    "EventTitle": row.EventTitle
                }
                for row in participants
            ]
            return participant_list

        except pyodbc.Error as e:
            print("Database error: ", e)
            return None

        finally:
            cursor.close()
            connection.close()
        


    @staticmethod
    def search_participants(query):
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

            if not query:
                return ParticipantModel.get_all_participants()
            else:
                cursor.execute(
                    """
                    SELECT 
                        p.ParticipantID,
                        p.RegistrationDate as ParticipantRegistrationDate,
                        u.UserName,
                        u.UserEmail,
                        u.UserContactInfo,
                        e.EventTitle
                    FROM [dbo].[Participants] p
                    JOIN [dbo].[TicketingUser] u ON p.UserID = u.UserID
                    JOIN [dbo].[Event] e ON p.EventID = e.EventID
                    WHERE u.UserName LIKE ?
                    ORDER BY p.ParticipantID
                    """,
                    (f'%{query}%',)
                )

            participants = cursor.fetchall()

            participant_list = [
                {
                    "ParticipantID": row.ParticipantID,
                    "ParticipantName": row.UserName,
                    "ParticipantEmail": row.UserEmail,
                    "ParticipantContactInfo": row.UserContactInfo,
                    "RegistrationDate": row.ParticipantRegistrationDate,
                    "EventTitle": row.EventTitle
                }
                for row in participants
            ]
            
            return participant_list

        except pyodbc.Error as e:
            print("Database error: ", e)
            return []

        finally:
            cursor.close()
            connection.close()


    @staticmethod
    def get_user_by_id(user_id):
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
                SELECT UserID, UserName, UserEmail, UserContactInfo
                FROM [dbo].[TicketingUser]
                WHERE UserID = ?
                """,
                (user_id,)
            )
            
            row = cursor.fetchone()
            if row:
                return {
                    'UserID': row.UserID,
                    'UserName': row.UserName,
                    'UserEmail': row.UserEmail,
                    'UserContactInfo': row.UserContactInfo
                }
            return None

        except pyodbc.Error as e:
            print("Database error: ", e)
            return None

        finally:
            cursor.close()
            connection.close()


    @staticmethod
    def get_all_events():
        # Get the current organizer ID from session
        from flask import session
        organiser_id = session.get('organiser_id')

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
                """,
                (organiser_id,)
            )
            
            events = cursor.fetchall()
            event_list = [
                {
                    "EventID": row.EventID,
                    "EventTitle": row.EventTitle
                }
                for row in events
            ]
            return event_list

        except pyodbc.Error as e:
            print("Database error: ", e)
            return []

        finally:
            cursor.close()
            connection.close()


    @staticmethod
    def get_next_participant_id():
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

            cursor.execute("SELECT MAX(ParticipantID) FROM [dbo].[Participants]")
            last_id = cursor.fetchone()[0]

            if last_id:
                # Extract the numeric part and increment
                num = int(last_id[1:]) + 1
            else:
                num = 1

            # Format new ID with leading zeros
            new_id = f"P{num:06d}"
            return new_id

        except pyodbc.Error as e:
            print("Database error: ", e)
            return None
        finally:
            cursor.close()
            connection.close()


    @staticmethod
    def add_participant(user_id, event_id, registration_date):
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

            # Get next participant ID
            participant_id = ParticipantModel.get_next_participant_id()
            if not participant_id:
                raise Exception("Failed to generate participant ID")

            # Check if participant already exists for this event
            cursor.execute(
                """
                SELECT COUNT(*) 
                FROM [dbo].[Participants] 
                WHERE UserID = ? AND EventID = ?
                """,
                (user_id, event_id)
            )
            if cursor.fetchone()[0] > 0:
                raise Exception("Participant already registered for this event")

            # Convert registration_date string to datetime
            try:
                # Parse the date string to datetime object
                registration_datetime = datetime.strptime(registration_date, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                raise Exception("Invalid date format. Expected format: YYYY-MM-DD HH:MM:SS")

            # Insert new participant with the datetime object
            cursor.execute(
                """
                INSERT INTO [dbo].[Participants]
                (ParticipantID, RegistrationDate, EventID, UserID)
                VALUES (?, ?, ?, ?)
                """,
                (participant_id, registration_datetime, event_id, user_id)
            )
            connection.commit()
            return True

        except pyodbc.Error as e:
            print("Database error: ", e)
            raise Exception(f"Database error: {str(e)}")
        except Exception as e:
            print("Error: ", e)
            raise
        finally:
            cursor.close()
            connection.close()


    @staticmethod
    def delete_participants(participant_ids):
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

            # Convert list of participant IDs to a format suitable for the SQL query
            ids_tuple = tuple(participant_ids)
            
            # If only one ID, we need to handle the tuple syntax differently
            if len(ids_tuple) == 1:
                query = "DELETE FROM [dbo].[Participants] WHERE ParticipantID = ?"
                cursor.execute(query, ids_tuple[0])
            else:
                placeholders = ','.join(['?' for _ in ids_tuple])
                query = f"DELETE FROM [dbo].[Participants] WHERE ParticipantID IN ({placeholders})"
                cursor.execute(query, ids_tuple)
                
            connection.commit()
            return True

        except pyodbc.Error as e:
            print("Database error: ", e)
            return False
        except Exception as e:
            print("Error: ", e)
            return False
        finally:
            cursor.close()
            connection.close()


    @staticmethod
    def get_participant_by_id(participant_id):
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
                SELECT 
                    p.ParticipantID,
                    p.UserID,
                    p.EventID,
                    p.RegistrationDate,
                    u.UserName,
                    u.UserEmail,
                    u.UserContactInfo,
                    e.EventTitle
                FROM [dbo].[Participants] p
                JOIN [dbo].[TicketingUser] u ON p.UserID = u.UserID
                JOIN [dbo].[Event] e ON p.EventID = e.EventID
                WHERE p.ParticipantID = ?
                """,
                (participant_id,)
            )
            
            row = cursor.fetchone()
            if row:
                return {
                    'ParticipantID': row.ParticipantID,
                    'UserID': row.UserID,
                    'EventID': row.EventID,
                    'RegistrationDate': row.RegistrationDate,
                    'UserName': row.UserName,
                    'UserEmail': row.UserEmail,
                    'UserContactInfo': row.UserContactInfo,
                    'EventTitle': row.EventTitle
                }
            return None

        except pyodbc.Error as e:
            print("Database error: ", e)
            return None
        finally:
            cursor.close()
            connection.close()


    @staticmethod
    def update_participant(participant_id, user_id, event_id, registration_date):
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

            # Convert registration_date string to datetime if it's a string
            if isinstance(registration_date, str):
                registration_date = datetime.strptime(registration_date, '%Y-%m-%dT%H:%M')

            cursor.execute(
                """
                UPDATE [dbo].[Participants]
                SET EventID = ?,
                    RegistrationDate = ?
                WHERE ParticipantID = ? AND UserID = ?
                """,
                (event_id, registration_date, participant_id, user_id)
            )
            
            connection.commit()
            return True

        except pyodbc.Error as e:
            print("Database error: ", e)
            return False
        finally:
            cursor.close()
            connection.close()


    @staticmethod
    def insert_participant_data(records):
        connection_string = (
            f"DRIVER={Config.DRIVER};"
            f"SERVER={Config.SERVER};"
            f"DATABASE={Config.DATABASE};"
            'Trusted_Connection=yes;'
            'Encrypt=no;'
        )

        success_count = 0
        try:
            with pyodbc.connect(connection_string) as connection:
                cursor = connection.cursor()
                
                for record in records:
                    try:
                        query = """
                            INSERT INTO [dbo].[Participants] 
                            (ParticipantID, RegistrationDate, EventID, UserID) 
                            VALUES (?, ?, ?, ?)
                        """
                        
                        cursor.execute(
                            query,
                            (
                                record['ParticipantID'],
                                record['RegistrationDate'],
                                record['EventID'],
                                record['UserID']
                            )
                        )
                        success_count += 1
                    except Exception as e:
                        print(f"Error inserting record {record['ParticipantID']}: {str(e)}")
                        continue

                connection.commit()
                return success_count

        except Exception as e:
            print(f"Database error in insert_participant_data: {str(e)}")
            raise


    @staticmethod
    def get_existing_participant_ids():
        connection_string = (
            f"DRIVER={Config.DRIVER};"
            f"SERVER={Config.SERVER};"
            f"DATABASE={Config.DATABASE};"
            'Trusted_Connection=yes;'
            'Encrypt=no;'
        )

        try:
            with pyodbc.connect(connection_string) as connection:
                cursor = connection.cursor()
                cursor.execute("SELECT ParticipantID FROM [dbo].[Participants]")
                return set(row[0] for row in cursor.fetchall())
        except Exception as e:
            print(f"Error getting existing participant IDs: {e}")
            return set()

    @staticmethod
    def get_existing_user_event_combinations():
        connection_string = (
            f"DRIVER={Config.DRIVER};"
            f"SERVER={Config.SERVER};"
            f"DATABASE={Config.DATABASE};"
            'Trusted_Connection=yes;'
            'Encrypt=no;'
        )

        try:
            with pyodbc.connect(connection_string) as connection:
                cursor = connection.cursor()
                cursor.execute("SELECT UserID, EventID FROM [dbo].[Participants]")
                return set(f"{row[0]}-{row[1]}" for row in cursor.fetchall())
        except Exception as e:
            print(f"Error getting existing user-event combinations: {e}")
            return set()

    @staticmethod
    def delete_selected_participants(participant_ids):
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

            # Convert list to tuple for SQL query
            ids_tuple = tuple(participant_ids)
            
            # Handle single ID case
            if len(ids_tuple) == 1:
                query = "DELETE FROM [dbo].[Participants] WHERE ParticipantID = ?"
                cursor.execute(query, ids_tuple[0])
            else:
                # Handle multiple IDs
                placeholders = ','.join(['?' for _ in ids_tuple])
                query = f"DELETE FROM [dbo].[Participants] WHERE ParticipantID IN ({placeholders})"
                cursor.execute(query, ids_tuple)

            connection.commit()
            return True

        except pyodbc.Error as e:
            print("Database error:", e)
            return False
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def get_all_participant_ids():
        connection_string = (
            f"DRIVER={Config.DRIVER};"
            f"SERVER={Config.SERVER};"
            f"DATABASE={Config.DATABASE};"
            'Trusted_Connection=yes;'
            'Encrypt=no;'
        )

        try:
            with pyodbc.connect(connection_string) as connection:
                cursor = connection.cursor()
                query = "SELECT ParticipantID FROM [dbo].[Participants]"
                cursor.execute(query)
                
                # Convert the results to a set for faster lookup
                participant_ids = {row[0] for row in cursor.fetchall()}
                return participant_ids

        except Exception as e:
            print(f"Error getting participant IDs: {str(e)}")
            return set()  # Return empty set if there's an error

    @staticmethod
    def get_paginated_participants(page=1, per_page=5, events=None, search_query=None, organiser_id=None):
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

            # Calculate offset
            offset = (page - 1) * per_page
            query_params = []

            # Base query for counting total records
            count_query = """
                SELECT COUNT(*) 
                FROM [dbo].[Participants] p
                JOIN [dbo].[TicketingUser] u ON p.UserID = u.UserID
                JOIN [dbo].[Event] e ON p.EventID = e.EventID
                WHERE 1=1
            """

            # Base query for fetching records
            main_query = """
                SELECT 
                    p.ParticipantID,
                    p.UserID,
                    p.RegistrationDate as ParticipantRegistrationDate,
                    u.UserName,
                    u.UserEmail,
                    u.UserContactInfo,
                    e.EventTitle
                FROM [dbo].[Participants] p
                JOIN [dbo].[TicketingUser] u ON p.UserID = u.UserID
                JOIN [dbo].[Event] e ON p.EventID = e.EventID
                WHERE 1=1
            """

            # Add organiser_id filter if provided
            if organiser_id:
                count_query += " AND e.OrganiserID = ?"
                main_query += " AND e.OrganiserID = ?"
                query_params.append(organiser_id)

            # Add event filters
            if events:
                event_placeholders = ','.join('?' * len(events))
                count_query += f" AND p.EventID IN ({event_placeholders})"
                main_query += f" AND p.EventID IN ({event_placeholders})"
                query_params.extend(events)

            # Add search filter
            if search_query:
                count_query += " AND u.UserName LIKE ?"
                main_query += " AND u.UserName LIKE ?"
                query_params.append(f'%{search_query}%')

            # Execute count query
            cursor.execute(count_query, query_params)
            total_records = cursor.fetchone()[0]
            total_pages = ceil(total_records / per_page)

            # Add pagination to main query
            main_query += " ORDER BY p.ParticipantID OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
            query_params.extend([offset, per_page])

            # Execute main query
            cursor.execute(main_query, query_params)
            participants = cursor.fetchall()

            participant_list = [
                {
                    "ParticipantID": row.ParticipantID,
                    "UserID": row.UserID,
                    "ParticipantName": row.UserName,
                    "ParticipantEmail": row.UserEmail,
                    "ParticipantContactInfo": row.UserContactInfo,
                    "RegistrationDate": row.ParticipantRegistrationDate,
                    "EventTitle": row.EventTitle
                }
                for row in participants
            ]

            return {
                'participants': participant_list,
                'total_pages': total_pages,
                'current_page': page,
                'total_records': total_records,
                'per_page': per_page
            }

        except pyodbc.Error as e:
            print("Database error: ", e)
            return None
        finally:
            cursor.close()
            connection.close()