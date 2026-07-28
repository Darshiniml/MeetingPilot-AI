# MeetingPilot backend architecture

## Folder responsibilities

- `app/api/`: HTTP transport. Routers parse requests, declare response contracts,
  and call services; they do not own business state.
- `app/services/`: business use cases. `MeetingService` owns the start, stop, and
  status transitions, making it reusable from HTTP, desktop, WebSocket, and jobs.
- `app/models/`: internal domain and future persistence representations. These
  must not be shaped by one frontend response.
- `app/schemas/`: Pydantic request/response contracts. They validate and document
  the public API independently of internal models.
- `app/config/`: typed environment configuration, including CORS and later
  database, provider, and deployment settings.
- `app/core/`: cross-cutting policies such as authentication, authorization,
  logging, security, and shared exception handling.
- `app/database/`: SQLite/SQLAlchemy sessions, migrations, repositories, and
  metadata adapters when persistence is introduced.
- `app/websocket/`: live transcript and meeting/agent event delivery.
- `app/agents/`: provider-agnostic orchestration for transcription, summaries,
  action items, RAG, and chat.
- `tests/`: behavior-level contract tests that protect frontend compatibility.

## FastAPI concepts used

`FastAPI` creates the ASGI application. `APIRouter` groups endpoints so each
feature can be mounted by the application factory. `CORSMiddleware` is
application-wide middleware that permits the configured frontend origin to call
the API from a browser. `response_model` makes Pydantic validate, serialize, and
publish response shapes in OpenAPI documentation.

Routes receive `MeetingService` through `Depends(get_meeting_service)`. This is
dependency injection: FastAPI resolves the required collaborator at request
time instead of the route constructing it. Tests can override that provider, and
the in-memory implementation can later be replaced with a persisted one without
changing endpoint code.

## Imports at a glance

- `fastapi` provides application, router, and dependency primitives.
- `fastapi.middleware.cors` provides browser-origin middleware.
- `pydantic` defines API schemas and OpenAPI field metadata.
- `pydantic_settings` reads typed values from environment variables and `.env`.
- `dataclasses` defines the lightweight internal meeting state.
- `threading.RLock` protects in-memory state during concurrent requests.
- `typing.Annotated` attaches FastAPI dependency metadata to a typed parameter.

## Local development

From `backend/`, copy `.env.example` to `.env` if needed, then run:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The current `MeetingService` is intentionally process-local to preserve the
existing API behavior. Before multi-instance SaaS deployment, replace its state
store with a database-backed repository and publish lifecycle events through a
shared broker or WebSocket/event layer.
