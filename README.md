# Job Application Intelligence System

**Autonomous AI agent for intelligent job application tracking and management.**

Automatically processes recruiter emails, maintains application state with validation, and provides context-aware follow-up suggestions using LangGraph orchestration and LLM-powered intelligence.

---

## 🎯 Key Features

| Feature | Tech | Benefit |
|---------|------|---------|
| **LangGraph Orchestration** | StateGraph + TypedDict | Declarative workflow, modular, testable |
| **Finite State Machine** | State validation layer | Prevents invalid transitions, ensures data integrity |
| **Email Intelligence** | Groq LLaMA-3 + multi-layer filtering | 99% noise reduction, accurate classification |
| **Incremental Sync** | Gmail API + timestamp tracking | Efficient, scalable email processing |
| **Follow-up Generation** | Context-aware LLM | Smart email draft suggestions |
| **Real-time Dashboard** | Flask + REST API | Live monitoring with auto-refresh |
| **WhatsApp Alerts** | Twilio API | Instant notifications for offers/interviews |

---

## 🏗️ Architecture

**Workflow**: Gmail API → LangGraph Orchestration → Classification/Extraction → State Validation → Excel Persistence → Dashboard

**LangGraph Graph**:
```
classify_node → extract_node → route_decision
                                  ├─→ job_suggestions_node
                                  └─→ validate_transition_node → applied_jobs_node → notification_node
```

**State Machine**: `Applied → Interview/Rejected → Offer/Rejected → Terminal`

---

## 🚀 Quick Start

### Setup
```bash
# Clone & setup
git clone <repo-url> && cd job-email-tracker
python -m venv .venv && .\.venv\Scripts\Activate.ps1

# Install & configure
pip install -r requirements.txt requirements-dashboard.txt

# Add credentials
# 1. Place credentials.json (Google Cloud Console)
# 2. Set GROQ_API_KEY=<your_key>
```

### Run
```bash
# Process emails (incremental sync)
python main.py

# View dashboard (http://localhost:5000)
python start_dashboard.py
```

---

## 📊 Example Output

**Terminal:**
```
✓ [1] Applied: Microsoft → Senior SWE
✓ [2] Updated: Google → SWE (Applied → Interview)
✗ [3] Invalid: Meta → PM (blocked: Interview → Applied)
✓ [4] Offer: Amazon → Data Scientist
⚠️  4 jobs need attention (10+ days no response)
```

**Dashboard:**
- Total applications: 28 | Active interviews: 6 | Offers: 2 | Success rate: 25%
- Real-time alerting for time-sensitive actions
- AI-generated follow-up email suggestions

---

## 📁 Project Structure

```
├── graph_pipeline.py       # LangGraph orchestration
├── main.py                 # Entry point
├── state_machine.py        # Finite state validation
├── classifier_agent.py     # Intent classification
├── extractor_agent.py      # Entity extraction
├── follow_up_agent.py      # Email suggestions
├── gmail_reader.py         # Incremental sync
├── email_filter.py         # Multi-layer filtering
├── excel_manager.py        # Dual-sheet persistence
├── dashboard_api.py        # REST API
├── app.py                  # Dashboard server
├── validation.py           # Test suite
└── requirements.txt        # Dependencies
```

---

## 🔧 Production Features

- ✅ **State Machine Validation**: Blocks invalid transitions at runtime
- ✅ **Error Resilience**: Graceful degradation, NaN-safe JSON serialization
- ✅ **Data Integrity**: `(Company, Role)` unique key, audit trail for all transitions
- ✅ **Scalability**: O(new emails) complexity, pagination support, stateless processing
- ✅ **Responsible AI**: Suggestions only (no auto-send), transparent reasoning, local data only
- ✅ **Responsible AI**: Human-in-the-loop design, local data persistence

---

## 🛠️ Tech Stack

**Backend**: Python 3.8+ | **Orchestration**: LangGraph | **LLM**: Groq LLaMA-3  
**Email**: Gmail API (OAuth 2.0) | **Storage**: Excel (openpyxl) | **Web**: Flask  
**Notifications**: Twilio (WhatsApp) | **Data**: Pandas | **Config**: python-dotenv

---

## 🧪 Testing

```bash
# Run automated test suite (state machine + filtering)
python validation.py

# Verify Gmail connection
python -c "from gmail_reader import read_latest_emails; print(len(read_latest_emails(5, False)))"
```

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Gmail token expired | `Remove-Item token.pkl` → `python main.py` (re-auth) |
| No new emails | Delete `last_run.txt` to force full mailbox scan |
| Missing dependencies | `pip install -r requirements.txt` |
| Dashboard 0 records | Run `python main.py` to populate Excel first |

---

## 📚 Use Cases

- **Job Seekers**: Automate tracking, never miss follow-up deadlines
- **Portfolio**: Demonstrates LangGraph, state machines, event-driven architecture
- **Learning**: Study agentic AI patterns, API integration, production practices

---

## 📄 License

MIT License - Free to use, modify, distribute.

---

**Status**: Production-ready | **Updated**: January 2026 | **Architecture**: LangGraph-based agentic AI
