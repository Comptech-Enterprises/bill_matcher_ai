# Bill Matcher - Profit/Loss Calculator

A web application that uses NVIDIA NIM's Vision-Language Model to extract data from purchase and sale bills, match items, and calculate profit/loss.

## 🚀 Features

- **User Authentication**: Secure login system with JWT tokens
- **Multi-user Support**: Admin can create and manage multiple user accounts
- **Role-based Access**: Admin and regular user roles
- **OCR Bill Processing**: Uses NVIDIA Nemotron-Parse API for accurate text extraction from bill images
- **Multi-format Support**: Accepts JPG, PNG, and PDF files
- **Smart Item Matching**: Matches purchase and sale items using serial numbers, HSN codes, and item names
- **Profit/Loss Calculation**: Automatically calculates profit/loss for each matched item
- **Excel Export**: Export results to professionally formatted Excel files
- **Manual Editing**: Add, edit, or delete items before matching
- **Responsive UI**: Works on desktop and mobile devices
- **Docker Support**: Easy deployment with Docker Compose

## 📁 Project Structure

```
bill_software/
├── backend/
│   ├── app.py                 # Flask API server
│   ├── auth.py                # JWT authentication service
│   ├── database.py            # SQLite database & user model
│   ├── nvidia_nim_service.py  # NVIDIA NIM OCR integration
│   ├── bill_processor.py      # Bill text parsing logic
│   ├── matcher.py             # Item matching & profit calculation
│   ├── pdf_processor.py       # PDF to image conversion
│   ├── excel_exporter.py      # Excel export functionality
│   └── bill_matcher.db        # SQLite database (auto-created)
├── frontend/
│   ├── index.html             # Main HTML page
│   ├── styles.css             # Styling
│   └── app.js                 # Frontend JavaScript
├── Dockerfile                 # Backend Docker image
├── docker-compose.yml         # Multi-container orchestration
├── nginx.conf                 # Nginx configuration for frontend
├── .dockerignore              # Docker build exclusions
├── .gitignore                 # Git exclusions
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variables template
└── README.md                  # This file
```

---

## 🐳 Docker Setup (Recommended)

