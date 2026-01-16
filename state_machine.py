"""
State Machine for Job Application Workflow

Valid states:
- Applied: User has submitted application
- Interview: Interview scheduled/ongoing
- Offer: Job offer received
- Rejected: Application rejected

Valid transitions:
- Applied → Interview (email from recruiter about interview)
- Applied → Rejected (rejection email)
- Interview → Offer (offer extended)
- Interview → Rejected (rejected after interview)

Invalid transitions are blocked and logged.
"""

from typing import Tuple, Optional
from enum import Enum

class JobStatus(Enum):
    """Job application status enumeration."""
    APPLIED = "Applied"
    INTERVIEW = "Interview"
    OFFER = "Offer"
    REJECTED = "Rejected"


# Define valid state transitions
VALID_TRANSITIONS = {
    JobStatus.APPLIED: [JobStatus.INTERVIEW, JobStatus.REJECTED],
    JobStatus.INTERVIEW: [JobStatus.OFFER, JobStatus.REJECTED],
    JobStatus.OFFER: [JobStatus.OFFER],  # Offer → Offer allowed (for clarifications)
    JobStatus.REJECTED: [JobStatus.REJECTED],  # Terminal state
}


def is_valid_transition(current_status: str, new_status: str) -> bool:
    """
    Check if transition from current_status to new_status is allowed.
    
    Args:
        current_status: Current status as string (e.g., "Applied")
        new_status: Proposed new status as string (e.g., "Interview")
    
    Returns:
        True if transition is valid, False otherwise.
    """
    try:
        current = JobStatus(current_status)
        new = JobStatus(new_status)
        return new in VALID_TRANSITIONS.get(current, [])
    except ValueError:
        # Invalid status value
        return False


def validate_transition(current_status: str, new_status: str) -> Tuple[bool, str]:
    """
    Validate transition and return explanation.
    
    Args:
        current_status: Current status as string
        new_status: Proposed new status as string
    
    Returns:
        Tuple of (is_valid: bool, message: str)
    """
    if not is_valid_transition(current_status, new_status):
        return False, f"Invalid transition: {current_status} → {new_status}"
    return True, f"Valid transition: {current_status} → {new_status}"


def get_next_states(current_status: str) -> list:
    """
    Get all valid next states from current status.
    
    Args:
        current_status: Current status as string
    
    Returns:
        List of valid next statuses.
    """
    try:
        current = JobStatus(current_status)
        return [s.value for s in VALID_TRANSITIONS.get(current, [])]
    except ValueError:
        return []


def is_terminal_state(status: str) -> bool:
    """Check if status is terminal (no valid transitions)."""
    next_states = get_next_states(status)
    # Terminal if only self-transitions allowed
    return len(next_states) == 0 or (len(next_states) == 1 and status in next_states)


def apply_state_transition(current_status: str, new_status: str, 
                          email_classifier_result: Optional[str] = None) -> Tuple[Optional[str], str]:
    """
    Attempt to apply a state transition.
    
    Args:
        current_status: Current job status
        new_status: Proposed new status
        email_classifier_result: Original classifier result for context
    
    Returns:
        Tuple of (final_status: Optional[str], reason: str)
        - final_status: The applied status or None if transition blocked
        - reason: Explanation message
    """
    valid, message = validate_transition(current_status, new_status)
    
    if valid:
        return new_status, f"✓ {message}"
    else:
        # Transition blocked - keep current status
        return None, f"✗ {message} [keeping {current_status}]"


# State machine for logic
def get_state_info(status: str) -> dict:
    """Get detailed info about a state."""
    try:
        job_status = JobStatus(status)
    except ValueError:
        return {"error": f"Unknown status: {status}"}
    
    return {
        "current": status,
        "valid_next_states": get_next_states(status),
        "is_terminal": is_terminal_state(status),
        "description": {
            "Applied": "Application submitted, awaiting response",
            "Interview": "Interview scheduled or in progress",
            "Offer": "Job offer received",
            "Rejected": "Application or interview rejected"
        }.get(status, "Unknown")
    }
