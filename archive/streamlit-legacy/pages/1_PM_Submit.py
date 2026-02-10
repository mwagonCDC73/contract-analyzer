"""
PM Submission Form - California Drywall Contract Review System
Allows Project Managers to submit contracts for executive review
"""

import streamlit as st
import os
from dotenv import load_dotenv
import requests
import json
from datetime import datetime
import PyPDF2
import pdfplumber
import io
import re

# Import database utilities
import db_utils
import components

# Load environment variables (override=True ensures .env file takes precedence over system env vars)
load_dotenv(override=True)

# Debug: Verify API key is loaded correctly
_api_key_check = os.getenv("ANTHROPIC_API_KEY")
if _api_key_check:
    print(f"✓ ANTHROPIC_API_KEY loaded: {len(_api_key_check)} characters")
    print(f"  Preview: {_api_key_check[:10]}...{_api_key_check[-8:]}")
else:
    print("✗ ANTHROPIC_API_KEY not found in environment")

# Check authentication (inherited from Home.py)
if not st.session_state.get('authenticated', False):
    st.error("Please log in from the Home page first")
    st.stop()

# Check if user profile exists
if not st.session_state.get('user_profile'):
    st.error("User profile not found. Please log in again.")
    st.stop()


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


def extract_text_from_pdf(file):
    """Extract text from PDF file using pdfplumber (better quality) with fallback to PyPDF2"""
    try:
        file_bytes = file.getvalue()

        # Try pdfplumber first (better extraction quality)
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"

                if text.strip():
                    cleaned_text = clean_extracted_text(text)
                    if cleaned_text and len(cleaned_text) > 100:
                        return cleaned_text
        except Exception as e:
            print(f"pdfplumber extraction failed, trying PyPDF2: {str(e)}")

        # Fallback to PyPDF2
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"

            if text.strip():
                cleaned_text = clean_extracted_text(text)
                if cleaned_text and len(cleaned_text) > 100:
                    return cleaned_text
        except Exception as e:
            print(f"PyPDF2 extraction also failed: {str(e)}")

        st.error("Failed to extract text from PDF. File may be scanned, encrypted, or corrupted.")
        return None

    except Exception as e:
        st.error(f"Error extracting PDF text: {str(e)}")
        return None


