# resetPassword_controller.py
from flask import Blueprint, request, redirect, url_for, render_template, session
from flask_mail import Message
from src.models.resetPassword_model import ResetPasswordModel
from extension import mail  # Import mail from extension

reset_password_bp = Blueprint('reset_password', __name__)

@reset_password_bp.route('/reset_password', methods=['POST'])
def reset_password():
    email = request.form.get('resetEmail')

    # Validate email format
    if not email or "@" not in email or "." not in email:
        return render_template('OrgResetPwEmail.html', error="Please enter a valid email address.")

    # Check if user exists in the database
    user = ResetPasswordModel.get_user_by_email(email)
    if not user:
        return render_template('OrgResetPwEmail.html', error="Invalid or unregistered email. Please enter a registered email address.")

    # Email exists; generate and send verification code
    verification_code = ResetPasswordModel.generate_verification_code()
    
    # Store the verification code and email in session
    session['verification_code'] = str(verification_code)
    session['email'] = email

    msg = Message("Password Reset Verification Code", recipients=[email])
    msg.body = f"Hi, Your verification code is {verification_code}. Please use it within 10 minutes before it expires."
    try:
        mail.send(msg)
        return redirect(url_for('reset_password.reset_password_form_new'))
    except Exception as e:
        print(f"Error sending email: {e}")
        return render_template('OrgResetPwEmail.html', error="Failed to send verification code. Try again later.")

@reset_password_bp.route('/reset_password_form_new', methods=['GET'])
def reset_password_form_new():
    return render_template('OrgNewPw.html')

@reset_password_bp.route('/reset_password_verify', methods=['POST'])
def reset_password_verify():
    # Get the form data
    verification_code_input = request.form.get('verificationCode')
    new_password = request.form.get('newPassword')
    confirm_password = request.form.get('confirmPassword')

    # Check the verification code
    if verification_code_input != session.get('verification_code'):
        return render_template('OrgNewPw.html', error="Invalid verification code.")

    # Check if passwords match
    if new_password != confirm_password:
        return render_template('OrgNewPw.html', error="Passwords do not match.")

    # Validate password strength
    if not (8 <= len(new_password) <= 12 and any(c.isupper() for c in new_password) and
            any(c.islower() for c in new_password) and any(c in "!@#$%^&*()-_=+[]{};:,.<>?/" for c in new_password)):
        return render_template('OrgNewPw.html', error="Password must be 8-12 characters with at least one uppercase, one lowercase, and one special character.")

    # Update the user's password in the database
    email = session.get('email')
    if email:
        ResetPasswordModel.update_user_password(email, new_password)
        session.pop('verification_code', None)
        session.pop('email', None)
        return redirect(url_for('login.login'))  # Redirect to login page after successful reset

    return render_template('OrgNewPw.html', error="An error occurred. Please try again.")
