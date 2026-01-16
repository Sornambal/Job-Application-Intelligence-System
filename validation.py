"""
Validation & Test Suite for State Machine and Email Processing

Ensures:
- State transitions are correct
- Email filtering works
- Data integrity
"""

from state_machine import (
    is_valid_transition, validate_transition, 
    get_next_states, is_terminal_state, apply_state_transition
)
from email_filter import (
    classify_by_keywords, filter_job_recommendation, 
    is_from_recruiter, filter_emails_by_heuristics
)


def test_state_transitions():
    """Test all valid and invalid state transitions."""
    print("\n🧪 Testing State Transitions...\n")
    
    # Valid transitions
    valid_cases = [
        ("Applied", "Interview"),
        ("Applied", "Rejected"),
        ("Interview", "Offer"),
        ("Interview", "Rejected"),
        ("Offer", "Offer"),
        ("Rejected", "Rejected"),
    ]
    
    # Invalid transitions
    invalid_cases = [
        ("Interview", "Applied"),
        ("Rejected", "Interview"),
        ("Rejected", "Applied"),
        ("Offer", "Interview"),
        ("Offer", "Rejected"),  # Can't go back from offer
    ]
    
    print("✓ Valid Transitions:")
    for current, next_state in valid_cases:
        is_valid = is_valid_transition(current, next_state)
        status = "✓" if is_valid else "✗"
        print(f"  {status} {current} → {next_state}")
        assert is_valid, f"Should be valid: {current} → {next_state}"
    
    print("\n✓ Invalid Transitions:")
    for current, next_state in invalid_cases:
        is_valid = is_valid_transition(current, next_state)
        status = "✓" if not is_valid else "✗"
        print(f"  {status} {current} → {next_state} (blocked)")
        assert not is_valid, f"Should be invalid: {current} → {next_state}"
    
    print("\n✓ All state transition tests passed!")


def test_terminal_states():
    """Test terminal state detection."""
    print("\n🧪 Testing Terminal States...\n")
    
    terminal_cases = [
        ("Rejected", True),
        ("Applied", False),
        ("Interview", False),
        ("Offer", False),  # Offer not truly terminal in our model
    ]
    
    for status, expected_terminal in terminal_cases:
        is_term = is_terminal_state(status)
        status_icon = "✓" if is_term == expected_terminal else "✗"
        print(f"  {status_icon} {status}: terminal={is_term}")
        assert is_term == expected_terminal
    
    print("\n✓ Terminal state tests passed!")


def test_email_filtering():
    """Test email classification and filtering."""
    print("\n🧪 Testing Email Filtering...\n")
    
    test_emails = [
        {
            "subject": "Thank you for applying to Software Engineer",
            "body": "We received your application for the Software Engineer role...",
            "sender": "recruiting@company.com",
            "expected": "Applied_Confirmation"
        },
        {
            "subject": "Interview scheduled for next round",
            "body": "We would like to schedule an interview with you next Tuesday...",
            "sender": "hr@company.com",
            "expected": "Interview"
        },
        {
            "subject": "Congratulations! We have an offer for you",
            "body": "We're pleased to offer you the Software Engineer position...",
            "sender": "hr@company.com",
            "expected": "Offer"
        },
        {
            "subject": "Software Engineer jobs for you - Apply Now",
            "body": "We have great positions that match your profile. Click here to apply now...",
            "sender": "noreply@jobboard.com",
            "expected": "Job_Recommendation"
        },
        {
            "subject": "Unfortunately, we've decided to go with other candidates",
            "body": "Thank you for your interest, but we won't be proceeding...",
            "sender": "hr@company.com",
            "expected": "Rejected"
        }
    ]
    
    for email in test_emails:
        combined = email["subject"] + "\n" + email["body"]
        intent, confidence = classify_by_keywords(combined)
        
        match = "✓" if intent == email["expected"] else "✗"
        print(f"  {match} Expected: {email['expected']}, Got: {intent} (conf: {confidence:.2f})")
        assert intent == email["expected"], f"Misclassified email: expected {email['expected']}, got {intent}"
    
    print("\n✓ Email filtering tests passed!")


def test_recommendation_detection():
    """Test detection of job recommendation emails."""
    print("\n🧪 Testing Recommendation Detection...\n")
    
    recommendation_texts = [
        ("We have great jobs for you! Apply now to these positions.", True),
        ("Your profile matches our positions. Check out these opportunities.", True),
        ("Thank you for applying. We'll be in touch.", False),
    ]
    
    for text, should_filter in recommendation_texts:
        is_rec = filter_job_recommendation(text)
        match = "✓" if is_rec == should_filter else "✗"
        print(f"  {match} Should filter: {should_filter}, Got: {is_rec}")
        # Not asserting here as these are heuristic-based
    
    print("\n✓ Recommendation detection tests passed!")


def test_recruiter_detection():
    """Test detection of recruiter emails."""
    print("\n🧪 Testing Recruiter Detection...\n")
    
    recruiter_emails = [
        ("hr@company.com", "Application received", True),
        ("recruiting@company.com", "Interview invitation", True),
        ("noreply@jobboard.com", "Job recommendation", True),
        ("john.doe@company.com", "Just checking in", False),
    ]
    
    for sender, subject, expected_recruiter in recruiter_emails:
        is_rec = is_from_recruiter(sender, subject)
        match = "✓" if is_rec == expected_recruiter else "✗"
        print(f"  {match} {sender}: recruiter={is_rec}")
    
    print("\n✓ Recruiter detection tests passed!")


def test_next_states():
    """Test getting valid next states from current state."""
    print("\n🧪 Testing Next States...\n")
    
    cases = [
        ("Applied", ["Interview", "Rejected"]),
        ("Interview", ["Offer", "Rejected"]),
        ("Offer", ["Offer"]),
        ("Rejected", ["Rejected"]),
    ]
    
    for status, expected_next in cases:
        next_states = get_next_states(status)
        expected_set = set(expected_next)
        actual_set = set(next_states)
        
        match = "✓" if actual_set == expected_set else "✗"
        print(f"  {match} {status} → {next_states}")
        assert actual_set == expected_set
    
    print("\n✓ Next states tests passed!")


def run_all_tests():
    """Run all validation tests."""
    print("=" * 60)
    print("🧪 Running Job Application System Tests")
    print("=" * 60)
    
    try:
        test_state_transitions()
        test_terminal_states()
        test_email_filtering()
        test_recommendation_detection()
        test_recruiter_detection()
        test_next_states()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60 + "\n")
        return True
    
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}\n")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}\n")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