def analyze_contract_with_claude(contract_text, api_key, contract_type="single", comparison_text=None):
    """Analyze contract using Claude API

    Args:
        contract_text: Main contract text to analyze
        api_key: Anthropic API key
        contract_type: "single" for one contract, "comparison" for prime+sub analysis
        comparison_text: Second contract text (for comparison mode)
    """

    # DEBUG - Check API key
    st.write("**DEBUG - API Key Check:**")
    if api_key:
        st.write(f"   - Key starts with: `{api_key[:15]}...`")
        st.write(f"   - Key length: {len(api_key)} characters")
        st.write(f"   - Starts with 'sk-ant-': {api_key.startswith('sk-ant-')}")
    else:
        st.error("   - API Key is None or empty!")
        return None

    if contract_type == "comparison" and comparison_text:
        # Dual contract comparison analysis
        prompt = """You are an expert construction contract analyst specializing in wall and ceiling specialty subcontractor agreements for California Drywall Co.

You are analyzing BOTH a prime contract and a subcontract together to identify:
1. Red flags in each contract individually
2. Flow-down clause issues between prime and subcontract
3. Gaps or conflicts between the two agreements

PRIME CONTRACT:
{prime_text}

---

SUBCONTRACT:
{sub_text}

Provide comprehensive analysis covering:

**A. PRIME CONTRACT RED FLAGS:**
- Payment terms and cash flow
- Schedule and performance requirements
- Insurance and bonding requirements
- Scope definition gaps
- Risk allocation concerns
- Change order provisions
- Dispute resolution terms

**B. SUBCONTRACT RED FLAGS:**
- All of the above, from subcontractor perspective
- Pay-when-paid vs pay-if-paid clauses
- Retainage provisions
- Warranty requirements
- Indemnification scope

**C. FLOW-DOWN & COMPARISON ISSUES:**
- Are prime contract obligations properly flowed down to subcontract?
- Payment timing gaps (e.g., prime gets paid Net-30, but sub must wait Net-60)
- Insurance requirements gaps (sub required to carry more than prime)
- Schedule constraints not aligned
- Change order markup inconsistencies
- Liquidated damages passed through without caps
- Dispute resolution method conflicts
- Missing flow-down provisions that create liability gaps

Format response as JSON:
{{
  "summary": {{
    "total_issues": <number>,
    "critical": <number>,
    "warning": <number>,
    "informational": <number>,
    "comparison_issues": <number of flow-down/gap issues>
  }},
  "findings": [
    {{
      "contract": "<prime|subcontract|both>",
      "category": "<category>",
      "severity": "<critical|warning|informational>",
      "issue": "<brief title>",
      "details": "<detailed explanation>",
      "location": "<Article X, Section Y>",
      "recommendation": "<action to take>"
    }}
  ]
}}
"""
        prompt = prompt.format(prime_text=contract_text[:40000], sub_text=comparison_text[:40000])
    else:
        # Single contract analysis
        prompt = """You are an expert construction contract analyst specializing in wall and ceiling specialty subcontractor agreements for California Drywall Co.

Analyze the following construction contract and provide comprehensive red flag analysis focusing on:

1. **Critical Issues** - Must be resolved before signing (deal-breakers, missing critical terms, unacceptable risk allocation)
2. **Warnings** - Items requiring negotiation or clarification (unfavorable terms, ambiguous language, business risks)
3. **Informational** - Items to be aware of (standard clauses, best practices, recommendations)

**Key Risk Areas to Examine:**

**Payment & Cash Flow:**
- Payment timing (Net-30? Net-60? Pay-when-paid vs pay-if-paid?)
- Retainage percentage and release timing
- Stored materials payment provisions
- Payment for extra work/changes
- Administrative burden for payment applications

**Schedule & Performance:**
- Realistic timelines for wall/ceiling scope
- Shop drawing submittal time
- Liquidated damages (capped? reasonable?)
- "No damage for delay" clauses
- Substantial completion criteria

**Scope & Coordination:**
- Clear scope definition for wall/ceiling systems
- Division of work between trades (backing, blocking, framing for others)
- BIM/VDC coordination requirements
- Prefabrication provisions and site access
- Fire-rated assemblies and acoustic testing responsibility

**Insurance & Risk:**
- Insurance requirements (reasonable for subcontractor?)
- Indemnification scope (for GC's sole negligence?)
- Waiver of subrogation
- OCIP/CCIP provisions

**Change Orders:**
- Unilateral change directives
- Markup limitations
- Notice requirements
- Time extension provisions

**California-Specific:**
- Prompt payment compliance (Civil Code §8800)
- Stop notice rights preserved
- Mechanics lien rights
- Indemnity limitations (Civil Code §2782)
- OSHPD requirements (if applicable)
- Prevailing wage compliance

**Dispute Resolution:**
- Arbitration vs litigation
- Venue/jurisdiction
- Attorney's fees provisions
- Step dispute resolution process

Format response as JSON:
{{
  "summary": {{
    "total_issues": <number>,
    "critical": <number>,
    "warning": <number>,
    "informational": <number>
  }},
  "findings": [
    {{
      "category": "<category>",
      "severity": "<critical|warning|informational>",
      "issue": "<brief title>",
      "details": "<detailed explanation with California Drywall context>",
      "location": "<Article X, Section Y>",
      "recommendation": "<specific action to take>"
    }}
  ]
}}

CONTRACT TEXT:
{contract_text}
"""
        prompt = prompt.format(contract_text=contract_text[:50000])
    
    try:
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        st.write(f"**DEBUG - Making API call to Anthropic...**")
        
        data = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 8000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt  # Already formatted above
                }
            ]
        }
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data,
            timeout=120
        )
        
        st.write(f"**DEBUG - API Response Status:** {response.status_code}")
        
        if response.status_code != 200:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
        
        result = response.json()
        response_text = result['content'][0]['text']
        
        # Find JSON in response
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
        return None


