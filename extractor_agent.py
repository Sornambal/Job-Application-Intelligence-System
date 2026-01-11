from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def extract_details(email_text, status):
    # Map classifier output to Excel-friendly status
    status_map = {
        "Applied_Confirmation": "Applied",
        "Interview": "Interview",
        "Rejected": "Rejected",
        "Offer": "Offer"
    }
    excel_status = status_map.get(status, status)
    
    prompt = f"""
Extract job application details from the email.

Return valid JSON with keys:
company, role, status

Status is already detected as: {excel_status}

Email:
\"\"\"{email_text}\"\"\"
\nRespond with ONLY the JSON object, no code fences, no prose.
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content.strip()
