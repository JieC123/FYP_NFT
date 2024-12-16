from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
import os
import re
from src.models.register_model import RegisterModel
from flask_bcrypt import Bcrypt
import requests

bcrypt = Bcrypt()

register_bp = Blueprint('register', __name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, '../profile')

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@register_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Verify reCAPTCHA first
        recaptcha_response = request.form.get('g-recaptcha-response')
        if not recaptcha_response:
            flash('Please complete the reCAPTCHA verification.', 'danger')
            return redirect(url_for('register.register'))

        # Verify with Google
        verify_response = requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data={
                'secret': '6Ld5SJAqAAAAAIpaFI6GrVhKxzSSB0xONZx3VLdu',
                'response': recaptcha_response
            }
        )
        
        if not verify_response.json().get('success'):
            flash('reCAPTCHA verification failed. Please try again.', 'danger')
            return redirect(url_for('register.register'))

        full_name = request.form.get('fullName').strip()
        ic_no = request.form.get('icNo').strip()
        email = request.form.get('email').strip()
        contact_no = request.form.get('contactNo').strip()
        password = request.form.get('password').strip()
        profile_image = request.files.get('profileImage')

        # Validate empty fields
        if not all([full_name, ic_no, email, contact_no, password, profile_image]):
            flash('Please fill in all fields.', 'danger')
            return redirect(url_for('register.register'))

        # Validation patterns
        ic_no_pattern = re.compile(r"^\d{6}-\d{2}-\d{4}$")
        email_pattern = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
        contact_no_pattern = re.compile(r"^\d{10,11}$")
        password_pattern = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\W).{8,12}$")

        # Validate formats
        if not ic_no_pattern.match(ic_no):
            flash('IC No must be in the format 123456-23-5643.', 'danger')
            return render_template('OrgRegister.html', full_name=full_name, ic_no=ic_no, email=email, contact_no=contact_no)
        if not email_pattern.match(email):
            flash('Please enter a valid email address.', 'danger')
            return render_template('OrgRegister.html', full_name=full_name, ic_no=ic_no, email=email, contact_no=contact_no)
        if not contact_no_pattern.match(contact_no):
            flash('Contact No must be a 10- to 11-digit number.', 'danger')
            return render_template('OrgRegister.html', full_name=full_name, ic_no=ic_no, email=email, contact_no=contact_no)
        if not password_pattern.match(password):
            flash('Password must be 8-12 characters, contain at least 1 uppercase, 1 lowercase, and 1 special character.', 'danger')
            return render_template('OrgRegister.html', full_name=full_name, ic_no=ic_no, email=email, contact_no=contact_no)

        # Check if the email already exists in the database
        if RegisterModel.email_exists(email):
            flash('This email is already registered. Please use a different email.', 'danger')
            return render_template('OrgRegister.html', full_name=full_name, ic_no=ic_no, email=email, contact_no=contact_no)

        # Check file extension for image
        if profile_image:
            allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif'}
            filename = secure_filename(profile_image.filename)
            file_extension = os.path.splitext(filename)[1].lower()

            if file_extension not in allowed_extensions:
                flash('Please upload a valid image file (.jpg, .jpeg, .png, .gif).', 'danger')
                return render_template('OrgRegister.html', full_name=full_name, ic_no=ic_no, email=email, contact_no=contact_no)

            # Define the relative path structure to store in the database
            relative_image_path = os.path.join('profile', filename)

            # Save the image in the profile folder
            profile_image.save(os.path.join(UPLOAD_FOLDER, filename))
        else:
            flash('Profile image is required.', 'danger')
            return render_template('OrgRegister.html', full_name=full_name, ic_no=ic_no, email=email, contact_no=contact_no)

        # Hash the password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        try:
            RegisterModel.register_user(full_name, ic_no, email, contact_no, hashed_password, relative_image_path)
            flash('Registration successful!', 'success')
            return redirect(url_for('login.login'))
        except Exception as e:
            flash(f'Error registering user: {e}', 'danger')
            return render_template('OrgRegister.html', full_name=full_name, ic_no=ic_no, email=email, contact_no=contact_no)

    return render_template('OrgRegister.html')