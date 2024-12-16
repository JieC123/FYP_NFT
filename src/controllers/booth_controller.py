from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify,session, send_from_directory, current_app
from werkzeug.utils import secure_filename
import pandas as pd
import re
import os
from src.models.booth_model import BoothModel

booth_bp = Blueprint('booth', __name__)

class BoothController:


    @booth_bp.after_request
    def add_no_cache_headers(response):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response

    @staticmethod
    @booth_bp.route('/OrgViewBooth', methods=['GET'])
    def view_booths():
        organiser_id = session.get('organiser_id')
        if not organiser_id:
            flash('You need to log in first.', 'danger')
            return redirect(url_for('login.login'))
        
        page = request.args.get('page', 1, type=int)
        search_query = request.args.get('query', '')
        selected_categories = request.args.getlist('categories')
        selected_sizes = request.args.getlist('sizes')
        selected_statuses = request.args.getlist('statuses')
        
        result = BoothModel.get_paginated_booths(
            page=page,
            categories=selected_categories,
            sizes=selected_sizes,
            statuses=selected_statuses,
            search_query=search_query
        )
        
        if not result:
            result = {'booths': [], 'total_pages': 1, 'current_page': 1}
        
        return render_template('OrgViewBooth.html', 
                             booths=result['booths'],
                             total_pages=result['total_pages'],
                             current_page=result['current_page'],
                             selected_categories=selected_categories,
                             selected_sizes=selected_sizes,
                             selected_statuses=selected_statuses)
    


    

    @staticmethod
    @booth_bp.route('/search_exhibitors', methods=['GET'])
    def search_exhibitors():
        organiser_id = session.get('organiser_id')
        if not organiser_id:
            flash('You need to log in first.', 'danger')
            return redirect(url_for('login.login'))
        
        page = request.args.get('page', 1, type=int)
        query = request.args.get('query', '')
        
        result = BoothModel.get_paginated_booths(
            page=page,
            search_query=query
        )
        
        if not result:
            result = {'booths': [], 'total_pages': 1, 'current_page': 1}
        
        return render_template('OrgViewBooth.html', 
                             booths=result['booths'],
                             total_pages=result['total_pages'],
                             current_page=result['current_page'],
                             query=query)
    

    @booth_bp.route('/OrgAddBooth', methods=['GET', 'POST'])
    def add_exhibitor():
        organiser_id = session.get('organiser_id')  
        if not organiser_id:
            flash('You need to log in first.', 'danger')
            return redirect(url_for('login.login'))
        error_messages = {}
        exhibitor_name = exhibitor_email = company = contact_no = booth_category = booth_size = booth_rental_fees = status = ''

        if request.method == 'POST':
            # Extract data from the form
            exhibitor_name = request.form.get('fullName')
            exhibitor_email = request.form.get('email')
            company = request.form.get('company')
            contact_no = request.form.get('contactNo')
            booth_category = request.form.get('boothCategory')
            booth_size = request.form.get('boothSize')
            booth_rental_fees = request.form.get('boothRentalFees')
            status = request.form.get('status')

            # Validation
            if not exhibitor_name:
                error_messages['fullName'] = 'Full Name is required.'
            
            # Email Validation: Check if email is valid and unique
            if not exhibitor_email:
                error_messages['email'] = 'Email is required.'
            elif not re.match(r"[^@]+@[^@]+\.[^@]+", exhibitor_email):
                error_messages['email'] = 'Please enter a valid email address.'
            elif BoothModel.is_email_exists(exhibitor_email):
                error_messages['email'] = 'Email address is already in use.'
            
            # Contact Number Validation (10-11 digits)
            if not contact_no:
                error_messages['contactNo'] = 'Contact number is required.'
            elif not re.match(r"^\d{10,11}$", contact_no):
                error_messages['contactNo'] = 'Contact number must be 10 to 11 digits.'
            
            # Booth Rental Fees Validation (greater than or equal to 0)
            if not booth_rental_fees:
                error_messages['boothRentalFees'] = 'Booth rental fees are required.'
            elif float(booth_rental_fees) < 0:
                error_messages['boothRentalFees'] = 'Booth rental fees must be greater than or equal to 0.'

            # Other field validations
            if not company:
                error_messages['company'] = 'Company is required.'
            if not booth_category:
                error_messages['boothCategory'] = 'Booth category is required.'
            if not booth_size:
                error_messages['boothSize'] = 'Booth size is required.'
            if not status:
                error_messages['status'] = 'Status is required.'

            # If there are no validation errors, proceed with adding the exhibitor
            if not error_messages:
                try:
                    # Add the exhibitor to the database
                    BoothModel.add_exhibitor(
                        exhibitor_name,
                        exhibitor_email,
                        company,
                        contact_no,
                        booth_category,
                        booth_size,
                        booth_rental_fees,
                        status
                    )
                    # flash('Exhibitor added successfully!', 'success')
                    return redirect(url_for('booth.view_booths'))  # Redirect to OrgViewBooth.html after successful addition
                except Exception as e:
                    flash('Error adding exhibitor. Please try again.', 'error')

        return render_template(
            'OrgAddBooth.html',
            error_messages=error_messages,
            exhibitor_name=exhibitor_name,
            exhibitor_email=exhibitor_email,
            company=company,
            contact_no=contact_no,
            booth_category=booth_category,
            booth_size=booth_size,
            booth_rental_fees=booth_rental_fees,
            status=status
        )


    
    @booth_bp.route('/delete_exhibitor', methods=['POST'])
    def delete_exhibitor():
        data = request.get_json()
        exhibitor_ids = data.get('exhibitor_ids', [])

        if not exhibitor_ids:
            return jsonify({'success': False, 'message': 'No exhibitors selected for deletion'}), 400

        try:
            result = BoothModel.delete_exhibitor(exhibitor_ids)
            if not result['success']:
                return jsonify(result), 400
            return jsonify(result), 200
        except Exception as e:
            print(f"Error deleting exhibitor: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

        


    @booth_bp.route('/edit_booth/<string:exhibitor_id>', methods=['GET', 'POST'])
    def edit_booth(exhibitor_id):
        organiser_id = session.get('organiser_id')  # Get OrganiserID from the session
        if not organiser_id:
            flash('You need to log in first.', 'danger')
            return redirect(url_for('login.login'))
        error_messages = {}  # Initialize an empty dictionary to store error messages

        if request.method == 'POST':
            # Retrieve form data for the update
            full_name = request.form.get('fullName')
            email = request.form.get('email')
            company = request.form.get('company')
            contact_no = request.form.get('contactNo')
            booth_category = request.form.get('boothCategory')
            booth_size = request.form.get('boothSize')
            booth_rental_fees = request.form.get('boothRentalFees')
            status = request.form.get('status')

            # Perform Validation
            # Validate required fields
            if not full_name or not email or not company or not contact_no or not booth_category or not booth_size or not booth_rental_fees or not status:
                error_messages['general'] = "All fields are required."

            # Validate email format
            email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
            if not re.match(email_pattern, email):
                error_messages['email'] = "Please enter a valid email address."

            # Check if the email is unique (excluding the current booth's email)
            if BoothModel.duplicate_boothEmail_for_update(email, exhibitor_id):
                error_messages['email_unique'] = "Email address is already in use."

            # Validate contact number (10 to 11 digits)
            contact_pattern = r'^\d{10,11}$'
            if not re.match(contact_pattern, contact_no):
                error_messages['contact_no'] = "Contact number must be 10 to 11 digits."

            # Validate booth rental fees (must be a number and >= 0)
            try:
                booth_rental_fees = float(booth_rental_fees)
                if booth_rental_fees < 0:
                    error_messages['booth_rental_fees'] = "Booth rental fees must be a number and more than or equal to 0."
            except ValueError:
                error_messages['booth_rental_fees'] = "Booth rental fees must be a valid number."

            # If there are any validation errors, return to the form with the error messages
            if error_messages:
                booth = {
                    'ExhibitorID': exhibitor_id,
                    'ExhibitorName': full_name,
                    'ExhibitorEmail': email,
                    'Company': company,
                    'ExhibitorContactInfo': contact_no,
                    'BoothCategory': booth_category,
                    'BoothSize': booth_size,
                    'BoothRentalFees': booth_rental_fees,
                    'Status': status
                }
                return render_template('OrgEditBooth.html', error_messages=error_messages, booth=booth)

            # Update booth information in the database
            try:
                BoothModel.update_booth(
                    exhibitor_id, full_name, email, contact_no,
                    company, booth_category, booth_size, booth_rental_fees, status
                )
                return redirect(url_for('booth.view_booths'))  # Adjust if you have a booth listing page
            except Exception as e:
                error_messages['update_error'] = "An error occurred while updating the booth."
                booth = {
                    'ExhibitorID': exhibitor_id,
                    'ExhibitorName': full_name,
                    'ExhibitorEmail': email,
                    'Company': company,
                    'ExhibitorContactInfo': contact_no,
                    'BoothCategory': booth_category,
                    'BoothSize': booth_size,
                    'BoothRentalFees': booth_rental_fees,
                    'Status': status
                }
                return render_template('OrgEditBooth.html', error_messages=error_messages, booth=booth)

        # Retrieve booth data to populate the form
        booth = BoothModel.get_booth_by_id(exhibitor_id)  # Now passing booth directly
        if booth:
            return render_template('OrgEditBooth.html', booth=booth, error_messages=error_messages)
        else:
            return jsonify({'success': False, 'message': 'Booth not found'}), 404





def allowed_file(filename):
    allowed_extensions = {'xlsx', 'xls'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@booth_bp.route('/upload_booth_file', methods=['POST'])
def upload_booth_file():
    if 'file' not in request.files:
        return redirect(url_for('booth.view_booths', error='No file selected'))

    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('booth.view_booths', error='No file selected'))

    if not allowed_file(file.filename):
        return redirect(url_for('booth.view_booths', error='Invalid file type. Please use .xlsx or .xls files'))

    try:
        # Read the Excel file
        data = pd.read_excel(file)
        data.columns = data.columns.str.strip()

        # Expected columns to validate the input file
        expected_columns = [
            'Exhibitor ID', 'Name', 'Email', 'Contact No', 'Company', 'Category',
            'Booth Size (meters)', 'Rental Fees (RM)', 'Status'
        ]

        # Check for missing columns
        missing_columns = set(expected_columns) - set(data.columns)
        if missing_columns:
            return redirect(url_for('booth.view_booths', error=f"Missing columns: {', '.join(missing_columns)}"))

        # Column mapping for database insertion
        column_mapping = {
            'Exhibitor ID': 'ExhibitorID',
            'Name': 'ExhibitorName',
            'Email': 'ExhibitorEmail',
            'Contact No': 'ExhibitorContactInfo',
            'Company': 'Company',
            'Category': 'BoothCategory',
            'Booth Size (meters)': 'BoothSize',
            'Rental Fees (RM)': 'BoothRentalFees',
            'Status': 'Status'
        }
        data.rename(columns=column_mapping, inplace=True)
        records = data.to_dict(orient='records')

        # Validate records before inserting
        valid_records = []
        errors = []

        # Retrieve existing Exhibitor IDs and Emails for duplicate checking
        existing_ids = {record['ExhibitorID'] for record in BoothModel.get_all_booths()}
        existing_emails = {record['ExhibitorEmail'] for record in BoothModel.get_all_booths()}
        valid_categories = {"Standard", "High Class", "Supreme"}
        valid_sizes = {"3x3", "5x5", "8x8"}
        valid_statuses = {"Active", "Inactive"}

        for index, record in enumerate(records, start=2):  # Start at row 2 for clarity in errors
            row_errors = []

            # Validate Exhibitor ID
            exhibitor_id = record.get('ExhibitorID', '')
            if not re.match(r'^Exh\d{5}$', str(exhibitor_id)):
                row_errors.append(f"Invalid Exhibitor ID: {exhibitor_id}")
            elif exhibitor_id in existing_ids:
                row_errors.append(f"Duplicate Exhibitor ID: {exhibitor_id}")

            # Validate Email
            email = record.get('ExhibitorEmail', '')
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                row_errors.append(f"Invalid Email: {email}")
            elif email in existing_emails:
                row_errors.append(f"Duplicate Email: {email}")

            contact_no = str(record.get('ExhibitorContactInfo', ''))  # Ensure it is a string

            if contact_no and contact_no.isdigit():
                # Prepend "0" if the contact number does not already start with "0"
                if not contact_no.startswith('0'):
                    contact_no = '0' + contact_no

                # Now validate the contact number length
                if len(contact_no) < 10 or len(contact_no) > 11:
                    row_errors.append(f"Invalid Contact No: {contact_no} (must be 10 to 11 digits)")
                else:
                    # Update the contact number in the record
                    record['ExhibitorContactInfo'] = contact_no
            else:
                row_errors.append(f"Invalid Contact No: {contact_no}")


            # Validate Booth Category
            category = record.get('BoothCategory', '').strip().title()
            if category not in valid_categories:
                row_errors.append(f"Invalid Booth Category: {category}")

            # Validate Booth Size (meters)
            booth_size = record.get('BoothSize', '').split()[0]
            if booth_size not in valid_sizes:
                row_errors.append(f"Invalid Booth Size: {booth_size}")

            # Validate Rental Fees
            try:
                rental_fees = float(record.get('BoothRentalFees', 0))
                if rental_fees < 0:
                    row_errors.append(f"Invalid Rental Fees: {rental_fees}")
            except ValueError:
                row_errors.append(f"Invalid Rental Fees: {record.get('BoothRentalFees')}")

            # Validate Status
            status = record.get('Status', '').strip().title()
            if status not in valid_statuses:
                row_errors.append(f"Invalid Status: {status}")

            # If errors found for this row, add to errors list and skip insertion
            if row_errors:
                errors.append(f"Row {index}: " + "; ".join(row_errors))
                continue

            # Prepare record for insertion
            record['BoothCategory'] = category
            record['BoothSize'] = booth_size
            record['Status'] = status
            valid_records.append(record)

        # Track successful and failed records
        success_count = 0
        error_messages = []

        # Process each valid record individually
        for record in valid_records:
            try:
                if BoothModel.insert_single_booth(record):
                    success_count += 1
            except Exception as e:
                error_message = f"Error inserting record {record.get('ExhibitorID', 'Unknown')}: {str(e)}"
                error_messages.append(error_message)

        # Prepare response message
        if error_messages or errors:  # Combine both validation and insertion errors
            response_messages = []
            if errors:  # Validation errors
                response_messages.extend(errors)
            if error_messages:  # Database insertion errors
                response_messages.extend(error_messages)
            
            error_text = "<br>".join(response_messages)
            
            if success_count > 0:
                return redirect(url_for('booth.view_booths', 
                    success=f'Successfully uploaded {success_count} record(s)',
                    error=error_text))
            else:
                return redirect(url_for('booth.view_booths', 
                    error=error_text))

        return redirect(url_for('booth.view_booths', 
            success=f'Successfully uploaded {success_count} record(s)'))

    except Exception as e:
        print(f"Exception: {e}")
        return redirect(url_for('booth.view_booths', 
            error=f"Error processing file: {str(e)}"))




@booth_bp.route('/download_booth_template')
def download_booth_template():
    directory = os.path.join(current_app.root_path, 'src', 'DataTemplates')
    filename = 'booth_template.xlsx'  # Updated template filename
    return send_from_directory(directory, filename, as_attachment=True)