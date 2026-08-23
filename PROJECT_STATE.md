# PROJECT_STATE.md — ClassPulse

Last updated: 2026-08-23

## Status

ClassPulse is a working Django 5.2 + PostgreSQL classroom attendance MVP.
The Monitor/CR authorization redesign and attendance audit history are complete.

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
* manually edit ordinary students' attendance
* manually edit their own attendance
* cannot edit or remove another CR
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
* Monitor-only promotion of existing students to CR
* Course and active enrollment management
* Safe enrollment deactivation that preserves historical attendance
* Course-scoped CR authorization enforced in views and attendance services
* Transactional creation of sessions and their three fixed sections
* Manual attendance for one section or all sections
* Secure, expiring, refreshable QR tokens
* Enrollment, token, active-session, expiry, and duplicate-scan checks
* Transactional session closing and missing-record absence creation
* Monitor-only reports, student details, and summary/detail CSV exports
* Immutable admin presentation of attendance audit history
* Monitor-only web audit page showing actor, old/new status, source, note, and time
* Audit entries for successful manual, QR, system-close, and admin attendance writes
* Django Unfold admin dashboard
* Idempotent sample-data command

## Database migrations

The current migrations preserve existing data:

* `accounts.0003` converts `TEACHER` roles to `MONITOR`, adds `CR`, and renames
  the demo username when safe.
* `courses.0002` renames `Course.teacher` to `Course.monitor`.
* `attendance.0004` creates `AttendanceAuditLog`.
* `attendance.0005` imports existing attendance as an audit baseline and
  normalizes existing superusers to the `ADMIN` role.
* `attendance.0006` allows both Student and CR users in attendance records.

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
python manage.py test: 129 tests passed
python manage.py makemigrations --check --dry-run: no changes detected
```

## Known limitations

* This remains an MVP with simple Django templates.
* Audit web history shows the newest 500 entries and has no filtering UI yet.
* Monitor course creation remains available through Django admin rather than a
  dedicated frontend form.
