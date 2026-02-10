import streamlit as st
import requests
import json
from datetime import datetime
import os
from dotenv import load_dotenv
from PyPDF2 import PdfReader
import pdfplumber
import io
import re

# Load environment variables (override=True ensures .env file takes precedence)
load_dotenv(override=True)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Debug: Show API key status (only first/last 4 chars for security)
if ANTHROPIC_API_KEY:
    key_preview = f"{ANTHROPIC_API_KEY[:7]}...{ANTHROPIC_API_KEY[-4:]}" if len(ANTHROPIC_API_KEY) > 11 else "KEY_TOO_SHORT"
    print(f"✓ API Key loaded: {key_preview} (length: {len(ANTHROPIC_API_KEY)})")
else:
    print("✗ API Key NOT loaded from .env file")

# Page configuration
st.set_page_config(
    page_title="California Drywall - Contract Analyzer",
    layout="wide"
)

# Initialize session state
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'uploaded_file_name' not in st.session_state:
    st.session_state.uploaded_file_name = None

# Sidebar for authentication and settings
with st.sidebar:
    st.title("Contract Analyzer")
    
    # Simple authentication (replace with proper auth later)
    user_role = st.selectbox(
        "Login as:",
        ["Project Manager", "Executive", "Admin"]
    )
    
    st.divider()
    st.caption("Version 2.0.0")
    st.caption("© 2025 California Drywall Co.")

# Main header
st.title("California Drywall Contract Analyzer")
st.markdown("**Contract analysis specialized for wall & ceiling specialty subcontractor agreements**")
st.caption("Customized for California Drywall's operations, risk profile, and project types")
st.divider()

