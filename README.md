# 📅 AgendAI: Your Smart Schedule Assistant

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://agendai.streamlit.app/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Gemini API](https://img.shields.io/badge/Gemini-3.0%20Flash-magenta)](https://ai.google.dev/)

AgendAI is a calendar management platform that leverages the power of Gemini 3.0 Flash to transform how you interact with your schedule. From natural language chat to visual schedule extraction, AgendAI acts as a proactive personal assistant.

## Overview

Managing a busy schedule often involves manual data entry and constant context switching. AgendAI solves this by providing a unified interface where users can "talk" to their calendar. Whether you're uploading a screenshot of a university timetable or asking about potential overlapping events next Tuesday, AgendAI handles the complexity in the background.

## Features

- **Natural Language Assistant:** Manage your schedule naturally. Beyond simple additions, the assistant understands complex intent, relative dates ("next Friday"), and recurring events. You can ask it to "Reschedule my 2 PM meeting to 4 PM," "Clear my Friday afternoon," or "Summarize my week," and it handles the database logic automatically.
- **Visual Schedule Import:** Upload images (PNG, JPG, WebP, JPEG) of physical or digital schedules. The system automatically extracts events and populates your calendar.
- **Smart Conflict Audit:** A built-in logic engine that identifies overlapping commitments through a simple click. It works for both recurrent and single events.
- **Real-time Synchronization:** A dynamic calendar interface that displays your entire schedule in monthly, weekly, or daily views. It updates instantly as you interact with the AI agent.
- **Secure Multi-User Environment:** AgendAI is built with privacy at its core. Its authentication system ensures complete data isolation between users. Each calendar is strictly tied to a unique user account, meaning your schedule, personal events, and command history remain private and inaccessible to others

## Tech Stack

**Backend & Logic:**
- **Python:** The core programming language.
- **Google Gemini 3.0 Flash:** Used for conversational tool-calling.
- **Google Gemini 2.0 Flash:** Used for multimodal vision extraction.
- **SQLite:** A lightweight, reliable database for user accounts and event storage.

**Frontend:**
- **Streamlit:** For the interactive web dashboard.
- **Streamlit-Calendar:** Integration of FullCalendar for a native scheduling experience.

**Observability & AI Tooling:**
- **Langfuse:** For tracing AI generations and monitoring tool-calling performance.
- **Pillow (PIL):** For image pre-processing before AI analysis.

## Architecture (High Level)

AgendAI follows a strict **3-Tier Architecture** to ensure clean separation of concerns and system security:

1. **Presentation Layer (UI):** A Streamlit-based interface that captures user input and displays the calendar. It is "decoupled," meaning it sends raw data to the services without knowing how the database or AI functions.
2. **Service Layer (Orchestration):** The `CalendarService` acts as the brain. It coordinates between the UI, the AI Agent, and the Database. It ensures that when an image is processed, both the database and the AI's "memory" are updated simultaneously.
3. **Data & Tool Layer:** A collection of specialized tools (CRUD operations, Vision extraction) that interact directly with the database and APIs.

*Note: For a detailed deep-dive into design decisions and security implementations (like User ID binding), please refer to [ARCHITECTURE.md](./docs/ARCHITECTURE.md).*

## Installation & Setup

### Prerequisites
- Python 3.9+
- A Google AI Studio API Key (for Gemini)
- Langfuse API Keys (for observability)

### Installation Steps

1. **Clone the repository:**
```bash
git clone https://github.com/thepalhoto/ai-calendar--AgendAI-
cd agendai
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment logic:
```
1. Go to your Streamlit Cloud Dashboard.
2. Find your app and click on the three dots (⋮) next to it.
3. Select Settings.
4. On the left sidebar, click Secrets.
5. In the text area you can find the API keys currently being used.
```

**Required environment variables:**
```
GOOGLE_API_KEY=your_gemini_api_key_here
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com
```

4. Run the application:
```bash
streamlit run streamlit_app.py
```

## Usage

Instructions and examples for using your application. Include:
- How to navigate the interface
- Key workflows
- Screenshots or GIFs demonstrating functionality (recommended for visual clarity)

**Example:**

1. Navigate to the main page
2. Upload a document or enter your query
3. Interact with the AI assistant through the chat interface
4. View results and explore additional features

*Add screenshots or GIFs here to visually demonstrate your application's key features*

## Deployment

**Live Application:** (https://agendai.streamlit.app/)

**Deployment Platform:** Streamlit Cloud

Instructions for deploying your own instance (if applicable).

## Project Structure

```
ai-calendar--AgendAI-/
├── streamlit_app.py       # Main application entry point & UI
├── src/                   # Agent initialization and core logic
│   └── agent.py           # AI Agent configuration
├── services/              # Business logic layer
│   └── calendar_service.py # Orchestrator for tools and UI
├── tools/                 # Specialized tool implementations
│   ├── api_client.py      # Gemini API wrappers
│   ├── calendar_ops.py    # Calendar CRUD operations
│   ├── database_ops.py    # Database & User management
│   └── document_extraction.py # Vision/PDF extraction
├── config/                # Configuration assets
│   ├── constants.py       # Global constants
│   └── prompts.py         # System prompts
├── data/
│   └── scheduler.db       # SQLite database (Users & Events)
├── utils/                 # Utility scripts
├── docs/                  # Documentation & assets
└── requirements.txt       # Dependencies
```

**Note:** Component-level READMEs (e.g., `services/README.md`, `tools/README.md`) are recommended if those components need detailed explanation.

## Team

- Carlota Fradinho e Silva - Frontend & UX Engineer
- Gonçalo Palhoto - Backend & Tools Engineer 
- Gonçalo Morais - AI & Logic Engineer

## What Makes a Good README?

Your README should answer:
- **What** does this application do?
- **Why** does it exist / what problem does it solve?
- **How** do I run it locally?
- **Who** built it?

Keep it clear, organized, and professional. This is often the first thing evaluators and potential users will see.