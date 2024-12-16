from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from src.models.sponsorshipAllo_model import SponsorshipAlloModel  

sponsorshipAllo_bp = Blueprint('sponsorshipAllo', __name__)


@sponsorshipAllo_bp.after_request
def add_no_cache_headers(response):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response

@sponsorshipAllo_bp.route('/sponsorship', methods=['GET', 'POST'])
def sponsorship_page():
        
    
    try:
        # Retrieve the organiser ID from the session
        organiser_id = session.get('organiser_id')
        if not organiser_id:
            flash('You need to login first.', 'warning')
            return redirect(url_for('login.login'))

        # Fetch all events for the dropdown based on the organiser ID
        events = SponsorshipAlloModel.get_events_for_sponsorship(organiser_id)

        # Initialize variables for selected event and sponsorship lists
        selected_event_id = None
        event_details = None
        unassigned_sponsorships = []
        assigned_sponsorships = []

        # Handle form submission for event selection
        if request.method == 'POST':
            selected_event_id = request.form.get('eventSelect')
            if selected_event_id:
                # Fetch event details based on the selected event
                event_details = SponsorshipAlloModel.get_event_details(selected_event_id)

                # Fetch unassigned sponsorships for the selected event
                unassigned_sponsorships = SponsorshipAlloModel.get_unassigned_sponsorships(selected_event_id)

                # Fetch assigned sponsorships for the selected event
                assigned_sponsorships = SponsorshipAlloModel.get_assigned_sponsorships(selected_event_id)

        return render_template(
            'OrgAlloSponsorship.html',
            events=events,
            event_details=event_details,
            unassigned_sponsorships=unassigned_sponsorships,
            assigned_sponsorships=assigned_sponsorships,
            selected_event_id=selected_event_id
        )

    except Exception as e:
        print(f"Error in sponsorship_page: {e}")
        flash('An error occurred while loading the page.', 'danger')
        return redirect(url_for('home'))



@sponsorshipAllo_bp.route('/assign_sponsorships', methods=['POST'])
def assign_sponsorships():
    try:
        # Get data from the POST request
        data = request.get_json()
        sponsorships = data.get('sponsorships')
        event_id = data.get('eventID')

        # Loop through the selected sponsorships and update the database
        for sponsorship_id in sponsorships:
            # Update the SponsorshipAssignment table with the new event assignment
            SponsorshipAlloModel.assign_sponsorship_to_event(sponsorship_id, event_id)

        # Return success response
        return jsonify({'success': True}), 200

    except Exception as e:
        print(f"Error assigning sponsorships: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    


@sponsorshipAllo_bp.route('/remove_allo_sponsorship', methods=['GET', 'POST'])
def remove_allo_page():
    try:
        organiser_id = session.get('organiser_id')
        if not organiser_id:
            flash('You need to log in first.', 'warning')
            return redirect(url_for('login.login'))

        # Fetch all events for the organiser
        events = SponsorshipAlloModel.get_events_for_sponsorship(organiser_id)

        selected_event_id = None
        event_details = None
        assigned_sponsorships = []

        if request.method == 'POST':
            # Get the selected event ID from the form
            selected_event_id = request.form.get('eventSelect')
            
            # Fetch the event details if an event is selected
            if selected_event_id:
                event_details = SponsorshipAlloModel.get_event_details(selected_event_id)
                assigned_sponsorships = SponsorshipAlloModel.get_assigned_sponsorships(selected_event_id)

                # Remove selected sponsorships if any are chosen
                selected_sponsorships = request.form.getlist('selected_sponsorships')
                if selected_sponsorships:
                    SponsorshipAlloModel.remove_multiple_sponsorship_assignments(selected_sponsorships, selected_event_id)
                    flash('Selected sponsorship(s) have been removed.', 'success')
                    return redirect(url_for('sponsorshipAllo.remove_allo_page'))

        return render_template(
            'RemoveAlloSponsorship.html', 
            events=events,
            event_details=event_details,
            assigned_sponsorships=assigned_sponsorships,
            selected_event_id=selected_event_id
        )

    except Exception as e:
        flash(f"An error occurred: {e}", 'danger')
        return redirect(url_for('home'))

@sponsorshipAllo_bp.route('/remove_sponsorships', methods=['POST'])
def remove_sponsorships():
    try:
        data = request.get_json()
        sponsorship_ids = data.get('sponsorshipIds', [])
        event_id = data.get('eventId')

        # Validate that there are sponsorships to delete and an event id is provided
        if not sponsorship_ids or not event_id:
            return jsonify({'success': False, 'message': 'Missing sponsorship IDs or event ID'}), 400

        # Call the model method to remove the sponsorships from the event
        result = SponsorshipAlloModel.remove_multiple_sponsorship_assignments(sponsorship_ids, event_id)

        if result:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Failed to remove sponsorships'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@sponsorshipAllo_bp.route('/refresh_assigned_sponsorships', methods=['GET'])
def refresh_assigned_sponsorships():
    try:
        event_id = request.args.get('event_id')
        
        if not event_id:
            return jsonify({'error': 'No event selected'}), 400

        assigned_sponsorships = SponsorshipAlloModel.get_assigned_sponsorships(event_id)
        event_details = SponsorshipAlloModel.get_event_details(event_id)
        
        return render_template(
            'OrgAlloSponsorship.html',
            assigned_sponsorships=assigned_sponsorships,
            event_details=event_details,
            selected_event_id=event_id,
            events=SponsorshipAlloModel.get_events_for_sponsorship(session.get('organiser_id')),
            show_assigned_table=True
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@sponsorshipAllo_bp.route('/refresh_unassigned_sponsorships', methods=['GET'])
def refresh_unassigned_sponsorships():
    try:
        event_id = request.args.get('event_id')
        
        if not event_id:
            return jsonify({'error': 'No event selected'}), 400

        unassigned_sponsorships = SponsorshipAlloModel.get_unassigned_sponsorships(event_id)
        event_details = SponsorshipAlloModel.get_event_details(event_id)
        
        return render_template(
            'OrgAlloSponsorship.html',
            unassigned_sponsorships=unassigned_sponsorships,
            event_details=event_details,
            selected_event_id=event_id,
            events=SponsorshipAlloModel.get_events_for_sponsorship(session.get('organiser_id')),
            show_unassigned_table=True
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500