# Contract analysis prompt template - Customized for California Drywall Co.
CONTRACT_ANALYSIS_PROMPT = """You are an expert construction contract analyst specializing in wall and ceiling specialty subcontractor agreements.

CONTEXT: You are analyzing this contract for California Drywall Co., the largest wall and ceiling specialty contractor in California (#8 nationally). They are a 100% employee-owned (ESOP) company with ~600 employees and 700+ union craftsmen, operating throughout Northern California and the Central Valley. They provide metal framing, drywall, acoustical ceilings, fireproofing, insulation, lath/plaster, and related systems for commercial, healthcare (OSHPD-certified), education, technology campus, and multi-family residential projects ranging from $10K to $17M+. They have advanced BIM/VDC capabilities, a 63,000 SF prefabrication facility, and extensive experience with traditional, design-build, design-assist, and IPD project delivery methods. Their culture emphasizes safety (0.49 EMR), quality, innovation, and long-term client relationships (95% repeat business).

Analyze the following construction contract and provide a comprehensive analysis focusing on:

1. **Critical Issues** - Must be resolved before signing (deal-breakers, missing critical terms, unacceptable risk allocation)
2. **Warnings** - Items requiring negotiation or clarification (unfavorable terms, ambiguous language, business risks)
3. **Informational** - Items to be aware of (standard clauses, best practices, recommendations for project execution)

For each issue found, provide:
- Category (see categories below)
- Severity (critical, warning, informational)
- Specific issue description with context for California Drywall's operations
- Exact location in contract (Article, Section, Page)
- Recommendation for project manager specific to their business model

PRIORITY RISK AREAS FOR WALL & CEILING SPECIALTY SUBCONTRACTORS:

**Scope & Coordination Issues:**
- Incomplete or ambiguous scope definition for wall/ceiling systems
- Unclear division of work between trades (who provides backing, blocking, framing for others)
- Missing or referenced specifications/drawings not attached
- Responsibility for layout, as-builts, and coordination drawings
- BIM/VDC model ownership, access rights, and coordination obligations
- Prefabrication/offsite manufacturing provisions and site access for delivery
- Interface coordination with MEP, structural, and architectural trades
- Responsibility for fire-rated assemblies, firestopping, and acoustic performance testing

**Schedule & Performance Risks:**
- Unrealistic schedule for wall/ceiling scope of work
- Inadequate time for shop drawing submittals and approvals
- No provisions for schedule delays caused by others (MEP, prior trades, owner changes)
- Liquidated damages excessive or uncapped for subcontractor scope
- "No damage for delay" clauses that prevent recovery of extended general conditions
- Substantial completion criteria unclear or dependent on other trades
- Warranty period starts before building occupancy/commissioning complete

**Payment & Cash Flow Concerns:**
- Payment terms longer than 30 days after GC receives owner payment (creates cash flow strain)
- Retainage over 5% or not released at substantial completion
- Front-loaded or unbalanced payment schedule that disadvantages subcontractor
- Pay-when-paid vs pay-if-paid clauses (pay-if-paid is high risk)
- Insufficient payment for stored materials (especially for prefabricated components)
- No provision for payment of undisputed amounts during disputes
- Administrative burden for payment applications (excessive documentation)
- Withholding rights too broad or not limited to disputed amounts

**Change Order & Extra Work Provisions:**
- GC has unilateral right to direct changes without price agreement
- Markup limitations on change orders (materials, labor, equipment, subcontractors)
- No compensation for impact costs, acceleration, or delay damages
- "Constructive change" process unclear or non-existent
- Strict notice requirements for extra work (may waive claims if not followed exactly)
- Time limits for pricing changes that don't account for subcontractor's estimating needs
- No provision for time extensions due to changes
- Force account (time and material) rates not specified or inadequate

**Safety & Site Conditions:**
- Safety responsibilities unclear or subcontractor assumes liability for GC/Owner failures
- Site access, laydown area, and material storage not specified (critical for prefab delivery)
- Utility locations, hoisting, and scaffolding provisions inadequate
- Environmental/hazardous materials responsibility unclear
- OSHA compliance coordination and multi-employer worksite citations
- Site security and theft/vandage responsibility

**Insurance & Risk Allocation:**
- Additional insured requirements not standard or require "primary and non-contributory"
- Waiver of subrogation missing (subcontractor's insurer can sue GC/Owner)
- Insurance limits excessive for subcontractor scope (GL, Auto, Umbrella, Workers Comp)
- Subcontractor required to indemnify for GC's sole negligence (may be unenforceable in CA)
- Wrap-up insurance (OCIP/CCIP) terms unclear regarding premium credits and deductibles
- Builders risk insurance gaps or subcontractor responsible for property insurance
- Professional liability insurance required but subcontractor provides no design services

**Labor & Union Considerations:**
- Project labor agreement (PLA) requirements not specified or conflict with existing agreements
- Prevailing wage requirements (CA DIR registration, CPRs, payroll compliance)
- Apprenticeship requirements under CA Labor Code
- Union jurisdiction conflicts between carpenters, laborers, painters, ironworkers
- Working hours restrictions and overtime approval process
- Non-union substitution clauses that conflict with collective bargaining agreements

**California-Specific & OSHPD Projects:**
- For OSHPD hospital projects: special inspection requirements, IOR coordination, seismic certification
- California prompt payment laws (CA Civil Code §8800 - subcontractor payment within 7 days)
- Stop notice rights preserved (CA Civil Code §8500-8560 for private projects)
- Mechanics lien rights not waived prematurely
- California indemnity limitations (CA Civil Code §2782 - can't indemnify for indemnitor's negligence)
- Title 24 energy compliance responsibilities
- CALGreen sustainable building requirements

**Dispute Resolution:**
- Mandatory arbitration vs litigation (arbitration can be expensive for subcontractors)
- Venue/jurisdiction outside Northern California
- Waiver of jury trial
- Prevailing party attorney's fees (double-edged sword)
- Limitations on consequential damages claims by subcontractor
- Short statute of limitations or notice of claim periods
- No "step" dispute resolution (escalation from PM to executives before arbitration)

**Technology & Intellectual Property:**
- BIM model ownership and permitted uses after project completion
- Proprietary prefabrication designs and shop drawings ownership
- Software/technology requirements imposed without compensation
- Digital collaboration platform costs passed to subcontractor

**Termination & Suspension:**
- Termination for convenience with inadequate compensation (profit on uncompleted work)
- Termination for cause without cure period or opportunity to remedy
- Suspension of work without compensation for standby costs and demobilization/remobilization
- Assignment and subcontracting restrictions too broad

**Documentation & Administrative Burdens:**
- Excessive submittals, RFIs, meeting attendance, and documentation requirements
- As-built drawings and O&M manuals beyond reasonable scope
- Closeout requirements that delay final payment unreasonably
- Warranty service response times that require dedicated service staff

CATEGORIES FOR FINDINGS:
- Scope of Work
- Schedule & Milestones
- Payment Terms
- Retainage
- Change Orders & Extra Work
- Insurance & Bonding
- Indemnification & Liability
- Safety & Site Conditions
- Labor & Union Compliance
- California Legal Compliance
- OSHPD & Healthcare Projects
- Coordination & BIM/VDC
- Prefabrication & Materials
- Warranties & Guarantees
- Dispute Resolution
- Termination & Suspension
- Administrative Requirements
- Risk Allocation

Format your response as a JSON object with this structure:
{{
  "summary": {{
    "total_issues": <number>,
    "critical": <number>,
    "warning": <number>,
    "informational": <number>,
    "risk_level": "<HIGH|MODERATE|LOW>",
    "recommendation": "<brief overall recommendation: NEGOTIATE MAJOR TERMS|ACCEPTABLE WITH MINOR CHANGES|PROCEED AS-IS>"
  }},
  "findings": [
    {{
      "category": "<category from list above>",
      "severity": "<critical|warning|informational>",
      "issue": "<brief title>",
      "details": "<detailed explanation of the issue and why it matters to California Drywall>",
      "location": "<Article X, Section Y, Page Z>",
      "recommendation": "<specific action to take - negotiate, clarify, add provision, seek legal review, etc.>",
      "business_impact": "<how this affects California Drywall's operations, cash flow, risk exposure, or profitability>"
    }}
  ]
}}

CONTRACT TEXT:
{contract_text}
"""

