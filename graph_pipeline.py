"""
LangGraph-based Orchestration for Job Application Intelligence System

ARCHITECTURE:
- Replaces custom if/else orchestration with graph-based workflow
- Each processing step becomes a LangGraph node
- Conditional routing replaces branching logic
- Shared state object flows through pipeline
- All existing agent logic remains unchanged

GRAPH STRUCTURE:
    classify → extract → route_decision
                           ├─→ job_suggestions_node → END
                           └─→ validate_transition → applied_jobs_node → check_notification
                                                                            ├─→ notification_node → END
                                                                            └─→ END
"""

from typing import TypedDict, Literal, Optional
from langgraph.graph import StateGraph, END
from datetime import datetime
import logging

# Import existing agents and modules (NO CHANGES TO THESE)
from classifier_agent import classify_email
from extractor_agent import extract_details
from state_machine import apply_state_transition, JobStatus
from excel_manager import (
    get_job_record, 
    insert_job, 
    update_job_status, 
    save_job_suggestion
)
from whatsapp_notifier import (
    notify_interview_scheduled, 
    notify_offer_received
)

logger = logging.getLogger(__name__)


# ============================================================================
# STATE DEFINITION
# ============================================================================

class EmailProcessingState(TypedDict):
    """
    Shared state that flows through the LangGraph pipeline.
    
    Each node reads from and writes to this state object.
    LangGraph automatically manages state updates and routing.
    """
    # Input
    email_subject: str
    email_body: str
    email_sender: str
    combined_text: str
    
    # Classification
    intent: Optional[str]  # Applied_Confirmation | Interview | Offer | Rejected | Job_Recommendation | Irrelevant
    
    # Extraction
    company: Optional[str]
    role: Optional[str]
    
    # State Machine
    current_status: Optional[str]
    new_status: Optional[str]
    transition_valid: bool
    transition_reason: Optional[str]
    
    # Control Flow
    should_notify: bool
    action_taken: Optional[str]  # Inserted | Updated | Saved_Suggestion | Skipped | Blocked
    
    # Result
    success: bool
    error_message: Optional[str]


# ============================================================================
# NODE 1: EMAIL INTENT CLASSIFICATION
# ============================================================================

def classify_node(state: EmailProcessingState) -> EmailProcessingState:
    """
    LangGraph Node: Classify email intent using Groq LLM.
    
    Maps to: classify_email() from classifier_agent.py
    
    Returns state with 'intent' field populated.
    """
    try:
        combined_text = state["combined_text"]
        intent = classify_email(combined_text)
        
        state["intent"] = intent
        logger.info(f"📋 Classified as: {intent}")
        
    except Exception as e:
        logger.error(f"Classification failed: {e}")
        state["intent"] = "Irrelevant"
        state["error_message"] = f"Classification error: {str(e)}"
    
    return state


# ============================================================================
# NODE 2: INFORMATION EXTRACTION
# ============================================================================

def extract_node(state: EmailProcessingState) -> EmailProcessingState:
    """
    LangGraph Node: Extract company and role using Groq LLM.
    
    Maps to: extract_details() from extractor_agent.py
    
    Handles JSON parsing with multiple fallback strategies.
    """
    import json
    import re
    
    try:
        combined_text = state["combined_text"]
        intent = state["intent"]
        
        # Call existing extractor
        extracted_json = extract_details(combined_text, intent)
        
        # Safe JSON parsing (same logic as before)
        try:
            data = json.loads(extracted_json)
        except json.JSONDecodeError:
            # Try to extract first JSON object
            try:
                matches = re.finditer(r"\{[^{}]*\}", extracted_json)
                for match in matches:
                    try:
                        data = json.loads(match.group(0))
                        break
                    except json.JSONDecodeError:
                        continue
                else:
                    data = {}
            except Exception:
                data = {}
        
        if data is None:
            data = {}
        
        # Extract with null safety
        state["company"] = (data.get("company") or "Unknown").strip()
        state["role"] = (data.get("role") or "Unknown").strip()
        
        logger.info(f"📦 Extracted: {state['company']} - {state['role']}")
        
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        state["company"] = "Unknown"
        state["role"] = "Unknown"
        state["error_message"] = f"Extraction error: {str(e)}"
    
    return state


# ============================================================================
# NODE 3: DECISION ROUTER (CONDITIONAL ROUTING)
# ============================================================================

def route_decision(state: EmailProcessingState) -> Literal["job_suggestions", "validate_transition", "skip"]:
    """
    LangGraph Conditional Edge: Route based on intent.
    
    ROUTING RULES:
    - Job_Recommendation → job_suggestions_node
    - Irrelevant → END (skip)
    - Applied/Interview/Offer/Rejected → validate_transition
    
    This replaces the if/else branching in original main.py
    """
    intent = state["intent"]
    
    if intent == "Job_Recommendation":
        logger.info("🔀 Routing to: Job Suggestions")
        return "job_suggestions"
    
    elif intent == "Irrelevant":
        logger.info("🔀 Routing to: Skip")
        state["action_taken"] = "Skipped"
        state["success"] = False
        return "skip"
    
    else:
        logger.info("🔀 Routing to: Applied Jobs Pipeline")
        return "validate_transition"


