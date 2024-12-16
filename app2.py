from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import pyodbc
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import json
import hashlib
import secrets
import time
from cryptography.fernet import Fernet
import qrcode
from io import BytesIO
import ipfshttpclient
from web3 import Web3
import json
import qrcode
import io
from PIL import Image
import base64
import ipfshttpclient
from datetime import datetime
from dotenv import load_dotenv
import aiohttp
import asyncio
from typing import Optional, Tuple, Dict, Any
from flask import Flask, render_template, session, redirect, url_for, flash, g, request
from functools import wraps
from src.controllers.register_controller import register_bp
from src.controllers.login_controller import login_bp
from src.controllers.event_controller import event_bp
from src.controllers.participant_controller import participant_bp
from src.controllers.profile_controller import profile_bp
from src.controllers.eventStaff_controller import event_staff_bp
from src.controllers.sponsorship_controller import sponsorship_bp
from src.controllers.booth_controller import booth_bp
from src.controllers.communication_controller import communication_bp
from src.controllers.resetPassword_controller import reset_password_bp
from src.controllers.sponsorshipAllo_controller import sponsorshipAllo_bp
from src.controllers.budget_simulate_controller import budget_simulate_bp
from src.controllers.boothAllo_controller import boothAllo_bp
from src.controllers.eventStaffAllo_controller import staffAllo_bp
from src.controllers.track_involvement_controller import track_involvement_bp
from src.controllers.budget_controller import budget_bp
from src.controllers.report_controller import report_bp
# from flask_mail import Mail
from config import Config
import logging
from datetime import datetime
import os
from extension import mail
from src.models.login_model import LoginModel


# Load environment variables
load_dotenv()

app = Flask(__name__, template_folder='src/templates', static_folder='src', static_url_path='/static')
app.secret_key = 'your_secret_key_here'

# Modified IPFS setup and MockIPFSClient
class MockIPFSClient:
    def __init__(self):
        self.storage = {}

    def add_bytes(self, content):
        # Generate a deterministic hash for the content
        if isinstance(content, str):
            content = content.encode()
        hash_value = hashlib.sha256(content).hexdigest()[:32]
        self.storage[hash_value] = content
        return hash_value

    def cat(self, hash_value):
        return self.storage.get(hash_value, b'')

class IPFSConnection:
    """Handles connection to IPFS node and basic IPFS operations"""
    def __init__(self):
        self.client = None
        # IPFS Desktop/Local Node Configuration
        self.ipfs_api_endpoint = '/ip4/127.0.0.1/tcp/5001'
        self.ipfs_gateway = 'http://localhost:8080/ipfs'
        self.connect()

    def connect(self):
        try:
            self.client = ipfshttpclient.connect(
                self.ipfs_api_endpoint,
                timeout=30
            )
            print("Successfully connected to local IPFS node")
            return self.client
        except Exception as e:
            print(f"Failed to connect to local IPFS node: {e}")
            print("Using mock IPFS client")
            return MockIPFSClient()

    def add_bytes(self, content):
        try:
            if isinstance(content, str):
                content = content.encode()
            
            if not self.client:
                self.connect()

            result = self.client.add_bytes(content)
            return result['Hash'] if isinstance(result, dict) else result
            
        except Exception as e:
            print(f"Error adding content to IPFS: {e}")
            if isinstance(self.client, MockIPFSClient):
                return self.client.add_bytes(content)
            return None

    async def pin_content(self, ipfs_hash: str) -> bool:
        """Pin content to ensure persistence"""
        try:
            if not isinstance(self.client, MockIPFSClient):
                await self.client.pin.add(ipfs_hash)
            return True
        except Exception as e:
            print(f"Error pinning content: {e}")
            return False

    def get_ipfs_url(self, ipfs_hash: str, use_local: bool = True) -> str:
        """Generate gateway URL for IPFS content"""
        if use_local:
            return f"{self.ipfs_gateway}/{ipfs_hash}"
        return f"{self.public_gateway}/{ipfs_hash}"

    async def cat_file(self, ipfs_hash: str) -> Optional[bytes]:
        """Retrieve content from IPFS"""
        try:
            if not self.client:
                self.connect()
            
            if isinstance(self.client, MockIPFSClient):
                return self.client.cat(ipfs_hash)
                
            return await self.client.cat(ipfs_hash, timeout=self.operation_timeout)
        except Exception as e:
            print(f"Error retrieving file from IPFS: {e}")
            return None

    async def verify_content_availability(self, ipfs_hash: str) -> bool:
        """Verify if content is available in IPFS network"""
        try:
            # Try local gateway first
            async with aiohttp.ClientSession() as session:
                async with session.head(self.get_ipfs_url(ipfs_hash)) as response:
                    return response.status == 200
        except:
            try:
                # Fall back to public gateway
                async with aiohttp.ClientSession() as session:
                    async with session.head(self.get_ipfs_url(ipfs_hash, use_local=False)) as response:
                        return response.status == 200
            except Exception as e:
                print(f"Error verifying content availability: {e}")
                return False

# Initialize IPFS connection
ipfs_connection = IPFSConnection()

# Define the connection string for SQL Server
server = r'LAPTOP-VB12GW\SQLEXPRESS01'
database = 'EventDB'
username = 'user'
password = 'db1234'
driver = '{ODBC Driver 18 for SQL Server}'

# Define the upload folder and allowed extensions
UPLOAD_FOLDER = 'src/image'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize encryption key
ENCRYPTION_KEY = Fernet.generate_key()
fernet = Fernet(ENCRYPTION_KEY)

