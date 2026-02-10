"""
Admin Panel Page Module
"""

import streamlit as st
import db_utils
import components

def show():
    """Display admin panel interface"""

    # Check authentication
    if not st.session_state.get('authenticated'):
        st.error("Please log in first")
        return

    # Check role
    user_role = st.session_state.user_profile.get('role')
    if user_role not in ['executive', 'admin']:
        st.warning(f"This page is for executives and admins. You are logged in as: {user_role}")
        return

    # Add global styles and render unified header
    components.add_global_styles()
    components.render_header(current_page='admin_panel')

    # Page title
    components.render_page_title(
        "Admin Panel",
        "Manage projects, users, and system settings"
    )

    st.info("""
    **Admin Panel**

    This page is being rebuilt with the new navigation system.

    For now, please use the original admin panel by running:
    ```
    streamlit run pages/3__Admin_Panel.py
    ```

    Full integration coming soon!
    """)

    if st.button("Return to Dashboard"):
        st.session_state.current_page = 'home'
        st.rerun()
