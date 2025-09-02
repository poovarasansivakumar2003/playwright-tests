# Iden Data Extraction Challenge

This repository contains a Python automation script built with [Microsoft Playwright](https://playwright.dev/python/) for completing the **Data Extraction Challenge** conducted by IDEN.

## 🎯 Challenge Objectives

The challenge tests automation skills by requiring a Playwright script that:

1. **Session Management**: First checks for an existing session and attempts to reuse it
2. **Authentication**: If no session exists, authenticate with provided credentials and save session for future use
3. **Wizard Navigation**: Navigate through a hidden 4-step wizard path:
   - Step 1: Select Data Source
   - Step 2: Choose Category  
   - Step 3: Select View Type
   - Step 4: View Products (reveals product data table)
4. **Data Extraction**: Capture all product data from the table, handling pagination/dynamic loading
5. **Export**: Export harvested data to structured JSON file for analysis
6. **Submission**: Submit solution via GitHub repository

---

## 🚀 Features

- ✅ **Smart Session Management**: Automatically detects and reuses existing sessions to avoid repeated logins
- ✅ **Robust Authentication**: Handles login process with credential validation and session persistence
- ✅ **Intelligent Wizard Navigation**: Auto-detects current wizard step and progresses through the flow
- ✅ **Comprehensive Data Extraction**: Extracts all product fields (ID, name, category, inventory, cost, timestamps)
- ✅ **Advanced Pagination Handling**: Supports dynamic loading and infinite scroll patterns
- ✅ **Progress Tracking**: Real-time progress display with extraction rate and time estimates
- ✅ **Graceful Error Handling**: Smart waiting strategies and exception management
- ✅ **Data Integrity**: Auto-save, backup creation, and corruption prevention
- ✅ **Resumable Extraction**: Can resume from interruption without losing progress

---

## 📋 Prerequisites

- Python 3.8 or higher
- Git (for cloning and submission)

---

## ⚙️ Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/poovarasansivakumar2003/playwright-tests
cd playwright-tests
```

### 2. Create Virtual Environment (Recommended)
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
# Install Playwright
pip install playwright

# Install Playwright browsers
playwright install
```

### 4. Clean Previous Data (Important!)
Before running the script, **delete any existing data files** to avoid conflicts with previous runs:

**For Command Prompt (Windows):**
```cmd
Remove-Item products_data.json -ErrorAction SilentlyContinue
Remove-Item backups -Recurse -Force -ErrorAction SilentlyContinue
```

**For macOS/Linux:**
```bash
# Delete previous session and data files
rm -f products_data.json
rm -rf backups
```

**Note**: This ensures a clean extraction without mixing old and new data.

---

## 🏃‍♂️ Usage

### Run the Script
```bash
python main.py
```

The script will:
1. Check for existing session, login if needed
2. Navigate through the wizard automatically  
3. Extract all product data with progress tracking
4. Save results to `products_data.json`

### Output Files
- **`products_data.json`**: Main output file with all extracted products
- **`session_state.json`**: Saved browser session for reuse
- **`backups/`**: Automatic backups and error recovery files

---

```
playwright-tests/
├── backups/                # Backup folder (generated)
├── LICENSE                 # License file
├── main.py                 # Main automation script
├── products_data.json      # Extracted product data (generated)
├── README.md               # This file
├── session_state.json      # Saved browser session (generated)
├── venv/                   # Virtual environment folder
└── .gitignore              # Git ignore file
```
```

---

## 🔧 Configuration

Key configuration options in `main.py`:

```python
CONFIG = {
    'base_url': 'https://hiring.idenhq.com/',
    'email': 'your-email@domain.com',          # Update with your credentials
    'password': 'your-password',               # Update with your credentials
    'session_file': 'session_state.json',
    'output_file': 'products_data.json',
    'backup_dir': 'backups',
    'timeout': 30000,  # 30 seconds
    'scroll_pause': 1.5,  # Optimized scroll pause time
    'autosave_threshold': 100,  # Save more frequently
    'progress_update_interval': 5  # Update progress display every N seconds
}
```

---

## 🎮 Script Features

### Progress Tracking
The script provides real-time progress updates:
```
Progress: [████████████████░░░░░░░░░░░░░░] 245/400 (61.3%) | Rate: 32.4 items/min | Elapsed: 0:07:34 | Est. remaining: 0:04:47
```

### Data Structure
Each product contains:
```json
{
  "id": "12345",
  "name": "Product Name",
  "category": "Electronics", 
  "inventory": "42",
  "cost": "$29.99",
  "modified": "2024-01-15",
  "updated": "2 days ago"
}
```

### Error Recovery
- **Ctrl+C Handling**: Gracefully saves progress before exit
- **Auto-backup**: Creates timestamped backups during extraction
- **Resume Support**: Can continue from where it left off
- **Session Recovery**: Reuses browser sessions across runs

---

## 🐛 Troubleshooting

### Common Issues

1. **Login Failed**: Verify credentials and internet connection
2. **Wizard Navigation Failed**: Check if website structure changed
3. **No Products Found**: Ensure wizard completed successfully

### Getting Help

If you encounter issues:
1. Check the console output for specific error messages
2. Review the backup files in `backups/` folder
3. Try deleting session files and running with fresh login
4. Ensure Python and Playwright are properly installed

---

## 🏆 Excellence Strategies Implemented

✅ **Smart Waiting**: Dynamic element waiting with timeout handling  
✅ **Robust Pagination**: Advanced scroll detection and lazy-loading support  
✅ **Session Management**: Persistent browser sessions across runs  
✅ **Clean Code**: Well-documented, modular, and maintainable Python code  
✅ **Exception Handling**: Comprehensive error recovery and logging  
✅ **Data Integrity**: Auto-save, backups, and corruption prevention  

---

## 📄 License

This project is created for the IDEN Data Extraction Challenge.