from flask import Blueprint, render_template, redirect, url_for, session, request, flash
from src.models.track_involvement_model import TrackInvolvementModel

track_involvement_bp = Blueprint('track_involvement', __name__)




@track_involvement_bp.route('/set_event_id/<string:event_id>', methods=['GET'])
def set_event_id(event_id):
    # Store the event_id in the session
    session['event_id'] = event_id
    return redirect(url_for('track_involvement.view_allo_staff'))




@track_involvement_bp.route('/view_allo_staff', methods=['GET'])
def view_allo_staff():
    organiser_id = session.get('organiser_id')
    if not organiser_id:
        flash('You need to log in first.', 'danger')
        return redirect(url_for('login.login'))

    event_id = session.get('event_id')
    if not event_id:
        return redirect(url_for('event.index'))

    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 5  # Number of items per page

    # Fetch event name
    event_name = TrackInvolvementModel.get_event_name(event_id)
    if not event_name:
        return render_template('ViewAlloStaff.html', 
                             staff=[], 
                             event_id=event_id, 
                             event_name=None,
                             error=request.args.get('error'),
                             success=request.args.get('success'),
                             current_page=page,
                             total_pages=1)

    # Get filter parameters
    roles = request.args.get('roles', '').split(',') if request.args.get('roles') else None
    statuses = request.args.get('statuses', '').split(',') if request.args.get('statuses') else None

    # Step 1: Fetch assigned staff IDs for the event
    staff_ids = TrackInvolvementModel.getStaffDetail(event_id)
    if not staff_ids:
        return render_template('ViewAlloStaff.html', 
                             staff=[], 
                             event_id=event_id, 
                             event_name=event_name,
                             error=request.args.get('error'),
                             success=request.args.get('success'),
                             current_page=page,
                             total_pages=1)

    # Step 2: Fetch filtered staff information
    staff_details = TrackInvolvementModel.match_staff(staff_ids, roles, statuses)
    
    # Calculate pagination
    total_items = len(staff_details)
    total_pages = (total_items + per_page - 1) // per_page  # Ceiling division
    
    # Ensure page is within valid range
    page = min(max(page, 1), total_pages)
    
    # Slice the results for the current page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_staff = staff_details[start_idx:end_idx]

    return render_template('ViewAlloStaff.html', 
                         staff=paginated_staff, 
                         event_id=event_id, 
                         event_name=event_name,
                         error=request.args.get('error'),
                         success=request.args.get('success'),
                         current_page=page,
                         total_pages=max(total_pages, 1))


@track_involvement_bp.route('/search_allocated_staff', methods=['GET'])
def search_allocated_staff():
    query = request.args.get('query', '').strip()
    event_id = session.get('event_id')
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 5  # Number of items per page
    
    if not event_id:
        return redirect(url_for('event.index'))
    
    # Fetch event name
    event_name = TrackInvolvementModel.get_event_name(event_id)
    if not event_name:
        return render_template('ViewAlloStaff.html', 
                             staff=[], 
                             event_id=event_id, 
                             event_name=None,
                             current_page=page,
                             total_pages=1)

    # Get staff details based on search or all staff
    if not query:
        staff_ids = TrackInvolvementModel.getStaffDetail(event_id)
        if not staff_ids:
            return render_template('ViewAlloStaff.html', 
                                 staff=[], 
                                 event_id=event_id, 
                                 event_name=event_name,
                                 current_page=page,
                                 total_pages=1)
        staff_details = TrackInvolvementModel.match_staff(staff_ids)
    else:
        staff_details = TrackInvolvementModel.search_allocated_staff(query, event_id)

    # Calculate pagination
    total_items = len(staff_details)
    total_pages = (total_items + per_page - 1) // per_page
    
    # Ensure page is within valid range
    page = min(max(page, 1), total_pages)
    
    # Slice the results for the current page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_staff = staff_details[start_idx:end_idx]

    return render_template('ViewAlloStaff.html', 
                         staff=paginated_staff, 
                         event_id=event_id, 
                         event_name=event_name,
                         current_page=page,
                         total_pages=max(total_pages, 1))



@track_involvement_bp.route('/view_the_allo', methods=['GET'])
def view_allo_booth():
    event_id = session.get('event_id')
    if not event_id:
        return redirect(url_for('event.index'))
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 5  # Number of items per page
    
    # Fetch event name and booth details
    event_name, booth_details = TrackInvolvementModel.get_booth_details(event_id)
    
    if not booth_details:
        return render_template('ViewAlloBooth.html', 
                             booths=[], 
                             event_id=event_id, 
                             event_name=event_name,
                             current_page=page,
                             total_pages=1)

    # Calculate pagination
    total_items = len(booth_details)
    total_pages = (total_items + per_page - 1) // per_page
    
    # Ensure page is within valid range
    page = min(max(page, 1), total_pages)
    
    # Slice the results for the current page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_booths = booth_details[start_idx:end_idx]
    
    return render_template('ViewAlloBooth.html', 
                         booths=paginated_booths, 
                         event_name=event_name, 
                         event_id=event_id,
                         current_page=page,
                         total_pages=max(total_pages, 1))


