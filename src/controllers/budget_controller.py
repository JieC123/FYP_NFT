from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from src.models.budget_model import BudgetModel

budget_bp = Blueprint('budget', __name__)


# Add cache control decorator
@budget_bp.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@budget_bp.route('/OrgEventBudget', methods=['GET', 'POST'])
def budget_page():
    try:
        # Check if user is logged in
        organiser_id = session.get('organiser_id')
        if not organiser_id:
            flash('You need to log in first', 'error')
            return redirect(url_for('login.login'))

        # Get list of events
        events = BudgetModel.get_events_for_budget(organiser_id)
        selected_event_id = None
        selected_event_title = None
        budgets = []

        # Check for selected event from redirect
        selected_event = request.args.get('selected_event')
        
        if request.method == 'POST':
            selected_event_id = request.form.get('eventSelect')
        elif selected_event:  # Handle the redirect case
            selected_event_id = selected_event
            
        if selected_event_id:
            budgets = BudgetModel.get_event_budget_details(selected_event_id)
            # Find the selected event title
            for event in events:
                if event['EventID'] == selected_event_id:
                    selected_event_title = event['EventTitle']
                    break

        return render_template(
            'OrgEventBudget.html',
            events=events,
            selected_event_id=selected_event_id,
            selected_event_title=selected_event_title,
            budgets=budgets
        )

    except Exception as e:
        print(f"Error in budget_page: {e}")
        flash('An error occurred while loading the page', 'error')
        return redirect(url_for('home'))


@budget_bp.route('/edit_budget/<budget_id>', methods=['GET', 'POST'])
def edit_budget(budget_id):
    try:
        if 'organiser_id' not in session:
            flash('You need to log in first', 'error')
            return redirect(url_for('login.login'))

        if request.method == 'POST':
            # Get form data
            budget_amount = request.form.get('budgetAmount', '').strip()
            expenses_amount = request.form.get('expensesAmount', '').strip()
            category = request.form.get('categoryName', '').strip()
            vendor = request.form.get('vendor', '').strip()
            payment_status = request.form.get('paymentStatus', '').strip()
            comments = request.form.get('comments', '').strip()

            # Initialize error messages
            error_messages = []

            # Validate Budget Amount
            try:
                budget_amount = float(budget_amount)
            except ValueError:
                error_messages.append('Budget Amount must be a valid number.')

            # Validate Expenses Amount
            try:
                expenses_amount = float(expenses_amount)
            except ValueError:
                error_messages.append('Expenses Amount must be a valid number.')

            # Validate Category
            if not category:
                error_messages.append('Category is required.')

            # Validate Payment Status
            valid_payment_statuses = ['Paid', 'Pending', 'Canceled']
            if not payment_status or payment_status not in valid_payment_statuses:
                error_messages.append('Invalid Payment Status.')

            # Validate Vendor
            if not vendor:
                error_messages.append('Vendor is required.')

            # Set default comment if empty
            if not comments:
                comments = 'No Comment'

            # If there are validation errors
            if error_messages:
                # Get current budget and categories for re-rendering the form
                budget = BudgetModel.get_budget_by_id(budget_id)
                categories = BudgetModel.get_expense_categories()
                return render_template(
                    'OrgEditBudget.html',
                    budget=budget,
                    categories=categories,
                    error_message=error_messages
                )

            # If validation passes, prepare data for update
            budget_data = {
                'budgetAmount': budget_amount,
                'expensesAmount': expenses_amount,
                'categoryName': category,
                'vendor': vendor,
                'paymentStatus': payment_status,
                'comments': comments
            }

            # Get the event ID before updating
            current_budget = BudgetModel.get_budget_by_id(budget_id)
            event_id = current_budget['EventID']

            # Update budget
            if BudgetModel.update_budget(budget_id, budget_data):
                flash('Budget updated successfully', 'success')
                return redirect(url_for('budget.budget_page', selected_event=event_id))
            else:
                flash('Failed to update budget', 'error')

        # Get budget details for GET request
        budget = BudgetModel.get_budget_by_id(budget_id)
        if not budget:
            flash('Budget not found', 'error')
            return redirect(url_for('budget.budget_page'))

        # Get expense categories
        categories = BudgetModel.get_expense_categories()

        return render_template(
            'OrgEditBudget.html',
            budget=budget,
            categories=categories
        )

    except Exception as e:
        print(f"Error in edit_budget: {e}")
        flash('An error occurred while updating the budget', 'error')
        return redirect(url_for('budget.budget_page'))


