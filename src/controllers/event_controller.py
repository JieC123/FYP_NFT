from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify,session
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from src.models.event_model import EventModel

event_bp = Blueprint('event', __name__)

UPLOAD_FOLDER = 'src/EventImage'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE_MB = 8

@event_bp.route('/events')
def index():
    organiser_id = session.get('organiser_id')
    if not organiser_id:
        flash('You need to log in first.', 'danger')
        return redirect(url_for('login.login'))

    # Get parameters
    page = request.args.get('page', 1, type=int)
    types = request.args.get('types')
    statuses = request.args.get('statuses')
    search_query = request.args.get('query')
    
    selected_types = types.split(',') if types else []
    selected_statuses = statuses.split(',') if statuses else []

    # Get paginated events
    result = EventModel.get_paginated_events(
        organiser_id,
        page=page,
        per_page=5,
        types=selected_types if selected_types else None,
        statuses=selected_statuses if selected_statuses else None,
        search_query=search_query
    )
    
    if not result:
        result = {'events': [], 'total_pages': 1, 'current_page': 1}

    return render_template('OrgViewEvent.html', 
                         events=result['events'],
                         total_pages=result['total_pages'],
                         current_page=result['current_page'],
                         selected_types=selected_types,
                         selected_statuses=selected_statuses)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@event_bp.route('/add_event', methods=['GET', 'POST'])
def add_event():
    organiser_id = session.get('organiser_id')
    if not organiser_id:
        flash('You need to log in first.', 'danger')
        return redirect(url_for('login.login')) 
    
    if request.method == 'POST':
        event_title = request.form.get('eventTitle')
        event_venue = request.form.get('eventVenue')
        event_status = request.form.get('eventStatus')
        event_type = request.form.get('eventType')
        start_date = request.form.get('startDate')
        end_date = request.form.get('endDate')
        capacity = request.form.get('capacity')
        description = request.form.get('description')
        organiser_id = session.get('organiser_id')

        # Check if organiser is logged in
        if not organiser_id:
            return render_template('OrgAddEvent.html', error_message="You need to log in first.")

        # Validate required fields
        if not all([event_title, event_venue, event_status, event_type, start_date, end_date, capacity, description]):
            return render_template('OrgAddEvent.html', error_message="All fields are required.")

        # Validate event end date > start date
        if start_date >= end_date:
            return render_template('OrgAddEvent.html', error_message="Event End Date must be later than Event Start Date.")

        # Validate event capacity is a positive integer without decimals
        if not capacity.isdigit() or int(capacity) <= 0:
            return render_template('OrgAddEvent.html', error_message="Event Capacity must be a valid positive integer.")

        # Handle file upload
        file = request.files.get('eventPoster')
        if file:
            if not allowed_file(file.filename):
                return render_template('OrgAddEvent.html', error_message="Invalid file type. Only image files are allowed.")

            # Validate file size
            file_size_mb = len(file.read()) / (1024 * 1024)  # Calculate size in MB
            file.seek(0)  # Reset file pointer after reading
            if file_size_mb > MAX_FILE_SIZE_MB:
                return render_template('OrgAddEvent.html', error_message="Event Poster file size exceeds 8 MB.")
            
            try:
                # Create upload directory if it doesn't exist
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                
                # Secure the filename and save the file
                filename = secure_filename(file.filename)
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                
                # Save the file
                file.save(file_path)
                event_image_path = filename  # Store just the filename
            except Exception as e:
                print(f"Error saving file: {e}")
                return render_template('OrgAddEvent.html', error_message=f"Error saving image: {e}")
        else:
            event_image_path = None

        try:
            # Add event to database with image path
            EventModel.add_event(
                event_title=request.form.get('eventTitle'),
                event_venue=request.form.get('eventVenue'),
                event_status=request.form.get('eventStatus'),
                event_type=request.form.get('eventType'),
                start_date_str=request.form.get('startDate'),
                end_date_str=request.form.get('endDate'),
                capacity=request.form.get('capacity'),
                description=request.form.get('description'),
                organiser_id=organiser_id,
                event_image_path=event_image_path  # Pass the filename to the model
            )
            return redirect(url_for('event.index'))
        except Exception as e:
            return render_template('OrgAddEvent.html', error_message=f"Error adding event: {e}")

    return render_template('OrgAddEvent.html')