# Register the blueprints
app.register_blueprint(participant_bp)
app.register_blueprint(register_bp)
app.register_blueprint(login_bp)
app.register_blueprint(event_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(event_staff_bp)
app.register_blueprint(sponsorship_bp)
app.register_blueprint(booth_bp)
app.register_blueprint(reset_password_bp)
app.register_blueprint(communication_bp)
app.register_blueprint(sponsorshipAllo_bp)
app.register_blueprint(budget_simulate_bp)
app.register_blueprint(boothAllo_bp)
app.register_blueprint(staffAllo_bp)
app.register_blueprint(track_involvement_bp)
app.register_blueprint(budget_bp)
app.register_blueprint(report_bp)

# Log the registered routes
with app.app_context():
    logging.basicConfig(level=logging.DEBUG)
    logging.debug('Registered routes:')
    for rule in app.url_map.iter_rules():
        logging.debug(f'{rule.endpoint}: {rule}')

class IPFSManager:
    """Manages high-level IPFS operations for the ticket system"""
    def __init__(self, ipfs_connection: Optional[Any] = None):
        self.ipfs_connection = ipfs_connection or IPFSConnection()
        self.is_mock = isinstance(self.ipfs_connection, MockIPFSClient)

    def generate_qr_code(self, ticket_data: Dict[str, Any]) -> Tuple[Optional[bytes], Optional[Dict[str, Any]]]:
        """Generate QR code for ticket with enhanced data"""
        try:
            # Create QR code instance with better error correction
            qr = qrcode.QRCode(
                version=None,  # Allow automatic version selection
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            
            # Create simplified ticket data structure
            qr_data = {
                'ticketId': str(ticket_data['ticket_id']),  # Ensure string format
                'tokenId': str(ticket_data.get('token_id', '')),  # Ensure string format
                'eventName': str(ticket_data['event_name']),
                'eventDate': str(ticket_data['event_date']),
                'ticketType': str(ticket_data['ticket_type']),
                'venue': str(ticket_data['venue']),
                'price': str(ticket_data['price']),
                'verificationHash': hashlib.sha256(
                    f"{ticket_data['ticket_id']}{ticket_data['event_name']}{datetime.now().isoformat()}".encode()
                ).hexdigest()
            }
            
            # Convert to JSON string
            qr_json = json.dumps(qr_data, ensure_ascii=False)
            
            # Add data to QR code
            qr.add_data(qr_json)
            qr.make(fit=True)
            
            # Create QR code image with higher resolution
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to bytes with higher quality
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            return img_byte_arr.getvalue(), qr_data
            
        except Exception as e:
            print(f"Error generating QR code: {e}")
            return None, None

    def create_ticket_metadata(self, ticket_data: Dict[str, Any], qr_hash: str) -> Optional[Dict[str, Any]]:
        """Create metadata JSON for the ticket"""
        try:
            return {
                "name": f"{ticket_data['event_name']} - {ticket_data['ticket_type']}",
                "description": f"Official NFT ticket for {ticket_data['event_name']}",
                "image": f"ipfs://{qr_hash}",
                "attributes": {
                    "eventName": ticket_data['event_name'],
                    "eventDate": ticket_data['event_date'],
                    "ticketType": ticket_data['ticket_type'],
                    "venue": ticket_data['venue'],
                    "price": ticket_data['price'],
                    "qrHash": qr_hash,
                    "issueDate": datetime.now().isoformat()
                }
            }
        except Exception as e:
            print(f"Error creating metadata: {e}")
            return None

    def __init__(self, ipfs_connection):
        self.ipfs_connection = ipfs_connection
        self.is_mock = isinstance(self.ipfs_connection.client, MockIPFSClient)

    def upload_to_ipfs(self, content):
        try:
            if isinstance(content, str):
                content = content.encode()
            
            result = self.ipfs_connection.add_bytes(content)
            return result
            
        except Exception as e:
            print(f"IPFS upload error: {e}")
            mock_hash = hashlib.sha256(content).hexdigest()[:32]
            return f"mock-{mock_hash}"

    async def process_ticket_data(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process ticket data and create NFT assets"""
        try:
            # Generate QR code
            qr_bytes, qr_data = self.generate_qr_code(ticket_data)
            if not qr_bytes or not qr_data:
                raise Exception("Failed to generate QR code")

            # Upload QR code to IPFS
            qr_hash = await self.upload_to_ipfs(qr_bytes)
            if not qr_hash:
                raise Exception("Failed to upload QR code to IPFS")

            # Create and upload metadata
            metadata = self.create_ticket_metadata(ticket_data, qr_hash)
            if not metadata:
                raise Exception("Failed to create metadata")

            metadata_hash = await self.upload_to_ipfs(
                json.dumps(metadata).encode(),
                is_json=True
            )
            if not metadata_hash:
                raise Exception("Failed to upload metadata to IPFS")

            # Convert QR code to base64 for immediate display
            qr_base64 = base64.b64encode(qr_bytes).decode('utf-8')

            return {
                'qrHash': qr_hash,
                'metadataHash': metadata_hash,
                'qrBase64': qr_base64,
                'metadata': metadata,
                'qrData': qr_data
            }

        except Exception as e:
            print(f"Error processing ticket data: {e}")
            raise

    async def verify_ticket_assets(self, qr_hash: str, metadata_hash: str) -> bool:
        """Verify that all ticket assets are available in IPFS"""
        try:
            qr_available = await self.ipfs_connection.verify_content_availability(qr_hash)
            metadata_available = await self.ipfs_connection.verify_content_availability(metadata_hash)
            return qr_available and metadata_available
        except Exception as e:
            print(f"Error verifying ticket assets: {e}")
            return False

def get_db_connection():
    conn = pyodbc.connect(f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password};Trusted_Connection=yes;Encrypt=no')
    return conn

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# @app.route('/')
# def organiser_dashboard():
#     if 'organiser_id' not in session:
#         return redirect(url_for('organiser_login'))
#     return redirect(url_for('ticket_management'))  # Redirect to ticket management page
# Define routes for the pages
@app.route('/')
def home():
    return render_template('Orglogin.html')

@app.route('/login', methods=['GET', 'POST'])
def organiser_login():
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password']

        if not email or not password:
            flash('Email and password are required', 'error')
            return redirect(url_for('organiser_login'))

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM dbo.Organiser WHERE OrganiserEmail = ?", (email,))
            organiser = cursor.fetchone()

            if organiser and organiser.Password == password:
                session['organiser_id'] = organiser.OrganiserID
                session['organiser_name'] = organiser.OrganiserName
                # flash('Login successful!', 'success')
                return redirect(url_for('ticket_management'))  # Redirect to ticket management page
            else:
                # flash('Invalid email or password', 'error')
                return redirect(url_for('organiser_login'))
        except Exception as e:
            # flash(f'An error occurred: {e}', 'error')
            return redirect(url_for('organiser_login'))
        finally:
            conn.close()

    return render_template('org_login.html')

app.config.from_object(Config)
mail.init_app(app)


@app.before_request
def before_request():
    if 'organiser_id' in session:
        organiser_id = session['organiser_id']
        organiser_name = LoginModel.get_user_by_id(organiser_id)  # Fetch name from DB
        g.organiser_name = organiser_name  # Store organiser's name in g
    else:
        g.organiser_name = None



@app.template_filter('to_datetime_local')
def to_datetime_local(value):
    if value:
        return value.strftime('%Y-%m-%dT%H:%M')  # Format as 'YYYY-MM-DDTHH:MM'
    return ''


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:  # Adjust key based on your session data
            flash("Please log in to access this page.", "danger")
            return redirect(url_for("login.login"))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/events')
@login_required
def org_view_event():
    return render_template('OrgViewEvent.html')

# Add additional routes
@app.route('/OrgViewParticipant')
def org_view_participant():
    return render_template('OrgViewParticipant.html')

@app.route('/OrgViewSponsorship')
def org_view_sponsorship():
    return render_template('OrgViewSponsorship.html')

@app.route('/OrgViewBooth')
def org_view_booth():
    return render_template('OrgViewBooth.html')

@app.route('/OrgViewStaff')
def org_view_staff():
    return render_template('OrgViewStaff.html')

@app.route('/OrgEventBudget')
def org_event_budget():
    return render_template('OrgEventBudget.html')

@app.route('/EventSummaryReport')
def event_summary_report():
    return render_template('EventSummaryReport.html')

@app.route('/StaffAllocationReport')
def staff_allocation_report():
    return render_template('StaffAllocationReport.html')

@app.route('/ExhibitorAllocationReport')
def exhibitor_allocation_report():
    return render_template('ExhibitorAllocationReport.html')

@app.route('/OrgProfile')
def org_profile():
    return render_template('OrgProfile.html')

@app.route('/edit-profile')
def edit_profile():
    return render_template('OrgEditProfile.html')

@app.route('/email')
def email_communicate():
    return render_template('EmailCommunication.html')

# @app.route('/viewTheAllo')
# def view_Allo():
#     return render_template('ViewAlloStaff.html')


@app.route('/OrgAddBudget')
def AddBudget():
    return render_template('OrgAddBudget.html')

@app.route('/viewTheAllo2')
def view_Allo2():
    return render_template('ViewAlloParticipant.html')

# @app.route('/viewTheAllo3')
# def view_Allo3():
#     return render_template('ViewAlloSponsor.html')
# @app.route('/viewTheAllo4')
# def view_Allo4():
#     return render_template('ViewAlloBooth.html')

# @app.route('/BudgetSimulation')
# def budgetSimulation():
#     return render_template('BudgetSimulation.html')

# @app.route('/OrgAlloSponsorship')
# def org_allo_sponsorship():
#     return render_template('OrgAlloSponsorship.html')

# @app.route('/OrgAlloBooth')
# def org_allo_sponsorship():
#     return render_template('OrgAlloBooth.html')


# @app.route('/OrgAlloStaff')
# def org_allo_sponsorship():
#     return render_template('OrgAlloStaff.html')


@app.route('/logout')
def logout():
    session.clear()  
    return render_template('Orglogin.html')

@app.route('/order_management')
def order_management():
    if 'organiser_id' not in session:
        return redirect(url_for('organiser_login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Simplified query without item details
        query = """
        SELECT DISTINCT
            t.TransactionID,
            t.TransactionType,
            t.TransactionHash,
            t.TransactionTime,
            t.Status,
            o.OrderID,
            o.UserID,
            o.OrderDate,
            o.TotalAmount
        FROM dbo.TransactionHistory t
        JOIN dbo.[Orders] o ON t.OrderID = o.OrderID
        JOIN dbo.OrderItems oi ON oi.OrderID = o.OrderID
        JOIN dbo.Ticket tk ON oi.TicketID = tk.TicketID
        JOIN dbo.Event e ON tk.EventID = e.EventID
        WHERE t.TransactionType = 'PURCHASE'
        AND e.OrganiserID = ?
        ORDER BY t.TransactionTime DESC
        """
    
        cursor.execute(query, (session['organiser_id'],))
        transactions = cursor.fetchall()
        
        transactions_list = []
        for transaction in transactions:
            transaction_dict = {
                'TransactionID': transaction.TransactionID,
                'TransactionType': transaction.TransactionType,
                'TransactionHash': transaction.TransactionHash,
                'TransactionTime': transaction.TransactionTime,
                'Status': transaction.Status,
                'OrderID': transaction.OrderID,
                'UserID': transaction.UserID,
                'OrderDate': transaction.OrderDate,
                'TotalAmount': transaction.TotalAmount
            }
            transactions_list.append(transaction_dict)
        
        return render_template('order_management.html', transactions=transactions_list)
    except Exception as e:
        print(f'An error occurred: {e}')
        flash(f'An error occurred: {e}', 'error')
        return redirect(url_for('organiser_login'))
    finally:
        conn.close()

@app.route('/smart_contract_management')
def smart_contract_management():
    if 'organiser_id' not in session:
        return redirect(url_for('organiser_login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Fetch pending tickets (IsNFT != 'Yes') for the logged-in organizer
        query = """
        SELECT t.*, e.EventTitle, e.EventVenue, e.EventStartDate
        FROM dbo.Ticket t
        JOIN dbo.Event e ON t.EventID = e.EventID
        WHERE e.OrganiserID = ? AND t.IsNFT != 'Yes'
        """
    
        cursor.execute(query, (session['organiser_id'],))
        pending_tickets = cursor.fetchall()
        
        # Convert row objects to dictionaries for easier handling in the template
        pending_tickets = [dict(zip([column[0] for column in cursor.description], row)) for row in pending_tickets]
        
        return render_template('smart_contract_management.html', pending_tickets=pending_tickets)
    except Exception as e:
        print(f'An error occurred: {e}')
        flash(f'An error occurred: {e}', 'error')
        return redirect(url_for('organiser_dashboard'))
    finally:
        conn.close()

@app.route('/order_detail/<transaction_id>')
def order_detail(transaction_id):
    if 'organiser_id' not in session:
        return redirect(url_for('organiser_login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get transaction and order details
        query = """
        SELECT 
            t.TransactionID,
            t.TransactionType,
            t.TransactionHash,
            t.TransactionTime as OrderDate,
            t.Status as TransactionStatus,
            o.OrderID,
            o.UserID,
            o.TotalAmount,
            u.UserName,
            u.UserEmail,
            u.UserContactInfo
        FROM dbo.TransactionHistory t
        JOIN dbo.[Orders] o ON t.OrderID = o.OrderID
        JOIN dbo.TicketingUser u ON o.UserID = u.UserID
        WHERE t.TransactionID = ?
        """
        
        cursor.execute(query, (transaction_id,))
        transaction = cursor.fetchone()
        
        # Get order items
        items_query = """
        SELECT 
            oi.TicketID,
            oi.Quantity,
            oi.Price,
            oi.TokenID,
            t.TicketType,
            e.EventTitle
        FROM dbo.OrderItems oi
        JOIN dbo.Ticket t ON oi.TicketID = t.TicketID
        JOIN dbo.Event e ON t.EventID = e.EventID
        WHERE oi.OrderID = ?
        """
        
        cursor.execute(items_query, (transaction.OrderID,))
        items = cursor.fetchall()
        
        # Convert to dictionary
        transaction_dict = {
            'TransactionID': transaction.TransactionID,
            'TransactionType': transaction.TransactionType,
            'TransactionHash': transaction.TransactionHash,
            'OrderDate': transaction.OrderDate,
            'TransactionStatus': transaction.TransactionStatus,
            'OrderID': transaction.OrderID,
            'UserID': transaction.UserID,
            'TotalAmount': transaction.TotalAmount,
            'UserName': transaction.UserName,
            'UserEmail': transaction.UserEmail,
            'UserContactInfo': transaction.UserContactInfo,
            'PaymentMethod': 'Metamask - Ethereum (ETH)',
            'Items': [{
                'EventTitle': item.EventTitle,
                'TicketType': item.TicketType,
                'TokenID': item.TokenID,
                'Quantity': item.Quantity,
                'Price': item.Price,
                'Subtotal': item.Price * item.Quantity
            } for item in items]
        }
        
        return render_template('order_detail.html', transaction=transaction_dict)
            
    except Exception as e:
        print(f'An error occurred: {e}')
        flash(f'An error occurred: {e}', 'error')
        return redirect(url_for('order_management'))
    finally:
        conn.close()

@app.route('/create_ticket', methods=['GET', 'POST'])
def create_ticket():
    print("Create ticket function called")  # Debug print
    if 'organiser_id' not in session:
        print("No organiser_id in session")  # Debug print
        return redirect(url_for('organiser_login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        print("POST request received")  # Debug print
        print("Form data:", request.form)  # Debug print
        event_id = request.form['event-id']
        ticket_type = request.form['ticket-type']
        ticket_price = request.form['ticket-price']
        ticket_quantity = request.form['ticket-quantity']

        print(f"Received data: event_id={event_id}, ticket_type={ticket_type}, ticket_price={ticket_price}, ticket_quantity={ticket_quantity}")  # Debug print

        try:
            # Generate new TicketID
            cursor.execute("SELECT TOP 1 TicketID FROM dbo.Ticket ORDER BY TicketID DESC")
            last_ticket = cursor.fetchone()
            if last_ticket:
                last_id = int(last_ticket.TicketID[2:])
                new_id = f"ET{last_id + 1:06}"
            else:
                new_id = "ET000001"

            cursor.execute("""
                INSERT INTO dbo.Ticket (TicketID, EventID, TicketType, Price, QuantityAvailable, QuantitySold, IsNFT, CreateDate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (new_id, event_id, ticket_type, ticket_price, ticket_quantity, 0, 'No', datetime.now().date()))
            conn.commit()
            flash('Ticket created successfully!', 'success')
            return redirect(url_for('ticket_management'))
        except Exception as e:
            flash(f'An error occurred: {e}', 'error')
            print(f'An error occurred: {e}')
            return redirect(url_for('create_ticket'))
        finally:
            conn.close()

    # Fetch events for the dropdown
    cursor.execute("SELECT * FROM dbo.Event WHERE OrganiserID = ?", (session['organiser_id'],))
    events = cursor.fetchall()
    events = [dict(zip([column[0] for column in cursor.description], event)) for event in events]

    return render_template('create_ticket.html', events=events)

@app.route('/track_sales')
def track_sales():
    if 'organiser_id' not in session:
        return redirect(url_for('organiser_login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get summary data for the current week
        cursor.execute("""
            SELECT 
                COALESCE(SUM(o.TotalAmount), 0) as TotalSales,
                COUNT(DISTINCT o.OrderID) as NewOrders,
                COUNT(DISTINCT e.EventID) as NumberOfEvents,
                COUNT(DISTINCT o.UserID) as NewCustomers
            FROM dbo.Orders o
            JOIN dbo.OrderItems oi ON o.OrderID = oi.OrderID
            JOIN dbo.Ticket t ON oi.TicketID = t.TicketID
            JOIN dbo.Event e ON t.EventID = e.EventID
            WHERE e.OrganiserID = ?
            AND o.OrderDate >= DATEADD(day, -7, GETDATE())
        """, (session['organiser_id'],))
        
        summary_row = cursor.fetchone()
        summary = {
            'TotalSales': float(summary_row[0] or 0),
            'NewOrders': int(summary_row[1] or 0),
            'NumberOfEvents': int(summary_row[2] or 0),
            'NewCustomers': int(summary_row[3] or 0)
        }
        
        # Get daily sales for the past week
        cursor.execute("""
            SELECT 
                CAST(o.OrderDate AS DATE) as OrderDate,
                COALESCE(SUM(o.TotalAmount), 0) as DailySales
            FROM dbo.Orders o
            JOIN dbo.OrderItems oi ON o.OrderID = oi.OrderID
            JOIN dbo.Ticket t ON oi.TicketID = t.TicketID
            JOIN dbo.Event e ON t.EventID = e.EventID
            WHERE e.OrganiserID = ?
            AND o.OrderDate >= DATEADD(day, -7, GETDATE())
            GROUP BY CAST(o.OrderDate AS DATE)
            ORDER BY OrderDate
        """, (session['organiser_id'],))
        
        daily_sales = []
        for row in cursor.fetchall():
            daily_sales.append({
                'OrderDate': row[0].isoformat(),
                'DailySales': float(row[1] or 0)
            })
        
        # Modified query to get event sales data with ticket types
        cursor.execute("""
            SELECT 
                e.EventID,
                e.EventTitle,
                t.TicketType,
                COUNT(DISTINCT o.OrderID) as OrderCount,
                COALESCE(SUM(o.TotalAmount), 0) as TotalRevenue,
                COALESCE(SUM(t.QuantitySold), 0) as TotalSold,
                COALESCE(SUM(t.QuantityAvailable + t.QuantitySold), 0) as TotalCapacity
            FROM dbo.Event e
            LEFT JOIN dbo.Ticket t ON e.EventID = t.EventID
            LEFT JOIN dbo.OrderItems oi ON t.TicketID = oi.TicketID
            LEFT JOIN dbo.Orders o ON oi.OrderID = o.OrderID
            WHERE e.OrganiserID = ?
            GROUP BY e.EventID, e.EventTitle, t.TicketType
        """, (session['organiser_id'],))
        
        event_sales = []
        for row in cursor.fetchall():
            event_sales.append({
                'EventID': str(row[0]),
                'EventTitle': row[1],
                'TicketType': row[2],
                'OrderCount': int(row[3] or 0),
                'TotalRevenue': float(row[4] or 0),
                'TotalSold': int(row[5] or 0),
                'TotalCapacity': int(row[6] or 0)
            })

        # Calculate percentage changes (using current week vs previous week)
        cursor.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN o.OrderDate >= DATEADD(day, -7, GETDATE()) THEN o.TotalAmount ELSE 0 END), 0) as ThisWeekSales,
                COALESCE(SUM(CASE WHEN o.OrderDate >= DATEADD(day, -14, GETDATE()) AND o.OrderDate < DATEADD(day, -7, GETDATE()) THEN o.TotalAmount ELSE 0 END), 0) as LastWeekSales,
                COUNT(DISTINCT CASE WHEN o.OrderDate >= DATEADD(day, -7, GETDATE()) THEN o.OrderID END) as ThisWeekOrders,
                COUNT(DISTINCT CASE WHEN o.OrderDate >= DATEADD(day, -14, GETDATE()) AND o.OrderDate < DATEADD(day, -7, GETDATE()) THEN o.OrderID END) as LastWeekOrders
            FROM dbo.Orders o
            JOIN dbo.OrderItems oi ON o.OrderID = oi.OrderID
            JOIN dbo.Ticket t ON oi.TicketID = t.TicketID
            JOIN dbo.Event e ON t.EventID = e.EventID
            WHERE e.OrganiserID = ?
        """, (session['organiser_id'],))
        
        changes_row = cursor.fetchone()
        this_week_sales = float(changes_row[0] or 0)
        last_week_sales = float(changes_row[1] or 0)
        this_week_orders = int(changes_row[2] or 0)
        last_week_orders = int(changes_row[3] or 0)
        
        sales_change = ((this_week_sales - last_week_sales) / last_week_sales * 100) if last_week_sales > 0 else 0
        orders_change = ((this_week_orders - last_week_orders) / last_week_orders * 100) if last_week_orders > 0 else 0

        return render_template('track_sales.html',
                             summary=summary,
                             daily_sales=daily_sales,
                             event_sales=json.dumps(event_sales),
                             sales_change=sales_change,
                             orders_change=orders_change)
                             
    except Exception as e:
        print(f'An error occurred: {e}')
        flash(f'An error occurred: {e}', 'error')
        return redirect(url_for('organiser_dashboard'))
    finally:
        conn.close()


@app.route('/update_ticket/<ticket_id>', methods=['GET'])
def edit_ticket(ticket_id):
    if 'organiser_id' not in session:
        return redirect(url_for('organiser_login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM dbo.Ticket WHERE TicketID = ?", (ticket_id,))
        ticket = cursor.fetchone()
        
        cursor.execute("SELECT * FROM dbo.Event WHERE OrganiserID = ?", (session['organiser_id'],))
        events = cursor.fetchall()
        
        if ticket:
            events = [dict(zip([column[0] for column in cursor.description], event)) for event in events]
            print(ticket)  # Debug print
            print(events)  # Debug print
            return render_template('update_ticket.html', ticket=ticket, events=events)
        else:
            flash('Ticket not found', 'error')
            return redirect(url_for('ticket_management'))
    except Exception as e:
        print(f'An error occurred: {e}')
        flash(f'An error occurred: {e}', 'error')
        return redirect(url_for('ticket_management'))
    finally:
        conn.close()

@app.route('/update_ticket/<ticket_id>', methods=['POST'])
def update_ticket(ticket_id):
    if 'organiser_id' not in session:
        return redirect(url_for('organiser_login'))

    event_id = request.form['event-id']
    ticket_type = request.form['ticket-type']
    ticket_price = request.form['ticket-price']
    ticket_quantity = request.form['ticket-quantity']
    
    
    if not event_id or not ticket_type or not ticket_price or not ticket_quantity:
        flash('All fields are required', 'error')
        return redirect(url_for('edit_ticket', ticket_id=ticket_id))
    # ticket_description = request.form['ticket-description']
    # ticket_image = request.files['ticket-image']

    # filename = None
    # if ticket_image and allowed_file(ticket_image.filename):
    #     filename = secure_filename(ticket_image.filename)
    #     ticket_image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
            
        cursor.execute("""
        UPDATE dbo.Ticket
        SET EventID = ?, TicketType = ?, Price = ?, QuantityAvailable = ?
        WHERE TicketID = ?
        """, (event_id, ticket_type, ticket_price, ticket_quantity, ticket_id))
        
        conn.commit()
        flash('Ticket updated successfully!', 'success')
        return redirect(url_for('ticket_management'))
    except Exception as e:
        print(f'An error occurred: {e}')
        flash(f'An error occurred: {e}', 'error')
        return redirect(url_for('edit_ticket', ticket_id=ticket_id))
    finally:
        conn.close()

@app.route('/ticket_management')
def ticket_management():
    if 'organiser_id' not in session:
        return redirect(url_for('organiser_login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Fetch tickets for the logged-in organizer
        query = """
        SELECT t.*, e.EventTitle, e.EventVenue, e.EventStartDate, e.EventEndDate
        FROM dbo.Ticket t
        JOIN dbo.Event e ON t.EventID = e.EventID
        WHERE e.OrganiserID = ?
        """
    
        cursor.execute(query, (session['organiser_id'],))
        tickets = cursor.fetchall()
        
        # Convert row objects to dictionaries for easier handling in the template
        tickets = [dict(zip([column[0] for column in cursor.description], row)) for row in tickets]
        
        return render_template('ticket_management.html', tickets=tickets)
    except Exception as e:
        # Log the error for debugging
        print(f'An error occurred: {e}')
        flash(f'An error occurred: {e}', 'error')
        return redirect(url_for('organiser_dashboard'))
    finally:
        conn.close()

@app.route('/event_management')
def event_management():
    if 'organiser_id' not in session:
        return redirect(url_for('organiser_login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Fetch events for the logged-in organizer
        query = """
        SELECT *
        FROM dbo.Event
        WHERE OrganiserID = ?
        """
    
        cursor.execute(query, (session['organiser_id'],))
        events = cursor.fetchall()
        
        # Convert row objects to dictionaries for easier handling in the template
        events = [dict(zip([column[0] for column in cursor.description], row)) for row in events]
        
        return render_template('event_management.html', events=events)
    except Exception as e:
        print(f'An error occurred: {e}')
        flash(f'An error occurred: {e}', 'error')
        return redirect(url_for('organiser_dashboard'))
    finally:
        conn.close()

@app.route('/create_event', methods=['GET', 'POST'])
def create_event():
    if 'organiser_id' not in session:
        return redirect(url_for('organiser_login'))

    if request.method == 'POST':
        event_title = request.form['event-title']
        event_description = request.form['event-description']
        event_start_date = request.form['event-start-date']
        event_end_date = request.form['event-end-date']
        event_venue = request.form['event-venue']
        event_capacity = request.form['event-capacity']

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Generate new EventID
            cursor.execute("SELECT TOP 1 EventID FROM dbo.Event ORDER BY EventID DESC")
            last_event = cursor.fetchone()
            if last_event:
                last_id = int(last_event.EventID[2:])
                new_id = f"EV{last_id + 1:06}"
            else:
                new_id = "EV000001"

            cursor.execute("""
                INSERT INTO dbo.Event (EventID, OrganiserID, EventTitle, EventDescription, EventStartDate, EventEndDate, EventVenue, EventCapacity, EventStatus)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (new_id, session['organiser_id'], event_title, event_description, event_start_date, event_end_date, event_venue, event_capacity, 'Upcoming'))
            conn.commit()
            flash('Event created successfully!', 'success')
            return redirect(url_for('event_management'))
        except Exception as e:
            flash(f'An error occurred: {e}', 'error')
            return redirect(url_for('create_event'))
        finally:
            conn.close()

    return render_template('create_event.html')

@app.route('/edit_event/<event_id>', methods=['GET', 'POST'])
def edit_event(event_id):
    if 'organiser_id' not in session:
        return redirect(url_for('organiser_login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        event_title = request.form['event-title']
        event_description = request.form['event-description']
        event_start_date = request.form['event-start-date']
        event_end_date = request.form['event-end-date']
        event_venue = request.form['event-venue']
        event_capacity = request.form['event-capacity']
        event_status = request.form['event-status']

        try:
            cursor.execute("""
                UPDATE dbo.Event
                SET EventTitle = ?, EventDescription = ?, EventStartDate = ?, EventEndDate = ?, EventVenue = ?, EventCapacity = ?, EventStatus = ?
                WHERE EventID = ? AND OrganiserID = ?
            """, (event_title, event_description, event_start_date, event_end_date, event_venue, event_capacity, event_status, event_id, session['organiser_id']))
            conn.commit()
            flash('Event updated successfully!', 'success')
            return redirect(url_for('event_management'))
        except Exception as e:
            flash(f'An error occurred: {e}', 'error')
        finally:
            conn.close()

@app.route('/participant_management')
def participant_management():
    if 'organiser_id' not in session:
        return redirect(url_for('organiser_login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Fetch participants for the logged-in organizer's events
        query = """
        SELECT 
            p.UserID,
            tu.UserName,
            tu.UserEmail,
            tu.UserContactInfo,
            p.RegistrationDate,
            e.EventID,
            e.EventTitle
        FROM 
            Participant p
        JOIN 
            TicketingUser tu ON p.UserID = tu.UserID
        JOIN 
            Event e ON p.EventID = e.EventID
        WHERE 
            e.OrganiserID = ?
        """
    
        cursor.execute(query, (session['organiser_id'],))
        participants = cursor.fetchall()
        
        print(participants)
        print("testing")
        print(session['organiser_id'])
        
        # Convert row objects to dictionaries for easier handling in the template
        # participants = [dict(zip([column[0] for column in cursor.description], row)) for row in participants]
        
        return render_template('part_management.html', participants=participants)
    except Exception as e:
        print(f'An error occurred: {e}')
        flash(f'An error occurred: {e}', 'error')
        return redirect(url_for('organiser_dashboard'))
    finally:
        conn.close()

@app.route('/delete_ticket/<ticket_id>')
def delete_ticket(ticket_id):
    if 'organiser_id' not in session:
        return redirect(url_for('organiser_login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # First check if the ticket belongs to the logged-in organizer
        cursor.execute("""
            SELECT t.TicketID
            FROM Ticket t
            JOIN Event e ON t.EventID = e.EventID
            WHERE t.TicketID = ? AND e.OrganiserID = ?
        """, (ticket_id, session['organiser_id']))
        
        if cursor.fetchone() is None:
            return jsonify({
                'success': False,
                'message': 'You do not have permission to delete this ticket.'
            })
        
        # Check if there are any NFT records associated with this ticket
        cursor.execute("""
            SELECT COUNT(*) as nft_count
            FROM NFT
            WHERE TicketID = ?
        """, (ticket_id,))
        
        nft_count = cursor.fetchone()[0]
        
        if nft_count > 0:
            return jsonify({
                'success': False,
                'message': f'Cannot delete this ticket as it has {nft_count} NFT(s) associated with it. Please ensure all NFTs are transferred or burned before deleting the ticket.'
            })
        
        # If no NFTs exist, proceed with deletion
        cursor.execute("DELETE FROM Ticket WHERE TicketID = ?", (ticket_id,))
        conn.commit()
        return jsonify({
            'success': True,
            'message': 'Ticket deleted successfully.'
        })
        
    except Exception as e:
        conn.rollback()
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })
    finally:
        conn.close()
    
    return redirect(url_for('ticket_management'))

@app.route('/get_contract_data')
def get_contract_data():
    contract_json_path = os.path.join(app.root_path, 'build', 'contracts', 'Tickets.json')
    with open(contract_json_path, 'r') as file:
        contract_data = json.load(file)
    
    # Get the network ID (you may need to adjust this based on your setup)
    network_id = '5777'  # This is typically the default for local development networks
    
    abi = contract_data['abi']
    address = contract_data['networks'][network_id]['address']
    
    return jsonify({'abi': abi, 'address': address})

@app.route('/update_ticket_nft_status', methods=['POST'])
def update_ticket_nft_status():
    data = request.json
    ticket_id = data['ticketId']
    quantity = data['quantity']

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Update the ticket status to NFT
        cursor.execute("""
            UPDATE dbo.Ticket
            SET IsNFT = 'Yes'
            WHERE TicketID = ?
        """, (ticket_id))
        conn.commit()
        return jsonify({'success': True, 'message': 'Ticket status updated successfully'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/create_nfts', methods=['POST'])
def create_nfts():
    data = request.json
    ticket_id = data['ticketId']
    token_ids = data['tokenIds']
    blockchain_tx_id = data['blockchainTxId']
    owner_id = data['ownerId']

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT TOP 1 NFTID FROM NFT ORDER BY NFTID DESC")
        last_nft_id = cursor.fetchone()
        
        if last_nft_id:
            last_nft_number = int(last_nft_id[0][3:])
        else:
            last_nft_number = 0

        for i, token_id in enumerate(token_ids):
            nft_id = f"NFT{(last_nft_number + i + 1):05d}"
            cursor.execute("""
                INSERT INTO NFT (NFTID, TicketID, TokenID, BlockchainTxID, OwnerID, CreateDate)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (nft_id, ticket_id, token_id, blockchain_tx_id, owner_id, datetime.now()))

        cursor.execute("""
            UPDATE dbo.Ticket
            SET IsNFT = 'Yes', QuantityAvailable = QuantityAvailable - ?
            WHERE TicketID = ?
        """, (len(token_ids), ticket_id))

        conn.commit()
        return jsonify({'success': True, 'message': 'NFTs created successfully'})
    except Exception as e:
        print("Error:", e)  # Debugging line
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/get_event_image/<ticket_id>')
def get_event_image(ticket_id):
    # Query your database to get the event image URL for the given ticket_id
    # Return JSON response with the image URL
    return jsonify({
        'imageUrl': 'https://postimg.cc/p5fmvrc4'
    })

@app.route('/mintNFT', methods=['POST'])
async def mint_nft():
    try:
        data = request.json
        ticket_id = data['ticketId']
        token_ids = data['tokenIds']
        blockchain_tx_id = data['blockchainTxId']
        quantity = int(data['quantity'])
        metadata_info = data.get('metadataInfo', [])
        owner_id = data.get('ownerId', '0x660c01ffc99a691e4186d529134ae6963aa0d3f8')

        conn = get_db_connection()
        cursor = conn.cursor()

        # Get last NFT ID
        cursor.execute("SELECT TOP 1 NFTID FROM NFT ORDER BY NFTID DESC")
        last_nft_id = cursor.fetchone()
        last_nft_number = int(last_nft_id[0][3:]) if last_nft_id else 0

        # Convert token_ids to list if it's not already
        if not isinstance(token_ids, list):
            token_ids = [token_ids]

        for i, token_id in enumerate(token_ids):
            try:
                print(f"Processing token {i+1}: {token_id}")  # Debug print
                nft_id = f"NFT{(last_nft_number + i + 1):05d}"
                
                # Check if NFT already exists
                cursor.execute("""
                    SELECT COUNT(*) FROM NFT 
                    WHERE TokenID = ? AND TicketID = ?
                """, (str(token_id), ticket_id))
                
                count = cursor.fetchone()[0]
                print(f"Existing NFT count for token {token_id}: {count}")  # Debug print
                
                if count == 0:
                    # Ensure all values are properly formatted
                    insert_values = (
                        nft_id,                          # NFTID
                        ticket_id,                       # TicketID
                        str(token_id),                   # TokenID (as string)
                        blockchain_tx_id,                # BlockchainTxID
                        owner_id,                        # OwnerID
                        datetime.now(),                  # CreateDate
                        session['organiser_id'],         # PlatOwnerID
                        f"ipfs://{metadata_info[i]['metadataHash']}",# MetadataURI
                        f"ipfs://{metadata_info[i]['qrHash']}",      # QRCodeURI
                        metadata_info[i]['verificationHash'] # VerificationHash
                    )

                    print(f"Inserting NFT with values: {insert_values}")  # Debug print
                    
                    cursor.execute("""
                        INSERT INTO NFT (
                            NFTID, TicketID, TokenID, BlockchainTxID, 
                            OwnerID, CreateDate, PlatOwnerID, MetadataURI, 
                            QRCodeURI, VerificationHash
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, insert_values)
                    
                    print(f"Successfully inserted NFT {nft_id}")  # Debug print
                else:
                    print(f"Skipping duplicate NFT for token {token_id}")  # Debug print

            except Exception as e:
                print(f"Error processing NFT {i+1}: {e}")
                print(f"Token ID: {token_id}")
                print(f"Metadata info for index {i}: {metadata_info[i]}")
                continue

        # After the loop
        print("Loop completed")

        # Update ticket quantity
        cursor.execute("""
            UPDATE dbo.Ticket
            SET IsNFT = 'Yes'
            WHERE TicketID = ?
        """, (ticket_id))

        conn.commit()
        return jsonify({
            'success': True,
            'message': f'Successfully minted {len(token_ids)} NFTs'
        })

    except Exception as e:
        print(f"Error minting NFT: {e}")
        if 'conn' in locals():
            conn.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/get_ticket_metadata/<ticket_id>')
async def get_ticket_metadata(ticket_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT n.MetadataURI, n.QRCodeURI
            FROM NFT n
            WHERE n.TicketID = ?
        """, (ticket_id,))
        nft_data = cursor.fetchone()
        
        if not nft_data:
            return jsonify({'success': False, 'message': 'NFT not found'}), 404
            
        return jsonify({
            'success': True,
            'metadataURI': nft_data.MetadataURI,
            'qrCodeURI': nft_data.QRCodeURI
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()
        
@app.route('/scan-ticket')
def scan_ticket():
    return render_template('verify_ticket.html')

def generate_qr_code(self, ticket_info):
    try:
        # Create QR code instance with better error correction
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        
        # Get numeric token ID (assuming it's the number after underscore)
        string_token_id = ticket_info['token_id']  # e.g., "ET000015_3"
        numeric_token_id = string_token_id.split('_')[1]  # e.g., "3"
        
        # Create comprehensive ticket data
        qr_data = {
            'ticketId': ticket_info['ticket_id'],
            'tokenId': string_token_id,  # Keep original format for display
            'numericTokenId': numeric_token_id,  # Add numeric version for contract
            'eventName': ticket_info['event_name'],
            'eventDate': ticket_info['event_date'],
            'ticketType': ticket_info['ticket_type'],
            'venue': ticket_info['venue'],
            'price': str(ticket_info['price']),
            'timestamp': datetime.now().isoformat(),
            'verificationHash': hashlib.sha256(
                f"{ticket_info['ticket_id']}{string_token_id}{datetime.now().isoformat()}".encode()
            ).hexdigest()
        }
        
        # Add data to QR code
        qr.add_data(json.dumps(qr_data))
        qr.make(fit=True)
        
        # Create QR code image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        return img_byte_arr.getvalue(), qr_data
        
    except Exception as e:
        print(f"Error generating QR code: {e}")
        return None, None

def run_async(app):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(app)

@app.route('/generateNFTMetadata', methods=['POST'])
async def generate_nft_metadata():
    try:
        data = request.json
        ticket_id = data['ticketId']
        quantity = int(data['quantity'])
        # Get token IDs from the request
        token_ids = data.get('tokenIds', [])  # This will be passed from the frontend
        
        if not token_ids or len(token_ids) != quantity:
            return jsonify({
                'success': False,
                'message': 'Missing or invalid token IDs from blockchain'
            }), 400
        
        # Fetch ticket details from database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.*, e.EventTitle, e.EventVenue, e.EventStartDate
            FROM dbo.Ticket t
            JOIN dbo.Event e ON t.EventID = e.EventID
            WHERE t.TicketID = ?
        """, (ticket_id,))
        ticket_data = cursor.fetchone()
        
        if not ticket_data:
            return jsonify({'success': False, 'message': 'Ticket not found'}), 404

        # Initialize IPFS manager
        ipfs_manager = IPFSManager(ipfs_connection)
        nft_data = []
        loop = asyncio.get_event_loop()

        for i in range(quantity):
            try:
                # Use the blockchain token ID instead of sequential number
                token_id = token_ids[i]
                
                verification_data = f"{ticket_id}{token_id}{datetime.now().isoformat()}"
                verification_hash = hashlib.sha256(verification_data.encode()).hexdigest()
                
                ticket_info = {
                    'ticket_id': ticket_id,
                    'token_id': token_id,  # Using blockchain token ID
                    'event_name': ticket_data.EventTitle,
                    'event_date': ticket_data.EventStartDate.isoformat(),
                    'ticket_type': ticket_data.TicketType,
                    'venue': ticket_data.EventVenue,
                    'price': str(ticket_data.Price),
                    'verification_hash': verification_hash
                }
                
                # Generate QR code and metadata
                qr_code_bytes, qr_data = ipfs_manager.generate_qr_code(ticket_info)
                if not qr_code_bytes:
                    raise Exception("Failed to generate QR code")
                
                qr_base64 = base64.b64encode(qr_code_bytes).decode('utf-8')
                
                # Upload to IPFS
                qr_hash = await loop.run_in_executor(
                    None, 
                    ipfs_manager.ipfs_connection.client.add_bytes, 
                    qr_code_bytes
                )
                qr_hash = qr_hash['Hash'] if isinstance(qr_hash, dict) else qr_hash
                
                metadata_json = json.dumps(ticket_info).encode()
                metadata_hash = await loop.run_in_executor(
                    None,
                    ipfs_manager.ipfs_connection.client.add_bytes,
                    metadata_json
                )
                metadata_hash = metadata_hash['Hash'] if isinstance(metadata_hash, dict) else metadata_hash

                nft_data.append({
                    'tokenId': token_id,  # Using blockchain token ID
                    'metadataHash': metadata_hash,
                    'qrHash': qr_hash,
                    'qrBase64': qr_base64,
                    'verificationHash': verification_hash,
                    'metadata': ticket_info
                })
                
            except Exception as e:
                print(f"Error processing NFT metadata {i+1}: {e}")
                continue

        if not nft_data:
            return jsonify({
                'success': False, 
                'message': 'Failed to generate any NFT metadata'
            }), 500

        return jsonify({
            'success': True,
            'nftData': nft_data,
            'message': f'Successfully generated metadata for {len(nft_data)} NFTs'
        })
        
    except Exception as e:
        print(f"Error generating NFT metadata: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/update_ticket_transferability', methods=['POST'])
def update_ticket_transferability():
    try:
        data = request.json
        ticket_id = data['ticketId']
        is_transferrable = data['isTransferrable']
        
        # Update the database
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE Ticket 
            SET IsTransferrable = ? 
            WHERE TicketID = ?
        """, (is_transferrable, ticket_id))
        
        conn.commit()
        
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.template_filter('from_json')
def from_json(value):
    return json.loads(value)

@app.route('/check_resale_status', methods=['POST'])
def check_resale_status():
    data = request.json
    token_id = data['tokenId']

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM ResaleListings WHERE TokenID = ? AND IsActive = 1", (token_id,))
        count = cursor.fetchone()[0]

        if count > 0:
            return jsonify({'isReselling': True})
        else:
            return jsonify({'isReselling': False})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)
    



# Initialize the Flask application with template and static folders inside src
app = Flask(__name__, template_folder='src/templates', static_folder='')

# Set secret key for session management
app.secret_key = 'your_unique_secret_key'


#email set up





# Run the application
if __name__ == '__main__':
    app.run(debug=True)