# ============================================================================
# NODE 4: JOB SUGGESTIONS STORAGE
# ============================================================================

def job_suggestions_node(state: EmailProcessingState) -> EmailProcessingState:
    """
    LangGraph Node: Save job recommendation to suggestions sheet.
    
    Maps to: save_job_suggestion() from excel_manager.py
    
    Terminal node for Job_Recommendation flow.
    """
    try:
        company = state["company"]
        role = state["role"]
        email_subject = state["email_subject"]
        email_sender = state["email_sender"]
        
        action = save_job_suggestion(
            company=company,
            role=role,
            source="Email",
            email_subject=email_subject,
            notes=f"From: {email_sender}"
        )
        
        state["action_taken"] = f"Suggestion_{action}"
        state["success"] = True
        
        logger.info(f"💡 Job suggestion {action.lower()}: {company} - {role}")
        
    except Exception as e:
        logger.error(f"Failed to save suggestion: {e}")
        state["success"] = False
        state["error_message"] = f"Suggestion storage error: {str(e)}"
    
    return state


# ============================================================================
# NODE 5: STATE MACHINE VALIDATION
# ============================================================================

def validate_transition_node(state: EmailProcessingState) -> EmailProcessingState:
    """
    LangGraph Node: Validate state transition using finite state machine.
    
    Maps to: apply_state_transition() from state_machine.py
    
    CRITICAL: Enforces valid job lifecycle transitions.
    """
    try:
        company = state["company"]
        role = state["role"]
        intent = state["intent"]
        
        # Normalize intent to status
        status_map = {
            "Applied_Confirmation": "Applied",
            "Interview": "Interview",
            "Rejected": "Rejected",
            "Offer": "Offer"
        }
        new_status = status_map.get(intent, intent)
        
        # Check existing record
        existing_record = get_job_record(company, role)
        
        if existing_record:
            current_status = existing_record.get("Status", "Applied")
            state["current_status"] = current_status
            
            # Validate transition
            final_status, reason = apply_state_transition(
                current_status, 
                new_status, 
                intent
            )
            
            if final_status is None:
                # Invalid transition
                state["transition_valid"] = False
                state["transition_reason"] = reason
                state["new_status"] = current_status
                logger.warning(f"❌ Blocked: {reason}")
            else:
                # Valid transition
                state["transition_valid"] = True
                state["transition_reason"] = reason
                state["new_status"] = final_status
                logger.info(f"✅ Valid transition: {current_status} → {final_status}")
        else:
            # New application
            state["transition_valid"] = True
            state["current_status"] = None
            state["new_status"] = new_status
            state["transition_reason"] = "New application detected"
            logger.info(f"✅ New application: {new_status}")
        
    except Exception as e:
        logger.error(f"State validation failed: {e}")
        state["transition_valid"] = False
        state["error_message"] = f"Validation error: {str(e)}"
    
    return state


# ============================================================================
# NODE 6: APPLIED JOBS UPDATE
# ============================================================================

def applied_jobs_node(state: EmailProcessingState) -> EmailProcessingState:
    """
    LangGraph Node: Update applied_jobs sheet in Excel.
    
    Maps to: insert_job() or update_job_status() from excel_manager.py
    
    Only executes if transition is valid.
    """
    if not state.get("transition_valid"):
        state["action_taken"] = "Blocked"
        state["success"] = False
        return state
    
    try:
        company = state["company"]
        role = state["role"]
        new_status = state["new_status"]
        email_sender = state["email_sender"]
        email_subject = state["email_subject"]
        reason = state["transition_reason"]
        
        if state["current_status"] is None:
            # Insert new record
            insert_job(
                company=company,
                role=role,
                status=new_status,
                recruiter_email=email_sender,
                email_subject=email_subject,
                notes=reason
            )
            state["action_taken"] = "Inserted"
            logger.info(f"➕ Inserted: {company} - {role} ({new_status})")
        else:
            # Update existing record
            update_job_status(
                company=company,
                role=role,
                new_status=new_status,
                recruiter_email=email_sender,
                email_subject=email_subject,
                notes=reason
            )
            state["action_taken"] = "Updated"
            logger.info(f"🔄 Updated: {company} - {role} → {new_status}")
        
        # Determine if notification needed
        state["should_notify"] = new_status in ["Interview", "Offer"]
        state["success"] = True
        
    except Exception as e:
        logger.error(f"Failed to update applied jobs: {e}")
        state["success"] = False
        state["error_message"] = f"Excel update error: {str(e)}"
    
    return state


