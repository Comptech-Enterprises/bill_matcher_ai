import os
import uuid
import tempfile
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from nvidia_nim_service import NvidiaNIMService
from bill_processor import BillProcessor
from matcher import ItemMatcher
from pdf_processor import PDFProcessor
from excel_exporter import ExcelExporter

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')
app.config['EXPORT_FOLDER'] = os.getenv('EXPORT_FOLDER', 'exports')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_FILE_SIZE', 16 * 1024 * 1024))

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['EXPORT_FOLDER'], exist_ok=True)

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


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'message': 'Bill Software API is running'})


@app.route('/api/session/create', methods=['POST'])
def create_session():
    """Create a new processing session"""
    session_id = generate_session_id()
    sessions[session_id] = {
        'purchase_items': [],
        'sale_items': [],
        'purchase_files': [],
        'sale_files': [],
        'status': 'created'
    }
    return jsonify({'session_id': session_id, 'status': 'created'})


@app.route('/api/upload/<bill_type>', methods=['POST'])
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
def match_items():
    """Match purchase and sale items to calculate profit/loss"""
    data = request.get_json()
    session_id = data.get('session_id')
    
    if not session_id or session_id not in sessions:
        return jsonify({'error': 'Invalid or missing session_id'}), 400
    
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
def get_session(session_id):
    """Get session details and results"""
    if session_id not in sessions:
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
def export_results(session_id):
    """Export matched results to Excel"""
    if session_id not in sessions:
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
def update_item():
    """Manually update an item's details"""
    data = request.get_json()
    session_id = data.get('session_id')
    item_type = data.get('item_type')  # 'purchase' or 'sale'
    item_index = data.get('item_index')
    updates = data.get('updates', {})
    
    if not session_id or session_id not in sessions:
        return jsonify({'error': 'Invalid or missing session_id'}), 400
    
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
def add_item():
    """Manually add an item"""
    data = request.get_json()
    session_id = data.get('session_id')
    item_type = data.get('item_type')
    item_data = data.get('item', {})
    
    if not session_id or session_id not in sessions:
        return jsonify({'error': 'Invalid or missing session_id'}), 400
    
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
def delete_item():
    """Delete an item"""
    data = request.get_json()
    session_id = data.get('session_id')
    item_type = data.get('item_type')
    item_index = data.get('item_index')
    
    if not session_id or session_id not in sessions:
        return jsonify({'error': 'Invalid or missing session_id'}), 400
    
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
def delete_session(session_id):
    """Delete a session and clean up resources"""
    if session_id not in sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    del sessions[session_id]
    
    return jsonify({'message': 'Session deleted successfully'})


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
    app.run(debug=True, host='0.0.0.0', port=5000)
