"""
Follow-up Agent: Context-aware email suggestions using Groq

Rules:
- CASE 1: Applied > 10 days, no response → Polite follow-up
- CASE 2: Interview > 7 days, no update → Ask about outcome
- CASE 3: Offer received → Generate acceptance/clarification
- CASE 4: Rejection → Optional thank you email

NOTE: This agent ONLY GENERATES suggestions. Never auto-sends emails.
"""

from groq import Groq
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def generate_followup_email(company: str, role: str, status: str, 
                           recruiter_email: str, days_since_update: int,
                           user_name: str = "John") -> dict:
    """
    Generate a follow-up email suggestion based on job status and time elapsed.
    
    Args:
        company: Company name
        role: Job role
        status: Current application status (Applied, Interview, Offer, Rejected)
        recruiter_email: Recruiter's email address
        days_since_update: Days since last status update
        user_name: User's name for personalization
    
    Returns:
        Dict with keys:
        - should_followup: bool (whether a follow-up is recommended)
        - subject: str
        - body: str
        - reasoning: str
        - suggested_recipient: str
    """
    
    # Determine if follow-up is needed
    should_followup = False
    reasoning = ""
    
    if status == "Applied" and days_since_update > 10:
        should_followup = True
        reasoning = f"No response for {days_since_update} days after applying"
    elif status == "Interview" and days_since_update > 7:
        should_followup = True
        reasoning = f"No update {days_since_update} days after interview"
    elif status == "Offer":
        should_followup = True
        reasoning = "Offer received - clarification or acceptance needed"
    
    if not should_followup:
        return {
            "should_followup": False,
            "subject": "",
            "body": "",
            "reasoning": f"No follow-up needed ({status}, {days_since_update} days)",
            "suggested_recipient": recruiter_email
        }
    
    # Use Groq to generate professional follow-up email
    if status == "Applied":
        prompt = f"""
You are a professional career coach. Generate a polite follow-up email for a job application.

Context:
- Applicant: {user_name}
- Company: {company}
- Role: {role}
- Days since applying: {days_since_update}
- No response received yet

Write a PROFESSIONAL, BRIEF follow-up email (subject + body).
Keep tone friendly but professional.
Do NOT sound desperate.

Format your response EXACTLY as:
SUBJECT: <subject line>
BODY: <email body>
"""
    elif status == "Interview":
        prompt = f"""
You are a professional career coach. Generate a follow-up email after an interview.

Context:
- Applicant: {user_name}
- Company: {company}
- Role: {role}
- Days since interview: {days_since_update}
- No status update received

Write a PROFESSIONAL follow-up email politely asking about the interview outcome.
Keep it brief and courteous.

Format your response EXACTLY as:
SUBJECT: <subject line>
BODY: <email body>
"""
    elif status == "Offer":
        prompt = f"""
You are a professional career coach. Generate an email for an offer decision.

Context:
- Applicant: {user_name}
- Company: {company}
- Role: {role}
- Status: Offer received

Generate TWO options:
1. An acceptance email
2. A clarification email (for asking questions about salary, start date, etc)

Format your response EXACTLY as:
SUBJECT (ACCEPTANCE): <subject line>
BODY (ACCEPTANCE): <email body>

SUBJECT (CLARIFICATION): <subject line>
BODY (CLARIFICATION): <email body>
"""
    
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}]
    )
    
    email_text = response.choices[0].message.content.strip()
    
    # Parse response
    lines = email_text.split("\n")
    subject = ""
    body = ""
    
    for i, line in enumerate(lines):
        if line.startswith("SUBJECT:"):
            subject = line.replace("SUBJECT:", "").strip()
            # Body starts from next line until we hit another section
            body_lines = []
            for j in range(i + 1, len(lines)):
                if lines[j].startswith("SUBJECT") or lines[j].startswith("BODY ("):
                    break
                body_lines.append(lines[j])
            body = "\n".join(body_lines).strip()
            break
    
    # If parsing failed, use raw response
    if not subject:
        subject = f"Follow-up: {role} at {company}"
        body = email_text
    
    return {
        "should_followup": True,
        "subject": subject,
        "body": body,
        "reasoning": reasoning,
        "suggested_recipient": recruiter_email
    }


def batch_generate_followups(jobs_data: list, user_name: str = "John") -> list:
    """
    Generate follow-up suggestions for multiple jobs.
    
    Args:
        jobs_data: List of job records (dicts with company, role, status, etc)
        user_name: User's name for personalization
    
    Returns:
        List of follow-up suggestions
    """
    followups = []
    
    for job in jobs_data:
        # Skip if missing required fields
        if not all(k in job for k in ["Company", "Role", "Status", "Recruiter_Email", "Days_Since_Update"]):
            continue
        
        followup = generate_followup_email(
            company=job["Company"],
            role=job["Role"],
            status=job["Status"],
            recruiter_email=job["Recruiter_Email"],
            days_since_update=int(job.get("Days_Since_Update", 0)),
            user_name=user_name
        )
        
        if followup["should_followup"]:
            followups.append({
                **followup,
                "company": job["Company"],
                "role": job["Role"]
            })
    
    return followups
