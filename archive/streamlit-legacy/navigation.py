"""
Shared Navigation Component for California Drywall Contract Review System
Simple, clean header bar
"""

import streamlit as st


def render_user_header():
    """
    Simple header bar with company name and user info
    """
    if not st.session_state.get('authenticated'):
        return

    profile = st.session_state.get('user_profile', {})
    full_name = profile.get('full_name', 'User')
    role = profile.get('role', 'unknown')
    role_display = role.replace('_', ' ').title()

    # Simple CSS for black header bar
    st.markdown("""
    <style>
        /* Black header bar styling */
        div[data-testid="stHorizontalBlock"]:has(div.header-content) {
            background: linear-gradient(90deg, #000000 0%, #32373c 100%);
            padding: 1rem 2rem;
            margin: -1rem -1rem 2rem -1rem;
            border-bottom: 2px solid #abb8c3;
        }

        /* Company name styling */
        .company-name {
            color: white;
            font-size: 1.5rem;
            font-weight: 700;
            line-height: 2.5rem;
            margin: 0;
            display: inline-block;
            margin-right: 2rem;
        }

        /* Main Dashboard link styling */
        .dashboard-link {
            color: white;
            font-size: 1rem;
            font-weight: 500;
            text-decoration: none;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            transition: background-color 0.2s;
            display: inline-block;
            line-height: 2.5rem;
            vertical-align: middle;
        }

        .dashboard-link:hover {
            background-color: rgba(255, 255, 255, 0.1);
            text-decoration: none;
        }

        /* User info container */
        .user-info {
            color: white;
            font-size: 1rem;
            text-align: right;
            line-height: 2.5rem;
        }

        .user-name {
            color: white;
            font-weight: 600;
            margin-right: 1rem;
        }

        .role-badge {
            background: #000000;
            color: #abb8c3;
            padding: 0.25rem 0.75rem;
            border-radius: 4px;
            font-size: 0.875rem;
            border: 1px solid #abb8c3;
        }

        /* Style buttons in header (Sign Out and Main Dashboard) */
        div[data-testid="stHorizontalBlock"]:has(div.header-content) .stButton > button {
            background: transparent !important;
            color: #abb8c3 !important;
            border: none !important;
            padding: 0.4rem 0.8rem !important;
            font-size: 0.875rem !important;
            font-weight: 400 !important;
            box-shadow: none !important;
            height: auto !important;
            min-height: 2.5rem !important;
            line-height: 2.5rem !important;
        }

        div[data-testid="stHorizontalBlock"]:has(div.header-content) .stButton > button:hover {
            background: transparent !important;
            color: white !important;
            border: none !important;
            text-decoration: underline;
        }

        div[data-testid="stHorizontalBlock"]:has(div.header-content) .stButton > button:focus,
        div[data-testid="stHorizontalBlock"]:has(div.header-content) .stButton > button:active {
            background: transparent !important;
            box-shadow: none !important;
            border: none !important;
        }

        /* Style Main Dashboard button specifically */
        div[data-testid="stHorizontalBlock"]:has(div.header-content) .stButton:has(button[key*="dashboard"]) > button {
            color: white !important;
            font-size: 1rem !important;
            font-weight: 500 !important;
            padding: 0.5rem 1rem !important;
        }

        div[data-testid="stHorizontalBlock"]:has(div.header-content) .stButton:has(button[key*="dashboard"]) > button:hover {
            background-color: rgba(255, 255, 255, 0.1) !important;
            text-decoration: none !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # Header bar with columns
    col1, col2 = st.columns([2, 3])

    with col1:
        # Company name and Main Dashboard button side by side
        col1_inner1, col1_inner2 = st.columns([3, 2])

        with col1_inner1:
            st.markdown('<div class="header-content"><p class="company-name">California Drywall</p></div>', unsafe_allow_html=True)

        with col1_inner2:
            # Main Dashboard button
            if st.button("Main Dashboard", key="nav_dashboard_btn"):
                # Navigate to home/main dashboard
                if 'current_page' in st.session_state:
                    st.session_state.current_page = 'home'
                if 'selected_project_id' in st.session_state:
                    st.session_state.selected_project_id = None
                st.rerun()

    with col2:
        # User info all on one line with clickable Sign Out
        col2_inner1, col2_inner2 = st.columns([4, 1])

        with col2_inner1:
            user_html = f'''
            <div class="header-content user-info">
                <span class="user-name">{full_name}</span>
                <span class="role-badge">{role_display}</span>
            </div>
            '''
            st.markdown(user_html, unsafe_allow_html=True)

        with col2_inner2:
            # Sign Out button styled to match header
            if st.button("Sign Out", key="signout_btn"):
                st.session_state.authenticated = False
                st.session_state.user = None
                st.session_state.user_profile = None
                if 'current_page' in st.session_state:
                    st.session_state.current_page = 'home'
                if 'selected_project_id' in st.session_state:
                    st.session_state.selected_project_id = None
                st.rerun()


def add_navigation_styles():
    """
    Add consistent navigation and styling CSS to all pages
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

        /* Consistent page spacing */
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
