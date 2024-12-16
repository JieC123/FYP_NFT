from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import pyodbc
from datetime import datetime, date, timedelta
import os
from werkzeug.utils import secure_filename
import time
import random
import json
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
import bcrypt
import requests
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__, template_folder='src', static_folder='src')
app.secret_key = 'your_secret_key_here'  # Set a secret key for flash messages and sessions

# Define the connection string for SQL Server
server = r'LAPTOP-VB12GW\SQLEXPRESS01'  # Using raw string to avoid escape sequence warning
database = 'EventDB'
username = 'user'
password = 'db1234'
driver = '{ODBC Driver 18 for SQL Server}'

# Define the upload folder and allowed extensions
UPLOAD_FOLDER = 'src/image'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Add these configurations after app initialization
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'angjc-pm21@student.tarc.edu.my'  # Replace with your Gmail
app.config['MAIL_PASSWORD'] = 'wmch bmfb butz uwyl'  # Replace with your app password
app.config['MAIL_DEFAULT_SENDER'] = 'angjc-pm21@student.tarc.edu.my'  # Replace with your Gmail
app.config['RECAPTCHA_SITE_KEY'] = '6Ldj7o8qAAAAACnkor28bW_ICqAJhe-QFJOLOcf2'
app.config['RECAPTCHA_SECRET_KEY'] = '6Ldj7o8qAAAAADPdN0hH-iTNzhMFsh9FxDZ6KR8S'

mail = Mail(app)
serializer = URLSafeTimedSerializer(app.secret_key)

def get_db_connection():
    conn = pyodbc.connect(f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password};Trusted_Connection=yes;Encrypt=no')
    return conn

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def verify_recaptcha(recaptcha_response):
    if not recaptcha_response:
        return False
    
    verify_url = 'https://www.google.com/recaptcha/api/siteverify'
    payload = {
        'secret': app.config['RECAPTCHA_SECRET_KEY'],
        'response': recaptcha_response
    }
    
    response = requests.post(verify_url, data=payload)
    result = response.json()
    
    return result.get('success', False)