@event_bp.route('/delete_events', methods=['POST'])
def delete_events():
    data = request.get_json()
    event_ids = data.get('event_ids', [])

    if not event_ids:
        return jsonify({'success': False, 'message': 'No events selected for deletion'}), 400

    try:
        # First check dependencies for all events
        error_messages = []
        for event_id in event_ids:
            dependency_message = EventModel.check_event_dependencies(event_id)
            if dependency_message:
                error_messages.append(dependency_message) 
        
        if error_messages:
            return jsonify({
                'success': False, 
                'message': '\n'.join(error_messages)
            }), 400

        # If no dependencies, proceed with deletion
        EventModel.delete_events(event_ids)
        return jsonify({'success': True, 'message': 'Events deleted successfully'}), 200

    except Exception as e:
        print(f"Error deleting events: {e}")
        return jsonify({
            'success': False, 
            'message': str(e)
        }), 500


@event_bp.route('/search_events', methods=['GET'])
def search_events():
    organiser_id = session.get('organiser_id')
    if not organiser_id:
        flash('You need to log in first.', 'danger')
        return redirect(url_for('login.login')) 
    
    page = request.args.get('page', 1, type=int)
    query = request.args.get('query', '')
    
    result = EventModel.get_paginated_events(
        organiser_id,
        page=page,
        per_page=5,
        search_query=query
    )
    
    if not result:
        result = {'events': [], 'total_pages': 1, 'current_page': 1}

    return render_template('OrgViewEvent.html', 
                         events=result['events'],
                         total_pages=result['total_pages'],
                         current_page=result['current_page'])


@event_bp.route('/edit_event/<string:event_id>', methods=['GET'])
def edit_event(event_id):
    organiser_id = session.get('organiser_id')  # Get OrganiserID from the session
    if not organiser_id:
        flash('You need to log in first.', 'danger')
        return redirect(url_for('login.login')) 
    # Retrieve event details using the event ID
    event_details = EventModel.get_event_by_id(event_id)
    
    if event_details:
        # Pass the event details to the edit form
        return render_template('OrgEditEvent.html', event=event_details)
    else:
        #flash(f'Event with ID {event_id} not found.', 'danger')
        return redirect(url_for('event.index'))


@event_bp.route('/update_event', methods=['POST'])
def update_event():
    event_id = request.form.get('eventID')
    event_title = request.form.get('eventTitle')
    event_venue = request.form.get('eventVenue')
    event_status = request.form.get('eventStatus')
    event_type = request.form.get('eventType')
    start_date = request.form.get('startDate')
    end_date = request.form.get('endDate')
    capacity = request.form.get('capacity')
    description = request.form.get('description')
    image = request.files.get('eventPoster')

    # Validation
    error_message = None
    
    # Validate event start and end dates
    if not start_date or not end_date:
        error_message = 'Please provide valid start and end dates.'
    elif datetime.strptime(start_date, '%Y-%m-%dT%H:%M') >= datetime.strptime(end_date, '%Y-%m-%dT%H:%M'):
        error_message = 'Event End Date must be later than Event Start Date.'

    # Validate event capacity (positive integer)
    elif not capacity.isdigit() or int(capacity) <= 0:
        error_message = 'Event capacity must be a positive integer.'
    
    # Validate file type for event poster (if provided)
    if image:
        filename = secure_filename(image.filename)
        if not allowed_file(filename):
            error_message = 'Only image files (png, jpg, jpeg, gif) are allowed.'
        elif image.mimetype not in ['image/png', 'image/jpeg', 'image/gif']:
            error_message = 'Invalid file type for event poster.'

    if error_message:
        return render_template('EditEvent.html', event_id=event_id, error_message=error_message, event=request.form)

    # If validation passes, call the model to update the event
    try:
        EventModel.update_event(
            event_id, event_title, event_venue, event_status, 
            event_type, start_date, end_date, capacity, description, image
        )
        return redirect(url_for('event.index'))
    except Exception as e:
        error_message = f'Error updating event: {e}'
        return render_template('EditEvent.html', event_id=event_id, error_message=error_message, event=request.form)


