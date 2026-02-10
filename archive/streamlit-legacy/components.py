"""
Shared UI Components for California Drywall Contract Review System
Single source of truth for all navigation and headers
"""

import streamlit as st
import os


def render_header(current_page=None):
    """
    Unified header component for ALL pages

    Args:
        current_page: String indicating current page ('home', 'pm_submit', 'executive_review', 'admin_panel')
    """
    if not st.session_state.get('authenticated'):
        return

    profile = st.session_state.get('user_profile', {})
    full_name = profile.get('full_name', 'User')
    role = profile.get('role', 'unknown')
    role_display = role.replace('_', ' ').title()

    # Detect if we're using multi-page app (Home.py) or single-page app (app_main.py)
    is_multipage = not st.session_state.get('current_page')  # app_main.py sets this

    # CSS for unified header
    st.markdown("""
    <style>
        /* Black header bar */
        div[data-testid="stHorizontalBlock"]:has(div.unified-header) {
            background: linear-gradient(90deg, #000000 0%, #32373c 100%);
            padding: 1rem 2rem;
            margin: -1rem -1rem 2rem -1rem;
            border-bottom: 2px solid #abb8c3;
        }

        /* Company name */
        .header-brand {
            color: white;
            font-size: 1.5rem;
            font-weight: 700;
            line-height: 2.5rem;
            margin: 0;
            display: inline-block;
            margin-right: 3rem;
        }

        /* Navigation links */
        .header-nav {
            display: inline-block;
            line-height: 2.5rem;
        }

        .header-nav-link {
            color: #abb8c3;
            font-size: 1rem;
            font-weight: 500;
            text-decoration: none;
            padding: 0.5rem 1rem;
            margin: 0 0.25rem;
            border-radius: 4px;
            transition: all 0.2s;
            display: inline-block;
        }

        .header-nav-link:hover {
            color: white;
            background-color: rgba(255, 255, 255, 0.1);
        }

        .header-nav-link.active {
            color: white;
            background-color: rgba(255, 255, 255, 0.15);
            font-weight: 600;
        }

        /* User info */
        .header-user-info {
            color: white;
            font-size: 1rem;
            text-align: right;
            line-height: 2.5rem;
        }

        .header-user-name {
            color: white;
            font-weight: 600;
            margin-right: 1rem;
        }

        .header-role-badge {
            background: #000000;
            color: #abb8c3;
            padding: 0.25rem 0.75rem;
            border-radius: 4px;
            font-size: 0.875rem;
            border: 1px solid #abb8c3;
            margin-right: 1rem;
        }

        /* Style header buttons */
        div[data-testid="stHorizontalBlock"]:has(div.unified-header) .stButton > button {
            background: transparent !important;
            color: #abb8c3 !important;
            border: none !important;
            padding: 0.5rem 1rem !important;
            font-size: 1rem !important;
            font-weight: 500 !important;
            box-shadow: none !important;
            height: auto !important;
            min-height: 2.5rem !important;
            line-height: 1.5rem !important;
            border-radius: 4px !important;
            margin: 0 0.25rem !important;
        }

        div[data-testid="stHorizontalBlock"]:has(div.unified-header) .stButton > button:hover {
            background: rgba(255, 255, 255, 0.1) !important;
            color: white !important;
        }

        /* Active page button */
        div[data-testid="stHorizontalBlock"]:has(div.unified-header) .stButton.active > button {
            color: white !important;
            background: rgba(255, 255, 255, 0.15) !important;
            font-weight: 600 !important;
        }

        /* Sign Out button styling */
        div[data-testid="stHorizontalBlock"]:has(div.unified-header) .stButton:has(button[key*="signout"]) > button {
            color: #abb8c3 !important;
            font-size: 0.875rem !important;
            font-weight: 400 !important;
            padding: 0.4rem 0.8rem !important;
        }

        div[data-testid="stHorizontalBlock"]:has(div.unified-header) .stButton:has(button[key*="signout"]) > button:hover {
            text-decoration: underline;
        }
    </style>
    """, unsafe_allow_html=True)

    # Header layout
    col_left, col_center, col_right = st.columns([2, 3, 2])

    with col_left:
        st.markdown('<div class="unified-header"><h1 class="header-brand">California Drywall</h1></div>', unsafe_allow_html=True)

    with col_center:
        st.markdown('<div class="unified-header"></div>', unsafe_allow_html=True)

        # Navigation buttons - adjust columns based on role
        if role == 'admin':
            nav_col1, nav_col2, nav_col3, nav_col4, nav_col5 = st.columns(5)
        elif role == 'project_manager':
            nav_col1, nav_col2, nav_col3, nav_col4, nav_col5 = st.columns([1, 1, 1, 0.5, 0.5])
        elif role == 'executive':
            nav_col1, nav_col2, nav_col3, nav_col4, nav_col5 = st.columns([1, 0.5, 1, 1, 0.5])
        else:
            nav_col1, nav_col2, nav_col3, nav_col4, nav_col5 = st.columns([1, 1, 1, 1, 1])

        with nav_col1:
            # Main Dashboard
            if is_multipage:
                # Use st.page_link for multi-page app
                st.page_link("Home.py", label="Main Dashboard")
            else:
                # Use button for single-page app
                if st.button("Main Dashboard", key="nav_home", use_container_width=True):
                    st.session_state.current_page = 'home'
                    if 'selected_project_id' in st.session_state:
                        st.session_state.selected_project_id = None
                    st.rerun()

        with nav_col2:
            # Submit Contract (only for PMs and admins)
            if role in ['project_manager', 'admin']:
                if is_multipage:
                    st.page_link("pages/1_PM_Submit.py", label="Submit Contract")
                else:
                    if st.button("Submit Contract", key="nav_submit", use_container_width=True):
                        st.session_state.current_page = 'pm_submit'
                        st.rerun()

        with nav_col3:
            # My Submissions (only for PMs and admins)
            if role in ['project_manager', 'admin']:
                if is_multipage:
                    st.page_link("pages/3_My_Submissions.py", label="My Submissions")
                else:
                    if st.button("My Submissions", key="nav_submissions", use_container_width=True):
                        st.session_state.current_page = 'my_submissions'
                        if 'selected_project_id' in st.session_state:
                            st.session_state.selected_project_id = None
                        st.rerun()

        with nav_col4:
            # Executive Review (only for executives/admins)
            if role in ['executive', 'admin']:
                if is_multipage:
                    st.page_link("pages/2_Executive_Review.py", label="Executive Review")
                else:
                    if st.button("Executive Review", key="nav_exec", use_container_width=True):
                        st.session_state.current_page = 'executive_review'
                        if 'selected_project_id' in st.session_state:
                            st.session_state.selected_project_id = None
                        st.rerun()

        with nav_col5:
            # Admin Panel (only for admins)
            if role == 'admin':
                if is_multipage:
                    st.page_link("pages/4_Admin_Panel.py", label="Admin Panel")
                else:
                    if st.button("Admin Panel", key="nav_admin", use_container_width=True):
                        st.session_state.current_page = 'admin_panel'
                        st.rerun()

    with col_right:
        st.markdown('<div class="unified-header"></div>', unsafe_allow_html=True)

        # User info and Sign Out
        user_col1, user_col2 = st.columns([3, 1])

        with user_col1:
            user_html = f'''
            <div class="header-user-info">
                <span class="header-user-name">{full_name}</span>
                <span class="header-role-badge">{role_display}</span>
            </div>
            '''
            st.markdown(user_html, unsafe_allow_html=True)

        with user_col2:
            if st.button("Sign Out", key="header_signout"):
                st.session_state.authenticated = False
                st.session_state.user = None
                st.session_state.user_profile = None
                if 'current_page' in st.session_state:
                    st.session_state.current_page = 'home'
                if 'selected_project_id' in st.session_state:
                    st.session_state.selected_project_id = None
                st.rerun()