def submission_form():
    """Display project submission form"""

    # Add global styles and render unified header
    components.add_global_styles()
    components.render_header(current_page='pm_submit')

    # Page title
    components.render_page_title(
        "Submit Contract for Review",
        "Upload and analyze contracts with automated review"
    )
    
    # Project Information
    st.subheader("Project Information")
    
    with st.form("project_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            project_name = st.text_input(
                "Project Name *",
                placeholder="e.g., Mission Street Office Renovation"
            )
        
        with col2:
            project_number = st.text_input(
                "Project Number (Optional)",
                placeholder="e.g., 2025-001"
            )
        
        pm_notes = st.text_area(
            "Notes / Context (Optional)",
            placeholder="Add any important notes or context for the executive review...",
            height=100
        )
        
        st.divider()
        
        # File Uploads
        st.subheader("Contract Documents")
        st.caption("At least ONE contract is required (you can upload Prime, Subcontract, or both)")
        st.info("**Tip:** Upload BOTH contracts for comparison analysis that checks flow-down clauses and identifies gaps between prime and subcontract terms!")

        col1, col2 = st.columns(2)

        with col1:
            prime_contract = st.file_uploader(
                "Prime Contract (Optional)",
                type=['pdf', 'docx', 'doc'],
                help="Upload the main/general contractor agreement"
            )

        with col2:
            subcontract = st.file_uploader(
                "Subcontract (Optional)",
                type=['pdf', 'docx', 'doc'],
                help="Upload the specialty subcontractor agreement"
            )
        
        st.divider()
        
        # Submit button
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            submit_button = st.form_submit_button(
                "Submit for Executive Review",
                use_container_width=True,
                type="primary"
            )
        
        if submit_button:
            # Validation
            if not project_name:
                st.error("Project name is required")
                return

            if not prime_contract and not subcontract:
                st.error("At least one contract document is required (Prime or Subcontract)")
                return

            # Process submission
            process_submission(
                project_name,
                project_number,
                pm_notes,
                prime_contract,
                subcontract
            )


