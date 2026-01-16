#!/usr/bin/env python3
"""Clear applications.xlsx and recreate both sheets.
Usage: python clear_excel.py
"""

from excel_manager import reset_workbook

if __name__ == "__main__":
    ok = reset_workbook()
    if ok:
        print("✅ Cleared applications.xlsx and recreated sheets: 'applied_jobs' & 'job_suggestions'")
        print("You can now run the email ingestion to rebuild from Gmail.")
    else:
        print("❌ Failed to reset workbook. Ensure Excel is closed and try again.")
