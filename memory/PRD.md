# AURA Campus — Academic & Club Community Platform

## Original Problem Statement (User Pivot, Feb 2026)
Build an academic + club community platform for a college campus with these modules:
1. Department & Year-wise Announcement Groups (CR/DCR post only, attendance tracker, deadline calendar).
2. Anonymous Query Groups — encrypted IDs, professors/seniors/peers answer, unanswered queries escalate to Seniors after 48h and Alumni after 7 days. Resolved queries auto-archive after 7 days.
3. Club Groups with sub-cells (media, writing, event management) + yearly calendar + past 5-year event archives.
4. Temporary Groups that auto-delete members after time/event completion.
5. General Complaint Group to admins/conveners.

## Architecture
- **Frontend**: React 19 + Craco + Tailwind, custom "Neo-Collegiate Daylight" theme (Cormorant Garamond serifs, Outfit sans, JetBrains Mono, warm paper backgrounds, tactile clay shadows, encrypted-ID shimmer chip). Icons via `@phosphor-icons/react`. Toasts via `sonner`.
- **Backend**: FastAPI + aiomysql (async MySQL 8, raw SQL, schema in backend/schema.sql) + JWT (HTTP-only cookie + Bearer fallback), bcrypt password hashing. All routes under `/api`.
- **Auth**: seeded demo users per role on startup (Admin, CR, DCR, Professor, Senior, Alumni, Student). See `/app/memory/test_credentials.md`.

## User Personas
- **Student**: post anonymous doubts, track attendance, file complaints, join clubs & temp groups.
- **CR / DCR**: post announcements to their department/year feed; everything a student can do.
- **Professor**: answer queries with verified role badge; can resolve queries.
- **Senior / Alumni**: visible role badges when answering; part of escalation pool.
- **Administrator**: role management panel; respond to complaints; view all users.
- **Convener**: respond to complaints.

## Features Implemented (Phase 2 — Feb 2026)
- Split-screen daylight auth page with warm campus hero, department/year/role selectors, and 6 demo persona quick-fill buttons.
- Sidebar shell with 8 sections (Dashboard, Announcements, Attendance, Anonymous Q&A, Clubs & Archives, Temporary Groups, Complaints, Admin Role Panel).
- Dashboard hero + 4 stat tiles + "What CRs pinned" + "Latest anonymous questions" strips (live from `/api/stats/overview`).
- Announcements: CR/DCR-gated composer (kind, deadline picker), deadline calendar strip, magazine-style feed.
- Attendance: add subjects, mark Present/Absent, SVG donut rings with 75% threshold colours.
- Anonymous Q&A: rotating `enc_usr_xxxx` IDs, escalation stage computed on-read (peers → seniors → alumni → archived), resolved queries auto-archive after 7 days, Active/Archived tabs.
- Clubs & Archives: 4 seeded clubs with cover images, cells and 5-year archive tiles.
- Temporary Groups: auto-expire on `expires_at`, join tracker, hours preset dropdown.
- Complaints: student → admin/convener workflow with response trail.
- Admin Panel: full user table with live role dropdowns (self-role change re-syncs session).

## APIs
Full list in `/app/memory/test_credentials.md`.

## Backend Test Report (iteration_2)
- Backend: 21 / 21 passing (pytest, `/app/backend/tests/backend_test.py`).
- Frontend: all critical flows verified for CR / Student / Admin personas.

## Prioritized Backlog (P2)
- P2: Real-time updates via WebSocket for announcements & queries.
- P2: Rich text / attachments for queries & announcements.
- P2: Professor analytics dashboard (response rates, question density heatmap).
- P2: Push / email notifications for escalations.
- P2: Split App.js into per-feature modules (currently ~1100 lines).
- P2: Migrate `on_event` startup to FastAPI lifespan handler.

## Next Action Items
- **Push Notifications**: Email or in-app pings when a query escalates to seniors or alumni.
- **Attachment Uploads**: Let students attach screenshots or PDFs to anonymous doubts and complaints.
- **Weekly Digest**: Send CRs a Monday email of pinned announcements and open queries.
- **Professor Analytics**: A dashboard showing which professors answer fastest and which topics stay unanswered.
