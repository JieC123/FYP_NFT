from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from src.models.budget_simulate_model import BudgetSimulateModel

budget_simulate_bp = Blueprint('budget_simulate', __name__)
model = BudgetSimulateModel()

# Add cache control decorator
@budget_simulate_bp.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@budget_simulate_bp.route('/BudgetSimulation', methods=['GET', 'POST'])
def budget_simulation():
    # Check for session
    organiser_id = session.get('organiser_id')
    if not organiser_id:
        flash('You need to log in first.', 'warning')
        return redirect(url_for('login.login'))
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            
            # Get all form data
            total_food_cost = float(data.get('total_food_cost', 0))
            marketing_type = data.get('marketing_cost', 'None')
            event_type = data.get('event_type')
            event_duration = int(data.get('event_duration', 1))
            venue_cost = float(data.get('venue_cost', 0))
            miscellaneous_cost = float(data.get('miscellaneous_cost', 0))

            # Get staff requirements
            staff_requirements = data.get('staff_requirements', {})

            # Get budget prediction with all costs
            budget_result = model.predict_budget(
                total_food_cost=total_food_cost,
                marketing_option=marketing_type,
                staff_requirements=staff_requirements,
                event_type=event_type,
                event_duration=event_duration,
                venue_cost=venue_cost,
                miscellaneous_cost=miscellaneous_cost
            )

            return jsonify(budget_result)

        except Exception as e:
            print(f"Error during budget simulation: {e}")
            return jsonify({'error': str(e)}), 500

    return render_template('BudgetSimulation.html')

@budget_simulate_bp.route('/fetch-staff-rate', methods=['POST'])
def fetch_staff_rate():
    try:
        role = request.json.get('role')
        event_type = request.json.get('event_type')
        experience_level = request.json.get('experience_level', 'Mid')
        daily_rate = model.predict_staff_cost(role, event_type, experience_level)
        return jsonify({'daily_rate': daily_rate})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@budget_simulate_bp.route('/fetch-marketing-costs', methods=['GET'])
def fetch_marketing_costs():
    try:
        tv_cost = model.predict_cost(model.tv_model)
        radio_cost = model.predict_cost(model.radio_model)
        newspaper_cost = model.predict_cost(model.newspaper_model)

        # Calculate combined costs
        tv_radio_cost = tv_cost + radio_cost
        tv_newspaper_cost = tv_cost + newspaper_cost
        radio_newspaper_cost = radio_cost + newspaper_cost
        all_costs = tv_cost + radio_cost + newspaper_cost

        return jsonify({
            'tv_cost': tv_cost,
            'radio_cost': radio_cost,
            'newspaper_cost': newspaper_cost,
            'tv_radio_cost': tv_radio_cost,
            'tv_newspaper_cost': tv_newspaper_cost,
            'radio_newspaper_cost': radio_newspaper_cost,
            'all_costs': all_costs
        })
    except Exception as e:
        print(f"Error in fetch-marketing-costs: {e}")
        return jsonify({'error': str(e)}), 500

@budget_simulate_bp.route('/predict-venue-cost', methods=['POST'])
def predict_venue_cost():
    try:
        data = request.json
        event_type = data.get('event_type')
        venue_type = data.get('venue_type')
        expected_attendance = int(data.get('expected_attendance'))
        duration = int(data.get('duration', 1))

        if not all([event_type, venue_type, expected_attendance]):
            return jsonify({'error': 'Missing required parameters'}), 400

        result = model.predict_venue_cost(
            event_type=event_type,
            venue_type=venue_type,
            expected_attendance=expected_attendance,
            duration=duration
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@budget_simulate_bp.route('/fetch-venue-options', methods=['GET'])
def fetch_venue_options():
    try:
        venue_options = model.get_venue_options()
        return jsonify({'venues': venue_options})
    except Exception as e:
        print(f"Error fetching venue options: {e}")
        return jsonify({'error': str(e)}), 500