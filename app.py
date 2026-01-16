"""
Flask API Server for Dashboard
Serves job application data to frontend dashboard
"""

from flask import Flask, jsonify, render_template
from flask_cors import CORS
from dashboard_api import (
    get_dashboard_summary, 
    get_status_breakdown,
    get_jobs_needing_attention,
    get_analytics_summary,
    get_followup_suggestions
)
from excel_manager import get_all_suggestions, get_saved_suggestions
from datetime import datetime
import json
import math

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)


class SafeJSONEncoder(json.JSONEncoder):
    """Handle NaN, Infinity, and None values in JSON serialization"""
    def encode(self, o):
        if isinstance(o, float):
            if math.isnan(o):
                return "0"
            elif math.isinf(o):
                return "0"
        return super().encode(o)
    
    def iterencode(self, o, _one_shot=False):
        for chunk in super().iterencode(o, _one_shot):
            yield chunk


app.json_encoder = SafeJSONEncoder


@app.route('/')
def index():
    """Serve the main dashboard HTML"""
    return render_template('dashboard.html')


@app.route('/api/dashboard')
def api_dashboard():
    """Get complete dashboard data"""
    try:
        summary = get_dashboard_summary()
        analytics = get_analytics_summary()
        
        return jsonify({
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "summary": summary,
            "analytics": analytics
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/applied-jobs')
def api_applied_jobs():
    """Get all applied jobs"""
    try:
        summary = get_dashboard_summary()
        records = summary.get('all_records', [])
        
        return jsonify({
            "success": True,
            "data": records,
            "count": len(records)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/followups')
def api_followups():
    """Generate follow-up email suggestions for jobs needing action."""
    try:
        followups = get_followup_suggestions(user_name="Sornambal")
        return jsonify({
            "success": True,
            "data": followups,
            "count": len(followups)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/suggestions')
def api_suggestions():
    """Get job suggestions"""
    try:
        all_suggestions = get_all_suggestions()
        saved = get_saved_suggestions()
        
        # Sanitize records to handle NaN values
        from dashboard_api import _sanitize_record
        all_suggestions = [_sanitize_record(s) for s in all_suggestions]
        saved = [_sanitize_record(s) for s in saved]
        
        return jsonify({
            "success": True,
            "all": all_suggestions,
            "saved": saved,
            "total": len(all_suggestions),
            "saved_count": len(saved)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/attention-needed')
def api_attention():
    """Get jobs needing attention"""
    try:
        attention = get_jobs_needing_attention()
        
        return jsonify({
            "success": True,
            "data": attention,
            "count": len(attention)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/status-breakdown')
def api_status_breakdown():
    """Get breakdown by status"""
    try:
        breakdown = get_status_breakdown()
        
        return jsonify({
            "success": True,
            "data": breakdown
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
