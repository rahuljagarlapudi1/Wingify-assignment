# Wingify Assignment — Backend Services

This README documents backend design, APIs, security, and operational best practices for the Financial Document Analyzer. It highlights how the backend is structured for scalability, security, and observability.

---

## ⚙️ Backend Architecture

- **FastAPI** app factory with modular routers.
- **MongoDB + Beanie ODM** for users, documents, and analyses.
- **Redis + Celery/RQ** for background jobs and task queues.
- **Singleton lifecycle** pattern for heavy clients (LLM, Redis, Celery, OCR).

---

## 🔑 API Surface

- **Auth**: register, login, me, OTP issue/verify.
- **Documents**: upload, list, detail, soft-delete; admin-only hard-delete with audit.
- **Analysis**: start, status, result, export; supports rate limits with Retry-After.
- **Admin**: reset password, enable/disable user, fetch errors, view user logs.

---

## 🔐 Security & Privacy

- JWT-based auth with expiry and refresh tokens.
- RBAC with role checks (user/admin).
- Upload hygiene (file size/type caps, antivirus scanning, signed URLs).
- PII masking in logs with user-id correlation.

---

## 📈 Observability

- Structured JSON logs with request, user, and document IDs.
- LLM observability: latency, token usage, error tags.
- Metrics: queue depth, wait times, analysis durations, error rates.

---

## 🧪 Testing

- Unit tests for models, security, and utilities.
- Integration tests for API routes with test DB/containers.
- End-to-end tests with docker-compose: upload → analyze → retrieve result.

---

## 🛡️ Ops & Reliability

- Backoff and retry policies for network, DB, and queue failures.
- Dead-letter strategy for failed analyses with replay tooling.
- Graceful shutdown with in-flight job draining.
