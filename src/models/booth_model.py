from config import Config
import pyodbc
from math import ceil

class BoothModel:

    @staticmethod
    def get_all_booths():
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
                SELECT ExhibitorID, ExhibitorName, ExhibitorEmail, ExhibitorContactInfo, 
                       Company, BoothCategory, BoothSize, BoothRentalFees, Status
                FROM [dbo].[ExhibitorAndBooth]
                ORDER BY ExhibitorID
                """
            )
            booths = cursor.fetchall()

            # Convert Row objects to dictionaries
            booth_list = [dict(zip([column[0] for column in cursor.description], row)) for row in booths]
            return booth_list  # Return list of dictionaries

        except pyodbc.Error as e:
            print("Database error: ", e)
            return None

        finally:
            cursor.close()
            connection.close()


    @staticmethod
    def search_exhibitors(query):
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
                SELECT ExhibitorID, ExhibitorName, ExhibitorEmail, 
                       ExhibitorContactInfo, Company, Status, 
                       BoothCategory, BoothSize, BoothRentalFees
                FROM [dbo].[ExhibitorAndBooth]
                WHERE ExhibitorName LIKE ?  -- Search by exhibitor name
                ORDER BY ExhibitorID
                """,
                (f'%{query}%',)
            )

            exhibitors = cursor.fetchall()

            # Convert Row objects to dictionaries
            exhibitor_list = [dict(zip([column[0] for column in cursor.description], row)) for row in exhibitors]
            return exhibitor_list  # Return list of dictionaries

        except pyodbc.Error as e:
            print("Database error: ", e)
            return []

        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def get_next_exhibitor_id():
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

            cursor.execute("SELECT MAX(CAST(SUBSTRING(ExhibitorID, 4, 5) AS INT)) FROM [dbo].[ExhibitorAndBooth]")
            max_id = cursor.fetchone()[0] or 0
            next_id = max_id + 1
            return f'Exh{next_id:05}'

        except pyodbc.Error as e:
            print("Database error: ", e)
            raise

        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def add_exhibitor(exhibitor_name, exhibitor_email, company, contact_no, booth_category, booth_size, booth_rental_fees, status):
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

            # Generate new ExhibitorID
            exhibitor_id = BoothModel.get_next_exhibitor_id()

            cursor.execute(
                """
                INSERT INTO [dbo].[ExhibitorAndBooth] (
                    ExhibitorID, ExhibitorName, ExhibitorEmail, 
                    ExhibitorContactInfo, Company, 
                    BoothCategory, BoothSize, BoothRentalFees, 
                    Status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    exhibitor_id,
                    exhibitor_name,
                    exhibitor_email,
                    contact_no,
                    company,
                    booth_category,
                    booth_size,
                    booth_rental_fees,
                    status
                )
            )

            connection.commit()
            print("Exhibitor added to the database successfully.")

        except pyodbc.Error as e:
            print("Database error: ", e)
            raise

        finally:
            cursor.close()
            connection.close()


    @staticmethod
    def is_email_exists(exhibitor_email):
        """
        Check if the given email already exists in the ExhibitorAndBooth table.
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
            
            # Print the query for debugging purposes
            print(f"Checking email existence with query: SELECT COUNT(*) FROM [dbo].[ExhibitorAndBooth] WHERE ExhibitorEmail = '{exhibitor_email}'")
            
            # Query to check for existing email in the ExhibitorAndBooth table
            cursor.execute(
                "SELECT COUNT(*) FROM [dbo].[ExhibitorAndBooth] WHERE ExhibitorEmail = ?", 
                exhibitor_email
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
    def delete_exhibitor(exhibitor_ids):
        connection_string = (
            f"DRIVER={Config.DRIVER};"
            f"SERVER={Config.SERVER};"
            f"DATABASE={Config.DATABASE};"
            'Trusted_Connection=yes;'
            'Encrypt=no;'
        )

        if not exhibitor_ids:
            return {'success': False, 'message': 'No exhibitors provided for deletion'}

        try:
            connection = pyodbc.connect(connection_string)
            cursor = connection.cursor()

            # Convert list of exhibitor IDs to a tuple for use in SQL queries
            ids_tuple = tuple(exhibitor_ids)
            if len(ids_tuple) == 1:
                ids_tuple = (ids_tuple[0],)  # Ensure it remains a tuple

            # Step 1: Check if any of the exhibitors are assigned to events
            check_query = f"""
                SELECT DISTINCT e.ExhibitorID, e.ExhibitorName
                FROM [dbo].[ExhibitorAndBoothAssignment] a
                JOIN [dbo].[ExhibitorAndBooth] e ON a.ExhibitorID = e.ExhibitorID
                WHERE a.ExhibitorID IN ({','.join(['?'] * len(ids_tuple))})
            """
            cursor.execute(check_query, ids_tuple)
            assigned_exhibitors = [row.ExhibitorName for row in cursor.fetchall()]

            if assigned_exhibitors:
                assigned_names = ', '.join(assigned_exhibitors)
                return {
                    'success': False,
                    'message': f"Cannot delete exhibitor and booth assigned to events: {assigned_names}"
                }

            # Step 2: Delete unassigned exhibitors from the `ExhibitorAndBooth` table
            delete_query = f"DELETE FROM [dbo].[ExhibitorAndBooth] WHERE ExhibitorID IN ({','.join(['?'] * len(ids_tuple))})"
            cursor.execute(delete_query, ids_tuple)
            connection.commit()

            return {'success': True, 'message': 'Exhibitors deleted successfully'}

        except pyodbc.Error as e:
            print("Database error: ", e)
            return {'success': False, 'message': str(e)}

        finally:
            cursor.close()
            connection.close()



    @staticmethod
    def get_booth_by_id(exhibitor_id):
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
                SELECT ExhibitorID, ExhibitorName, ExhibitorEmail, 
                    ExhibitorContactInfo, Company, BoothCategory, 
                    BoothSize, BoothRentalFees, Status
                FROM [dbo].[ExhibitorAndBooth]
                WHERE ExhibitorID = ?
                """,
                (exhibitor_id,)
            )
            
            booth = cursor.fetchone()
            if booth:
                return dict(zip([column[0] for column in cursor.description], booth))
            return None

        except pyodbc.Error as e:
            print("Database error: ", e)
            return None

        finally:
            cursor.close()
            connection.close()



    @staticmethod
    def update_booth(exhibitor_id, full_name, email, contact_no, company, booth_category, booth_size, booth_rental_fees, status):
        # Connection string setup
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
            
            # Update statement for booth information
            cursor.execute(
                """
                UPDATE [dbo].[ExhibitorAndBooth]
                SET ExhibitorName = ?, ExhibitorEmail = ?, ExhibitorContactInfo = ?, 
                    Company = ?, BoothCategory = ?, BoothSize = ?, 
                    BoothRentalFees = ?, Status = ?
                WHERE ExhibitorID = ?
                """,
                (full_name, email, contact_no, company, booth_category, 
                 booth_size, booth_rental_fees, status, exhibitor_id)
            )
            
            # Commit the transaction
            connection.commit()

        except pyodbc.Error as e:
            print("Database error during update: ", e)
            raise e

        finally:
            cursor.close()
            connection.close()


    @staticmethod
    def duplicate_boothEmail_for_update(exhibitor_email, exhibitor_id):
        """
        Check if the given email already exists in the ExhibitorAndBooth table
        excluding the current booth's ExhibitorID.
        Returns True if a duplicate is found (excluding the current booth), otherwise False.
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
            
            # Print the query for debugging purposes
            print(f"Checking for duplicate email (excluding current booth) with query: "
                "SELECT COUNT(*) FROM [dbo].[ExhibitorAndBooth] WHERE ExhibitorEmail = ? AND ExhibitorID != ?")
            
            # Query to check for existing email excluding the current exhibitor
            cursor.execute(
                "SELECT COUNT(*) FROM [dbo].[ExhibitorAndBooth] WHERE ExhibitorEmail = ? AND ExhibitorID != ?",
                exhibitor_email, exhibitor_id
            )
            result = cursor.fetchone()
            return result[0] > 0  # Return True if email exists for another booth, otherwise False

        except pyodbc.Error as e:
            print("Database error during email check:", e)
            raise

        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def insert_exhibitor_data(records):
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
                    INSERT INTO [dbo].[ExhibitorAndBooth] (
                        ExhibitorID, ExhibitorName, ExhibitorEmail,
                        ExhibitorContactInfo, Company, BoothCategory,
                        BoothSize, BoothRentalFees, Status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                # Loop through records and insert them
                for record in records:
                    try:
                        cursor.execute(
                            query,
                            (
                                record.get('ExhibitorID'),
                                record.get('ExhibitorName'),
                                record.get('ExhibitorEmail'),
                                record.get('ExhibitorContactInfo'),
                                record.get('Company'),
                                record.get('BoothCategory'),
                                record.get('BoothSize'),
                                record.get('BoothRentalFees'),
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

    @staticmethod
    def get_filtered_booths(categories=None, sizes=None, statuses=None):
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
                SELECT ExhibitorID, ExhibitorName, ExhibitorEmail, 
                    ExhibitorContactInfo, Company, BoothCategory, 
                    BoothSize, BoothRentalFees, Status
                FROM [dbo].[ExhibitorAndBooth]
                WHERE 1=1
            """
            
            params = []
            
            if categories:
                query += " AND BoothCategory IN ({})".format(','.join(['?' for _ in categories]))
                params.extend(categories)
                
            if sizes:
                query += " AND BoothSize IN ({})".format(','.join(['?' for _ in sizes]))
                params.extend(sizes)
                
            if statuses:
                query += " AND Status IN ({})".format(','.join(['?' for _ in statuses]))
                params.extend(statuses)
                
            query += " ORDER BY ExhibitorID"
            
            cursor.execute(query, params)
            booths = cursor.fetchall()
            
            # Convert to list of dictionaries
            booth_list = [dict(zip([column[0] for column in cursor.description], row)) for row in booths]
            return booth_list

        except pyodbc.Error as e:
            print("Database error: ", e)
            return None
            
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def get_paginated_booths(page=1, per_page=5, categories=None, sizes=None, statuses=None, search_query=None):
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
            count_query = "SELECT COUNT(*) FROM [dbo].[ExhibitorAndBooth] WHERE 1=1"
            query_params = []

            # Add filters to count query
            if categories:
                count_query += " AND BoothCategory IN ({})".format(','.join('?' * len(categories)))
                query_params.extend(categories)
            if sizes:
                count_query += " AND BoothSize IN ({})".format(','.join('?' * len(sizes)))
                query_params.extend(sizes)
            if statuses:
                count_query += " AND Status IN ({})".format(','.join('?' * len(statuses)))
                query_params.extend(statuses)
            if search_query:
                count_query += " AND ExhibitorName LIKE ?"
                query_params.extend([f"%{search_query}%"])

            # Get total count
            cursor.execute(count_query, query_params)
            total_records = cursor.fetchone()[0]
            total_pages = ceil(total_records / per_page)
            offset = (page - 1) * per_page

            # Main query for fetching records
            main_query = """
                SELECT ExhibitorID, ExhibitorName, ExhibitorEmail, 
                       ExhibitorContactInfo, Company, BoothCategory, 
                       BoothSize, BoothRentalFees, Status
                FROM [dbo].[ExhibitorAndBooth]
                WHERE 1=1
            """

            # Reset query_params for main query
            query_params = []

            # Add filters to main query
            if categories:
                main_query += " AND BoothCategory IN ({})".format(','.join('?' * len(categories)))
                query_params.extend(categories)
            if sizes:
                main_query += " AND BoothSize IN ({})".format(','.join('?' * len(sizes)))
                query_params.extend(sizes)
            if statuses:
                main_query += " AND Status IN ({})".format(','.join('?' * len(statuses)))
                query_params.extend(statuses)
            if search_query:
                main_query += " AND ExhibitorName LIKE ?"
                query_params.extend([f"%{search_query}%"])

            main_query += " ORDER BY ExhibitorID OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
            query_params.extend([offset, per_page])

            cursor.execute(main_query, query_params)
            booths = cursor.fetchall()
            
            booth_list = [dict(zip([column[0] for column in cursor.description], row)) for row in booths]

            return {
                'booths': booth_list,
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
    def insert_single_booth(record):
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
                INSERT INTO [dbo].[ExhibitorAndBooth] (
                    ExhibitorID, ExhibitorName, ExhibitorEmail,
                    ExhibitorContactInfo, Company, BoothCategory,
                    BoothSize, BoothRentalFees, Status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            cursor.execute(query, (
                record['ExhibitorID'],
                record['ExhibitorName'],
                record['ExhibitorEmail'],
                record['ExhibitorContactInfo'],
                record['Company'],
                record['BoothCategory'],
                record['BoothSize'],
                float(record['BoothRentalFees']),
                record['Status']
            ))

            connection.commit()
            return True

        except pyodbc.Error as e:
            print(f"Database error in insert_single_booth: {e}")
            raise Exception(f"Database error: {str(e)}")

        finally:
            cursor.close()
            connection.close()