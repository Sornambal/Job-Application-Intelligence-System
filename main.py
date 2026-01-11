from gmail_reader import read_latest_emails
from classifier_agent import classify_email
from extractor_agent import extract_details
from decision_agent import decide_and_update
from excel_manager import EXCEL_FILE
import json
import re

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
        match = re.search(r"\{.*\}", text, re.S)
        if match:
            return json.loads(match.group(0))
        raise


def _truncate_text(text: str, max_chars: int = 6000) -> str:
    """Truncate text to stay within token limits (~4 chars per token)."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n[... truncated for length]"


def run_agent():
    emails = read_latest_emails()

    for email in emails:
        combined_text = email["subject"] + "\n" + email["body"]
        combined_text = _truncate_text(combined_text)

        status = classify_email(combined_text)

        # Skip irrelevant and job recommendation emails
        if status in ["Irrelevant", "Job_Recommendation"]:
            print(f"Skipped: {status} - {email['subject'][:50]}")
            continue

        # Hard rule: Must contain proof of application
        if status == "Applied_Confirmation" and not is_applied_email(combined_text):
            print(f"Skipped: No application proof - {email['subject'][:50]}")
            continue

        extracted_json = extract_details(combined_text, status)
        data = _safe_load_json(extracted_json)

        action = decide_and_update(data, EXCEL_FILE)

        print(f"{action}: {data['company']} | {data['role']} | {data['status']}")

if __name__ == "__main__":
    run_agent()
