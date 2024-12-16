from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime
from src.models.eventStaffAllo_model import StaffAlloModel

staffAllo_bp = Blueprint('staffAllo', __name__)



@staffAllo_bp.after_request
def add_no_cache_headers(response):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response

@staffAllo_bp.route('/staffAllocation', methods=['GET', 'POST'])
def staffAllocation_page():
    try:
        organiser_id = session.get('organiser_id')
        if not organiser_id:
            flash('You need to login first.', 'warning')
            return redirect(url_for('login.login'))

        events = StaffAlloModel.get_events_for_staff(organiser_id)
        selected_event_id = None
        event_details = None
        unassigned_staff = []
        assigned_staff = []

        if request.method == 'POST':
            selected_event_id = request.form.get('eventSelect')
            if selected_event_id:
                event_details = StaffAlloModel.get_event_details(selected_event_id)
                unassigned_staff = StaffAlloModel.get_unassigned_staff(selected_event_id)
                assigned_staff = StaffAlloModel.get_assigned_staff(selected_event_id)

        return render_template(
            'OrgAlloStaff.html',
            events=events,
            event_details=event_details,
            unassigned_staff=unassigned_staff,
            assigned_staff=assigned_staff,
            selected_event_id=selected_event_id
        )

    except Exception as e:
        print(f"Error in staffAllocation_page: {e}")
        flash('An error occurred while loading the page.', 'danger')
        return redirect(url_for('home'))


@staffAllo_bp.route('/assign_staff', methods=['POST'])
def assign_staff():
    try:
        # Get data from the POST request
        data = request.get_json()
        staff_data = data.get('staffData')  # Expecting an array of staff data with job start and end periods
        event_id = data.get('eventID')

        # Check if staff data is provided
        if not staff_data or not isinstance(staff_data, list):
            return jsonify({'success': False, 'message': 'No staff data provided.'}), 400

        # Fetch event details, including start and end dates
        event_details = StaffAlloModel.get_event_details(event_id)

        # Check if event details were retrieved successfully
        if not event_details:
            return jsonify({'success': False, 'message': 'Event not found.'}), 404

        # Use the event details to get the start and end dates
        event_start_date = event_details['EventStartDate']
        event_end_date = event_details['EventEndDate']

        # Loop through the selected staff data and assign them to the event
        for staff in staff_data:
            staff_id = staff['staffId']
            job_start_period = staff['jobStartPeriod']
            job_end_period = staff['jobEndPeriod']

            try:
                # Assuming the inputs are already datetime objects, no need to parse them again.
                # If they are strings, convert them to datetime objects like below:
                if isinstance(job_start_period, str):
                    job_start_period = datetime.strptime(job_start_period, '%Y-%m-%d %H:%M:%S')
                if isinstance(job_end_period, str):
                    job_end_period = datetime.strptime(job_end_period, '%Y-%m-%d %H:%M:%S')

                if isinstance(event_start_date, str):
                    event_start_date = datetime.strptime(event_start_date, '%Y-%m-%d %H:%M:%S')
                if isinstance(event_end_date, str):
                    event_end_date = datetime.strptime(event_end_date, '%Y-%m-%d %H:%M:%S')

            except ValueError as e:
                return jsonify({'success': False, 'message': f'Invalid date format for staff {staff_id}. Expected YYYY-MM-DD HH:MM:SS.'}), 400

            # Validate event start and end date against job start and end period including time
            if not (job_start_period <= event_start_date and job_end_period >= event_end_date):
                return jsonify({'success': False, 'message': f'Staff {staff_id} job period does not fully cover the event period, including time.'}), 400

            # Assign staff to event
            success = StaffAlloModel.assign_staff_to_event(
                staff_id, event_id, job_start_period, job_end_period, event_start_date, event_end_date
            )

            # If assignment failed (overlap or other issue)
            if not success:
                return jsonify({'success': False, 'message': f'Failed to assign staff, {staff_id}. The staff may already be assigned to another event during the same period.'}), 400

        return jsonify({'success': True, 'message': 'Staff successfully assigned to event.'}), 200

    except Exception as e:
        print(f"Error assigning staff: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500



@staffAllo_bp.route('/staffAllocationRemoval', methods=['GET', 'POST'])
def staffAllocationRemoval_page():
    try:
        # Ensure the organiser is logged in
        organiser_id = session.get('organiser_id')
        if not organiser_id:
            flash('You need to login first.', 'warning')
            return redirect(url_for('login.login'))

        # Fetch events for the organiser
        events = StaffAlloModel.get_events_for_staff(organiser_id)

        selected_event_id = None
        assigned_staff = []
        event_details = None

        if request.method == 'POST':
            # Get the selected event ID from the form
            selected_event_id = request.form.get('eventSelect')

            # Fetch assigned staff for the selected event
            if selected_event_id:
                assigned_staff = StaffAlloModel.get_assigned_staff(selected_event_id)
                event_details = StaffAlloModel.get_event_details(selected_event_id)

                # Handle removal of selected staff if the form contains staff to be removed
                selected_staff = request.form.getlist('selected_staff')
                if selected_staff:
                    StaffAlloModel.remove_multiple_staff_assignments(selected_staff, selected_event_id)
                    flash('Selected staff have been removed from the event.', 'success')
                    return redirect(url_for('staffAllo.staffAllocationRemoval_page'))

        return render_template(
            'RemoveAlloStaff.html',
            events=events,
            assigned_staff=assigned_staff,
            selected_event_id=selected_event_id,
            event_details=event_details
        )

    except Exception as e:
        flash(f"An error occurred: {e}", 'danger')
        return redirect(url_for('home'))
    


@staffAllo_bp.route('/remove_staff_assignments', methods=['POST'])
def remove_staff_assignments():
        try:
            data = request.get_json()
            selected_staff_ids = data.get('staffIds', [])
            event_id = data.get('eventId')

            # Validate that there are selected staff IDs and an event ID is provided
            if not selected_staff_ids or not event_id:
                return jsonify({'success': False, 'message': 'Missing staff IDs or event ID'}), 400

            # Call the model method to remove the staff assignments from the event
            result = StaffAlloModel.remove_multiple_staff_assignments(selected_staff_ids, event_id)

            if result:
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'message': 'Failed to remove staff assignments'}), 500
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500