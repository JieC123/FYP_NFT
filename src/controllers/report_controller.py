from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from src.models.report_model import ReportModel

report_bp = Blueprint('report', __name__)

class ReportController:
    @report_bp.after_request
    def add_no_cache_headers(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    @staticmethod
    @report_bp.route('/StaffAllocationReport', methods=['GET', 'POST'])
    def staffAllocation_report():
        try:
            if 'organiser_id' not in session:
                flash('You need to login first', 'error')
                return redirect(url_for('login.login'))

            organiser_id = session['organiser_id']
            events = ReportModel.get_events_for_report(organiser_id)
            selected_event_id = None
            event_details = None
            staff_records = []
            total_staff_cost = 0

            if request.method == 'POST':
                selected_event_id = request.form.get('eventSelect')
                if selected_event_id:
                    event_details = ReportModel.get_event_details(selected_event_id)
                    staff_records = ReportModel.get_staff_allocation(selected_event_id)
                    total_staff_cost = sum(record['total_cost'] for record in staff_records)

            return render_template(
                'StaffAllocationReport.html',
                events=events,
                selected_event_id=selected_event_id,
                event_details=event_details,
                staff_records=staff_records,
                total_staff_cost=total_staff_cost
            )

        except Exception as e:
            print(f"Error in staffAllocation_report: {e}")
            flash('An error occurred while loading the report', 'error')
            return redirect(url_for('report.staffAllocation_report'))

    @staticmethod
    @report_bp.route('/ExhibitorAllocationReport', methods=['GET', 'POST'])
    def exhibitorAllocation_report():
        try:
            if 'organiser_id' not in session:
                flash('You need to login first', 'error')
                return redirect(url_for('login.login'))

            organiser_id = session['organiser_id']
            events = ReportModel.get_events_for_report(organiser_id)
            selected_event_id = None
            event_details = None
            exhibitor_records = []

            if request.method == 'POST':
                selected_event_id = request.form.get('eventSelect')
                if selected_event_id:
                    event_details = ReportModel.get_event_details(selected_event_id)
                    exhibitor_records = ReportModel.get_exhibitor_allocation(selected_event_id)

            return render_template(
                'ExhibitorAllocationReport.html',
                events=events,
                selected_event_id=selected_event_id,
                event_details=event_details,
                exhibitor_records=exhibitor_records
            )

        except Exception as e:
            print(f"Error in exhibitorAllocation_report: {e}")
            flash('An error occurred while loading the report', 'error')
            return redirect(url_for('report.exhibitorAllocation_report'))

    @staticmethod
    @report_bp.route('/SponsorshipAllocationReport', methods=['GET', 'POST'])
    def sponsorshipAllocation_report():
        try:
            if 'organiser_id' not in session:
                flash('You need to login first', 'error')
                return redirect(url_for('login.login'))

            organiser_id = session['organiser_id']
            events = ReportModel.get_events_for_report(organiser_id)
            selected_event_id = None
            event_details = None
            sponsorship_records = []

            if request.method == 'POST':
                selected_event_id = request.form.get('eventSelect')
                if selected_event_id:
                    event_details = ReportModel.get_event_details(selected_event_id)
                    sponsorship_records = ReportModel.get_sponsorship_allocation(selected_event_id)

            return render_template(
                'SponsorshipAllocationReport.html',
                events=events,
                selected_event_id=selected_event_id,
                event_details=event_details,
                sponsorship_records=sponsorship_records
            )

        except Exception as e:
            print(f"Error in sponsorshipAllocation_report: {e}")
            flash('An error occurred while loading the report', 'error')
            return redirect(url_for('report.sponsorshipAllocation_report'))

    @staticmethod
    @report_bp.route('/ParticipantAllocationReport', methods=['GET', 'POST'])
    def participantAllocation_report():
        try:
            if 'organiser_id' not in session:
                flash('You need to login first', 'error')
                return redirect(url_for('login.login'))

            organiser_id = session['organiser_id']
            events = ReportModel.get_events_for_report(organiser_id)
            selected_event_id = None
            event_details = None
            participant_records = []

            if request.method == 'POST':
                selected_event_id = request.form.get('eventSelect')
                if selected_event_id:
                    event_details = ReportModel.get_event_details(selected_event_id)
                    participant_records = ReportModel.get_participant_allocation(selected_event_id)

            return render_template(
                'ParticipantAllocationReport.html',
                events=events,
                selected_event_id=selected_event_id,
                event_details=event_details,
                participant_records=participant_records
            )

        except Exception as e:
            print(f"Error in participantAllocation_report: {e}")
            flash('An error occurred while loading the report', 'error')
            return redirect(url_for('report.participantAllocation_report'))

    @staticmethod
    @report_bp.route('/EventSummaryReport', methods=['GET', 'POST'])
    def event_summary_report():
        try:
            if 'organiser_id' not in session:
                flash('You need to login first', 'error')
                return redirect(url_for('login.login'))

            organiser_id = session['organiser_id']
            from datetime import datetime
            today = datetime.now().strftime('%Y-%m-%d')

            # Initialize variables
            events = None
            total_events = 0
            
            # Only fetch events if it's a POST request (Generate button clicked)
            if request.method == 'POST':
                start_date = request.form.get('startDate')
                end_date = request.form.get('endDate')
                if start_date and end_date:
                    events = ReportModel.get_event_summary(start_date, end_date, organiser_id)
                    total_events = len(events) if events else 0

            return render_template(
                'EventSummaryReport.html',
                events=events,
                total_events=total_events,
                default_date=today
            )

        except Exception as e:
            print(f"Error in event_summary_report: {e}")
            flash('An error occurred while loading the report', 'error')
            return redirect(url_for('report.event_summary_report'))