def analyze_contract_with_claude(contract_text, api_key):
    """Analyze contract using Claude API via direct HTTP request"""
    try:
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        data = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 8000,
            "messages": [
                {
                    "role": "user",
                    "content": CONTRACT_ANALYSIS_PROMPT.format(contract_text=contract_text)
                }
            ]
        }
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data,
            timeout=120
        )
        
        if response.status_code != 200:
            st.error(f"API Error: {response.status_code}")
            st.error(f"Response: {response.text}")
            return None
        
        result = response.json()
        response_text = result['content'][0]['text']
        
        # Find JSON in response (Claude might wrap it in markdown)
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        
        return json.loads(response_text)
    
    except Exception as e:
        st.error(f"Error analyzing contract: {str(e)}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")
        return None

def display_severity_badge(severity):
    """Display colored badge for severity level"""
    colors = {
        "critical": "",
        "warning": "",
        "informational": ""
    }
    return colors.get(severity, "")

def clean_extracted_text(text):
    """Clean extracted text to remove problematic characters and normalize formatting"""
    if not text:
        return None

    # Remove null bytes and other control characters except newlines and tabs
    text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F-\x9F]', '', text)

    # Normalize unicode characters
    text = text.encode('ascii', 'ignore').decode('ascii')

    # Replace multiple spaces with single space
    text = re.sub(r' +', ' ', text)

    # Replace multiple newlines with double newline
    text = re.sub(r'\n\n+', '\n\n', text)

    # Remove leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)

    return text.strip()


def extract_text_from_pdf(uploaded_file):
    """Extract text from PDF file using pdfplumber (better quality) with fallback to PyPDF2"""
    try:
        # Reset file pointer
        uploaded_file.seek(0)
        file_bytes = uploaded_file.read()

        # Try pdfplumber first (better extraction quality)
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                text = ""
                for page_num, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"

                if text.strip():
                    cleaned_text = clean_extracted_text(text)
                    if cleaned_text and len(cleaned_text) > 100:  # Ensure we got meaningful text
                        st.success(f"PDF extracted successfully using pdfplumber - {len(cleaned_text)} characters")
                        return cleaned_text
        except Exception as e:
            st.warning(f"pdfplumber extraction failed, trying PyPDF2: {str(e)}")

        # Fallback to PyPDF2 if pdfplumber fails
        try:
            pdf_reader = PdfReader(io.BytesIO(file_bytes))
            text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"

            if text.strip():
                cleaned_text = clean_extracted_text(text)
                if cleaned_text and len(cleaned_text) > 100:
                    st.success(f"PDF extracted successfully using PyPDF2 - {len(cleaned_text)} characters")
                    return cleaned_text
        except Exception as e:
            st.error(f"PyPDF2 extraction also failed: {str(e)}")

        # If both methods failed to extract meaningful text
        st.error("Failed to extract text from PDF. The file may be:")
        st.error("  - A scanned image (requires OCR)")
        st.error("  - Password protected")
        st.error("  - Corrupted or invalid format")
        return None

    except Exception as e:
        st.error(f"Error reading PDF: {str(e)}")
        return None

