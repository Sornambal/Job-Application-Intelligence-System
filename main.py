from gmail_reader import read_latest_emails
from classifier_agent import classify_email
from extractor_agent import extract_details
from excel_manager import get_job_record, insert_job, update_job_status, save_job_suggestion
from state_machine import apply_state_transition, JobStatus
from dashboard_api import get_jobs_needing_attention
from whatsapp_notifier import notify_interview_scheduled, notify_offer_received, notify_follow_up_reminder
import json
import re
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

APPLIED_KEYWORDS = [
    "thank you for applying",
    "we received your application",
    "application submitted",
    "your application for",
    "has been received",
    "application received",
    "confirming your application"
]


def is_applied_email(text: str) -> bool:
    """Check if email contains proof of application submission."""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in APPLIED_KEYWORDS)


def _safe_load_json(text: str) -> dict:
    """Parse JSON from the model; try to salvage the first JSON object if wrapped."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract and parse just the first JSON object
        try:
            matches = re.finditer(r"\{[^{}]*\}", text)
            for match in matches:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    continue
        except Exception:
            pass
        # If all else fails, return empty dict
        logger.warning(f"Could not parse JSON from LLM response: {text[:100]}")
        return {}


def _truncate_text(text: str, max_chars: int = 6000) -> str:
    """Truncate text to stay within token limits (~4 chars per token)."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n[... truncated for length]"


def normalize_status(classifier_status: str) -> str:
    """Convert classifier status to state machine status."""
    status_map = {
        "Applied_Confirmation": "Applied",
        "Interview": "Interview",
        "Rejected": "Rejected",
        "Offer": "Offer"
    }
    return status_map.get(classifier_status, classifier_status)


def process_email(email: dict) -> dict:
    """
    Process a single email through the full pipeline with state validation.
    
    HANDLES TWO FLOWS:
    1. Applied jobs → State machine validation → Excel (main sheet)
    2. Job recommendations → Save to suggestions sheet
    
    Returns:
        Dict with keys: success, action, company, role, status, reason, classifier_result
    """
    combined_text = email["subject"] + "\n" + email["body"]
    combined_text = _truncate_text(combined_text)

    # Step 1: Classify email
    classifier_result = classify_email(combined_text)

    # FEATURE 2: Handle Job Recommendations
    # ===========================================
    # Route job recommendations to suggestions sheet instead of applied jobs
    if classifier_result == "Job_Recommendation":
        try:
            # Extract details even for recommendations
            extracted_json = extract_details(combined_text, classifier_result)
            data = _safe_load_json(extracted_json)
            
            if data is None:
                data = {}
            
            company = (data.get("company") or "Unknown").strip()
            role = (data.get("role") or "Unknown").strip()
            
            # Save to job_suggestions sheet
            action = save_job_suggestion(
                company=company,
                role=role,
                source="Email",
                email_subject=email.get("subject", ""),
                notes=f"From: {email.get('sender', '')}"
            )
            
            logger.info(f"💡 Suggestion: {company} - {role}")
            
            return {
                "success": True,
                "action": f"Suggestion {action}",
                "company": company,
                "role": role,
                "reason": "Saved to job_suggestions sheet",
                "classifier_result": classifier_result
            }
        except Exception as e:
            logger.error(f"Error processing job recommendation: {e}")
            return {
                "success": False,
                "action": "Error",
                "reason": str(e),
                "classifier_result": classifier_result
            }

    # Skip irrelevant emails
    if classifier_result == "Irrelevant":
        return {
            "success": False,
            "action": "Skipped",
            "reason": f"Email type: {classifier_result}",
            "classifier_result": classifier_result
        }

    # Step 2: Hard rule check - Applied emails must have proof
    if classifier_result == "Applied_Confirmation" and not is_applied_email(combined_text):
        return {
            "success": False,
            "action": "Skipped",
            "reason": "No application proof found",
            "classifier_result": classifier_result
        }

    # Step 3: Extract details
    try:
        extracted_json = extract_details(combined_text, classifier_result)
        data = _safe_load_json(extracted_json)
    except Exception as e:
        logger.warning(f"Failed to extract details: {e}")
        return {
            "success": False,
            "action": "Skipped",
            "reason": f"Extraction failed: {str(e)[:50]}",
            "classifier_result": classifier_result
        }
    
    if data is None:
        data = {}
    
    company = (data.get("company") or "Unknown").strip()
    role = (data.get("role") or "Unknown").strip()
    new_status = normalize_status(classifier_result)

    # Step 4: Validate state transition
    existing_record = get_job_record(company, role)
    
    if existing_record:
        current_status = existing_record.get("Status", "Applied")
        
        # Check if transition is valid
        final_status, transition_reason = apply_state_transition(current_status, new_status, classifier_result)
        
        if final_status is None:
            # Invalid transition - block update
            return {
                "success": False,
                "action": "Blocked",
                "reason": transition_reason,
                "company": company,
                "role": role,
                "current_status": current_status,
                "proposed_status": new_status
            }
        
        # Valid transition - update
        update_job_status(
            company=company,
            role=role,
            new_status=final_status,
            recruiter_email=email.get("sender", ""),
            email_subject=email.get("subject", ""),
            notes=transition_reason
        )
        
        # FEATURE 1: Send WhatsApp Notification
        # =====================================
        # Trigger notifications for important state changes
        if final_status == "Interview":
            logger.info("📱 Sending interview notification...")
            notify_interview_scheduled(company, role)
        elif final_status == "Offer":
            logger.info("📱 Sending offer notification...")
            notify_offer_received(company, role)
        
        return {
            "success": True,
            "action": "Updated",
            "company": company,
            "role": role,
            "current_status": current_status,
            "new_status": final_status,
            "reason": transition_reason,
            "classifier_result": classifier_result
        }
    else:
        # New application
        insert_job(
            company=company,
            role=role,
            status=new_status,
            recruiter_email=email.get("sender", ""),
            email_subject=email.get("subject", ""),
            notes=f"Initial application detected via: {classifier_result}"
        )
        
        return {
            "success": True,
            "action": "Inserted",
            "company": company,
            "role": role,
            "new_status": new_status,
            "reason": "New application record created",
            "classifier_result": classifier_result
        }


def run_agent():
    """Main agent pipeline: read emails → classify → validate → update → notify."""
    print("\n🚀 Starting Job Application Agent...\n")
    
    emails = read_latest_emails()
    print(f"📧 Found {len(emails)} emails to process\n")

    processed_count = 0
    suggestions_count = 0
    
    for i, email in enumerate(emails, 1):
        result = process_email(email)
        
        # Format output
        status_icon = "✓" if result["success"] else "✗"
        action = result.get("action", "Unknown")
        classifier = result.get("classifier_result", "")
        
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
    
    # Show jobs needing attention (with follow-up reminder notifications)
    attention_jobs = get_jobs_needing_attention()
    if attention_jobs:
        print(f"\n⚠️  Jobs needing attention: {len(attention_jobs)}")
        
        # Send follow-up reminder notifications
        reminder_count = 0
        for job in attention_jobs[:5]:
            print(f"   • {job['company']} - {job['role']} ({job['priority']}): {job['reason']}")
            
            # Send WhatsApp follow-up reminder
            if job["priority"] == "high":
                logger.info(f"📱 Sending follow-up reminder for {job['company']}...")
                if notify_follow_up_reminder(job['company'], job['role'], job.get('days_since_update', 0)):
                    reminder_count += 1
        
        if reminder_count > 0:
            print(f"\n   📱 Sent {reminder_count} follow-up reminder notifications")
    
    print("="*60 + "\n")


if __name__ == "__main__":
    run_agent()
