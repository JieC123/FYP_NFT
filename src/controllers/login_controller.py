# src/controllers/login_controller.py
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from flask_bcrypt import Bcrypt
from src.models.login_model import LoginModel  # Import your model for database interactions


bcrypt = Bcrypt()  # Initialize Bcrypt
login_bp = Blueprint('login', __name__)

@login_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Use the LoginModel to get user data
        user = LoginModel.get_user_by_email(email)

        if user and bcrypt.check_password_hash(user["Password"], password):
            # Successful login
            session['user'] = user["OrganiserEmail"]  # Save user email in session
            session['organiser_id'] = user["OrganiserID"]  # Store OrganiserID in session
            # session['organiser_name'] = user["OrganiserName"]
            return redirect(url_for('event.index'))  # Redirect to OrgViewEvent.html (mimicking the event_controller's index route)
        else:
            # Failed login
            flash('Invalid email or password. Please try again.', 'error')  # Flash error message
            return redirect(url_for('login.login'))  # Redirect back to login page

    return render_template('Orglogin.html')  # Render login page on GET request

@login_bp.route('/reset_password')
def reset_password():
    return render_template('OrgResetPwEmail.html')

@login_bp.route('/logout')
def logout():
    # Clear the session
    session.clear()  
    flash('You have been logged out successfully.', 'success')  
    return redirect(url_for('login.login'))


# @login_bp.before_request
# def before_request():
#     if 'organiser_id' in session:
#         organiser_id = session['organiser_id']
#         # Fetch the organiser's name from the database
#         organiser_name = LoginModel.get_user_by_id(organiser_id)
#         g.organiser_name = organiser_name  # Store the organiser's name globally in g
#     else:
#         g.organiser_name = None