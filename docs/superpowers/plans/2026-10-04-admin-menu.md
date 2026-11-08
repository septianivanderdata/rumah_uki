# Admin Menu Implementation Plan

> **For agentic workers:** Execute inline in this session; user authorized a working menu administration feature.

**Goal:** Let authenticated administrators manage shared portal menus without editing HTML or pushing Git.

**Architecture:** Flask provides authentication and menu CRUD; SQLite persists menus and sessions outside source control. Existing HTML pages request public menus and retain their static fallback if the API is unavailable. One shared dataset controls header, mobile navigation, footer and homepage service cards.

**Tech Stack:** Python 3.11+, Flask, SQLite, vanilla HTML/CSS/JavaScript. Gunicorn is specified for server deployment; hosting selection is pending user input.

## Tasks

- [x] Build server.py: restricted static routes, database initialization with existing menu seeds, local-only first-admin setup, password hashing, server-side sessions, rate limiting, Origin and CSRF checks, schema/URL validation, version conflicts and menu CRUD/reordering.
- [x] Build admin.html plus assets/admin.css and assets/admin.js: account setup/login, list, add/edit form, preview, visibility, navigation/card toggles, reorder, delete confirmation, loading/error/empty states and logout.
- [x] Add assets/menus.js and menu markers to all public pages. Render text safely, retain seed illustrations, keep mobile navigation functional after refresh and collapse long navigation to the menu button.
- [x] Add dependency specification, ignored private data, startup/backup/deployment documentation and administrator CLI account creation/reset.
- [x] Test authentication, authorization, cross-origin and CSRF protection, stored persistence, malformed/unsafe input, stale revisions, CRUD, hide/delete/reorder and blocked private-file routes with unittest.
- [x] Run browser checks for setup/login, CRUD reflected in a separate visitor context, responsive layout, Escape behavior, logout and original public routes. Leave the application running locally with no preset administrator password.

## Deployment constraints

Data must live on a persistent disk on the server. GitHub Pages can still serve the static fallback but cannot run the Python API. Production startup uses Gunicorn behind HTTPS with UKI_PUBLIC_ORIGIN set to the exact public origin, and local account setup disabled. Private credentials, session rows and database files are never served as static files or committed.

## Results

10 unittest integration checks pass. Real Chrome testing passed account setup, login, menu create/edit/hide/show/reorder/delete, an anonymous visitor in a separate browser context, safe rendering of HTML-like text, dynamic mobile link dismissal, shared updates, persistence across navigation and logout. Desktop and 390px admin screenshots were inspected; all original public routes have no horizontal overflow at phone width. Private data is ignored by Git. The old static server was replaced with the application at http://localhost:8765/. No administrator password is preset and the actual portal database has no administrator yet. Hosting remains unconfigured pending user preference.