def add_global_styles():
    """
    Add global CSS styles that apply to all pages
    """
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

        /* Page spacing */
        .block-container {
            padding-top: 1rem;
            padding-bottom: 2rem;
        }

        /* Page titles */
        h1, h2, h3 {
            color: var(--cd-black);
            font-weight: 600;
        }

        /* Buttons */
        .stButton > button {
            background-color: var(--cd-dark-gray);
            color: white;
            border: none;
            font-weight: 500;
            transition: all 0.3s ease;
            border-radius: 6px;
        }

        .stButton > button:hover {
            background-color: var(--cd-black);
            border: 1px solid var(--cd-light-gray);
        }

        .stButton > button[kind="primary"] {
            background-color: var(--cd-black);
            color: white;
            border: 2px solid var(--cd-light-gray);
        }

        .stButton > button[kind="primary"]:hover {
            background-color: var(--cd-dark-gray);
        }

        /* Hide Streamlit branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}

        /* Metrics */
        [data-testid="stMetricValue"] {
            color: var(--cd-black);
            font-weight: 700;
        }
    </style>
    """, unsafe_allow_html=True)


def render_page_title(title, subtitle=None):
    """
    Render consistent page title with optional subtitle

    Args:
        title: Main page title
        subtitle: Optional subtitle/description
    """
    st.markdown(f"<h1 style='margin-bottom: 0.5rem;'>{title}</h1>", unsafe_allow_html=True)
    if subtitle:
        st.markdown(f"<p style='color: #666; font-size: 1.1rem; margin-top: 0;'>{subtitle}</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
