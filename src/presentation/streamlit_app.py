import sys
from pathlib import Path

# Add project root to Python path for src imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

from src.application.services.job_orchestrator import JobOrchestrator
from src.infrastructure.adapters.blacklist_file_based import BlacklistFileBasedAdapter
from src.infrastructure.adapters.company_command_file_based import (
    CompanyCommandFileBasedAdapter,
)
from src.infrastructure.adapters.company_query_file_based import (
    CompanyQueryFileBasedAdapter,
)
from src.infrastructure.adapters.job_command_file_based import (
    JobCommandFileBasedAdapter,
)
from src.infrastructure.adapters.job_query_file_based import JobQueryFileBasedAdapter
from src.infrastructure.scrapers.jobspy_scraper import JobspyScraper
from src.infrastructure.scrapers.kununu_scraper import KununuScraper
from src.utils.settings import COMPANY_BLACKLIST_FILENAME, JOB_BLACKLIST_FILENAME


@st.cache_resource
def get_orchestrator() -> JobOrchestrator:
    """Initialize the job orchestrator with all adapters"""
    job_query_adapter = JobQueryFileBasedAdapter()
    job_command_adapter = JobCommandFileBasedAdapter()
    company_query_adapter = CompanyQueryFileBasedAdapter()
    company_command_adapter = CompanyCommandFileBasedAdapter()
    company_blacklist_adapter = BlacklistFileBasedAdapter(COMPANY_BLACKLIST_FILENAME)
    job_blacklist_adapter = BlacklistFileBasedAdapter(JOB_BLACKLIST_FILENAME)
    kununu_scraper = KununuScraper
    job_scraper_adapter = JobspyScraper()

    return JobOrchestrator(
        job_query_port=job_query_adapter,
        job_command_port=job_command_adapter,
        company_query_port=company_query_adapter,
        company_command_port=company_command_adapter,
        company_scraper=kununu_scraper,
        job_scraper_port=job_scraper_adapter,
        company_blacklist_port=company_blacklist_adapter,
        job_blacklist_port=job_blacklist_adapter,
    )


def main():
    st.set_page_config(page_title="Job Search Dashboard", layout="wide")
    st.title("Job Search Dashboard")

    orchestrator = get_orchestrator()

    # Sidebar filters
    st.sidebar.header("Filters")

    # Minimum rating filter
    min_rating = st.sidebar.slider(
        "Minimum Kununu Rating",
        min_value=0.0,
        max_value=5.0,
        value=0.0,
        step=0.1,
        help="Filter jobs by minimum company rating (0 = show all)",
    )

    # Blacklist management
    st.sidebar.header("Blacklist Management")

    # Get all unique company names
    all_companies = sorted([company.name for company in orchestrator.companies()])
    current_blacklist = orchestrator.company_blacklist()

    # Multiselect for blacklist
    selected_blacklist = st.sidebar.multiselect(
        "Blacklisted Companies",
        options=all_companies,
        default=current_blacklist,
        help="Select companies to exclude from results",
    )

    # Update blacklist if changed
    if set(selected_blacklist) != set(current_blacklist):
        # Add newly selected companies
        for company in set(selected_blacklist) - set(current_blacklist):
            orchestrator.add_to_blacklist(company)
        # Remove deselected companies
        for company in set(current_blacklist) - set(selected_blacklist):
            orchestrator.remove_from_blacklist(company)
        st.sidebar.success("Blacklist updated!")

    # Get filtered jobs dataframe
    df = orchestrator.get_jobs_dataframe(min_rating=min_rating, apply_blacklist=True)

    # Display stats
    st.header("Overview")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Jobs", len(df))
    with col2:
        jobs_with_rating = df["kununu_rating"].notna().sum()
        st.metric("Jobs with Rating", jobs_with_rating)
    with col3:
        st.metric("Blacklisted Companies", len(current_blacklist))
    with col4:
        avg_rating = df["kununu_rating"].mean()
        st.metric("Avg Rating", f"{avg_rating:.2f}" if avg_rating else "N/A")

    # Display jobs table
    st.header("Job Listings")

    if df.empty:
        st.warning("No jobs found matching your criteria.")
    else:
        # Select columns to display
        display_columns = [
            "job_id",
            "title",
            "company_name",
            "kununu_rating",
            "url",
            "kununu_review_count",
            "location",
            "working_model",
            "salary",
        ]

        # Filter to only existing columns
        display_columns = [col for col in display_columns if col in df.columns]

        # Sort by rating (descending), then by company name
        df_display = (
            df[display_columns]
            .sort_values(
                by=["kununu_rating", "company_name"],
                ascending=[False, True],
                na_position="last",
            )
            .copy()
        )

        # Add checkbox column for hiding jobs
        df_display.insert(0, "Hide", False)

        # Format the dataframe with editable checkboxes
        edited_df = st.data_editor(
            df_display,
            width="stretch",
            hide_index=True,
            column_config={
                "Hide": st.column_config.CheckboxColumn(
                    "Hide",
                    help="Check to hide this job from future views",
                    width=60,
                ),
                "job_id": None,  # Hide job_id column
                "title": st.column_config.TextColumn("Job Title", width="large"),
                "company_name": st.column_config.TextColumn("Company", width="medium"),
                "kununu_rating": st.column_config.NumberColumn(
                    "Rating", format="%.2f", width=80
                ),
                "url": st.column_config.LinkColumn("Link", width=150),
                "kununu_review_count": st.column_config.NumberColumn(
                    "Reviews", width=80
                ),
                "location": st.column_config.TextColumn("Location", width="medium"),
                "working_model": st.column_config.TextColumn("Model", width=100),
                "salary": st.column_config.NumberColumn(
                    "Salary", format="€%d", width=100
                ),
            },
            disabled=[
                "job_id",
                "title",
                "company_name",
                "kununu_rating",
                "url",
                "kununu_review_count",
                "location",
                "working_model",
                "salary",
            ],
        )

        # Process checkbox changes
        jobs_to_hide = edited_df[edited_df["Hide"]]["job_id"].tolist()
        if jobs_to_hide:
            for job_id in jobs_to_hide:
                orchestrator.add_to_job_blacklist(job_id)
            st.success(
                f"Added {len(jobs_to_hide)} job(s) to hidden list. Refresh to update."
            )
            st.button("Refresh", on_click=st.rerun)

    # Export functionality
    st.sidebar.header("Export")
    if st.sidebar.button("Export to CSV"):
        orchestrator.export_to_csv()
        st.sidebar.success("Exported to data/filtered_jobs.csv")


if __name__ == "__main__":
    main()
