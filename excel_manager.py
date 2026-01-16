import pandas as pd
from datetime import datetime
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows

EXCEL_FILE = "applications.xlsx"
APPLIED_SHEET = "applied_jobs"        # Main sheet for applied positions
SUGGESTIONS_SHEET = "job_suggestions"  # New sheet for recommendations

# Excel schema with all tracking fields (Applied Jobs)
SCHEMA = {
    "Company": str,
    "Role": str,
    "Status": str,                  # Applied, Interview, Offer, Rejected
    "Applied_Date": str,            # Date when initially applied (YYYY-MM-DD)
    "Last_Update": str,             # Latest status update date (YYYY-MM-DD)
    "Recruiter_Email": str,         # Contact email of recruiter
    "Email_Subject": str,           # Original email subject
    "Notes": str,                   # Additional notes or follow-up suggestions
    "Days_Since_Update": int        # Calculated field for dashboard (computed on read)
}

# Schema for job suggestions (recommendations not yet applied)
SUGGESTIONS_SCHEMA = {
    "Company": str,
    "Role": str,
    "Source": str,                  # LinkedIn / Glassdoor / Email / Other
    "Email_Date": str,              # Date email received (YYYY-MM-DD)
    "Saved": str,                   # Yes / No / Maybe
    "Notes": str                    # Additional details about the role
}


def get_or_create_dataframe():
    """Load Excel file or create empty DataFrame with proper schema."""
    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name=APPLIED_SHEET)
        # Ensure all columns exist (backward compatibility)
        for col in SCHEMA.keys():
            if col not in df.columns:
                df[col] = None
        return df
    except (FileNotFoundError, ValueError):
        # Create new DataFrame with schema
        df = pd.DataFrame(columns=SCHEMA.keys())
        # Ensure both sheets exist when creating new file
        _ensure_all_sheets_exist()
        return df


def _ensure_all_sheets_exist():
    """Ensure both applied_jobs and job_suggestions sheets exist."""
    try:
        with pd.ExcelFile(EXCEL_FILE) as xls:
            sheets = xls.sheet_names
            if APPLIED_SHEET not in sheets:
                df_applied = pd.DataFrame(columns=SCHEMA.keys())
                with pd.ExcelWriter(EXCEL_FILE, mode="a", engine="openpyxl") as writer:
                    df_applied.to_excel(writer, sheet_name=APPLIED_SHEET, index=False)
            if SUGGESTIONS_SHEET not in sheets:
                df_suggestions = pd.DataFrame(columns=SUGGESTIONS_SCHEMA.keys())
                with pd.ExcelWriter(EXCEL_FILE, mode="a", engine="openpyxl") as writer:
                    df_suggestions.to_excel(writer, sheet_name=SUGGESTIONS_SHEET, index=False)
    except FileNotFoundError:
        # File doesn't exist yet - will be created on first write
        pass


def get_job_record(company: str, role: str):
    """Fetch existing job record by company + role (unique key)."""
    df = get_or_create_dataframe()
    match = df[
        (df["Company"].str.strip().str.lower() == company.strip().lower()) &
        (df["Role"].str.strip().str.lower() == role.strip().lower())
    ]
    return match.iloc[0].to_dict() if not match.empty else None


def insert_job(company: str, role: str, status: str, recruiter_email: str, 
               email_subject: str, notes: str = ""):
    """Insert new job application record."""
    df = get_or_create_dataframe()
    now = datetime.now().strftime("%Y-%m-%d")
    
    new_row = {
        "Company": company.strip(),
        "Role": role.strip(),
        "Status": status,
        "Applied_Date": now,           # New applications start today
        "Last_Update": now,
        "Recruiter_Email": recruiter_email,
        "Email_Subject": email_subject,
        "Notes": notes,
        "Days_Since_Update": 0
    }
    
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    # Ensure both sheets exist
    _ensure_all_sheets_exist()
    # Write both sheets
    _write_multiple_sheets(get_suggestions_dataframe(), df)
    return "Inserted"


