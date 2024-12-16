from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, current_app
from src.models.participant_model import ParticipantModel
import pandas as pd
from datetime import datetime
from flask import session
import os
from werkzeug.utils import secure_filename

participant_bp = Blueprint('participant', __name__)

# Add no-cache headers
@participant_bp.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Add these constants at the top of your file
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@participant_bp.route('/OrgViewParticipant', methods=['GET'])
def view_participants():
    organiser_id = session.get('organiser_id')
    if not organiser_id:
        flash('You need to log in first.', 'danger')
        return redirect(url_for('login.login'))

    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 5  # Consistent with sponsorship page

    # Get filter parameters
    selected_events = request.args.get('events', '').split(',')
    selected_events = [e for e in selected_events if e]
    
    # Get search query
    search_query = request.args.get('query', '')

    # Get all events for the filter modal
    events = ParticipantModel.get_all_events()
    
    # Fetch participants for the organiser's events
    result = ParticipantModel.get_paginated_participants(
        page=page,
        per_page=per_page,
        events=selected_events if selected_events else None,
        search_query=search_query,
        organiser_id=organiser_id  # Pass organiser_id to filter events
    )
    
    if not result:
        result = {
            'participants': [], 
            'total_pages': 1, 
            'current_page': 1,
            'total_records': 0
        }

    return render_template('OrgViewParticipant.html', 
                         participants=result['participants'],
                         total_pages=result['total_pages'],
                         current_page=result['current_page'],
                         events=events,
                         selected_events=selected_events,
                         error=request.args.get('error'),
                         success=request.args.get('success'))

@participant_bp.route('/search_participants', methods=['GET'])
def search_participants():
    organiser_id = session.get('organiser_id')
    if not organiser_id:
        flash('You need to login first.', 'warning')
        return redirect(url_for('login.login'))

    page = request.args.get('page', 1, type=int)
    query = request.args.get('query', '').strip()
    
    # Get all events for the filter modal (only for this organiser)
    events = ParticipantModel.get_all_events()
    
    # Get selected events from the URL parameters
    selected_events = request.args.get('events', '').split(',')
    selected_events = [e for e in selected_events if e]
    
    # Pass organiser_id to get_paginated_participants
    result = ParticipantModel.get_paginated_participants(
        page=page,
        per_page=5,
        search_query=query,
        events=selected_events if selected_events else None,
        organiser_id=organiser_id  # Add this line
    )
    
    if not result:
        result = {
            'participants': [], 
            'total_pages': 1, 
            'current_page': 1,
            'total_records': 0
        }

    return render_template('OrgViewParticipant.html', 
                         participants=result['participants'],
                         total_pages=result['total_pages'],
                         current_page=result['current_page'],
                         events=events,
                         selected_events=selected_events)

@participant_bp.route('/check_user/<user_id>')
def check_user(user_id):
    # Add session check
    organiser_id = session.get('organiser_id')
    if not organiser_id:
        return jsonify({'error': 'Authentication required'}), 401

    user = ParticipantModel.get_user_by_id(user_id)
    if user:
        return jsonify({
            'exists': True,
            'user': {
                'UserName': user['UserName'],
                'UserEmail': user['UserEmail'],
                'UserContactInfo': user['UserContactInfo']
            }
        })
    return jsonify({'exists': False})

