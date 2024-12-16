from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from app.utils.db import get_db_connection, allowed_file
from werkzeug.utils import secure_filename
from datetime import datetime
import os
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

# Load environment variables
load_dotenv()

organizer_bp = Blueprint('organizer', __name__)

@organizer_bp.route('/')
def dashboard():
    if 'organiser_id' not in session:
        return redirect(url_for('organizer.login'))
    return redirect(url_for('organizer.ticket_management'))

@organizer_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password']

        if not email or not password:
            flash('Email and password are required', 'error')
            return redirect(url_for('organizer.login'))

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM dbo.Organiser WHERE OrganiserEmail = ?", (email,))
            organiser = cursor.fetchone()

            if organiser and organiser.Password == password:
                session['organiser_id'] = organiser.OrganiserID
                session['organiser_name'] = organiser.OrganiserName
                return redirect(url_for('organizer.ticket_management'))
            else:
                flash('Invalid email or password', 'error')
                return redirect(url_for('organizer.login'))
        except Exception as e:
            flash('An error occurred', 'error')
            return redirect(url_for('organizer.login'))
        finally:
            conn.close()

    return render_template('org/org_login.html')

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

@organizer_bp.route('/ticket-management')
def ticket_management():
    if 'organiser_id' not in session:
        return redirect(url_for('organizer.login'))
    
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
        
        return render_template('org/ticket_management.html', tickets=tickets)
    except Exception as e:
        # Log the error for debugging
        print(f'An error occurred: {e}')
        flash(f'An error occurred: {e}', 'error')
        return redirect(url_for('organizer.dashboard'))
    finally:
        conn.close()

@organizer_bp.route('/event_management')
def event_management():
    if 'organiser_id' not in session:
        return redirect(url_for('organizer.login'))
    
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
        
        return render_template('org/event_management.html', events=events)
    except Exception as e:
        print(f'An error occurred: {e}')
        flash(f'An error occurred: {e}', 'error')
        return redirect(url_for('organizer.dashboard'))
    finally:
        conn.close()

@organizer_bp.route('/create_event', methods=['GET', 'POST'])
def create_event():
    if 'organiser_id' not in session:
        return redirect(url_for('organizer.login'))

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
            return redirect(url_for('organizer.event_management'))
        except Exception as e:
            flash(f'An error occurred: {e}', 'error')
            return redirect(url_for('organizer.create_event'))
        finally:
            conn.close()

    return render_template('org/create_event.html')

@organizer_bp.route('/edit_event/<event_id>', methods=['GET', 'POST'])
def edit_event(event_id):
    if 'organiser_id' not in session:
        return redirect(url_for('organizer.login'))

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
            return redirect(url_for('organizer.event_management'))
        except Exception as e:
            flash(f'An error occurred: {e}', 'error')
        finally:
            conn.close()

@organizer_bp.route('/participant_management')
def participant_management():
    if 'organiser_id' not in session:
        return redirect(url_for('organizer.login'))
    
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
        
        return render_template('org/part_management.html', participants=participants)
    except Exception as e:
        print(f'An error occurred: {e}')
        flash(f'An error occurred: {e}', 'error')
        return redirect(url_for('organizer.dashboard'))
    finally:
        conn.close()

@organizer_bp.route('/delete_ticket/<ticket_id>')
def delete_ticket(ticket_id):
    if 'organiser_id' not in session:
        return redirect(url_for('organizer.login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if the ticket belongs to the logged-in organizer
        cursor.execute("""
            SELECT t.TicketID
            FROM Ticket t
            JOIN Event e ON t.EventID = e.EventID
            WHERE t.TicketID = ? AND e.OrganiserID = ?
        """, (ticket_id, session['organiser_id']))
        
        if cursor.fetchone() is None:
            flash('You do not have permission to delete this ticket.', 'error')
            return redirect(url_for('organizer.ticket_management'))
        
        # Delete the ticket
        cursor.execute("DELETE FROM Ticket WHERE TicketID = ?", (ticket_id,))
        conn.commit()
        flash('Ticket deleted successfully.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'An error occurred: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('organizer.ticket_management'))

@organizer_bp.route('/get_contract_data')
def get_contract_data():
    contract_json_path = os.path.join(organizer_bp.root_path, 'build', 'contracts', 'Tickets.json')
    with open(contract_json_path, 'r') as file:
        contract_data = json.load(file)
    
    # Get the network ID (you may need to adjust this based on your setup)
    network_id = '5777'  # This is typically the default for local development networks
    
    abi = contract_data['abi']
    address = contract_data['networks'][network_id]['address']
    
    return jsonify({'abi': abi, 'address': address})

@organizer_bp.route('/update_ticket_nft_status', methods=['POST'])
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

@organizer_bp.route('/create_nfts', methods=['POST'])
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

@organizer_bp.route('/get_event_image/<ticket_id>')
def get_event_image(ticket_id):
    # Query your database to get the event image URL for the given ticket_id
    # Return JSON response with the image URL
    return jsonify({
        'imageUrl': 'https://postimg.cc/p5fmvrc4'
    })

@organizer_bp.route('/mintNFT', methods=['POST'])
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

@organizer_bp.route('/get_ticket_metadata/<ticket_id>')
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
        
@organizer_bp.route('/scan-ticket')
def scan_ticket():
    return render_template('org/verify_ticket.html')

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

@organizer_bp.route('/generateNFTMetadata', methods=['POST'])
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

# @organizer_bp.template_filter('from_json')
# def from_json(value):
#     return json.loads(value)

if __name__ == '__main__':
    organizer_bp.run(debug=True)