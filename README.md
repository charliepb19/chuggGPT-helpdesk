# ChuggGPT AI Helpdesk

ChuggGPT AI Helpdesk is an AI-powered IT support platform built with FastAPI, WebSockets, SQLAlchemy, SQLite, Jinja2, and the OpenAI API. It helps users submit support tickets, receive AI-guided troubleshooting in real time, and enables admins to manage ticket operations through a centralized dashboard.

## Overview

This project was built to simulate a modern AI-native IT helpdesk experience. It combines classic support workflows with AI ticket triage, live troubleshooting chat, automation execution, and audit logging.

ChuggGPT is designed to feel like an early-stage SaaS platform rather than just a basic CRUD app.

---

# Features

## User Features

- User signup and login
- Ticket submission form
- Ticket history view
- Real-time AI support chat via WebSockets
- AI-guided troubleshooting workflow

## Admin Features

- Admin dashboard with ticket overview
- Ticket filtering by name, status, category, and severity
- Ticket claiming and assignment
- Ticket status updates
- Automation execution
- Audit log visibility

## AI Features

- AI ticket triage on submission
- Category prediction
- Severity prediction
- Business impact estimation
- Confidence scoring
- Escalation flagging
- Suggested automation recommendations
- AI support chat that responds interactively

## Automation Features

- Simulated automation execution
- DNS flush
- Network reset
- Printer restart
- Disk cleanup
- Automation logging and audit trail
- Risk-aware automation policy foundation

---

# Tech Stack

Backend
- FastAPI
- SQLAlchemy
- SQLite

Frontend
- Jinja2 templates
- HTML
- CSS
- JavaScript

AI
- OpenAI API

Other
- WebSockets
- Session-based authentication

---

# System Architecture


User / Admin
|
v
FastAPI Routes
|
+--> Auth
+--> Tickets
+--> Dashboard
+--> Chat
|
v
Services Layer
|
+--> AI Classifier
+--> AI Triage
+--> Chat Agent
+--> Automation Engine
+--> Automation Policy
|
v
SQLite Database
|
+--> Users
+--> Tickets
+--> Audit Logs
+--> Chat Sessions
+--> Chat Messages
+--> Ticket Predictions
+--> Automation Runs


---

# Project Structure


chuggGPT-helpdesk
│
├── app
│ ├── routes
│ │ ├── auth.py
│ │ ├── tickets.py
│ │ ├── dashboard.py
│ │ └── chat.py
│ │
│ ├── services
│ │ ├── ai_classifier.py
│ │ ├── ai_triage.py
│ │ ├── chat_agent.py
│ │ ├── automation.py
│ │ ├── automation_policy.py
│ │ └── auth.py
│ │
│ ├── templates
│ │ ├── base.html
│ │ ├── login.html
│ │ ├── signup.html
│ │ ├── submit_ticket.html
│ │ ├── my_tickets.html
│ │ ├── dashboard.html
│ │ └── chat.html
│ │
│ ├── static
│ │ └── style.css
│ │
│ ├── database.py
│ ├── models.py
│ ├── main.py
│ └── create_admin.py
│
├── requirements.txt
├── README.md
└── .gitignore

---

# How the System Works

## Ticket Submission

A user submits an IT support ticket including:

- device type
- urgency level
- issue description

---

## AI Ticket Triage

After submission, the AI system analyzes the ticket and predicts:

- category
- severity
- business impact
- automation possibilities

The result is stored in the database.

---

## Real-Time AI Support Chat

A chat session is automatically created.

The AI agent:

- guides troubleshooting
- asks follow-up questions
- can trigger automations
- escalates issues when needed

---

## Automation Execution

Automations simulate real IT operations such as:

- flushing DNS
- restarting printers
- resetting network configurations
- disk cleanup

Each automation is logged for auditing.

---

## Admin Dashboard

Admins can:

- review tickets
- claim tickets
- update statuses
- execute automations
- review audit logs

---

# Running the Project Locally

## Clone the repository
git clone https://github.com/charliepb19/chuggGPT-helpdesk.git

cd chuggGPT-helpdesk


---

## Create virtual environment


py -m venv venv


---

## Activate environment

Windows:


.\venv\Scripts\Activate.ps1


---

## Install dependencies


pip install -r requirements.txt


---

## Add OpenAI API Key

Create an environment variable or `.env` file:


OPENAI_API_KEY=your_api_key_here


---

## Start the server


uvicorn app.main:app --reload


---

## Open the app


http://127.0.0.1:8000


---

# Creating an Admin Account

Run:


python -m app.create_admin


Then log in with the generated admin credentials.

---

# Screenshots

Add screenshots here later.

Example:


screenshots/login.png
screenshots/dashboard.png
screenshots/chat.png

---

# Why This Project Is Interesting

This project demonstrates real-world skills including:

- backend API development
- AI integration
- real-time systems
- system automation
- SaaS-style application design

It showcases concepts used in modern AI-powered support platforms.

---

# Future Improvements

Potential enhancements include:

- AI incident clustering
- duplicate ticket detection
- knowledge base integration
- AI embeddings for troubleshooting search
- analytics dashboards
- approval workflows for automations
- Slack or email integrations

---

# Resume Summary

Built an AI-powered IT helpdesk platform using FastAPI, SQLAlchemy, SQLite, WebSockets, and the OpenAI API. Implemented automated ticket triage, real-time AI troubleshooting chat, admin operations tooling, and automation execution workflows.

---

# License

MIT
