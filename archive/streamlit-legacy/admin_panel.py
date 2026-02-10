"""
Admin Panel - California Drywall Contract Review System
Allows admins to manage projects, users, and data
"""

import streamlit as st
import os
from dotenv import load_dotenv
from datetime import datetime
import db_utils

# Load environment variables
load_dotenv(override=True)

# Page config
st.set_page_config(
    page_title="Admin Panel - California Drywall",
    layout="wide"
)

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = None


def login_form():
    """Display login form for admins"""
    st.title("California Drywall Contract Review")
    st.subheader("Admin Panel Login")

    with st.form("login_form"):
        email = st.text_input("Email", placeholder="admin@caldrywall.com")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login", use_container_width=True)

        if submit:
            if not email or not password:
                st.error("Please enter both email and password")
                return

            with st.spinner("Logging in..."):
                auth_response = db_utils.authenticate_user(email, password)

                if auth_response and auth_response.user:
                    profile = db_utils.get_user_profile(auth_response.user.id)

                    if not profile:
                        st.error(f"User profile not found for {email}")
                        return

                    # Check if user has admin or executive role
                    if profile.get('role') not in ['admin', 'executive']:
                        st.error("Access denied. Admin or Executive role required.")
                        return

                    st.session_state.authenticated = True
                    st.session_state.user = auth_response.user
                    st.session_state.user_profile = profile
                    st.success(f"Welcome, {profile.get('full_name', email)}!")
                    st.rerun()
                else:
                    st.error("Invalid email or password")


def get_all_projects_admin():
    """Get all projects for admin view"""
    supabase = db_utils.get_supabase_client()
    try:
        response = supabase.table("projects").select("*").order("created_at", desc=True).execute()
        projects = response.data if response.data else []

        # Fetch PM names
        for project in projects:
            pm_id = project.get('project_manager_id')
            if pm_id:
                try:
                    pm_response = supabase.table("user_profiles").select("full_name").eq("id", pm_id).execute()
                    if pm_response.data and len(pm_response.data) > 0:
                        project['pm_name'] = pm_response.data[0]['full_name']
                    else:
                        project['pm_name'] = 'Unknown PM'
                except:
                    project['pm_name'] = 'Unknown PM'
            else:
                project['pm_name'] = 'Unknown PM'

        return projects
    except Exception as e:
        st.error(f"Error fetching projects: {e}")
        return []


def delete_project_cascade(project_id):
    """Delete project and all associated data"""
    supabase = db_utils.get_supabase_client()
    try:
        # Get contracts
        contracts = supabase.table('contracts').select('id, file_path').eq('project_id', project_id).execute()

        if contracts.data:
            for contract in contracts.data:
                # Delete red flags
                supabase.table('red_flags').delete().eq('contract_id', contract['id']).execute()

                # Delete storage file
                if contract.get('file_path'):
                    try:
                        supabase.storage.from_('contracts').remove([contract['file_path']])
                    except Exception as e:
                        st.warning(f"Could not delete file {contract['file_path']}: {e}")

        # Delete contracts
        supabase.table('contracts').delete().eq('project_id', project_id).execute()

        # Delete project
        supabase.table('projects').delete().eq('id', project_id).execute()

        return True
    except Exception as e:
        st.error(f"Error deleting project: {e}")
        return False


def archive_project(project_id):
    """Archive a project by setting status to archived"""
    supabase = db_utils.get_supabase_client()
    try:
        supabase.table('projects').update({
            'status': 'archived',
            'archived_at': 'now()'
        }).eq('id', project_id).execute()
        return True
    except Exception as e:
        st.error(f"Error archiving project: {e}")
        return False