@participant_bp.route('/register_participant', methods=['POST'])
def register_participant():
    # Add session check
    organiser_id = session.get('organiser_id')
    if not organiser_id:
        return jsonify({
            'success': False,
            'message': 'Authentication required'
        }), 401

    try:
        data = request.get_json()
        
        user_id = data.get('userID', '').strip()
        event_id = data.get('eventID', '').strip()
        registration_date = data.get('registrationDate', '').strip()

        # Simple required field validation
        if not user_id or not event_id or not registration_date:
            return jsonify({
                'success': False,
                'message': 'All fields are required'
            }), 400

        # Check if user exists before proceeding with registration
        user = ParticipantModel.get_user_by_id(user_id)
        if not user:
            return jsonify({
                'success': False,
                'message': 'User ID not found. Please verify the User ID and try again.'
            }), 400

        try:
            success = ParticipantModel.add_participant(user_id, event_id, registration_date)
            return jsonify({
                'success': True,
                'message': 'Participant registered successfully'
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    except Exception as e:
        print("Error registering participant:", str(e))
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@participant_bp.route('/delete_participants', methods=['POST'])
def delete_participants():
    # Add session check
    organiser_id = session.get('organiser_id')
    if not organiser_id:
        return jsonify({
            'success': False,
            'message': 'Authentication required'
        }), 401

    try:
        data = request.get_json()
        participant_ids = data.get('participant_ids', [])

        if not participant_ids:
            return jsonify({
                'success': False,
                'message': 'No participants selected for deletion'
            }), 400

        success = ParticipantModel.delete_participants(participant_ids)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Participants deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to delete participants'
            }), 500

    except Exception as e:
        print("Error deleting participants:", str(e))
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@participant_bp.route('/OrgEditParticipant/<participant_id>')
def edit_participant(participant_id):
    # Session check already exists in this function
    organiser_id = session.get('organiser_id')
    if not organiser_id:
        flash('You need to login first.', 'warning')
        return redirect(url_for('login.login'))

    try:
        # Get participant details
        participant = ParticipantModel.get_participant_by_id(participant_id)
        if not participant:
            flash('Participant not found.', 'error')
            return redirect(url_for('participant.view_participants'))

        # Get all events for the dropdown
        events = ParticipantModel.get_all_events()
        
        return render_template('OrgEditParticipant.html', 
                             participant=participant,
                             events=events)
    except Exception as e:
        print("Error fetching participant details:", str(e))
        flash('Error loading participant details.', 'error')
        return redirect(url_for('participant.view_participants'))

@participant_bp.route('/update_participant', methods=['POST'])
def update_participant():
    # Add session check
    organiser_id = session.get('organiser_id')
    if not organiser_id:
        return jsonify({
            'success': False,
            'message': 'Authentication required'
        }), 401

    try:
        data = request.get_json()
        
        # Extract data from request
        participant_id = data.get('participantID')
        user_id = data.get('userID')
        event_id = data.get('eventID', '').strip()
        registration_date = data.get('registrationDate', '').strip()

        # Only validate event_id and registration_date as they are the only editable required fields
        if not event_id or not registration_date:
            return jsonify({
                'success': False,
                'message': 'Event and Registration Date are required fields'
            }), 400

        success = ParticipantModel.update_participant(
            participant_id=participant_id,
            user_id=user_id,
            event_id=event_id,
            registration_date=registration_date
        )

        if success:
            return jsonify({
                'success': True,
                'message': 'Participant updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to update participant'
            }), 500

    except Exception as e:
        print("Error updating participant:", str(e))
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@participant_bp.route('/download_participant_template')
def download_participant_template():
    directory = os.path.join(current_app.root_path, 'src', 'DataTemplates')
    filename = 'participant_template.xlsx'
    return send_from_directory(directory, filename, as_attachment=True)