@app.route('/')
def index():
    # if 'user_id' not in session:
    #     return redirect(url_for('login'))
    
    # Get featured events from database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # You can modify this query to select featured events based on your criteria
    cursor.execute("""
    SELECT DISTINCT e.EventID, e.EventTitle, e.EventStartDate, e.EventEndDate, e.EventVenue, e.EventImage, o.OrganiserName, MIN(t.Price) as Price
    FROM dbo.Event e 
    JOIN dbo.Organiser o ON e.OrganiserID = o.OrganiserID 
    JOIN dbo.Ticket t ON e.EventID = t.EventID
    WHERE t.IsNFT = 'Yes'
    GROUP BY e.EventID, e.EventTitle, e.EventStartDate, e.EventEndDate, e.EventVenue, e.EventImage, o.OrganiserName
    ORDER BY e.EventStartDate DESC
""")
    events = cursor.fetchall()
    conn.close()
    
    # Format the events data
    formatted_events = []
    for event in events:    
        event_image = f'EventImage/{event.EventImage}'
        event_start_datetime = event.EventStartDate
        event_end_datetime = event.EventEndDate
        
        formatted_event = {
            'EventID': event.EventID,
            'EventTitle': event.EventTitle,
            'EventStartDate': event_start_datetime.date(),
            'EventStartTime': event_start_datetime.time(),
            'EventEndDate': event_end_datetime.date(),
            'EventEndTime': event_end_datetime.time(),
            'EventVenue': event.EventVenue,
            'OrganiserName': event.OrganiserName,
            'Price': event.Price,
            'EventImage': event_image,
        }
        formatted_events.append(formatted_event)
    
    return render_template('index.html', featured_events=formatted_events)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password']
        confirm_password = request.form['confirmPassword']

        if not email or not password:
            return jsonify({
                'success': False,
                'message': 'All fields are required'
            })

        if password != confirm_password:
            return jsonify({
                'success': False,
                'message': 'Passwords do not match'
            })

        # Hash password with bcrypt
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM dbo.TicketingUser WHERE UserEmail = ?", (email,))
            if cursor.fetchone():
                return jsonify({
                    'success': False,
                    'message': 'Email already registered'
                })

            user_id = 'TU' + str(cursor.execute("SELECT COUNT(*) FROM dbo.TicketingUser").fetchone()[0] + 1).zfill(6)
            registration_date = datetime.now().strftime('%Y-%m-%d')

            cursor.execute("""
                INSERT INTO dbo.TicketingUser (UserID, UserName, UserEmail, UserContactInfo, ProfileImage, RegistrationDate, Password)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, 'user', email, '', 'image/user-avatar.png', registration_date, hashed_password))
            conn.commit()

            return jsonify({
                'success': True,
                'message': 'Signup successful! Please log in.',
                'redirect': url_for('login')
            })

        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            })
        finally:
            conn.close()

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password']
        recaptcha_response = request.form.get('g-recaptcha-response')

        if not email or not password:
            return jsonify({
                'success': False,
                'message': 'Email and password are required'
            })

        # Verify reCAPTCHA
        if not verify_recaptcha(recaptcha_response):
            return jsonify({
                'success': False,
                'message': 'Please complete the reCAPTCHA correctly'
            })

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM dbo.TicketingUser WHERE UserEmail = ?", (email,))
            user = cursor.fetchone()

            # Convert stored hash back to bytes before comparing
            if user and bcrypt.checkpw(password.encode('utf-8'), user.Password.encode('utf-8')):
                session['user_id'] = user.UserID
                session['username'] = user.UserName
                return jsonify({
                    'success': True,
                    'message': 'Login successful!',
                    'redirect': url_for('index')
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Invalid email or password'
                })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            })
        finally:
            conn.close()

    return render_template('login.html')

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('user_id', None)
    session.clear()
    return jsonify({
        'success': True,
        'message': 'Logged out successfully',
        'redirect': url_for('login')
    })

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email'].strip()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Check if email exists in database
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM dbo.TicketingUser 
                WHERE UserEmail = ?
            """, (email,))
            result = cursor.fetchone()
            
            if not result or result.count == 0:
                return jsonify({
                    'success': False,
                    'message': 'This email is not registered in our system. Please check your email or sign up for a new account.'
                })
            
            # Email exists, proceed with password reset
            token = serializer.dumps(email, salt='password-reset-salt')
            reset_url = url_for('reset_password', token=token, _external=True)
            
            try:
                msg = Message('TicketPro - Password Reset Request',
                            recipients=[email])
                msg.body = f'''To reset your password, visit the following link:
{reset_url}

If you did not make this request, please ignore this email.

This link will expire in 30 minutes for security purposes.
'''
                mail.send(msg)
                
                return jsonify({
                    'success': True,
                    'message': 'Password reset instructions have been sent to your email.',
                    'redirect': url_for('login')
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': 'Failed to send reset email. Please try again later.'
                })
                
        except Exception as e:
            return jsonify({
                'success': False,
                'message': 'An error occurred. Please try again.'
            })
        finally:
            cursor.close()
            conn.close()
            
    return render_template('forgetpass.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=1800)  # 30 minutes expiry
    except:
        return jsonify({
            'success': False,
            'message': 'The password reset link is invalid or has expired.',
            'redirect': url_for('forgot_password')
        })
    
    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            return jsonify({
                'success': False,
                'message': 'Passwords do not match.'
            })
        
        if len(password) < 6:  # Basic password validation
            return jsonify({
                'success': False,
                'message': 'Password must be at least 6 characters long.'
            })
        
        # Hash the new password with bcrypt
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE dbo.TicketingUser 
                SET Password = ? 
                WHERE UserEmail = ?
            """, (hashed_password, email))
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Your password has been successfully updated! Please login with your new password.',
                'redirect': url_for('login')
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': 'An error occurred while updating your password. Please try again.'
            })
        finally:
            conn.close()
    
    return render_template('resetpass.html', token=token)

@app.route('/eventlist')
def eventlist():
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Modified query to avoid grouping/sorting TEXT fields
    cursor.execute("""
        WITH UniqueEvents AS (
            SELECT DISTINCT
                e.EventID,
                e.EventTitle,
                e.EventStartDate,
                e.EventEndDate,
                e.EventVenue,
                o.OrganiserName,
                e.EventImage
            FROM dbo.Event e 
            JOIN dbo.Organiser o ON e.OrganiserID = o.OrganiserID
            JOIN dbo.Ticket t ON e.EventID = t.EventID
            WHERE e.EventStartDate >= GETDATE() AND e.EventStatus = 'Upcoming' AND t.IsNFT = 'Yes'
        )
        SELECT 
            ue.*,
            e.EventDescription,
            (SELECT MIN(Price) FROM dbo.Ticket WHERE EventID = ue.EventID) as MinPrice
        FROM UniqueEvents ue
        JOIN dbo.Event e ON ue.EventID = e.EventID
        ORDER BY ue.EventStartDate
    """)
    
    # WHERE e.EventStartDate >= GETDATE()  -- Optional: Only show future events
    
    events = cursor.fetchall()
    conn.close()
    
    # Format the event dates and times
    formatted_events = []
    for event in events:
        event_start_datetime = event.EventStartDate
        event_end_datetime = event.EventEndDate
        event_image = f'EventImage/{event.EventImage}'
        
        formatted_event = {
            'EventID': event.EventID,
            'EventTitle': event.EventTitle,
            'EventStartDate': event_start_datetime.date(),
            'EventStartTime': event_start_datetime.time(),
            'EventEndDate': event_end_datetime.date(),
            'EventEndTime': event_end_datetime.time(),
            'EventVenue': event.EventVenue,
            'OrganiserName': event.OrganiserName,
            'EventDescription': event.EventDescription,
            'Price': event.MinPrice,  # Shows the minimum ticket price
            'EventImage': event_image,
        }
        formatted_events.append(formatted_event)
    
    return render_template('eventlist.html', events=formatted_events)

@app.route('/myticket')
def myticket():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Updated query to ensure we get all unique NFT records
    query = """
    SELECT DISTINCT
        n.TokenID,
        t.TicketID,
        t.EventID,
        t.TicketType,
        t.Price,
        t.IsTransferrable,  -- Make sure this column exists in Ticket table
        e.EventTitle,
        e.EventStartDate,
        e.EventEndDate,
        e.EventVenue,
        e.EventImage,
        CASE 
            WHEN EXISTS (
                SELECT 1 
                FROM dbo.ResaleListings r 
                WHERE r.TokenID = n.TokenID 
                AND r.IsActive = 1
            ) THEN 1 
            ELSE 0 
        END as IsReselling
    FROM dbo.NFT n
    INNER JOIN dbo.Ticket t ON n.TicketID = t.TicketID  -- Changed to INNER JOIN
    INNER JOIN dbo.Event e ON t.EventID = e.EventID     -- Changed to INNER JOIN
    WHERE n.PlatOwnerID = ?
    ORDER BY e.EventStartDate DESC
"""
    
    try:
        cursor.execute(query, (session['user_id'],))
        tickets = cursor.fetchall()
        
        print(tickets)
        
        now = datetime.now()
        
        formatted_tickets = []
        for ticket in tickets:
            event_start_datetime = ticket.EventStartDate
            event_end_datetime = ticket.EventEndDate
            event_image = f'EventImage/{ticket.EventImage}'
            
            formatted_ticket = {
                'TicketID': ticket.TicketID,
                'TokenID': ticket.TokenID,
                'EventTitle': ticket.EventTitle,
                'EventStartDate': event_start_datetime.date(),
                'EventStartTime': event_start_datetime.time(),
                'EventEndDate': event_end_datetime.date(),
                'EventEndTime': event_end_datetime.time(),
                'EventVenue': ticket.EventVenue,
                'Price': float(ticket.Price),
                'TicketType': ticket.TicketType,
                'EventStartDateTime': event_start_datetime,
                'IsReselling': bool(ticket.IsReselling),
                'EventImage': event_image,
                'IsTransferrable': ticket.IsTransferrable
            }
            formatted_tickets.append(formatted_ticket)
        
        return render_template('myticket.html', tickets=formatted_tickets, now=now)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Error retrieving tickets',
            'redirect': url_for('index')
        }), 500
    finally:
        conn.close()

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        username = request.form['name'].strip()
        phone = request.form['phone'].strip()
        file = request.files.get('image')

        if not username or not phone:
            return jsonify({
                'success': False,
                'message': 'All fields are required'
            }), 400

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            profile_image = os.path.join('image', filename).replace('\\', '/')
        else:
            profile_image = request.form['current_image']

        try:
            cursor.execute("""
                UPDATE dbo.TicketingUser
                SET UserName = ?, UserContactInfo = ?, ProfileImage = ?
                WHERE UserID = ?
            """, (username, phone, profile_image, user_id))
            conn.commit()

            # Update session username
            session['username'] = username

            return jsonify({
                'success': True,
                'message': 'Profile updated successfully!',
                'redirect': url_for('index'),
                'username': username  # Send updated username back to client
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            }), 500
        finally:
            conn.close()

    try:
        cursor.execute("SELECT * FROM dbo.TicketingUser WHERE UserID = ?", (user_id,))
        user = cursor.fetchone()

        if user:
            return render_template('profile.html', user=user)
        else:
            return jsonify({
                'success': False,
                'message': 'User not found',
                'redirect': url_for('index')
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}',
            'redirect': url_for('index')
        }), 500
    finally:
        conn.close()

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Implement cart logic here
    return render_template('cart.html')

@app.route('/checkout')
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Implement checkout logic here
    return render_template('checkout.html', event={
        'EventTitle': '',  # This will be populated by JavaScript
        'TicketType': ''   # This will be populated by JavaScript
})

@app.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please log in first'}), 401
    
    event_id = request.json.get('event_id')
    quantity = request.json.get('quantity', 1)
    
    # Implement add to cart logic here
    # For now, we'll just return a success message
    return jsonify({'success': True, 'message': 'Added to cart successfully'})

@app.route('/remove-from-cart', methods=['POST'])
def remove_from_cart():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please log in first'}), 401
    
    item_id = request.json.get('item_id')
    
    # Implement remove from cart logic here
    # For now, we'll just return a success message
    return jsonify({'success': True, 'message': 'Removed from cart successfully'})

@app.route('/eventdetail/<string:id>')
def eventdetail(id):
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # First, get event and organizer details
        cursor.execute("""
            SELECT e.*, o.OrganiserName, o.OrganiserEmail, o.OrganiserContactNo, o.OrganiserProfileImage, o.EventHistoryCount
            FROM dbo.Event e 
            JOIN dbo.Organiser o ON e.OrganiserID = o.OrganiserID
            WHERE e.EventID = ?
        """, (id,))
        event = cursor.fetchone()
        
        # Then, get all ticket types for this event
        cursor.execute("""
            SELECT *
            FROM dbo.Ticket
            WHERE EventID = ?
            AND IsNft = 'Yes'
        """, (id,))
        tickets = cursor.fetchall()
        
        if not event:
            return jsonify({
                'success': False,
                'message': 'Event not found',
                'redirect': url_for('eventlist')
            }), 404
            
        event_start_datetime = event.EventStartDate
        event_end_datetime = event.EventEndDate
        event_image = f'EventImage/{event.EventImage}'
        
        formatted_event = {
            'EventID': event.EventID,
            'EventTitle': event.EventTitle,
            'EventStartDate': event_start_datetime.date(),
            'EventStartTime': event_start_datetime.time(),
            'EventEndDate': event_end_datetime.date(),
            'EventEndTime': event_end_datetime.time(),
            'EventVenue': event.EventVenue,
            'EventImage': event_image,
            'OrganiserName': event.OrganiserName,
            'OrganiserEmail': event.OrganiserEmail,
            'OrganiserContactNo': event.OrganiserContactNo,
            'OrganiserProfileImage': event.OrganiserProfileImage,
            'EventHistoryCount': event.EventHistoryCount,
            'EventDescription': event.EventDescription,
        }
        
        # Format ticket types
        formatted_tickets = []
        for ticket in tickets:
            formatted_tickets.append({
                'TicketID': ticket.TicketID,
                'TicketType': ticket.TicketType,
                'Price': ticket.Price,
                'QuantityAvailable': ticket.QuantityAvailable,
                'IsTransferrable': ticket.IsTransferrable
            })
        
        # Add exchange rate
        exchange_rate = 14000  # Example static rate of 1 ETH = 14000 MYR
        
        return render_template('eventdetail.html', 
                             event=formatted_event, 
                             tickets=formatted_tickets,
                             exchange_rate=exchange_rate)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Error retrieving event details',
            'redirect': url_for('eventlist')
        }), 500
    finally:
        conn.close()
    
@app.route('/get_contract_data')
def get_contract_data():
    try:
        contract_json_path = os.path.join(app.root_path, 'build', 'contracts', 'Tickets.json')
        if not os.path.exists(contract_json_path):
            return jsonify({'error': 'Contract JSON file not found'}), 404

        with open(contract_json_path, 'r') as file:
            contract_data = json.load(file)

        # Get the network ID (you may need to adjust this based on your setup)
        network_id = '5777'  # This is typically the default for local development networks

        if network_id not in contract_data['networks']:
            return jsonify({'error': 'Network ID not found in contract data'}), 404

        abi = contract_data['abi']
        address = contract_data['networks'][network_id]['address']

        return jsonify({'abi': abi, 'address': address})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_nft_data')
def get_nft_data():
    try:
        # Fetch NFT contract details
        contract_json_path = os.path.join(app.root_path, 'build', 'contracts', 'Tickets.json')
        if not os.path.exists(contract_json_path):
            return jsonify({'error': 'Contract JSON file not found'}), 404

        with open(contract_json_path, 'r') as file:
            contract_data = json.load(file)

        network_id = '5777'  # Adjust based on your setup

        if network_id not in contract_data['networks']:
            return jsonify({'error': 'Network ID not found in contract data'}), 404

        abi = contract_data['abi']
        address = contract_data['networks'][network_id]['address']

        return jsonify({'abi': abi, 'address': address})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/update_owner', methods=['POST'])
def update_owner():
    data = request.json
    token_id = data.get('tokenId')
    new_owner = data.get('newOwner')
    quantity = int(data.get('quantity', 1)) 
                
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Begin transaction
        # cursor.execute("BEGIN TRANSACTION")
        
        # First check if NFT exists
        cursor.execute("SELECT TicketID, PlatOwnerID FROM dbo.NFT WHERE TokenID = ?", (str(token_id),))  # Convert to string if needed
        nft_data = cursor.fetchone()
    
        ticket_id = nft_data.TicketID
        
        # Update NFT owner if it exists
        cursor.execute("""
            UPDATE dbo.NFT 
            SET OwnerID = ?, 
                PlatOwnerID = ?
            WHERE TokenID = ?
        """, (new_owner, session['user_id'], str(token_id)))
        
        print(f"Updated NFT owner - Rows affected: {cursor.rowcount}")  # Debug log

        # Update ticket quantities
        cursor.execute("""
            UPDATE dbo.Ticket 
            SET QuantitySold = QuantitySold + ?
            WHERE TicketID = ? 
        """, (quantity, ticket_id))
        
        print(f"Updated ticket quantities - Rows affected: {cursor.rowcount}")  # Debug log

        # Check if updates were successful
        if cursor.rowcount == 0:
            cursor.execute("ROLLBACK")
            return jsonify({'error': 'Failed to update ticket quantities'}), 400

        # Commit all changes
        cursor.execute("COMMIT")
        
        return jsonify({
            'success': True, 
            'message': f'Owner and quantities updated successfully. {quantity} tickets purchased.'
        })
        
    except Exception as e:
        cursor.execute("ROLLBACK")
        print(f"Error in update_owner: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/check_and_get_nft/<string:ticket_id>', methods=['GET'])
def check_and_get_nft(ticket_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Check ticket availability including reservations
        cursor.execute("""
            SELECT 
                t.QuantityAvailable,
                ISNULL(
                    (SELECT SUM(r.Quantity)
                    FROM dbo.TicketReservations r
                    WHERE r.TicketID = t.TicketID
                    AND r.Status = 'ACTIVE'
                    AND r.ExpiryTime > GETDATE()), 0
                ) as ReservedQuantity
            FROM dbo.Ticket t
            WHERE t.TicketID = ?
        """, (ticket_id,))
        
        ticket_info = cursor.fetchone()
        
        if not ticket_info:
            return jsonify({'error': 'Ticket not found'}), 404

        actual_available = ticket_info.QuantityAvailable + ticket_info.ReservedQuantity
        
        print(f"Ticket {ticket_id} - Available: {ticket_info.QuantityAvailable}, Reserved: {ticket_info.ReservedQuantity}, Actual: {actual_available}")  # Debug log

        if actual_available <= 0:
            return jsonify({'error': 'Ticket not available'}), 404

        # Retrieve NFT data
        cursor.execute("""
            SELECT n.TokenID, n.OwnerID
            FROM dbo.NFT n
            WHERE n.TicketID = ?
        """, (ticket_id,))
        nft = cursor.fetchone()

        if not nft:
            return jsonify({'error': 'No NFT available for transfer'}), 404

        return jsonify({'tokenId': nft.TokenID, 'ownerId': nft.OwnerID})

    except Exception as e:
        print(f"Error in check_and_get_nft: {str(e)}")  # Debug log
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/get_ticket_id', methods=['POST'])
def get_ticket_id():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401

    event_title = request.json.get('eventTitle')
    ticket_type = request.json.get('ticketType')
    
    print(f"Received event title: {event_title}, ticket type: {ticket_type}")  # Debug log

    if not event_title or not ticket_type:
        return jsonify({'error': 'Event title and ticket type are required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Query to get the TicketID and check availability including reservations
        cursor.execute("""
            SELECT 
                t.TicketID,
                t.QuantityAvailable,
                t.Price,
                ISNULL(
                    (SELECT SUM(r.Quantity)
                    FROM dbo.TicketReservations r
                    WHERE r.TicketID = t.TicketID
                    AND r.Status = 'ACTIVE'
                    AND r.ExpiryTime > GETDATE()), 0
                ) as ReservedQuantity
            FROM dbo.Ticket t
            JOIN dbo.Event e ON t.EventID = e.EventID
            WHERE e.EventTitle = ?
            AND t.TicketType = ?
        """, (event_title, ticket_type))
        
        ticket = cursor.fetchone()

        if ticket:
            actual_available = ticket.QuantityAvailable + ticket.ReservedQuantity
            print(f"Ticket found - ID: {ticket.TicketID}, Available: {ticket.QuantityAvailable}, Reserved: {ticket.ReservedQuantity}, Actual: {actual_available}")  # Debug log
            
            if actual_available > 0:
                ticket_data = {
                    'ticketId': ticket.TicketID,
                    'quantityAvailable': actual_available,
                    'price': float(ticket.Price)
                }
                return jsonify(ticket_data)
            else:
                return jsonify({'error': f'No available tickets found for {ticket_type}'}), 404
        else:
            return jsonify({'error': f'No tickets found for {ticket_type}'}), 404

    except Exception as e:
        print(f"Error in get_ticket_id: {str(e)}")  # Debug log
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
        
@app.route('/marketplace')
def marketplace():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get all resale listings with event details
        cursor.execute("""
            SELECT 
                t.TicketID, 
                t.TokenID, 
                tk.TicketType,
                tk.Price as OriginalPrice,
                t.Price as ResalePrice, 
                e.EventTitle, 
                e.EventStartDate, 
                e.EventVenue,
                e.EventImage,
                u.UserName as SellerName
            FROM dbo.ResaleListings t
            JOIN dbo.Ticket tk ON t.TicketID = tk.TicketID
            JOIN dbo.Event e ON tk.EventID = e.EventID
            JOIN dbo.TicketingUser u ON t.SellerID = u.UserID
            WHERE t.IsActive = 1
        """)
        listings = cursor.fetchall()
        
        # Format the listings data
        formatted_listings = []
        for listing in listings:
            event_image = f'EventImage/{listing.EventImage}'
            
            formatted_listing = {
                'TicketID': listing.TicketID,
                'TokenID': listing.TokenID,
                'ResalePrice': float(listing.ResalePrice),  # Convert decimal to float
                'EventTitle': listing.EventTitle,
                'EventStartDate': listing.EventStartDate.strftime('%Y-%m-%d'),  # Format date
                'EventVenue': listing.EventVenue,
                'EventImage': event_image,
                'SellerName': listing.SellerName,
                'TicketType': listing.TicketType,
                'OriginalPrice': float(listing.OriginalPrice)
            }
            
            formatted_listings.append(formatted_listing)
        
        return render_template('marketplace.html', listings=formatted_listings)
        
    except Exception as e:
        print(f"Error in marketplace route: {str(e)}")
        return redirect(url_for('index'))
    finally:
        conn.close()

@app.route('/list_ticket', methods=['POST'])
def list_ticket():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.json
    token_id = data.get('tokenId')
    price = data.get('price')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # First get the ticket ID associated with this token
        cursor.execute("""
            SELECT TicketID 
            FROM dbo.NFT 
            WHERE TokenID = ?
        """, (str(token_id),))
        
        nft_data = cursor.fetchone()
        if not nft_data:
            return jsonify({'error': 'NFT not found'}), 404
            
        ticket_id = nft_data.TicketID
        
        # Add listing to database with ticket ID
        cursor.execute("""
            INSERT INTO dbo.ResaleListings 
            (TokenID, TicketID, SellerID, Price, IsActive) 
            VALUES (?, ?, ?, ?, 1)
        """, (str(token_id), ticket_id, session['user_id'], price))
        
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error in list_ticket: {str(e)}")  # Debug log
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/cancel_listing', methods=['POST'])
def cancel_listing():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.json
    token_id = data.get('tokenId')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE dbo.ResaleListings 
            SET IsActive = 0 
            WHERE TokenID = ? AND SellerID = ?
        """, (token_id, session['user_id']))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/update_resale_owner', methods=['POST'])
