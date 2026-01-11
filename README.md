# Agentic AI Job Application Email Tracker

An autonomous AI agent that reads recruiter emails, understands job application updates, and maintains an Excel-based job tracker automatically.

## Features
- Reads Gmail inbox using Gmail API
- Classifies job emails using Groq LLaMA-3
- Extracts company, role, and status
- Auto-inserts or updates Excel rows
- Fully local and secure

## Tech Stack
- Python
- Gmail API
- Groq LLaMA-3
- Pandas
- OAuth 2.0

## How to Run
1. Add `credentials.json`
2. Add Groq API key to `.env`
3. Install dependencies
4. Run `python main.py`

## Output
An auto-updated Excel file: `applications.xlsx`
