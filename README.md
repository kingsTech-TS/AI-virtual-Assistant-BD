# Academic Support Chatbot — Backend API

![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas%20%2F%20Motor-47A248.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

A production-grade, AI-powered academic support chatbot backend built with **FastAPI**, **MongoDB**, and an OpenAI-compatible LLM layer. It serves students, staff, and administrators through a structured REST API supporting chat conversations, intent recognition, RAG-powered responses, support ticket management, FAQ and knowledge base management, feedback, notifications, analytics, and administrative audit logging.

---

## Table of Contents

1. [Features](#features)
2. [System Architecture](#system-architecture)
3. [Project Structure](#project-structure)
4. [Technology Stack](#technology-stack)
5. [Prerequisites](#prerequisites)
6. [Installation](#installation)
7. [Configuration](#configuration)
8. [Running the Application](#running-the-application)
9. [Database Setup](#database-setup)
10. [API Documentation](#api-documentation)
11. [Authentication](#authentication)
12. [Role-Based Access Control](#role-based-access-control)
13. [Staff & Admin Workflows](#staff--admin-workflows)
14. [AI Pipeline](#ai-pipeline)
15. [Testing](#testing)
16. [Scripts](#scripts)
17. [Deployment](#deployment)
18. [Environment Variables Reference](#environment-variables-reference)

---

## Features

- 🤖 **Intelligent AI Chat** — Intent classification, RAG retrieval, LLM response generation with graceful fallbacks.
- 🔐 **Secure Authentication** — JWT access/refresh tokens, bcrypt password hashing, password reset via email token.
- 👥 **Role-Based Access Control** — `student`, `staff`, `admin`, `super_admin` roles with fine-grained permissions.
- 🎫 **Support Ticket System** — FSM-based status lifecycle with department-scoped routing and notifications.
- 📚 **Knowledge Base** — Searchable vector-embedded documents with category tagging for RAG retrieval.
- 📋 **FAQ Management** — Staff-managed FAQ entries with view and helpful counts.
- 🏫 **Department Management** — Multi-department support with staff assignment.
- 🔔 **Real-Time Notifications** — Per-user notification delivery for ticket events and system updates.
- 📊 **Analytics Dashboard** — Overview metrics, intent distribution, ticket statistics, and feedback analytics.
- 📝 **Audit Logging** — Immutable audit trail for all admin and data-mutating actions.
- 💬 **Feedback** — Per-message positive/negative rating with deduplication.
- 🏥 **Health Checks** — Application and database health monitoring endpoints.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Application                     │
│  ┌──────────┐  ┌──────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │   Auth   │  │  Users   │  │    Chat     │  │   Tickets   │  │
│  │  Routes  │  │  Routes  │  │   Routes    │  │   Routes    │  │
│  └────┬─────┘  └────┬─────┘  └──────┬──────┘  └──────┬──────┘  │
│       │              │               │                  │       │
│  ┌────▼─────────────────────────────▼──────────────────▼──────┐  │
│  │                        Services Layer                      │  │
│  │  auth_service  user_service  chat_service  ticket_service   │  │
│  └──────────────────────────┬─────────────────────────────────┘  │
│                              │                                  │
│  ┌───────────────────────────▼─────────────────────────────────┐  │
│  │                      AI Pipeline                             │  │
│  │  IntentClassifier → RAGService → ResponseGenerator          │  │
│  │          ↓               ↓               ↓                  │  │
│  │   Embeddings        VectorSearch        LLMClient           │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                      MongoDB (Motor)                         │  │
│  │  users  conversations  messages  tickets  knowledge_base     │  │
│  │  faqs   departments    feedback  notifications  audit_logs   │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Chat Pipeline Flow

```
POST /api/v1/chat
       ↓
  ChatService
       ↓
  IntentClassifier  ──(LLM/keyword scoring)──→  intent + confidence
       ↓
  RAGService  ──(vector search / text fallback)──→  relevant sources
       ↓
  ResponseGenerator  ──(LLM prompt)──→  response text
       ↓
  Guardrails  ──(content safety check)──→  validated response
       ↓
  MongoDB  ──(persist messages + conversation)──→
       ↓
  JSON Response {conversation_id, message_id, response, intent, sources}
```

---

## Project Structure

```
academic-virtual-A-BD/
├── app/
│   ├── ai/                      # AI pipeline components
│   │   ├── embeddings.py        # Embedding provider (OpenAI-compatible)
│   │   ├── guardrails.py        # Content safety filter
│   │   ├── intent_classifier.py # LLM/keyword intent classification
│   │   ├── llm_client.py        # OpenAI-compatible LLM client
│   │   ├── prompt_manager.py    # System/RAG prompt construction
│   │   ├── rag_service.py       # Vector search + fallback retrieval
│   │   └── response_generator.py# Response assembly
│   ├── api/
│   │   ├── router.py            # APIRouter aggregator
│   │   └── routes/              # Resource route handlers
│   │       ├── admin.py         # Audit logs, role management
│   │       ├── analytics.py     # Overview, intent, ticket, feedback stats
│   │       ├── auth.py          # Register, login, refresh, reset
│   │       ├── chat.py          # Main chat endpoint
│   │       ├── conversations.py # Conversation history management
│   │       ├── departments.py   # Department CRUD
│   │       ├── faqs.py          # FAQ CRUD
│   │       ├── feedback.py      # Per-message feedback
│   │       ├── health.py        # Health checks
│   │       ├── knowledge.py     # Knowledge base CRUD
│   │       ├── notifications.py # User notifications
│   │       ├── tickets.py       # Support tickets
│   │       └── users.py         # User profile management
│   ├── constants/               # Enums (roles, statuses, intents, priorities)
│   ├── core/                    # Config, security, logging, exceptions
│   ├── database/                # MongoDB connection, index definitions, collections
│   ├── dependencies/            # FastAPI dependency functions (auth, db, permissions)
│   ├── models/                  # Document factories and dict serializers
│   ├── schemas/                 # Pydantic request/response schemas
│   ├── services/                # Business logic (one service per domain)
│   └── utils/                   # Helpers (IDs, dates, text formatting)
├── scripts/
│   ├── create_admin.py          # Create super_admin user
│   ├── create_indexes.py        # Create MongoDB indexes
│   └── seed_database.py         # Seed demo data
├── tests/
│   ├── conftest.py              # Test fixtures and in-memory mock database
│   ├── test_auth.py
│   ├── test_chat.py
│   ├── test_conversations.py
│   ├── test_faqs.py
│   ├── test_feedback.py
│   ├── test_knowledge.py
│   ├── test_tickets.py
│   └── test_users.py
├── .env                         # Environment variables (git-ignored)
├── .env.example                 # Environment variables template
├── deploy.md                    # Detailed GitHub & Render deployment guide
├── Dockerfile                   # Production Docker configuration
├── docker-compose.yml           # Local Docker development setup
├── pyproject.toml               # Build configuration & pytest settings
├── requirements.txt             # Python dependencies
└── README.md
```

---

## Technology Stack

| Component | Technology |
| :--- | :--- |
| **Framework** | FastAPI 0.115+ |
| **Database** | MongoDB Atlas (via Motor async driver) |
| **Auth** | JWT (`python-jose`), `bcrypt` |
| **AI / LLM** | OpenAI-compatible API (configurable) |
| **Embeddings** | OpenAI-compatible Embeddings API |
| **Validation** | Pydantic v2 |
| **Config** | `pydantic-settings` |
| **Testing** | `pytest-asyncio`, `httpx` ASGI |
| **Runtime** | Python 3.11+ |

---

## Prerequisites

- **Python 3.11+**
- **MongoDB Atlas** cluster (or local MongoDB 6+)
- An OpenAI-compatible LLM API key *(optional — keyword fallbacks operate seamlessly without it)*

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/academic-virtual-backend.git
cd academic-virtual-A-BD

# 2. Create and activate a virtual environment
python -m venv venv

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Configuration

Copy the example environment file and set your credentials:

```bash
cp .env.example .env
```

Example `.env` content:

```env
APP_NAME="Academic Support Chatbot"
APP_ENV=development
DEBUG=true

# MongoDB
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=academic_chatbot

# JWT — generate a secret using: python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=<your-32-byte-hex-secret>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# LLM (optional — falls back to keyword classification if empty)
LLM_API_KEY=<your-api-key>
LLM_MODEL=xai/grok-4.6
LLM_BASE_URL=https://ai-gateway.vercel.sh/v1

# Embeddings (optional — falls back to keyword vector matching if empty)
EMBEDDING_API_KEY=<your-api-key>
EMBEDDING_MODEL=openai/text-embedding-3-small
EMBEDDING_BASE_URL=https://ai-gateway.vercel.sh/v1

FRONTEND_URL=http://localhost:3000
LOG_LEVEL=INFO
```

---

## Running the Application

```bash
# Start local development server with hot-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Access local endpoints:
- **API Base:** `http://localhost:8000/api/v1`
- **Swagger UI Docs:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **Health Check:** `http://localhost:8000/`

---

## Database Setup

### 1. Create MongoDB Indexes

```bash
python scripts/create_indexes.py
```

### 2. Seed Demo Data (Optional)

```bash
python scripts/seed_database.py
```
*Seeds demo departments, sample knowledge base documents with embeddings, and default FAQs.*

### 3. Create Super Admin Account

```bash
# Using environment variables
ADMIN_EMAIL=admin@institution.edu ADMIN_PASSWORD=SecurePass123! python scripts/create_admin.py

# Or interactively:
python scripts/create_admin.py
```

---

## API Documentation

### Base URL
```
/api/v1
```

### Endpoints Summary

| Method | Path | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| **Auth** | | | |
| `POST` | `/auth/register` | Register new student account | No |
| `POST` | `/auth/login` | Login and receive JWT tokens | No |
| `POST` | `/auth/refresh` | Refresh access token | No |
| `GET` | `/auth/me` | Get authenticated user profile | Yes |
| `POST` | `/auth/forgot-password` | Request password reset token | No |
| `POST` | `/auth/reset-password` | Reset password using token | No |
| `POST` | `/auth/logout` | Revoke refresh token | Yes |
| **Chat** | | | |
| `POST` | `/chat` | Send message and receive AI response | Yes |
| `GET` | `/chat/conversations` | List user conversations | Yes |
| `GET` | `/chat/conversations/{id}` | Get conversation with messages | Yes |
| `DELETE` | `/chat/conversations/{id}` | Delete conversation | Yes (owner) |
| **Users** | | | |
| `GET` | `/users/me` | Get own profile | Yes |
| `PATCH` | `/users/me` | Update own profile | Yes |
| `GET` | `/users` | List all users | Admin+ |
| `GET` | `/users/{id}` | Get user by ID | Admin+ |
| `PATCH` | `/users/{id}` | Update user | Admin+ |
| **Tickets** | | | |
| `POST` | `/tickets` | Create support ticket | Yes |
| `GET` | `/tickets` | List tickets (role-scoped) | Yes |
| `GET` | `/tickets/{id}` | Get ticket details | Yes (scoped) |
| `PATCH` | `/tickets/{id}` | Update ticket status/comment | Yes (scoped) |
| **Knowledge Base** | | | |
| `GET` | `/knowledge` | List knowledge documents | Yes |
| `POST` | `/knowledge` | Create knowledge document | Staff+ |
| `GET` | `/knowledge/{id}` | Get document | Yes |
| `PATCH` | `/knowledge/{id}` | Update document | Staff+ |
| `DELETE` | `/knowledge/{id}` | Delete document | Staff+ |
| **FAQs** | | | |
| `GET` | `/faqs` | List FAQs | Yes |
| `POST` | `/faqs` | Create FAQ | Staff+ |
| `GET` | `/faqs/{id}` | Get FAQ | Yes |
| `PATCH` | `/faqs/{id}` | Update FAQ | Staff+ |
| `DELETE` | `/faqs/{id}` | Delete FAQ | Staff+ |
| **Feedback** | | | |
| `POST` | `/feedback` | Submit message feedback | Yes |
| **Departments** | | | |
| `GET` | `/departments` | List departments | Yes |
| `POST` | `/departments` | Create department | Admin+ |
| `GET` | `/departments/{id}` | Get department | Yes |
| `PATCH` | `/departments/{id}` | Update department | Admin+ |
| `DELETE` | `/departments/{id}` | Delete department | Admin+ |
| **Notifications** | | | |
| `GET` | `/notifications` | List user notifications | Yes |
| `PATCH` | `/notifications/{id}/read` | Mark notification as read | Yes |
| **Analytics** | | | |
| `GET` | `/analytics/overview` | System overview metrics | Admin+ |
| `GET` | `/analytics/intents` | Intent distribution stats | Admin+ |
| `GET` | `/analytics/tickets` | Ticket analytics | Admin+ |
| `GET` | `/analytics/feedback` | Feedback analytics | Admin+ |
| **Admin** | | | |
| `GET` | `/admin/audit-logs` | View audit trail | Admin+ |
| `PATCH` | `/admin/users/{id}/role` | Change user role | Super Admin |
| `GET` | `/admin/users` | Advanced user management | Admin+ |
| **Health** | | | |
| `GET` | `/` | Application health status | No |
| `GET` | `/api/v1/health` | Service health status | No |
| `GET` | `/api/v1/health/database` | Database connectivity check | No |

---

## Authentication

The API uses **Bearer JWT authentication**.

### Login Flow

```bash
# 1. Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Jane Doe","email":"jane@university.edu","password":"SecurePass123!","matric_number":"CSC/2024/001"}'

# 2. Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"jane@university.edu","password":"SecurePass123!"}'
# Returns: { "access_token": "...", "refresh_token": "...", "expires_in": 3600 }

# 3. Access Protected Endpoint
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

---

## Role-Based Access Control

The system enforces a 4-tier Role-Based Access Control hierarchy:

1. **`student`**: Chats with AI, creates & manages personal support tickets, submits feedback.
2. **`staff`**: Triages and resolves department tickets, communicates with students, adds notes.
3. **`admin`**: System administrator; manages staff, departments, knowledge documents, FAQs, analytics, and audit logs.
4. **`super_admin`**: Highest authority; manages administrators and updates user roles.

### Permission Matrix

| Feature / Resource | Student | Staff | Admin | Super Admin |
| :--- | :---: | :---: | :---: | :---: |
| **AI Chat & Conversations** | ✅ | ✅ | ✅ | ✅ |
| **Own Tickets (Create & View)** | ✅ | ✅ | ✅ | ✅ |
| **Staff Dashboard (`/api/v1/staff/*`)** | ❌ | ✅ | ✅ | ✅ |
| **Department & Assigned Tickets** | ❌ | ✅ | ✅ | ✅ |
| **All System Tickets (View & Reassign)** | ❌ | ❌ | ✅ | ✅ |
| **Close / Reassign Tickets** | ❌ | ❌ | ✅ | ✅ |
| **Staff Management (`/api/v1/admin/staff`)** | ❌ | ❌ | ✅ | ✅ |
| **User Management (`/api/v1/admin/users`)** | ❌ | ❌ | ✅ | ✅ |
| **Department Management** | ❌ | ❌ | ✅ | ✅ |
| **Knowledge Base Management** | ❌ | ❌ | ✅ | ✅ |
| **FAQ Management** | ❌ | ❌ | ✅ | ✅ |
| **System-Wide Analytics** | ❌ | ❌ | ✅ | ✅ |
| **Audit Logs Inspection** | ❌ | ❌ | ✅ | ✅ |
| **Role Elevation / Super Admin** | ❌ | ❌ | ❌ | ✅ |

---

## Staff & Admin Workflows

### Staff Workflow
1. **Login & Dashboard**: Staff logs in and views metrics (`GET /api/v1/staff/dashboard`).
2. **Ticket Triage**: Staff queries departmental tickets (`GET /api/v1/staff/tickets`).
3. **Claim Ticket**: Assigns ticket to self (`POST /api/v1/staff/tickets/{id}/assign`).
4. **Student Communication**: Responds to tickets (`POST /api/v1/staff/tickets/{id}/respond`).
5. **Resolution**: Resolves ticket upon completion (`POST /api/v1/staff/tickets/{id}/resolve`).

### Admin Workflow
1. **Staff Onboarding**: Creates staff accounts with department bindings (`POST /api/v1/admin/staff`).
2. **Knowledge Ingestion**: Uploads handbook/policy documents (`POST /api/v1/admin/knowledge/upload`).
3. **Institutional Oversight**: Manages overall tickets, department settings, analytics, and audit trails.

---

## AI Pipeline

### Recognized Academic Intents

| Intent | Description |
| :--- | :--- |
| `course_registration` | Course enrollment and registration guidance |
| `admission` | Admission requirements, processes, and status |
| `exam_schedule` | Examination dates, timetables, and guidelines |
| `academic_calendar` | Semester start/end dates and academic events |
| `results` | Grade queries, transcripts, and CGPA computation |
| `fees` | Fee payments, deadlines, and bursary queries |
| `portal_problem` | Technical support for student portal access |
| `password_change` | Account security and password reset guidance |
| `departmental_issue` | Department-specific academic support |
| `general_inquiry` | General institution questions and greetings |

### Fallback Strategies

| Scenario | System Behavior |
| :--- | :--- |
| **Missing `LLM_API_KEY`** | Keyword-based intent classification (zero external API calls required) |
| **LLM Timeout / Error** | Returns friendly fallback response and sets `requires_human_support: true` |
| **Low Intent Confidence (<0.3)** | Offers option to open a human support ticket |
| **Missing Embedding Key** | Cosine similarity on TF-IDF / keyword vectors |

---

## Testing

```bash
# Run all unit and integration tests
pytest -v

# Run specific test module
pytest tests/test_auth.py -v

# Run specific test function
pytest tests/test_tickets.py::test_ticket_status_transition_fsm -v
```

*Note: The test suite uses an in-memory mock database. No external database connection is required to run tests.*

---

## Scripts

| Script | Command | Description |
| :--- | :--- | :--- |
| **Create Indexes** | `python scripts/create_indexes.py` | Sets up unique, text, and vector indexes on MongoDB. |
| **Seed Database** | `python scripts/seed_database.py` | Populates demo departments, knowledge docs, and FAQs. |
| **Create Admin** | `python scripts/create_admin.py` | Provisions a `super_admin` account. |

---

## Deployment

For step-by-step guidance on pushing code to **GitHub** and hosting on **Render**, consult the dedicated deployment document:

📖 **[Deployment Guide (deploy.md)](file:///c:/Users/theki/Desktop/Coding%20Projects/academic-virtual-A-BD/deploy.md)**

### Local Docker Build

```bash
# Build image
docker build -t academic-chatbot-api .

# Run container with environment variables
docker run -p 8000:8000 --env-file .env academic-chatbot-api
```

---

## Environment Variables Reference

| Variable | Required | Default | Description |
| :--- | :---: | :--- | :--- |
| `MONGODB_URI` | ✅ | — | MongoDB Atlas connection URI |
| `MONGODB_DATABASE` | ❌ | `academic_chatbot` | Database name |
| `JWT_SECRET_KEY` | ✅ | — | JWT signing key (minimum 32 characters) |
| `JWT_ALGORITHM` | ❌ | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | ❌ | `60` | Access token TTL in minutes |
| `REFRESH_TOKEN_EXPIRE_DAYS` | ❌ | `7` | Refresh token TTL in days |
| `LLM_API_KEY` | ❌ | — | API key for OpenAI-compatible LLM |
| `LLM_MODEL` | ❌ | — | Model identifier (e.g. `xai/grok-4.6`) |
| `LLM_BASE_URL` | ❌ | — | OpenAI-compatible endpoint URL |
| `EMBEDDING_API_KEY` | ❌ | — | API key for embeddings |
| `EMBEDDING_MODEL` | ❌ | — | Embedding model identifier |
| `EMBEDDING_BASE_URL` | ❌ | — | Embeddings endpoint URL |
| `FRONTEND_URL` | ❌ | `http://localhost:3000` | Allowed CORS origin |
| `LOG_LEVEL` | ❌ | `INFO` | Application log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `APP_NAME` | ❌ | `Academic Support Chatbot` | Application title |
| `APP_ENV` | ❌ | `development` | Environment name (`development`, `production`) |
| `DEBUG` | ❌ | `false` | Enable debug mode |