def update_resale_owner():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.json
    token_id = data.get('tokenId')
    new_owner = data.get('newOwner')
    transaction_hash = data.get('transactionHash')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Begin transaction
        transaction_id = get_next_transaction_id()
        
        # Get seller ID and price from active listing
        cursor.execute("""
            SELECT rl.SellerID, rl.Price, rl.TicketID
            FROM dbo.ResaleListings rl
            WHERE rl.TokenID = ? AND rl.IsActive = 1
        """, (str(token_id),))
        
        listing = cursor.fetchone()
        if not listing:
            raise Exception('Active listing not found')
            
        # Generate order ID
        order_id = f'ORD{int(time.time())}'
        
        # Insert into Orders table
        cursor.execute("""
            INSERT INTO dbo.Orders 
            (OrderID, UserID, TotalAmount, TransactionHash, Status)
            VALUES (?, ?, ?, ?, ?)
        """, (
            order_id,
            session['user_id'],
            float(listing.Price),
            transaction_hash,
            'Completed'
        ))
        
        # Insert into OrderItems table
        cursor.execute("""
            INSERT INTO dbo.OrderItems 
            (OrderID, TokenID, TicketID, Quantity, Price)
            VALUES (?, ?, ?, ?, ?)
        """, (
            order_id,
            str(token_id),
            listing.TicketID,
            1,  # Quantity is always 1 for resale
            float(listing.Price)
        ))
            
        # Update NFT ownership
        cursor.execute("""
            UPDATE dbo.NFT 
            SET OwnerID = ?,
                PlatOwnerID = ?
            WHERE TokenID = ?
        """, (new_owner, session['user_id'], str(token_id)))
        
        # Mark the resale listing as inactive and record buyer
        cursor.execute("""
            UPDATE dbo.ResaleListings 
            SET IsActive = 0,
                SoldTime = GETDATE(),
                BuyerID = ?,
                TransactionHash = ?
            WHERE TokenID = ? AND IsActive = 1
        """, (session['user_id'], transaction_hash, str(token_id)))
        
        # Add transaction record
        cursor.execute("""
            INSERT INTO dbo.TransactionHistory 
            (TransactionID, OrderID, TransactionType, TransactionHash, Status)
            VALUES (?, ?, 'RESALE', ?, ?)
        """, (
            transaction_id,
            order_id,
            transaction_hash,
            'SUCCESS'
        ))
        
        # Commit all changes
        conn.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        conn.rollback()
        print(f"Error in update_resale_owner: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/ticket_detail/<string:ticket_id>/<string:token_id>')
def ticket_detail(ticket_id, token_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                t.TicketID,
                t.TicketType,
                t.Price,
                t.IsTransferrable,
                n.TokenID,
                n.QRCodeURI,
                n.VerificationHash,
                e.EventTitle,
                e.EventStartDate,
                e.EventEndDate,
                e.EventVenue,
                e.EventDescription,
                e.EventImage,
                CASE 
                    WHEN EXISTS (
                        SELECT 1 
                        FROM dbo.ResaleListings r 
                        WHERE r.TokenID = n.TokenID 
                        AND r.IsActive = 1
                    ) THEN 1 
                    ELSE 0 
                END as IsReselling
            FROM dbo.NFT n
            JOIN dbo.Ticket t ON n.TicketID = t.TicketID
            JOIN dbo.Event e ON t.EventID = e.EventID
            WHERE t.TicketID = ? 
            AND n.TokenID = ?
            AND n.PlatOwnerID = ?
        """, (ticket_id, token_id, session['user_id']))
        
        ticket = cursor.fetchone()
        
        if not ticket:
            return jsonify({
                'success': False,
                'message': 'Ticket not found or unauthorized',
                'redirect': url_for('myticket')
            }), 404
            
        event_start_datetime = ticket.EventStartDate
        event_end_datetime = ticket.EventEndDate
        
        qr_code_hash = ticket.QRCodeURI.replace('ipfs://', '') if ticket.QRCodeURI else ''
        
        # Format the image path correctly
        event_image = ticket.EventImage if ticket.EventImage else 'image/event1.jpg'
        if event_image and not event_image.startswith('image/'):
            event_image = f'EventImage/{event_image}'
        
        ticket_details = {
            'TicketID': ticket.TicketID,
            'TokenID': ticket.TokenID,
            'EventTitle': ticket.EventTitle,
            'EventStartDate': ticket.EventStartDate.date(),
            'EventStartTime': ticket.EventStartDate.time(),
            'EventEndDate': ticket.EventEndDate.date(),
            'EventEndTime': ticket.EventEndDate.time(),
            'EventVenue': ticket.EventVenue,
            'EventDescription': ticket.EventDescription,
            'EventImage': event_image,
            'TicketType': ticket.TicketType,
            'Price': float(ticket.Price),
            'IsReselling': bool(ticket.IsReselling),
            'QRCodeHash': qr_code_hash,
            'VerificationHash': ticket.VerificationHash,
            'QRCodeGateway': f'https://gateway.ipfs.io/ipfs/{qr_code_hash}' if qr_code_hash else None,
            'LocalIPFSUrl': f'http://localhost:5001/ipfs/{qr_code_hash}' if qr_code_hash else None,
            'IsTransferrable': ticket.IsTransferrable
        }
        
        return render_template('ticket_detail.html', ticket=ticket_details)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Error retrieving ticket details',
            'redirect': url_for('myticket')
        }), 500
    finally:
        conn.close()

def generate_participant_id():
    # Get the latest participant ID from the database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT TOP 1 ParticipantID FROM Participants ORDER BY ParticipantID DESC")
    result = cursor.fetchone()
    
    if result:
        # Extract the number from existing ID and increment
        last_id = result[0]
        num = int(last_id[2:]) + 1
    else:
        # Start with first ID
        num = 1
    
    # Format new ID with leading zeros
    new_id = f"P{num:06d}"
    return new_id

@app.route('/insert_order', methods=['POST'])
def insert_order():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Begin transaction
        
        transaction_id = get_next_transaction_id()
        
        # Insert into Orders table
        cursor.execute("""
            INSERT INTO dbo.Orders 
            (OrderID, UserID, TotalAmount, TransactionHash, Status)
            VALUES (?, ?, ?, ?, ?)
        """, (
            data['orderId'],
            session['user_id'],
            data['totalAmount'],
            data['transactionHash'],
            data['status']
        ))
        
        # Insert into TransactionHistory table
        cursor.execute("""
            INSERT INTO dbo.TransactionHistory 
            (TransactionID, OrderID, TransactionType, TransactionHash, Status)
            VALUES (?, ?, ?, ?, ?)
        """, (
            transaction_id,
            data['orderId'],
            'PURCHASE',
            data['transactionHash'],
            'SUCCESS'
        ))
        
        participant_id = generate_participant_id()
        cursor.execute("""
            INSERT INTO Participants (ParticipantID, RegistrationDate, EventID, UserID)
            VALUES (?, GETDATE(), ?, ?)
        """, (participant_id, data['eventId'], session['user_id']))

        # Commit the transaction
        cursor.execute("COMMIT")
        conn.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        cursor.execute("ROLLBACK")
        print(f"Error in insert_order: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/insert_order_item', methods=['POST'])
def insert_order_item():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Insert single record with quantity
        cursor.execute("""
            INSERT INTO dbo.OrderItems 
            (OrderID, TokenID, TicketID, Quantity, Price)
            VALUES (?, ?, ?, ?, ?)
        """, (
            data['orderId'],
            data['tokenId'],  # Now contains comma-separated tokenIds
            data['ticketId'],
            data['quantity'],
            data['price']
        ))
        
        conn.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error in insert_order_item: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()
        
def get_next_transaction_id():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Get the current highest transaction ID using string comparison
        cursor.execute("""
            SELECT TOP 1 TransactionID 
            FROM dbo.TransactionHistory 
            ORDER BY TransactionID DESC
        """)
        
        result = cursor.fetchone()
        if result and result.TransactionID:
            # Extract number and increment
            current_num = int(result.TransactionID[2:])  # Skip 'TX' prefix
            next_num = current_num + 1
        else:
            next_num = 1
            
        # Format new ID with leading zeros (TX000001)
        return f'TX{next_num:06d}'
        
    finally:
        cursor.close()
        conn.close()

@app.route('/orders')
def orders():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Query for regular orders (purchases) and resale purchases
        cursor.execute("""
            SELECT 
                o.OrderID,
                COALESCE(rl.SoldTime, o.OrderDate) as OrderDate,
                o.TotalAmount,
                o.Status,
                o.TransactionHash,
                oi.TokenID,
                oi.TicketID,
                oi.Quantity,
                oi.Price,
                t.TicketType,
                e.EventTitle,
                e.EventImage,
                CASE 
                    WHEN rl.ListingID IS NOT NULL THEN 'RESALE'
                    ELSE 'PURCHASE'
                END as Type,
                0 as IsSeller,
                b.UserName as BuyerName,
                s.UserName as SellerName,
                COALESCE(
                    CAST(rl.TokenID as VARCHAR),
                    (
                        SELECT STRING_AGG(CAST(TokenID AS VARCHAR(20)), ', ')
                        FROM dbo.NFT n2
                        WHERE n2.TicketID = oi.TicketID
                        AND n2.TokenID IN (
                            SELECT value
                            FROM STRING_SPLIT(oi.TokenID, ',')
                        )
                    )
                ) as TokenIDs
            FROM dbo.Orders o
            JOIN dbo.OrderItems oi ON o.OrderID = oi.OrderID
            JOIN dbo.Ticket t ON oi.TicketID = t.TicketID
            JOIN dbo.Event e ON t.EventID = e.EventID
            LEFT JOIN dbo.ResaleListings rl ON o.TransactionHash = rl.TransactionHash
            LEFT JOIN dbo.TicketingUser b ON rl.BuyerID = b.UserID
            LEFT JOIN dbo.TicketingUser s ON rl.SellerID = s.UserID
            WHERE o.UserID = ?

            UNION ALL

            -- Query for resale transactions (as seller only)
            SELECT 
                CONCAT('RSL', rl.ListingID) as OrderID,
                rl.SoldTime as OrderDate,
                rl.Price as TotalAmount,
                'Completed' as Status,
                rl.TransactionHash,
                CAST(rl.TokenID as VARCHAR) as TokenID,
                rl.TicketID,
                1 as Quantity,
                rl.Price,
                t.TicketType,
                e.EventTitle,
                e.EventImage,
                'RESALE' as Type,
                1 as IsSeller,
                b.UserName as BuyerName,
                s.UserName as SellerName,
                CAST(rl.TokenID as VARCHAR) as TokenIDs
            FROM dbo.ResaleListings rl
            JOIN dbo.Ticket t ON rl.TicketID = t.TicketID
            JOIN dbo.Event e ON t.EventID = e.EventID
            JOIN dbo.TicketingUser b ON rl.BuyerID = b.UserID
            JOIN dbo.TicketingUser s ON rl.SellerID = s.UserID
            WHERE rl.SellerID = ? AND rl.SoldTime IS NOT NULL

            ORDER BY OrderDate DESC
        """, (session['user_id'], session['user_id']))
        
        orders_data = cursor.fetchall()
        
        # Format the orders data
        formatted_orders = []
        for order in orders_data:
            event_image = f'EventImage/{order.EventImage}'
            
            order_dict = {
                'OrderID': order.OrderID,
                'OrderDate': order.OrderDate,
                'Status': order.Status,
                'TotalAmount': float(order.TotalAmount),
                'TransactionHash': order.TransactionHash,
                'Type': order.Type,
                'IsSeller': order.IsSeller,
                'BuyerName': order.BuyerName,
                'SellerName': order.SellerName,
                'Items': [{
                    'EventTitle': order.EventTitle,
                    'EventImage': event_image,
                    'TicketType': order.TicketType,
                    'Quantity': order.Quantity,
                    'Price': float(order.Price),
                    'TokenIDs': [tid.strip() for tid in order.TokenIDs.split(',')] if order.TokenIDs else None
                }]
            }
            formatted_orders.append(order_dict)
        
        return render_template('orders.html', orders=formatted_orders)
        
    except Exception as e:
        print(f"Error in orders route: {str(e)}")
        return redirect(url_for('index'))
    finally:
        cursor.close()
        conn.close()

@app.route('/reserve_tickets', methods=['POST'])
def reserve_tickets():
    print("Reservation attempt started")
    if 'user_id' not in session:
        print("No user session found")
        return jsonify({'error': 'Not logged in'}), 401
        
    data = request.json
    tickets = data.get('tickets', [])  # Expect an array of ticket reservations
    
    if not tickets:
        return jsonify({'error': 'No tickets provided'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Verify availability for all tickets
        for ticket in tickets:
            cursor.execute("""
                SELECT QuantityAvailable 
                FROM dbo.Ticket 
                WHERE TicketID = ?
            """, (ticket['ticketId'],))
            
            ticket_data = cursor.fetchone()
            if not ticket_data or ticket_data.QuantityAvailable < ticket['quantity']:
                return jsonify({
                    'error': f'Not enough tickets available for ticket ID {ticket["ticketId"]}'
                }), 400
        
        # Calculate reservation times
        current_time = datetime.now()
        expiry_time = current_time + timedelta(minutes=5)
        
        # Generate base reservation ID
        base_reservation_id = f'RES{int(time.time())}'
        
        # Create reservations for each ticket type with unique IDs
        for index, ticket in enumerate(tickets):
            # Create unique reservation ID for each ticket type
            unique_reservation_id = f"{base_reservation_id}_{index + 1}"
            
            cursor.execute("""
                INSERT INTO dbo.TicketReservations 
                (ReservationID, TicketID, UserID, Quantity, ReservationTime, ExpiryTime, Status)
                VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE')
            """, (unique_reservation_id, ticket['ticketId'], session['user_id'], ticket['quantity'], current_time, expiry_time))
            
            # Temporarily reduce available quantity
            cursor.execute("""
                UPDATE dbo.Ticket 
                SET QuantityAvailable = QuantityAvailable - ?
                WHERE TicketID = ?
            """, (ticket['quantity'], ticket['ticketId']))
        
        conn.commit()
        print(f"Reservations created successfully: {base_reservation_id}")
        
        return jsonify({
            'success': True,
            'reservationId': base_reservation_id,  # Return base ID for reference
            'expiryTime': expiry_time.isoformat()
        })
        
    except Exception as e:
        conn.rollback()
        print(f"Error in reservation: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/check_reservation/<reservation_id>', methods=['GET'])
def check_reservation(reservation_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT Status, ExpiryTime 
            FROM dbo.TicketReservations 
            WHERE ReservationID = ? AND UserID = ?
        """, (reservation_id, session['user_id']))
        
        reservation = cursor.fetchone()
        if not reservation:
            return jsonify({'error': 'Reservation not found'}), 404
            
        return jsonify({
            'status': reservation.Status,
            'expiryTime': reservation.ExpiryTime.isoformat()
        })
        
    finally:
        conn.close()

@app.route('/release_reservation/<reservation_id>', methods=['POST'])
def release_reservation(reservation_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get all reservation details for this reservation ID (including all sub-reservations)
        cursor.execute("""
            SELECT TicketID, Quantity, Status 
            FROM dbo.TicketReservations 
            WHERE ReservationID LIKE ? AND Status = 'ACTIVE'
        """, (f"{reservation_id}%",))  # Use LIKE to match all related reservations
        
        reservations = cursor.fetchall()
        if not reservations:
            return jsonify({'error': 'Invalid reservation'}), 400
            
        for reservation in reservations:
            # Update reservation status
            cursor.execute("""
                UPDATE dbo.TicketReservations 
                SET Status = 'EXPIRED' 
                WHERE ReservationID LIKE ? AND TicketID = ?
            """, (f"{reservation_id}%", reservation.TicketID))
            
            # Restore ticket quantity
            cursor.execute("""
                UPDATE dbo.Ticket 
                SET QuantityAvailable = QuantityAvailable + ?
                WHERE TicketID = ?
            """, (reservation.Quantity, reservation.TicketID))
        
        conn.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/complete_reservation/<reservation_id>', methods=['POST'])
def complete_reservation(reservation_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE dbo.TicketReservations 
            SET Status = 'COMPLETED' 
            WHERE ReservationID LIKE ?
        """, (f"{reservation_id}%",))  # Use LIKE to match all related reservations
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)