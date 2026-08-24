# Implementation Plan: Intelligent Academic Support Chatbot Backend

## Project Overview
Build a complete production-quality backend for an **Intelligent Academic Support Chatbot** using Python, FastAPI, MongoDB Atlas, and LLM/RAG integration. The system serves tertiary-institution students with natural-language academic and administrative support, escalating unresolved issues to human staff via tickets.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Web Framework | FastAPI (async) |
| Database | MongoDB Atlas (Motor async driver) |
| Schema Validation | Pydantic / Pydantic Settings |
| Auth | JWT (access + refresh tokens) + bcrypt |
| AI | LLM API (configurable provider) + RAG + MongoDB Atlas Vector Search |
| Testing | pytest |
| Containerization | Docker + docker-compose (dev only) |
| App Server | Uvicorn |

---

## Project Structure (Target)

```
academic-chatbot-backend/
├── app/
│   ├── main.py                          # FastAPI app entrypoint; mounts routers, CORS, startup/shutdown events
│   ├── core/
│   │   ├── config.py                    # Pydantic Settings: env vars, DB URI, JWT config, LLM config, CORS origins
│   │   ├── security.py                  # bcrypt hashing, JWT create/verify, password utilities
│   │   ├── exceptions.py                # Custom exception classes + FastAPI exception handlers (consistent {success,error} format)
│   │   └── logging.py                   # Structured logger setup (request ID, endpoint, status, exec time, no secrets)
│   ├── database/
│   │   ├── mongodb.py                   # Singleton AsyncIOMotorClient, db/collection accessors, startup/shutdown, health check
│   │   ├── indexes.py                   # Index definitions for all collections (referenced by create_indexes script)
│   │   └── collections.py               # Named collection constants + typed helper accessors
│   ├── models/                          # MongoDB document field definitions (dataclass/dict-style helpers, NOT ORM)
│   │   ├── user.py                      # user fields: name, email, password_hash, matric_number, department_id, faculty, phone, role, is_active, timestamps
│   │   ├── conversation.py              # conversation fields: user_id, title, status, timestamps
│   │   ├── message.py                   # message fields: conversation_id, sender, content, intent, confidence, sources, timestamps
│   │   ├── knowledge.py                 # knowledge fields: title, content, category, department_id, faculty, source, status, embedding, metadata, created_by, timestamps
│   │   ├── faq.py                       # faq fields: question, answer, category, status, created_by, timestamps
│   │   ├── ticket.py                    # ticket fields: ticket_number, user_id, department_id, subject, description, category, priority, status, assigned_to, timestamps
│   │   ├── department.py                # department fields: name, code, faculty, description, support_email, is_active
│   │   ├── notification.py              # notification fields: user_id, title, message, type, is_read, created_at
│   │   ├── feedback.py                  # feedback fields: message_id, user_id, rating, comment, created_at
│   │   └── audit_log.py                 # audit_log fields: user_id, action, resource_type, resource_id, metadata, created_at
│   ├── schemas/                         # Pydantic request/response models
│   │   ├── auth.py                      # RegisterRequest, LoginRequest, TokenResponse, MeResponse, ForgotPasswordRequest, ResetPasswordRequest
│   │   ├── user.py                      # UserResponse, UserUpdateRequest, UserListResponse
│   │   ├── chat.py                      # ChatRequest, ChatResponse
│   │   ├── conversation.py              # ConversationResponse, ConversationListResponse
│   │   ├── knowledge.py                 # KnowledgeCreate, KnowledgeUpdate, KnowledgeResponse, KnowledgeListResponse
│   │   ├── faq.py                       # FAQCreate, FAQUpdate, FAQResponse, FAQListResponse
│   │   ├── ticket.py                    # TicketCreate, TicketUpdate, TicketResponse, TicketListResponse
│   │   ├── department.py                # DepartmentCreate, DepartmentUpdate, DepartmentResponse, DepartmentListResponse
│   │   ├── notification.py              # NotificationResponse, NotificationListResponse
│   │   ├── feedback.py                  # FeedbackCreate, FeedbackResponse
│   │   └── common.py                    # PaginationParams, PaginatedResponse, SuccessResponse, ErrorResponse
│   ├── api/
│   │   ├── router.py                    # Aggregates all route modules under /api/v1 prefix
│   │   └── routes/
│   │       ├── auth.py                  # register, login, refresh, logout, me, forgot-password, reset-password
│   │       ├── users.py                 # list/get/update users (admin), /me endpoints (student self)
│   │       ├── chat.py                  # POST /chat (process message + return response)
│   │       ├── conversations.py         # list, get, delete conversations (ownership-checked)
│   │       ├── knowledge.py             # CRUD for knowledge base (admin/staff authorized)
│   │       ├── faqs.py                  # CRUD for FAQs
│   │       ├── tickets.py               # create (student), list (role-scoped), get, update (staff/admin)
│   │       ├── departments.py           # CRUD for departments
│   │       ├── notifications.py         # list user notifications, mark as read
│   │       ├── feedback.py              # submit feedback
│   │       ├── analytics.py             # overview, intents, tickets, feedback analytics (admin)
│   │       ├── admin.py                 # misc admin actions (role changes, audit log access)
│   │       └── health.py                # /health and /health/database
│   ├── services/                        # Business logic layer (between routes and DB/AI)
│   │   ├── auth_service.py              # register, login, refresh, logout, forgot/reset password
│   │   ├── user_service.py              # create, get, list, update, delete users
│   │   ├── chat_service.py              # Orchestrates chat pipeline: auth -> conv -> message -> intent -> RAG -> LLM -> guardrails -> save -> return
│   │   ├── conversation_service.py      # create, list, get, delete conversations
│   │   ├── knowledge_service.py         # CRUD + embedding regeneration + audit log + vector search update
│   │   ├── faq_service.py               # CRUD FAQs
│   │   ├── ticket_service.py             # create, list (scoped), get, update, assign, status transitions, notifications
│   │   ├── department_service.py        # CRUD departments
│   │   ├── notification_service.py      # create notifications, list, mark read
│   │   ├── feedback_service.py          # create feedback, retrieve (analytics)
│   │   └── analytics_service.py         # aggregate queries for overview, intents, tickets, feedback
│   ├── ai/                              # AI/LLM logic, separated from business/services
│   │   ├── llm_client.py                # Provider-agnostic LLMClient class (async generate). Configurable via env (model, base_url, key). Internally uses OpenAI-compatible SDK if applicable but doesn't leak abstraction.
│   │   ├── intent_classifier.py         # classify(text) -> {intent, confidence}. Uses LLM with intent prompt + 13 intents (course_registration, admission, exam_schedule, academic_calendar, results, portal_problem, password_change, personal_details, departmental_issue, fees, general_information, human_support, unknown). Keyword-based fallback if LLM unavailable.
│   │   ├── rag_service.py               # RAG pipeline: embed query -> vector search knowledge_base -> rank/filter -> return list of {title, content, category, id} sources. Handles graceful fallbacks if vector search not available (category/keyword search).
│   │   ├── embeddings.py                # Embeddings module: text -> vector (configurable provider; reuses LLM config or separate embedding model env var). Batch support for knowledge seeding.
│   │   ├── prompt_manager.py            # build_intent_prompt(), build_answer_prompt(context, intent, question), build_rag_prompt(question, sources), build_escalation_prompt(reason). Centralized prompt storage.
│   │   ├── response_generator.py        # generate_response(question, intent, sources, confidence) -> response text + requires_human_support flag. Orchestrates prompt_manager + llm_client.
│   │   └── guardrails.py                # validate_response(response, question, sources) -> cleaned response + escalation flag. Checks: no hallucinated policies, no private data exposure, no prompt leakage, insufficient-knowledge detection, sensitive-issue escalation.
│   ├── dependencies/                    # FastAPI Depends injection helpers
│   │   ├── auth.py                      # get_current_user (JWT), require_roles(*roles), get_optional_user
│   │   ├── database.py                  # get_db (returns the singleton motor db)
│   │   └── permissions.py               # ownership checks (e.g., owns_conversation, owns_ticket)
│   ├── constants/
│   │   ├── intents.py                   # INTENTS enum/const list, intent descriptions, keyword hints
│   │   ├── roles.py                     # ROLES: student, staff, admin, super_admin + role hierarchy helpers
│   │   ├── statuses.py                  # TICKET_STATUSES (open, in_progress, waiting_for_student, resolved, closed), CONVERSATION_STATUSES, KNOWLEDGE_STATUSES, FAQ_STATUSES
│   │   └── priorities.py                # TICKET_PRIORITIES: low, medium, high, urgent
│   └── utils/
│       ├── validators.py                # Reusable validators (email, phone, matric format, safe-string for MongoDB injection)
│       ├── pagination.py                # paginate(collection, query, page, limit, max_limit=100) -> PaginatedResponse
│       ├── helpers.py                   # Misc: generate_ticket_number(), utcnow(), mask_sensitive(), merge_dicts()
│       └── ids.py                       # ObjectId conversions, str->OID safe parsing, Pydantic ObjectId annotation
├── tests/
│   ├── conftest.py                      # Test fixtures: test client, test db (separate env), seed test data, auth headers helpers
│   ├── test_auth.py                     # registration, login, invalid creds, token validation, refresh, authorization, forgot/reset
│   ├── test_users.py                    # profile retrieval, profile update, unauthorized access, admin user list
│   ├── test_chat.py                     # new conversation, existing conversation, message storage, intent classification, AI failure fallback
│   ├── test_conversations.py            # list, get, delete, ownership enforcement
│   ├── test_knowledge.py                # create, retrieve, update, delete, authorization, embedding regeneration
│   ├── test_faqs.py                     # CRUD FAQs, status filters, pagination
│   ├── test_tickets.py                  # create, retrieve (role-scoped), update, assign, permissions, status transitions
│   └── test_feedback.py                 # create feedback, invalid message_id, duplicate guard
├── scripts/
│   ├── create_indexes.py                # Creates all MongoDB indexes (users.email, users.matric_number, conversations.user_id, messages.conversation_id, knowledge_base.category, tickets.ticket_number, feedback.message_id, etc.) safely (create_index with background=true)
│   ├── seed_database.py                 # Seeds demo departments (CSC, Physics, Math, Chemistry), sample knowledge (registration, admission, exam, calendar, portal troubleshooting, password recovery, departmental support), sample FAQs. All data clearly marked DEMO/SAMPLE.
│   └── create_admin.py                  # Reads ADMIN_EMAIL / ADMIN_PASSWORD from env or secure CLI prompt (getpass), creates super_admin user if not exists, outputs credentials reminder.
├── .env                                 # Local env (gitignored)
├── .env.example                         # All required env vars with descriptions and sample values
├── .gitignore                           # venv, __pycache__, .env, pytest cache, .pytest_cache, *.pyc, .mypy_cache
├── requirements.txt                     # FastAPI, uvicorn[standard], motor, pydantic, pydantic-settings, python-jose[cryptography], passlib[bcrypt], python-multipart, httpx, pytest, pytest-asyncio, email-validator
├── Dockerfile                           # Multi-stage? Slim python image. Non-root user. Installs deps, copies app. CMD: uvicorn app.main:app --host 0.0.0.0 --port 8000
├── docker-compose.yml                   # Dev convenience: only the backend service + env file pass-through. NO mongo container (Atlas is external).
├── README.md                            # Setup instructions per prompt Section 58
└── pyproject.toml                       # PEP 621 project metadata, tool configs (pytest, ruff optional)
```