@participant_bp.route('/upload_participant_file', methods=['POST'])
def upload_participant_file():
    # Add session check
    organiser_id = session.get('organiser_id')
    if not organiser_id:
        return redirect(url_for('participant.view_participants', error='Please login first'))

    try:
        if 'file' not in request.files:
            return redirect(url_for('participant.view_participants', error='No file part'))
        
        file = request.files['file']
        if file.filename == '':
            return redirect(url_for('participant.view_participants', error='No selected file'))
        
        if not allowed_file(file.filename):
            return redirect(url_for('participant.view_participants', error='Invalid file type'))

        # Get organiser's events
        organiser_id = session.get('organiser_id')
        if not organiser_id:
            return redirect(url_for('participant.view_participants', error='Please login first'))

        # Get existing data and valid IDs
        organiser_events = ParticipantModel.get_all_events()
        valid_event_ids = [str(event['EventID']) for event in organiser_events]  # Convert to string
        existing_user_event_combinations = ParticipantModel.get_existing_user_event_combinations()
        existing_participant_ids = ParticipantModel.get_existing_participant_ids()

        # Read Excel file
        df = pd.read_excel(file)
        
        valid_records = []
        error_messages = []
        
        # First pass: Validate all records
        for index, row in enumerate(df.to_dict('records'), start=2):
            row_errors = []
            current_record = {}

            # Validate Participant ID
            participant_id = str(row.get('Participant ID', '')).strip()
            if not participant_id:
                row_errors.append(f"Row {index}: Participant ID is required")
            elif not participant_id.startswith('P') or not participant_id[1:].isdigit() or len(participant_id) != 7:
                row_errors.append(f"Row {index}: Invalid Participant ID format: {participant_id} (must be P followed by 6 digits)")
            elif participant_id in existing_participant_ids:
                row_errors.append(f"Row {index}: Duplicate Participant ID: {participant_id} already exists in database")
            else:
                current_record['ParticipantID'] = participant_id

            # Validate Registration Date
            registration_date = row.get('Registration Date')
            if pd.isna(registration_date):
                row_errors.append(f"Row {index}: Registration Date is required")
            else:
                try:
                    registration_date = pd.to_datetime(registration_date)
                    current_record['RegistrationDate'] = registration_date
                except:
                    row_errors.append(f"Row {index}: Invalid Registration Date format (required: YYYY-MM-DD HH:MM:SS)")

            # Validate Event ID
            event_id = str(row.get('Event ID', '')).strip()
            if not event_id:
                row_errors.append(f"Row {index}: Event ID is required")
            elif event_id not in valid_event_ids:
                row_errors.append(f"Row {index}: Invalid Event ID: {event_id}")
            else:
                current_record['EventID'] = event_id

            # Validate User ID
            user_id = str(row.get('User ID', '')).strip()
            if not user_id:
                row_errors.append(f"Row {index}: User ID is required")
            elif not user_id.startswith('TU') or not user_id[2:].isdigit() or len(user_id) != 8:
                row_errors.append(f"Row {index}: Invalid User ID format: {user_id} (must be TU followed by 6 digits)")
            else:
                current_record['UserID'] = user_id

            # If no errors for this row, add to valid records
            if not row_errors:
                valid_records.append(current_record)
            else:
                error_messages.extend(row_errors)

        # Process valid records even if there are some invalid ones
        success_count = 0
        if valid_records:
            for record in valid_records:
                try:
                    success = ParticipantModel.add_participant(
                        user_id=record['UserID'],
                        event_id=record['EventID'],
                        registration_date=record['RegistrationDate'].strftime('%Y-%m-%d %H:%M:%S')
                    )
                    if success:
                        success_count += 1
                except Exception as e:
                    error_messages.append(f"Error inserting record {record['ParticipantID']}: {str(e)}")

        # Prepare response message
        if error_messages:
            error_text = "Records failed to upload:<br>" + "<br>".join(error_messages)
            if success_count > 0:
                return redirect(url_for('participant.view_participants', 
                    success=f'Successfully uploaded {success_count} record(s)',
                    error=error_text))
            else:
                return redirect(url_for('participant.view_participants', 
                    error=error_text))

        return redirect(url_for('participant.view_participants', 
            success=f'Successfully uploaded {success_count} record(s)'))

    except Exception as e:
        print(f"Exception: {e}")
        return redirect(url_for('participant.view_participants', 
            error=f"Error processing file: {str(e)}"))

@participant_bp.route('/delete_selected_participants', methods=['POST'])
def delete_selected_participants():
    # Add session check
    organiser_id = session.get('organiser_id')
    if not organiser_id:
        return jsonify({
            'success': False,
            'message': 'Authentication required'
        }), 401

    try:
        data = request.get_json()
        participant_ids = data.get('participant_ids', [])

        if not participant_ids:
            return jsonify({
                'success': False,
                'message': 'No participants selected for deletion'
            }), 400

        success = ParticipantModel.delete_selected_participants(participant_ids)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Participants deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to delete participants'
            }), 500

    except Exception as e:
        print("Error deleting participants:", str(e))
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@participant_bp.route('/OrgAddParticipant', methods=['GET'])
def add_participant():
    # Add session check
    organiser_id = session.get('organiser_id')
    if not organiser_id:
        flash('You need to login first.', 'warning')
        return redirect(url_for('login.login'))

    try:
        events = ParticipantModel.get_all_events()  # Get events for dropdown
        return render_template('OrgAddParticipant.html', events=events)
    except Exception as e:
        print("Error fetching events:", str(e))
        flash('Error loading events.', 'error')
        return render_template('OrgAddParticipant.html', events=[])