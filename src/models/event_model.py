from config import Config
import pyodbc
from datetime import datetime
import os
from werkzeug.utils import secure_filename


UPLOAD_FOLDER = 'src/EventImage'  # Path where the image will be saved
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE_MB = 8


def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


class EventModel:
    
    

    @staticmethod
    def get_all_events(organiser_id):
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
            
            # Updated query to include EventImage
            cursor.execute(
                """
                SELECT EventID, OrganiserID, EventTitle, EventType, 
                    EventVenue, EventStartDate, EventEndDate, 
                    EventDescription, EventStatus, EventCapacity, EventImage
                FROM [dbo].[Event]
                WHERE OrganiserID = ?
                ORDER BY EventID
                """,
                (organiser_id,)
            )
            events = cursor.fetchall()

            event_list = []
            for row in events:
                event_dict = dict(zip([column[0] for column in cursor.description], row))
                
                # Update the image path construction
                if event_dict['EventImage']:
                    event_dict['EventImagePath'] = f"/static/EventImage/{event_dict['EventImage']}"
                else:
                    event_dict['EventImagePath'] = None
                
                event_list.append(event_dict)

            return event_list

        except pyodbc.Error as e:
            print("Database error: ", e)
            return None

        finally:
            cursor.close()
            connection.close()


    
    @staticmethod
    def get_next_event_id():
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

            cursor.execute("SELECT MAX(EventID) FROM [dbo].[Event]")
            max_event_id = cursor.fetchone()[0]

            if max_event_id:
                print(f"Current max EventID: {max_event_id}")  # Debug print
                event_number = int(max_event_id[3:]) + 1  # Assuming 'Eve' prefix
                new_event_id = f'Eve{event_number:05d}'
                print(f"New EventID generated: {new_event_id}")  # Debug print
                return new_event_id
            else:
                return 'Eve00001'  # Starting ID if no events exist

        except pyodbc.Error as e:
            print("Database error: ", e)
            return None

        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def add_event(event_title, event_venue, event_status, event_type, 
                start_date_str, end_date_str, capacity, description, 
                organiser_id, event_image_path):
        start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')

        # Extract just the filename from the path
        if event_image_path:
            event_image_path = os.path.basename(event_image_path)  # This will get just the filename

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

            event_id = EventModel.get_next_event_id()
            
            cursor.execute(
                """
                INSERT INTO [dbo].[Event] (
                    EventID, OrganiserID, EventTitle, EventType, 
                    EventVenue, EventStartDate, EventEndDate, 
                    EventDescription, EventStatus, EventCapacity, EventImage
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (event_id, organiser_id, event_title, event_type, event_venue, 
                start_date, end_date, description, event_status, capacity, event_image_path)
            )
            connection.commit()
        
        except pyodbc.Error as e:
            print("Database error: ", e)
            raise

        finally:
            cursor.close()
            connection.close()



    @staticmethod
    def check_event_dependencies(event_id):
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
            
            dependencies = []

            # Check Participants
            cursor.execute("SELECT COUNT(*) FROM [dbo].[Participants] WHERE [EventID] = ?", event_id)
            if cursor.fetchone()[0] > 0:
                dependencies.append("Participants: Registered participants are associated with this event.\n")

            # Check Sponsorship Assignments
            cursor.execute("SELECT COUNT(*) FROM [dbo].[SponsorshipAssignment] WHERE [EventID] = ?", event_id)
            if cursor.fetchone()[0] > 0:
                dependencies.append("Sponsorships: Sponsorship assignments exist for this event.\n")

            # Check Budget Records
            cursor.execute("SELECT COUNT(*) FROM [dbo].[EventBudgetsAndExpenses] WHERE [EventID] = ?", event_id)
            if cursor.fetchone()[0] > 0:
                dependencies.append("Budgets and Expenses: Budget or expense records are linked to this event.\n")

            # Check Exhibitor Assignments
            cursor.execute("SELECT COUNT(*) FROM [dbo].[ExhibitorAndBoothAssignment] WHERE [EventID] = ?", event_id)
            if cursor.fetchone()[0] > 0:
                dependencies.append("Exhibitors and Booths: Exhibitor or booth assignments are associated with this event.\n")

            # Check Event Staff
            cursor.execute("SELECT COUNT(*) FROM [dbo].[EventStaffAssignment] WHERE [EventID] = ?", event_id)
            if cursor.fetchone()[0] > 0:
                dependencies.append("Event Staff: Event staff are assigned to this event.\n")

            if dependencies:
                message = f"Unable to delete Event {event_id}:\n\n"
                message += "This event cannot be deleted because it has dependencies in the following areas:\n\n"
                message += "\n".join(dependencies)
                return message

            return None  # No dependencies found

        except pyodbc.Error as e:
            print("Database error: ", e)
            raise
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def delete_events(event_ids):
        connection_string = (
            f"DRIVER={Config.DRIVER};"
            f"SERVER={Config.SERVER};"
            f"DATABASE={Config.DATABASE};"
            'Trusted_Connection=yes;'
            'Encrypt=no;'
        )

        try:
            # Check dependencies for each event
            error_messages = []
            for event_id in event_ids:
                dependency_message = EventModel.check_event_dependencies(event_id)
                if dependency_message:
                    error_messages.append(f"Event {event_id}: {dependency_message}")

            if error_messages:
                raise ValueError("\n".join(error_messages))

            # If no dependencies, proceed with deletion
            connection = pyodbc.connect(connection_string)
            cursor = connection.cursor()
            ids_tuple = tuple(event_ids)
            query = f"DELETE FROM [dbo].[Event] WHERE EventID IN ({','.join(['?']*len(ids_tuple))})"
            cursor.execute(query, ids_tuple)
            connection.commit()

        except pyodbc.Error as e:
            print("Database error: ", e)
            raise
        finally:
            if 'connection' in locals():
                cursor.close()
                connection.close()
    
    @staticmethod
    def search_events(query, organiser_id):
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

            # Updated query to include EventImage
            cursor.execute(
                """
                SELECT EventID, OrganiserID, EventTitle, EventType, 
                    EventVenue, EventStartDate, EventEndDate, 
                    EventDescription, EventStatus, EventCapacity, EventImage
                FROM [dbo].[Event]
                WHERE EventTitle LIKE ? AND OrganiserID = ?
                ORDER BY EventID
                """,
                (f'%{query}%', organiser_id)
            )

            events = cursor.fetchall()

            event_list = []
            for row in events:
                event_dict = dict(zip([column[0] for column in cursor.description], row))

                # Update the image path construction
                if event_dict['EventImage']:
                    event_dict['EventImagePath'] = f"/static/EventImage/{event_dict['EventImage']}"
                else:
                    event_dict['EventImagePath'] = None

                event_list.append(event_dict)

            return event_list

        except pyodbc.Error as e:
            print("Database error: ", e)
            return []

        finally:
            cursor.close()
            connection.close()


    @staticmethod
    def get_event_by_id(event_id):
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
                SELECT EventID, EventTitle, EventType, 
                       EventVenue, EventStartDate, EventEndDate, 
                       EventDescription, EventStatus, EventCapacity 
                FROM [dbo].[Event]
                WHERE EventID = ?
                """,
                (event_id,)
            )
            event = cursor.fetchone()

            if event:
                event_dict = dict(zip([column[0] for column in cursor.description], event))
                # If there's an image, construct the full path for display
                if event_dict.get('EventImage'):
                    event_dict['EventImagePath'] = f"/static/EventImage/{event_dict['EventImage']}"
                return event_dict
            return None

        except pyodbc.Error as e:
            print("Database error: ", e)
            return None

        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def update_event(event_id, event_title, event_venue, event_status, event_type, start_date_str, end_date_str, capacity, description, image=None):
        # Convert string dates to datetime objects
        start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')

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

            # Check if image is provided
            if image:
                filename = secure_filename(image.filename)
                if allowed_file(filename):
                    # Check for file size
                    if image and image.content_length > (MAX_FILE_SIZE_MB * 1024 * 1024):
                        raise ValueError(f"File size exceeds {MAX_FILE_SIZE_MB}MB limit")

                    # Save image to the server directory
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    image.save(file_path)

                    # Store just the filename in the database
                    image_url = filename
                else:
                    raise ValueError("Invalid file type. Only PNG, JPG, JPEG, and GIF are allowed.")
            else:
                # No new image uploaded, retain the old image path from the database
                cursor.execute("SELECT EventImage FROM [dbo].[Event] WHERE EventID = ?", event_id)
                row = cursor.fetchone()
                image_url = row.EventImage if row else None

            # Now update the event data including the image URL
            cursor.execute(
                """
                UPDATE [dbo].[Event]
                SET EventTitle = ?, EventType = ?, EventVenue = ?, EventStartDate = ?, 
                    EventEndDate = ?, EventDescription = ?, EventStatus = ?, EventCapacity = ?, 
                    EventImage = ?
                WHERE EventID = ?
                """,
                (
                    event_title, 
                    event_type, 
                    event_venue, 
                    start_date, 
                    end_date, 
                    description, 
                    event_status, 
                    capacity, 
                    image_url,
                    event_id
                )
            )

            # Commit the changes to the database
            connection.commit()

        except pyodbc.Error as e:
            print("Database error: ", e)
            raise
        except Exception as e:
            print("Error: ", e)
            raise

        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def get_filtered_events(organiser_id, types=None, statuses=None):
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
                SELECT EventID, OrganiserID, EventTitle, EventType, 
                    EventVenue, EventStartDate, EventEndDate, 
                    EventDescription, EventStatus, EventCapacity, EventImage
                FROM [dbo].[Event]
                WHERE OrganiserID = ?
            """
            params = [organiser_id]

            if types:
                query += " AND EventType IN ({})".format(','.join('?' * len(types)))
                params.extend(types)
                
            if statuses:
                query += " AND EventStatus IN ({})".format(','.join('?' * len(statuses)))
                params.extend(statuses)

            query += " ORDER BY EventID"
            
            cursor.execute(query, params)
            events = cursor.fetchall()
            
            event_list = []
            for row in events:
                event_dict = dict(zip([column[0] for column in cursor.description], row))
                if event_dict['EventImage']:
                    event_dict['EventImagePath'] = f"/static/EventImage/{event_dict['EventImage']}"
                else:
                    event_dict['EventImagePath'] = None
                event_list.append(event_dict)

            return event_list

        except pyodbc.Error as e:
            print("Database error: ", e)
            return None
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def get_paginated_events(organiser_id, page=1, per_page=5, types=None, statuses=None, search_query=None):
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
            
            # Base query
            query = """
                SELECT EventID, OrganiserID, EventTitle, EventType, 
                    EventVenue, EventStartDate, EventEndDate, 
                    EventDescription, EventStatus, EventCapacity, EventImage
                FROM [dbo].[Event]
                WHERE OrganiserID = ?
            """
            params = [organiser_id]

            # Add filters
            if types:
                query += " AND EventType IN ({})".format(','.join('?' * len(types)))
                params.extend(types)
                
            if statuses:
                query += " AND EventStatus IN ({})".format(','.join('?' * len(statuses)))
                params.extend(statuses)

            if search_query:
                query += " AND EventTitle LIKE ?"
                params.append(f'%{search_query}%')

            # Count total records
            count_query = f"SELECT COUNT(*) FROM ({query}) as count_table"
            cursor.execute(count_query, params)
            total_records = cursor.fetchone()[0]
            total_pages = (total_records + per_page - 1) // per_page

            # Add pagination
            query += f" ORDER BY EventID OFFSET {(page-1)*per_page} ROWS FETCH NEXT {per_page} ROWS ONLY"
            
            cursor.execute(query, params)
            events = cursor.fetchall()
            
            event_list = []
            for row in events:
                event_dict = dict(zip([column[0] for column in cursor.description], row))
                if event_dict['EventImage']:
                    event_dict['EventImagePath'] = f"/static/EventImage/{event_dict['EventImage']}"
                else:
                    event_dict['EventImagePath'] = None
                event_list.append(event_dict)

            return {
                'events': event_list,
                'total_pages': total_pages,
                'current_page': page,
                'per_page': per_page,
                'total_records': total_records
            }

        except pyodbc.Error as e:
            print("Database error: ", e)
            return None
        finally:
            cursor.close()
            connection.close()