---

## Phased Implementation Order (per prompt Section 54)

Each phase produces a runnable, testable subset of the system.

---

### Phase 1: Foundation & Infrastructure

**Goal:** FastAPI app boots, connects to MongoDB, health check returns 200, errors are formatted consistently.

**Tasks:**

1. **Create root config files**
   - `.gitignore`
   - `requirements.txt` (all packages listed above with reasonable pinned versions)
   - `pyproject.toml` (project metadata, pytest config: `asyncio_mode = "auto"`, testpaths = ["tests"])
   - `.env.example` (full list of env vars per prompt Section 36)
   - `Dockerfile`
   - `docker-compose.yml`

2. **Core module (app/core/)**
   - `config.py` — Pydantic Settings: reads env vars (APP_NAME, APP_ENV, DEBUG, MONGODB_URI, MONGODB_DATABASE, JWT_SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS, LLM_API_KEY, LLM_MODEL, LLM_BASE_URL, EMBEDDING_MODEL, EMBEDDING_BASE_URL, FRONTEND_URL, LOG_LEVEL). Validates required vars in non-dev environments.
   - `logging.py` — Structured JSON-ish logger. Adds request ID via Starlette middleware. Logs method, path, status code, duration. Filter: never logs values for keys matching password/secret/key/token/hash/uri/authorization.
   - `exceptions.py` — Exception classes: AppException(code, message, status_code=400), NotFound, Unauthorized, Forbidden, BadRequest, ServiceUnavailable. FastAPI exception handlers that format errors as `{success:false, error:{code, message}}`. Also catches RequestValidationError and generic Exception (no stack traces).
   - `security.py` — (placeholder stub for now; full implementation in Phase 2. We need it early because config/logging may reference it.) bcrypt context, empty JWT functions.

