# Archive AI Frontend

This directory contains the Vue 3 single-page application that replaces the original static HTML interface.

## Tech stack

- [Vue 3](https://vuejs.org/) with the Vue CLI build system
- [Vue Router](https://router.vuejs.org/) for client-side navigation
- [Pinia](https://pinia.vuejs.org/) for state management
- [Axios](https://axios-http.com/) for HTTP requests
- Global styles migrated from the legacy static site (`src/assets/styles/main.css`)
- [Vitest](https://vitest.dev/) + [Vue Test Utils](https://test-utils.vuejs.org/) for unit testing

## Project setup

```bash
cd frontend
npm install
```

Create a `.env.local` file (or export environment variables) to point the app at your backend API:

```bash
cp .env.example .env.local
```

Edit the file as needed:

```
VUE_APP_API_BASE_URL=http://localhost:8000/api
VUE_APP_TOKEN_STORAGE_KEY=archive_ai_token
```

## Development server

```bash
npm run serve
```

This starts the Vue CLI dev server at <http://localhost:8080>. The proxy/base URL is defined by `VUE_APP_API_BASE_URL`.

## Production build

```bash
npm run build
```

Outputs the production-ready bundle to `dist/`.

## Linting

```bash
npm run lint
```

## Unit tests

```bash
npm run test:unit
```

## Project structure

```
src/
  assets/styles/     # Global CSS migrated from the legacy frontend
  components/        # Reusable UI components (sidebar, tables, modals, toasts)
  layouts/           # Authenticated vs authentication layouts
  router/            # Route configuration with guards
  services/          # Axios instance + API helpers
  store/             # Pinia stores for auth, documents, chat, domains, users, UI state
  views/             # Page-level views for login, dashboard, documents, admin, chat
```

## Feature highlights

- **Authentication** – Login & register views with client-side validation, Pinia-powered session handling, token persistence, and router guards.
- **Dashboard** – Displays profile information, recent document activity, and quick links.
- **Documents** – Searchable, sortable table, modal workflow for text or CSV uploads (with validation), and detailed view with edit/delete flows.
- **Administration** – Role-gated views for domain and user management.
- **Chat** – Conversation list, streaming indicator, new conversation modal, and message composer.
- **Notifications** – Toast system for success/error messaging.

## Working with the backend API

All HTTP requests are made through the Axios instance in `src/services/api.js`. The instance automatically attaches the stored JWT and logs the user out when a 401/419 response is received.

## Migrating additional legacy styles or views

Legacy static assets remain under `../legacy_frontend/` for reference. When migrating new UI pieces, convert them into Vue single-file components and either scope styles locally or place shared rules inside `src/assets/styles/main.css`.
