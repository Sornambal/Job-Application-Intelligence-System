"""
Job Application Intelligence System - Main Entry Point

ORCHESTRATION: Now uses LangGraph (see graph_pipeline.py)
- Old: Custom if/else logic in process_email()
- New: LangGraph state machine with conditional routing

RESPONSIBILITIES:
1. Fetch emails from Gmail
2. Pass each email to LangGraph pipeline
3. Display formatted results
"""

from gmail_reader import read_latest_emails
from dashboard_api import get_jobs_needing_attention
from whatsapp_notifier import notify_follow_up_reminder

# NEW: Import LangGraph orchestration
from graph_pipeline import process_email_with_graph

import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_agent():
    """
    Main agent pipeline: read emails → process through LangGraph → display results.
    
    REFACTORED: Now uses LangGraph orchestration instead of custom logic.
    
    OLD FLOW (main.py):
        classify_email() → extract_details() → if/else routing → 
        state validation → Excel update → WhatsApp notification
    
    NEW FLOW (graph_pipeline.py):
        LangGraph with nodes and conditional edges handling all orchestration
    """
    print("\n🚀 Starting Job Application Agent (LangGraph Orchestration)...\n")
    
    emails = read_latest_emails()
    print(f"📧 Found {len(emails)} emails to process\n")

    processed_count = 0
    suggestions_count = 0
    
    for i, email in enumerate(emails, 1):
        # NEW: Process through LangGraph pipeline
        result = process_email_with_graph(email)
        
        # Format output (unchanged)
        status_icon = "✓" if result["success"] else "✗"
        action = result.get("action", "Unknown")
        
        if result["success"]:
            if "Suggestion" in action:
                # Job recommendation saved
                print(f"{status_icon} [{i}] {action}: {result['company']} → {result['role']}")
                print(f"    💡 Saved to suggestions sheet")
                suggestions_count += 1
            else:
                # Applied job updated
                print(f"{status_icon} [{i}] {action}: {result['company']} → {result['role']}")
                if result.get("current_status"):
                    print(f"    Status: {result.get('current_status')} → {result.get('new_status')}")
                processed_count += 1
        else:
            if result.get("reason"):
                print(f"{status_icon} [{i}] {action}: {result.get('reason')}")
            else:
                print(f"{status_icon} [{i}] {action}")
        
        print()

    # Show summary
    print("\n" + "="*60)
    print(f"✓ Applied jobs processed: {processed_count}")
    print(f"💡 Suggestions saved: {suggestions_count}")
    print(f"✗ Skipped/Blocked: {len(emails) - processed_count - suggestions_count}")
    
    # Show jobs needing attention
    attention_jobs = get_jobs_needing_attention()
    if attention_jobs:
        print(f"\n⚠️  Jobs needing attention: {len(attention_jobs)}")
        
        reminder_count = 0
        for job in attention_jobs[:5]:
            print(f"   • {job['company']} - {job['role']} ({job['priority']}): {job['reason']}")
            
            if job["priority"] == "high":
                logger.info(f"📱 Sending follow-up reminder for {job['company']}...")
                if notify_follow_up_reminder(job['company'], job['role'], job.get('days_since_update', 0)):
                    reminder_count += 1
        
        if reminder_count > 0:
            print(f"\n   📱 Sent {reminder_count} follow-up reminder notifications")
    
    print("="*60 + "\n")


if __name__ == "__main__":
    run_agent()
