# FULL BACKEND DEVELOPMENT PROMPT

## Project: Intelligent Chatbot for Academic Support Service

You are a senior Python backend engineer and AI systems architect.

Build a complete, production-quality backend for an **Intelligent Academic Support Chatbot** using:

* **Python**
* **FastAPI**
* **MongoDB Atlas**
* **Motor / PyMongo**
* **Pydantic / Pydantic Settings**
* **JWT authentication**
* **bcrypt password hashing**
* **LLM API integration**
* **RAG (Retrieval-Augmented Generation)**
* **MongoDB Atlas Vector Search where appropriate**
* **RESTful API architecture**
* **pytest for testing**

The backend will serve a Next.js + TypeScript + Tailwind CSS frontend.

The system is an academic support platform for tertiary-institution students. Its primary purpose is to allow students to ask academic and administrative questions using natural language and receive fast, clear, context-aware responses.

The chatbot must complement human academic/administrative staff rather than replace them. Complex, sensitive, or unresolved issues must be escalated through a support-ticket system.

---

# 1. CORE PROJECT OBJECTIVES

The backend must support the following major objectives:

1. Allow students to communicate with an intelligent chatbot using natural language.
2. Provide quick answers to common academic enquiries.
3. Retrieve trusted information from an institutional knowledge base.
4. Understand different ways students ask the same question.
5. Support course-registration enquiries.
6. Support admission enquiries.
7. Support examination and academic-calendar enquiries.
8. Support results-related enquiries.
9. Support student portal issues.
10. Support password-change guidance.
11. Support personal-information update guidance.
12. Support departmental issues.
13. Allow unresolved issues to become support tickets.
14. Allow staff/admins to manage support tickets.
15. Allow administrators to manage the chatbot's knowledge base.
16. Store conversations and messages.
17. Collect feedback about chatbot responses.
18. Provide administrative analytics.
19. Implement proper authentication and authorization.
20. Protect student data.
21. Provide clean REST APIs for a Next.js frontend.
22. Keep the architecture modular and easy to extend.

The system should follow an iterative and incremental architecture so additional features can be added later without rewriting the entire backend.

---

# 2. IMPORTANT ARCHITECTURAL PRINCIPLE

Do NOT build the application as one large FastAPI file.

Do NOT put:

* MongoDB queries
* AI logic
* authentication
* business logic
* validation
* routing
* prompts

inside `main.py`.

Use a modular architecture with:

```text
Routes
   ↓
Services
   ↓
AI / Business Logic
   ↓
Database
```

For AI functionality:

```text
Student Question
       ↓
FastAPI
       ↓
Intent Classification
       ↓
Knowledge Retrieval / RAG
       ↓
LLM
       ↓
Response Validation
       ↓
Save Conversation
       ↓
Return Response
```

---

# 3. REQUIRED PROJECT STRUCTURE

Create this structure:

