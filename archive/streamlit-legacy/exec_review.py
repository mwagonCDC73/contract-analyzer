"""
Executive Review Dashboard - California Drywall Contract Review System
Allows Executives to review contract submissions from Project Managers
"""

import streamlit as st
import os
from dotenv import load_dotenv
from datetime import datetime
import json

# Import database utilities
import db_utils

# Load environment variables
load_dotenv(override=True)

# Page config
st.set_page_config(
    page_title="Executive Review - California Drywall",
    layout="wide"
)

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = None
if 'selected_project_id' not in st.session_state:
    st.session_state.selected_project_id = None


def login_form():
    """Display login form for executives"""
    st.title("California Drywall Contract Review")
    st.subheader("Executive Dashboard Login")

    with st.form("login_form"):
        email = st.text_input("Email", placeholder="exec.test@caldrywall.com")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login", use_container_width=True)

        if submit:
            if not email or not password:
                st.error("Please enter both email and password")
                return

            with st.spinner("Logging in..."):
                auth_response = db_utils.authenticate_user(email, password)

                if auth_response and auth_response.user:
                    # Get user profile
                    profile = db_utils.get_user_profile(auth_response.user.id)

                    if not profile:
                        st.error(f"User profile not found for {email}. Please contact your administrator.")
                        return

                    st.session_state.authenticated = True
                    st.session_state.user = auth_response.user
                    st.session_state.user_profile = profile

                    if profile.get('role') not in ['executive', 'admin']:
                        st.warning(f"Note: You're logged in as {profile.get('role')}. This dashboard is for Executives.")

                    st.success(f"Welcome, {profile.get('full_name', email)}!")
                    st.rerun()
                else:
                    st.error("Invalid email or password")


def get_all_projects():
    """Get all projects with submitted status"""
    supabase = db_utils.get_supabase_client()
    try:
        # Fetch projects
        response = supabase.table("projects").select("*").order("submitted_at", desc=True).execute()
        projects = response.data if response.data else []

        # Manually fetch project manager names
        for project in projects:
            pm_id = project.get('project_manager_id')
            if pm_id:
                try:
                    pm_response = supabase.table("user_profiles").select("full_name").eq("id", pm_id).execute()
                    if pm_response.data and len(pm_response.data) > 0:
                        project['project_manager'] = {'full_name': pm_response.data[0]['full_name']}
                    else:
                        project['project_manager'] = {'full_name': 'Unknown PM'}
                except:
                    project['project_manager'] = {'full_name': 'Unknown PM'}
            else:
                project['project_manager'] = {'full_name': 'Unknown PM'}

        return projects
    except Exception as e:
        st.error(f"Error fetching projects: {e}")
        return []


def get_project_contracts(project_id):
    """Get all contracts for a project"""
    supabase = db_utils.get_supabase_client()
    try:
        response = supabase.table("contracts").select("*").eq("project_id", project_id).execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Error fetching contracts: {e}")
        return []


def get_contract_red_flags(contract_id):
    """Get all red flags for a contract"""
    supabase = db_utils.get_supabase_client()
    try:
        response = supabase.table("red_flags").select("*").eq("contract_id", contract_id).order("severity", desc=False).execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Error fetching red flags: {e}")
        return []


def update_red_flag_status(flag_id, status):
    """Update red flag review status"""
    supabase = db_utils.get_supabase_client()
    try:
        response = supabase.table("red_flags").update({"review_status": status}).eq("id", flag_id).execute()
        return True
    except Exception as e:
        st.error(f"Error updating red flag: {e}")
        return False


def display_severity_badge(severity):
    """Display colored badge for severity level"""
    colors = {
        "critical": "",
        "warning": "",
        "informational": ""
    }
    return colors.get(severity, "")


def get_status_badge(status):
    """Get badge for review status"""
    badges = {
        "needs_review": "Needs Review",
        "reviewed": "Reviewed",
        "resolved": "Resolved"
    }
    return badges.get(status, status)