# File upload section
st.header("Upload Contract")

uploaded_file = st.file_uploader(
    "Upload construction contract (PDF or Word)",
    type=['pdf', 'docx', 'doc', 'txt'],
    help="Supported formats: PDF, Word (.docx, .doc), or plain text"
)

contract_text = None

if uploaded_file:
    st.session_state.uploaded_file_name = uploaded_file.name
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.success(f"Uploaded: {uploaded_file.name}")
    with col2:
        st.metric("File Size", f"{uploaded_file.size / 1024:.1f} KB")
    with col3:
        st.metric("Type", uploaded_file.type.split('/')[-1].upper())
    
    # Read file content
    try:
        if uploaded_file.type == "text/plain":
            contract_text = uploaded_file.read().decode('utf-8')
            st.info("Text file loaded successfully")
        elif uploaded_file.type == "application/pdf":
            with st.spinner("Extracting text from PDF..."):
                contract_text = extract_text_from_pdf(uploaded_file)
                if not contract_text:
                    st.error("Could not extract readable text. Please try pasting the text manually below.")
        elif "word" in uploaded_file.type or uploaded_file.name.endswith(('.doc', '.docx')):
            st.warning("Word document parsing requires additional libraries. For now, please use .txt or PDF file, or paste text below.")
            contract_text = None
        else:
            # Try to read as text for other file types
            contract_text = uploaded_file.read().decode('utf-8')
            st.info("File loaded successfully")
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        contract_text = None

# Manual text input option
with st.expander("Or paste contract text manually"):
    manual_text = st.text_area(
        "Paste contract text here",
        height=200,
        placeholder="Paste the full contract text here for analysis..."
    )
    if manual_text:
        contract_text = manual_text

# Analysis button
st.divider()

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    analyze_button = st.button(
        "Analyze Contract",
        type="primary",
        use_container_width=True,
        disabled=not ANTHROPIC_API_KEY or not contract_text
    )

if not ANTHROPIC_API_KEY:
    st.error("ANTHROPIC_API_KEY not found in environment variables. Please check your .env file.")
    with st.expander("Troubleshooting"):
        st.markdown("""
        **Steps to fix:**
        1. Create/check `.env` file in project root: `C:\\dev\\cdc\\contractreading\\contract-analyzer\\.env`
        2. Add this line (replace with your actual key):
           ```
           ANTHROPIC_API_KEY=sk-ant-api03-xxxxx...
           ```
        3. Ensure no spaces around the `=` sign
        4. Ensure the key is complete (typically 100+ characters)
        5. Restart Streamlit: `streamlit run app.py`
        """)
elif len(ANTHROPIC_API_KEY) < 50:
    st.warning(f"API Key loaded but seems too short ({len(ANTHROPIC_API_KEY)} chars). Anthropic keys are typically 100+ characters.")
    st.info("Please verify your API key in the .env file is complete.")

if not contract_text and not uploaded_file:
    st.info("Please upload a contract file or paste contract text above")

# Perform analysis
if analyze_button and ANTHROPIC_API_KEY and contract_text:
    with st.spinner("AI analyzing contract... This may take 30-60 seconds..."):
        results = analyze_contract_with_claude(contract_text, ANTHROPIC_API_KEY)
        
        if results:
            st.session_state.analysis_results = results
            st.session_state.analysis_date = datetime.now()

