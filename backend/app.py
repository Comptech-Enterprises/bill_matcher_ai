import os
import uuid
import tempfile
from flask import Flask, request, jsonify, send_file, g
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from nvidia_nim_service import NvidiaNIMService
from bill_processor import BillProcessor
from matcher import ItemMatcher
from pdf_processor import PDFProcessor
from excel_exporter import ExcelExporter
from database import User, init_db
from auth import login_required, admin_required, AuthService, get_current_user

load_dotenv()

app = Flask(__name__)

# CORS Configuration - Allow both local development and production domains
cors_origins = [
    'http://localhost:8080',
    'http://127.0.0.1:8080',
    'https://bill-matcher-frontend.onrender.com',  # Update this after deploying frontend
]

# Add custom domain if provided
custom_frontend = os.getenv('FRONTEND_URL')
if custom_frontend:
    cors_origins.append(custom_frontend)

CORS(app, origins=cors_origins, supports_credentials=True)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')
app.config['EXPORT_FOLDER'] = os.getenv('EXPORT_FOLDER', 'exports')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_FILE_SIZE', 16 * 1024 * 1024))

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['EXPORT_FOLDER'], exist_ok=True)

# Initialize database
init_db()

# Initialize services
nim_service = NvidiaNIMService()
bill_processor = BillProcessor()
item_matcher = ItemMatcher()
pdf_processor = PDFProcessor()
excel_exporter = ExcelExporter()

# In-memory storage for sessions (in production, use Redis or database)
sessions = {}


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_session_id():
    """Generate unique session ID"""
    return str(uuid.uuid4())


# ==================== Health Check ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({
        'status': 'healthy',
        'service': 'bill-matcher-api',
        'version': '1.0.0'
    }), 200


# ==================== Authentication Routes ====================

@app.route('/api/auth/login', methods=['POST'])
def login():
    """User login endpoint"""
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    result, status_code = AuthService.login(username, password)
    return jsonify(result), status_code


@app.route('/api/auth/me', methods=['GET'])
@login_required
def get_current_user_info():
    """Get current authenticated user info"""
    current_user = get_current_user()
    user_info = AuthService.get_user_info(current_user['id'])
    
    if user_info:
        return jsonify(user_info)
    return jsonify({'error': 'User not found'}), 404


@app.route('/api/auth/change-password', methods=['POST'])
@login_required
def change_password():
    """Change current user's password"""
    current_user = get_current_user()
    data = request.get_json()
    
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    
    result, status_code = AuthService.change_password(
        current_user['id'], 
        current_password, 
        new_password
    )
    return jsonify(result), status_code


# ==================== Admin Routes ====================

@app.route('/api/admin/users', methods=['GET'])
@admin_required
def list_users():
    """List all users (admin only)"""
    users = User.get_all()
    # Remove password hash from response
    for user in users:
        if 'password_hash' in user:
            del user['password_hash']
        # Convert datetime to string
        if user.get('created_at'):
            user['created_at'] = str(user['created_at'])
        if user.get('last_login'):
            user['last_login'] = str(user['last_login'])
    
    return jsonify({'users': users})


