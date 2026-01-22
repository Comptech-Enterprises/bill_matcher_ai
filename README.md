# Bill Matcher - Profit/Loss Calculator

A web application that uses NVIDIA NIM's OCR capabilities to extract data from purchase and sale bills, match items, and calculate profit/loss.

## 🚀 Features

- **OCR Bill Processing**: Uses NVIDIA Nemotron-Parse API for accurate text extraction from bill images
- **Multi-format Support**: Accepts JPG, PNG, and PDF files
- **Smart Item Matching**: Matches purchase and sale items using serial numbers, HSN codes, and item names
- **Profit/Loss Calculation**: Automatically calculates profit/loss for each matched item
- **Excel Export**: Export results to professionally formatted Excel files
- **Manual Editing**: Add, edit, or delete items before matching
- **Responsive UI**: Works on desktop and mobile devices

## 📁 Project Structure

```
bill_software/
├── backend/
│   ├── app.py                 # Flask API server
│   ├── nvidia_nim_service.py  # NVIDIA NIM OCR integration
│   ├── bill_processor.py      # Bill text parsing logic
│   ├── matcher.py             # Item matching & profit calculation
│   ├── pdf_processor.py       # PDF to image conversion
│   └── excel_exporter.py      # Excel export functionality
├── frontend/
│   ├── index.html             # Main HTML page
│   ├── styles.css             # Styling
│   └── app.js                 # Frontend JavaScript
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variables template
└── README.md                  # This file
```

## 🛠️ Installation

### Prerequisites

- Python 3.8 or higher
- NVIDIA API Key (get one from [NVIDIA NGC](https://ngc.nvidia.com/))

### Setup

1. **Clone the repository**
   ```bash
   cd bill_software
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env and add your NVIDIA API key
   NVIDIA_API_KEY=your_actual_api_key_here
   SECRET_KEY=your_secret_key_here
   ```

## 🚀 Running the Application

### Start the Backend Server

```bash
cd backend
python app.py
```

The API server will start at `http://localhost:5000`

### Open the Frontend

Open `frontend/index.html` in your web browser, or serve it with a simple HTTP server:

```bash
# Using Python
cd frontend
python -m http.server 8080

# Then open http://localhost:8080 in your browser
```

## 📖 Usage

### Step 1: Upload Bills
1. Upload purchase bills (invoices showing items you bought)
2. Upload sale bills (invoices showing items you sold)
3. Click "Process Bills" to extract item data using OCR

### Step 2: Review Items
1. Review extracted items from both purchase and sale bills
2. Add missing items manually if needed
3. Edit incorrect item details
4. Delete duplicate or unwanted items

### Step 3: Match & View Results
1. Click "Match Items" to match purchase and sale items
2. View matched items with profit/loss calculations
3. Check unmatched purchases and sales
4. Export results to Excel

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/session/create` | POST | Create new session |
| `/api/upload/<type>` | POST | Upload bill (purchase/sale) |
| `/api/session/<id>` | GET | Get session details |
| `/api/match` | POST | Match items and calculate P/L |
| `/api/export/<id>` | GET | Export results to Excel |
| `/api/items/add` | POST | Add item manually |
| `/api/items/update` | POST | Update item |
| `/api/items/delete` | POST | Delete item |
| `/api/session/<id>` | DELETE | Delete session |

## 🧠 Matching Algorithm

Items are matched using a weighted scoring system:

| Criteria | Weight | Description |
|----------|--------|-------------|
| Serial Number | 50% | Exact match of serial numbers |
| HSN Code | 30% | Exact match of HSN codes |
| Item Name | 20% | Fuzzy matching of item names |

Items with a match score ≥ 70% are considered matches.

## 📊 Excel Export

The exported Excel file contains:

1. **Summary Sheet**: Overview statistics
   - Total matched items
   - Total purchase/sale values
   - Overall profit/loss

2. **Matched Items Sheet**: All matched items with:
   - Serial number, item name, HSN code
   - Purchase price, sale price
   - Profit/loss amount and percentage

3. **Unmatched Purchases Sheet**: Items not sold

4. **Unmatched Sales Sheet**: Items without purchase records

## ⚙️ Configuration

Environment variables (`.env` file):

| Variable | Description | Default |
|----------|-------------|---------|
| `NVIDIA_API_KEY` | Your NVIDIA NIM API key | Required |
| `SECRET_KEY` | Flask secret key | `dev-secret-key` |
| `UPLOAD_FOLDER` | Folder for uploaded files | `uploads` |
| `EXPORT_FOLDER` | Folder for exported files | `exports` |
| `MAX_FILE_SIZE` | Maximum file size (bytes) | `16777216` (16MB) |

## 🔧 Troubleshooting

### "Failed to create session" error
- Ensure the backend server is running on port 5000
- Check for CORS issues if using a different frontend port

### OCR not extracting text correctly
- Ensure images are clear and well-lit
- Try higher resolution images
- For PDFs, check if they're scanned or text-based

### Items not matching
- Check if serial numbers are consistent across bills
- Verify HSN codes are correct
- Item names should be similar (not case-sensitive)

## 📝 License

MIT License - feel free to use for personal or commercial projects.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
