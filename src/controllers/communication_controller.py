from flask import Blueprint, request, render_template, flash, redirect, url_for, session
from flask_mail import Message
from extension import mail

communication_bp = Blueprint('communication', __name__)





@communication_bp.route('/send_email', methods=['POST'])
def send_email():

    
    
    to = request.form.get('to')  # This is a comma-separated string
    subject = request.form.get('subject')
    message = request.form.get('message')
    attachment = request.files.get('attachment')

    # Convert the comma-separated string into a list
    recipient_list = [email.strip() for email in to.split(',') if email.strip()]

    # Create the email message
    msg = Message(subject, recipients=recipient_list, body=message)
    
    if attachment:
        msg.attach(attachment.filename, attachment.content_type, attachment.read())

    try:
        mail.send(msg)
        # Email sent successfully, redirect to the referrer page
        referrer = request.form.get('referrer')
        return redirect(referrer or url_for('event_staff.view_event_staff'))  # Default redirect if no referrer
    except Exception as e:
        # Handle error
        return f"An error occurred: {str(e)}", 500





# @communication_bp.route('/email')
# def email_communicate():
#     return render_template('EmailCommunication.html')



@communication_bp.route('/email_communication')
def email_communication():
    
    emails = request.args.get('emails', '').split(',')
    return render_template('EmailCommunication.html', emails=emails)


