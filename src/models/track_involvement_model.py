import pyodbc
from config import Config

class TrackInvolvementModel:


    @staticmethod
    def getStaffDetail(event_id):
        """Fetch staff assignment details based on event_id"""
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
                SELECT EventStaffID, HoursWorked, DateAssigned 
                FROM [dbo].[EventStaffAssignment]
                WHERE EventID = ?
                """,
                (event_id,)
            )
            
            assignments = cursor.fetchall()
            staff_ids = [row[0] for row in assignments]

            return staff_ids

        except pyodbc.Error as e:
            print("Database error (getStaffDetail): ", e)
            return None
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def match_staff(staff_ids, roles=None, statuses=None):
        """Fetch staff details using staff IDs with optional filters"""
        if not staff_ids:
            return []

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
            
            # Generate the base query with placeholders for staff IDs
            placeholders = ', '.join('?' for _ in staff_ids)
            query = f"""
                SELECT EventStaffID, EventStaffName, EventStaffEmail, 
                    EventStaffContactInfo, IC, Role, JobStartPeriod, 
                    JobEndPeriod, Salary, OneTimeFees, Status
                FROM [dbo].[EventStaff]
                WHERE EventStaffID IN ({placeholders})
            """
            params = staff_ids.copy()

            # Add role filter if specified
            if roles:
                role_placeholders = ', '.join('?' for _ in roles)
                query += f" AND Role IN ({role_placeholders})"
                params.extend(roles)

            # Add status filter if specified
            if statuses:
                status_placeholders = ', '.join('?' for _ in statuses)
                query += f" AND Status IN ({status_placeholders})"
                params.extend(statuses)
            
            cursor.execute(query, params)
            staff_details = cursor.fetchall()
            
            # Convert to list of dictionaries and format dates
            staff_list = []
            for row in staff_details:
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
            print("Database error (match_staff): ", e)
            return None
        finally:
            cursor.close()
            connection.close()


    @staticmethod
    def get_event_name(event_id):
        """Fetch event name based on event_id"""
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
                SELECT EventTitle
                FROM [dbo].[Event]
                WHERE EventID = ?
                """,
                (event_id,)
            )

            event = cursor.fetchone()
            if event:
                return event[0]  # Return event title

            return None

        except pyodbc.Error as e:
            print("Database error (get_event_name): ", e)
            return None
        finally:
            cursor.close()
            connection.close()




    @staticmethod
    def get_booth_details(event_id):
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

            # SQL query to fetch event title along with booth details
            cursor.execute(
                """
                SELECT e.EventTitle, b.ExhibitorID, b.ExhibitorName, b.ExhibitorEmail, b.ExhibitorContactInfo, 
                    b.Company, b.Status, b.BoothCategory, b.BoothSize, b.BoothRentalFees
                FROM [dbo].[ExhibitorAndBooth] b
                JOIN [dbo].[ExhibitorAndBoothAssignment] a 
                    ON b.ExhibitorID = a.ExhibitorID
                JOIN [dbo].[Event] e 
                    ON a.EventID = e.EventID
                WHERE a.EventID = ?
                """,
                (event_id,)
            )

            booths = cursor.fetchall()

            booth_list = []
            event_name = None
            for row in booths:
                booth_dict = dict(zip([column[0] for column in cursor.description], row))
                booth_list.append(booth_dict)
                
                # Store the event title (assuming it's the same for all rows)
                event_name = booth_dict.get('EventTitle')

            return event_name, booth_list

        except pyodbc.Error as e:
            print("Database error: ", e)
            return None, []

        finally:
            cursor.close()
            connection.close()



    @staticmethod
    def get_sponsorship_details(event_id):
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
            
            # Updated query to fetch event name along with sponsorship details
            cursor.execute(
                """
                SELECT e.EventTitle, s.SponsorshipID, s.SponsorshipName, s.SponsorshipEmail, 
                    s.SponsorshipContactInfo, s.Company, s.SponsorDetail, 
                    s.AmountContributed, s.PaymentSchedule, s.Status
                FROM [dbo].[Sponsorship] s
                JOIN [dbo].[SponsorshipAssignment] a ON s.SponsorshipID = a.SponsorshipID
                JOIN [dbo].[Event] e ON a.EventID = e.EventID
                WHERE a.EventID = ?
                """,
                (event_id,)
            )
            sponsors = cursor.fetchall()

            sponsor_list = []
            event_name = None
            for row in sponsors:
                sponsor_dict = dict(zip([column[0] for column in cursor.description], row))
                sponsor_list.append(sponsor_dict)
                
                # Store the event name (assuming it's the same for all rows)
                event_name = sponsor_dict.get('EventTitle')

            return event_name, sponsor_list

        except pyodbc.Error as e:
            print("Database error: ", e)
            return None, []

        finally:
            cursor.close()
            connection.close()


    @staticmethod
    def search_allocated_staff(query, event_id):
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

            # Search for staff by name (partial match), only those allocated to the specific event
            cursor.execute("""
                SELECT EventStaffID, EventStaffName, EventStaffEmail, EventStaffContactInfo,
                    IC, Role, JobStartPeriod, JobEndPeriod, Salary, OneTimeFees, Status
                FROM [dbo].[EventStaff]
                WHERE EventStaffName LIKE ? AND EventStaffID IN (
                    SELECT EventStaffID
                    FROM [dbo].[EventStaffAssignment]
                    WHERE EventID = ?
                )
            """, (f'%{query}%', event_id))
            
            staff = cursor.fetchall()

            staff_list = []
            for row in staff:
                staff_dict = dict(zip([column[0] for column in cursor.description], row))
                staff_list.append(staff_dict)

            return staff_list
        
        except pyodbc.Error as e:
            print("Database error: ", e)
            return []

        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def search_allocated_booth(query, event_id):
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

            cursor.execute("""
                SELECT e.EventTitle, b.ExhibitorID, b.ExhibitorName, b.ExhibitorEmail, 
                    b.ExhibitorContactInfo, b.Company, b.Status, b.BoothCategory, 
                    b.BoothSize, b.BoothRentalFees
                FROM [dbo].[ExhibitorAndBooth] b
                JOIN [dbo].[ExhibitorAndBoothAssignment] a ON b.ExhibitorID = a.ExhibitorID
                JOIN [dbo].[Event] e ON a.EventID = e.EventID
                WHERE a.EventID = ? AND b.ExhibitorName LIKE ?
            """, (event_id, f'%{query}%'))
            
            booths = cursor.fetchall()
            
            booth_list = []
            for row in booths:
                booth_dict = dict(zip([column[0] for column in cursor.description], row))
                booth_list.append(booth_dict)

            return booth_list
        
        except pyodbc.Error as e:
            print("Database error: ", e)
            return []

        finally:
            cursor.close()
            connection.close()


    @staticmethod
    def search_allocated_sponsorship(query, event_id):
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

            cursor.execute("""
                SELECT e.EventTitle, s.SponsorshipID, s.SponsorshipName, s.SponsorshipEmail, 
                    s.SponsorshipContactInfo, s.Company, s.SponsorDetail, 
                    s.AmountContributed, s.PaymentSchedule, s.Status
                FROM [dbo].[Sponsorship] s
                JOIN [dbo].[SponsorshipAssignment] a ON s.SponsorshipID = a.SponsorshipID
                JOIN [dbo].[Event] e ON a.EventID = e.EventID
                WHERE a.EventID = ? AND s.SponsorshipName LIKE ?
            """, (event_id, f'%{query}%'))
            
            sponsors = cursor.fetchall()
            
            sponsor_list = []
            for row in sponsors:
                sponsor_dict = dict(zip([column[0] for column in cursor.description], row))
                sponsor_list.append(sponsor_dict)

            return sponsor_list
        
        except pyodbc.Error as e:
            print("Database error: ", e)
            return []

        finally:
            cursor.close()
            connection.close()


    @staticmethod
    def is_booth_email_exists(exhibitor_email):
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
            
            # Query to check for existing email
            cursor.execute(
                "SELECT COUNT(*) FROM [dbo].[ExhibitorAndBooth] WHERE ExhibitorEmail = ?", 
                exhibitor_email
            )
            result = cursor.fetchone()
            return result[0] > 0  # Return True if the email exists, otherwise False

        except pyodbc.Error as e:
            print("Database error during email check:", e)
            return False

        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def get_participant_details(event_id):
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

            cursor.execute("""
                SELECT e.EventTitle, p.ParticipantID, u.UserID, u.UserName, u.UserEmail, 
                    u.UserContactInfo, p.RegistrationDate
                FROM [dbo].[Participants] p
                JOIN [dbo].[TicketingUser] u ON p.UserID = u.UserID
                JOIN [dbo].[Event] e ON p.EventID = e.EventID
                WHERE p.EventID = ?
            """, (event_id,))

            participants = cursor.fetchall()
            
            participant_list = []
            event_name = None
            for row in participants:
                participant_dict = dict(zip([column[0] for column in cursor.description], row))
                participant_list.append(participant_dict)
                event_name = participant_dict.get('EventTitle')

            return event_name, participant_list

        except pyodbc.Error as e:
            print("Database error: ", e)
            return None, []
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def search_allocated_participant(query, event_id):
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

            cursor.execute("""
                SELECT e.EventTitle, p.ParticipantID, u.UserID, u.UserName, u.UserEmail, 
                    u.UserContactInfo, p.RegistrationDate
                FROM [dbo].[Participants] p
                JOIN [dbo].[TicketingUser] u ON p.UserID = u.UserID
                JOIN [dbo].[Event] e ON p.EventID = e.EventID
                WHERE p.EventID = ? AND u.UserName LIKE ?
            """, (event_id, f'%{query}%'))
            
            participants = cursor.fetchall()
            
            participant_list = []
            for row in participants:
                participant_dict = dict(zip([column[0] for column in cursor.description], row))
                participant_list.append(participant_dict)

            return participant_list
        
        except pyodbc.Error as e:
            print("Database error: ", e)
            return []
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def get_filtered_sponsorship_details(event_id, packages=None, schedules=None, statuses=None):
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
                SELECT e.EventTitle, s.SponsorshipID, s.SponsorshipName, s.SponsorshipEmail, 
                    s.SponsorshipContactInfo, s.Company, s.SponsorDetail, 
                    s.AmountContributed, s.PaymentSchedule, s.Status
                FROM [dbo].[Sponsorship] s
                JOIN [dbo].[SponsorshipAssignment] a ON s.SponsorshipID = a.SponsorshipID
                JOIN [dbo].[Event] e ON a.EventID = e.EventID
                WHERE a.EventID = ?
            """
            params = [event_id]

            if packages:
                query += " AND s.SponsorDetail IN ({})".format(','.join('?' * len(packages)))
                params.extend(packages)
            if schedules:
                query += " AND s.PaymentSchedule IN ({})".format(','.join('?' * len(schedules)))
                params.extend(schedules)
            if statuses:
                query += " AND s.Status IN ({})".format(','.join('?' * len(statuses)))
                params.extend(statuses)

            cursor.execute(query, params)
            sponsors = cursor.fetchall()
            
            sponsor_list = []
            event_name = None
            for row in sponsors:
                sponsor_dict = dict(zip([column[0] for column in cursor.description], row))
                sponsor_list.append(sponsor_dict)
                event_name = sponsor_dict.get('EventTitle')

            return event_name, sponsor_list

        except pyodbc.Error as e:
            print("Database error: ", e)
            return None, []
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def get_filtered_booth_details(event_id, categories=None, sizes=None, statuses=None):
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
                SELECT e.EventTitle, b.ExhibitorID, b.ExhibitorName, b.ExhibitorEmail, 
                    b.ExhibitorContactInfo, b.Company, b.Status, b.BoothCategory, 
                    b.BoothSize, b.BoothRentalFees
                FROM [dbo].[ExhibitorAndBooth] b
                JOIN [dbo].[ExhibitorAndBoothAssignment] a ON b.ExhibitorID = a.ExhibitorID
                JOIN [dbo].[Event] e ON a.EventID = e.EventID
                WHERE a.EventID = ?
            """
            params = [event_id]

            if categories:
                query += " AND b.BoothCategory IN ({})".format(','.join('?' * len(categories)))
                params.extend(categories)
            if sizes:
                query += " AND b.BoothSize IN ({})".format(','.join('?' * len(sizes)))
                params.extend(sizes)
            if statuses:
                query += " AND b.Status IN ({})".format(','.join('?' * len(statuses)))
                params.extend(statuses)

            cursor.execute(query, params)
            booths = cursor.fetchall()
            
            booth_list = []
            event_name = None
            for row in booths:
                booth_dict = dict(zip([column[0] for column in cursor.description], row))
                booth_list.append(booth_dict)
                event_name = booth_dict.get('EventTitle')

            return event_name, booth_list

        except pyodbc.Error as e:
            print("Database error: ", e)
            return None, []
        finally:
            cursor.close()
            connection.close()