```text
academic-chatbot-backend/
│
├── app/
│   ├── main.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── exceptions.py
│   │   └── logging.py
│   │
│   ├── database/
│   │   ├── mongodb.py
│   │   ├── indexes.py
│   │   └── collections.py
│   │
│   ├── models/
│   │   ├── user.py
│   │   ├── conversation.py
│   │   ├── message.py
│   │   ├── knowledge.py
│   │   ├── faq.py
│   │   ├── ticket.py
│   │   ├── department.py
│   │   ├── notification.py
│   │   ├── feedback.py
│   │   └── audit_log.py
│   │
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── chat.py
│   │   ├── conversation.py
│   │   ├── knowledge.py
│   │   ├── faq.py
│   │   ├── ticket.py
│   │   ├── department.py
│   │   ├── notification.py
│   │   ├── feedback.py
│   │   └── common.py
│   │
│   ├── api/
│   │   ├── router.py
│   │   │
│   │   └── routes/
│   │       ├── auth.py
│   │       ├── users.py
│   │       ├── chat.py
│   │       ├── conversations.py
│   │       ├── knowledge.py
│   │       ├── faqs.py
│   │       ├── tickets.py
│   │       ├── departments.py
│   │       ├── notifications.py
│   │       ├── feedback.py
│   │       ├── analytics.py
│   │       ├── admin.py
│   │       └── health.py
│   │
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── chat_service.py
│   │   ├── conversation_service.py
│   │   ├── knowledge_service.py
│   │   ├── faq_service.py
│   │   ├── ticket_service.py
│   │   ├── department_service.py
│   │   ├── notification_service.py
│   │   ├── feedback_service.py
│   │   └── analytics_service.py
│   │
│   ├── ai/
│   │   ├── llm_client.py
│   │   ├── intent_classifier.py
│   │   ├── rag_service.py
│   │   ├── embeddings.py
│   │   ├── prompt_manager.py
│   │   ├── response_generator.py
│   │   └── guardrails.py
│   │
│   ├── dependencies/
│   │   ├── auth.py
│   │   ├── database.py
│   │   └── permissions.py
│   │
│   ├── constants/
│   │   ├── intents.py
│   │   ├── roles.py
│   │   ├── statuses.py
│   │   └── priorities.py
│   │
│   └── utils/
│       ├── validators.py
│       ├── pagination.py
│       ├── helpers.py
│       └── ids.py
│
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_users.py
│   ├── test_chat.py
│   ├── test_conversations.py
│   ├── test_knowledge.py
│   ├── test_faqs.py
│   ├── test_tickets.py
│   └── test_feedback.py
│
├── scripts/
│   ├── create_indexes.py
│   ├── seed_database.py
│   └── create_admin.py
│
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── README.md
└── pyproject.toml
```

Create every required directory and file.

Do not create unnecessary files merely to make the structure look larger. Every module must have a clear responsibility.

---

# 4. DATABASE

Use **MongoDB Atlas**.

Use asynchronous database operations where possible.

Preferred database access:

```python
motor.motor_asyncio.AsyncIOMotorClient
```

Design the application so the MongoDB connection is initialized once and reused.

Database name should come from:

```env
MONGODB_DATABASE=academic_chatbot
```

MongoDB collections:

```text
users
conversations
messages
knowledge_base
faqs
tickets
departments
notifications
feedback
audit_logs
```

---

# 5. MONGODB CONNECTION

Create:

```text
app/database/mongodb.py
```

It should:

* create the MongoDB client
* select the configured database
* expose collection access
* support application startup
* support application shutdown
* properly close the MongoDB client
* handle connection errors
* provide a health-check function

Do not create a new MongoDB client for every request.

---

# 6. DATABASE INDEXES

Create indexes for frequently queried fields.

At minimum:

### users

```text
email
matric_number
role
department_id
```

### conversations

```text
user_id
created_at
updated_at
```

### messages

```text
conversation_id
created_at
```

### knowledge_base

```text
category
status
department_id
created_at
```

### FAQs

```text
category
status
created_at
```

### tickets

```text
ticket_number
user_id
department_id
status
priority
created_at
```

### feedback

```text
message_id
user_id
created_at
```

Create:

```text
scripts/create_indexes.py
```

to create these indexes safely.

---

# 7. USER SYSTEM

Implement users with these roles:

```text
student
staff
admin
super_admin
```

A user should contain fields similar to:

```json
{
  "_id": "...",
  "name": "...",
  "email": "...",
  "password_hash": "...",
  "matric_number": "...",
  "department_id": "...",
  "faculty": "...",
  "phone": "...",
  "role": "student",
  "is_active": true,
  "created_at": "...",
  "updated_at": "..."
}
```

Do not expose `password_hash` through any API response.

---

# 8. AUTHENTICATION

Implement JWT-based authentication.

