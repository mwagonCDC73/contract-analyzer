# California Drywall Contract Review System

Contract analysis system for wall & ceiling specialty contractors.

## 🚀 Quick Start

### Run the Application

```bash
streamlit run Home.py
```

This will start the unified multi-page application at `http://localhost:8501`

### First Time Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   Create a `.env` file in the project root:
   ```env
   ANTHROPIC_API_KEY=your_api_key_here
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
   ```

3. **Login**
   - Project Managers: Use your PM credentials
   - Executives: Use executive credentials (dg@caldrywall.com, pg@caldrywall.com)

## 📋 Application Structure

### Home Page (Home.py)
- Unified login for all users
- Role-based dashboard
- Quick navigation to all features
- System statistics

### Pages

#### 1. 📋 PM Submit (pages/1_📋_PM_Submit.py)
**For: Project Managers**
- Upload and analyze contracts
- Submit for executive review
- View analysis results
- Download reports

#### 2. 👔 Executive Review (pages/2_👔_Executive_Review.py)
**For: Executives & Admins**
- Review submitted projects
- Approve/reject contracts
- View detailed analysis
- Download original contracts
- Track red flags

#### 3. ⚙️ Admin Panel (pages/3_⚙️_Admin_Panel.py)
**For: Executives & Admins**
- Manage projects
- Archive or delete projects
- Bulk actions
- System statistics

## 👥 User Roles

### Project Manager
- Submit contracts for review
- View analysis results
- Track submission status

### Executive
- Review and approve contracts
- Access all executive features
- Manage projects (admin panel)

### Admin
- All executive permissions
- Full system management
- User management (coming soon)

## 🔧 Maintenance Tools

### Admin Panel (GUI)
```bash
streamlit run Home.py
```
Then navigate to Admin Panel page

### Cleanup Script (CLI)
```bash
python cleanup_database.py
```
For bulk data management and complete resets

## 📁 File Structure

```
contract-analyzer/
├── Home.py                      # Main entry point
├── pages/
│   ├── 1_📋_PM_Submit.py        # PM submission form
│   ├── 2_👔_Executive_Review.py # Executive review dashboard
│   └── 3_⚙️_Admin_Panel.py      # Admin management panel
├── db_utils.py                  # Database utilities
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (create this)
├── cleanup_database.py          # CLI cleanup tool
├── ADMIN_GUIDE.md              # Admin documentation
└── README.md                    # This file
```

## 🎨 Features

### Automated Analysis
- Automated contract review
- Risk identification and categorization
- California-specific compliance checks
- Business impact assessment

### Workflow Management
- PM submission workflow
- Executive review and approval
- Status tracking
- Project archiving

### Document Management
- PDF upload and text extraction
- Original contract download
- Analysis report export
- Multiple contract types

## 🔐 Security

- Supabase authentication
- Role-based access control
- Secure file storage
- Session management

## 🆘 Troubleshooting

### Can't Login
1. Check credentials with your administrator
2. Ensure user profile exists in database
3. Verify role permissions

### PDF Extraction Issues
- System uses both pdfplumber and PyPDF2
- If extraction fails, try pasting text manually
- Scanned PDFs require OCR (not supported yet)

### Navigation Issues
- Always start from `Home.py`
- Use sidebar navigation between pages
- Don't run individual page files directly

## 📞 Support

For support contact your IT department or project management office.

## 📝 Version History

- **v2.0** - Multi-page unified application
- **v1.0** - Initial separate apps

---

© 2025 California Drywall Co.
