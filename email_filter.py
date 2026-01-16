"""
Email Filter: Advanced filtering for job application emails

Multi-layer filtering:
1. Gmail API query optimization
2. Keyword pattern matching
3. Heuristic scoring
"""

from typing import List, Dict, Tuple


# Keywords for each intent
INTENT_KEYWORDS = {
    "Applied_Confirmation": [
        "thank you for applying",
        "we received your application",
        "application submitted",
        "your application for",
        "has been received",
        "application received",
        "confirming your application",
        "thanks for your interest",
        "we have received"
    ],
    "Interview": [
        "interview",
        "schedule",
        "let's chat",
        "next round",
        "meeting invitation",
        "round 2",
        "technical interview",
        "phone call",
        "video interview",
        "would like to discuss"
    ],
    "Offer": [
        "congratulations",
        "we're pleased",
        "we'd like to offer",
        "job offer",
        "pleased to offer",
        "excited to offer",
        "offer letter",
        "salary expectation",
        "offer package"
    ],
    "Rejected": [
        "rejected",
        "unfortunately",
        "we've decided",
        "not move forward",
        "not the right fit",
        "other candidates",
        "closed this position",
        "no longer under consideration",
        "we won't be proceeding"
    ],
    "Job_Recommendation": [
        "great fit for you",
        "positions for you",
        "jobs for you",
        "recommended for you",
        "apply now",
        "we have a job",
        "we think you'd be great",
        "we found a role",
        "thought of your profile",
        "candidate match"
    ]
}

# Negative indicators (suggests job recommendation, not real application)
REJECTION_KEYWORDS = [
    "apply now",
    "click here",
    "view job",
    "save this job",
    "apply to this position",
    "see more jobs",
    "weekly digest",
    "job alert",
    "job recommendation"
]


def keyword_score(text: str, keywords: List[str]) -> float:
    """
    Score text based on keyword matches (0-1).
    
    Args:
        text: Email text to score
        keywords: List of keywords to match
    
    Returns:
        Score between 0 and 1
    """
    text_lower = text.lower()
    matches = sum(1 for keyword in keywords if keyword.lower() in text_lower)
    score = min(1.0, matches / max(1, len(keywords)))
    return score


def get_intent_scores(text: str) -> Dict[str, float]:
    """
    Score email against all intents.
    
    Returns dict mapping intent → score (0-1)
    """
    scores = {}
    for intent, keywords in INTENT_KEYWORDS.items():
        scores[intent] = keyword_score(text, keywords)
    return scores


def has_rejection_signals(text: str) -> bool:
    """Check if email has signals of job recommendation vs real update."""
    text_lower = text.lower()
    rejection_count = sum(1 for keyword in REJECTION_KEYWORDS if keyword.lower() in text_lower)
    return rejection_count >= 2


def filter_job_recommendation(text: str) -> bool:
    """
    Detect and filter job recommendation emails.
    
    Returns True if likely a recommendation (should skip), False if real update.
    """
    # Job recommendation score should be high
    scores = get_intent_scores(text)
    rec_score = scores.get("Job_Recommendation", 0)
    
    # If recommendation score is high AND has rejection signals, likely spam
    if rec_score > 0.5 and has_rejection_signals(text):
        return True
    
    # Check subject/body for "apply now" patterns
    if has_rejection_signals(text):
        return True
    
    return False


def classify_by_keywords(text: str) -> Tuple[str, float]:
    """
    Classify email by keyword matching alone.
    
    Returns:
        Tuple of (intent: str, confidence: float)
    """
    scores = get_intent_scores(text)
    
    # Filter out job recommendations first
    if filter_job_recommendation(text):
        return "Job_Recommendation", scores.get("Job_Recommendation", 0)
    
    # Find highest scoring intent
    best_intent = max(scores, key=scores.get)
    best_score = scores[best_intent]
    
    # If all scores are low, classify as Irrelevant
    if best_score < 0.15:
        return "Irrelevant", best_score
    
    return best_intent, best_score


def is_from_recruiter(sender_email: str, subject: str) -> bool:
    """
    Heuristic to detect if email is from recruiter.
    
    Checks:
    - Domain (hr@, recruit@, hiring@, etc)
    - Subject keywords
    """
    sender_lower = sender_email.lower()
    subject_lower = subject.lower()
    
    # Recruiter email patterns
    recruiter_domains = [
        "hr@", "recruit@", "hiring@", "careers@",
        "talent@", "jobs@", "noreply@"
    ]
    
    if any(domain in sender_lower for domain in recruiter_domains):
        return True
    
    # Subject indicators
    recruiter_subjects = [
        "application",
        "interview",
        "job",
        "position",
        "offer",
        "rejected"
    ]
    
    if any(subject in subject_lower for subject in recruiter_subjects):
        return True
    
    return False


def build_gmail_query(exclude_keywords: List[str] = None) -> str:
    """
    Build optimized Gmail API query for job application emails.
    
    Args:
        exclude_keywords: Keywords to exclude from search
    
    Returns:
        Gmail query string
    """
    # Core search terms
    query_terms = [
        "subject:(application OR applied OR interview OR shortlisted)",
        'subject:("thank you for applying")',
        "subject:(offer OR rejection OR rejected)",
        "subject:(\"next round\" OR \"job offer\")"
    ]
    
    # Combine with OR
    base_query = " OR ".join(query_terms)
    
    # Exclusions
    if exclude_keywords:
        exclude_string = " ".join([f"-subject:{keyword}" for keyword in exclude_keywords])
        base_query = f"({base_query}) {exclude_string}"
    else:
        # Default exclusions
        default_excludes = [
            "-subject:(\"job alert\")",
            "-subject:(\"weekly digest\")",
            "-subject:(\"apply now\")",
            "-subject:(\"view job\")"
        ]
        base_query = f"({base_query}) {' '.join(default_excludes)}"
    
    return base_query


def filter_emails_by_heuristics(emails: List[Dict]) -> Dict:
    """
    Apply multi-layer filtering to emails.
    
    Returns dict with:
    - valid: Emails likely to be real updates
    - recommendations: Job recommendation emails
    - irrelevant: Clearly not job-related
    """
    valid = []
    recommendations = []
    irrelevant = []
    
    for email in emails:
        combined = (email.get("subject", "") + "\n" + email.get("body", "")).lower()
        
        # Layer 1: Check if from recruiter
        if not is_from_recruiter(email.get("sender", ""), email.get("subject", "")):
            irrelevant.append(email)
            continue
        
        # Layer 2: Classify by keywords
        intent, confidence = classify_by_keywords(combined)
        
        if intent == "Job_Recommendation":
            email["_filtered_intent"] = intent
            email["_confidence"] = confidence
            recommendations.append(email)
        elif intent == "Irrelevant":
            irrelevant.append(email)
        else:
            email["_filtered_intent"] = intent
            email["_confidence"] = confidence
            valid.append(email)
    
    return {
        "valid": valid,
        "recommendations": recommendations,
        "irrelevant": irrelevant
    }
