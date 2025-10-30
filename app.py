import streamlit as st
import anthropic
import os
from datetime import datetime
import json

# Page configuration
st.set_page_config(
    page_title="California Drywall - Contract Analyzer",
    page_icon="📋",
    layout="wide"
)

# Initialize session state
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'uploaded_file_name' not in st.session_state:
    st.session_state.uploaded_file_name = None

# Sidebar for authentication and settings
with st.sidebar:
    st.image("https://via.placeholder.com/200x80/FF6B35/FFFFFF?text=CA+Drywall", use_container_width=True)
    st.title("Contract Analyzer")
    
    # Simple authentication (replace with proper auth later)
    user_role = st.selectbox(
        "Login as:",
        ["Project Manager", "Executive", "Admin"]
    )
    
    st.divider()
    
    # API Key input (in production, use secrets management)
    api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        help="Enter your Anthropic API key. Get one at console.anthropic.com"
    )
    
    st.divider()
    st.caption("Version 1.0.0")
    st.caption("© 2025 California Drywall")

# Main header
st.title("🏗️ Construction Contract Analyzer")
st.markdown("**AI-powered contract analysis for California Drywall project managers**")
st.divider()

# Contract analysis prompt template
CONTRACT_ANALYSIS_PROMPT = """You are an expert construction contract analyst specializing in identifying risks, red flags, and issues in construction contracts. 

Analyze the following construction contract and provide a comprehensive analysis focusing on:

1. **Critical Issues** - Must be resolved before signing (missing GMP, undefined dates, lack of bonds)
2. **Warnings** - Items requiring negotiation or clarification (high markups, unfavorable terms, vague language)
3. **Informational** - Items to be aware of (standard clauses, best practices, recommendations)

For each issue found, provide:
- Category (Payment Terms, Timeline, Insurance, Scope, Risk Allocation, etc.)
- Severity (critical, warning, informational)
- Specific issue description
- Exact location in contract (Article, Section)
- Recommendation for project manager

Focus on common construction contract red flags:
- Incomplete or TBD pricing/dates
- Missing or inadequate bonds/insurance
- Unclear scope definition
- Unfavorable payment terms
- Weak change order provisions
- High liquidated damages without caps
- Vague completion criteria
- Missing exhibits or schedules
- Unbalanced risk allocation
- Problematic dispute resolution terms

Format your response as a JSON object with this structure:
{
  "summary": {
    "total_issues": <number>,
    "critical": <number>,
    "warning": <number>,
    "informational": <number>
  },
  "findings": [
    {
      "category": "<category>",
      "severity": "<critical|warning|informational>",
      "issue": "<brief title>",
      "details": "<detailed explanation>",
      "location": "<Article X, Section Y>",
      "recommendation": "<action to take>"
    }
  ]
}

CONTRACT TEXT:
{contract_text}
"""

def analyze_contract_with_claude(contract_text, api_key):
    """Analyze contract using Claude API"""
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
            messages=[
                {
                    "role": "user",
                    "content": CONTRACT_ANALYSIS_PROMPT.format(contract_text=contract_text)
                }
            ]
        )
        
        # Extract JSON from response
        response_text = message.content[0].text
        
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
        return None

def display_severity_badge(severity):
    """Display colored badge for severity level"""
    colors = {
        "critical": "🔴",
        "warning": "🟡",
        "informational": "🔵"
    }
    return colors.get(severity, "⚪")

# File upload section
st.header("📤 Upload Contract")

uploaded_file = st.file_uploader(
    "Upload construction contract (PDF or Word)",
    type=['pdf', 'docx', 'doc', 'txt'],
    help="Supported formats: PDF, Word (.docx, .doc), or plain text"
)

if uploaded_file:
    st.session_state.uploaded_file_name = uploaded_file.name
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.success(f"✅ Uploaded: {uploaded_file.name}")
    with col2:
        st.metric("File Size", f"{uploaded_file.size / 1024:.1f} KB")
    with col3:
        st.metric("Type", uploaded_file.type.split('/')[-1].upper())
    
    # Read file content
    try:
        if uploaded_file.type == "text/plain":
            contract_text = uploaded_file.read().decode('utf-8')
        elif uploaded_file.type == "application/pdf":
            st.warning("📄 PDF parsing requires additional libraries. For demo, please use .txt file or paste text below.")
            contract_text = None
        elif "word" in uploaded_file.type or uploaded_file.name.endswith(('.doc', '.docx')):
            st.warning("📝 Word document parsing requires additional libraries. For demo, please use .txt file or paste text below.")
            contract_text = None
        else:
            contract_text = uploaded_file.read().decode('utf-8')
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        contract_text = None

# Manual text input option
with st.expander("📝 Or paste contract text manually"):
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
        "🔍 Analyze Contract",
        type="primary",
        use_container_width=True,
        disabled=not api_key or (not uploaded_file and not manual_text)
    )

if not api_key:
    st.info("👈 Please enter your Anthropic API key in the sidebar to begin analysis")

# Perform analysis
if analyze_button and api_key:
    if 'contract_text' in locals() and contract_text:
        with st.spinner("🤖 AI analyzing contract... This may take 30-60 seconds..."):
            results = analyze_contract_with_claude(contract_text, api_key)
            
            if results:
                st.session_state.analysis_results = results
                st.session_state.analysis_date = datetime.now()
    else:
        st.error("Please upload a valid contract file or paste contract text")

# Display results
if st.session_state.analysis_results:
    results = st.session_state.analysis_results
    
    st.divider()
    st.header("📊 Analysis Results")
    
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
            "🔴 Critical",
            results['summary']['critical'],
            delta=None,
            help="Must be resolved before signing"
        )
    with col3:
        st.metric(
            "🟡 Warnings",
            results['summary']['warning'],
            delta=None,
            help="Require attention or negotiation"
        )
    with col4:
        st.metric(
            "🔵 Informational",
            results['summary']['informational'],
            delta=None,
            help="Items to be aware of"
        )
    
    # Risk assessment
    if results['summary']['critical'] > 0:
        st.error(f"⚠️ **HIGH RISK**: {results['summary']['critical']} critical issues must be resolved before contract execution")
    elif results['summary']['warning'] > 3:
        st.warning(f"⚠️ **MODERATE RISK**: {results['summary']['warning']} warnings require review and potential negotiation")
    else:
        st.success("✅ **LOW RISK**: No critical issues found. Review warnings before proceeding.")
    
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
                st.caption(f"📁 {finding['category']}")
            
            st.markdown(f"**Details:** {finding['details']}")
            st.caption(f"📍 Location: {finding['location']}")
            
            st.info(f"**💡 Recommendation:** {finding['recommendation']}")
            
            st.markdown("</div>", unsafe_allow_html=True)
    
    # Export options
    st.divider()
    st.subheader("📥 Export Results")
    
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
        if st.button("🔄 Analyze Another Contract"):
            st.session_state.analysis_results = None
            st.session_state.uploaded_file_name = None
            st.rerun()

# Footer
st.divider()
st.caption("""
**California Drywall Contract Analyzer** | Powered by Claude AI  
For support, contact your IT department or project management office.
""")
