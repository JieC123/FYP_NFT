from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import pyodbc
from datetime import datetime, date
import os
from werkzeug.utils import secure_filename
import time
import random
import json
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app.utils.db import get_db_connection, allowed_file
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from flask_mail import Message
from app.extensions import mail

user_bp = Blueprint('user', __name__)

@user_bp.route('/')
def index():
    # if 'user_id' not in session:
    #     return redirect(url_for('login'))
    
    # Get featured events from database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # You can modify this query to select featured events based on your criteria
    cursor.execute("""
        SELECT TOP 4 e.*, o.OrganiserName 
        FROM dbo.Event e 
        JOIN dbo.Organiser o ON e.OrganiserID = o.OrganiserID 
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
            'Price': event.EventFee,
            'EventImage': event_image,
        }
        formatted_events.append(formatted_event)
    
    return render_template('index.html', featured_events=formatted_events)

@user_bp.route('/signup', methods=['GET', 'POST'])
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
            """, (user_id, "username", email, '', 'image/user-avatar.png', registration_date, password))
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

@user_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password']

        if not email or not password:
            return jsonify({
                'success': False,
                'message': 'Email and password are required'
            })

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM dbo.TicketingUser WHERE UserEmail = ?", (email,))
            user = cursor.fetchone()

            if user and user.Password == password:
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

@user_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    session.clear()
    return jsonify({
        'success': True,
        'message': 'Logged out successfully',
        'redirect': url_for('login')
    })

@user_bp.route('/forgot-password', methods=['GET', 'POST'])
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
            token = URLSafeTimedSerializer(user_bp.secret_key).dumps(email, salt='password-reset-salt')
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

@user_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = URLSafeTimedSerializer(user_bp.secret_key).loads(token, salt='password-reset-salt', max_age=3600)
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
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE dbo.TicketingUser 
                SET Password = ? 
                WHERE UserEmail = ?
            """, (password, email))
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Your password has been updated! Please login.',
                'redirect': url_for('login')
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': 'An error occurred. Please try again.'
            })
        finally:
            conn.close()
    
    return render_template('resetpass.html', token=token)

@user_bp.route('/eventlist')
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

@user_bp.route('/myticket')
def myticket():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Updated query to ensure we get all unique NFT records
    query = """
    SELECT DISTINCT
        n.TokenID,  -- Include TokenID in selection to ensure uniqueness
        t.TicketID,
        t.EventID,
        t.TicketType,
        t.Price,
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
    LEFT JOIN dbo.Ticket t ON n.TicketID = t.TicketID
    LEFT JOIN dbo.Event e ON t.EventID = e.EventID
    WHERE n.PlatOwnerID = ?
    """
    
    try:
        cursor.execute(query, (session['user_id'],))
        tickets = cursor.fetchall()
        
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
                'EventImage': event_image
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

@user_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        username = request.form['name'].strip()
        phone = request.form['phone'].strip()
        email = request.form['email'].strip()
        file = request.files.get('image')

        if not username or not phone or not email:
            return jsonify({
                'success': False,
                'message': 'All fields are required'
            }), 400

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(user_bp.config['UPLOAD_FOLDER'], filename))
            profile_image = os.path.join('image', filename).replace('\\', '/')  #
        else:
            profile_image = request.form['current_image']

        try:
            cursor.execute("""
                UPDATE dbo.TicketingUser
                SET UserName = ?, UserContactInfo = ?, UserEmail = ?, ProfileImage = ?
                WHERE UserID = ?
            """, (username, phone, email, profile_image, user_id))
            conn.commit()
            return jsonify({
                'success': True,
                'message': 'Profile updated successfully!'
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

@user_bp.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Implement cart logic here
    return render_template('cart.html')

@user_bp.route('/checkout')
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Implement checkout logic here
    return render_template('checkout.html', event={
        'EventTitle': '',  # This will be populated by JavaScript
        'TicketType': ''   # This will be populated by JavaScript
})

@user_bp.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please log in first'}), 401
    
    event_id = request.json.get('event_id')
    quantity = request.json.get('quantity', 1)
    
    # Implement add to cart logic here
    # For now, we'll just return a success message
    return jsonify({'success': True, 'message': 'Added to cart successfully'})

@user_bp.route('/remove-from-cart', methods=['POST'])
def remove_from_cart():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please log in first'}), 401
    
    item_id = request.json.get('item_id')
    
    # Implement remove from cart logic here
    # For now, we'll just return a success message
    return jsonify({'success': True, 'message': 'Removed from cart successfully'})

@user_bp.route('/eventdetail/<string:id>')
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
                'QuantityAvailable': ticket.QuantityAvailable
            })
        
        return render_template('eventdetail.html', event=formatted_event, tickets=formatted_tickets)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Error retrieving event details',
            'redirect': url_for('eventlist')
        }), 500
    finally:
        conn.close()
    
@user_bp.route('/get_contract_data')
def get_contract_data():
    try:
        contract_json_path = os.path.join(user_bp.root_path, 'build', 'contracts', 'Tickets.json')
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

@user_bp.route('/get_nft_data')
def get_nft_data():
    try:
        # Fetch NFT contract details
        contract_json_path = os.path.join(user_bp.root_path, 'build', 'contracts', 'Tickets.json')
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

@user_bp.route('/update_owner', methods=['POST'])
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
            SET QuantityAvailable = QuantityAvailable - ?,
                QuantitySold = QuantitySold + ?
            WHERE TicketID = ? 
        """, (quantity, quantity, ticket_id))
        
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

