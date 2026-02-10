# California Drywall Contract Review - Redesigned Application

## Single-Page Application with Top Navigation

The application has been completely redesigned with a professional, clean interface.

### To Run:

```bash
streamlit run app_main.py
```

## What's New:

### Professional Design
- **Top Navigation Bar** - User name, role badge, and sign out button always visible
- **No Sidebar** - Clean, full-width interface
- **No Emoji Icons** - Professional, corporate design
- **California Drywall Branding** - Black, white, and gray color scheme matching www.caldrywall.com
- **Dashboard Cards** - Click cards to navigate between sections

### Fully Integrated Features

#### For Project Managers:
- **Submit Contracts** - Upload prime and/or subcontract PDFs
- **AI Analysis** - Automatic contract analysis with red flag identification
- **Comparison Mode** - Upload both contracts for flow-down analysis
- **Project Submission** - Submit for executive review

#### For Executives:
- **Review Contracts** - View all submitted projects
- **Detailed Analysis** - Review AI findings and red flags
- **Download Files** - Access original contracts and analysis reports
- **Approve/Reject** - Take action on submissions
- **Track Status** - Monitor project workflow

### Navigation Flow:

1. **Login** - Sign in with your California Drywall credentials
2. **Dashboard** - See role-specific features as clickable cards
3. **Click Any Card** - Navigate to that section
4. **Top Bar Navigation** - Always see buttons to switch pages or sign out
5. **Return to Dashboard** - Use buttons or navigation to go back

### User Accounts:

- **Project Manager**: mw@caldrywall.com
- **Executives**: dg@caldrywall.com, pg@caldrywall.com

### Color Scheme:

Matching www.caldrywall.com:
- Primary: Black (#000000)
- Secondary: Dark Gray (#32373c)
- Accents: Light Gray (#abb8c3)
- Backgrounds: White / Light Gray (#f5f5f5)

## Features:

### PM Submission:
- PDF upload for prime contracts
- PDF upload for subcontracts
- Dual contract comparison analysis
- Improved PDF text extraction (pdfplumber + PyPDF2)
- Automated red flag identification
- Automatic project submission

### Executive Review:
- List all submitted projects
- Filter by status
- View project details
- Review analysis results
- Download original contracts
- Download analysis reports (JSON)
- Mark red flags as reviewed/resolved
- Approve/reject projects
- Change project status

### Design:
- No decorative icons
- Professional button styling
- Clean card-based layouts
- California Drywall branding throughout
- Consistent top navigation
- Full-width content areas

## Installation:

If you haven't installed dependencies:

```bash
pip install -r requirements.txt
```

Or use the batch file:
```bash
install_dependencies.bat
```

## Notes:

- The old multi-page app (Home.py) still exists but is deprecated
- All functionality is now in `app_main.py`
- Pages are in the `pages/` directory as modules
- Admin panel integration coming soon

---

© 2025 California Drywall Co.