def update_job_status(company: str, role: str, new_status: str, 
                      recruiter_email: str = "", email_subject: str = "", 
                      notes: str = ""):
    """Update existing job status and track update time."""
    df = get_or_create_dataframe()
    
    match = df[
        (df["Company"].str.strip().str.lower() == company.strip().lower()) &
        (df["Role"].str.strip().str.lower() == role.strip().lower())
    ]
    
    if match.empty:
        return insert_job(company, role, new_status, recruiter_email, email_subject, notes)
    
    idx = match.index[0]
    now = datetime.now().strftime("%Y-%m-%d")
    
    df.at[idx, "Status"] = new_status
    df.at[idx, "Last_Update"] = now
    
    # Update optional fields if provided
    if recruiter_email:
        df.at[idx, "Recruiter_Email"] = recruiter_email
    if email_subject:
        df.at[idx, "Email_Subject"] = email_subject
    if notes:
        df.at[idx, "Notes"] = notes
    
    # Ensure both sheets exist and write
    _ensure_all_sheets_exist()
    _write_multiple_sheets(get_suggestions_dataframe(), df)
    return "Updated"


def get_dashboard_data():
    """Fetch all records with computed days_since_update for dashboard."""
    df = get_or_create_dataframe()
    
    if df.empty:
        return {
            "total_applied": 0,
            "total_interviews": 0,
            "total_offers": 0,
            "total_rejections": 0,
            "pending": 0,
            "records": []
        }
    
    # Compute days since last update
    today = datetime.now().strftime("%Y-%m-%d")
    df["Days_Since_Update"] = df["Last_Update"].apply(
        lambda x: (datetime.now() - datetime.strptime(x, "%Y-%m-%d")).days 
        if pd.notna(x) else 0
    )
    
    # Compute aggregates
    status_counts = df["Status"].value_counts().to_dict()
    
    return {
        "total_applied": status_counts.get("Applied", 0),
        "total_interviews": status_counts.get("Interview", 0),
        "total_offers": status_counts.get("Offer", 0),
        "total_rejections": status_counts.get("Rejected", 0),
        "pending": status_counts.get("Applied", 0) + status_counts.get("Interview", 0),
        "records": df.to_dict("records")
    }


def get_records_by_status(status: str):
    """Filter records by status."""
    df = get_or_create_dataframe()
    filtered = df[df["Status"].str.lower() == status.lower()]
    return filtered.to_dict("records") if not filtered.empty else []


def search_records(keyword: str):
    """Search by company or role."""
    df = get_or_create_dataframe()
    keyword_lower = keyword.lower()
    mask = (
        df["Company"].str.lower().str.contains(keyword_lower, na=False) |
        df["Role"].str.lower().str.contains(keyword_lower, na=False)
    )
    return df[mask].to_dict("records")


# ============================================================================
# JOB SUGGESTIONS SHEET FUNCTIONS (NEW FEATURE)
# ============================================================================
# Handles recommendations/job alerts where user has NOT applied yet
# Stores separately from applied jobs for future reference

def _ensure_suggestions_sheet_exists():
    """
    Ensure job_suggestions sheet exists in Excel file.
    Creates it if missing (backward compatibility).
    """
    try:
        # Try to load existing file
        with pd.ExcelFile(EXCEL_FILE) as xls:
            if SUGGESTIONS_SHEET not in xls.sheet_names:
                # Sheet doesn't exist - create it
                df_suggestions = pd.DataFrame(columns=SUGGESTIONS_SCHEMA.keys())
                
                # Append to existing file
                with pd.ExcelWriter(EXCEL_FILE, mode="a", engine="openpyxl") as writer:
                    df_suggestions.to_excel(writer, sheet_name=SUGGESTIONS_SHEET, index=False)
    except FileNotFoundError:
        # File doesn't exist yet, will be created on first applied job
        pass