# Display results
if st.session_state.analysis_results:
    results = st.session_state.analysis_results
    
    st.divider()
    st.header("Analysis Results")
    
    # Summary metrics
    st.subheader("Summary")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Issues",
            results['summary']['total_issues'],
            delta=None
        )
    with col2:
        st.metric(
            "Critical",
            results['summary']['critical'],
            delta=None,
            help="Must be resolved before signing"
        )
    with col3:
        st.metric(
            "Warnings",
            results['summary']['warning'],
            delta=None,
            help="Require attention or negotiation"
        )
    with col4:
        st.metric(
            "Informational",
            results['summary']['informational'],
            delta=None,
            help="Items to be aware of"
        )
    
    # Overall Risk Assessment
    risk_level = results['summary'].get('risk_level', 'UNKNOWN')
    overall_recommendation = results['summary'].get('recommendation', 'Review findings below')

    if risk_level == 'HIGH' or results['summary']['critical'] > 0:
        st.error(f"**HIGH RISK CONTRACT**")
        st.markdown(f"**{results['summary']['critical']} critical issues** must be resolved before contract execution")
        st.markdown(f"**Overall Recommendation:** {overall_recommendation}")
    elif risk_level == 'MODERATE' or results['summary']['warning'] > 3:
        st.warning(f"**MODERATE RISK CONTRACT**")
        st.markdown(f"**{results['summary']['warning']} warnings** require review and potential negotiation")
        st.markdown(f"**Overall Recommendation:** {overall_recommendation}")
    else:
        st.success(f"**LOW RISK CONTRACT**")
        st.markdown("No critical issues found. Review warnings before proceeding.")
        st.markdown(f"**Overall Recommendation:** {overall_recommendation}")
    
    st.divider()
    
    # Detailed findings
    st.subheader("Detailed Findings")
    
    # Filter options
    col1, col2 = st.columns([1, 3])
    with col1:
        severity_filter = st.multiselect(
            "Filter by severity:",
            ["critical", "warning", "informational"],
            default=["critical", "warning", "informational"]
        )
    
    # Display findings
    filtered_findings = [f for f in results['findings'] if f['severity'] in severity_filter]
    
    for idx, finding in enumerate(filtered_findings, 1):
        severity = finding['severity']
        
        # Color coding
        if severity == "critical":
            color = "red"
        elif severity == "warning":
            color = "orange"
        else:
            color = "blue"
        
        with st.container():
            st.markdown(f"""
            <div style="
                padding: 20px; 
                border-left: 4px solid {color}; 
                background-color: #f8f9fa; 
                border-radius: 5px;
                margin-bottom: 15px;
            ">
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{display_severity_badge(severity)} {finding['issue']}**")
            with col2:
                st.caption(f"{finding['category']}")
            
            st.markdown(f"**Details:** {finding['details']}")
            st.caption(f"📍 Location: {finding['location']}")

            # Business impact (if provided in the analysis)
            if 'business_impact' in finding and finding['business_impact']:
                st.warning(f"**Business Impact:** {finding['business_impact']}")

            st.info(f"**Recommendation:** {finding['recommendation']}")

            st.markdown("</div>", unsafe_allow_html=True)
    
    # Export options
    st.divider()
    st.subheader("Export Results")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # JSON export
        json_data = json.dumps(results, indent=2)
        st.download_button(
            label="Download JSON",
            data=json_data,
            file_name=f"contract_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    with col2:
        # Text report export
        report = f"""CONTRACT ANALYSIS REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
File: {st.session_state.uploaded_file_name or 'Manual Input'}

SUMMARY
=======
Total Issues: {results['summary']['total_issues']}
Critical: {results['summary']['critical']}
Warnings: {results['summary']['warning']}
Informational: {results['summary']['informational']}

DETAILED FINDINGS
=================

"""
        for idx, finding in enumerate(results['findings'], 1):
            report += f"""
{idx}. [{finding['severity'].upper()}] {finding['issue']}
   Category: {finding['category']}
   Details: {finding['details']}
   Location: {finding['location']}
   Recommendation: {finding['recommendation']}

"""
        
        st.download_button(
            label="Download Report",
            data=report,
            file_name=f"contract_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain"
        )
    
    with col3:
        if st.button("Analyze Another Contract"):
            st.session_state.analysis_results = None
            st.session_state.uploaded_file_name = None
            st.rerun()

# Footer
st.divider()
st.caption("""
**California Drywall Contract Analyzer**
For support, contact your IT department or project management office.
""")