The easiest way to run the application is with Docker.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- NVIDIA API Key (get one from [NVIDIA NGC](https://build.nvidia.com/))

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/Comptech-Enterprises/bill_matcher_ai.git
   cd bill_matcher_ai
   ```

2. **Set your NVIDIA API key**

   **Option A: Create .env file**
   ```bash
   cp .env.example .env
   # Edit .env and add your API key
   ```

   **Option B: Set environment variable**
   ```bash
   # Windows PowerShell
   $env:NVIDIA_API_KEY="nvapi-your-key-here"

   # Linux/Mac
   export NVIDIA_API_KEY="nvapi-your-key-here"
   ```

3. **Build and run**
   ```bash
   docker-compose up --build
   ```

4. **Access the application**
   
   Open [http://localhost:8080](http://localhost:8080) in your browser

### Docker Architecture

```
┌─────────────────────────────────────────┐
│       http://localhost:8080             │
├─────────────────┬───────────────────────┤
│   Nginx         │   Flask Backend       │
│   (Frontend)    │   (Python API)        │
│   Port: 8080    │   Port: 5000          │
│                 │                       │
│   Serves HTML   │   NVIDIA NIM API      │
│   Proxies /api  │   OCR Processing      │
└─────────────────┴───────────────────────┘
```

### Docker Commands

```bash
# Build and start containers
docker-compose up --build

# Run in background (detached mode)
docker-compose up -d

# View logs
docker-compose logs -f

# View backend logs only
docker-compose logs -f backend

# Stop containers
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v

# Rebuild after code changes
docker-compose up --build
```

---

## 🛠️ Local Development Setup

For development without Docker.

### Prerequisites

- Python 3.8 or higher
- NVIDIA API Key (get one from [NVIDIA NGC](https://build.nvidia.com/))

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Comptech-Enterprises/bill_matcher_ai.git
   cd bill_matcher_ai
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

5. **Update frontend API URL** (for local dev)
   
   Edit `frontend/app.js` and change:
   ```javascript
   const API_BASE_URL = '/api';
   ```
   to:
   ```javascript
   const API_BASE_URL = 'http://localhost:5000/api';
   ```

### Running Locally

**Start the Backend Server:**
```bash
cd backend
python app.py
```
The API server will start at `http://localhost:5000`

**Open the Frontend:**

Open `frontend/index.html` directly in your browser, or serve with a simple HTTP server:
```bash
cd frontend
python -m http.server 8080
```
Then open http://localhost:8080

---

## 🔐 Authentication

### Default Admin Account

On first run, a default admin account is created automatically:
- **Username:** `admin`
- **Password:** `admin123`

> ⚠️ **Important:** Change the default admin password immediately after first login!

### User Roles

| Role | Permissions |
|------|------------|
| **admin** | Full access + user management |
| **user** | Bill processing only |

### User Management (Admin Only)

1. Click on your username in the top-right corner
2. Select "User Management"
3. From here you can:
   - Add new users
   - Edit existing users (username, password, role)
   - Delete users (except yourself)

### Authentication API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/login` | POST | User login |
| `/api/auth/me` | GET | Get current user info |
| `/api/auth/change-password` | POST | Change password |
| `/api/admin/users` | GET | List all users (admin) |
| `/api/admin/users` | POST | Create user (admin) |
| `/api/admin/users/<id>` | PUT | Update user (admin) |
| `/api/admin/users/<id>` | DELETE | Delete user (admin) |

## 📖 Usage

### Step 1: Login
1. Open the application in your browser
2. Login with your credentials (default: admin/admin123)
3. Change your password if this is your first login

### Step 2: Upload Bills
1. Upload purchase bills (invoices showing items you bought)
2. Upload sale bills (invoices showing items you sold)
3. Click "Process Bills" to extract item data using AI

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

---

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

---

## 🧠 Matching Algorithm

Items are matched using a weighted scoring system:

| Criteria | Weight | Description |
|----------|--------|-------------|
| Serial Number | 50% | Exact match of serial numbers |
| HSN Code | 30% | Exact match of HSN codes |
| Item Name | 20% | Fuzzy matching of item names |

Items with a match score ≥ 70% are considered matches.

---

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

---

## ⚙️ Configuration

Environment variables (`.env` file):

| Variable | Description | Default |
|----------|-------------|---------|
| `NVIDIA_API_KEY` | Your NVIDIA NIM API key | Required |
| `SECRET_KEY` | Flask secret key | `dev-secret-key` |
| `UPLOAD_FOLDER` | Folder for uploaded files | `uploads` |
| `EXPORT_FOLDER` | Folder for exported files | `exports` |
| `MAX_FILE_SIZE` | Maximum file size (bytes) | `16777216` (16MB) |

---

## 🔧 Troubleshooting

### "Failed to create session" error
- Ensure the backend server is running on port 5000
- For Docker: check if containers are running (`docker-compose ps`)
- Check for CORS issues if using different ports

### OCR not extracting text correctly
- Ensure images are clear and well-lit
- Try higher resolution images
- For PDFs, check if they're scanned properly

### Items not matching
- Check if serial numbers are consistent across bills
- Verify HSN codes are correct
- Item names should be similar (not case-sensitive)

### Docker issues
```bash
# Check container status
docker-compose ps

# View logs for errors
docker-compose logs backend

# Restart containers
docker-compose restart

# Full rebuild
docker-compose down && docker-compose up --build
```

---

## 📝 License

MIT License - feel free to use for personal or commercial projects.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 🔗 Links

- **GitHub**: [https://github.com/Comptech-Enterprises/bill_matcher_ai](https://github.com/Comptech-Enterprises/bill_matcher_ai)
- **NVIDIA NIM**: [https://build.nvidia.com/](https://build.nvidia.com/)