def get_suggestions_dataframe():
    """Load or create job_suggestions sheet."""
    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name=SUGGESTIONS_SHEET)
        # Ensure all columns exist
        for col in SUGGESTIONS_SCHEMA.keys():
            if col not in df.columns:
                df[col] = None
        return df
    except (FileNotFoundError, ValueError):
        # Sheet doesn't exist or file missing - create empty
        df = pd.DataFrame(columns=SUGGESTIONS_SCHEMA.keys())
        return df


def save_job_suggestion(company: str, role: str, source: str = "Email", 
                       email_subject: str = "", notes: str = ""):
    """
    Save a job recommendation/suggestion to job_suggestions sheet.
    
    Args:
        company: Company name
        role: Job role
        source: Source of recommendation (LinkedIn/Glassdoor/Email/Other)
        email_subject: Original email subject (if applicable)
        notes: Additional notes about the role
    
    Returns:
        "Inserted" if new record, "Updated" if already exists
    """
    # Ensure sheet exists
    _ensure_suggestions_sheet_exists()
    
    df = get_suggestions_dataframe()
    now = datetime.now().strftime("%Y-%m-%d")
    
    # Check if already saved
    match = df[
        (df["Company"].str.strip().str.lower() == company.strip().lower()) &
        (df["Role"].str.strip().str.lower() == role.strip().lower())
    ]
    
    if not match.empty:
        # Update existing record
        idx = match.index[0]
        df.at[idx, "Saved"] = "Yes"  # Mark as reviewed
        if notes:
            df.at[idx, "Notes"] = notes
        action = "Updated"
    else:
        # Insert new record
        new_row = {
            "Company": company.strip(),
            "Role": role.strip(),
            "Source": source,
            "Email_Date": now,
            "Saved": "No",
            "Notes": notes or email_subject
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        action = "Inserted"
    
    # Save to Excel
    _write_multiple_sheets(df, get_or_create_dataframe())
    
    return action


def mark_suggestion_saved(company: str, role: str, saved: str = "Yes"):
    """
    Mark a job suggestion as saved (Yes/No/Maybe).
    
    Args:
        company: Company name
        role: Job role
        saved: "Yes" / "No" / "Maybe"
    """
    df = get_suggestions_dataframe()
    
    match = df[
        (df["Company"].str.strip().str.lower() == company.strip().lower()) &
        (df["Role"].str.strip().str.lower() == role.strip().lower())
    ]
    
    if not match.empty:
        idx = match.index[0]
        df.at[idx, "Saved"] = saved
        _write_multiple_sheets(df, get_or_create_dataframe())
        return True
    
    return False


def get_saved_suggestions():
    """Get all saved job suggestions (Saved = 'Yes')."""
    df = get_suggestions_dataframe()
    saved = df[df["Saved"] == "Yes"]
    return saved.to_dict("records") if not saved.empty else []


def get_all_suggestions():
    """Get all job suggestions (for manual review)."""
    df = get_suggestions_dataframe()
    return df.to_dict("records") if not df.empty else []


def _write_multiple_sheets(suggestions_df, applied_df):
    """
    Helper to write both sheets to Excel file simultaneously.
    Ensures both sheets are always in sync.
    """
    try:
        with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
            # Write applied jobs to main sheet
            applied_df.to_excel(writer, sheet_name=APPLIED_SHEET, index=False)
            # Write suggestions to second sheet
            suggestions_df.to_excel(writer, sheet_name=SUGGESTIONS_SHEET, index=False)
    except Exception as e:
        print(f"Warning: Failed to write multiple sheets: {e}")


def reset_workbook():
    """Clear all data and recreate both sheets with headers only."""
    applied_df = pd.DataFrame(columns=SCHEMA.keys())
    suggestions_df = pd.DataFrame(columns=SUGGESTIONS_SCHEMA.keys())
    try:
        with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
            applied_df.to_excel(writer, sheet_name=APPLIED_SHEET, index=False)
            suggestions_df.to_excel(writer, sheet_name=SUGGESTIONS_SHEET, index=False)
        return True
    except Exception as e:
        print(f"Error resetting workbook: {e}")
        return False
