from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify,session, send_from_directory, current_app
from werkzeug.utils import secure_filename
import pandas as pd
import re
import os
from datetime import datetime, date
from src.models.eventStaff_model import EventStaffModel

# Create a Blueprint for event staff
event_staff_bp = Blueprint('event_staff', __name__)


class EventStaffController:
    
    @event_staff_bp.after_request
    def add_no_cache_headers(response):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response


    @staticmethod
    @event_staff_bp.route('/OrgViewStaff', methods=['GET'])
    def view_event_staff():
        organiser_id = session.get('organiser_id')
        if not organiser_id:
            flash('You need to log in first.', 'danger')
            return redirect(url_for('login.login'))
        
        # Get filter parameters
        roles = request.args.get('roles', '').split(',') if request.args.get('roles') else None
        statuses = request.args.get('statuses', '').split(',') if request.args.get('statuses') else None
        search_query = request.args.get('search', '')
        page = request.args.get('page', 1, type=int)
        
        # Get paginated staff list with search
        result = EventStaffModel.get_paginated_staff(
            page=page,
            per_page=5,
            roles=roles,
            statuses=statuses,
            search_query=search_query
        )
        
        if not result:
            result = {'staff': [], 'total_pages': 1, 'current_page': 1}
        
        # Check for contract end dates
        current_date = date.today()
        for staff in result['staff']:
            if staff.get('JobEndPeriodFormatted'):
                try:
                    end_date = datetime.strptime(staff['JobEndPeriodFormatted'], '%Y-%m-%d').date()
                    days_until_end = (end_date - current_date).days
                    if days_until_end <= 30:
                        staff['DaysUntilEnd'] = days_until_end
                except (ValueError, TypeError):
                    continue

        return render_template('OrgViewStaff.html', 
                             staff=result['staff'],
                             total_pages=result['total_pages'],
                             current_page=result['current_page'],
                             selected_roles=roles,
                             selected_statuses=statuses,
                             search_query=search_query)
    
    @staticmethod
    @event_staff_bp.route('/search_event_staff', methods=['GET'])  # New route for searching staff
    def search_event_staff():
        organiser_id = session.get('organiser_id')  # Get OrganiserID from the session
        if not organiser_id:
            flash('You need to log in first.', 'danger')
            return redirect(url_for('login.login'))
        query = request.args.get('query', '')  # Get the search query from the request
        staff_list = EventStaffModel.search_event_staff(query)  # Fetch staff based on search query
        return render_template('OrgViewStaff.html', staff=staff_list)
    
 

    @event_staff_bp.route('/OrgAddStaff', methods=['GET', 'POST'])
    def add_staff():
        organiser_id = session.get('organiser_id')  # Get OrganiserID from the session
        if not organiser_id:
            flash('You need to log in first.', 'danger')
            return redirect(url_for('login.login'))
        error_messages = {}
        staff_data = {}

        if request.method == 'POST':
            # Extract data from the form
            full_name = request.form.get('fullName')
            email = request.form.get('email')
            job_start_date = request.form.get('jobStartDate')
            salary = request.form.get('salaryAmount')
            status = request.form.get('status')
            ic_no = request.form.get('icNo')
            contact_no = request.form.get('contactNo')
            role = request.form.get('role')
            job_end_date = request.form.get('jobEndDate')
            one_time_fees = request.form.get('oneTimeFees')

            # Store user inputs in a dictionary
            staff_data = {
                'fullName': full_name,
                'email': email,
                'jobStartDate': job_start_date,
                'salaryAmount': salary,
                'status': status,
                'icNo': ic_no,
                'contactNo': contact_no,
                'role': role,
                'jobEndDate': job_end_date,
                'oneTimeFees': one_time_fees
            }

            # Check if all fields are provided
            if not full_name:
                error_messages['fullName'] = 'Full Name is required.'
            if not email:
                error_messages['email'] = 'Email is required.'
            if not job_start_date:
                error_messages['jobStartDate'] = 'Job Start Date is required.'
            if not salary:
                error_messages['salaryAmount'] = 'Salary Amount is required.'
            if not ic_no:
                error_messages['icNo'] = 'IC No is required.'
            if not contact_no:
                error_messages['contactNo'] = 'Contact No is required.'
            if not job_end_date:
                error_messages['jobEndDate'] = 'Job End Date is required.'
            if not one_time_fees:
                error_messages['oneTimeFees'] = 'One Time Fees is required.'

            # Validate IC No format
            ic_pattern = r"^\d{6}-\d{2}-\d{4}$"  # 6 digits-2 digits-4 digits
            if ic_no and not re.match(ic_pattern, ic_no):
                error_messages['icNo'] = 'IC No must be in the format 12xx56-12-3456.'

            # Validate email format and check for duplicates
            email_pattern = r"[^@]+@[^@]+\.[^@]+"
            if email and not re.match(email_pattern, email):
                error_messages['email'] = 'Invalid email format.'
            elif email and EventStaffModel.check_duplicate_staff_email(email):
                error_messages['email'] = 'Email address is already in use.'

            # Validate contact number (10 to 11 digits)
            if contact_no and not re.match(r"^\d{10,11}$", contact_no):
                error_messages['contactNo'] = 'Contact number must be 10 to 11 digits.'

            # Validate job end date is after job start date
            try:
                job_start_dt = datetime.strptime(job_start_date, '%Y-%m-%dT%H:%M')
                job_end_dt = datetime.strptime(job_end_date, '%Y-%m-%dT%H:%M')
                if job_end_dt <= job_start_dt:
                    error_messages['jobEndDate'] = 'Job End Date must be later than Job Start Date.'
            except ValueError:
                error_messages['jobEndDate'] = 'Invalid date format.'

            # Validate salary and one-time fees
            def validate_decimal(value):
                value = value.replace(',', '.')
                try:
                    float(value)
                    return True
                except ValueError:
                    return False

            if salary and not validate_decimal(salary):
                error_messages['salaryAmount'] = 'Salary must be a valid number (e.g., 50, 50.00, 50.5).'
            elif salary and float(salary) < 0:
                error_messages['salaryAmount'] = 'Salary must be greater than or equal to 0.'

            if one_time_fees and not validate_decimal(one_time_fees):
                error_messages['oneTimeFees'] = 'One Time Fees must be a valid number (e.g., 50, 50.00, 50.5).'
            elif one_time_fees and float(one_time_fees) < 0:
                error_messages['oneTimeFees'] = 'One Time Fees must be greater than or equal to 0.'

            # If there are any validation errors, return to the form with the error messages and the user input
            if error_messages:
                return render_template('OrgAddStaff.html', error_messages=error_messages, staff=staff_data)

            # If there are no errors, proceed to add the staff to the database
            try:
                EventStaffModel.add_staff(
                    full_name,
                    email,
                    job_start_date,
                    salary,
                    status,
                    ic_no,
                    contact_no,
                    role,
                    job_end_date,
                    one_time_fees
                )
                # flash('Staff added successfully!', 'success')
                return redirect(url_for('event_staff.view_event_staff'))
            except Exception as e:
                flash(f'Error adding staff: {str(e)}', 'error')

        # Render the form for GET requests
        return render_template('OrgAddStaff.html', staff=staff_data)


    

    @event_staff_bp.route('/delete_staff', methods=['POST'])
    def delete_staff():
        data = request.get_json()
        staff_ids = data.get('staff_ids', [])

        if not staff_ids:
            return jsonify({'success': False, 'message': 'No staff members selected for deletion'}), 400

        try:
            # Check if any staff members are assigned to events
            assigned_staff = EventStaffModel.get_assigned_staff(staff_ids)

            if assigned_staff:
                assigned_names = ', '.join(assigned_staff)
                return jsonify({
                    'success': False,
                    'message': f"Cannot delete staff members assigned to events: {assigned_names}"
                }), 400

            # Proceed to delete if no assignments found
            EventStaffModel.delete_staff(staff_ids)
            return jsonify({'success': True}), 200

        except Exception as e:
            print(f"Error deleting staff: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500


    @event_staff_bp.route('/edit_staff/<string:staff_id>', methods=['GET', 'POST'])
    def edit_staff(staff_id):
        organiser_id = session.get('organiser_id')  # Get OrganiserID from the session
        if not organiser_id:
            flash('You need to log in first.', 'danger')
            return redirect(url_for('login.login'))
        # Fetch the staff details from the database based on staff_id
        staff = EventStaffModel.get_event_staff_by_id(staff_id)  
        error_messages = {}

        if request.method == 'POST':
            # Extract data from the form
            updated_data = {
                "EventStaffName": request.form.get('fullName'),
                "EventStaffEmail": request.form.get('email'),
                "JobStartPeriod": request.form.get('jobStartDate'),
                "Salary": request.form.get('salaryAmount'),
                "Role": request.form.get('role'),
                "IC": request.form.get('icNo'),
                "EventStaffContactInfo": request.form.get('contactNo'),
                "JobEndPeriod": request.form.get('jobEndDate'),
                "Status": request.form.get('status'),
                "OneTimeFees": request.form.get('oneTimeFees')
            }

            # 1. Check if all required fields are provided
            for field, value in updated_data.items():
                if not value:
                    error_messages[field] = f"{field.replace('_', ' ')} is required."

            # 2. Validate email format and uniqueness
            email = updated_data["EventStaffEmail"]
            if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                error_messages['email'] = "Invalid email format."
            elif email and EventStaffModel.check_duplicate_staff_email_for_update(email, staff_id):
                error_messages['email'] = "Email address is already in use."

            # 3. Validate IC format (must be in the format 123456-12-3456)
            ic_no = updated_data["IC"]
            if ic_no and not re.match(r"^\d{6}-\d{2}-\d{4}$", ic_no):
                error_messages['icNo'] = "IC must be in the format 123456-12-3456."

            # 4. Validate salary and one-time fees (must be non-negative numbers)
            def is_valid_number(value):
                try:
                    return float(value) >= 0
                except ValueError:
                    return False

            salary = updated_data["Salary"]
            one_time_fees = updated_data["OneTimeFees"]
            if salary and not is_valid_number(salary):
                error_messages['salaryAmount'] = "Salary must be a valid non-negative number."
            if one_time_fees and not is_valid_number(one_time_fees):
                error_messages['oneTimeFees'] = "One-Time Fees must be a valid non-negative number."

            # 5. Validate job dates (JobEndPeriod must be later than JobStartPeriod)
            job_start_date = updated_data["JobStartPeriod"]
            job_end_date = updated_data["JobEndPeriod"]

            if job_start_date and job_end_date:
                try:
                    job_start_date_obj = datetime.strptime(job_start_date, '%Y-%m-%dT%H:%M')
                    job_end_date_obj = datetime.strptime(job_end_date, '%Y-%m-%dT%H:%M')
                    if job_end_date_obj <= job_start_date_obj:
                        error_messages['jobEndDate'] = "Job End Date must be later than Job Start Date."
                except ValueError:
                    error_messages['jobStartDate'] = "Invalid date format."

            # If there are any validation errors, render the form with error messages
            if error_messages:
                return render_template('OrgEditStaff.html', staff=staff, error_messages=error_messages)

            # 6. Update the staff details if no validation errors
            EventStaffModel.update_staff(
                staff_id,
                updated_data["EventStaffName"],
                updated_data["EventStaffEmail"],
                updated_data["JobStartPeriod"],
                updated_data["Salary"],
                updated_data["Role"],
                updated_data["IC"],
                updated_data["EventStaffContactInfo"],
                updated_data["JobEndPeriod"],
                updated_data.get("OneTimeFees", 0),
                updated_data["Status"]
            )

            return redirect(url_for('event_staff.view_event_staff'))

        # Render the form for editing staff
        return render_template('OrgEditStaff.html', staff=staff)
    
    # Define allowed_file function outside the route handler
def allowed_file(filename):
    allowed_extensions = {'xlsx', 'xls'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@event_staff_bp.route('/upload_staff_file', methods=['POST'])
def upload_staff_file():
    # Add session check
    organiser_id = session.get('organiser_id')
    if not organiser_id:
        return redirect(url_for('event_staff.view_event_staff', error='Please login first'))

    try:
        if 'file' not in request.files:
            return redirect(url_for('event_staff.view_event_staff', error='No file part'))
        
        file = request.files['file']
        if file.filename == '':
            return redirect(url_for('event_staff.view_event_staff', error='No selected file'))
        
        if not allowed_file(file.filename):
            return redirect(url_for('event_staff.view_event_staff', error='Invalid file type'))

        # Read Excel file
        data = pd.read_excel(file)
        data.columns = data.columns.str.strip()

        # Expected columns validation
        expected_columns = [
            'Staff ID', 'Name', 'Email', 'Contact No', 'IC No',
            'Salary (RM)', 'One Time Fee (RM)', 'Role', 'Job Start Period', 
            'Job End Period', 'Status'
        ]

        # Check for missing columns
        missing_columns = set(expected_columns) - set(data.columns)
        if missing_columns:
            return redirect(url_for('event_staff.view_event_staff', 
                error=f"Missing columns: {', '.join(missing_columns)}"))

        # Column mapping for database insertion
        column_mapping = {
            'Staff ID': 'EventStaffID',
            'Name': 'EventStaffName',
            'Email': 'EventStaffEmail',
            'Contact No': 'EventStaffContactInfo',
            'IC No': 'IC',
            'Salary (RM)': 'Salary',
            'One Time Fee (RM)': 'OneTimeFees',
            'Role': 'Role',
            'Job Start Period': 'JobStartPeriod',
            'Job End Period': 'JobEndPeriod',
            'Status': 'Status'
        }
        data.rename(columns=column_mapping, inplace=True)
        records = data.to_dict(orient='records')

        # Retrieve existing IDs and emails for duplicate checking
        existing_ids = {record['EventStaffID'] for record in EventStaffModel.get_all_event_staff()}
        existing_emails = {record['EventStaffEmail'] for record in EventStaffModel.get_all_event_staff()}
        valid_roles = {"Speaker", "Coordinator", "Support"}
        valid_statuses = {"Active", "Inactive"}

        valid_records = []
        error_messages = []
        
        # First pass: Validate all records
        for index, record in enumerate(records, start=2):
            row_errors = []
            
            # Validate Staff ID
            staff_id = record.get('EventStaffID', '')
            if not re.match(r'^Stf\d{5}$', str(staff_id)):
                row_errors.append(f"Invalid Staff ID: {staff_id}")
            elif staff_id in existing_ids:
                row_errors.append(f"Duplicate Staff ID: {staff_id}")

            # Validate Email
            email = record.get('EventStaffEmail', '')
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                row_errors.append(f"Invalid Email: {email}")
            elif email in existing_emails:
                row_errors.append(f"Duplicate Email: {email}")

            # Contact number validation
            contact_no = str(record.get('EventStaffContactInfo', ''))  # Ensure it is a string

            if contact_no and contact_no.isdigit():
                # Prepend "0" if the contact number does not already start with "0"
                if not contact_no.startswith('0'):
                    contact_no = '0' + contact_no

                # Now validate the contact number length
                if len(contact_no) < 10 or len(contact_no) > 11:
                    row_errors.append(f"Invalid Contact No: {contact_no} (must be 10 to 11 digits)")
                else:
                    # Update the contact number in the record
                    record['EventStaffContactInfo'] = contact_no
            else:
                row_errors.append(f"Invalid Contact No: {contact_no}")


            # Validate IC No
            ic_no = record.get('IC', '')
            if not re.match(r'^\d{6}-\d{2}-\d{4}$', ic_no):
                row_errors.append(f"Invalid IC No: {ic_no}")

            # Validate Role
            role = record.get('Role', '').strip().title()
            if role not in valid_roles:
                row_errors.append(f"Invalid Role: {role}")

            # Validate Salary and One-Time Fees
            try:
                salary = float(record.get('Salary', 0))
                if salary < 0:
                    row_errors.append(f"Invalid Salary: {salary}")
            except ValueError:
                row_errors.append(f"Invalid Salary: {record.get('Salary')}")
            
            try:
                one_time_fee = float(record.get('OneTimeFees', 0))
                if one_time_fee < 0:
                    row_errors.append(f"Invalid One-Time Fee: {one_time_fee}")
            except ValueError:
                row_errors.append(f"Invalid One-Time Fee: {record.get('OneTimeFees')}")

            # Validate Job Start and End Periods
            try:
                job_start = pd.to_datetime(record.get('JobStartPeriod'), format='%m/%d/%Y %I:%M:%S %p', errors='coerce')
                job_end = pd.to_datetime(record.get('JobEndPeriod'), format='%m/%d/%Y %I:%M:%S %p', errors='coerce')
                if pd.isnull(job_start) or pd.isnull(job_end) or job_end <= job_start:
                    row_errors.append(f"Invalid Job Periods: Start - {job_start} cannot later than End - {job_end}")
            except Exception as e:
                row_errors.append(f"Error parsing Job Periods: {e}")

            # Validate Status
            status = record.get('Status', '').strip().title()
            if status not in valid_statuses:
                row_errors.append(f"Invalid Status: {status}")

            # If errors found, skip insertion for this record
            if row_errors:
                error_messages.extend(row_errors)
                continue

            # Prepare record for insertion
            record['Role'] = role
            record['Status'] = status
            valid_records.append(record)

        # Process valid records even if there are some invalid ones
        success_count = 0
        if valid_records:
            for record in valid_records:
                try:
                    if EventStaffModel.insert_single_staff(record):
                        success_count += 1
                except Exception as e:
                    error_messages.append(f"Error inserting record {record['EventStaffID']}: {str(e)}")

        # Prepare response message
        if error_messages:
            error_text = "Records failed to upload:<br>" + "<br>".join(error_messages)
            if success_count > 0:
                return redirect(url_for('event_staff.view_event_staff', 
                    success=f'Successfully uploaded {success_count} record(s)',
                    error=error_text))
            else:
                return redirect(url_for('event_staff.view_event_staff', 
                    error=error_text))

        return redirect(url_for('event_staff.view_event_staff', 
            success=f'Successfully uploaded {success_count} record(s)'))

    except Exception as e:
        print(f"Exception: {e}")
        return redirect(url_for('event_staff.view_event_staff', 
            error=f"Error processing file: {str(e)}"))



    

@event_staff_bp.route('/download_staff_template')
def download_staff_template():
        directory = os.path.join(current_app.root_path, 'src', 'DataTemplates')
        filename = 'staff_template.xlsx'
        return send_from_directory(directory, filename, as_attachment=True)