@app.route('/api/admin/users', methods=['POST'])
@admin_required
def create_user():
    """Create a new user (admin only)"""
    data = request.get_json()
    
    username = data.get('username', '').strip()
    password = data.get('password', '')
    role = data.get('role', 'user')
    
    # Validation
    if not username:
        return jsonify({'error': 'Username is required'}), 400
    
    if len(username) < 3:
        return jsonify({'error': 'Username must be at least 3 characters'}), 400
    
    if not password:
        return jsonify({'error': 'Password is required'}), 400
    
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    if role not in ['admin', 'user']:
        return jsonify({'error': 'Role must be "admin" or "user"'}), 400
    
    try:
        user = User.create(username, password, role)
        return jsonify({
            'message': 'User created successfully',
            'user': user
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    """Update a user (admin only)"""
    current_user = get_current_user()
    data = request.get_json()
    
    # Check if user exists
    user = User.get_by_id(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    username = data.get('username', '').strip() or None
    password = data.get('password', '') or None
    role = data.get('role', '') or None
    
    # Validation
    if username and len(username) < 3:
        return jsonify({'error': 'Username must be at least 3 characters'}), 400
    
    if password and len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    if role and role not in ['admin', 'user']:
        return jsonify({'error': 'Role must be "admin" or "user"'}), 400
    
    # Prevent admin from demoting themselves
    if user_id == current_user['id'] and role == 'user':
        return jsonify({'error': 'You cannot demote yourself from admin'}), 400
    
    try:
        User.update(user_id, username=username, password=password, role=role)
        updated_user = User.get_by_id(user_id)
        return jsonify({
            'message': 'User updated successfully',
            'user': {
                'id': updated_user['id'],
                'username': updated_user['username'],
                'role': updated_user['role']
            }
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """Delete a user (admin only)"""
    current_user = get_current_user()
    
    # Prevent admin from deleting themselves
    if user_id == current_user['id']:
        return jsonify({'error': 'You cannot delete your own account'}), 400
    
    # Check if user exists
    user = User.get_by_id(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    User.delete(user_id)
    return jsonify({'message': 'User deleted successfully'})


# ==================== Bill Processing Routes (Protected) ====================

@app.route('/api/session/create', methods=['POST'])
@login_required
def create_session():
    """Create a new processing session"""
    current_user = get_current_user()
    session_id = generate_session_id()
    sessions[session_id] = {
        'user_id': current_user['id'],
        'purchase_items': [],
        'sale_items': [],
        'purchase_files': [],
        'sale_files': [],
        'status': 'created'
    }
    return jsonify({'session_id': session_id, 'status': 'created'})


@app.route('/api/upload/<bill_type>', methods=['POST'])
@login_required
def upload_bill(bill_type):
    """
    Upload a bill (purchase or sale)
    bill_type: 'purchase' or 'sale'
    """
    if bill_type not in ['purchase', 'sale']:
        return jsonify({'error': 'Invalid bill type. Use "purchase" or "sale"'}), 400
    
    session_id = request.form.get('session_id')
    if not session_id or session_id not in sessions:
        return jsonify({'error': 'Invalid or missing session_id'}), 400
    
    # Verify session belongs to current user
    current_user = get_current_user()
    if sessions[session_id].get('user_id') != current_user['id']:
        return jsonify({'error': 'Session not found'}), 404
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
    
    try:
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        # Process the file
        extracted_items = process_bill_file(filepath, bill_type)
        
        # Store results in session
        if bill_type == 'purchase':
            sessions[session_id]['purchase_items'].extend(extracted_items)
            sessions[session_id]['purchase_files'].append(filename)
        else:
            sessions[session_id]['sale_items'].extend(extracted_items)
            sessions[session_id]['sale_files'].append(filename)
        
        sessions[session_id]['status'] = 'processing'
        
        # Clean up uploaded file
        os.remove(filepath)
        
        return jsonify({
            'message': f'{bill_type.capitalize()} bill processed successfully',
            'items_extracted': len(extracted_items),
            'items': extracted_items,
            'session_id': session_id
        })
    
    except Exception as e:
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500


def process_bill_file(filepath, bill_type):
    """Process a bill file (image or PDF) and extract items"""
    items = []
    
    print(f"\n[PROCESS] Processing {bill_type} bill: {filepath}")
    
    # Check if PDF
    if filepath.lower().endswith('.pdf'):
        # Convert PDF pages to images
        print(f"[PROCESS] Converting PDF to images...")
        image_paths = pdf_processor.pdf_to_images(filepath)
        print(f"[PROCESS] PDF has {len(image_paths)} pages")
        
        for i, image_path in enumerate(image_paths):
            try:
                print(f"[PROCESS] Processing page {i+1}...")
                # Extract items directly from image using NVIDIA VLM
                page_items = nim_service.extract_items_from_image(image_path, bill_type)
                items.extend(page_items)
                
                # Clean up temporary image
                os.remove(image_path)
            except Exception as e:
                print(f"[PROCESS ERROR] Error processing page {i+1}: {e}")
                continue
    else:
        # Process single image - extract items directly using VLM
        items = nim_service.extract_items_from_image(filepath, bill_type)
    
    print(f"[PROCESS] Total items extracted: {len(items)}")
    for item in items:
        print(f"[PROCESS] - {item}")
    
    return items


@app.route('/api/match', methods=['POST'])
@login_required
def match_items():
    """Match purchase and sale items to calculate profit/loss"""
    data = request.get_json()
    session_id = data.get('session_id')
    
    if not session_id or session_id not in sessions:
        return jsonify({'error': 'Invalid or missing session_id'}), 400
    
    # Verify session belongs to current user
    current_user = get_current_user()
    if sessions[session_id].get('user_id') != current_user['id']:
        return jsonify({'error': 'Session not found'}), 404
    
    session = sessions[session_id]
    
    if not session['purchase_items']:
        return jsonify({'error': 'No purchase items uploaded'}), 400
    
    if not session['sale_items']:
        return jsonify({'error': 'No sale items uploaded'}), 400
    
    try:
        # Match items
        matched_results = item_matcher.match_items(
            session['purchase_items'],
            session['sale_items']
        )
        
        # Calculate summary
        summary = item_matcher.calculate_summary(matched_results)
        
        # Store results in session
        session['matched_results'] = matched_results
        session['summary'] = summary
        session['status'] = 'completed'
        
        return jsonify({
            'matched': matched_results['matched'],
            'unmatched_purchases': matched_results['unmatched_purchases'],
            'unmatched_sales': matched_results['unmatched_sales'],
            'summary': summary,
            'session_id': session_id
        })
    
    except Exception as e:
        return jsonify({'error': f'Error matching items: {str(e)}'}), 500


@app.route('/api/session/<session_id>', methods=['GET'])
@login_required
def get_session(session_id):
    """Get session details and results"""
    if session_id not in sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    # Verify session belongs to current user
    current_user = get_current_user()
    if sessions[session_id].get('user_id') != current_user['id']:
        return jsonify({'error': 'Session not found'}), 404
    
    session = sessions[session_id]
    
    return jsonify({
        'session_id': session_id,
        'status': session['status'],
        'purchase_items_count': len(session['purchase_items']),
        'sale_items_count': len(session['sale_items']),
        'purchase_files': session['purchase_files'],
        'sale_files': session['sale_files'],
        'purchase_items': session['purchase_items'],
        'sale_items': session['sale_items'],
        'matched_results': session.get('matched_results'),
        'summary': session.get('summary')
    })


@app.route('/api/export/<session_id>', methods=['GET'])
@login_required
def export_results(session_id):
    """Export matched results to Excel"""
    if session_id not in sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    # Verify session belongs to current user
    current_user = get_current_user()
    if sessions[session_id].get('user_id') != current_user['id']:
        return jsonify({'error': 'Session not found'}), 404
    
    session = sessions[session_id]
    
    if 'matched_results' not in session:
        return jsonify({'error': 'No matched results to export. Run matching first.'}), 400
    
    try:
        # Generate Excel file
        export_filename = f"bill_matching_{session_id[:8]}.xlsx"
        export_path = os.path.join(app.config['EXPORT_FOLDER'], export_filename)
        
        excel_exporter.export_results(
            matched_results=session['matched_results'],
            summary=session['summary'],
            output_path=export_path
        )
        
        return send_file(
            export_path,
            as_attachment=True,
            download_name=export_filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    except Exception as e:
        return jsonify({'error': f'Error exporting results: {str(e)}'}), 500


@app.route('/api/items/update', methods=['POST'])
@login_required
def update_item():
    """Manually update an item's details"""
    data = request.get_json()
    session_id = data.get('session_id')
    item_type = data.get('item_type')  # 'purchase' or 'sale'
    item_index = data.get('item_index')
    updates = data.get('updates', {})
    
    if not session_id or session_id not in sessions:
        return jsonify({'error': 'Invalid or missing session_id'}), 400
    
    # Verify session belongs to current user
    current_user = get_current_user()
    if sessions[session_id].get('user_id') != current_user['id']:
        return jsonify({'error': 'Session not found'}), 404
    
    if item_type not in ['purchase', 'sale']:
        return jsonify({'error': 'Invalid item_type'}), 400
    
    session = sessions[session_id]
    items_key = f'{item_type}_items'
    
    if item_index < 0 or item_index >= len(session[items_key]):
        return jsonify({'error': 'Invalid item_index'}), 400
    
    # Update item
    for key, value in updates.items():
        if key in ['serial_number', 'item_name', 'hsn_code', f'{item_type}_price']:
            session[items_key][item_index][key] = value
    
    return jsonify({
        'message': 'Item updated successfully',
        'item': session[items_key][item_index]
    })


@app.route('/api/items/add', methods=['POST'])
@login_required
def add_item():
    """Manually add an item"""
    data = request.get_json()
    session_id = data.get('session_id')
    item_type = data.get('item_type')
    item_data = data.get('item', {})
    
    if not session_id or session_id not in sessions:
        return jsonify({'error': 'Invalid or missing session_id'}), 400
    
    # Verify session belongs to current user
    current_user = get_current_user()
    if sessions[session_id].get('user_id') != current_user['id']:
        return jsonify({'error': 'Session not found'}), 404
    
    if item_type not in ['purchase', 'sale']:
        return jsonify({'error': 'Invalid item_type'}), 400
    
    session = sessions[session_id]
    items_key = f'{item_type}_items'
    
    # Add item
    session[items_key].append(item_data)
    
    return jsonify({
        'message': 'Item added successfully',
        'item': item_data,
        'total_items': len(session[items_key])
    })


@app.route('/api/items/delete', methods=['POST'])
@login_required
def delete_item():
    """Delete an item"""
    data = request.get_json()
    session_id = data.get('session_id')
    item_type = data.get('item_type')
    item_index = data.get('item_index')
    
    if not session_id or session_id not in sessions:
        return jsonify({'error': 'Invalid or missing session_id'}), 400
    
    # Verify session belongs to current user
    current_user = get_current_user()
    if sessions[session_id].get('user_id') != current_user['id']:
        return jsonify({'error': 'Session not found'}), 404
    
    if item_type not in ['purchase', 'sale']:
        return jsonify({'error': 'Invalid item_type'}), 400
    
    session = sessions[session_id]
    items_key = f'{item_type}_items'
    
    if item_index < 0 or item_index >= len(session[items_key]):
        return jsonify({'error': 'Invalid item_index'}), 400
    
    # Delete item
    deleted_item = session[items_key].pop(item_index)
    
    return jsonify({
        'message': 'Item deleted successfully',
        'deleted_item': deleted_item,
        'total_items': len(session[items_key])
    })


@app.route('/api/session/<session_id>', methods=['DELETE'])
@login_required
def delete_session(session_id):
    """Delete a session and clean up resources"""
    if session_id not in sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    # Verify session belongs to current user
    current_user = get_current_user()
    if sessions[session_id].get('user_id') != current_user['id']:
        return jsonify({'error': 'Session not found'}), 404
    
    del sessions[session_id]
    
    return jsonify({'message': 'Session deleted successfully'})


# ==================== Error Handlers ====================

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 16MB'}), 413


@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Resource not found'}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    # Use PORT from environment (Render provides this) or default to 5000
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'development') == 'development'

    print(f"Starting Bill Matcher API on port {port}...")
    print(f"Debug mode: {debug}")

    app.run(debug=debug, host='0.0.0.0', port=port)