def projects_list():
    """Display list of all submitted projects"""

    # Check if user profile exists
    if not st.session_state.user_profile:
        st.error("User profile not found. Please log in again.")
        st.session_state.authenticated = False
        st.rerun()
        return

    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("Contract Submissions")
        st.write(f"Welcome, **{st.session_state.user_profile.get('full_name')}** ({st.session_state.user_profile.get('role')})")
    with col2:
        if st.button("Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.session_state.user_profile = None
            st.session_state.selected_project_id = None
            st.rerun()

    st.divider()

    # Get all projects
    projects = get_all_projects()

    if not projects:
        st.info("No contract submissions yet")
        return

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Submissions", len(projects))
    with col2:
        submitted = len([p for p in projects if p.get('status') == 'submitted'])
        st.metric("Pending Review", submitted)
    with col3:
        under_review = len([p for p in projects if p.get('status') == 'under_review'])
        st.metric("Under Review", under_review)
    with col4:
        approved = len([p for p in projects if p.get('status') == 'approved'])
        st.metric("Approved", approved)

    st.divider()

    # Filter options
    st.subheader("Filter Projects")
    col1, col2 = st.columns([1, 3])
    with col1:
        status_filter = st.multiselect(
            "Status",
            ["submitted", "under_review", "approved", "rejected"],
            default=["submitted", "under_review"]
        )

    # Filter projects
    filtered_projects = [p for p in projects if p.get('status') in status_filter]

    # Display projects
    st.subheader(f"Projects ({len(filtered_projects)})")

    for project in filtered_projects:
        with st.container():
            # Get project manager name
            pm_name = "Unknown PM"
            if project.get('project_manager'):
                pm_name = project['project_manager'].get('full_name', 'Unknown PM')

            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

            with col1:
                st.markdown(f"**{project.get('project_name')}**")
                if project.get('project_number'):
                    st.caption(f"Project #{project.get('project_number')}")

            with col2:
                st.caption(f"PM: {pm_name}")
                submitted_date = project.get('submitted_at')
                if submitted_date:
                    st.caption(f"Submitted: {datetime.fromisoformat(submitted_date.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M')}")

            with col3:
                status = project.get('status', 'unknown')
                status_colors = {
                    "submitted": "",
                    "under_review": "",
                    "approved": "",
                    "rejected": ""
                }
                st.markdown(f"{status_colors.get(status, '')} **{status.replace('_', ' ').title()}**")

            with col4:
                if st.button("Review", key=f"review_{project['id']}", use_container_width=True):
                    st.session_state.selected_project_id = project['id']
                    st.rerun()

            st.divider()


def project_detail_view():
    """Display detailed view of a specific project"""

    project_id = st.session_state.selected_project_id

    # Get project details
    supabase = db_utils.get_supabase_client()
    try:
        # Fetch project
        project_response = supabase.table("projects").select("*").eq("id", project_id).execute()
        if not project_response.data or len(project_response.data) == 0:
            st.error("Project not found")
            if st.button("← Back to Projects"):
                st.session_state.selected_project_id = None
                st.rerun()
            return

        project = project_response.data[0]

        # Fetch project manager name
        pm_id = project.get('project_manager_id')
        if pm_id:
            try:
                pm_response = supabase.table("user_profiles").select("full_name").eq("id", pm_id).execute()
                if pm_response.data and len(pm_response.data) > 0:
                    project['project_manager'] = {'full_name': pm_response.data[0]['full_name']}
                else:
                    project['project_manager'] = {'full_name': 'Unknown PM'}
            except:
                project['project_manager'] = {'full_name': 'Unknown PM'}
        else:
            project['project_manager'] = {'full_name': 'Unknown PM'}

    except Exception as e:
        st.error(f"Error loading project: {e}")
        if st.button("← Back to Projects"):
            st.session_state.selected_project_id = None
            st.rerun()
        return

    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(f"{project.get('project_name')}")
        if project.get('project_number'):
            st.caption(f"Project #{project.get('project_number')}")
    with col2:
        if st.button("← Back to Projects", use_container_width=True):
            st.session_state.selected_project_id = None
            st.rerun()

    st.divider()

    # Project Info
    col1, col2, col3 = st.columns(3)
    with col1:
        pm_name = "Unknown PM"
        if project.get('project_manager'):
            pm_name = project['project_manager'].get('full_name', 'Unknown PM')
        st.info(f"**Project Manager:** {pm_name}")
    with col2:
        submitted_date = project.get('submitted_at')
        if submitted_date:
            st.info(f"**Submitted:** {datetime.fromisoformat(submitted_date.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M')}")
    with col3:
        status = project.get('status', 'unknown')
        st.info(f"**Status:** {status.replace('_', ' ').title()}")

    # PM Notes
    if project.get('pm_notes'):
        with st.expander("Project Manager Notes"):
            st.write(project.get('pm_notes'))

    st.divider()

    # Get contracts
    contracts = get_project_contracts(project_id)

    if not contracts:
        st.warning("No contracts found for this project")
        return

    # Display contracts
    st.subheader(f"Contracts ({len(contracts)})")

    for contract in contracts:
        contract_type = contract.get('contract_type', 'unknown').title()

        with st.expander(f"**{contract_type} Contract** - {contract.get('file_name')}", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Analysis Status", contract.get('analysis_status', 'unknown').title())
            with col2:
                analysis_date = contract.get('analysis_date')
                if analysis_date:
                    st.caption(f"Analyzed: {datetime.fromisoformat(analysis_date.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M')}")
                else:
                    st.caption("Not analyzed yet")
            with col3:
                # Download original contract file
                file_path = contract.get('file_path')
                file_name = contract.get('file_name')
                if file_path:
                    try:
                        # Fetch file from Supabase Storage
                        file_data = supabase.storage.from_("contracts").download(file_path)
                        st.download_button(
                            label="Download Original",
                            data=file_data,
                            file_name=file_name,
                            mime="application/pdf",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.caption(f"File unavailable")
                        st.caption(f"Error: {str(e)}")

            # Get analysis results
            analysis_results = contract.get('analysis_results')

            if analysis_results and isinstance(analysis_results, dict):
                summary = analysis_results.get('summary', {})

                # Summary metrics
                st.markdown("### Analysis Summary")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Issues", summary.get('total_issues', 0))
                with col2:
                    st.metric("Critical", summary.get('critical', 0))
                with col3:
                    st.metric("Warning", summary.get('warning', 0))
                with col4:
                    st.metric("Informational", summary.get('informational', 0))

                # Risk assessment
                critical_count = summary.get('critical', 0)
                warning_count = summary.get('warning', 0)

                if critical_count > 0:
                    st.error(f"**HIGH RISK**: {critical_count} critical issues must be resolved before contract execution")
                elif warning_count > 3:
                    st.warning(f"**MODERATE RISK**: {warning_count} warnings require review and potential negotiation")
                else:
                    st.success("**LOW RISK**: No critical issues found")

                st.divider()

                # Get red flags from database
                red_flags = get_contract_red_flags(contract.get('id'))

                if red_flags:
                    st.markdown("### 🚩 Red Flags")

                    # Filter by severity
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        severity_filter = st.multiselect(
                            "Filter by severity:",
                            ["critical", "warning", "informational"],
                            default=["critical", "warning", "informational"],
                            key=f"severity_filter_{contract.get('id')}"
                        )

                    with col2:
                        status_filter = st.multiselect(
                            "Filter by status:",
                            ["needs_review", "reviewed", "resolved"],
                            default=["needs_review", "reviewed"],
                            key=f"status_filter_{contract.get('id')}"
                        )

                    # Filter red flags
                    filtered_flags = [
                        f for f in red_flags
                        if f.get('severity') in severity_filter
                        and f.get('review_status') in status_filter
                    ]

                    st.caption(f"Showing {len(filtered_flags)} of {len(red_flags)} red flags")

                    # Display red flags
                    for idx, flag in enumerate(filtered_flags, 1):
                        severity = flag.get('severity', 'informational')

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

                            col1, col2, col3 = st.columns([2, 1, 1])
                            with col1:
                                st.markdown(f"**{display_severity_badge(severity)} {flag.get('issue_title')}**")
                            with col2:
                                st.caption(f"{flag.get('category', 'Uncategorized')}")
                            with col3:
                                st.caption(get_status_badge(flag.get('review_status', 'needs_review')))

                            st.markdown(f"**Details:** {flag.get('details', 'No details provided')}")

                            if flag.get('location'):
                                st.caption(f"📍 Location: {flag.get('location')}")

                            st.info(f"**Recommendation:** {flag.get('recommendation', 'No recommendation provided')}")

                            # Update status buttons
                            col1, col2, col3, col4 = st.columns([1, 1, 1, 3])
                            with col1:
                                if st.button("Resolve", key=f"resolve_{flag.get('id')}"):
                                    if update_red_flag_status(flag.get('id'), 'resolved'):
                                        st.success("Marked as resolved")
                                        st.rerun()
                            with col2:
                                if st.button("Review", key=f"review_{flag.get('id')}"):
                                    if update_red_flag_status(flag.get('id'), 'reviewed'):
                                        st.success("Marked as reviewed")
                                        st.rerun()
                            with col3:
                                if st.button("Reset", key=f"reset_{flag.get('id')}"):
                                    if update_red_flag_status(flag.get('id'), 'needs_review'):
                                        st.success("Reset to needs review")
                                        st.rerun()

                            st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.info("No red flags found in database")

                # Download options
                st.divider()
                st.markdown("### Download Options")
                col1, col2, col3 = st.columns(3)
                with col1:
                    analysis_json = json.dumps(analysis_results, indent=2)
                    st.download_button(
                        label="Download Analysis (JSON)",
                        data=analysis_json,
                        file_name=f"{contract_type}_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        use_container_width=True
                    )
                with col2:
                    # Download original contract file
                    file_path = contract.get('file_path')
                    file_name = contract.get('file_name')
                    if file_path:
                        try:
                            file_data = supabase.storage.from_("contracts").download(file_path)
                            st.download_button(
                                label="Download Original Contract",
                                data=file_data,
                                file_name=file_name,
                                mime="application/pdf",
                                use_container_width=True
                            )
                        except Exception as e:
                            st.button(
                                label="Original Unavailable",
                                disabled=True,
                                use_container_width=True
                            )
            else:
                st.warning("No analysis results available for this contract")
                # Still offer to download original contract if no analysis
                file_path = contract.get('file_path')
                file_name = contract.get('file_name')
                if file_path:
                    st.divider()
                    st.markdown("### Download Options")
                    try:
                        file_data = supabase.storage.from_("contracts").download(file_path)
                        st.download_button(
                            label="Download Original Contract",
                            data=file_data,
                            file_name=file_name,
                            mime="application/pdf"
                        )
                    except Exception as e:
                        st.caption(f"Original contract file unavailable: {str(e)}")

    # Project Actions
    st.divider()
    st.subheader("Project Actions")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("Mark Under Review", use_container_width=True):
            if db_utils.update_project_status(project_id, "under_review"):
                st.success("Project marked as under review")
                st.rerun()

    with col2:
        if st.button("Approve Project", use_container_width=True):
            if db_utils.update_project_status(project_id, "approved"):
                st.success("Project approved!")
                st.rerun()

    with col3:
        if st.button("Reject Project", use_container_width=True):
            if db_utils.update_project_status(project_id, "rejected"):
                st.warning("Project rejected")
                st.rerun()

    with col4:
        if st.button("Reset to Submitted", use_container_width=True):
            if db_utils.update_project_status(project_id, "submitted"):
                st.info("Project reset to submitted")
                st.rerun()


# Main app logic
def main():
    if not st.session_state.authenticated:
        login_form()
    else:
        if st.session_state.selected_project_id:
            project_detail_view()
        else:
            projects_list()


if __name__ == "__main__":
    main()