Endpoints:

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
GET  /api/v1/auth/me
POST /api/v1/auth/forgot-password
POST /api/v1/auth/reset-password
```

Use secure password hashing.

Implement:

* password hashing
* password verification
* access tokens
* refresh tokens
* token expiration
* authentication dependency
* role-based authorization

Protect all private endpoints.

---

# 9. ROLE-BASED ACCESS CONTROL

Students should be able to:

* chat
* view their conversations
* create support tickets
* view their own tickets
* update permitted profile fields
* submit feedback
* view notifications

Staff should be able to:

* view assigned tickets
* update assigned tickets
* communicate ticket status
* access relevant departmental information

Admins should be able to:

* manage users
* manage FAQs
* manage knowledge base
* manage tickets
* manage departments
* view conversations
* view analytics

Super admins should have full system access.

Never trust the role sent from the frontend.

Always determine the authenticated user's role from the backend/database.

---

# 10. CHAT SYSTEM

Implement a complete conversation system.

A conversation should contain:

```json
{
  "_id": "...",
  "user_id": "...",
  "title": "...",
  "status": "active",
  "created_at": "...",
  "updated_at": "..."
}
```

Messages:

```json
{
  "_id": "...",
  "conversation_id": "...",
  "sender": "student",
  "content": "...",
  "intent": "...",
  "confidence": 0.95,
  "sources": [],
  "created_at": "..."
}
```

Sender types:

```text
student
assistant
system
staff
```

---

# 11. CHAT ENDPOINTS

Implement:

```text
POST /api/v1/chat
GET  /api/v1/chat/conversations
GET  /api/v1/chat/conversations/{conversation_id}
DELETE /api/v1/chat/conversations/{conversation_id}
```

Chat request:

```json
{
  "conversation_id": null,
  "message": "How do I register my courses?"
}
```

If `conversation_id` is null:

1. Create a conversation.
2. Save the student message.
3. Process the message.
4. Generate the response.
5. Save the assistant response.
6. Return the response.

---

# 12. CHAT RESPONSE

Return a consistent structure:

```json
{
  "success": true,
  "data": {
    "conversation_id": "...",
    "message_id": "...",
    "response": "...",
    "intent": "course_registration",
    "confidence": 0.95,
    "sources": [],
    "requires_human_support": false
  }
}
```

Do not expose internal prompts or API credentials.

---

# 13. INTENT CLASSIFICATION

Implement an intent-classification layer.

Initial intents:

```text
course_registration
admission
exam_schedule
academic_calendar
results
portal_problem
password_change
personal_details
departmental_issue
fees
general_information
human_support
unknown
```

Create:

```text
app/constants/intents.py
```

The intent classifier should return:

```json
{
  "intent": "portal_problem",
  "confidence": 0.94
}
```

The classifier must understand different natural-language variations.

For example:

```text
"My portal isn't working"

"I can't access my student portal"

"My school portal is giving me an error"

"I can't login to the portal"
```

should generally be recognized as portal-related requests.

---

# 14. LLM INTEGRATION

Create:

```text
app/ai/llm_client.py
```

Do not tightly couple the entire application to one AI provider.

Create an abstraction such as:

```python
class LLMClient:
    async def generate(self, prompt: str):
        ...
```

The provider/model must be configurable using environment variables.

Example:

```env
LLM_API_KEY=
LLM_MODEL=
LLM_BASE_URL=
```

If the selected provider has an official Python SDK, use it appropriately.

If a compatible OpenAI-style API is used, isolate that implementation inside `llm_client.py`.

The rest of the application should not care which provider is being used.

---

# 15. PROMPT MANAGEMENT

Create:

```text
app/ai/prompt_manager.py
```

Do not hard-code huge prompts inside route files.

Create functions for:

```text
build_intent_prompt()
build_answer_prompt()
build_rag_prompt()
build_escalation_prompt()
```

The chatbot's system prompt should instruct the model to:

1. Act as an academic support assistant.
2. Give concise and understandable answers.
3. Prefer verified institutional information.
4. Never invent university policies.
5. Never fabricate deadlines, fees, examination dates, registration dates, or official procedures.
6. Clearly state when information is unavailable.
7. Recommend human support for complex or sensitive issues.
8. Avoid exposing private student information.
9. Not claim to have performed actions it did not perform.
10. Use retrieved knowledge when provided.

---

# 16. RAG SYSTEM

Implement Retrieval-Augmented Generation.

Create:

```text
app/ai/rag_service.py
app/ai/embeddings.py
```

The RAG pipeline should be:

```text
Student Question
      ↓
Create embedding
      ↓
Search knowledge base
      ↓
Retrieve relevant documents
      ↓
Rank/filter results
      ↓
Send relevant context to LLM
      ↓
