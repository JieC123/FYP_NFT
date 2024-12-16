from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify,session, send_from_directory, current_app
from werkzeug.utils import secure_filename
import pandas as pd
import re
import os
from config import Config
from src.models.sponsorship_model import SponsorshipModel


# Create a Blueprint for sponsorship
sponsorship_bp = Blueprint('sponsorship', __name__)

class SponsorshipController:

    # Add the after_request function to prevent caching
    @sponsorship_bp.after_request
    def add_no_cache_headers(response):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response


    @staticmethod
    @sponsorship_bp.route('/OrgViewSponsorship', methods=['GET'])
    def view_sponsorships():
        organiser_id = session.get('organiser_id')
        if not organiser_id:
            flash('You need to log in first.', 'danger')
            return redirect(url_for('login.login'))

        # Get filter parameters
        page = request.args.get('page', 1, type=int)
        packages = request.args.get('packages')
        schedules = request.args.get('schedules')
        statuses = request.args.get('statuses')
        search_query = request.args.get('query')

        selected_packages = packages.split(',') if packages else []
        selected_schedules = schedules.split(',') if schedules else []
        selected_statuses = statuses.split(',') if statuses else []

        # Get paginated sponsorships
        result = SponsorshipModel.get_paginated_sponsorships(
            page=page,
            per_page=5,
            packages=selected_packages if selected_packages else None,
            schedules=selected_schedules if selected_schedules else None,
            statuses=selected_statuses if selected_statuses else None,
            search_query=search_query
        )
        
        if not result:
            result = {'sponsorships': [], 'total_pages': 1, 'current_page': 1}

        return render_template('OrgViewSponsorship.html', 
                             sponsorships=result['sponsorships'],
                             total_pages=result['total_pages'],
                             current_page=result['current_page'],
                             selected_packages=selected_packages,
                             selected_schedules=selected_schedules,
                             selected_statuses=selected_statuses)
    
    @staticmethod
    @sponsorship_bp.route('/search_sponsorships', methods=['GET'])
    def search_sponsorships():
        organiser_id = session.get('organiser_id')
        if not organiser_id:
            flash('You need to log in first.', 'danger')
            return redirect(url_for('login.login'))
        
        # Get parameters
        page = request.args.get('page', 1, type=int)
        query = request.args.get('query', '')
        
        # Get paginated search results
        result = SponsorshipModel.get_paginated_sponsorships(
            page=page,
            per_page=5,
            search_query=query
        )
        
        if not result:
            result = {'sponsorships': [], 'total_pages': 1, 'current_page': 1}

        return render_template('OrgViewSponsorship.html', 
                             sponsorships=result['sponsorships'],
                             total_pages=result['total_pages'],
                             current_page=result['current_page'],
                             selected_packages=[],
                             selected_schedules=[],
                             selected_statuses=[])
    



    @sponsorship_bp.route('/OrgAddSponsorship', methods=['GET', 'POST'])
    def add_sponsorship():
        error_messages = {}
        form_data = {}
        
        # Get OrganiserID from the session
        organiser_id = session.get('organiser_id')
        if not organiser_id:
            flash('You need to log in first.', 'danger')
            return redirect(url_for('login.login'))
        
        if request.method == 'POST':
            # Extract and strip data from the form
            form_data = {
                'full_name': request.form.get('fullName', '').strip(),
                'email': request.form.get('email', '').strip(),
                'company': request.form.get('company', '').strip(),
                'contact_no': request.form.get('contactNo', '').strip(),
                'sponsor_detail': request.form.get('sponsorDetail', '').strip(),
                'amount_contributed': request.form.get('sponsorAmount', '').strip(),
                'payment_schedule': request.form.get('paymentSchedule', '').strip(),
                'status': request.form.get('status', '').strip()
            }

            # Server-side validation
            if not all(form_data.values()):
                error_messages['general'] = "All fields are required."

            # Validate email format
            email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
            if not re.match(email_pattern, form_data['email']):
                error_messages['email'] = "Invalid email format."

            # Validate contact number (10-11 digits)
            if not re.match(r'^\d{10,11}$', form_data['contact_no']):
                error_messages['contact_no'] = "Contact number must be 10 to 11 digits."

            # Validate sponsor amount (must be a positive number)
            try:
                sponsor_amount = float(form_data['amount_contributed'])
                if sponsor_amount <= 0:
                    error_messages['amount_contributed'] = "Sponsor amount must be more than 0."
            except ValueError:
                error_messages['amount_contributed'] = "Sponsor amount must be a valid number."

            # Check for duplicate email
            if not error_messages and SponsorshipModel.check_duplicate_email(form_data['email']):
                error_messages['email'] = "Email already exists. Please use a different email."

            # If no errors, proceed with adding the sponsorship
            if not error_messages:
                try:
                    SponsorshipModel.add_sponsorship(
                        form_data['full_name'],
                        form_data['email'],
                        form_data['company'],
                        form_data['contact_no'],
                        form_data['sponsor_detail'],
                        sponsor_amount,
                        form_data['payment_schedule'],
                        form_data['status']
                    )
                    return redirect(url_for('sponsorship.view_sponsorships'))
                except Exception as e:
                    print(f'Error adding sponsorship: {str(e)}')
                    error_messages['general'] = "Error adding sponsorship. Please try again."

        return render_template('OrgAddSponsorship.html', error_messages=error_messages, form_data=form_data)




    

    @sponsorship_bp.route('/delete_sponsorship', methods=['POST'])
    def delete_sponsorship():
        data = request.get_json()
        sponsorship_ids = data.get('sponsorship_ids', [])

        if not sponsorship_ids:
            return jsonify({'success': False, 'message': 'No sponsorships selected for deletion'}), 400

        try:
            result = SponsorshipModel.delete_sponsorship(sponsorship_ids)
            if not result['success']:
                return jsonify(result), 400
            return jsonify(result), 200
        except Exception as e:
            print(f"Error deleting sponsorship: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500



    @staticmethod
    @sponsorship_bp.route('/OrgEditSponsorship/<sponsorship_id>', methods=['GET', 'POST'])
    def edit_sponsorship(sponsorship_id):


        organiser_id = session.get('organiser_id')  # Get OrganiserID from the session
        if not organiser_id:
            flash('You need to log in first.', 'danger')
            return redirect(url_for('login.login'))
        
        sponsorship = SponsorshipModel.get_sponsorship_by_id(sponsorship_id)

        error_messages = {}

        if request.method == 'POST':
            # Handle the form submission for updates
            full_name = request.form.get('fullName').strip()
            email = request.form.get('email').strip()
            company = request.form.get('company').strip()
            contact_no = request.form.get('contactNo').strip()
            sponsor_detail = request.form.get('sponsorDetail').strip()
            amount_contributed = request.form.get('sponsorAmount').strip()
            payment_schedule = request.form.get('paymentSchedule').strip()
            status = request.form.get('status').strip()

            # Server-side validation
            errors = []

            # 1. Full Name Validation
            if not full_name or len(full_name) < 3:
                errors.append("Full name must be at least 3 characters long.")
                error_messages['fullName'] = "Full name must be at least 3 characters long."
            
                        # 2. Email Validation - common format check and uniqueness (except for the current record)
            email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
            if not email or not re.match(email_pattern, email):
                errors.append("Please enter a valid email address.")
                error_messages['email'] = "Please enter a valid email address."
            else:
                # Check if the email is already used by another record, excluding the current sponsorship
                if SponsorshipModel.check_duplicate_email_for_update(email, sponsorship_id):
                    errors.append("Email already exists. Please use a different email.")
                    error_messages['email'] = "Email already exists. Please use a different email."


            
            # 3. Company Name Validation
            if not company or len(company) < 2:
                errors.append("Company name must be at least 2 characters long.")
                error_messages['company'] = "Company name must be at least 2 characters long."
            
            # 4. Contact Number Validation - 10-11 digit number
            if not contact_no.isdigit() or not (10 <= len(contact_no) <= 11):
                errors.append("Contact number must be a valid number with 10 to 11 digits.")
                error_messages['contactNo'] = "Contact number must be a valid number with 10 to 11 digits."
            
                    # 5. Sponsor Amount Validation - must be a numeric value > 0
            try:
                # Try converting the amount to a float (works for integers and decimals)
                amount_contributed_value = float(amount_contributed)
                if amount_contributed_value <= 0:
                    errors.append("Sponsor amount must be more than 0.")
                    error_messages['sponsorAmount'] = "Sponsor amount must be a valid number more than 0."
            except ValueError:
                errors.append("Sponsor amount must be more than 0.")
                error_messages['sponsorAmount'] = "Sponsor amount must be a valid number more than 0."

            
            # 6. Sponsor Detail Validation
            if not sponsor_detail:
                errors.append("Sponsor detail is required.")
                error_messages['sponsorDetail'] = "Sponsor detail is required."
            
            # 7. Payment Schedule Validation
            if not payment_schedule:
                errors.append("Payment schedule is required.")
                error_messages['paymentSchedule'] = "Payment schedule is required."
            
            # 8. Status Validation
            if not status:
                errors.append("Status is required.")
                error_messages['status'] = "Status is required."

            # Check if there are any validation errors
            if errors:
                for error in errors:
                    flash(error, "danger")
            else:
                # Update sponsorship information in the database
                try:
                    SponsorshipModel.update_sponsorship(
                        sponsorship_id, full_name, email, contact_no, company,
                        sponsor_detail, amount_contributed, payment_schedule, status
                    )
                    # flash("Sponsorship updated successfully.", "success")
                    return redirect(url_for('sponsorship.view_sponsorships'))
                except Exception as e:
                    print(f"Error updating sponsorship: {e}")
                    flash("An error occurred while updating the sponsorship.", "danger")
        
        return render_template('OrgEditSponsorship.html', sponsorship=sponsorship, error_messages=error_messages)




def allowed_file(filename):
    allowed_extensions = {'xlsx', 'xls'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@sponsorship_bp.route('/upload_file', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(url_for('sponsorship.view_sponsorships', error='No file selected'))

    file = request.files['file']

    if file.filename == '':
        return redirect(url_for('sponsorship.view_sponsorships', error='No file selected'))

    if not allowed_file(file.filename):
        return redirect(url_for('sponsorship.view_sponsorships', error='Invalid file type. Please use .xlsx or .xls files'))

    try:
        # Read the Excel file
        data = pd.read_excel(file)
        data.columns = data.columns.str.strip()

        # Expected columns validation
        expected_columns = [
            'Sponsorship ID', 'Name', 'Email', 'Contact No', 'Company', 'Package',
            'Amount Contributed', 'Payment Schedule', 'Status'
        ]

        # Check for missing columns
        missing_columns = set(expected_columns) - set(data.columns)
        if missing_columns:
            return redirect(url_for('sponsorship.view_sponsorships', 
                error=f"Missing columns: {', '.join(missing_columns)}"))

        # Column mapping for database insertion
        column_mapping = {
            'Sponsorship ID': 'SponsorshipID',
            'Name': 'SponsorshipName',
            'Email': 'SponsorshipEmail',
            'Contact No': 'SponsorshipContactInfo',
            'Company': 'Company',
            'Package': 'SponsorDetail',
            'Amount Contributed': 'AmountContributed',
            'Payment Schedule': 'PaymentSchedule',
            'Status': 'Status'
        }
        data.rename(columns=column_mapping, inplace=True)
        records = data.to_dict(orient='records')

        # Validate records before inserting
        valid_records = []
        errors = []

        existing_ids = {record['SponsorshipID'] for record in SponsorshipModel.get_all_sponsorships()}
        existing_emails = {record['SponsorshipEmail'] for record in SponsorshipModel.get_all_sponsorships()}
        valid_packages = {"Gold Package", "Silver Package", "Supply Package"}
        valid_schedules = {"Monthly", "Quarterly", "One-time"}
        valid_statuses = {"Active", "Inactive"}

        for index, record in enumerate(records, start=2):  # Start at 2 to account for header row
            row_errors = []

            # Sponsorship ID validation
            sponsorship_id = record.get('SponsorshipID', '')
            if not sponsorship_id.startswith("Sp") or not sponsorship_id[2:].isdigit() or len(sponsorship_id) != 7:
                row_errors.append(f"Invalid Sponsorship ID: {sponsorship_id}")
            elif sponsorship_id in existing_ids:
                row_errors.append(f"Duplicate Sponsorship ID: {sponsorship_id}")

            # Email validation
            email = record.get('SponsorshipEmail', '')
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                row_errors.append(f"Invalid Email: {email}")
            elif email in existing_emails:
                row_errors.append(f"Duplicate Email: {email}")

                        
                        # Contact number validation
            contact_no = str(record.get('SponsorshipContactInfo', ''))
            # Always prepend a 0 before validating the contact number
            contact_no = '0' + contact_no

            # Ensure the contact number has 11 or 12 digits after fixing
            if not contact_no.isdigit() or not (10 <= len(contact_no) <= 11):
                row_errors.append(f"Invalid Contact No: {contact_no} (must be 10 to 11 digits)")

            # Package validation
            package = record.get('SponsorDetail', '').title()
            if package not in valid_packages:
                row_errors.append(f"Invalid Package: {package}")

            # Amount Contributed validation
            amount = record.get('AmountContributed', 0)
            if not isinstance(amount, (int, float)) or amount <= 0:
                row_errors.append(f"Invalid Amount Contributed: {amount}")

            # Payment Schedule validation
            schedule = record.get('PaymentSchedule', '').title()
            if schedule not in valid_schedules:
                row_errors.append(f"Invalid Payment Schedule: {schedule}")

            # Status validation
            status = record.get('Status', '').title()
            if status not in valid_statuses:
                row_errors.append(f"Invalid Status: {status}")

            # If errors found, add to the error list
            if row_errors:
                errors.append(f"Row {index}: " + "; ".join(row_errors))
                continue

            # Convert validated fields to standard format
            record['SponsorshipContactInfo'] = contact_no  # Save the corrected contact number
            record['SponsorDetail'] = package
            record['PaymentSchedule'] = schedule
            record['Status'] = status

            valid_records.append(record)

        # Process valid records even if there are some invalid ones
        success_count = 0
        if valid_records:
            for record in valid_records:
                try:
                    if SponsorshipModel.insert_single_sponsorship(record):
                        success_count += 1
                except Exception as e:
                    errors.append(f"Error inserting record {record['SponsorshipID']}: {str(e)}")

        # Prepare response message
        if errors:
            error_text = "Records failed to upload:<br>" + "<br>".join(errors)
            if success_count > 0:
                return redirect(url_for('sponsorship.view_sponsorships', 
                    success=f'Successfully uploaded {success_count} record(s)',
                    error=error_text))
            else:
                return redirect(url_for('sponsorship.view_sponsorships', 
                    error=error_text))

        return redirect(url_for('sponsorship.view_sponsorships', 
            success=f'Successfully uploaded {success_count} record(s)'))

    except Exception as e:
        print(f"Exception: {e}")
        return redirect(url_for('sponsorship.view_sponsorships', 
            error=f"Error processing file: {str(e)}"))


 

@sponsorship_bp.route('/download_sponsorship_template')
def download_sponsorship_template():
    directory = os.path.join(current_app.root_path, 'src', 'DataTemplates')
    filename = 'sponsorship_template.xlsx'
    return send_from_directory(directory, filename, as_attachment=True)




# @sponsorship_bp.route('/sponsorship', methods=['GET', 'POST'])
# def event_for_sponsorship():
#     try:
#         # Fetch events for sponsorship
#         events = SponsorshipModel.get_events_for_sponsorship()

#         # Check if events were found
#         if not events:
#             flash('No events available.', 'warning')

#         # Handle form submission (if POST request)
#         if request.method == 'POST':
#             selected_event_id = request.form.get('eventSelect')
#             if selected_event_id:
#                 flash(f"Event {selected_event_id} selected.", 'success')
#                 # Redirect to another route if needed
#                 return redirect(url_for('sponsorship.process_sponsorship', event_id=selected_event_id))

#         # Render template with events
#         return render_template('OrgAlloSponsorship.html', events=events)  # Pass events to template

#     except Exception as e:
#         flash(f"An error occurred: {e}", 'danger')
#         return redirect(url_for('home')) 


# @sponsorship_bp.route('/sponsorship/process/<event_id>')
# def process_sponsorship(event_id):
#     flash(f"Processing sponsorship for event {event_id}.")
#     # Add your logic here to process the event sponsorship
#     return redirect(url_for('sponsorship.event_for_sponsorship'))