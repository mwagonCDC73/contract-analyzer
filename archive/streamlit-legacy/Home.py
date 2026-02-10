"""
California Drywall Contract Review System - Home Page
Main entry point with unified navigation and authentication
"""

import streamlit as st
import os
from dotenv import load_dotenv
import db_utils

load_dotenv(override=True)

# Page config - MUST be first Streamlit command
st.set_page_config(
    page_title="California Drywall - Contract Review",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = None

# Custom CSS matching California Drywall branding (caldrywall.com)
st.markdown("""
<style>
    /* California Drywall Color Scheme */
    :root {
        --cd-black: #000000;
        --cd-dark-gray: #32373c;
        --cd-light-gray: #abb8c3;
        --cd-white: #ffffff;
        --cd-bg-light: #f5f5f5;
    }

    /* Main header styling */
    .main-header {
        background: linear-gradient(135deg, #000000 0%, #32373c 100%);
        padding: 2.5rem;
        border-radius: 8px;
        margin-bottom: 2rem;
        color: white;
        border-bottom: 3px solid #abb8c3;
    }

    .main-header h1 {
        color: white !important;
        margin-bottom: 0.5rem;
        font-weight: 700;
        letter-spacing: -0.5px;
    }

    .main-header p {
        color: #abb8c3 !important;
    }

    /* Card styling */
    .feature-card {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        border: 2px solid #e5e7eb;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
        margin-bottom: 1rem;
        transition: all 0.3s ease;
    }

    .feature-card:hover {
        border-color: #abb8c3;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        transform: translateY(-3px);
    }

    .feature-card h3 {
        color: #000000;
        font-weight: 600;
        margin-bottom: 0.75rem;
    }

    .feature-card p {
        color: #32373c;
    }

    .feature-card ul {
        color: #32373c;
    }

    /* Sidebar user info */
    .sidebar-user-info {
        padding: 1rem;
        background: #f5f5f5;
        border-radius: 8px;
        margin-bottom: 1rem;
        border: 1px solid #abb8c3;
    }

    .sidebar-user-name {
        font-size: 1.1rem;
        font-weight: 600;
        color: #000000;
        margin-bottom: 0.5rem;
        display: block;
    }

    /* Role badge colors - matching CD brand */
    .role-badge {
        background: #000000;
        color: #abb8c3;
        padding: 0.25rem 0.75rem;
        border-radius: 4px;
        font-weight: 500;
        font-size: 0.813rem;
        border: 1px solid #abb8c3;
        display: inline-block;
    }

    .role-executive {
        background: #000000;
        color: #ffffff;
        border-color: #abb8c3;
    }

    .role-pm {
        background: #32373c;
        color: #ffffff;
    }

    .role-admin {
        background: #000000;
        color: #abb8c3;
        border: 2px solid #abb8c3;
    }

    /* Streamlit button overrides */
    .stButton > button {
        background-color: #32373c;
        color: white;
        border: none;
        font-weight: 500;
        transition: all 0.3s ease;
    }

    .stButton > button:hover {
        background-color: #000000;
        border: 1px solid #abb8c3;
    }

    /* Primary button styling */
    .stButton > button[kind="primary"] {
        background-color: #000000;
        color: white;
        border: 2px solid #abb8c3;
    }

    .stButton > button[kind="primary"]:hover {
        background-color: #32373c;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #f5f5f5;
    }

    /* Metrics styling */
    [data-testid="stMetricValue"] {
        color: #000000;
        font-weight: 700;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def login_page():
    """Display login page"""

    # Header
    st.markdown("""
    <div class="main-header">
        <h1>California Drywall Co.</h1>
        <p style="font-size: 1.2rem; margin: 0;">Contract Review System</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("### Sign In")
        st.markdown("Access the contract review system with your credentials")

        with st.form("login_form"):
            email = st.text_input(
                "Email Address",
                placeholder="your.email@caldrywall.com"
            )
            password = st.text_input(
                "Password",
                type="password"
            )

            col_a, col_b = st.columns(2)
            with col_a:
                submit = st.form_submit_button("Sign In", use_container_width=True, type="primary")

            if submit:
                if not email or not password:
                    st.error("Please enter both email and password")
                    return

                with st.spinner("Authenticating..."):
                    auth_response = db_utils.authenticate_user(email, password)

                    if auth_response and auth_response.user:
                        profile = db_utils.get_user_profile(auth_response.user.id)

                        if not profile:
                            st.error("User profile not found. Please contact your administrator.")
                            return

                        st.session_state.authenticated = True
                        st.session_state.user = auth_response.user
                        st.session_state.user_profile = profile
                        st.success(f"Welcome, {profile.get('full_name')}!")
                        st.rerun()
                    else:
                        st.error("Invalid email or password")

        st.divider()

        # Info section
        with st.expander("About This System"):
            st.markdown("""
            The California Drywall Contract Review System provides analysis of
            construction contracts, identifying risks, compliance issues, and opportunities
            for negotiation.

            **Features:**
            - Automated contract analysis
            - Risk identification and categorization
            - Executive review and approval workflow
            - Project and document management

            **Need Help?**
            Contact your IT department or project management office.
            """)


def home_page():
    """Display home page for authenticated users"""

    profile = st.session_state.user_profile
    role = profile.get('role', 'unknown')
    full_name = profile.get('full_name', 'User')

    # Sidebar with improved user info styling
    with st.sidebar:
        # User info section
        role_display = role.replace("_", " ").title()

        # Determine role class
        if role == 'executive':
            role_class = 'role-executive'
        elif role == 'admin':
            role_class = 'role-admin'
        else:
            role_class = 'role-pm'

        st.markdown(f"""
        <div class="sidebar-user-info">
            <span class="sidebar-user-name">{full_name}</span>
            <span class="role-badge {role_class}">{role_display}</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### Quick Navigation")
        st.markdown("Use the pages menu above to navigate between sections")

        st.divider()

        if st.button("Sign Out", use_container_width=True, key="sidebar_signout"):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.session_state.user_profile = None
            st.rerun()

    # Main header
    st.markdown("""
    <div class="main-header">
        <h1>California Drywall Contract Review</h1>
        <p style="font-size: 1.1rem; margin: 0;">Contract analysis for wall & ceiling specialty contractors</p>
    </div>
    """, unsafe_allow_html=True)

    # Welcome message
    st.markdown(f"## Welcome back, {full_name}!")

    # Role-specific quick links
    if role == 'project_manager':
        st.markdown("### Project Manager Dashboard")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
            <div class="feature-card">
                <h3>Submit New Contract</h3>
                <p>Upload and analyze construction contracts with automated review</p>
                <ul>
                    <li>Upload subcontract or owner contract</li>
                    <li>Automated analysis</li>
                    <li>Risk identification</li>
                    <li>Submit for executive review</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            st.page_link("pages/1__PM_Submit.py", label="Go to Submit Contract", use_container_width=True)

        with col2:
            st.markdown("""
            <div class="feature-card">
                <h3>View My Submissions</h3>
                <p>Track your contract submissions and their review status</p>
                <ul>
                    <li>View submission history</li>
                    <li>Check review status</li>
                    <li>Download analysis reports</li>
                    <li>Review executive feedback</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            st.page_link("pages/3_My_Submissions.py", label="Go to My Submissions", use_container_width=True)

    elif role in ['executive', 'admin']:
        st.markdown("### Executive Dashboard")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("""
            <div class="feature-card">
                <h3>Review Contracts</h3>
                <p>Review and approve project manager submissions</p>
                <ul>
                    <li>View pending submissions</li>
                    <li>Review analysis</li>
                    <li>Approve or reject projects</li>
                    <li>Download original contracts</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            st.page_link("pages/2__Executive_Review.py", label="Go to Executive Review", use_container_width=True)

        with col2:
            st.markdown("""
            <div class="feature-card">
                <h3>Admin Panel</h3>
                <p>Manage projects, users, and system data</p>
                <ul>
                    <li>Archive or delete projects</li>
                    <li>View system statistics</li>
                    <li>Bulk actions</li>
                    <li>User management</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            st.page_link("pages/3__Admin_Panel.py", label="Go to Admin Panel", use_container_width=True)

        with col3:
            st.markdown("""
            <div class="feature-card">
                <h3>Reports</h3>
                <p>View analytics and generate reports</p>
                <ul>
                    <li>Project statistics</li>
                    <li>Risk analysis trends</li>
                    <li>Executive summaries</li>
                    <li>Export data</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            st.info("Coming soon: Reports page")

    # System status
    st.divider()

    col1, col2, col3, col4 = st.columns(4)

    try:
        supabase = db_utils.get_supabase_client()

        with col1:
            projects = supabase.table('projects').select('id', count='exact').execute()
            st.metric("Total Projects", projects.count if projects.count else 0)

        with col2:
            submitted = supabase.table('projects').select('id', count='exact').eq('status', 'submitted').execute()
            st.metric("Pending Review", submitted.count if submitted.count else 0)

        with col3:
            contracts = supabase.table('contracts').select('id', count='exact').execute()
            st.metric("Contracts Analyzed", contracts.count if contracts.count else 0)

        with col4:
            red_flags = supabase.table('red_flags').select('id', count='exact').eq('severity', 'critical').execute()
            st.metric("Critical Issues Found", red_flags.count if red_flags.count else 0)
    except:
        pass

    # Footer
    st.divider()
    st.caption("© 2025 California Drywall Co. | Version 2.0")


def main():
    """Main application logic"""
    if not st.session_state.authenticated:
        login_page()
    else:
        home_page()


if __name__ == "__main__":
    main()
