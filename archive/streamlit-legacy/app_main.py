"""
California Drywall Contract Review System - Main Application
Single-page app with top navigation bar
"""

import streamlit as st
import os
from dotenv import load_dotenv
import db_utils

# Import page modules
import sys
sys.path.insert(0, os.path.dirname(__file__))
from pages import pm_submit_page, executive_review_page, admin_panel_page
import components

load_dotenv(override=True)

# Page config
st.set_page_config(
    page_title="California Drywall - Contract Review",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'home'
if 'selected_project_id' not in st.session_state:
    st.session_state.selected_project_id = None

# Custom CSS
st.markdown("""
<style>
    /* Hide sidebar */
    [data-testid="stSidebar"] {
        display: none;
    }

    /* California Drywall Color Scheme */
    :root {
        --cd-black: #000000;
        --cd-dark-gray: #32373c;
        --cd-light-gray: #abb8c3;
        --cd-white: #ffffff;
        --cd-bg-light: #f5f5f5;
    }

    /* Top Navigation Bar */
    .top-nav {
        background: linear-gradient(90deg, #000000 0%, #32373c 100%);
        padding: 1rem 2rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: -1rem -1rem 2rem -1rem;
        border-bottom: 2px solid #abb8c3;
    }

    .top-nav-left {
        display: flex;
        align-items: center;
        gap: 2rem;
    }

    .top-nav-brand {
        color: white;
        font-size: 1.5rem;
        font-weight: 700;
        margin: 0;
    }

    .top-nav-links {
        display: flex;
        gap: 1rem;
        align-items: center;
    }

    .top-nav-right {
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    .user-info {
        color: #abb8c3;
        font-size: 0.9rem;
        margin-right: 1rem;
    }

    .user-name {
        color: white;
        font-weight: 600;
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
        padding: 2rem;
        border-radius: 8px;
        border: 2px solid #e5e7eb;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
        margin-bottom: 1rem;
        transition: all 0.3s ease;
        cursor: pointer;
        height: 100%;
    }

    .feature-card:hover {
        border-color: #000000;
        box-shadow: 0 6px 16px rgba(0,0,0,0.15);
        transform: translateY(-3px);
    }

    .feature-card h3 {
        color: #000000;
        font-weight: 600;
        margin-bottom: 0.75rem;
        font-size: 1.3rem;
    }

    .feature-card p {
        color: #32373c;
        margin-bottom: 1rem;
    }

    .feature-card ul {
        color: #32373c;
    }

    /* Role badge */
    .role-badge {
        background: #000000;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.75rem;
        border: 1px solid #abb8c3;
        display: inline-block;
    }

    /* Buttons */
    .stButton > button {
        background-color: #32373c;
        color: white;
        border: none;
        font-weight: 500;
        transition: all 0.3s ease;
        border-radius: 6px;
        padding: 0.5rem 1.5rem;
    }

    .stButton > button:hover {
        background-color: #000000;
        border: 1px solid #abb8c3;
    }

    .stButton > button[kind="primary"] {
        background-color: #000000;
        color: white;
        border: 2px solid #abb8c3;
    }

    .stButton > button[kind="primary"]:hover {
        background-color: #32373c;
    }

    /* Metrics */
    [data-testid="stMetricValue"] {
        color: #000000;
        font-weight: 700;
    }

    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Page content spacing */
    .block-container {
        padding-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)


def render_top_nav():
    """Render top navigation bar"""
    if not st.session_state.authenticated:
        return

    profile = st.session_state.user_profile
    role = profile.get('role', 'unknown')
    full_name = profile.get('full_name', 'User')

    # Navigation bar HTML
    nav_html = f"""
    <div class="top-nav">
        <div class="top-nav-left">
            <h2 class="top-nav-brand">California Drywall</h2>
        </div>
        <div class="top-nav-right">
            <div class="user-info">
                <span class="user-name">{full_name}</span>
                <span class="role-badge">{role.replace('_', ' ').title()}</span>
            </div>
        </div>
    </div>
    """

    st.markdown(nav_html, unsafe_allow_html=True)

    # Navigation buttons in columns
    if st.session_state.current_page != 'home':
        cols = st.columns([1, 1, 1, 1, 6])
        with cols[0]:
            if st.button("Home", use_container_width=True):
                st.session_state.current_page = 'home'
                st.rerun()

        # Role-specific navigation
        if role == 'project_manager':
            with cols[1]:
                if st.button("Submit Contract", use_container_width=True):
                    st.session_state.current_page = 'pm_submit'
                    st.rerun()
        elif role in ['executive', 'admin']:
            with cols[1]:
                if st.button("Review Contracts", use_container_width=True):
                    st.session_state.current_page = 'executive_review'
                    st.rerun()
            with cols[2]:
                if st.button("Admin Panel", use_container_width=True):
                    st.session_state.current_page = 'admin_panel'
                    st.rerun()

        with cols[-1]:
            col_right1, col_right2 = st.columns([6, 1])
            with col_right2:
                if st.button("Sign Out", use_container_width=True):
                    st.session_state.authenticated = False
                    st.session_state.user = None
                    st.session_state.user_profile = None
                    st.session_state.current_page = 'home'
                    st.rerun()


def login_page():
    """Display login page"""

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
                        st.session_state.current_page = 'home'
                        st.success(f"Welcome, {profile.get('full_name')}!")
                        st.rerun()
                    else:
                        st.error("Invalid email or password")

        st.divider()

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


def home_dashboard():
    """Display home dashboard for authenticated users"""

    # Add global styles and render unified header
    components.add_global_styles()
    components.render_header(current_page='home')

    profile = st.session_state.user_profile
    role = profile.get('role', 'unknown')
    full_name = profile.get('full_name', 'User')

    components.render_page_title(
        f"Welcome back, {full_name}!",
        "Your California Drywall Contract Review Dashboard"
    )

    # Role-specific dashboard
    if role == 'project_manager':
        st.markdown("### Project Manager Dashboard")

        col1, col2 = st.columns(2)

        with col1:
            with st.container():
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
                if st.button("Go to Submit Contract", key="dashboard_submit", use_container_width=True, type="primary"):
                    st.session_state.current_page = 'pm_submit'
                    st.rerun()

        with col2:
            with st.container():
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
                st.info("Coming soon: My Submissions page")

    elif role in ['executive', 'admin']:
        st.markdown("### Executive Dashboard")

        col1, col2, col3 = st.columns(3)

        with col1:
            with st.container():
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
                if st.button("Go to Executive Review", key="dashboard_exec", use_container_width=True, type="primary"):
                    st.session_state.current_page = 'executive_review'
                    st.rerun()

        with col2:
            with st.container():
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
                if st.button("Go to Admin Panel", key="dashboard_admin", use_container_width=True, type="primary"):
                    st.session_state.current_page = 'admin_panel'
                    st.rerun()

        with col3:
            with st.container():
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
    st.caption("© 2025 California Drywall Co.")


def main():
    """Main application logic"""

    if not st.session_state.authenticated:
        login_page()
        return

    # Route to appropriate page based on current_page state
    current_page = st.session_state.current_page

    if current_page == 'home':
        home_dashboard()
    elif current_page == 'pm_submit':
        # Navigation header is rendered inside pm_submit_page.show()
        pm_submit_page.show()
    elif current_page == 'executive_review':
        # Navigation header is rendered inside executive_review_page.show()
        executive_review_page.show()
    elif current_page == 'admin_panel':
        # Navigation header is rendered inside admin_panel_page.show()
        admin_panel_page.show()
    else:
        home_dashboard()


if __name__ == "__main__":
    main()
