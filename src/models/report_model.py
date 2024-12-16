from config import Config
import pyodbc

class ReportModel:
    @staticmethod
    def get_events_for_report(organiser_id):
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
            
            query = """
                SELECT EventID, EventTitle 
                FROM [dbo].[Event]
                WHERE OrganiserID = ?
                ORDER BY EventTitle ASC
            """
            
            cursor.execute(query, (organiser_id,))
            
            events = [{'EventID': str(row.EventID), 'EventTitle': row.EventTitle} 
                     for row in cursor.fetchall()]
            
            return events
            
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
            "Trusted_Connection=yes;"
            "Encrypt=no;"
        )
        
        try:
            connection = pyodbc.connect(connection_string)
            cursor = connection.cursor()
            
            query = """
                SELECT EventTitle, EventStartDate, EventEndDate
                FROM [dbo].[Event]
                WHERE EventID = ?
            """
            
            cursor.execute(query, (event_id,))
            event = cursor.fetchone()
            
            if event:
                return {
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
    def get_staff_allocation(event_id):
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
            
            query = """
                SELECT 
                    es.EventStaffName,
                    es.Role,
                    es.Salary,
                    es.OneTimeFees,
                    esa.HoursWorked
                FROM EventStaff es
                JOIN EventStaffAssignment esa ON es.EventStaffID = esa.EventStaffID
                WHERE esa.EventID = ?
                ORDER BY es.EventStaffName
            """
            
            cursor.execute(query, (event_id,))
            staff_records = []
            
            for row in cursor.fetchall():
                # Calculate hourly rate (Salary divided by 720 hours in a month)
                hourly_rate = float(row.Salary) / 720
                
                # Calculate total cost (One time fees + (Hours worked × Hourly rate))
                total_cost = float(row.OneTimeFees) + (float(row.HoursWorked) * hourly_rate)
                
                staff_records.append({
                    'name': row.EventStaffName,
                    'role': row.Role,
                    'salary': float(row.Salary),
                    'one_time_fees': float(row.OneTimeFees),
                    'hours_worked': float(row.HoursWorked),
                    'total_cost': round(total_cost, 2)
                })
            
            return staff_records
            
        except pyodbc.Error as e:
            print(f"Database error: {e}")
            return []
            
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def get_exhibitor_allocation(event_id):
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
            
            query = """
                SELECT 
                    e.ExhibitorID,
                    e.ExhibitorName,
                    e.Company,
                    e.BoothRentalFees,
                    a.RentalStartDate,
                    a.RentalEndDate,
                    a.TotalRentalDays
                FROM ExhibitorAndBooth e
                JOIN ExhibitorAndBoothAssignment a ON e.ExhibitorID = a.ExhibitorID
                WHERE a.EventID = ?
                ORDER BY e.ExhibitorName
            """
            
            cursor.execute(query, (event_id,))
            exhibitor_records = []
            
            for row in cursor.fetchall():
                # Calculate total rental charges
                total_rental_charges = float(row.BoothRentalFees) * float(row.TotalRentalDays)
                
                exhibitor_records.append({
                    'ExhibitorID': row.ExhibitorID,
                    'ExhibitorName': row.ExhibitorName,
                    'Company': row.Company,
                    'RentalStartDate': row.RentalStartDate,
                    'RentalEndDate': row.RentalEndDate,
                    'TotalRentalDays': float(row.TotalRentalDays),
                    'BoothRentalFees': float(row.BoothRentalFees),
                    'TotalRentalCharges': round(total_rental_charges, 2)
                })
            
            return exhibitor_records
            
        except pyodbc.Error as e:
            print(f"Database error: {e}")
            return []
            
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def get_event_summary(start_date, end_date, organiser_id):
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
            
            query = """
                WITH ParticipantCounts AS (
                    SELECT EventID, COUNT(*) as ParticipantCount
                    FROM [dbo].[Participants]
                    GROUP BY EventID
                ),
                BudgetSummary AS (
                    SELECT 
                        EventID,
                        SUM(BudgetAmount) as TotalBudget,
                        SUM(ExpensesAmount) as TotalExpenses,
                        SUM(RemainingBudgetAmount) as TotalRemaining
                    FROM [dbo].[EventBudgetsAndExpenses]
                    GROUP BY EventID
                )
                SELECT 
                    e.EventTitle,
                    e.EventStartDate,
                    e.EventEndDate,
                    ISNULL(p.ParticipantCount, 0) as ParticipantCount,
                    ISNULL(b.TotalBudget, 0) as TotalBudget,
                    ISNULL(b.TotalExpenses, 0) as TotalExpenses,
                    ISNULL(b.TotalRemaining, 0) as TotalRemaining
                FROM [dbo].[Event] e
                LEFT JOIN ParticipantCounts p ON e.EventID = p.EventID
                LEFT JOIN BudgetSummary b ON e.EventID = b.EventID
                WHERE e.OrganiserID = ?
                AND e.EventStartDate BETWEEN ? AND ?
                ORDER BY e.EventStartDate ASC
            """
            
            cursor.execute(query, (organiser_id, start_date, end_date))
            
            events = []
            for row in cursor.fetchall():
                events.append({
                    'EventTitle': row.EventTitle,
                    'EventStartDate': row.EventStartDate.strftime('%Y-%m-%d'),
                    'EventEndDate': row.EventEndDate.strftime('%Y-%m-%d'),
                    'ParticipantCount': row.ParticipantCount,
                    'Budget': float(row.TotalBudget),
                    'Expenses': float(row.TotalExpenses),
                    'RemainingBudget': float(row.TotalRemaining)
                })
            
            return events
            
        except pyodbc.Error as e:
            print(f"Database error: {e}")
            return []
            
        finally:
            cursor.close()
            connection.close()
