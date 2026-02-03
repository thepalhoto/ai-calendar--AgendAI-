# System Architecture

## Overview
AgendAI follows a standard **3-Tier Architecture** that separates user interaction (Presentation), business orchestration (Logic), and data management (Data & Tools).
This design ensures that the user interface is decoupled from the complex AI logic, allowing for easier testing and future scalability.

## Architecture Diagram

graph TD
    %% Actors
    User([User])

    %% Frontend Layer
    subgraph Frontend ["Frontend (Streamlit)"]
        UI["streamlit_app.py<br/>(Main Interface)"]
    end

    %% Logic Layer
    subgraph Core ["Core Logic"]
        Agent["src/agent.py<br/>(AI Agent & Tool Orchestration)"]
        Service["services/calendar_service.py<br/>(Auth & Bridge)"]
    end

    %% Tools Layer
    subgraph Tools ["Tools & Integrations"]
        API["tools/api_client.py<br/>(Gemini Client)"]
        CalOps["tools/calendar_ops.py<br/>(CRUD Operations)"]
        DocExt["tools/document_extraction.py<br/>(Vision/PDF)"]
        DBOps["tools/database_ops.py<br/>(User Management)"]
    end

    %% Config Layer
    subgraph Config ["Configuration"]
        Const["config/constants.py"]
        Prompts["config/prompts.py"]
    end

    %% External Systems
    subgraph External ["External Services"]
        Gemini[("Google Gemini API<br/>(LLM & Vision)")]
        LocalDB[("Database/Storage")]
    end

    %% Relationships
    User <-->|Interacts| UI

    %% UI Dependencies
    UI -->|Initializes| Agent
    UI -->|Calls| Service
    UI -.->|Reads| Const

    %% Agent Dependencies
    Agent -->|Configures| API
    Agent -->|Registers Tools| CalOps
    Agent -.->|Uses System Prompt| Prompts

    %% Service Dependencies
    Service -->|Verifies User| DBOps
    Service -->|Delegates Events| CalOps
    Service -->|Extracts Data| DocExt

    %% Tool Implementations
    API <-->|Requests| Gemini
    DocExt <-->|Vision Request| Gemini
    CalOps -->|Read/Write| LocalDB
    DBOps -->|Auth Check| LocalDB

## Layers

### 1. Presentation Layer (Frontend)
- **Tech Stack:** Streamlit, Streamlit-Calendar
- **Responsibility:** Handles all user input (chat, file uploads) and renders the visual calendar using FullCalendar.
- **Key File:** `streamlit_app.py`
- **Design Decision:** The UI is "dumb"; it does not know about the database or the AI implementation. It simply calls the Service Layer and displays the result.

### 2. Service Layer (Orchestration)
- **Tech Stack:** Python Classes (`CalendarService`, `Agent`)
- **Responsibility:** Acts as the brain of the application.
    - **Authentication:** Verifies user credentials before allowing access.
    - **Orchestration:** Connects the "dumb" UI to the "smart" Tools.
    - **Agent Management:** Determines which tool to call based on user intent (e.g., "Add Event" vs. "Check Conflict").
- **Key Files:** `services/calendar_service.py`, `src/agent.py`

### 3. Data & Tool Layer (Backend)
- **Tech Stack:** SQLite, Google Gemini API (Vision & Chat)
- **Responsibility:** Executes the actual work.
    - **Calendar Ops:** CRUD operations (Create, Read, Update, Delete) on the database.
    - **Vision Extraction:** Sending images to Gemini 2.0 Flash to parse schedules.
    - **Database:** Storing user credentials and event data securely.
- **Key Files:** `tools/calendar_ops.py`, `tools/database_ops.py`, `tools/document_extraction.py`

## Data Flow (Example: "Visual Import")
1. **User** uploads an image via Streamlit.
2. **CalendarService** receives the image bytes and calls the `extract_events_from_image` tool.
3. **Gemini 2.0 Flash** analyzes the image and returns a structured JSON list of events.
4. **CalendarService** iterates through the JSON and calls `add_event` for each item, writing to **SQLite**.
5. **CalendarService** triggers a system notification to the **AI Agent** so it "knows" the schedule has changed.
6. **UI** refreshes the calendar view to show the new blocks.

## Key Design Decisions

### User Isolation via SQLite
Instead of a complex cloud database, we used **SQLite** with a relational schema (`users` table linked to `events` table).
- **Reasoning:** It simplifies deployment (single file) while still strictly enforcing data isolation. A query like `SELECT * FROM events WHERE user_id = ?` ensures a user never sees another person's data.

### Hybrid AI Approach
We use two different models for specialized tasks:
- **Gemini 2.0 Flash:** Used for Vision (Parsing images) because of its superior multimodal capabilities.
- **Gemini 3.0 Flash (implied/upgradable):** Used for the Chat Agent for faster, high-throughput logical reasoning.

### Observability First
**Langfuse** is integrated into nearly every function (via the `@observe` decorator).
- **Reasoning:** In an AI application, "why did it do that?" is the hardest question to answer. Tracing allows us to see exactly what prompt was sent and what tool outputs led to a specific decision.

## Observability
All AI interactions (Tool calls, Parsed Images, Chat Responses) are traced using Langfuse. This enables:
- Debugging tool failures (e.g., "Why did the add_event tool fail?")
- Monitoring latency and token usage.
- Evaluating the quality of the Vision extraction prompts.
