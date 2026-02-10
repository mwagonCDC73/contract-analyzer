"""
PM Submit Page Module - Full functionality
Integrated into new navigation system
"""

import streamlit as st
import requests
import json
from datetime import datetime
import os
import io
import re
import PyPDF2

# Import pdfplumber with error handling
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False
    st.error("pdfplumber is not installed. PDF extraction quality will be reduced. Run: pip install pdfplumber")

import db_utils
import components
from dotenv import load_dotenv

load_dotenv(override=True)


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
        if HAS_PDFPLUMBER:
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
    """Analyze contract using Claude API"""

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

Provide comprehensive analysis. Format response as JSON:
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
        prompt = """You are an expert construction contract analyst for California Drywall Co.

Analyze the following construction contract for red flags focusing on payment, schedule, scope, insurance, change orders, and California-specific requirements.

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
      "details": "<detailed explanation>",
      "location": "<Article X, Section Y>",
      "recommendation": "<specific action>"
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

        data = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 8000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
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


def process_submission(project_name, project_number, pm_notes, prime_contract, subcontract):
    """Process the contract submission"""

    progress_bar = st.progress(0)
    status_text = st.empty()

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

            # Extract text
            status_text.text("Extracting text from prime contract...")
            progress_bar.progress(30)
            prime_text = extract_text_from_pdf(prime_contract)

        # Step 3: Upload subcontract (if provided)
        if has_sub:
            status_text.text("Uploading subcontract...")
            progress_bar.progress(40)

            sub_file_info = db_utils.upload_contract_file(subcontract, project_id, "subcontract")
            if not sub_file_info:
                st.error("Failed to upload subcontract")
                return

            sub_contract_record = db_utils.create_contract_record(project_id, "subcontract", sub_file_info)

            # Extract text
            status_text.text("Extracting text from subcontract...")
            progress_bar.progress(50)
            sub_text = extract_text_from_pdf(subcontract)

        # Step 4: AI Analysis
        if not prime_text and not sub_text:
            st.warning("Could not extract text from PDFs. Skipping automated analysis.")
        else:
            api_key = os.getenv("ANTHROPIC_API_KEY")

            if not api_key:
                st.error("ANTHROPIC_API_KEY not found in .env file")
            else:
                # Determine analysis mode
                if prime_text and sub_text:
                    # Comparison analysis
                    status_text.text("Analyzing both contracts (comparison mode)...")
                    progress_bar.progress(60)

                    analysis_results = analyze_contract_with_claude(
                        prime_text,
                        api_key,
                        contract_type="comparison",
                        comparison_text=sub_text
                    )

                    if analysis_results:
                        # Save results to both contracts
                        if prime_contract_record:
                            db_utils.update_contract_analysis(prime_contract_record['id'], analysis_results)
                            db_utils.create_red_flags(prime_contract_record['id'], analysis_results.get('findings', []))

                        if sub_contract_record:
                            db_utils.update_contract_analysis(sub_contract_record['id'], analysis_results)
                            db_utils.create_red_flags(sub_contract_record['id'], analysis_results.get('findings', []))

                elif prime_text:
                    # Analyze prime only
                    status_text.text("Analyzing prime contract...")
                    progress_bar.progress(60)

                    analysis_results = analyze_contract_with_claude(prime_text, api_key)

                    if analysis_results and prime_contract_record:
                        db_utils.update_contract_analysis(prime_contract_record['id'], analysis_results)
                        db_utils.create_red_flags(prime_contract_record['id'], analysis_results.get('findings', []))

                elif sub_text:
                    # Analyze subcontract only
                    status_text.text("Analyzing subcontract...")
                    progress_bar.progress(60)

                    analysis_results = analyze_contract_with_claude(sub_text, api_key)

                    if analysis_results and sub_contract_record:
                        db_utils.update_contract_analysis(sub_contract_record['id'], analysis_results)
                        db_utils.create_red_flags(sub_contract_record['id'], analysis_results.get('findings', []))

        # Step 5: Submit project
        status_text.text("Submitting project for review...")
        progress_bar.progress(90)

        db_utils.update_project_status(project_id, "submitted")

        progress_bar.progress(100)
        status_text.text("Complete!")

        st.success(f"Project '{project_name}' submitted successfully!")
        st.info("The project is now pending executive review.")

        # Set success flag and trigger rerun to exit form context
        st.session_state.submission_success = True
        st.session_state.submitted_project_name = project_name

        # Small delay to let user see the success message
        import time
        time.sleep(1.5)
        st.rerun()

    except Exception as e:
        st.error(f"Error during submission: {str(e)}")
        import traceback
        st.error(traceback.format_exc())


def show():
    """Display PM submission form"""

    # Check authentication
    if not st.session_state.get('authenticated'):
        st.error("Please log in first")
        return

    # Add global styles and render unified header
    components.add_global_styles()
    components.render_header(current_page='pm_submit')

    # Handle successful submission display (before showing form again)
    if st.session_state.get('submission_success'):
        components.render_page_title(
            "Submission Successful!",
            "Your contract has been submitted for executive review"
        )

        project_name = st.session_state.get('submitted_project_name', 'Your project')
        st.success(f"Project '{project_name}' has been submitted successfully!")
        st.info("The project is now pending executive review.")

        st.divider()

        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("Return to Dashboard", type="primary", use_container_width=True):
                # Clear the success flags
                st.session_state.submission_success = False
                if 'submitted_project_name' in st.session_state:
                    del st.session_state.submitted_project_name
                st.session_state.current_page = 'home'
                st.rerun()

        # Don't show the form again
        return

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
                "Project Name",
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
        st.info("Tip: Upload BOTH contracts for comparison analysis that checks flow-down clauses and identifies gaps!")

        col1, col2 = st.columns(2)

        with col1:
            prime_contract = st.file_uploader(
                "Prime Contract (Optional)",
                type=['pdf'],
                help="Upload the main/general contractor agreement"
            )

        with col2:
            subcontract = st.file_uploader(
                "Subcontract (Optional)",
                type=['pdf'],
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