@budget_bp.route('/add_budget', methods=['GET', 'POST'])
def add_budget():
    try:
        if 'organiser_id' not in session:
            flash('You need to log in first', 'error')
            return redirect(url_for('login.login'))

        # Get the event_id from the URL parameters
        event_id = request.args.get('event_id')
        if not event_id:
            flash('Please select an event first', 'error')
            return redirect(url_for('budget.budget_page'))

        # Get expense categories for the dropdown
        categories = BudgetModel.get_expense_categories()

        if request.method == 'POST':
            # Get form data
            budget_amount = request.form.get('budgetAmount', '').strip()
            expenses_amount = request.form.get('expensesAmount', '').strip()
            category = request.form.get('categoryName', '').strip()
            vendor = request.form.get('vendor', '').strip()
            payment_status = request.form.get('paymentStatus', '').strip()
            comments = request.form.get('comments', '').strip()

            # Initialize error messages
            error_messages = []

            # Validate Budget Amount
            try:
                budget_amount = float(budget_amount)
            except ValueError:
                error_messages.append('Budget Amount must be a valid number.')

            # Validate Expenses Amount
            try:
                expenses_amount = float(expenses_amount)
            except ValueError:
                error_messages.append('Expenses Amount must be a valid number.')

            # Validate Category
            if not category:
                error_messages.append('Category is required.')

            # Validate Payment Status
            valid_payment_statuses = ['Paid', 'Pending', 'Canceled']
            if not payment_status or payment_status not in valid_payment_statuses:
                error_messages.append('Invalid Payment Status.')

            # Validate Vendor
            if not vendor:
                error_messages.append('Vendor is required.')

            # Set default comment if empty
            if not comments:
                comments = 'No Comment'

            # If there are validation errors
            if error_messages:
                return render_template(
                    'OrgAddBudget.html',
                    categories=categories,
                    event_id=event_id,
                    error_message=error_messages
                )

            # If validation passes, prepare data for insertion
            budget_data = {
                'event_id': event_id,
                'budgetAmount': budget_amount,
                'expensesAmount': expenses_amount,
                'categoryName': category,
                'vendor': vendor,
                'paymentStatus': payment_status,
                'comments': comments
            }

            if BudgetModel.add_budget(budget_data):
                # flash('Budget added successfully', 'success')
                return redirect(url_for('budget.budget_page', selected_event=event_id))
            else:
                flash('Failed to add budget', 'error')

        return render_template(
            'OrgAddBudget.html',
            categories=categories,
            event_id=event_id
        )

    except Exception as e:
        print(f"Error in add_budget: {e}")
        flash('An error occurred while adding the budget', 'error')
        return redirect(url_for('budget.budget_page'))


@budget_bp.route('/delete_budget', methods=['POST'])
def delete_budget():
    try:
        if 'organiser_id' not in session:
            return jsonify({'success': False, 'message': 'You need to log in first'})

        data = request.get_json()
        budget_ids = data.get('budget_ids', [])

        if not budget_ids:
            return jsonify({'success': False, 'message': 'No budgets selected for deletion'})

        if BudgetModel.delete_budgets(budget_ids):
            return jsonify({
                'success': True, 
                'message': 'Selected budget(s) deleted successfully'
            })
        else:
            return jsonify({
                'success': False, 
                'message': 'Failed to delete selected budget(s)'
            })

    except Exception as e:
        print(f"Error in delete_budget: {e}")
        return jsonify({
            'success': False, 
            'message': 'An error occurred while deleting the budget(s)'
        })
