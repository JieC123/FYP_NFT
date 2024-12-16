from config import Config
from datetime import datetime
import pyodbc
from math import ceil
import pandas as pd

class EventStaffModel:
    
    

    @staticmethod
    def get_all_event_staff():
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
                SELECT EventStaffID, EventStaffName, EventStaffEmail, 
                    EventStaffContactInfo, IC, Role, 
                    JobStartPeriod, JobEndPeriod, Salary, 
                    OneTimeFees, Status 
                FROM [dbo].[EventStaff]
                ORDER BY EventStaffID
                """
            )
            event_staff = cursor.fetchall()

            # Convert Row objects to dictionaries and format the dates
            staff_list = []
            for row in event_staff:
                staff_dict = dict(zip([column[0] for column in cursor.description], row))

                # Format dates for display (but keep original values in the dictionary)
                if staff_dict['JobStartPeriod']:
                    staff_dict['JobStartPeriodFormatted'] = staff_dict['JobStartPeriod'].strftime('%Y-%m-%d')
                else:
                    staff_dict['JobStartPeriodFormatted'] = ""

                if staff_dict['JobEndPeriod']:
                    staff_dict['JobEndPeriodFormatted'] = staff_dict['JobEndPeriod'].strftime('%Y-%m-%d')
                else:
                    staff_dict['JobEndPeriodFormatted'] = ""
                
                staff_list.append(staff_dict)

            return staff_list  # Return list of dictionaries

        except pyodbc.Error as e:
            print("Database error: ", e)
            return None

        finally:
            cursor.close()
            connection.close()



    @staticmethod
    def get_event_staff_by_id(staff_id):
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
                SELECT EventStaffID, EventStaffName, EventStaffEmail, 
                       EventStaffContactInfo, IC, Role, 
                       JobStartPeriod, JobEndPeriod, Salary, 
                       OneTimeFees, Status 
                FROM [dbo].[EventStaff]
                WHERE EventStaffID = ?
                """,
                (staff_id,)
            )
            staff = cursor.fetchone()

            if staff:
                return dict(zip([column[0] for column in cursor.description], staff))
            return None

        except pyodbc.Error as e:
            print("Database error: ", e)
            return None

        finally:
            cursor.close()
            connection.close()


    @staticmethod
    def search_event_staff(query):
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
                SELECT EventStaffID, EventStaffName, EventStaffEmail, 
                    EventStaffContactInfo, IC, Salary, Role, 
                    JobStartPeriod, JobEndPeriod, OneTimeFees, Status  -- Added OneTimeFees
                FROM [dbo].[EventStaff]
                WHERE EventStaffName LIKE ?  -- Only searching by staff name
                ORDER BY EventStaffID
                """,
                (f'%{query}%',)
            )

            staff = cursor.fetchall()

            # Convert Row objects to dictionaries
            staff_list = [dict(zip([column[0] for column in cursor.description], row)) for row in staff]
            return staff_list  # Return list of dictionaries

        except pyodbc.Error as e:
            print("Database error: ", e)
            return []

        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def get_next_staff_id():
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

            cursor.execute("SELECT MAX(EventStaffID) FROM [dbo].[EventStaff]")
            max_staff_id = cursor.fetchone()[0]

            if max_staff_id:
                print(f"Current max EventStaffID: {max_staff_id}")  # Debug print
                # Extract number part after 'Stf'
                staff_number = int(max_staff_id[3:]) + 1  # Assuming 'Stf' prefix
                new_staff_id = f'Stf{staff_number:05d}'  # Ensure it's zero-padded
                print(f"New EventStaffID generated: {new_staff_id}")  # Debug print
                return new_staff_id
            else:
                return 'Stf00001'  # Starting ID if no staff exists

        except pyodbc.Error as e:
            print("Database error: ", e)
            return None

        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def add_staff(full_name, email, job_start_date_str, salary, status,
                ic_no, contact_no, role, job_end_date_str, one_time_fees):
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

            # Parse the date strings into datetime objects
            start_date = datetime.strptime(job_start_date_str, '%Y-%m-%dT%H:%M')
            end_date = datetime.strptime(job_end_date_str, '%Y-%m-%dT%H:%M')

            # Generate new EventStaffID
            staff_id = EventStaffModel.get_next_staff_id()

            cursor.execute(
                """
                INSERT INTO [dbo].[EventStaff] (
                    EventStaffID, EventStaffName, EventStaffEmail, 
                    EventStaffContactInfo, IC, Role, 
                    JobStartPeriod, JobEndPeriod, 
                    Salary, OneTimeFees, Status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    staff_id,
                    full_name,
                    email,
                    contact_no,  # Adjusting based on the field name
                    ic_no,
                    role,
                    start_date,  # Use parsed datetime object
                    end_date,    # Use parsed datetime object
                    salary,
                    one_time_fees,
                    status
                )
            )

            connection.commit()
            print("Staff added to the database successfully.")  # Debug print

        except pyodbc.Error as e:
            print("Database error: ", e)
            raise

        finally:
            cursor.close()
            connection.close()


    @staticmethod
    def check_duplicate_staff_email(email):
        """
        Check if the given email already exists in the EventStaff table.
        Returns True if a duplicate is found, otherwise False.
        """
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

            # Query to check for existing email in the EventStaff table
            cursor.execute(
                "SELECT COUNT(*) FROM [dbo].[EventStaff] WHERE EventStaffEmail = ?", 
                email
            )
            result = cursor.fetchone()
            return result[0] > 0  # Return True if email exists, otherwise False

        except pyodbc.Error as e:
            print("Database error during email check:", e)
            raise

        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def get_assigned_staff(staff_ids):
        connection_string = (
            f"DRIVER={Config.DRIVER};"
            f"SERVER={Config.SERVER};"
            f"DATABASE={Config.DATABASE};"
            'Trusted_Connection=yes;'
            'Encrypt=no;'
        )

        if not staff_ids:
            return []

        try:
            connection = pyodbc.connect(connection_string)
            cursor = connection.cursor()

            # Convert list of staff IDs to a tuple
            ids_tuple = tuple(staff_ids)
            if len(ids_tuple) == 1:
                ids_tuple = (ids_tuple[0],)

            query = f"""
                SELECT DISTINCT s.EventStaffID, e.EventStaffName
                FROM [dbo].[EventStaffAssignment] s
                JOIN [dbo].[EventStaff] e ON s.EventStaffID = e.EventStaffID
                WHERE s.EventStaffID IN ({','.join(['?'] * len(ids_tuple))})
            """
            cursor.execute(query, ids_tuple)
            assigned_staff = [row.EventStaffName for row in cursor.fetchall()]

            return assigned_staff

        except pyodbc.Error as e:
            print("Database error:", e)
            raise

        finally:
            cursor.close()
            connection.close()


    @staticmethod
    def delete_staff(staff_ids):
        connection_string = (
            f"DRIVER={Config.DRIVER};"
            f"SERVER={Config.SERVER};"
            f"DATABASE={Config.DATABASE};"
            'Trusted_Connection=yes;'
            'Encrypt=no;'
        )

        if not staff_ids:
            return {'success': False, 'message': 'No staff members provided for deletion'}

        try:
            connection = pyodbc.connect(connection_string)
            cursor = connection.cursor()

            # Convert list of staff IDs to a tuple
            ids_tuple = tuple(staff_ids)
            if len(ids_tuple) == 1:
                ids_tuple = (ids_tuple[0],)

            # Check if any of the staff members are assigned to events
            check_query = f"""
                SELECT DISTINCT s.EventStaffID, e.EventStaffName
                FROM [dbo].[EventStaffAssignment] s
                JOIN [dbo].[EventStaff] e ON s.EventStaffID = e.EventStaffID
                WHERE s.EventStaffID IN ({','.join(['?'] * len(ids_tuple))})
            """
            cursor.execute(check_query, ids_tuple)
            assigned_staff = [row.EventStaffName for row in cursor.fetchall()]

            if assigned_staff:
                assigned_names = ', '.join(assigned_staff)
                return {
                    'success': False,
                    'message': f"Cannot delete staff members assigned to events: {assigned_names}"
                }

            # Delete unassigned staff members
            delete_query = f"DELETE FROM [dbo].[EventStaff] WHERE EventStaffID IN ({','.join(['?'] * len(ids_tuple))})"
            cursor.execute(delete_query, ids_tuple)
            connection.commit()

            return {'success': True, 'message': 'Staff members deleted successfully'}

        except pyodbc.Error as e:
            print("Database error:", e)
            return {'success': False, 'message': str(e)}

        finally:
            cursor.close()
            connection.close()




    @staticmethod
    def get_staff_by_id(staff_id):
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
                SELECT EventStaffID, EventStaffName, EventStaffEmail, JobStartPeriod, Salary, Role, IC, EventStaffContactInfo, JobEndPeriod, OneTimeFees, Status
                FROM [dbo].[EventStaff]
                WHERE EventStaffID = ?
                """,
                (staff_id,)
            )
            staff = cursor.fetchone()

            if staff:
                staff_data = dict(zip([column[0] for column in cursor.description], staff))
                # Format datetime objects for HTML date inputs
                if staff_data['JobStartPeriod']:
                    staff_data['JobStartPeriod'] = staff_data['JobStartPeriod'].strftime('%Y-%m-%dT%H:%M')
                else:
                    staff_data['JobStartPeriod'] = ''

                if staff_data['JobEndPeriod']:
                    staff_data['JobEndPeriod'] = staff_data['JobEndPeriod'].strftime('%Y-%m-%dT%H:%M')
                else:
                    staff_data['JobEndPeriod'] = ''
                    
                return staff_data
            return None

        except pyodbc.Error as e:
            print("Database error: ", e)
            return None

        finally:
            cursor.close()
            connection.close()



    

    @staticmethod
    def update_staff(staff_id, full_name, email, job_start_date, salary_amount,
                     role, ic_no, contact_no, job_end_date, one_time_fees, status):
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

            # Convert the job start and end date strings to datetime objects
            job_start_date = datetime.strptime(job_start_date, '%Y-%m-%dT%H:%M') if job_start_date else None
            job_end_date = datetime.strptime(job_end_date, '%Y-%m-%dT%H:%M') if job_end_date else None

            cursor.execute(
                """
                UPDATE [dbo].[EventStaff]
                SET EventStaffName = ?, EventStaffEmail = ?, JobStartPeriod = ?, Salary = ?, Role = ?, 
                    IC = ?, EventStaffContactInfo = ?, JobEndPeriod = ?, OneTimeFees = ?, Status = ?
                WHERE EventStaffID = ?
                """,
                (
                    full_name,
                    email,
                    job_start_date,
                    salary_amount,
                    role,
                    ic_no,
                    contact_no,
                    job_end_date,
                    one_time_fees,
                    status,
                    staff_id
                )
            )

            connection.commit()

        except pyodbc.Error as e:
            print("Database error: ", e)
            raise

        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def check_duplicate_staff_email_for_update(email, staff_id):
        """
        Check if the given email already exists in the EventStaff table, excluding
        the current staff record being updated.
        Returns True if a duplicate is found, otherwise False.
        """
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
            
            # Query to check for existing email excluding the current staff_id
            cursor.execute(
                """
                SELECT COUNT(*) FROM [dbo].[EventStaff] 
                WHERE EventStaffEmail = ? AND EventStaffID != ?
                """,
                email, staff_id
            )
            result = cursor.fetchone()
            return result[0] > 0  # Return True if email exists, otherwise False

        except pyodbc.Error as e:
            print("Database error during email check:", e)
            raise

        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def insert_staff_data(records):
        connection_string = (
            f"DRIVER={Config.DRIVER};"
            f"SERVER={Config.SERVER};"
            f"DATABASE={Config.DATABASE};"
            "Trusted_Connection=yes;"
            "Encrypt=no;"
        )

        try:
            # Connect to the database
            with pyodbc.connect(connection_string) as connection:
                cursor = connection.cursor()

                query = """
                    INSERT INTO [dbo].[EventStaff] (
                        EventStaffID, EventStaffName, EventStaffEmail,
                        EventStaffContactInfo, IC, Salary, OneTimeFees,
                        Role, JobStartPeriod, JobEndPeriod, Status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """

                # Loop through the list of staff records and insert them
                for record in records:
                    try:
                        cursor.execute(
                            query,
                            (
                                record.get('EventStaffID'),
                                record.get('EventStaffName'),
                                record.get('EventStaffEmail'),
                                record.get('EventStaffContactInfo'),
                                record.get('IC'),
                                record.get('Salary'),
                                record.get('OneTimeFees'),
                                record.get('Role'),
                                record.get('JobStartPeriod'),
                                record.get('JobEndPeriod'),
                                record.get('Status')
                            )
                        )

                    except Exception as e:
                        print(f"Failed to insert record: {record}, Error: {e}")
                        continue  # Skip to the next record if there's an error

                connection.commit()
                print("All staff records inserted successfully.")
                return True

        except pyodbc.Error as e:
            print(f"Database connection error: {e}")
            return False

    @staticmethod
    def get_filtered_staff(roles=None, statuses=None):
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
                SELECT EventStaffID, EventStaffName, EventStaffEmail, 
                    EventStaffContactInfo, IC, Role, 
                    JobStartPeriod, JobEndPeriod, Salary, 
                    OneTimeFees, Status 
                FROM [dbo].[EventStaff]
                WHERE 1=1
            """
            
            params = []
            
            if roles:
                query += f" AND Role IN ({','.join(['?' for _ in roles])})"
                params.extend(roles)
                
            if statuses:
                query += f" AND Status IN ({','.join(['?' for _ in statuses])})"
                params.extend(statuses)
                
            query += " ORDER BY EventStaffID"
            
            cursor.execute(query, params)
            staff = cursor.fetchall()
            
            # Convert to list of dictionaries
            staff_list = []
            for row in staff:
                staff_dict = dict(zip([column[0] for column in cursor.description], row))
                
                # Format dates
                if staff_dict['JobStartPeriod']:
                    staff_dict['JobStartPeriodFormatted'] = staff_dict['JobStartPeriod'].strftime('%Y-%m-%d')
                else:
                    staff_dict['JobStartPeriodFormatted'] = ""
                    
                if staff_dict['JobEndPeriod']:
                    staff_dict['JobEndPeriodFormatted'] = staff_dict['JobEndPeriod'].strftime('%Y-%m-%d')
                else:
                    staff_dict['JobEndPeriodFormatted'] = ""
                    
                staff_list.append(staff_dict)
                
            return staff_list

        except pyodbc.Error as e:
            print("Database error: ", e)
            return None
            
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def get_paginated_staff(page=1, per_page=5, roles=None, statuses=None, search_query=None):
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
            
            # Base query for total count
            count_query = "SELECT COUNT(*) FROM [dbo].[EventStaff] WHERE 1=1"
            query_params = []

            # Add filter conditions to count query
            if roles:
                count_query += " AND Role IN ({})".format(','.join('?' * len(roles)))
                query_params.extend(roles)
            if statuses:
                count_query += " AND Status IN ({})".format(','.join('?' * len(statuses)))
                query_params.extend(statuses)
            if search_query:
                count_query += " AND EventStaffName LIKE ?"
                query_params.extend([f'%{search_query}%'])

            # Get total count
            cursor.execute(count_query, query_params)
            total_records = cursor.fetchone()[0]
            total_pages = ceil(total_records / per_page)
            offset = (page - 1) * per_page

            # Main query for fetching staff
            main_query = """
                SELECT EventStaffID, EventStaffName, EventStaffEmail, 
                       EventStaffContactInfo, IC, Role, 
                       JobStartPeriod, JobEndPeriod, Salary, 
                       OneTimeFees, Status
                FROM [dbo].[EventStaff]
                WHERE 1=1
            """

            # Reset query_params for main query
            query_params = []

            # Add filters to main query
            if roles:
                main_query += " AND Role IN ({})".format(','.join('?' * len(roles)))
                query_params.extend(roles)
            if statuses:
                main_query += " AND Status IN ({})".format(','.join('?' * len(statuses)))
                query_params.extend(statuses)
            if search_query:
                main_query += " AND EventStaffName LIKE ?"
                search_pattern = f'%{search_query}%'
                query_params.extend([search_pattern])

            main_query += " ORDER BY EventStaffID OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
            query_params.extend([offset, per_page])

            cursor.execute(main_query, query_params)
            staff = cursor.fetchall()
            
            staff_list = []
            for row in staff:
                staff_dict = dict(zip([column[0] for column in cursor.description], row))
                
                # Format dates
                if staff_dict['JobStartPeriod']:
                    staff_dict['JobStartPeriodFormatted'] = staff_dict['JobStartPeriod'].strftime('%Y-%m-%d')
                else:
                    staff_dict['JobStartPeriodFormatted'] = ""
                    
                if staff_dict['JobEndPeriod']:
                    staff_dict['JobEndPeriodFormatted'] = staff_dict['JobEndPeriod'].strftime('%Y-%m-%d')
                else:
                    staff_dict['JobEndPeriodFormatted'] = ""
                    
                staff_list.append(staff_dict)

            return {
                'staff': staff_list,
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

    @staticmethod
    def insert_single_staff(record):
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

            # Insert query with parameterized values
            query = """
                INSERT INTO [dbo].[EventStaff] (
                    EventStaffID, 
                    EventStaffName, 
                    EventStaffEmail, 
                    EventStaffContactInfo, 
                    IC, 
                    Role, 
                    JobStartPeriod, 
                    JobEndPeriod, 
                    Salary, 
                    OneTimeFees, 
                    Status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            # Convert dates to datetime objects if they're strings
            job_start = pd.to_datetime(record['JobStartPeriod']) if record['JobStartPeriod'] else None
            job_end = pd.to_datetime(record['JobEndPeriod']) if record['JobEndPeriod'] else None

            # Execute the query with parameters
            cursor.execute(query, (
                record['EventStaffID'],
                record['EventStaffName'],
                record['EventStaffEmail'],
                record['EventStaffContactInfo'],
                record['IC'],
                record['Role'],
                job_start,
                job_end,
                float(record['Salary']),
                float(record['OneTimeFees']),
                record['Status']
            ))

            connection.commit()
            return True

        except pyodbc.Error as e:
            print(f"Database error in insert_single_staff: {e}")
            raise Exception(f"Database error: {str(e)}")

        finally:
            cursor.close()
            connection.close()

