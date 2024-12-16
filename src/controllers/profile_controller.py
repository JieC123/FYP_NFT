# src/controllers/profile_controller.py
from flask import Blueprint, render_template, session, redirect, url_for, flash, request, send_from_directory
from src.models.profile_model import ProfileModel
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
import os
import re

profile_bp = Blueprint('profile', __name__)
bcrypt = Bcrypt()


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, '../profile')

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@profile_bp.route('/OrgProfile')
def view_profile():
    organiser_id = session.get('organiser_id')  # Assume organiser_id is stored in the session after login

    if not organiser_id:
        flash("You need to log in first.", "danger")
        return redirect(url_for('login.login'))

    try:
        profile = ProfileModel.get_profile_by_id(organiser_id)

        if profile:
            return render_template('OrgProfile.html', organiser=profile)  # Pass the profile as 'organiser'
        else:
            flash("Profile not found.", "warning")
            return redirect(url_for('home'))
    except Exception as e:
        flash(f"An error occurred: {e}", "danger")
        return redirect(url_for('home'))

@profile_bp.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    organiser_id = session.get('organiser_id')

    if not organiser_id:
        flash("You need to log in first.", "danger")
        return redirect(url_for('login.login'))

    if request.method == 'POST':
        # Get updated profile information from the form
        name = request.form.get('name').strip()
        contact_no = request.form.get('contact').strip()
        ic_no = request.form.get('ic').strip()
        password = request.form.get('password').strip()
        profile_image = request.files.get('profile_image')

        # Fetch the current profile to retain unchanged values
        profile = ProfileModel.get_profile_by_id(organiser_id)
        if not profile:
            flash("Profile not found.", "danger")
            return redirect(url_for('profile.view_profile'))

        # Validation patterns
        ic_no_pattern = re.compile(r"^\d{6}-\d{2}-\d{4}$")
        contact_no_pattern = re.compile(r"^\d{10,11}$")
        password_pattern = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\W).{8,12}$")

        # Validate formats
        if not ic_no_pattern.match(ic_no):
            flash('IC No must be in the format 123456-23-5643.', 'danger')
            return redirect(url_for('profile.edit_profile'))
        if not contact_no_pattern.match(contact_no):
            flash('Contact No must be a 10- to 11-digit number.', 'danger')
            return redirect(url_for('profile.edit_profile'))
        if password and not password_pattern.match(password):
            flash('Password must be 8-12 characters, contain at least 1 uppercase, 1 lowercase, and 1 special character.', 'danger')
            return redirect(url_for('profile.edit_profile'))

        # Handle file upload securely if a new profile image is provided
        if profile_image:
            filename = secure_filename(profile_image.filename)
            allowed_extensions = ('.jpg', '.jpeg', '.png', '.gif')
            if not filename.lower().endswith(allowed_extensions):
                flash("Please upload a valid image file (.jpg, .jpeg, .png, .gif).", 'danger')
                return redirect(url_for('profile.edit_profile'))

            relative_image_path = os.path.join('profile', filename)
            profile_image.save(os.path.join(UPLOAD_FOLDER, filename))
        else:
            relative_image_path = profile['profile_image']

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8') if password else profile.get('password')

        try:
            ProfileModel.update_profile(
                organiser_id=organiser_id,
                name=name,
                contact_no=contact_no,
                ic_no=ic_no,
                password=hashed_password,
                profile_image=relative_image_path
            )
            # flash("Profile updated successfully!", "success")
            return redirect(url_for('profile.view_profile'))
        except Exception as e:
            flash(f"An error occurred while updating profile: {e}", "danger")
            return redirect(url_for('profile.edit_profile'))

    profile = ProfileModel.get_profile_by_id(organiser_id)
    if profile:
        return render_template('OrgEditProfile.html', organiser=profile)
    else:
        # flash("Profile not found.", "warning")
        return redirect(url_for('home'))

# Route to serve images from the src/profile folder
@profile_bp.route('/profile_images/<filename>')
def profile_images(filename):
    profile_image_folder = os.path.join(os.getcwd(), 'src', 'profile')
    return send_from_directory(profile_image_folder, filename)