Generate grounded answer
```

Use MongoDB Atlas Vector Search where available.

Design the code so that vector-search configuration is isolated from the rest of the application.

---

# 17. KNOWLEDGE BASE

Knowledge documents should contain:

```json
{
  "_id": "...",
  "title": "Course Registration Procedure",
  "content": "...",
  "category": "course_registration",
  "department_id": null,
  "faculty": null,
  "source": "Academic Handbook",
  "status": "published",
  "embedding": [],
  "metadata": {},
  "created_by": "...",
  "updated_by": "...",
  "created_at": "...",
  "updated_at": "..."
}
```

Categories may include:

```text
registration
admission
examination
results
academic_calendar
fees
portal
password
departments
general
```

---

# 18. KNOWLEDGE BASE API

Implement:

```text
GET    /api/v1/knowledge
POST   /api/v1/knowledge
GET    /api/v1/knowledge/{id}
PATCH  /api/v1/knowledge/{id}
DELETE /api/v1/knowledge/{id}
```

Only authorized staff/admin users should create or modify knowledge.

When a knowledge document changes:

1. Update the document.
2. Regenerate its embedding if required.
3. Update vector-search data.
4. Record the change in the audit log.

---

# 19. FAQ SYSTEM

Implement:

```text
GET    /api/v1/faqs
POST   /api/v1/faqs
GET    /api/v1/faqs/{id}
PATCH  /api/v1/faqs/{id}
DELETE /api/v1/faqs/{id}
```

FAQ structure:

```json
{
  "_id": "...",
  "question": "How do I register courses?",
  "answer": "...",
  "category": "registration",
  "status": "published",
  "created_by": "...",
  "created_at": "...",
  "updated_at": "..."
}
```

---

# 20. SUPPORT TICKETS

Implement human escalation.

The chatbot should not attempt to solve every problem.

If:

* confidence is low
* information is unavailable
* the user explicitly requests staff
* the issue is sensitive
* the issue requires manual intervention

the chatbot should recommend or create a support ticket.

Ticket structure:

```json
{
  "_id": "...",
  "ticket_number": "TCK-10001",
  "user_id": "...",
  "department_id": "...",
  "subject": "...",
  "description": "...",
  "category": "portal_problem",
  "priority": "medium",
  "status": "open",
  "assigned_to": null,
  "created_at": "...",
  "updated_at": "..."
}
```

Statuses:

```text
open
in_progress
waiting_for_student
resolved
closed
```

Priorities:

```text
low
medium
high
urgent
```

---

# 21. TICKET API

Implement:

```text
POST  /api/v1/tickets
GET   /api/v1/tickets
GET   /api/v1/tickets/{ticket_id}
PATCH /api/v1/tickets/{ticket_id}
```

Students can only see their own tickets.

Staff can see tickets assigned to them or their department.

Admins can see all tickets.

---

# 22. DEPARTMENT SYSTEM

Create:

```text
departments
```

Example:

```json
{
  "_id": "...",
  "name": "Computer Science",
  "code": "CSC",
  "faculty": "Physical Sciences",
  "description": "...",
  "support_email": "...",
  "is_active": true
}
```

Endpoints:

```text
GET /api/v1/departments
GET /api/v1/departments/{id}
POST /api/v1/departments
PATCH /api/v1/departments/{id}
DELETE /api/v1/departments/{id}
```

---

# 23. SPECIAL PROJECT OBJECTIVES

The system must explicitly support the four project objectives:

## Password change

When the student asks:

```text
"I forgot my password"
```

detect:

```text
password_change
```

Provide the approved password-recovery process.

Do not expose passwords or password hashes.

---

## Portal problems

When the student reports:

```text
"My portal isn't working"
```

detect:

```text
portal_problem
```

Retrieve troubleshooting information.

If unresolved:

```text
Create support ticket
```

---

## Personal details

Support requests such as:

```text
"I want to update my phone number"
"I need to change my address"
"I want to update my personal details"
```

should map to:

```text
personal_details
```

For sensitive profile changes, use controlled backend endpoints rather than allowing the LLM to directly modify arbitrary database fields.

---

## Departmental issues

Questions such as:

```text
"I have a problem with my department"
"I need help with my CSC course"
"I want to contact my department"
```

should map to:

```text
departmental_issue
```

The system should identify the student's department where possible and route/escalate appropriately.

---

# 24. FEEDBACK SYSTEM

Allow students to rate chatbot responses.

Example:

```text
POST /api/v1/feedback
```

Request:

```json
{
  "message_id": "...",
  "rating": "positive",
  "comment": "This solved my problem."
}
```

Ratings:

```text
positive
negative
```

Store feedback for future chatbot improvement.

---

# 25. NOTIFICATIONS

Create a notification system for events such as:

* ticket created
* ticket updated
* ticket resolved
* staff response
* important academic information

Notification:

```json
{
  "_id": "...",
  "user_id": "...",
  "title": "...",
  "message": "...",
  "type": "ticket_update",
  "is_read": false,
  "created_at": "..."
}
```

Endpoints:

```text
GET   /api/v1/notifications
PATCH /api/v1/notifications/{id}/read
```

---

# 26. ANALYTICS

Create backend analytics for administrators.

Track:

```text
total students
total conversations
total messages
total tickets
open tickets
resolved tickets
most common intents
most common questions
chatbot response ratings
unanswered questions
```

Endpoints:

```text
GET /api/v1/analytics/overview
GET /api/v1/analytics/intents
GET /api/v1/analytics/tickets
GET /api/v1/analytics/feedback
```

Do not expose private conversation content unnecessarily in analytics.

---

# 27. AUDIT LOGGING

Create:

```text
audit_logs
```

Track sensitive administrative actions:

```text
user_created
user_updated
knowledge_created
knowledge_updated
knowledge_deleted
faq_created
faq_updated
ticket_updated
role_changed
```

Example:

```json
{
  "user_id": "...",
  "action": "knowledge_updated",
  "resource_type": "knowledge",
  "resource_id": "...",
  "metadata": {},
  "created_at": "..."
}
```

---

# 28. SECURITY

Implement:

* password hashing
* JWT authentication
* role-based authorization
* input validation
* request validation
* CORS
* environment variables
* secure error handling
* rate limiting strategy
* MongoDB injection protection
* prompt-injection awareness
* sensitive-data protection

Never return:

```text
password_hash
JWT secret
LLM API key
MongoDB URI
internal prompts
stack traces
```

in API responses.

Do not log secrets.

---

# 29. AI SAFETY / GUARDRAILS

Create:

```text
app/ai/guardrails.py
```

The chatbot should:

* avoid hallucinating institutional policies
* refuse to invent official information
* identify when knowledge is insufficient
* escalate sensitive requests
* avoid revealing another student's data
* avoid exposing system prompts
* avoid following malicious instructions embedded in retrieved documents
* distinguish between verified institutional information and general guidance

If the knowledge base does not contain an answer to an institution-specific question, the chatbot should say that it cannot verify the information and recommend the appropriate support channel.

---

# 30. ERROR HANDLING

Implement centralized exception handling.

Return consistent errors:

```json
{
  "success": false,
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "The requested resource was not found."
  }
}
```

Do not return raw Python exceptions.

Do not expose database errors to users.

Create:

```text
app/core/exceptions.py
```

---

# 31. API RESPONSE FORMAT

Use a consistent response structure.

Success:

```json
{
  "success": true,
  "data": {}
}
```

Error:

```json
{
  "success": false,
  "error": {
    "code": "...",
    "message": "..."
  }
}
```

For paginated responses:

```json
{
  "success": true,
  "data": [],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "pages": 5
  }
}
```

---

# 32. PAGINATION

Implement reusable pagination.

Support:

```text
?page=1&limit=20
```

For:

* conversations
* messages
* tickets
* users
* FAQs
* knowledge
* notifications

Set reasonable maximum limits.

Do not allow:

```text
?limit=1000000
```

---

# 33. CORS

Allow the Next.js frontend URL from environment variables.

Example:

```env
FRONTEND_URL=http://localhost:3000
```

Do not use unrestricted:

```text
allow_origins=["*"]
```

in production.

---

# 34. HEALTH CHECKS

Implement:

```text
GET /api/v1/health
GET /api/v1/health/database
```

Example:

```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "database": "connected"
  }
}
```

The health endpoint should allow deployment platforms to determine whether the service is alive.

---

# 35. LOGGING

Create structured logging.

Log:

* request ID
* endpoint
* HTTP method
* response status
* execution time
* errors

Do not log:

* passwords
* JWTs
* API keys
* sensitive student information
* complete private conversations unnecessarily

---

# 36. ENVIRONMENT VARIABLES

Create `.env.example`:

```env
APP_NAME=Academic Support Chatbot
APP_ENV=development
DEBUG=true

