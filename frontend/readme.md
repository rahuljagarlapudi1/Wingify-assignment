# Wingify Assignment — Frontend Application

This README describes the frontend application for the Financial Document Analyzer. It emphasizes professional UX practices, routing, error handling, and admin flows.

---

## 🖥️ Frontend Architecture

- **React + Vite** base application.
- **TailwindCSS + shadcn/ui** styling with accessible components.
- Routes: `/login`, `/`, `/docs/:id`, `/admin`, `/settings`.

---

## 🎨 User Experience

- Drag-and-drop and paste-to-upload with progress tracking.
- Live document analysis updates via WebSockets (fallback to polling).
- Badges for statuses: uploaded, processing, completed, failed.
- Delete with optimistic UI and undo option.
- Export analysis results in JSON/Markdown.

---

## 🔧 Admin Features

- `/admin` dashboard for error stream, failing jobs, queue depth.
- `/admin/users` for user management (reset password, enable/disable, OTP issue).
- `/admin/settings` for system overview and key rotation reminders.

---

## ⚠️ Error Handling

- Central fetch wrapper supports Retry-After for 429 errors.
- Error boundaries wrap major panels (table/detail).
- Clear empty/loading/error states for all key flows.

---

## ⚡ Performance & State

- Small cache by `doc_id` to prevent redundant fetches.
- Debounced actions (e.g., analyze) to avoid duplicates.
- Graceful fallback between polling and WebSocket.

---

## ♿ Accessibility & Theming

- Focus-visible states and reduced-motion respect.
- High-contrast theme toggle for accessibility compliance.

---

## 🧪 Testing

- Component-level tests for forms, tables, and detail views.
- E2E coverage (Playwright/Cypress) for core flows: login → upload → analyze → result.
- Admin workflows verified under test conditions.
