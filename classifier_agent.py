from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def classify_email(email_text):
    prompt = f"""
You are an AI agent that classifies recruiter emails.

Possible categories:
- Applied_Confirmation (user already applied, confirmation received)
- Interview
- Rejected
- Offer
- Job_Recommendation (inviting user to apply, NOT applied yet - signals: "great fit", "jobs for you", "recommended", "apply now")
- Irrelevant

Email:
\"\"\"{email_text}\"\"\"

Respond ONLY with one word.
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content.strip()