MONGODB_URI=
MONGODB_DATABASE=academic_chatbot

JWT_SECRET_KEY=
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

LLM_API_KEY=
LLM_MODEL=
LLM_BASE_URL=

FRONTEND_URL=http://localhost:3000

LOG_LEVEL=INFO
```

Never hard-code credentials.

---

# 37. REQUIREMENTS

Create a clean `requirements.txt`.

Include the required packages for:

* FastAPI
* Uvicorn
* MongoDB
* Pydantic
* JWT
* password hashing
* HTTP requests
* environment configuration
* testing

Only include packages that are actually used.

---

# 38. DOCKER

Create a production-friendly Dockerfile.

The application should run using:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Also create a development `docker-compose.yml` if useful.

Do NOT create a MongoDB container if the application is intended to use MongoDB Atlas in production. MongoDB Atlas should remain the external database.

---

# 39. DATABASE SEEDING

Create:

```text
scripts/seed_database.py
```

Seed realistic demo data:

### Departments

```text
Computer Science
Physics
Mathematics
Chemistry
```

### Knowledge

Add sample information for:

* course registration
* admission
* examination
* academic calendar
* portal troubleshooting
* password recovery
* departmental support

Clearly mark seeded information as demo/sample data.

Do not pretend that sample information is official university information.

---

# 40. ADMIN CREATION SCRIPT

Create:

```text
scripts/create_admin.py
```

It should allow creation of an initial administrator securely.

Do not hard-code admin credentials.

Read them from environment variables or secure CLI input.

---

# 41. TESTING

Use pytest.

Test:

### Authentication

* registration
* login
* invalid credentials
* token validation
* authorization

### Users

* profile retrieval
* profile update
* unauthorized access

### Chat

* new conversation
* existing conversation
* message storage
* intent classification
* AI failure handling

### Knowledge

* create
* retrieve
* update
* delete
* authorization

### Tickets

* create
* retrieve
* update
* permissions

### Feedback

* create feedback
* prevent invalid feedback

---

# 42. AI FAILURE HANDLING

The chatbot must remain stable if the LLM API fails.

For example:

```text
LLM unavailable
      ↓
