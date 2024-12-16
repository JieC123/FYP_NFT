from config import Config
import pyodbc

class SponsorshipModel:
    
    @staticmethod
    def get_all_sponsorships():
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
                SELECT SponsorshipID, SponsorshipName, SponsorshipEmail, 
                       SponsorshipContactInfo, Company, 
                       SponsorDetail, AmountContributed, 
                       PaymentSchedule, Status 
                FROM [dbo].[Sponsorship]
                ORDER BY SponsorshipID
                """
            )
            sponsorships = cursor.fetchall()

            # Convert Row objects to dictionaries
            sponsorship_list = [dict(zip([column[0] for column in cursor.description], row)) for row in sponsorships]
            return sponsorship_list  # Return list of dictionaries

        except pyodbc.Error as e:
            print("Database error: ", e)
            return None

        finally:
            cursor.close()
            connection.close()


    @staticmethod
    def search_sponsorships(query):
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
                SELECT SponsorshipID, SponsorshipName, SponsorshipEmail, 
                       SponsorshipContactInfo, Company, 
                       SponsorDetail, AmountContributed, 
                       PaymentSchedule, Status 
                FROM [dbo].[Sponsorship]
                WHERE SponsorshipName LIKE ?  -- Searching by sponsorship name
                ORDER BY SponsorshipID
                """,
                (f'%{query}%',)
            )

            sponsorships = cursor.fetchall()

            # Convert Row objects to dictionaries
            sponsorship_list = [dict(zip([column[0] for column in cursor.description], row)) for row in sponsorships]
            return sponsorship_list  # Return list of dictionaries

        except pyodbc.Error as e:
            print("Database error: ", e)
            return []

        finally:
            cursor.close()
            connection.close()


    @staticmethod
    def get_next_sponsorship_id():
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

            cursor.execute("SELECT MAX(CAST(SUBSTRING(SponsorshipID, 3, 5) AS INT)) FROM [dbo].[Sponsorship]")
            max_id = cursor.fetchone()[0] or 0
            next_id = max_id + 1
            return f'Sp{next_id:05}'

        except pyodbc.Error as e:
            print("Database error: ", e)
            raise

        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def add_sponsorship(full_name, email, company, contact_no, sponsor_detail, amount_contributed, payment_schedule, status):
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

            # Generate new SponsorshipID
            sponsorship_id = SponsorshipModel.get_next_sponsorship_id()

            cursor.execute(
                """
                INSERT INTO [dbo].[Sponsorship] (
                    SponsorshipID, SponsorshipName, SponsorshipEmail, 
                    SponsorshipContactInfo, Company, 
                    SponsorDetail, AmountContributed, 
                    PaymentSchedule, Status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sponsorship_id,
                    full_name,
                    email,
                    contact_no,
                    company,
                    sponsor_detail,
                    amount_contributed,
                    payment_schedule,
                    status
                )
            )

            connection.commit()
            print("Sponsorship added to the database successfully.")

        except pyodbc.Error as e:
            print("Database error: ", e)
            raise

        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def check_duplicate_email(email):
        """
        Check if the given email already exists in the Sponsorship table.
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
            
            # Query to check for existing email
            cursor.execute(
                "SELECT COUNT(*) FROM [dbo].[Sponsorship] WHERE SponsorshipEmail = ?", 
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
    def check_duplicate_email_for_update(email, sponsorship_id):
        """
        Check if the given email already exists in the Sponsorship table, excluding
        the current sponsorship record.
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
            
            # Query to check for existing email excluding the current sponsorship_id
            cursor.execute(
                "SELECT COUNT(*) FROM [dbo].[Sponsorship] WHERE SponsorshipEmail = ? AND SponsorshipID != ?", 
                email, sponsorship_id
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
    def delete_sponsorship(sponsorship_ids):
        connection_string = (
            f"DRIVER={Config.DRIVER};"
            f"SERVER={Config.SERVER};"
            f"DATABASE={Config.DATABASE};"
            'Trusted_Connection=yes;'
            'Encrypt=no;'
        )

        if not sponsorship_ids:
            return {'success': False, 'message': 'No sponsorships provided for deletion'}

        try:
            connection = pyodbc.connect(connection_string)
            cursor = connection.cursor()

            # Convert the list of sponsorship IDs to a tuple for the SQL query
            ids_tuple = tuple(sponsorship_ids)
            if len(ids_tuple) == 1:
                ids_tuple = (ids_tuple[0],)  # Ensure it remains a tuple

            # Step 1: Check if any of the sponsorships are assigned to events
            check_query = f"""
                SELECT DISTINCT s.SponsorshipID, s.SponsorshipName
                FROM [dbo].[SponsorshipAssignment] a
                JOIN [dbo].[Sponsorship] s ON a.SponsorshipID = s.SponsorshipID
                WHERE a.SponsorshipID IN ({','.join(['?'] * len(ids_tuple))})
            """
            cursor.execute(check_query, ids_tuple)
            assigned_sponsorships = [row.SponsorshipName for row in cursor.fetchall()]

            # If any sponsorships are assigned, return an error
            if assigned_sponsorships:
                assigned_names = ', '.join(assigned_sponsorships)
                return {
                    'success': False,
                    'message': f"Cannot delete sponsorship assigned to event: {assigned_names}"
                }

            # Step 2: Delete unassigned sponsorships from the `Sponsorship` table
            delete_query = f"DELETE FROM [dbo].[Sponsorship] WHERE SponsorshipID IN ({','.join(['?'] * len(ids_tuple))})"
            cursor.execute(delete_query, ids_tuple)
            connection.commit()

            return {'success': True, 'message': 'Sponsorship(s) deleted successfully'}

        except pyodbc.Error as e:
            print("Database error:", e)
            return {'success': False, 'message': str(e)}

        finally:
            cursor.close()
            connection.close()


    @staticmethod
    def get_sponsorship_by_id(sponsorship_id):
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
            
            cursor.execute(
                """
                SELECT SponsorshipID, SponsorshipName, SponsorshipEmail, 
                    SponsorshipContactInfo, Company, SponsorDetail, 
                    AmountContributed, PaymentSchedule, Status 
                FROM [dbo].[Sponsorship]
                WHERE SponsorshipID = ?
                """,
                (sponsorship_id,)
            )
            
            sponsorship = cursor.fetchone()
            if sponsorship:
                return dict(zip([column[0] for column in cursor.description], sponsorship))
            return None

        except pyodbc.Error as e:
            print("Database error: ", e)
            return None

        finally:
            cursor.close()
            connection.close()


    @staticmethod
    def update_sponsorship(sponsorship_id, name, email, contact_info, company, sponsor_detail, 
                           amount_contributed, payment_schedule, status):
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
                UPDATE [dbo].[Sponsorship]
                SET SponsorshipName = ?, SponsorshipEmail = ?, SponsorshipContactInfo = ?, 
                    Company = ?, SponsorDetail = ?, AmountContributed = ?, 
                    PaymentSchedule = ?, Status = ?
                WHERE SponsorshipID = ?
                """,
                (
                    name,
                    email,
                    contact_info,
                    company,
                    sponsor_detail,
                    amount_contributed,
                    payment_schedule,
                    status,
                    sponsorship_id
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
    def insert_sponsorship_data(records):
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
                    INSERT INTO [dbo].[Sponsorship] (
                        SponsorshipID, SponsorshipName, SponsorshipEmail,
                        SponsorshipContactInfo, Company, SponsorDetail,
                        AmountContributed, PaymentSchedule, Status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                # Loop through records and insert them
                for record in records:
                    try:
                        cursor.execute(
                            query,
                            (
                                record.get('SponsorshipID'),
                                record.get('SponsorshipName'),
                                record.get('SponsorshipEmail'),
                                record.get('SponsorshipContactInfo'),
                                record.get('Company'),
                                record.get('SponsorDetail'),
                                record.get('AmountContributed'),
                                record.get('PaymentSchedule'),
                                record.get('Status')
                            )
                        )
                    except Exception as e:
                        print(f"Failed to insert record: {record}, Error: {e}")
                        continue  # Skip to the next record if there's an error

                connection.commit()
                print("All records inserted successfully.")
                return True

        except pyodbc.Error as e:
            print(f"Database connection error: {e}")
            return False



    # @staticmethod
    # def get_events_for_sponsorship():
    #     connection_string = (
    #         f"DRIVER={Config.DRIVER};"
    #         f"SERVER={Config.SERVER};"
    #         f"DATABASE={Config.DATABASE};"
    #         'Trusted_Connection=yes;'
    #         'Encrypt=no;'
    #     )

    #     try:
    #         connection = pyodbc.connect(connection_string)
    #         cursor = connection.cursor()

    #         # Fetch all events (removing the filter for OrganiserID)
    #         cursor.execute(
    #             """
    #             SELECT EventID, EventTitle
    #             FROM [dbo].[Event]
    #             ORDER BY EventTitle
    #             """
    #         )
    #         events = cursor.fetchall()

    #         # Convert the fetched data into a list of dictionaries
    #         event_list = [{'EventID': row.EventID, 'EventTitle': row.EventTitle} for row in events]

    #         return event_list

    #     except pyodbc.Error as e:
    #         print(f"Database error: {e}")
    #         return []  # Return an empty list on error

    #     finally:
    #         cursor.close()
    #         connection.close()

    @staticmethod
    def get_filtered_sponsorships(packages=None, schedules=None, statuses=None):
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
                SELECT SponsorshipID, SponsorshipName, SponsorshipEmail, 
                       SponsorshipContactInfo, Company, 
                       SponsorDetail, AmountContributed, 
                       PaymentSchedule, Status 
                FROM [dbo].[Sponsorship]
                WHERE 1=1
            """
            params = []

            if packages:
                query += " AND SponsorDetail IN ({})".format(','.join('?' * len(packages)))
                params.extend(packages)
            
            if schedules:
                query += " AND PaymentSchedule IN ({})".format(','.join('?' * len(schedules)))
                params.extend(schedules)
            
            if statuses:
                query += " AND Status IN ({})".format(','.join('?' * len(statuses)))
                params.extend(statuses)

            query += " ORDER BY SponsorshipID"
            
            cursor.execute(query, params)
            sponsorships = cursor.fetchall()
            
            sponsorship_list = [dict(zip([column[0] for column in cursor.description], row)) for row in sponsorships]

            return sponsorship_list

        except pyodbc.Error as e:
            print("Database error: ", e)
            return None
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def get_paginated_sponsorships(page=1, per_page=5, packages=None, schedules=None, statuses=None, search_query=None):
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
            count_query = "SELECT COUNT(*) FROM [dbo].[Sponsorship] WHERE 1=1"
            query_params = []

            # Add filters to count query
            if packages:
                count_query += " AND SponsorDetail IN ({})".format(','.join('?' * len(packages)))
                query_params.extend(packages)
            
            if schedules:
                count_query += " AND PaymentSchedule IN ({})".format(','.join('?' * len(schedules)))
                query_params.extend(schedules)
            
            if statuses:
                count_query += " AND Status IN ({})".format(','.join('?' * len(statuses)))
                query_params.extend(statuses)

            if search_query:
                count_query += """ AND (
                    SponsorshipName LIKE ? OR 
                    SponsorshipEmail LIKE ? OR 
                    Company LIKE ? OR 
                    SponsorDetail LIKE ?
                )"""
                search_pattern = f'%{search_query}%'
                query_params.extend([search_pattern] * 4)

            # Get total count
            cursor.execute(count_query, query_params)
            total_records = cursor.fetchone()[0]
            total_pages = (total_records + per_page - 1) // per_page

            # Main query with pagination
            offset = (page - 1) * per_page
            main_query = """
                SELECT SponsorshipID, SponsorshipName, SponsorshipEmail, 
                       SponsorshipContactInfo, Company, SponsorDetail, 
                       AmountContributed, PaymentSchedule, Status
                FROM [dbo].[Sponsorship]
                WHERE 1=1
            """

            # Add filters to main query
            if packages:
                main_query += " AND SponsorDetail IN ({})".format(','.join('?' * len(packages)))
            if schedules:
                main_query += " AND PaymentSchedule IN ({})".format(','.join('?' * len(schedules)))
            if statuses:
                main_query += " AND Status IN ({})".format(','.join('?' * len(statuses)))
            if search_query:
                main_query += """ AND (
                    SponsorshipName LIKE ? OR 
                    SponsorshipEmail LIKE ? OR 
                    Company LIKE ? OR 
                    SponsorDetail LIKE ?
                )"""

            main_query += " ORDER BY SponsorshipID OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
            query_params.extend([offset, per_page])

            cursor.execute(main_query, query_params)
            sponsorships = cursor.fetchall()
            
            sponsorship_list = [dict(zip([column[0] for column in cursor.description], row)) for row in sponsorships]

            return {
                'sponsorships': sponsorship_list,
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
    def insert_single_sponsorship(record):
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
                INSERT INTO [dbo].[Sponsorship] (
                    SponsorshipID, SponsorshipName, SponsorshipEmail,
                    SponsorshipContactInfo, Company, SponsorDetail,
                    AmountContributed, PaymentSchedule, Status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            cursor.execute(query, (
                record['SponsorshipID'],
                record['SponsorshipName'],
                record['SponsorshipEmail'],
                record['SponsorshipContactInfo'],
                record['Company'],
                record['SponsorDetail'],
                float(record['AmountContributed']),
                record['PaymentSchedule'],
                record['Status']
            ))

            connection.commit()
            return True

        except pyodbc.Error as e:
            print(f"Database error in insert_single_sponsorship: {e}")
            raise Exception(f"Database error: {str(e)}")

        finally:
            cursor.close()
            connection.close()