def admin_dashboard():
    """Main admin dashboard"""

    # Check if user profile exists
    if not st.session_state.user_profile:
        st.error("User profile not found. Please log in again.")
        st.session_state.authenticated = False
        st.rerun()
        return

    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("Admin Panel")
        st.write(f"Welcome, **{st.session_state.user_profile.get('full_name')}** ({st.session_state.user_profile.get('role')})")
    with col2:
        if st.button("Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.session_state.user_profile = None
            st.rerun()

    st.divider()

    # Tabs for different admin functions
    tab1, tab2, tab3 = st.tabs(["Manage Projects", "Statistics", "Bulk Actions"])

    with tab1:
        st.subheader("Project Management")

        # Filters
        col1, col2, col3 = st.columns([2, 2, 2])
        with col1:
            status_filter = st.multiselect(
                "Filter by Status",
                ["draft", "submitted", "under_review", "approved", "rejected", "archived"],
                default=["draft", "submitted", "under_review"]
            )
        with col2:
            search_term = st.text_input("Search by name/number", "")

        # Get all projects
        projects = get_all_projects_admin()

        # Apply filters
        if status_filter:
            projects = [p for p in projects if p.get('status') in status_filter]

        if search_term:
            projects = [p for p in projects if
                       search_term.lower() in p.get('project_name', '').lower() or
                       search_term.lower() in p.get('project_number', '').lower()]

        st.info(f"Showing {len(projects)} projects")

        # Display projects
        for project in projects:
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1, 1])

                with col1:
                    st.markdown(f"**{project.get('project_name')}**")
                    st.caption(f"#{project.get('project_number')} | PM: {project.get('pm_name')}")

                with col2:
                    created = project.get('created_at')
                    if created:
                        st.caption(f"Created: {datetime.fromisoformat(created.replace('Z', '+00:00')).strftime('%Y-%m-%d')}")

                with col3:
                    status = project.get('status', 'unknown')
                    status_colors = {
                        "draft": "",
                        "submitted": "",
                        "under_review": "",
                        "approved": "",
                        "rejected": "",
                        "archived": ""
                    }
                    st.markdown(f"{status_colors.get(status, '')} {status.replace('_', ' ').title()}")

                with col4:
                    if status != 'archived':
                        if st.button("Archive", key=f"archive_{project['id']}", use_container_width=True):
                            if archive_project(project['id']):
                                st.success("Archived!")
                                st.rerun()

                with col5:
                    if st.button("Delete", key=f"delete_{project['id']}", use_container_width=True, type="secondary"):
                        # Show confirmation dialog
                        st.session_state[f"confirm_delete_{project['id']}"] = True

                # Confirmation dialog
                if st.session_state.get(f"confirm_delete_{project['id']}", False):
                    st.warning(f"Delete '{project.get('project_name')}'? This will delete all contracts, red flags, and files. This cannot be undone!")
                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("Yes, Delete", key=f"confirm_yes_{project['id']}"):
                            if delete_project_cascade(project['id']):
                                st.success("Project deleted!")
                                st.session_state[f"confirm_delete_{project['id']}"] = False
                                st.rerun()
                    with col_no:
                        if st.button("Cancel", key=f"confirm_no_{project['id']}"):
                            st.session_state[f"confirm_delete_{project['id']}"] = False
                            st.rerun()

                st.divider()

    with tab2:
        st.subheader("System Statistics")

        supabase = db_utils.get_supabase_client()

        # Get counts
        try:
            projects_response = supabase.table('projects').select('id, status').execute()
            contracts_response = supabase.table('contracts').select('id').execute()
            red_flags_response = supabase.table('red_flags').select('id').execute()
            users_response = supabase.table('user_profiles').select('id, role').execute()

            # Display metrics
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Total Projects", len(projects_response.data) if projects_response.data else 0)

            with col2:
                st.metric("Total Contracts", len(contracts_response.data) if contracts_response.data else 0)

            with col3:
                st.metric("Total Red Flags", len(red_flags_response.data) if red_flags_response.data else 0)

            with col4:
                st.metric("Total Users", len(users_response.data) if users_response.data else 0)

            # Status breakdown
            st.divider()
            st.subheader("Projects by Status")

            if projects_response.data:
                status_counts = {}
                for p in projects_response.data:
                    status = p.get('status', 'unknown')
                    status_counts[status] = status_counts.get(status, 0) + 1

                for status, count in sorted(status_counts.items()):
                    st.write(f"**{status.replace('_', ' ').title()}:** {count}")

            # Users breakdown
            st.divider()
            st.subheader("Users by Role")

            if users_response.data:
                role_counts = {}
                for u in users_response.data:
                    role = u.get('role', 'unknown')
                    role_counts[role] = role_counts.get(role, 0) + 1

                for role, count in sorted(role_counts.items()):
                    st.write(f"**{role.replace('_', ' ').title()}:** {count}")

        except Exception as e:
            st.error(f"Error fetching statistics: {e}")

    with tab3:
        st.subheader("Bulk Actions")
        st.warning("Bulk actions are destructive and cannot be undone!")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Delete by Status")
            delete_status = st.selectbox(
                "Select status to delete",
                ["draft", "submitted", "under_review", "approved", "rejected", "archived"]
            )

            if st.button("Delete All Projects with This Status", type="secondary"):
                st.session_state.confirm_bulk_delete_status = delete_status

            if st.session_state.get('confirm_bulk_delete_status'):
                status = st.session_state.confirm_bulk_delete_status
                st.error(f"Delete ALL projects with status '{status}'?")

                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("Yes, Delete All", key="bulk_delete_confirm"):
                        # Get projects with this status
                        projects = supabase.table('projects').select('id').eq('status', status).execute()
                        count = len(projects.data) if projects.data else 0

                        if count > 0:
                            progress_bar = st.progress(0)
                            for i, project in enumerate(projects.data):
                                delete_project_cascade(project['id'])
                                progress_bar.progress((i + 1) / count)

                            st.success(f"Deleted {count} projects!")
                            st.session_state.confirm_bulk_delete_status = None
                            st.rerun()
                        else:
                            st.info(f"No projects with status '{status}'")
                            st.session_state.confirm_bulk_delete_status = None

                with col_no:
                    if st.button("Cancel", key="bulk_delete_cancel"):
                        st.session_state.confirm_bulk_delete_status = None
                        st.rerun()

        with col2:
            st.markdown("### Archive by Date")
            archive_before = st.date_input("Archive projects created before")

            if st.button("Archive Old Projects"):
                st.info("Archive functionality - would archive projects before selected date")


# Main app logic
def main():
    if not st.session_state.authenticated:
        login_form()
    else:
        admin_dashboard()


if __name__ == "__main__":
    main()