Do not crash FastAPI
      ↓
Return friendly fallback
      ↓
Offer support ticket
```

Example response:

```text
"I'm currently unable to process your request. You can try again shortly or create a support ticket for assistance."
```

Never expose:

```text
OpenAIError
HTTP 500
API key error
```

to students.

---

# 43. DATABASE FAILURE HANDLING

If MongoDB becomes unavailable:

* return an appropriate service error
* log the database failure
* don't expose connection strings
* don't crash the entire application unnecessarily

Health checks should detect MongoDB availability.

---

# 44. CHATBOT RESPONSE PIPELINE

Implement this exact conceptual pipeline:

```text
1. Authenticate user
       ↓
2. Validate request
       ↓
3. Create/find conversation
       ↓
4. Save student message
       ↓
5. Detect intent
       ↓
6. Determine whether knowledge retrieval is needed
       ↓
7. Retrieve relevant academic information
       ↓
8. Evaluate confidence/relevance
       ↓
9. Generate grounded response using LLM
       ↓
10. Apply guardrails
       ↓
11. Determine whether human escalation is required
       ↓
12. Save assistant response
       ↓
13. Return response
```

---

# 45. EXAMPLE CHAT FLOW

Student:

```text
"When does course registration close?"
```

Backend:

```text
POST /api/v1/chat
```

Intent:

```text
course_registration
```

Knowledge retrieval:

```text
Search knowledge_base
```

Retrieved information:

```text
Official registration information...
```

LLM:

```text
Generate answer using retrieved information.
```

Response:

```json
{
  "success": true,
  "data": {
    "response": "...",
    "intent": "course_registration",
    "confidence": 0.94,
    "sources": [
      {
        "title": "Course Registration Guide"
      }
    ],
    "requires_human_support": false
  }
}
```

---

# 46. EXAMPLE ESCALATION FLOW

Student:

```text
"My portal has removed all my registered courses and I need someone to fix it."
```

Intent:

```text
portal_problem
```

The system should first provide appropriate troubleshooting.

If the issue requires staff intervention:

```text
requires_human_support = true
```

Offer:

```text
Create Support Ticket
```

If the user accepts:

```text
POST /api/v1/tickets
```

Create:

```text
TCK-10001
```

Route to the student's department.

---

# 47. SOURCE TRACKING

When RAG retrieves knowledge, store source metadata.

Example:

```json
"sources": [
  {
    "id": "...",
    "title": "Academic Handbook",
    "category": "registration"
  }
]
```

This allows the frontend to display:

```text
Sources:
Academic Handbook
Course Registration Guide
```

Do not expose internal embeddings.

---

# 48. PERFORMANCE

Use asynchronous operations.

Avoid:

```python
time.sleep()
```

inside async endpoints.

Use:

```python
await
```

for asynchronous database/API operations.

Avoid unnecessary database queries.

Use MongoDB indexes.

Implement pagination.

Do not retrieve the entire knowledge base for every chatbot request.

---

# 49. CODE QUALITY

Follow:

* PEP 8
* type hints
* clear function names
* small functions
* dependency injection
* separation of concerns
* reusable services
* meaningful comments
* proper docstrings where necessary

Do not create overly complicated abstractions.

Prioritize maintainability.

---

# 50. SWAGGER / API DOCUMENTATION

FastAPI's automatic documentation must work.

Ensure:

```text
/docs
/redoc
/openapi.json
```

are available during development.

Every endpoint should have:

* summary
* description
* request schema
* response schema
* status codes
* authentication requirements

Use tags:

```text
Authentication
Users
Chat
Conversations
Knowledge
FAQs
Tickets
Departments
Notifications
Feedback
Analytics
Admin
Health
```

---

# 51. FRONTEND COMPATIBILITY

The backend will be consumed by a Next.js frontend.

Therefore:

* return JSON
* use predictable response structures
* use RESTful endpoints
* use proper HTTP status codes
* enable CORS
* document request/response schemas
* never require frontend access to MongoDB
* never expose LLM API keys to the frontend

Architecture:

```text
Next.js
   ↓
