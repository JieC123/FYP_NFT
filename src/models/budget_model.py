from config import Config
import pyodbc
from decimal import Decimal

class BudgetModel:
    @staticmethod
    def get_events_for_budget(organiser_id):
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
            
            # Convert the results to a list of dictionaries
            columns = [column[0] for column in cursor.description]
            events = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            return events
            
        except pyodbc.Error as e:
            print(f"Database error: {e}")
            return []
            
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def get_event_budget_details(event_id):
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
                SELECT b.BudgetID, b.EventID,
                       ec.ExpensesName as CategoryName, 
                       CAST(b.BudgetAmount AS DECIMAL(10,2)) as BudgetAmount,
                       CAST(b.ExpensesAmount AS DECIMAL(10,2)) as ExpensesAmount,
                       CAST(b.RemainingBudgetAmount AS DECIMAL(10,2)) as RemainingBudgetAmount,
                       b.Vendor, b.PaymentStatus, b.Comments
                FROM [dbo].[EventBudgetsAndExpenses] b
                JOIN [dbo].[ExpensesCategory] ec ON b.CategoryID = ec.CategoryID
                WHERE b.EventID = ?
                ORDER BY b.BudgetID ASC
            """
            
            cursor.execute(query, (event_id,))
            rows = cursor.fetchall()
            
            budget_list = []
            for row in rows:
                budget_list.append({
                    'BudgetID': str(row.BudgetID).strip(),
                    'CategoryName': row.CategoryName,
                    'BudgetAmount': float(row.BudgetAmount),
                    'ExpensesAmount': float(row.ExpensesAmount),
                    'RemainingBudgetAmount': float(row.RemainingBudgetAmount),
                    'Vendor': row.Vendor,
                    'PaymentStatus': row.PaymentStatus,
                    'Comments': row.Comments
                })
            
            return budget_list
            
        except pyodbc.Error as e:
            print(f"Database error: {e}")
            return []
            
        finally:
            if connection:
                connection.close()

    @staticmethod
    def get_budget_by_id(budget_id):
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
                SELECT b.BudgetID, b.EventID, b.CategoryID,
                       ec.ExpensesName as CategoryName, 
                       CAST(b.BudgetAmount AS DECIMAL(10,2)) as BudgetAmount,
                       CAST(b.ExpensesAmount AS DECIMAL(10,2)) as ExpensesAmount,
                       CAST(b.RemainingBudgetAmount AS DECIMAL(10,2)) as RemainingBudgetAmount,
                       b.Vendor, b.PaymentStatus, b.Comments
                FROM [dbo].[EventBudgetsAndExpenses] b
                JOIN [dbo].[ExpensesCategory] ec ON b.CategoryID = ec.CategoryID
                WHERE b.BudgetID = ?
            """
            
            cursor.execute(query, (budget_id,))
            row = cursor.fetchone()
            
            if row:
                return {
                    'BudgetID': str(row.BudgetID).strip(),
                    'EventID': str(row.EventID).strip(),
                    'CategoryID': str(row.CategoryID).strip(),
                    'CategoryName': row.CategoryName,
                    'BudgetAmount': float(row.BudgetAmount),
                    'ExpensesAmount': float(row.ExpensesAmount),
                    'RemainingBudgetAmount': float(row.RemainingBudgetAmount),
                    'Vendor': row.Vendor,
                    'PaymentStatus': row.PaymentStatus,
                    'Comments': row.Comments
                }
            return None
            
        except pyodbc.Error as e:
            print(f"Database error: {e}")
            return None
            
        finally:
            if connection:
                connection.close()

    @staticmethod
    def get_expense_categories():
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
                SELECT CategoryID, ExpensesName
                FROM [dbo].[ExpensesCategory]
                ORDER BY ExpensesName ASC
            """
            
            cursor.execute(query)
            categories = [{'CategoryID': str(row.CategoryID).strip(), 
                          'ExpensesName': row.ExpensesName} 
                         for row in cursor.fetchall()]
            return categories
            
        except pyodbc.Error as e:
            print(f"Database error: {e}")
            return []
            
        finally:
            if connection:
                connection.close()

    @staticmethod
    def update_budget(budget_id, budget_data):
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
                UPDATE [dbo].[EventBudgetsAndExpenses]
                SET BudgetAmount = ?,
                    ExpensesAmount = ?,
                    RemainingBudgetAmount = ?,
                    CategoryID = ?,
                    Vendor = ?,
                    PaymentStatus = ?,
                    Comments = ?
                WHERE BudgetID = ?
            """
            
            remaining_amount = float(budget_data['budgetAmount']) - float(budget_data['expensesAmount'])
            
            params = (
                budget_data['budgetAmount'],
                budget_data['expensesAmount'],
                remaining_amount,
                budget_data['categoryName'],  # This is actually CategoryID from the form
                budget_data['vendor'],
                budget_data['paymentStatus'],
                budget_data['comments'],
                budget_id
            )
            
            cursor.execute(query, params)
            connection.commit()
            return True
            
        except pyodbc.Error as e:
            print(f"Database error in update_budget: {e}")
            return False
            
        finally:
            if connection:
                connection.close()

    @staticmethod
    def generate_next_budget_id():
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
            
            # Get the highest BudgetID
            query = """
                SELECT TOP 1 BudgetID
                FROM [dbo].[EventBudgetsAndExpenses]
                ORDER BY BudgetID DESC
            """
            
            cursor.execute(query)
            result = cursor.fetchone()
            
            if result:
                # Extract the number from the last ID and increment
                last_id = result[0]
                next_number = int(last_id[1:]) + 1
            else:
                # If no existing records, start with 1
                next_number = 1
                
            # Format the new ID with leading zeros
            new_id = f"B{next_number:05d}"
            return new_id
            
        except pyodbc.Error as e:
            print(f"Database error in generate_next_budget_id: {e}")
            return None
            
        finally:
            if connection:
                connection.close()

    @staticmethod
    def add_budget(budget_data):
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
            
            # Generate new BudgetID
            budget_id = BudgetModel.generate_next_budget_id()
            if not budget_id:
                return False
            
            query = """
                INSERT INTO [dbo].[EventBudgetsAndExpenses]
                (BudgetID, EventID, CategoryID, BudgetAmount, ExpensesAmount, 
                 RemainingBudgetAmount, Vendor, PaymentStatus, Comments)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            remaining_amount = float(budget_data['budgetAmount']) - float(budget_data['expensesAmount'])
            
            params = (
                budget_id,
                budget_data['event_id'],
                budget_data['categoryName'],  # This is actually CategoryID from the form
                budget_data['budgetAmount'],
                budget_data['expensesAmount'],
                remaining_amount,
                budget_data['vendor'],
                budget_data['paymentStatus'],
                budget_data['comments']
            )
            
            cursor.execute(query, params)
            connection.commit()
            return True
            
        except pyodbc.Error as e:
            print(f"Database error in add_budget: {e}")
            return False
            
        finally:
            if connection:
                connection.close()

    @staticmethod
    def delete_budgets(budget_ids):
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
            
            # Create a parameterized query with the correct number of placeholders
            placeholders = ','.join(['?' for _ in budget_ids])
            query = f"""
                DELETE FROM [dbo].[EventBudgetsAndExpenses]
                WHERE BudgetID IN ({placeholders})
            """
            
            cursor.execute(query, tuple(budget_ids))
            connection.commit()
            return True
            
        except pyodbc.Error as e:
            print(f"Database error in delete_budgets: {e}")
            return False
            
        finally:
            if connection:
                connection.close()
