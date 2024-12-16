from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from src.models.boothAllo_model import BoothAlloModel 


boothAllo_bp = Blueprint('boothAllo', __name__)



@boothAllo_bp.after_request
def add_no_cache_headers(response):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response

@boothAllo_bp.route('/booth', methods=['GET', 'POST'])
def booth_page():
    try:
        # Retrieve the organiser ID from the session
        organiser_id = session.get('organiser_id')
        if not organiser_id:
            flash('You need to log first.', 'warning')
            return redirect(url_for('login.login'))

        # Fetch all events for the dropdown based on the organiser ID
        events = BoothAlloModel.get_events_for_booth(organiser_id)

        # Initialize variables for selected event and booth lists
        selected_event_id = None
        event_details = None
        unassigned_booths = []
        assigned_booths = []

        # Handle form submission for event selection
        if request.method == 'POST':
            selected_event_id = request.form.get('eventSelect')
            if selected_event_id:
                # Fetch event details based on the selected event
                event_details = BoothAlloModel.get_event_details(selected_event_id)

                # Fetch unassigned booths for the selected event
                unassigned_booths = BoothAlloModel.get_unassigned_booths(selected_event_id)

                # Fetch assigned booths for the selected event (you can adjust this as per your needs)
                assigned_booths = BoothAlloModel.get_assigned_booths(selected_event_id)

        return render_template(
            'OrgAlloBooth.html',
            events=events,
            event_details=event_details,
            unassigned_booths=unassigned_booths,
            assigned_booths=assigned_booths,
            selected_event_id=selected_event_id
        )

    except Exception as e:
        print(f"Error in booth_page: {e}")
        flash('An error occurred while loading the page.', 'danger')
        return redirect(url_for('home'))
    



@boothAllo_bp.route('/assign_booths', methods=['POST'])
def assign_booths():
    try:
        data = request.get_json()
        booths = data.get('booths')
        event_id = data.get('eventID')

        event_details = BoothAlloModel.get_event_details(event_id)

        if not event_details:
            return jsonify({'success': False, 'message': 'Event not found.'}), 404

        rental_start_date = event_details['EventStartDate']
        rental_end_date = event_details['EventEndDate']

        # The rental_days calculation is now handled in the model
        # We just pass the dates and let the model calculate the days
        for exhibitor_id in booths:
            BoothAlloModel.assign_booth_to_event(
                exhibitor_id, 
                event_id, 
                rental_start_date, 
                rental_end_date, 
                None  # rental_days will be calculated in the model
            )

        return jsonify({'success': True}), 200

    except Exception as e:
        print(f"Error assigning booths: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500



@boothAllo_bp.route('/remove_booth_allocation', methods=['GET', 'POST'])
def remove_booth_allo_page():
    try:
        # Retrieve the organiser ID from the session
        organiser_id = session.get('organiser_id')
        if not organiser_id:
            flash('You need to log in first.', 'warning')
            return redirect(url_for('login.login'))

        # Fetch all events for the dropdown based on the organiser ID
        events = BoothAlloModel.get_events_for_booth(organiser_id)

        # Initialize variables for selected event and assigned booths
        selected_event_id = None
        event_details = None
        assigned_booths = []

        # Handle form submission for event selection
        if request.method == 'POST':
            selected_event_id = request.form.get('eventSelect')
            if selected_event_id:
                # Fetch event details based on the selected event
                event_details = BoothAlloModel.get_event_details(selected_event_id)

                # Fetch assigned booths for the selected event
                assigned_booths = BoothAlloModel.get_assigned_booths(selected_event_id)

            

        return render_template(
            'RemoveAlloBooth.html',
            events=events,
            event_details=event_details,
            assigned_booths=assigned_booths,
            selected_event_id=selected_event_id
        )

    except Exception as e:
        print(f"Error in remove_booth_allo_page: {e}")
        flash('An error occurred while loading the page.', 'danger')
        return redirect(url_for('home'))
    

@boothAllo_bp.route('/remove_booths', methods=['POST'])
def remove_booths():
    try:
        data = request.get_json()
        booth_ids = data.get('boothIds', [])
        event_id = data.get('eventId')

        # Log data to confirm what's received
        print(f"Received booth_ids: {booth_ids}, event_id: {event_id}")

        # Validate that there are booth IDs and an event ID provided
        if not booth_ids or not event_id:
            return jsonify({'success': False, 'message': 'Missing booth IDs or event ID'}), 400

        # Call the model method to remove the booths from the event
        result = BoothAlloModel.remove_multiple_booth_assignments(booth_ids, event_id)

        if result:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Failed to remove booths'}), 500
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500



@boothAllo_bp.route('/booth_map_planning', methods=['GET', 'POST'])
def booth_map_planning():
    try:
        # Retrieve the organiser ID from the session
        organiser_id = session.get('organiser_id')
        if not organiser_id:
            flash('You need to log in first.', 'warning')
            return redirect(url_for('login.login'))

        # Fetch events for the dropdown based on the organiser ID
        events = BoothAlloModel.get_events_for_booth(organiser_id)

        # Initialize selected_event_id for the form submission
        selected_event_id = None
        booths = []  # Empty list to store booth information for the selected event

        # Handle form submission for event selection
        if request.method == 'POST':
            selected_event_id = request.form.get('eventSelect')

            if selected_event_id:
                # Fetch the booths for the selected event
                booths = BoothAlloModel.get_booths_for_event(selected_event_id)

        return render_template(
            'BoothPlaceSelection.html',
            events=events,
            selected_event_id=selected_event_id,
            booths=booths  # Pass the booth data to the template
        )

    except Exception as e:
        print(f"Error in booth_map_planning: {e}")
        flash('An error occurred while loading the page.', 'danger')
        return redirect(url_for('home'))