FastAPI
   ↓
MongoDB Atlas
```

Never:

```text
Next.js
   ↓
MongoDB Atlas
```

for sensitive backend operations.

---

# 52. IMPORTANT SECURITY RULE

The frontend must never be trusted.

A student should not be able to change:

```json
{
  "role": "admin"
}
```

simply by modifying the request.

The backend must enforce permissions.

Similarly, a student must not be able to request:

```text
GET /users/{another_student_id}
```

and receive private information.

Implement ownership checks.

---

# 53. DO NOT OVERENGINEER

This is a university prototype but should have production-quality architecture.

Do NOT unnecessarily add:

* Kubernetes
* microservices
* Kafka
* Redis
* Celery
* GraphQL
* multiple databases

unless there is a clear technical reason.

Start with:

```text
Next.js
     ↓
FastAPI
     ↓
MongoDB Atlas
     ↓
LLM API
```

Keep it modular enough to add these technologies later if required.

---

# 54. DEVELOPMENT ORDER

Implement the project in this order:

## Phase 1

Create:

```text
FastAPI application
MongoDB connection
Configuration
Health endpoint
Error handling
Logging
```

## Phase 2

Implement:

```text
User model
Authentication
JWT
Roles
Permissions
```

## Phase 3

Implement:

```text
Conversations
Messages
Chat endpoints
```

## Phase 4

Implement:

```text
LLM client
Intent classification
Response generation
```

## Phase 5

Implement:

```text
Knowledge base
FAQs
Embeddings
RAG
MongoDB Vector Search
```

## Phase 6

Implement:

```text
Tickets
Departments
Human escalation
```

## Phase 7

Implement:

```text
Feedback
Notifications
Analytics
Audit logs
```

## Phase 8

Implement:

```text
Tests
Seed scripts
Admin creation
Docker
Documentation
```

---

# 55. ACCEPTANCE CRITERIA

The backend is considered complete only when:

* FastAPI starts successfully.
* MongoDB Atlas connects successfully.
* `/docs` works.
* Authentication works.
* JWT protection works.
* Role-based permissions work.
* Students can create accounts.
* Students can log in.
* Students can create conversations.
* Students can send messages.
* Messages are persisted.
* AI responses are generated.
* Intent classification works.
* Knowledge retrieval works.
* RAG works where configured.
* FAQs can be managed.
* Knowledge documents can be managed.
* Tickets can be created.
* Tickets can be assigned.
* Staff can update tickets.
* Students can view their own tickets.
* Feedback can be submitted.
* Admin analytics work.
* Errors are handled properly.
* Secrets are stored in environment variables.
* API documentation works.
* Tests pass.
* Docker build works.
* No sensitive information is exposed in API responses.

---

# 56. IMPORTANT IMPLEMENTATION RULE

Do not merely generate empty placeholder files.

Every requested module should contain working implementation where possible.

If a third-party AI provider is required and credentials are not available, create a clean provider abstraction and configuration system, then provide a clear `.env.example`.

Do not fabricate API keys.

Do not hard-code credentials.

Do not fabricate institutional academic information.

Use clearly marked demo data for seeding.

---

# 57. FINAL DELIVERABLE

At the end of implementation, provide:

1. Complete backend source code.
2. Complete folder structure.
3. `requirements.txt`.
4. `.env.example`.
5. Dockerfile.
6. docker-compose configuration where useful.
7. MongoDB index creation script.
8. Database seed script.
9. Admin creation script.
10. Complete API routes.
11. Pydantic schemas.
12. Authentication system.
13. AI integration abstraction.
14. Intent classification.
15. RAG implementation.
16. Knowledge-base management.
17. FAQ management.
18. Ticket system.
19. Department management.
20. Feedback system.
21. Notification system.
22. Analytics.
23. Audit logging.
24. Tests.
25. README with setup instructions.
26. API documentation.
27. Example API requests.
28. Example environment configuration.

---

# 58. README REQUIREMENTS

The README must explain:

```text
Project overview
Architecture
Technology stack
Requirements
Installation
Environment variables
MongoDB Atlas configuration
Running locally
Running with Docker
Creating indexes
Seeding database
Creating admin
Running tests
API documentation
Authentication
Chatbot architecture
RAG architecture
Deployment
Troubleshooting
```

Include commands such as:

```bash
python -m venv venv
```

Activation for Windows:

```powershell
venv\Scripts\activate
```

Install:

```bash
pip install -r requirements.txt
```

Run:

```bash
uvicorn app.main:app --reload
```

Tests:

```bash
pytest
```

---

# 59. FINAL ARCHITECTURE

The final backend should follow this architecture:

```text
                         ┌─────────────────────┐
                         │      NEXT.JS        │
                         │      FRONTEND       │
                         └──────────┬──────────┘
                                    │
                                  REST
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │       FASTAPI       │
                         │                     │
                         │ Authentication      │
                         │ Authorization       │
                         │ Chat API            │
                         │ User API            │
                         │ Ticket API          │
                         │ Knowledge API       │
                         │ Admin API            │
                         └──────────┬──────────┘
                                    │
                 ┌──────────────────┼──────────────────┐
                 │                  │                  │
                 ▼                  ▼                  ▼
          ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
          │   MongoDB    │   │   AI LAYER   │   │   SERVICES   │
          │    ATLAS     │   │              │   │              │
          │              │   │ Intent       │   │ Auth         │
          │ Users        │   │ RAG          │   │ Tickets      │
          │ Messages     │   │ Embeddings   │   │ Knowledge    │
          │ Conversations│   │ LLM          │   │ Analytics    │
          │ Knowledge    │   │ Guardrails   │   │ Notifications│
          │ Tickets      │   └──────┬───────┘   └──────────────┘
          │ FAQs         │          │
          └──────────────┘          ▼
                             ┌──────────────┐
                             │   LLM API    │
                             │              │
                             │ Understanding│
                             │ Classification│
                             │ Generation   │
                             └──────────────┘
```

The key principle is:

**FastAPI controls the application. MongoDB Atlas stores the institutional data. RAG retrieves trusted academic information. The LLM understands language and generates responses. The ticket system handles issues the AI cannot safely resolve.**

Build the backend according to this specification, keeping the code modular, secure, testable, documented, and ready for integration with a Next.js + TypeScript + Tailwind frontend.