@user_bp.route('/check_and_get_nft/<string:ticket_id>', methods=['GET'])
def check_and_get_nft(ticket_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Check ticket availability
        cursor.execute("SELECT QuantityAvailable FROM dbo.Ticket WHERE TicketID = ?", (ticket_id,))
        ticket = cursor.fetchone()

        if not ticket or ticket.QuantityAvailable <= 0:
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
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@user_bp.route('/get_ticket_id', methods=['POST'])
def get_ticket_id():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401

    event_title = request.json.get('eventTitle')
    ticket_type = request.json.get('ticketType')

    if not event_title or not ticket_type:
        return jsonify({'error': 'Event title and ticket type are required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Query to get the TicketID and check availability
        cursor.execute("""
            SELECT t.TicketID, t.QuantityAvailable, t.Price
            FROM dbo.Ticket t
            JOIN dbo.Event e ON t.EventID = e.EventID
            WHERE e.EventTitle = ?
            AND t.TicketType = ?
            AND t.QuantityAvailable > 0
        """, (event_title, ticket_type))
        
        ticket = cursor.fetchone()

        if ticket:
            ticket_data = {
                'ticketId': ticket.TicketID,
                'quantityAvailable': ticket.QuantityAvailable,
                'price': float(ticket.Price)  # Convert decimal to float for JSON serialization
            }
            return jsonify(ticket_data)
        else:
            return jsonify({'error': f'No available tickets found for {ticket_type}'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
        
@user_bp.route('/marketplace')
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
                'SellerName': listing.SellerName
            }
            
            formatted_listings.append(formatted_listing)
        
        return render_template('marketplace.html', listings=formatted_listings)
        
    except Exception as e:
        print(f"Error in marketplace route: {str(e)}")
        flash('Error retrieving listings', 'error')
        return redirect(url_for('index'))
    finally:
        conn.close()

@user_bp.route('/list_ticket', methods=['POST'])
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

@user_bp.route('/cancel_listing', methods=['POST'])
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

@user_bp.route('/update_resale_owner', methods=['POST'])
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
            'RESALE',
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

@user_bp.route('/ticket_detail/<string:ticket_id>/<string:token_id>')
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
            'LocalIPFSUrl': f'http://localhost:5001/ipfs/{qr_code_hash}' if qr_code_hash else None
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

@user_bp.route('/insert_order', methods=['POST'])
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

@user_bp.route('/insert_order_item', methods=['POST'])
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

if __name__ == '__main__':
    user_bp.run(debug=True)