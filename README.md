# Academic Support Chatbot — Backend API

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
13. [AI Pipeline](#ai-pipeline)
14. [Testing](#testing)
15. [Scripts](#scripts)
16. [Deployment](#deployment)
17. [Environment Variables Reference](#environment-variables-reference)

---

## Features

- 🤖 **Intelligent AI Chat** — Intent classification, RAG retrieval, LLM response generation with graceful fallbacks
- 🔐 **Secure Authentication** — JWT access/refresh tokens, bcrypt password hashing, password reset via email token
- 👥 **Role-Based Access Control** — `student`, `staff`, `admin`, `super_admin` roles with fine-grained permissions
- 🎫 **Support Ticket System** — FSM-based status lifecycle with department-scoped routing and notifications
- 📚 **Knowledge Base** — Searchable vector-embedded documents with category tagging for RAG retrieval
- 📋 **FAQ Management** — Staff-managed FAQ entries with view and helpful counts
- 🏫 **Department Management** — Multi-department support with staff assignment
- 🔔 **Real-Time Notifications** — Per-user notification delivery for ticket events, system updates
- 📊 **Analytics Dashboard** — Overview metrics, intent distribution, ticket statistics, feedback analytics
- 📝 **Audit Logging** — Immutable audit trail for all admin and data-mutating actions
- 💬 **Feedback** — Per-message positive/negative rating with deduplication
- 🏥 **Health Checks** — Application and database health monitoring endpoints

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Application                       │
│  ┌──────────┐  ┌──────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │   Auth   │  │  Users   │  │    Chat     │  │   Tickets   │  │
│  │  Routes  │  │  Routes  │  │   Routes    │  │   Routes    │  │
│  └────┬─────┘  └────┬─────┘  └──────┬──────┘  └──────┬──────┘  │
│       │              │               │                  │         │
│  ┌────▼─────────────────────────────▼──────────────────▼──────┐  │
│  │                        Services Layer                        │  │
│  │  auth_service  user_service  chat_service  ticket_service   │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
│                              │                                      │
│  ┌───────────────────────────▼───────────────────────────────────┐  │
│  │                      AI Pipeline                               │  │
│  │  IntentClassifier → RAGService → ResponseGenerator            │  │
│  │          ↓               ↓               ↓                    │  │
│  │   Embeddings        VectorSearch        LLMClient             │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                      MongoDB (Motor)                           │  │
│  │  users  conversations  messages  tickets  knowledge_base       │  │
│  │  faqs   departments    feedback  notifications  audit_logs     │  │
│  └────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────┘
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
│   │   └── routes/              # One file per resource
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
│   └── utils/                   # Helpers (ids, dates, text)
├── scripts/
│   ├── create_admin.py          # Create super_admin user
│   ├── create_indexes.py        # Create MongoDB indexes
│   └── seed_database.py         # Seed demo data
├── tests/
│   ├── conftest.py              # Fixtures, in-memory mock database, auth helpers
│   ├── test_auth.py
│   ├── test_chat.py
│   ├── test_conversations.py
│   ├── test_faqs.py
│   ├── test_feedback.py
│   ├── test_knowledge.py
│   ├── test_tickets.py
│   └── test_users.py
├── .env                         # Environment variables (not committed)
├── .env.example                 # Template for environment variables
├── pyproject.toml               # Build config and pytest settings
├── requirements.txt             # Python dependencies
└── README.md
```

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Framework | FastAPI 0.115+ |
| Database | MongoDB Atlas (via Motor async driver) |
| Auth | JWT (python-jose), bcrypt |
| AI / LLM | OpenAI-compatible API (configurable) |
| Embeddings | OpenAI-compatible Embeddings API |
| Validation | Pydantic v2 |
| Config | pydantic-settings |
| Testing | pytest-asyncio, httpx ASGI |
| Python | 3.11+ |

---

## Prerequisites

- Python 3.11 or higher
- MongoDB Atlas cluster (or local MongoDB 6+)
- An OpenAI-compatible LLM API key (optional — keyword fallbacks work without it)

---

## Installation

```bash
# 1. Clone the repository
git clone <repository-url>
cd academic-virtual-A-BD

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Configuration

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:

```env
APP_NAME=Academic Support Chatbot
APP_ENV=development
DEBUG=true

# MongoDB
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=academic_chatbot

# JWT — generate a strong secret: python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=<your-32-byte-hex-secret>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# LLM (optional — falls back to keyword classification if not set)
# Vercel AI Gateway (OpenAI-compatible); model ids are provider-prefixed
LLM_API_KEY=<your-vercel-ai-gateway-key>
LLM_MODEL=xai/grok-4.6
LLM_BASE_URL=https://ai-gateway.vercel.sh/v1

# Embeddings (optional — falls back to cosine similarity if not set)
EMBEDDING_API_KEY=<your-vercel-ai-gateway-key>
EMBEDDING_MODEL=openai/text-embedding-3-small
EMBEDDING_BASE_URL=https://ai-gateway.vercel.sh/v1

FRONTEND_URL=http://localhost:3000
LOG_LEVEL=INFO
```

---

## Running the Application

```bash
# Development server with hot reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API Base:** `http://localhost:8000/api/v1`
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **Health:** `http://localhost:8000/api/v1/health`

---

## Database Setup

### 1. Create MongoDB Indexes

```bash
python scripts/create_indexes.py
```

This creates all required indexes (unique constraints, text indexes, vector search indexes) on your MongoDB Atlas cluster.

### 2. Seed Demo Data (optional)

```bash
python scripts/seed_database.py
```

Inserts demo departments (Computer Science, Physics, Mathematics, Chemistry), 8 knowledge base documents with embeddings, and 10 sample FAQs.

### 3. Create Super Admin Account

```bash
# Using environment variables:
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
|--------|------|-------------|---------------|
| **Auth** | | | |
| POST | `/auth/register` | Register new student account | No |
| POST | `/auth/login` | Login and receive JWT tokens | No |
| POST | `/auth/refresh` | Refresh access token | No |
| GET | `/auth/me` | Get authenticated user profile | Yes |
| POST | `/auth/forgot-password` | Request password reset token | No |
| POST | `/auth/reset-password` | Reset password using token | No |
| POST | `/auth/logout` | Revoke refresh token | Yes |
| **Chat** | | | |
| POST | `/chat` | Send message and receive AI response | Yes |
| GET | `/chat/conversations` | List user conversations | Yes |
| GET | `/chat/conversations/{id}` | Get conversation with messages | Yes |
| DELETE | `/chat/conversations/{id}` | Delete conversation | Yes (owner) |
| **Users** | | | |
| GET | `/users/me` | Get own profile | Yes |
| PATCH | `/users/me` | Update own profile | Yes |
| GET | `/users` | List all users | Admin+ |
| GET | `/users/{id}` | Get user by ID | Admin+ |
| PATCH | `/users/{id}` | Update user | Admin+ |
| **Tickets** | | | |
| POST | `/tickets` | Create support ticket | Yes |
| GET | `/tickets` | List tickets (role-scoped) | Yes |
| GET | `/tickets/{id}` | Get ticket details | Yes (scoped) |
| PATCH | `/tickets/{id}` | Update ticket status/comment | Yes (scoped) |
| **Knowledge Base** | | | |
| GET | `/knowledge` | List knowledge documents | Yes |
| POST | `/knowledge` | Create knowledge document | Staff+ |
| GET | `/knowledge/{id}` | Get document | Yes |
| PATCH | `/knowledge/{id}` | Update document | Staff+ |
| DELETE | `/knowledge/{id}` | Delete document | Staff+ |
| **FAQs** | | | |
| GET | `/faqs` | List FAQs | Yes |
| POST | `/faqs` | Create FAQ | Staff+ |
| GET | `/faqs/{id}` | Get FAQ | Yes |
| PATCH | `/faqs/{id}` | Update FAQ | Staff+ |
| DELETE | `/faqs/{id}` | Delete FAQ | Staff+ |
| **Feedback** | | | |
| POST | `/feedback` | Submit message feedback | Yes |
| **Departments** | | | |
| GET | `/departments` | List departments | Yes |
| POST | `/departments` | Create department | Admin+ |
| GET | `/departments/{id}` | Get department | Yes |
| PATCH | `/departments/{id}` | Update department | Admin+ |
| DELETE | `/departments/{id}` | Delete department | Admin+ |
| **Notifications** | | | |
| GET | `/notifications` | List user notifications | Yes |
| PATCH | `/notifications/{id}/read` | Mark notification as read | Yes |
| **Analytics** | | | |
| GET | `/analytics/overview` | System overview metrics | Admin+ |
| GET | `/analytics/intents` | Intent distribution stats | Admin+ |
| GET | `/analytics/tickets` | Ticket analytics | Admin+ |
| GET | `/analytics/feedback` | Feedback analytics | Admin+ |
| **Admin** | | | |
| GET | `/admin/audit-logs` | View audit trail | Admin+ |
| PATCH | `/admin/users/{id}/role` | Change user role | Super Admin |
| GET | `/admin/users` | Advanced user management | Admin+ |
| **Health** | | | |
| GET | `/health` | Application health | No |
| GET | `/health/database` | Database connectivity | No |

---

## Authentication

The API uses **Bearer JWT authentication**.

### Login Flow

```bash
# 1. Register
curl -X POST /api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Jane Doe","email":"jane@university.edu","password":"SecurePass123!","matric_number":"CSC/2024/001"}'

# 2. Login
curl -X POST /api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"jane@university.edu","password":"SecurePass123!"}'
# Returns: { "access_token": "...", "refresh_token": "...", "expires_in": 3600 }

# 3. Use token
curl -X GET /api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

### Token Refresh

```bash
curl -X POST /api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<refresh_token>"}'
```

---

## Role-Based Access Control (RBAC)

The system implements a strict, 4-tier Role-Based Access Control system:

1. **`student`** — Primary system user. Chats with the AI, manages own support tickets, views own conversations, and submits feedback.
2. **`staff`** — Departmental support personnel. Triage and resolve student tickets, communicate with students, add internal notes, escalate issues, and view only department/assigned tickets.
3. **`admin`** — System management. Manages users, staff, departments, knowledge documents, FAQs, assigns/reassigns all tickets, inspects analytics, and views audit logs.
4. **`super_admin`** — Controls administrators and critical system configuration. Exclusively authorized to promote/demote administrator roles and manage super admin accounts.

### Permission Matrix

| Feature / Resource | Student | Staff | Admin | Super Admin |
|:---|:---:|:---:|:---:|:---:|
| **AI Chat & Conversations** | ✅ YES | ✅ YES | ✅ YES | ✅ YES |
| **Own Tickets (Create & View)** | ✅ YES | ✅ YES | ✅ YES | ✅ YES |
| **Staff Dashboard (`/api/v1/staff/*`)** | ❌ NO | ✅ YES | ✅ YES | ✅ YES |
| **Department & Assigned Tickets** | ❌ NO | ✅ YES | ✅ YES | ✅ YES |
| **All System Tickets (View & Reassign)** | ❌ NO | ❌ NO | ✅ YES | ✅ YES |
| **Close / Reassign Tickets** | ❌ NO | ❌ NO | ✅ YES | ✅ YES |
| **Staff Management (`/api/v1/admin/staff`)** | ❌ NO | ❌ NO | ✅ YES | ✅ YES |
| **User Management (`/api/v1/admin/users`)** | ❌ NO | ❌ NO | ✅ YES | ✅ YES |
| **Department Management** | ❌ NO | ❌ NO | ✅ YES | ✅ YES |
| **Knowledge Base Management & Ingestion** | ❌ NO | ❌ NO | ✅ YES | ✅ YES |
| **FAQ Management** | ❌ NO | ❌ NO | ✅ YES | ✅ YES |
| **System-Wide Analytics** | ❌ NO | ❌ NO | ✅ YES | ✅ YES |
| **Audit Logs Inspection** | ❌ NO | ❌ NO | ✅ YES | ✅ YES |
| **Super Admin / Role Elevation** | ❌ NO | ❌ NO | ❌ NO | ✅ YES |

---

## Staff & Admin Workflows

### Staff Workflow (Human Support)
1. **Login & Dashboard**: Staff logs in (`POST /api/v1/auth/login`) and retrieves dashboard metrics via `GET /api/v1/staff/dashboard`.
2. **Ticket Triage**: Staff queries `GET /api/v1/staff/tickets` to list tickets belonging to their assigned department.
3. **Claim Ticket**: Staff assigns a ticket to themselves via `POST /api/v1/staff/tickets/{id}/assign`.
4. **Student Communication**: Staff responds to student inquiries via `POST /api/v1/staff/tickets/{id}/respond`. The student receives an in-app notification and the ticket status transitions to `waiting_for_student`.
5. **Escalation**: If higher authority is needed, staff calls `POST /api/v1/staff/tickets/{id}/escalate` with reason.
6. **Resolution**: Staff resolves the ticket via `POST /api/v1/staff/tickets/{id}/resolve`, notifying the student.

### Admin Workflow (System Management)
1. **Staff Onboarding**: Admin creates staff accounts with departmental assignments via `POST /api/v1/admin/staff`.
2. **Knowledge Ingestion**: Admin uploads academic handbooks and policy PDFs via `POST /api/v1/admin/knowledge/upload`. The system automatically extracts text, chunks, computes vector embeddings, and publishes documents for RAG retrieval.
3. **Ticket Oversight**: Admin views all tickets across the institution (`GET /api/v1/admin/tickets`) and can assign or reassign tickets (`POST /api/v1/admin/tickets/{id}/assign`, `/reassign`).
4. **Analytics & Audit**: Admin monitors institutional KPIs (`GET /api/v1/admin/analytics/overview`) and inspects immutable audit trails (`GET /api/v1/admin/audit-logs`).

---

## AI Pipeline

### Intent Classification

Supports the following academic intents:

| Intent | Description |
|--------|-------------|
| `course_registration` | Course enrollment and registration help |
| `admission` | Admission requirements and processes |
| `exam_schedule` | Examination dates, dockets, and guidelines |
| `academic_calendar` | Semester dates and academic events |
| `results` | Grade queries and CGPA computation |
| `fees` | Fee payment and bursary queries |
| `portal_problem` | Student portal technical issues |
| `password_change` | Password reset and account access |
| `departmental_issue` | Department-specific academic support |
| `general_inquiry` | General questions and greetings |

### Fallback Behavior

| Scenario | Behavior |
|----------|----------|
| No `LLM_API_KEY` | Keyword-based intent scoring (no LLM calls) |
| LLM timeout / error | Returns friendly fallback message, sets `requires_human_support: true` |
| Low confidence (<0.3) | Suggests creating a support ticket |
| No matching knowledge | Uses LLM general knowledge with escalation offer |
| No `EMBEDDING_API_KEY` | Falls back to cosine similarity on keyword vectors |

---

## Testing

```bash
# Run all tests
python -m pytest -v

# Run specific test module
python -m pytest tests/test_auth.py -v

# Run specific test
python -m pytest tests/test_tickets.py::test_ticket_status_transition_fsm -v
```

The test suite uses an in-memory mock MongoDB database with full async support — **no real database connection required** for tests.

---

## Scripts

| Script | Description |
|--------|-------------|
| `scripts/create_indexes.py` | Create all required MongoDB indexes |
| `scripts/seed_database.py` | Seed demo departments, knowledge docs, FAQs |
| `scripts/create_admin.py` | Create a `super_admin` user interactively or via env vars |

---

## Deployment

### Docker (recommended)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t academic-chatbot-api .
docker run -p 8000:8000 --env-file .env academic-chatbot-api
```

### Production Checklist

- [ ] Set `APP_ENV=production` and `DEBUG=false`
- [ ] Use a strong, randomly generated `JWT_SECRET_KEY`
- [ ] Enable MongoDB Atlas network access restrictions
- [ ] Run `python scripts/create_indexes.py` after first deploy
- [ ] Run `python scripts/create_admin.py` to create the super admin
- [ ] Set `FRONTEND_URL` to your production frontend domain
- [ ] Use HTTPS (reverse proxy with nginx/caddy)

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MONGODB_URI` | ✅ | — | MongoDB connection string |
| `MONGODB_DATABASE` | ❌ | `academic_chatbot` | Database name |
| `JWT_SECRET_KEY` | ✅ | — | JWT signing secret (min 32 chars) |
| `JWT_ALGORITHM` | ❌ | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | ❌ | `60` | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | ❌ | `7` | Refresh token TTL |
| `LLM_API_KEY` | ❌ | — | LLM API key (enables AI responses) |
| `LLM_MODEL` | ❌ | — | LLM model identifier |
| `LLM_BASE_URL` | ❌ | — | LLM API base URL |
| `EMBEDDING_API_KEY` | ❌ | — | Embeddings API key (enables vector search) |
| `EMBEDDING_MODEL` | ❌ | — | Embedding model identifier |
| `EMBEDDING_BASE_URL` | ❌ | — | Embeddings API base URL |
| `FRONTEND_URL` | ❌ | `http://localhost:3000` | Allowed CORS origin |
| `LOG_LEVEL` | ❌ | `INFO` | Logging level |
| `APP_NAME` | ❌ | `Academic Support Chatbot` | Application name |
| `APP_ENV` | ❌ | `development` | Environment (`development`/`production`) |
| `DEBUG` | ❌ | `false` | Enable debug mode |
#   A I - v i r t u a l - A s s i s t a n t - B D  
 