@track_involvement_bp.route('/search_allocated_booth', methods=['GET'])
def search_allocated_booth():
    query = request.args.get('query', '').strip()
    event_id = session.get('event_id')
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 5  # Number of items per page
    
    if not event_id:
        return redirect(url_for('event.index'))
    
    # Fetch event name
    event_name = TrackInvolvementModel.get_event_name(event_id)
    if not event_name:
        return render_template('ViewAlloBooth.html', 
                             booths=[], 
                             event_id=event_id, 
                             event_name=None,
                             current_page=page,
                             total_pages=1)

    # Get booth details based on search
    if not query:
        event_name, booth_details = TrackInvolvementModel.get_booth_details(event_id)
    else:
        booth_details = TrackInvolvementModel.search_allocated_booth(query, event_id)

    # Calculate pagination
    total_items = len(booth_details)
    total_pages = (total_items + per_page - 1) // per_page
    
    # Ensure page is within valid range
    page = min(max(page, 1), total_pages)
    
    # Slice the results for the current page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_booths = booth_details[start_idx:end_idx]

    return render_template('ViewAlloBooth.html', 
                         booths=paginated_booths, 
                         event_id=event_id, 
                         event_name=event_name,
                         current_page=page,
                         total_pages=max(total_pages, 1))




@track_involvement_bp.route('/view_the_allo3', methods=['GET'])
def view_allo_sponsorship():
    event_id = session.get('event_id')
    if not event_id:
        return redirect(url_for('event.index'))

    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 5  # Number of items per page

    # Fetch event name and sponsorship details
    event_name, sponsorship_details = TrackInvolvementModel.get_sponsorship_details(event_id)
    
    if not sponsorship_details:
        return render_template('ViewAlloSponsor.html', 
                             sponsors=[], 
                             event_name=event_name, 
                             event_id=event_id,
                             current_page=page,
                             total_pages=1)

    # Calculate pagination
    total_items = len(sponsorship_details)
    total_pages = (total_items + per_page - 1) // per_page
    
    # Ensure page is within valid range
    page = min(max(page, 1), total_pages)
    
    # Slice the results for the current page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_sponsors = sponsorship_details[start_idx:end_idx]

    return render_template('ViewAlloSponsor.html', 
                         sponsors=paginated_sponsors, 
                         event_name=event_name, 
                         event_id=event_id,
                         current_page=page,
                         total_pages=max(total_pages, 1))


@track_involvement_bp.route('/search_allocated_sponsorship', methods=['GET'])
def search_allocated_sponsorship():
    query = request.args.get('query', '').strip()
    event_id = session.get('event_id')
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 5  # Number of items per page
    
    if not event_id:
        return redirect(url_for('event.index'))
    
    # Fetch event name
    event_name = TrackInvolvementModel.get_event_name(event_id)
    if not event_name:
        return render_template('ViewAlloSponsor.html', 
                             sponsors=[], 
                             event_id=event_id, 
                             event_name=None,
                             current_page=page,
                             total_pages=1)

    # Get sponsor details based on search
    if not query:
        event_name, sponsor_details = TrackInvolvementModel.get_sponsorship_details(event_id)
    else:
        sponsor_details = TrackInvolvementModel.search_allocated_sponsorship(query, event_id)

    # Calculate pagination
    total_items = len(sponsor_details)
    total_pages = (total_items + per_page - 1) // per_page
    
    # Ensure page is within valid range
    page = min(max(page, 1), total_pages)
    
    # Slice the results for the current page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_sponsors = sponsor_details[start_idx:end_idx]

    return render_template('ViewAlloSponsor.html', 
                         sponsors=paginated_sponsors, 
                         event_id=event_id, 
                         event_name=event_name,
                         current_page=page,
                         total_pages=max(total_pages, 1))


@track_involvement_bp.route('/viewTheAllo2', methods=['GET'])
def view_allo_participant():
    event_id = session.get('event_id')
    if not event_id:
        return redirect(url_for('event.index'))

    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 5  # Number of items per page

    # Fetch event name and participant details
    event_name, participant_details = TrackInvolvementModel.get_participant_details(event_id)
    
    if not participant_details:
        return render_template('ViewAlloParticipant.html', 
                            participants=[], 
                            event_name=event_name, 
                            event_id=event_id,
                            current_page=page,
                            total_pages=1)

    # Calculate pagination
    total_items = len(participant_details)
    total_pages = (total_items + per_page - 1) // per_page
    
    # Ensure page is within valid range
    page = min(max(page, 1), total_pages)
    
    # Slice the results for the current page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_participants = participant_details[start_idx:end_idx]

    return render_template('ViewAlloParticipant.html', 
                         participants=paginated_participants, 
                         event_name=event_name, 
                         event_id=event_id,
                         current_page=page,
                         total_pages=max(total_pages, 1))

