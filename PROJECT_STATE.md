# PROJECT_STATE.md — ClassPulse

Last updated: 2026-08-30

## Status

ClassPulse is a working Django 5.2 + PostgreSQL classroom attendance MVP.
The Monitor/CR authorization redesign and attendance audit history are complete.

The production instance is deployed at `http://84.200.192.35/` on Ubuntu 24.04
using Docker Compose, Gunicorn, PostgreSQL 16, and Nginx. Its database is empty
except for one `ADMIN` superuser; sample data was not loaded.

## Stack

```text
Backend: Django 5.2
Database: PostgreSQL via psycopg
Tests: Django test framework with SQLite in memory
Frontend: Django templates and forms
Admin UI: Django Unfold
Authentication: Custom accounts.User
QR generation: qrcode
Environment: python-dotenv
```

## Current roles

```text
ADMIN    Full administrative access
MONITOR  Access to all courses, reports, audit history, and CR promotion
CR       A promoted student; manages only actively assigned courses
STUDENT  Uses QR attendance for actively enrolled courses
```

CR permissions:

* view only courses where the CR has an active enrollment
* create sessions for assigned courses
* generate and refresh QR codes
* close active sessions
* assign and deactivate ordinary student enrollments
* create Student accounts with required assignment to one of the CR's courses
* view and edit ordinary Student accounts in assigned courses
* manually edit ordinary students' attendance
* manually edit their own attendance
* cannot edit or remove another CR
* cannot view unrelated Student accounts or globally deactivate accounts
* cannot view reports, CSV exports, or attendance audit history

Monitors can access every course regardless of which Monitor originally created
it. The `Course.monitor` field records the creating Monitor; it is not an
authorization boundary.

## Attendance rules

* One class session has exactly 3 sections.
* Each section is physically 45 minutes and counts as 1 attendance hour.
* Statuses are `PRESENT`, `LATE`, `ABSENT`, and `LEAVE`.
* Attendance is unique per student and section.
* Every 3 `LATE` records count as 1 absence equivalent.
* `LEAVE` is counted separately and is not an unexcused absence.
* Closing a session preserves existing records and creates `ABSENT` records for
  missing active enrollments.

## Implemented features

* Environment-based development, production, and isolated test settings
* Custom user roles and student-code validation
* Public login/logout pages for Monitor, CR, and Student accounts
* Monitor-only searchable student directory with create and edit forms
* Safe student deactivation/restoration that disables active enrollments while
  preserving attendance and audit history
* Monitor-only promotion of existing students to CR
* Monitor-only course creation page with code and date validation
* Course and active enrollment management
* Safe enrollment deactivation that preserves historical attendance
* Course-scoped CR authorization enforced in views and attendance services
* Transactional creation of sessions and their three fixed sections
* Manual attendance for one section or all sections
* Secure, expiring, refreshable QR tokens
* Enrollment, token, active-session, expiry, and duplicate-scan checks
* Transactional session closing and missing-record absence creation
* Monitor-only reports, student details, and summary/detail CSV exports
* Monitor/Admin report center with searchable course selection and interactive,
  summary CSV, or detailed CSV output choices
* Role-aware signed-in homepage for Monitor/Admin, CR, and Student workflows
* Monitor/CR operational dashboard with metrics, today's schedule, upcoming
  sessions, and missing-attendance attention queue
* Monitor dashboard recent attendance activity sourced from the audit history
* Student dashboard with enrolled courses, upcoming classes, personal totals,
  and recent section attendance
* Student/CR notification inbox with unread state and ownership-safe read actions
* Automatic roster notifications when sessions are created and personal
  notifications when attendance is entered or changed, including admin edits
* Monitor/CR class-update composer on each accessible session
* Environment-configured SMTP delivery with console development mode and
  sent, failed, or skipped delivery tracking
* Course-scoped monthly session calendar with month navigation, course/status
  filters, direct session links, and date-prefilled session creation
* Immutable admin presentation of attendance audit history
* Monitor-only web audit page showing actor, old/new status, source, note, and time
* Audit entries for successful manual, QR, system-close, and admin attendance writes
* Django Unfold admin dashboard
* Responsive frontend design system with course cards, status badges, polished
  forms, mobile tables, focused QR presentation, and consistent empty states
* Fully clickable course cards and reusable searchable, keyboard-friendly
  student selectors for enrollment, promotion, and attendance entry
* Idempotent sample-data command
* Docker production stack with isolated web/database/proxy services, health
  checks, automatic migrations, restart policies, and persistent data volumes
* GitHub Actions CI/CD on pushes to `main`, with tests before deployment,
  environment-scoped secrets, a dedicated SSH account, and health-gated releases

## Database migrations

The current migrations preserve existing data:

* `accounts.0003` converts `TEACHER` roles to `MONITOR`, adds `CR`, and renames
  the demo username when safe.
* `courses.0002` renames `Course.teacher` to `Course.monitor`.
* `courses.0003` permits both Monitor and Admin users to create courses.
* `attendance.0004` creates `AttendanceAuditLog`.
* `attendance.0005` imports existing attendance as an audit baseline and
  normalizes existing superusers to the `ADMIN` role.
* `attendance.0006` allows both Student and CR users in attendance records.
* `accounts.0004` adds durable in-app notifications and email delivery status.

## Sample data

Run:

```bash
python manage.py seed_sample_data
```

Credentials:

```text
Monitor: sample_monitor
Students: sample_student_1, sample_student_2, sample_student_3
Password: classpulse123
```

The command creates `DEMO-101`, three active enrollments, and one active session.

## Commands

```bash
python manage.py migrate
python manage.py seed_sample_data
python manage.py runserver
python manage.py test
python manage.py makemigrations --check --dry-run
```

## Current verification

```text
python manage.py test: 163 tests passed
python manage.py makemigrations --check --dry-run: no changes detected
production Docker services: web and PostgreSQL healthy; Nginx reachable
production data: 1 Admin plus 1 user-created Monitor, 0 courses, 0 enrollments,
0 sessions, 0 attendance
```

## Known limitations

* This remains an MVP with simple Django templates.
* Audit web history shows the newest 500 entries and has no filtering UI yet.
* Email is delivered after the database commit in the web request; this MVP has
  no background job queue. SMTP failures do not undo attendance or session data.
* The current IP-only deployment uses HTTP. Add a domain and trusted certificate
  before enabling production HTTPS redirects, secure cookies, and HSTS.