3. **Database module (app/database/)**
   - `collections.py` — Collection name constants: USERS, CONVERSATIONS, MESSAGES, KNOWLEDGE_BASE, FAQS, TICKETS, DEPARTMENTS, NOTIFICATIONS, FEEDBACK, AUDIT_LOGS. Helper function `get_collection(db, name)`.
   - `indexes.py` — Module-level list of tuples: (collection_name, field, unique_bool, kwargs). E.g. ("users", "email", True, {}), ("tickets", "ticket_number", True, {}), etc. per prompt Section 6.
   - `mongodb.py` — `MongoDBManager` singleton class:
     - `__init__(config: Settings)`: stores URI
     - `async connect()`: creates `AsyncIOMotorClient`, pings server, selects database
     - `async disconnect()`: `client.close()`
     - `get_collection(name)`: returns `db[name]`
     - `async health_check()`: returns {"status": "connected"|"disconnected"} after ping
     - Module-level instance `db_manager` populated at startup.

4. **Utils module (app/utils/)**
   - `ids.py` — Custom Pydantic field type `PyObjectId` (str serialization of ObjectId). Helper `to_obj_id(value)` and `safe_oid(value, default=None)`.
   - `pagination.py` — `PaginatedResponse` model + `paginate_cursor(cursor, page, limit, max_limit=100)` async function that returns `{items, pagination:{page, limit, total, pages}}`.
   - `helpers.py` — `utcnow()` returns timezone-aware UTC datetime, `generate_ticket_number()` returns "TCK-<sequential or random 5-digit>" (use db counter or random with collision check), `mask_email()`.
   - `validators.py` — `is_safe_query_string()` rejects MongoDB operator injection in strings (rejects strings containing `$` at certain positions), `validate_email()`, `validate_matric_number()`.

5. **Constants module (app/constants/)**
   - `roles.py` — `class UserRole(str, Enum): STUDENT="student", STAFF="staff", ADMIN="admin", SUPER_ADMIN="super_admin"`. `ROLE_HIERARCHY = {student: 0, staff: 1, admin: 2, super_admin: 3}` + helper `has_min_role(user_role, required_role)`.
   - `statuses.py` — Enums for TicketStatus, ConversationStatus, KnowledgeStatus, PublicationStatus (draft/published/archived).
   - `priorities.py` — `class TicketPriority(str, Enum): LOW="low", MEDIUM="medium", HIGH="high", URGENT="urgent"`.
   - `intents.py` — (stub; full list populated Phase 4)

6. **API skeleton + main.py**
   - `app/api/router.py` — `api_router = APIRouter(prefix="/api/v1")`. Imports all sub-routers (placeholders) and includes tags.
   - `app/api/routes/health.py` — `GET /api/v1/health` (returns `{success:true, data:{status:"healthy", database: db_status}}`) and `GET /api/v1/health/database` (detail).
   - `app/main.py`:
     - Creates FastAPI with title, description, version, docs_url="/docs", redoc_url="/redoc"
     - CORS middleware: origins = [FRONTEND_URL] (from config). Dev mode can add localhost variants. No `*` in prod.
     - Request ID middleware + logging middleware
     - Registers all exception handlers from `exceptions.py`
     - Startup event: `await db_manager.connect(settings)` + optional index creation call (if env flag)
     - Shutdown event: `await db_manager.disconnect()`
     - `app.include_router(api_router)`
     - `app.include_router(health_router, prefix="/api/v1", tags=["Health"])`

7. **Index creation script**
   - `scripts/create_indexes.py` — Loads settings, connects MongoDB, iterates the index list in `indexes.py`, calls `await collection.create_index(...)` with `background=True`. Run standalone: `python -m scripts.create_indexes`.

**Acceptance criteria for Phase 1:**
- `pip install -r requirements.txt` succeeds
- `uvicorn app.main:app --reload` starts without errors
- `GET /api/v1/health` returns JSON with `success: true`
- `GET /api/v1/health/database` reflects MongoDB Atlas connection
- `/docs` and `/redoc` render
- `/openapi.json` is valid
- Structured logs appear with request IDs
- Malformed requests return consistent `{success:false, error:{code, message}}`
- Any uncaught exception does NOT leak stack trace or secrets
- `python scripts/create_indexes.py` runs without errors against Atlas cluster

---

### Phase 2: Authentication, Users, Roles, Permissions

**Goal:** JWT auth works; students/staff/admins have distinct access. Register, login, refresh, me, forgot/reset password all functional.

**Tasks:**

1. **Models (app/models/)**
   - `user.py` — Field list plus `user_to_dict(user_oid, fields)` helper + `DEFAULT_USER_FIELDS` (excludes password_hash for responses).

