# Dialog Kinerja Link Administration

**Goal:** Extend the existing admin panel to manage the actual document links inside Dialog Kinerja.

**Architecture:** A separate SQLite table and revision track documents, monthly folders, and unit reports. Existing links are migrated once from a committed seed file. Existing account/session/CSRF checks protect all mutations. Public rendering keeps HTML as an outage fallback.

- [x] Add migration, validated CRUD/reorder endpoints and independent revisions without changing existing accounts or menus.
- [x] Add a Dialog Kinerja tab and a form for section, document title, URL, month/unit, order and visibility.
- [x] Render the three public document groups from the database; preserve existing links and unavailable months.
- [x] Test migration, authentication, validation, duplicate months, CRUD, conflicts, persistence and separation from navigation menus.
- [x] Check desktop/mobile browser flows with a separate anonymous visitor; restart the user's local server and retain their account.

## Validation results

All 16 backend integration tests passed. Browser checks passed document add/edit/hide/show/reorder/delete, adding the May folder, creating a new unit report, persistence across reload, updates in an anonymous browser context, safe text rendering, native Escape dismissal and 320/390px layout. Desktop and phone screenshots were inspected. Existing account and menu rows were fingerprinted before migration and verified unchanged afterward; 27 initial dialog records were imported. The local app remains running at http://localhost:8765/ and the test server is stopped.
