"""
Dashboard API: Data aggregation and insights for job application tracking

Provides aggregations, filtering, and follow-up suggestions for frontend/CLI dashboards.
"""

from excel_manager import get_dashboard_data, get_records_by_status, search_records
from follow_up_agent import batch_generate_followups
from datetime import datetime
from typing import List, Dict
import math


def _sanitize_value(val):
    """Convert NaN, Infinity, and None to safe values"""
    if val is None:
        return ""
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            return 0
    return val


def _sanitize_record(record):
    """Sanitize a record dict to remove NaN/Infinity values"""
    return {k: _sanitize_value(v) for k, v in record.items()}


def get_dashboard_summary(user_name: str = "John") -> Dict:
    """
    Get complete dashboard summary with stats and action items.
    
    Returns dict with:
    - stats: Application counts by status
    - recent_updates: Jobs updated in last 7 days
    - action_items: Jobs requiring follow-up
    - pending_decision: Offers/rejections needing action
    """
    data = get_dashboard_data()
    
    records = [_sanitize_record(r) for r in data.get("records", [])]
    
    # Find pending applications (Applied > 10 days, Interview > 7 days)
    action_items = []
    for job in records:
        status = job.get("Status", "")
        days_since = int(job.get("Days_Since_Update", 0) or 0)
        
        if (status == "Applied" and days_since > 10) or (status == "Interview" and days_since > 7):
            action_items.append({
                "company": job["Company"],
                "role": job["Role"],
                "status": status,
                "days_since_update": days_since,
                "priority": "high" if days_since > 14 else "medium"
            })
    
    # Find recent updates (last 7 days)
    recent_updates = [
        job for job in records 
        if int(job.get("Days_Since_Update", 0) or 0) <= 7
    ]
    
    # Find offers and rejections
    pending_decision = [
        job for job in records 
        if job.get("Status") in ["Offer", "Rejected"]
    ]
    
    return {
        "timestamp": datetime.now().isoformat(),
        "stats": {
            "total_applied": data["total_applied"],
            "total_interviews": data["total_interviews"],
            "total_offers": data["total_offers"],
            "total_rejections": data["total_rejections"],
            "pending_responses": data["pending"],
        },
        "action_items": action_items,
        "recent_updates": recent_updates,
        "pending_decision": pending_decision,
        "all_records": records
    }


def get_followup_suggestions(user_name: str = "John") -> List[Dict]:
    """
    Get actionable follow-up suggestions for all jobs.
    
    Returns list of suggested follow-ups with:
    - company, role
    - email subject and body
    - reasoning
    - recipient email
    """
    data = get_dashboard_data()
    records = data.get("records", [])
    
    followups = batch_generate_followups(records, user_name)
    
    return followups


def get_status_breakdown() -> Dict:
    """Get detailed breakdown by status with record counts."""
    data = get_dashboard_data()
    
    breakdown = {}
    for record in data.get("records", []):
        status = record.get("Status", "Unknown")
        if status not in breakdown:
            breakdown[status] = []
        breakdown[status].append({
            "company": record["Company"],
            "role": record["Role"],
            "last_update": record.get("Last_Update", ""),
            "days_since": int(record.get("Days_Since_Update", 0)),
            "recruiter": record.get("Recruiter_Email", "")
        })
    
    return breakdown


def get_jobs_by_status(status: str) -> List[Dict]:
    """
    Get all jobs filtered by a specific status (Applied, Interview, Offer, Rejected).

    This function sanitizes records to remove NaN/Infinity so JSON serialization
    cannot fail on the frontend fetch (previously causing "Unexpected token NaN").
    """
    data = get_dashboard_data()
    records = data.get("records", [])

    filtered: List[Dict] = []
    for record in records:
        if record.get("Status") != status:
            continue

        cleaned = _sanitize_record(record)
        filtered.append({
            "Company": cleaned.get("Company", ""),
            "Role": cleaned.get("Role", ""),
            "Status": cleaned.get("Status", ""),
            "Applied_Date": cleaned.get("Applied_Date", ""),
            "Last_Update": cleaned.get("Last_Update", ""),
            "Days_Since_Update": int(cleaned.get("Days_Since_Update", 0) or 0),
            "Recruiter_Email": cleaned.get("Recruiter_Email", ""),
            "Notes": cleaned.get("Notes", ""),
            "Link": cleaned.get("Link", ""),
        })

    return filtered