# ============================================================================
# NODE 7: NOTIFICATION CHECK (CONDITIONAL ROUTING)
# ============================================================================

def check_notification(state: EmailProcessingState) -> Literal["notify", "end"]:
    """
    LangGraph Conditional Edge: Route to notification if needed.
    
    ROUTING RULES:
    - If Interview/Offer → notification_node
    - Else → END
    """
    if state.get("should_notify", False):
        logger.info("🔀 Routing to: Notification")
        return "notify"
    else:
        logger.info("🔀 Routing to: End")
        return "end"


# ============================================================================
# NODE 8: NOTIFICATION AGENT
# ============================================================================

def notification_node(state: EmailProcessingState) -> EmailProcessingState:
    """
    LangGraph Node: Send WhatsApp notification via Twilio.
    
    Maps to: notify_interview_scheduled() / notify_offer_received()
    from whatsapp_notifier.py
    """
    try:
        company = state["company"]
        role = state["role"]
        new_status = state["new_status"]
        
        if new_status == "Interview":
            notify_interview_scheduled(company, role)
            logger.info(f"📱 Sent interview notification: {company}")
        
        elif new_status == "Offer":
            notify_offer_received(company, role)
            logger.info(f"📱 Sent offer notification: {company}")
        
    except Exception as e:
        logger.error(f"Notification failed: {e}")
        # Don't fail the entire pipeline if notification fails
    
    return state


# ============================================================================
# GRAPH CONSTRUCTION
# ============================================================================

def create_job_processing_graph():
    """
    Build the LangGraph workflow.
    
    REPLACES: Custom if/else logic in main.py process_email()
    
    GRAPH FLOW:
    1. classify_node → extract_node → route_decision
    2a. Job_Recommendation → job_suggestions_node → END
    2b. Applied/Interview/Offer/Rejected → validate_transition_node → applied_jobs_node → check_notification
    3a. Interview/Offer → notification_node → END
    3b. Else → END
    """
    workflow = StateGraph(EmailProcessingState)
    
    # Add all nodes
    workflow.add_node("classify", classify_node)
    workflow.add_node("extract", extract_node)
    workflow.add_node("job_suggestions", job_suggestions_node)
    workflow.add_node("validate_transition", validate_transition_node)
    workflow.add_node("applied_jobs", applied_jobs_node)
    workflow.add_node("notification", notification_node)
    
    # Set entry point
    workflow.set_entry_point("classify")
    
    # Linear edges
    workflow.add_edge("classify", "extract")
    
    # Conditional routing after extraction
    workflow.add_conditional_edges(
        "extract",
        route_decision,
        {
            "job_suggestions": "job_suggestions",
            "validate_transition": "validate_transition",
            "skip": END
        }
    )
    
    # Job suggestions flow (terminal)
    workflow.add_edge("job_suggestions", END)
    
    # Applied jobs flow
    workflow.add_edge("validate_transition", "applied_jobs")
    
    # Conditional notification routing
    workflow.add_conditional_edges(
        "applied_jobs",
        check_notification,
        {
            "notify": "notification",
            "end": END
        }
    )
    
    # Notification flow (terminal)
    workflow.add_edge("notification", END)
    
    # Compile the graph
    app = workflow.compile()
    
    return app


# ============================================================================
# PUBLIC API
# ============================================================================

def process_email_with_graph(email: dict) -> dict:
    """
    Process a single email through the LangGraph pipeline.
    
    REPLACES: process_email() function in main.py
    
    Args:
        email: Dict with keys: subject, body, sender
    
    Returns:
        Dict with processing result
    """
    # Initialize state
    combined_text = email["subject"] + "\n" + email["body"]
    
    # Truncate if needed (same as before)
    if len(combined_text) > 6000:
        combined_text = combined_text[:6000] + "\n[... truncated for length]"
    
    initial_state: EmailProcessingState = {
        "email_subject": email["subject"],
        "email_body": email["body"],
        "email_sender": email.get("sender", ""),
        "combined_text": combined_text,
        "intent": None,
        "company": None,
        "role": None,
        "current_status": None,
        "new_status": None,
        "transition_valid": False,
        "transition_reason": None,
        "should_notify": False,
        "action_taken": None,
        "success": False,
        "error_message": None
    }
    
    # Create and run graph
    graph = create_job_processing_graph()
    final_state = graph.invoke(initial_state)
    
    # Format result (compatible with original return format)
    result = {
        "success": final_state["success"],
        "action": final_state.get("action_taken", "Unknown"),
        "company": final_state.get("company"),
        "role": final_state.get("role"),
        "classifier_result": final_state.get("intent"),
        "reason": final_state.get("transition_reason") or final_state.get("error_message"),
    }
    
    if final_state.get("current_status"):
        result["current_status"] = final_state["current_status"]
        result["new_status"] = final_state["new_status"]
    
    return result
