# Bou-inspired Portal Implementation Plan

> **For agentic workers:** Execute this plan task-by-task in the current session. The user authorized redesigning all four pages.

**Goal:** Give the internal compliance portal a cohesive, photo-led design inspired by https://wearebou.com/.

**Architecture:** Keep the four static HTML routes and their existing external document links. Replace duplicated inline styles and scripts with shared assets/site.css and assets/site.js, with consistent navigation and footer markup.

**Tech Stack:** HTML, CSS, vanilla JavaScript; Chrome headless for browser validation.

---

## Design direction

Reference inspected via source and a 1440px browser screenshot. Bou uses a full-screen visual hero, centered light-weight sans-serif text, monochrome controls and generous spacing. Adapt that to the portal's audience: employees accessing reporting and performance documents.

Palette: carbon #101310, white #ffffff, mist #f4f5f2, stone #dfe2dc, muted #626760, maritime #36534b. Display: Manrope 400; body: DM Sans 400/500. Signature: full-viewport harbor photograph with a centered statement about integrity and a compact location/service capsule. Photography is illustrative, not a claim to depict Teluk Nibung.

Layout: photo hero → three service tiles → five compliance pillars → existing announcements → large typographic footer. Inner pages: breadcrumb and large left-aligned title → document groups → shared footer. Avoid decorative statistics and emoji-led cards; use document marks and clear links.

## Implementation

- [x] Create shared styling in assets/site.css with responsive layout at 1000px and 640px, keyboard focus and reduced-motion support.
- [x] Create assets/site.js for consistent mobile navigation, Escape dismissal, resize handling, scroll header and progressive reveals.
- [x] Rebuild index.html with the photo hero and existing subject matter, linking to the three service routes.
- [x] Update lhk.html, pengelolaan-kinerja.html and dialog-kinerja.html to the same navigation, typography and footer; retain their external document destinations. Replace unavailable month anchors with clearly labelled unavailable items; wire performance document cards to their existing quick-access destinations.
- [x] Replace DESIGN.md with the implemented visual system and photo source.
- [x] Verify each route in Chrome at desktop and mobile widths: no overflow, no script errors, menu open/close and Escape behavior, working local routes, retained external links and loaded photograph. Capture and review screenshots.

## Validation commands

Run a local server with `python3 -m http.server 8765 --bind 127.0.0.1`. Use Chrome DevTools Protocol to inspect each page at 1440×1000, 768×1024 and 390×844, capture screenshots, and assert navigation visibility, document links and zero horizontal overflow. Run `git diff --check` before completion. No dependency installation or build pipeline is needed for this static site.

## Results

All four routes passed browser checks at 1440px, 768px, 390px and 320px: zero horizontal overflow, one primary heading, loaded images and no JavaScript exceptions. Menu opening, Escape dismissal, link selection, desktop resize and reduced motion passed. Desktop and phone screenshots were inspected; document-introduction spacing was adjusted after review. Local route anchors and all original external document destinations were verified. The preview server remains running at http://localhost:8765/.