@track_involvement_bp.route('/search_allocated_participant', methods=['GET'])
def search_allocated_participant():
    query = request.args.get('query', '').strip()
    event_id = session.get('event_id')
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 5  # Number of items per page
    
    if not event_id:
        return redirect(url_for('event.index'))
    
    # Fetch event name
    event_name = TrackInvolvementModel.get_event_name(event_id)
    if not event_name:
        return render_template('ViewAlloParticipant.html', 
                            participants=[], 
                            event_id=event_id, 
                            event_name=None,
                            current_page=page,
                            total_pages=1)

    # Get participant details based on search
    if not query:
        event_name, participant_details = TrackInvolvementModel.get_participant_details(event_id)
    else:
        participant_details = TrackInvolvementModel.search_allocated_participant(query, event_id)

    # Calculate pagination
    total_items = len(participant_details)
    total_pages = (total_items + per_page - 1) // per_page
    
    # Ensure page is within valid range
    page = min(max(page, 1), total_pages)
    
    # Slice the results for the current page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_participants = participant_details[start_idx:end_idx]

    return render_template('ViewAlloParticipant.html', 
                         participants=paginated_participants, 
                         event_id=event_id, 
                         event_name=event_name,
                         current_page=page,
                         total_pages=max(total_pages, 1))


@track_involvement_bp.route('/filter_allocated_sponsorship', methods=['GET'])
def filter_allocated_sponsorship():
    event_id = session.get('event_id')
    if not event_id:
        return redirect(url_for('event.index'))

    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 5  # Number of items per page

    # Get filter parameters
    packages = request.args.get('packages', '').split(',') if request.args.get('packages') else None
    schedules = request.args.get('schedules', '').split(',') if request.args.get('schedules') else None
    statuses = request.args.get('statuses', '').split(',') if request.args.get('statuses') else None

    # Get filtered sponsorship details
    event_name, sponsorship_details = TrackInvolvementModel.get_filtered_sponsorship_details(
        event_id, packages, schedules, statuses)
    
    if not sponsorship_details:
        return render_template('ViewAlloSponsor.html', 
                            sponsors=[], 
                            event_name=event_name, 
                            event_id=event_id,
                            current_page=page,
                            total_pages=1)

    # Calculate pagination
    total_items = len(sponsorship_details)
    total_pages = (total_items + per_page - 1) // per_page
    
    # Ensure page is within valid range
    page = min(max(page, 1), total_pages)
    
    # Slice the results for the current page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_sponsors = sponsorship_details[start_idx:end_idx]

    return render_template('ViewAlloSponsor.html', 
                         sponsors=paginated_sponsors, 
                         event_name=event_name, 
                         event_id=event_id,
                         current_page=page,
                         total_pages=max(total_pages, 1))


@track_involvement_bp.route('/filter_allocated_booth', methods=['GET'])
def filter_allocated_booth():
    event_id = session.get('event_id')
    if not event_id:
        return redirect(url_for('event.index'))

    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 5  # Number of items per page

    # Get filter parameters
    categories = request.args.get('categories', '').split(',') if request.args.get('categories') else None
    sizes = request.args.get('sizes', '').split(',') if request.args.get('sizes') else None
    statuses = request.args.get('statuses', '').split(',') if request.args.get('statuses') else None

    # Get filtered booth details
    event_name, booth_details = TrackInvolvementModel.get_filtered_booth_details(
        event_id, categories, sizes, statuses)
    
    if not booth_details:
        return render_template('ViewAlloBooth.html', 
                             booths=[], 
                             event_name=event_name, 
                             event_id=event_id,
                             current_page=page,
                             total_pages=1)

    # Calculate pagination
    total_items = len(booth_details)
    total_pages = (total_items + per_page - 1) // per_page
    
    # Ensure page is within valid range
    page = min(max(page, 1), total_pages)
    
    # Slice the results for the current page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_booths = booth_details[start_idx:end_idx]
    
    return render_template('ViewAlloBooth.html', 
                         booths=paginated_booths, 
                         event_name=event_name, 
                         event_id=event_id,
                         current_page=page,
                         total_pages=max(total_pages, 1))


class TrackInvolvementController:
    @track_involvement_bp.after_request
    def add_no_cache_headers(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