2. **Schemas (app/schemas/)**
   - `auth.py` — RegisterRequest (name, email, password, matric_number, department_id, faculty, phone), LoginRequest (email, password), TokenResponse (access_token, refresh_token, token_type, expires_in), MeResponse (UserResponse shape), ForgotPasswordRequest (email), ResetPasswordRequest (token, new_password).
   - `user.py` — UserResponse (id, name, email, matric_number, role, department_id, faculty, phone, is_active, created_at), UserUpdateRequest (name?, phone?, faculty?, department_id?, password_old?, password_new?), UserListResponse (paginated).
   - `common.py` — PaginationParams (page: int = 1, limit: int = 20 with validator), SuccessResponse[T] generic model, ErrorResponse, PaginatedResponse[T].

3. **Core security completion**
   - `core/security.py` — `hash_password(password:str)->str` (bcrypt), `verify_password(plain, hashed)->bool`. `create_access_token(sub, role, expires_delta=None)->str` (jose.jwt.encode with JWT_ALGORITHM, includes sub, role, exp, type="access"). `create_refresh_token(sub)` (longer expiry, type="refresh"). `decode_token(token)` -> payload, raises on expiry/invalid. Optional: token blacklist in-memory for logout (simple set; alternatively skip immediate revocation and rely on short-lived access + refresh rotation).

4. **Dependencies (app/dependencies/)**
   - `auth.py` — `async def get_current_user(token = Depends(oauth2_scheme or Header(Authorization)), db = Depends(get_db)) -> UserResponse`. Reads token, finds user by ID (sub claim), checks `is_active`. Returns user dict (no password_hash). `require_roles(*roles)` returns a dependency that runs get_current_user then checks role hierarchy (uses `has_min_role`). `get_optional_user` for endpoints that optionally benefit from auth.
   - `database.py` — `async def get_db()` returns the motor db instance from `db_manager`.
   - `permissions.py` — Helpers: `async def ensure_ticket_owner_or_staff(current_user, ticket_id, db)`, `async def ensure_conversation_owner(current_user, conv_id, db)`. Raises Forbidden if check fails.