def get_jobs_needing_attention() -> List[Dict]:
    """
    Get jobs that require immediate attention:
    - No response for 10+ days after apply
    - No update for 7+ days after interview
    - Offers waiting for decision
    """
    data = get_dashboard_data()
    records = data.get("records", [])
    
    attention_needed = []
    
    for job in records:
        days = int(job.get("Days_Since_Update", 0))
        status = job.get("Status", "")
        
        reason = None
        priority = "low"
        
        if status == "Applied" and days > 10:
            reason = f"No response for {days} days"
            priority = "high" if days > 14 else "medium"
        elif status == "Interview" and days > 7:
            reason = f"No update for {days} days since interview"
            priority = "high" if days > 10 else "medium"
        elif status == "Offer":
            reason = "Decision needed on offer"
            priority = "high"
        elif status == "Rejected":
            reason = "Application rejected"
            priority = "low"
        
        if reason:
            attention_needed.append({
                "company": job["Company"],
                "role": job["Role"],
                "status": status,
                "reason": reason,
                "priority": priority,
                "last_update": job.get("Last_Update", ""),
                "recruiter": job.get("Recruiter_Email", "")
            })
    
    # Sort by priority (high first) and days since update (descending)
    priority_order = {"high": 0, "medium": 1, "low": 2}
    attention_needed.sort(
        key=lambda x: (priority_order.get(x["priority"], 3), -int(x.get("Days_Since_Update", 0)))
    )
    
    return attention_needed


def get_analytics_summary() -> Dict:
    """
    Get high-level analytics for insight/reflection.
    
    Includes:
    - Success rate (offers / total applied)
    - Average time in each stage
    - Most active recruiters
    - Application trends
    """
    data = get_dashboard_data()
    records = data.get("records", [])
    
    if not records:
        return {
            "success_rate": 0,
            "average_time_to_interview": 0,
            "average_time_to_offer": 0,
            "total_applications": 0,
            "top_recruiters": [],
            "stage_distribution": {}
        }
    
    # Calculate success rate
    total = len(records)
    offers = len([r for r in records if r.get("Status") == "Offer"])
    success_rate = (offers / total * 100) if total > 0 else 0
    
    # Count by status
    status_count = {}
    for record in records:
        status = record.get("Status", "Unknown")
        status_count[status] = status_count.get(status, 0) + 1
    
    # Find top recruiters (by email count)
    recruiter_count = {}
    for record in records:
        recruiter = record.get("Recruiter_Email", "Unknown")
        if recruiter and recruiter != "Unknown":
            recruiter_count[recruiter] = recruiter_count.get(recruiter, 0) + 1
    
    top_recruiters = sorted(recruiter_count.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        "success_rate": round(success_rate, 2),
        "total_applications": total,
        "total_offers": offers,
        "stage_distribution": status_count,
        "top_recruiters": [{"email": r[0], "interactions": r[1]} for r in top_recruiters],
        "application_funnel": {
            "applied": status_count.get("Applied", 0),
            "interview": status_count.get("Interview", 0),
            "offer": status_count.get("Offer", 0),
            "rejected": status_count.get("Rejected", 0)
        }
    }


def search_dashboard(query: str) -> Dict:
    """
    Search dashboard by company or role.
    
    Args:
        query: Search keyword (company or role)
    
    Returns:
        Matching records with stats
    """
    records = search_records(query)
    
    return {
        "query": query,
        "results": records,
        "count": len(records),
        "breakdown": {
            "applied": len([r for r in records if r.get("Status") == "Applied"]),
            "interview": len([r for r in records if r.get("Status") == "Interview"]),
            "offer": len([r for r in records if r.get("Status") == "Offer"]),
            "rejected": len([r for r in records if r.get("Status") == "Rejected"])
        }
    }