def process_submission(project_name, project_number, pm_notes, prime_contract, subcontract):
    """Process the contract submission - handles one or both contracts"""

    progress_bar = st.progress(0)
    status_text = st.empty()

    # Track which contracts we have
    has_prime = prime_contract is not None
    has_sub = subcontract is not None

    try:
        # Step 1: Create project
        status_text.text("Creating project...")
        progress_bar.progress(10)

        project_data = {
            "project_name": project_name,
            "project_number": project_number,
            "pm_notes": pm_notes
        }

        project = db_utils.create_project(project_data, st.session_state.user.id)

        if not project:
            st.error("Failed to create project")
            return

        project_id = project['id']

        # Track contract records and texts
        prime_contract_record = None
        sub_contract_record = None
        prime_text = None
        sub_text = None

        # Step 2: Upload prime contract (if provided)
        if has_prime:
            status_text.text("Uploading prime contract...")
            progress_bar.progress(20)

            prime_file_info = db_utils.upload_contract_file(prime_contract, project_id, "prime")
            if not prime_file_info:
                st.error("Failed to upload prime contract")
                return

            prime_contract_record = db_utils.create_contract_record(project_id, "prime", prime_file_info)

            # Extract text from prime contract
            status_text.text("Extracting text from prime contract...")
            progress_bar.progress(30)
            prime_text = extract_text_from_pdf(prime_contract)
            if not prime_text:
                st.warning("Could not extract text from prime contract PDF")

        # Step 3: Upload subcontract (if provided)
        if has_sub:
            status_text.text("Uploading subcontract...")
            progress_bar.progress(40)

            sub_file_info = db_utils.upload_contract_file(subcontract, project_id, "subcontract")
            if not sub_file_info:
                st.error("Failed to upload subcontract")
                return

            sub_contract_record = db_utils.create_contract_record(project_id, "subcontract", sub_file_info)

            # Extract text from subcontract
            status_text.text("Extracting text from subcontract...")
            progress_bar.progress(50)
            sub_text = extract_text_from_pdf(subcontract)
            if not sub_text:
                st.warning("Could not extract text from subcontract PDF")

        # Step 4: AI Analysis
        if not prime_text and not sub_text:
            st.warning("Could not extract text from any PDFs. Skipping automated analysis.")
        else:
            # Get API key
            status_text.text("Loading API credentials...")
            progress_bar.progress(55)

            api_key = os.getenv("ANTHROPIC_API_KEY")

            st.write("---")
            st.write("### API Key Debug Information")
            if not api_key:
                st.error("ANTHROPIC_API_KEY not found in .env file!")
                st.info("Make sure your .env file contains: ANTHROPIC_API_KEY=sk-ant-...")
                # Don't return - continue with upload even if analysis fails
            else:
                st.success(f"API key loaded from .env")
                st.info(f"**Key Length:** {len(api_key)} characters")
                st.info(f"**Key Preview:** `{api_key[:10]}...{api_key[-8:]}`")
                if len(api_key) < 50:
                    st.error(f"**WARNING:** API key seems too short ({len(api_key)} chars). Expected 100+ characters.")
                    st.warning("This may be a cached/old key. Try restarting Streamlit.")

                # Determine analysis mode
                if prime_text and sub_text:
                    # Both contracts - do comparison analysis
                    status_text.text("Analyzing both contracts for red flags and flow-down issues... (60-90 seconds)")
                    progress_bar.progress(60)

                    st.write("---")
                    st.write("### Analyzing Prime + Subcontract (Comparison Mode)")
                    st.info("Checking for red flags in each contract AND flow-down/gap issues between them")

                    comparison_analysis = analyze_contract_with_claude(
                        prime_text,
                        api_key,
                        contract_type="comparison",
                        comparison_text=sub_text
                    )

                    if comparison_analysis:
                        st.success("Comparison analysis completed successfully")

                        # Save results to both contract records
                        if prime_contract_record:
                            db_utils.update_contract_analysis(prime_contract_record['id'], comparison_analysis)
                        if sub_contract_record:
                            db_utils.update_contract_analysis(sub_contract_record['id'], comparison_analysis)

                        # Create red flags (associate with appropriate contract)
                        if comparison_analysis.get('findings'):
                            # Split findings by contract
                            prime_findings = [f for f in comparison_analysis['findings']
                                             if f.get('contract') in ['prime', 'both']]
                            sub_findings = [f for f in comparison_analysis['findings']
                                           if f.get('contract') in ['subcontract', 'both']]

                            if prime_findings and prime_contract_record:
                                db_utils.create_red_flags(prime_contract_record['id'], prime_findings)
                            if sub_findings and sub_contract_record:
                                db_utils.create_red_flags(sub_contract_record['id'], sub_findings)
                    else:
                        st.warning("Comparison analysis failed")

                elif prime_text:
                    # Only prime contract
                    status_text.text("Analyzing prime contract... (30-60 seconds)")
                    progress_bar.progress(60)

                    st.write("---")
                    st.write("### Analyzing Prime Contract Only")

                    prime_analysis = analyze_contract_with_claude(prime_text, api_key, contract_type="single")

                    if prime_analysis:
                        st.success("Prime contract analyzed successfully")
                        if prime_contract_record:
                            db_utils.update_contract_analysis(prime_contract_record['id'], prime_analysis)
                            if prime_analysis.get('findings'):
                                db_utils.create_red_flags(prime_contract_record['id'], prime_analysis['findings'])
                    else:
                        st.warning("Prime contract analysis failed")

                elif sub_text:
                    # Only subcontract
                    status_text.text("Analyzing subcontract... (30-60 seconds)")
                    progress_bar.progress(60)

                    st.write("---")
                    st.write("### Analyzing Subcontract Only")

                    sub_analysis = analyze_contract_with_claude(sub_text, api_key, contract_type="single")

                    if sub_analysis:
                        st.success("Subcontract analyzed successfully")
                        if sub_contract_record:
                            db_utils.update_contract_analysis(sub_contract_record['id'], sub_analysis)
                            if sub_analysis.get('findings'):
                                db_utils.create_red_flags(sub_contract_record['id'], sub_analysis['findings'])
                    else:
                        st.warning("Subcontract analysis failed")
        
        # Step 8: Update project status to submitted
        status_text.text("Finalizing submission...")
        progress_bar.progress(90)
        
        db_utils.update_project_status(project_id, "submitted")
        
        # Complete!
        progress_bar.progress(100)
        status_text.text("Complete!")
        
        # Show success message
        contracts_uploaded = []
        if has_prime:
            contracts_uploaded.append("Prime Contract")
        if has_sub:
            contracts_uploaded.append("Subcontract")

        st.success(f"Contract{'s' if len(contracts_uploaded) > 1 else ''} submitted successfully for executive review!")

        # Show summary
        with st.expander("Submission Summary", expanded=True):
            st.write(f"**Project:** {project_name}")
            if project_number:
                st.write(f"**Project #:** {project_number}")
            st.write(f"**Contracts Uploaded:** {' + '.join(contracts_uploaded)}")
            st.write(f"**Submitted:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")

            # Show analysis results if available
            st.divider()

            # Check what analysis we performed
            if has_prime and has_sub and prime_text and sub_text:
                # Both contracts analyzed in comparison mode
                st.write("**Analysis Mode:** Comparison (Both Contracts + Flow-Down Issues)")
                # Note: In comparison mode, we stored the same analysis to both records
                # We could retrieve and display it, but for now just note it was done

            elif has_prime and prime_text:
                # Only prime analyzed
                st.write("**Analysis Mode:** Single Contract (Prime Only)")

            elif has_sub and sub_text:
                # Only sub analyzed
                st.write("**Analysis Mode:** Single Contract (Subcontract Only)")
            else:
                st.write("**Analysis:** PDF text extraction failed - manual review required")

            st.info("Executives will be notified and can now review your submission.")
    
    except Exception as e:
        st.error(f"Error processing submission: {str(e)}")
        import traceback
        st.error(traceback.format_exc())


# Display submission form
submission_form()