5. **Services**
   - `auth_service.py` — `register(db, data: RegisterRequest) -> UserResponse`. Checks email uniqueness, hashes password, assigns role=student by default (can't self-escalate). `login(db, data: LoginRequest) -> TokenResponse`. Verifies creds, issues tokens. `refresh_token(db, refresh_token) -> TokenResponse`. `logout(token)`. `forgot_password(db, email)` — issues a short-lived reset token (JWT) and logs the action (actual email sending is optional stubbed out of scope; return the token for dev/testing). `reset_password(db, token, new_password)`.
   - `user_service.py` — `get_user_by_id(db, id)`, `list_users(db, pagination, filters={})`, `update_user(db, user_id, data, current_user)` (students can only update self fields not role; admins can change more). `update_me(db, current_user, data)`.

6. **API Routes**
   - `routes/auth.py` — All 7 auth endpoints listed in prompt Section 8. Tags=["Authentication"]. Each endpoint has summary, description, request/response schemas, status codes.
   - `routes/users.py` — `GET /users/me` (authenticated), `PATCH /users/me`, `GET /users` (admin/super_admin, paginated), `GET /users/{id}` (admin/super_admin OR self), `PATCH /users/{id}` (admin/super_admin). Tags=["Users"].

7. **Update main.py**
   - Include auth + users routers.

**Acceptance criteria:**
- Student can register with email, password, matric_number.
- Student can login and receives access_token + refresh_token.
- `GET /api/v1/auth/me` with Bearer token returns own user info (no password_hash).
- Student cannot PATCH `/users/{another_id}` (403).
- Student registering with `role=admin` in payload is still assigned student role.
- refresh_token exchange works.
- `require_roles(UserRole.ADMIN)` endpoint returns 403 for a student JWT.
- Invalid JWT returns 401 with consistent error format.
- Forgot password flow returns reset token, reset-password endpoint accepts it and updates hash.

---

### Phase 3: Conversations, Messages, Chat Endpoints (no AI yet — stub AI)

**Goal:** Core chat flow works end-to-end with a stubbed AI (echo-based responder). Student can create conversation, send message, get response, retrieve history. All persisted in MongoDB.

**Tasks:**

1. **Models**
   - `conversation.py`, `message.py` — Field schemas as per prompt Sections 10.

2. **Schemas**
   - `chat.py` — ChatRequest { conversation_id: str | None, message: str }, ChatResponseData { conversation_id, message_id, response, intent, confidence, sources, requires_human_support }, ChatResponse = SuccessResponse[ChatResponseData].
   - `conversation.py` — ConversationResponse, ConversationListResponse (paginated).

3. **Services**
   - `conversation_service.py` — create_conversation(db, user_id, first_message_preview->title), list_user_conversations(db, user_id, pagination), get_conversation_by_id(db, conv_id, ensure_user_id), delete_conversation(db, conv_id, ensure_user_id).
   - `chat_service.py` — `async process_chat(db, current_user, req: ChatRequest) -> ChatResponseData`:
     1. If conversation_id is None: create_conversation()
     2. Validate conversation ownership
     3. Save student message (sender="student", content=req.message)
     4. Call **stub AI** (returns: response="Echo: ...", intent="general_information", confidence=0.5, sources=[], requires_human_support=False)
     5. Save assistant message (sender="assistant")
     6. Update conversation updated_at + title if first message
     7. Return ChatResponseData
   - The stub AI lives in `app/ai/response_generator.py` (stub impl, replaced Phase 4).

4. **AI stub files** (create dirs + placeholder implementation)
   - `ai/llm_client.py` — Stub: if LLM_API_KEY not set, `generate()` raises `LLMUnavailableError` (custom exception)
   - `ai/intent_classifier.py` — Stub: returns {"intent":"general_information","confidence":0.5}
   - `ai/prompt_manager.py` — Stub prompt builders (return template strings)
   - `ai/response_generator.py` — Stub generate_response (echo mode, no LLM call)
   - `ai/guardrails.py` — Stub validate_response (pass-through)
   - `ai/rag_service.py`, `ai/embeddings.py` — Empty/stub with not-implemented.

5. **API Routes**
   - `routes/chat.py` — `POST /api/v1/chat` (authenticated student+). Body: ChatRequest. Returns ChatResponse.
   - `routes/conversations.py` — `GET /api/v1/chat/conversations`, `GET /api/v1/chat/conversations/{conversation_id}`, `DELETE /api/v1/chat/conversations/{conversation_id}`. All ownership-checked via permission dependency.

6. **Update db/indexes for conversations/messages**
   - Ensure index definitions cover: conversations (user_id, created_at, updated_at); messages (conversation_id, created_at).

**Acceptance criteria:**
- `POST /chat` with conversation_id=null creates conversation + student msg + assistant msg in MongoDB.
- `POST /chat` with existing conversation_id appends messages.
- `GET /chat/conversations` lists only the authenticated student's conversations.
- `GET /chat/conversations/{id}` returns 403 when student tries another's conversation.
- Message timestamps correct; sender enum respected.
- Response envelope matches exact `{success,data:{conversation_id,message_id,response,intent,confidence,sources,requires_human_support}}` structure.

---

### Phase 4: Real AI (LLM Client, Intent Classification, Response Generation)

**Goal:** Plug in actual configurable LLM. Intent classifier uses LLM + prompt manager. Response generation works with fallback on LLM failure.

**Tasks:**

1. **Constants intents.py**
   - Populate all 13 intents as `class Intent(str, Enum)`. Add per-intent keyword hints dict `INTENT_KEYWORDS = {portal_problem: ["portal","login","can't access","error page"], ...}` for fallback keyword classifier.

2. **Prompt manager** (`ai/prompt_manager.py`)
   - `build_intent_prompt(question, intent_list, keyword_hints)` → system+user prompt that instructs the LLM to output a single JSON object `{"intent": "<one of list>", "confidence": <0..1 float>}` (use Structured Output or prompt-force JSON).
   - `build_answer_prompt(question, intent, context=None)` → System prompt (academic support persona per prompt Section 15 rules 1-10) + user question + optional context block.
   - `build_rag_prompt(question, sources)` → variant of answer prompt with clearly delimited source blocks.
   - `build_escalation_prompt(reason)` → short escalation offer string template.

3. **LLM client** (`ai/llm_client.py`)
   - Abstract base `class BaseLLMClient(ABC)` with `async generate(prompt: str, **kwargs)->str`, `async generate_structured(prompt: str, response_schema: dict)->dict`.
   - `class OpenAICompatibleLLMClient(BaseLLMClient)`: uses httpx async POST to `{LLM_BASE_URL}/chat/completions` (or official openai SDK async client if installed). Headers: Authorization Bearer LLM_API_KEY. Body: model=LLM_MODEL, messages=[{role, content}]. Retry (2 retries, exponential backoff 0.5s/1.5s). Timeout 30s.
   - Factory `get_llm_client(settings)` returns the configured instance. If LLM_API_KEY missing, returns a raising-stub that throws `LLMUnavailableError` every call.

4. **Intent classifier** (`ai/intent_classifier.py`)
   - `async classify(question: str, llm: BaseLLMClient) -> {intent, confidence}`:
     1. Build intent prompt via prompt_manager.
     2. Call `llm.generate_structured(...)`.
     3. Validate response: intent must be in allowed set, confidence in [0,1].
     4. On any failure (LLM down, bad JSON, unknown intent), **fallback to keyword classifier**: score each intent by keyword overlap, pick max with confidence = (match_count / len(question_words)) clamped. If no match, intent=unknown, confidence=0.1.

5. **Response generator** (`ai/response_generator.py`)
   - `async generate_response(question, intent, confidence, sources=None) -> {response, requires_human_support}`:
     - If low confidence (<0.3) → skip LLM, return fallback escalation message + requires_human_support=True.
     - Else build prompt (RAG prompt if sources, else answer prompt).
     - Call `llm.generate()`.
     - On LLM failure, return friendly fallback (per prompt Section 42: "I'm currently unable to process your request... create a support ticket...") + requires_human_support=True. Never leak errors.

6. **Guardrails** (`ai/guardrails.py`)
   - `def validate_response(question: str, response: str, sources: list | None, confidence: float, intent: str) -> {response: str, requires_human_support: bool, escalate_reason: str | None}`:
     - If response contains ANY substring matching the system prompt's first 20 chars (leakage check) → redact + escalate.
     - If intent is institution-specific AND no sources exist AND confidence < 0.6 → prepend "I cannot verify official information on this... Please contact [support department]" and flag requires_human_support=True.
     - Regex-block personal identifiers of other students (e.g. other matric numbers in response not present in original question).
     - Never include fabrications: if the model says "I've updated your record" → replace with "I cannot perform account actions directly. Please..." + escalate.

7. **Wire everything into chat_service.py**
   - Replace stub AI pipeline with: detect_intent → (if warranted, retrieve knowledge — stubbed for now, empty sources) → generate_response → guardrails → save assistant message with intent/confidence/sources.

**Acceptance criteria:**
- With valid LLM_API_KEY in env, intent classification returns a valid enum member + confidence for sample questions (e.g., "My portal isn't working" → portal_problem with high confidence).
- Intent classification still works (keyword fallback) if LLM_API_KEY is blank or LLM raises an error.
- LLM unavailability returns the exact friendly fallback string per prompt Section 42, never 500, never stack trace.
- Guardrails block a test response that contains "I've updated your password in the system" → replaced with escalation.
- Guardrails prepend "I cannot verify official information..." when no RAG sources for intent=course_registration + low confidence.

---

### Phase 5: Knowledge Base, FAQs, Embeddings, RAG, Vector Search

**Goal:** Knowledge base CRUD with admin permission. Embeddings generated on create/update. RAG retrieves knowledge for chat pipeline. Vector search used; falls back gracefully.

**Tasks:**

1. **Models**
   - `knowledge.py`, `faq.py` — field definitions per prompt Sections 17/19.

2. **Schemas**
   - `knowledge.py`, `faq.py` — CRUD request/response models.

3. **AI modules completion**
   - `ai/embeddings.py`:
     - `BaseEmbeddingProvider(ABC): async embed(texts: list[str]) -> list[list[float]]`, `async embed_one(text)->list[float]`
     - `OpenAICompatibleEmbeddings`: POST to embeddings endpoint. Configurable: EMBEDDING_MODEL, EMBEDDING_BASE_URL, EMBEDDING_API_KEY (or reuses LLM creds). Dimension size stored.
     - Fallback provider (simple token-count pseudo-embedding for dev when no API key; warns loudly).
   - `ai/rag_service.py`:
     - `async retrieve_relevant(db, question: str, top_k=5, filters={}) -> list[source_dicts]`:
       1. Embed question via embeddings.embedding_one.
       2. Try Atlas vector search on `knowledge_base` collection via `$vectorSearch` aggregation (requires vector index defined; catch OperationFailure and fallback).
       3. Fallback: regex/keyword match on category + content (using intent classifier output to restrict category first), then cosine-sim score in-app if embeddings available.
       4. Rank/filter: de-duplicate by id, score threshold 0.7 (if metric available), return top_k.
       5. Map each result to {"id": oid_str, "title": str, "category": str, "content_snippet": truncated_content, "source": metadata.source}.

4. **Services**
   - `knowledge_service.py` — CRUD:
     - create(db, data, created_by_id): validate fields, call embeddings.embed_one(content) to populate embedding field, insert, log audit event `knowledge_created`.
     - list(db, pagination, filters={category, status, department_id}).
     - get(db, id).
     - update(db, id, data, updated_by_id): if `content` or `title` changed, regenerate embedding. Audit `knowledge_updated`.
     - delete(db, id, deleter_id): soft or hard delete (prompt says delete; use hard delete but log audit `knowledge_deleted`).
   - `faq_service.py` — CRUD similarly. Publish/draft status filters. Admin-only write.

5. **API Routes**
   - `routes/knowledge.py` — 5 endpoints, CRUD, auth=admin/staff for write, authenticated read.
   - `routes/faqs.py` — 5 endpoints, same pattern.

6. **Wire RAG into chat_service.py**
   - After intent detection, call `rag_service.retrieve_relevant(db, question, top_k=5, filters={category: intent_category_map(intent)})`.
   - Pass sources to response_generator.
   - Save assistant message.sources = sources (trim to id,title,category only — never include embedding vector).

7. **Update seed script + indexes**
   - Seed script creates knowledge documents with embeddings (requires embed provider; fallback is ok).
   - indexes.py: for knowledge_base, declare that `embedding` field has a vector index (separate create call; note that MongoDB Atlas Vector Search indexes are created via Atlas CLI / UI in practice; script can attempt `createSearchIndex` via pymongo if available, else print manual instructions in stdout).

**Acceptance criteria:**
- Admin can POST a knowledge document; after creation `GET /knowledge/{id}` returns it with populated metadata (created_by, timestamps).
- Student trying POST /knowledge receives 403.
- Knowledge update changes embedding when content changes.
- Sample seeded question "When does course registration close?" → RAG returns the seeded Course Registration knowledge document as first result.
- Chat now includes sources[] array in response when relevant docs found (sources[id, title, category]).
- If Atlas vector search not configured (index missing), chat still functions (falls back to keyword search) and logs a WARNING.
- No response body includes the `embedding` array.

---

### Phase 6: Tickets, Departments, Human Escalation

**Goal:** Tickets CRUD with role-scoped access. Departments managed. Chatbot can recommend ticket creation (requires_human_support flag). Ticket flow: open → in_progress → waiting_for_student → resolved → closed.

**Tasks:**

1. **Models**
   - `ticket.py`, `department.py` — field definitions per Sections 20/22.

2. **Schemas**
   - `ticket.py` — TicketCreate { subject, description, category, priority? }, TicketUpdate { status?, priority?, assigned_to?, internal_note? }, TicketResponse (includes ticket_number), TicketListResponse (paginated).
   - `department.py` — CRUD models.

3. **Services**
   - `department_service.py` — CRUD. List, get (any authenticated), write (admin only).
   - `ticket_service.py`:
     - create(db, current_user, data): auto-generate ticket_number, status=open, user_id=current_user.id, department_id = (data.department_id or user.department_id). Emit notification to department staff + welcome notification to student.
     - list(db, current_user, pagination, filters):
       - student: only where user_id == current_user.id
       - staff: where assigned_to == current_user.id OR department_id == current_user.department_id
       - admin/super_admin: all
     - get(db, current_user, ticket_id): ownership check per list rules.
     - update(db, current_user, ticket_id, data):
       - student: can only add description/comments (no status/priority/assigned changes). Status transitions: if status=waiting_for_student and student responds → in_progress.
       - staff/admin: can change status/priority/assigned_to, write to assigned_to (must be valid staff user in department).
       - All updates audit `ticket_updated` and emit `ticket_update` notification to student + assignee.
       - Status transitions validated via enum FSM (e.g., open→closed allowed only by admin).
     - assign(db, admin, ticket_id, staff_id): validates staff belongs to ticket's department.

4. **API Routes**
   - `routes/tickets.py` — 4 endpoints (POST, GET list, GET one, PATCH). Role scoped via service layer.
   - `routes/departments.py` — 5 endpoints.

5. **Wire escalation into chat_service.py**
   - After guardrails, if `requires_human_support == True`:
     - In the response text, append suggestion: "Would you like me to create a support ticket for this issue?" (via prompt_manager.build_escalation_prompt).
     - Do NOT auto-create tickets (per prompt, offer only). Frontend handles user accepting → calls POST /tickets.
   - For intent=portal_problem + unresolved (sources empty or low confidence) → requires_human_support=True.

6. **Notifications service (start)**
   - `notification_service.py` — `create(db, user_id, title, message, type)`, `list_for_user(db, user_id, pagination, only_unread=False)`, `mark_read(db, user_id, notification_id)` (ownership). Ticket events call this.

**Acceptance criteria:**
- Student can POST /tickets → gets ticket_number "TCK-xxxxx".
- Staff can GET /tickets and sees tickets in their department (not other depts unless super_admin).
- Student cannot see another student's ticket → 403.
- Student cannot PATCH ticket status → 403.
- Staff can assign ticket to themselves or another staff in same dept.
- Valid status transitions: open→in_progress→waiting_for_student→in_progress→resolved→closed work; invalid transitions return error.
- Notifications are auto-created for ticket creation and updates.
- Student asking about severe portal issue → chat response has requires_human_support=true + escalation offer.

---

### Phase 7: Feedback, Notifications API, Analytics, Audit Logs

**Goal:** Feedback submissions; notifications API; admin analytics endpoints; audit tracking for sensitive actions.

**Tasks:**

1. **Models**
   - `feedback.py`, `notification.py`, `audit_log.py`.

2. **Schemas**
   - `feedback.py` — FeedbackCreate { message_id: str, rating: "positive"|"negative", comment?: str }. Rating enum.
   - `notification.py` — NotificationResponse, mark-read response.
   - (analytics schemas inline in services.)

3. **Audit service helper**
   - `services/` — Create `audit_service.py` (or add to analytics_service.py). `log(db, user_id, action, resource_type, resource_id, metadata={})`. Insert into audit_logs collection.
   - Update knowledge_service, ticket_service, auth_service role changes, user_service updates to call log().

4. **Feedback service**
   - `feedback_service.py` — create(db, current_user, data): validates message_id exists, and message sender=assistant AND conversation belongs to user. Prevents duplicate feedback on same message_id by same user. Stores with created_at.

5. **Notification service API**
   - Finish notification service from Phase 6.
   - Routes: `routes/notifications.py` — `GET /api/v1/notifications` (user's own, paginated, ?unread=true), `PATCH /api/v1/notifications/{id}/read`.

6. **Analytics service + routes**
   - `analytics_service.py`:
     - overview(db) → total_students, total_conversations, total_messages, total_tickets, open_tickets, resolved_tickets, avg_feedback_rating (positive=1, negative=0), unanswered_count.
     - intents(db, days=30) → [{intent, count, avg_confidence}] top N.
     - tickets(db, days=30) → { by_status: {open:x,in_progress:y,...}, by_priority: {...}, by_department: [...] }, resolution_time_avg (resolved - created_at).
     - feedback(db, days=30) → total_positive, total_negative, top_comments (most recent), ratings_per_day.
   - All analytics queries avoid loading conversation content (only counts, intents, meta).
   - Routes: `routes/analytics.py` — 4 endpoints, all require admin/super_admin role.

7. **Admin route**
   - `routes/admin.py` — Extras: `GET /api/v1/admin/audit-logs` (paginated, filters: action, user_id, date range), `PATCH /api/v1/admin/users/{id}/role` (super_admin only), `POST /api/v1/admin/users` (create staff/admin users by admin, bypass self-signup role lock).

8. **Feedback route**
   - `routes/feedback.py` — `POST /api/v1/feedback` (authenticated). Returns success or validation error.

**Acceptance criteria:**
- Student can submit positive feedback on a valid assistant message.
- Duplicate feedback → 400 "Already submitted".
- Student submitting feedback on another student's message → 403.
- `GET /api/v1/notifications?unread=true` returns user's unread items.
- Admin `GET /api/v1/analytics/overview` returns sensible numbers (>=0).
- Admin modifies a knowledge doc → audit_logs has `knowledge_updated` entry with resource_id + timestamp + user_id.
- Super_admin PATCH user role staff→admin works; student trying same → 403.
- Audit logs never contain password hashes.

---

### Phase 8: Tests, Seed Scripts, Admin Creation, Docker, README

**Goal:** Test suite passes. Seed + admin scripts work standalone. Docker build succeeds. README complete.

**Tasks:**

1. **Scripts**
   - `scripts/seed_database.py` (prompt Section 39):
     - Departments: Computer Science (CSC), Physics (PHY), Mathematics (MAT), Chemistry (CHE).
     - Knowledge documents with clearly prefixed titles like "[DEMO] Course Registration Procedure" and content marked sample. Content covers: course registration steps, admission requirements, exam timetable process, academic calendar sample, portal troubleshooting steps (clear browser cache, try incognito, reset password, check network), password recovery flow, departmental contact info. Attach embeddings via provider (fallback allowed).
     - FAQs: 10 sample FAQs covering the same categories. Clearly demo-marked.
   - `scripts/create_admin.py` (prompt Section 40):
     - Tries `ADMIN_EMAIL, ADMIN_PASSWORD` from env first.
     - If missing, uses getpass/input prompts securely.
     - Checks if user exists by email; else creates super_admin.
     - Prints success.

2. **Tests (pytest + pytest-asyncio)**
   - `conftest.py`:
     - Fixture `settings` with test-only values, separate MONGODB_DATABASE suffixed with `_test`, JWT_SECRET_KEY="test-secret".
     - Fixture `db` — connects before tests, drops DB after session, creates indexes.
     - Fixture `client` — TestClient from httpx.AsyncClient against app with dependency overrides (get_db → test db, settings → test settings).
     - Fixtures: `student_user`, `staff_user`, `admin_user` — creates in DB, returns dict + access_token.
     - Helpers: `auth_headers(user_fixture)` → Bearer token.
   - `test_auth.py` — 15+ cases: register success, duplicate email, weak password, login success, wrong password, token valid, token expired, refresh rotation, me endpoint, admin role hidden from self-signup, forgot returns reset token, reset with bad token fails, logout blacklist works if implemented.
   - `test_users.py` — get me, update me (name, phone, password), student tries access other user → 403, admin list users, admin updates user department.
   - `test_chat.py` — new conv, existing conv, messages saved with correct sender, intent returned, LLM failure returns friendly fallback (override llm client fixture to raise), requires_human_support can be true in edge cases.
   - `test_conversations.py` — list convs empty → []; after POST chat → 1 conv; delete conv works; delete others conv → 403.
   - `test_knowledge.py` — student create → 403; admin create → 201; get returns; update changes embedding (mock embed provider); delete removes; list with category filter.
   - `test_faqs.py` — CRUD mirror tests.
   - `test_tickets.py` — student create → 201; ticket_number matches pattern; list own (student sees own, staff sees dept); status transitions valid/invalid; assign cross-department → error; student can't change priority; student adds notes when waiting_for_student → status moves to in_progress.
   - `test_feedback.py` — create positive on assistant msg → success; duplicate → error; student feedback on peer's msg → 403; invalid rating enum → validation error.

3. **Docker + compose**
   - `Dockerfile`:
     - Base `python:3.11-slim`.
     - WORKDIR /app.
     - Copy requirements.txt, install (--no-cache-dir).
     - Copy app/, scripts/.
     - Non-root user creation.
     - EXPOSE 8000.
     - CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"].
   - `docker-compose.yml`:
     - Single service `backend`.
     - build: ., ports: 8000:8000.
     - env_file: .env.
     - volumes: ./app:/app/app (dev hot reload optional via override).
     - No mongo service; Atlas external.

4. **README.md per Section 58**
   - Project overview, architecture diagram text, tech stack, requirements (Python 3.11+, MongoDB Atlas account, LLM API key).
   - Installation: venv + activate (Windows and Unix commands), pip install.
   - Environment variables: reference .env.example.
   - MongoDB Atlas setup: create cluster, get URI, add IP whitelist, create DB user.
   - Running locally: uvicorn command, health check, /docs.
   - Running with Docker: docker-compose up -d.
   - Create indexes + seed + create-admin scripts with exact commands.
   - Running tests: pytest -v.
   - API documentation /docs.
   - Auth flow explained + example curl requests (register, login, chat).
   - Chatbot architecture: pipeline 13 steps from prompt Section 44.
   - RAG architecture: diagram text.
   - Deployment: Docker image + env vars.
   - Troubleshooting: common errors (MongoDB connection, LLM auth, missing env vars, CORS).

5. **Final integration polish**
   - Verify all routes in `app/api/router.py` are imported (no 404 on any listed endpoint).
   - Verify tags match list in prompt Section 50.
   - Verify each endpoint's summary/description/response_model/tags populated.
   - Verify consistent `{success:true, data: ...}` wrapper across all successful responses (middleware or helper).

**Acceptance criteria:**
- `docker build -t chatbot-backend .` succeeds.
- `pytest -v` with proper test env → 90%+ tests pass.
- `python scripts/create_indexes.py` → runs against Atlas test cluster.
- `python scripts/seed_database.py` → creates demo depts/knowledge/faqs.
- `python scripts/create_admin.py` → creates super_admin (with env vars avoids prompt).
- README contains every section listed in prompt Section 58.
- Every endpoint documented in prompt has a route that responds (manual spot-check via /docs).
- No endpoint returns password_hash in any response.
- No log lines contain secrets.
- Final acceptance criteria of prompt Section 55: every bullet verified manually or by automated test.

---

## Cross-Cutting Architectural Constraints (Enforced in Every Phase)

- **No monolithic main.py.** Only router mounting, middleware, events live there.
- **Async everywhere.** Motor, httpx, LLM calls, `await` over `time.sleep()`.
- **4-layer stack:** Routes → Services → AI/Business Logic → Database.
- **Chat pipeline:** Auth → Validate → Conv → Save Student Msg → Intent → Retrieval → Confidence → LLM → Guardrails → Escalation decision → Save Assistant Msg → Return.
- **Never trust frontend.** Role ownership always re-derived from JWT user + DB lookup.
- **No secrets in responses/logs** (password_hash, JWT secret, LLM key, Mongo URI, internal prompts, stack traces).
- **Consistent envelopes:** Success: `{success:true, data}`. Error: `{success:false, error:{code, message}}`. Paginated: add `pagination` key at root.
- **Pagination max limit = 100** across all list endpoints; no unbounded queries.
- **PEP 8 + type hints on all public functions**; docstrings on services and AI functions.
- **Graceful degradation:** LLM down → chat still responds (fallback). DB down → health returns degradation.

---

## Final Delivery Checklist (Prompt Section 57)

- [ ] 1. Complete backend source code
- [ ] 2. Complete folder structure (matches Section 3)
- [ ] 3. `requirements.txt`
- [ ] 4. `.env.example`
- [ ] 5. Dockerfile
- [ ] 6. docker-compose.yml
- [ ] 7. `scripts/create_indexes.py`
- [ ] 8. `scripts/seed_database.py`
- [ ] 9. `scripts/create_admin.py`
- [ ] 10. Complete API routes (auth, users, chat, conversations, knowledge, faqs, tickets, departments, notifications, feedback, analytics, admin, health)
- [ ] 11. Pydantic schemas for each domain (schemas/)
- [ ] 12. Authentication system (JWT + bcrypt)
- [ ] 13. AI integration abstraction (LLMClient ABC + configurable provider)
- [ ] 14. Intent classification (13 intents + keyword fallback)
- [ ] 15. RAG implementation (embeddings + vector search + fallback)
- [ ] 16. Knowledge-base management (CRUD + embeddings + audit)
- [ ] 17. FAQ management
- [ ] 18. Ticket system (CRUD + role-scoped + status FSM)
- [ ] 19. Department management
- [ ] 20. Feedback system
- [ ] 21. Notification system
- [ ] 22. Analytics (4 endpoints)
- [ ] 23. Audit logging (audit_logs collection + writes)
- [ ] 24. Tests (pytest suite across 8 test modules)
- [ ] 25. README with setup instructions (Section 58 checklist)
- [ ] 26. API documentation (/docs, /redoc, openapi.json)
- [ ] 27. Example API requests (in README)
- [ ] 28. Example environment configuration (.env.example)
